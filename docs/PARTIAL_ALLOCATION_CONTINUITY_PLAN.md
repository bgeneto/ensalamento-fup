# Partial Allocation Continuity Plan

Plano técnico implementável para evoluir o modo de alocação parcial atual, preservando suas vantagens de flexibilidade, mas adicionando duas preferências de alto valor operacional:

1. manter, sempre que possível, todos os blocos de uma disciplina não híbrida na mesma sala
2. manter, sempre que possível, disciplinas diferentes de um mesmo professor na mesma sala ou, no mínimo, no mesmo contexto espacial

Este plano foi desenhado para o código atual, especialmente:

- `src/services/optimized_autonomous_allocation_service.py`
- `src/services/room_scoring_service.py`
- `src/services/manual_allocation_service.py`
- `src/services/hybrid_discipline_service.py`
- `src/config/scoring_config.py`

---

## Objetivos

### Objetivo principal

Evoluir o fluxo parcial de um modelo puramente guloso por dia para um modelo híbrido com:

- tentativa explícita de consolidação por disciplina
- fallback parcial por dia quando a consolidação não for viável
- preferência por continuidade espacial do professor ao longo do semestre

### Objetivos secundários

- preservar o suporte a disciplinas híbridas
- não quebrar a semântica atual de hard rules obrigatórias
- manter implementação incremental, testável e reversível
- evitar reescrever toda a arquitetura de alocação

---

## Diagnóstico do fluxo atual

Hoje o modo parcial faz o seguinte:

1. agrupa blocos pendentes por dia
2. ranqueia salas para cada grupo de dia de forma independente
3. escolhe a melhor candidata válida naquele momento

Isso funciona bem para split allocation, mas não modela explicitamente:

- a continuidade da disciplina inteira
- a continuidade espacial entre disciplinas de um mesmo professor

O efeito colateral é previsível:

- uma disciplina não híbrida pode ser fragmentada sem necessidade
- a primeira escolha local de uma sala por dia pode inviabilizar a consolidação dos dias restantes
- a alocação do professor fica dependente apenas de preferências explícitas já cadastradas, sem aproveitar o contexto construído durante o próprio semestre

---

## Princípios de projeto

### 1. Hierarquia de decisão, não score único indiferenciado

As duas novas exigências não devem entrar apenas como mais alguns pontos no score.

Elas devem entrar em uma política lexicográfica de decisão:

1. viabilidade e hard rules
2. consolidação da disciplina não híbrida em uma única sala
3. continuidade da própria disciplina já parcialmente alocada
4. continuidade espacial do professor
5. histórico, preferências e demais bônus existentes

Isso evita que um bônus secundário supere uma exigência estrutural mais importante.

### 2. Split como fallback, não como primeira escolha universal

Para disciplinas não híbridas, o fluxo deve tentar primeiro alocar todos os blocos pendentes em uma única sala.

Somente se isso não for possível, o algoritmo deve cair para o modo parcial por dia.

### 3. Continuidade do professor como preferência forte, não hard rule

A continuidade por professor melhora a operação, mas não deve derrubar a taxa de alocação.

Ela deve ser tratada como:

- bônus forte quando a mesma sala é possível
- bônus médio quando ao menos o mesmo prédio é possível
- bônus leve quando ao menos o mesmo tipo de sala é possível

---

## Estratégia de alto nível

### Novo pipeline proposto

1. Phase 0: Hybrid Detection
2. Phase 1: Hard Rules Allocation
3. Phase 1.5: Discipline Continuity Allocation
4. Phase 2: Partial Fallback Allocation
5. Phase 3: Reporting / metrics

### Significado de cada fase

#### Phase 0: Hybrid Detection

Sem mudança conceitual. Continua detectando disciplinas híbridas e dias historicamente laboratoriais.

#### Phase 1: Hard Rules Allocation

Sem mudança conceitual principal. Continua tentando resolver casos obrigatórios de forma direta.

#### Phase 1.5: Discipline Continuity Allocation

Nova fase.

Responsável por tentar consolidar em uma única sala todas as demandas:

- não híbridas
- com blocos pendentes
- sem solução já concluída em sala única

#### Phase 2: Partial Fallback Allocation

Fase atual mantida, mas com duas melhorias:

- só recebe disciplinas híbridas ou não consolidáveis
- passa a considerar continuidade da disciplina e do professor no score e no desempate

---

## Novo modelo conceitual

### 1. Continuity profile da disciplina

Cada demanda precisa ser pré-analisada antes da decisão.

Novo conceito sugerido:

```python
@dataclass
class DemandContinuityProfile:
    demanda_id: int
    codigo_disciplina: str
    is_hybrid: bool
    total_pending_blocks: int
    distinct_days: int
    compatible_full_room_ids: list[int]
    pending_blocks_by_day: dict[int, list[tuple[str, int]]]
    existing_room_ids: list[int]
    preferred_existing_room_id: int | None
    professor_anchor_room_id: int | None
    professor_anchor_building_id: int | None
    professor_anchor_room_type_id: int | None
```

Responsabilidade:

- concentrar a informação necessária para decidir se vale tentar consolidar a disciplina inteira antes do split

### 2. Sala âncora do professor no semestre

Novo conceito sugerido:

```python
@dataclass
class ProfessorAnchor:
    professor_id: int
    semester_id: int
    room_id: int | None
    building_id: int | None
    room_type_id: int | None
    source: str  # current_semester | historical | inferred
    allocation_count: int
```

Regra de construção da âncora:

1. preferir a sala mais usada pelo professor no semestre atual
2. se ainda não houver alocações no semestre atual, usar a sala histórica mais frequente do professor
3. se não houver sinal suficiente, âncora inexistente

Importante:

- a âncora não é imutável
- ela deve poder ser recalculada a cada fase ou lote de decisões

---

## Algoritmo proposto

## Etapa A: pré-análise das demandas

Antes de iniciar a fase 1.5, construir o perfil de continuidade de cada demanda pendente.

Para cada demanda:

1. identificar se é híbrida
2. calcular blocos pendentes
3. agrupar blocos pendentes por dia
4. calcular salas viáveis para todos os blocos pendentes da disciplina
5. detectar se a própria disciplina já possui uma sala parcialmente usada
6. resolver a âncora do professor

### Regra crítica

O conjunto `compatible_full_room_ids` deve considerar simultaneamente:

- sala ativa
- sala habilitada para todos os blocos necessários
- hard rules satisfeitas
- ausência de conflito em todos os blocos pendentes

Esse conjunto é o dado central da fase 1.5.

---

## Etapa B: ordenação das demandas para continuidade

O critério de ordenação não deve ser apenas “tem vários dias”.

Deve ser uma ordenação por restritividade real.

### Ordenação lexicográfica sugerida

1. menor número de salas viáveis para todos os blocos pendentes
2. disciplina não híbrida antes de híbrida
3. maior número de dias distintos
4. maior número total de blocos pendentes
5. presença de hard rule específica de sala
6. existência de professor com âncora já definida
7. código da disciplina como desempate determinístico

### Justificativa

Isso ataca primeiro os casos em que a chance de consolidação é mais frágil.

Se a disciplina tem só 1 ou 2 salas viáveis para todos os dias, ela deve ser resolvida antes das disciplinas com grande espaço de manobra.

---

## Etapa C: phase 1.5 de consolidação da disciplina

Para cada demanda não híbrida ordenada:

1. se `compatible_full_room_ids` estiver vazio, enviar a demanda para fallback parcial
2. se houver exatamente uma sala viável, alocar todos os blocos pendentes nessa sala
3. se houver várias salas viáveis, ranquear essas salas por um novo score de consolidação

### Novo score de consolidação

Esse score deve reutilizar o scorer existente, mas acrescentar fatores próprios.

Fórmula sugerida:

```text
full_continuity_score =
    current_full_demand_score
    + discipline_room_continuity_bonus
    + professor_anchor_room_bonus
    + professor_anchor_building_bonus
    + professor_anchor_room_type_bonus
```

#### Componentes novos

- `discipline_room_continuity_bonus`
  - bônus alto se a disciplina já tem blocos alocados nessa mesma sala
- `professor_anchor_room_bonus`
  - bônus alto se a sala coincide com a âncora atual do professor
- `professor_anchor_building_bonus`
  - bônus médio se a sala fica no mesmo prédio da âncora
- `professor_anchor_room_type_bonus`
  - bônus menor se a sala tem o mesmo tipo da âncora

### Resultado esperado

Disciplinas não híbridas passam a ser consolidadas sempre que isso for viável, e o split deixa de ser o comportamento default nesses casos.

---

## Etapa D: fallback parcial com continuidade

Se a disciplina não puder ser consolidada por inteiro, o algoritmo continua usando alocação parcial por dia, mas com uma política melhor.

### Melhorias no score por dia

O score de bloco por dia deve ganhar novos componentes:

```text
block_group_score =
    current_block_group_score
    + discipline_existing_room_bonus
    + professor_anchor_room_bonus
    + professor_anchor_building_bonus
    + future_day_coverage_bonus
    - non_hybrid_room_fragmentation_penalty
```

#### Novos fatores

- `discipline_existing_room_bonus`
  - bônus alto se a sala já foi usada pela própria disciplina no semestre atual
- `future_day_coverage_bonus`
  - bônus para salas que também são viáveis para outros dias pendentes da mesma disciplina
- `non_hybrid_room_fragmentation_penalty`
  - penalidade ao abrir uma nova sala para disciplina não híbrida quando já existe outra sala em uso

### Observação importante

`future_day_coverage_bonus` é a peça que evita o erro típico do guloso puro:

- a melhor sala para hoje não é necessariamente a melhor sala para fechar a disciplina inteira

---

## Etapa E: continuidade do professor

### Objetivo

Fazer com que disciplinas diferentes do mesmo professor tendam a se concentrar na mesma sala ao longo do semestre, sem transformar isso em restrição rígida.

### Estratégia

Resolver a âncora do professor uma vez por lote de alocação e recalcular após cada fase de commits.

### Ordem de preferência

1. mesma sala da âncora do professor
2. mesmo prédio da âncora
3. mesmo tipo de sala da âncora

### Regra de segurança

O bônus de âncora nunca pode superar:

- hard rules
- viabilidade integral da disciplina não híbrida

Em outras palavras, a preferência do professor é forte, mas subordinada à viabilidade e à continuidade da própria disciplina.

---

## Mudanças de arquitetura recomendadas

## 1. Extrair um planner de continuidade

Adicionar um serviço novo:

- `src/services/allocation_continuity_planner.py`

Responsabilidades:

- construir `DemandContinuityProfile`
- resolver `ProfessorAnchor`
- calcular viabilidade integral por disciplina
- ordenar demandas para a fase 1.5

### Benefício

Evita inflar `OptimizedAutonomousAllocationService` com lógica de preparação e heurística.

## 2. Manter `RoomScoringService` como motor de score

Não mover o scoring para o planner.

O planner deve decidir:

- quando tentar consolidação
- em que ordem processar demandas
- que contexto adicional passar para o scorer

O scorer deve continuar responsável por:

- calcular pontos
- produzir breakdown auditável
- ordenar salas candidatas

### Padrão aplicado

- `Planner` para preparação e orquestração
- `Scorer` para avaliação de candidatos
- `Service` para execução e commit

---

## Mudanças concretas por arquivo

## 1. `src/services/allocation_continuity_planner.py`

### Novo arquivo

Adicionar:

- `DemandContinuityProfile`
- `ProfessorAnchor`
- `AllocationContinuityPlanner`

### Métodos sugeridos

```python
def build_demand_profiles(self, demands: list[Any], semester_id: int) -> dict[int, DemandContinuityProfile]
def resolve_professor_anchor(self, professor: Any, semester_id: int) -> ProfessorAnchor | None
def get_full_compatible_rooms(self, demanda: Any, pending_blocks: list[tuple[str, int]], semester_id: int) -> list[Any]
def prioritize_demands_for_continuity(self, profiles: dict[int, DemandContinuityProfile]) -> list[int]
def count_future_day_coverage(self, demanda: Any, room_id: int, pending_by_day: dict[int, list[tuple[str, int]]], semester_id: int) -> int
```

## 2. `src/services/optimized_autonomous_allocation_service.py`

### Alterações

Adicionar nova fase entre hard rules e partial fallback.

### Métodos sugeridos

```python
def _execute_discipline_continuity_phase(self, demands: list[Any], semester_id: int, dry_run: bool) -> PhaseResult
def _allocate_full_pending_demand_to_room(self, demanda: Any, room: Any, pending_blocks: list[tuple[str, int]], semester_id: int) -> bool
def _get_demands_for_partial_fallback(self, semester_id: int) -> list[Any]
```

### Fluxo novo no método principal

```text
Phase 0 -> Phase 1 -> Phase 1.5 -> recompute pending demands -> Phase 2 partial fallback
```

## 3. `src/services/room_scoring_service.py`

### Alterações

Adicionar contexto opcional de continuidade sem quebrar chamadas existentes.

### Novo contexto sugerido

```python
@dataclass
class ContinuityScoringContext:
    is_hybrid: bool = False
    discipline_existing_room_ids: list[int] = field(default_factory=list)
    professor_anchor_room_id: int | None = None
    professor_anchor_building_id: int | None = None
    professor_anchor_room_type_id: int | None = None
    future_day_coverage_count: int = 0
```

### Campos novos no breakdown

- `discipline_continuity_points`
- `professor_anchor_points`
- `future_coverage_points`
- `fragmentation_penalty`

### Métodos novos sugeridos

```python
def score_room_candidates_for_full_continuity(..., continuity_context: ContinuityScoringContext | None = None)
def _calculate_continuity_bonus(...)
def _calculate_professor_anchor_bonus(...)
def _calculate_future_day_coverage_bonus(...)
def _calculate_fragmentation_penalty(...)
```

## 4. `src/config/scoring_config.py`

### Extensão de pesos

Adicionar pesos configuráveis para continuidade.

Sugestão inicial:

```python
DISCIPLINE_EXISTING_ROOM_BONUS
PROFESSOR_ANCHOR_ROOM_BONUS
PROFESSOR_ANCHOR_BUILDING_BONUS
PROFESSOR_ANCHOR_ROOM_TYPE_BONUS
FUTURE_DAY_COVERAGE_PER_DAY
NON_HYBRID_FRAGMENTATION_PENALTY
```

### Diretriz

Esses pesos devem ficar em JSON como os demais, não hardcoded no serviço.

## 5. `tests/`

### Novos testes recomendados

- `tests/test_partial_allocation_continuity.py`
- `tests/test_professor_anchor_scoring.py`

---

## Ordem de implementação recomendada

## Fase A: infraestrutura mínima

1. criar `AllocationContinuityPlanner`
2. criar dataclasses de profile e anchor
3. adicionar pesos de continuidade ao config
4. adicionar contexto opcional ao scorer

### Critério de aceite

- sem alterar ainda o comportamento final do algoritmo
- apenas infraestrutura e testes unitários de cálculo

## Fase B: consolidação da disciplina

1. implementar `_execute_discipline_continuity_phase()`
2. calcular salas viáveis para todos os blocos pendentes
3. ordenar demandas por restritividade real
4. alocar disciplinas não híbridas em sala única quando possível

### Critério de aceite

- disciplina não híbrida multi-dia deve preferir sala única se existir ao menos uma candidata viável

## Fase C: fallback parcial com continuidade

1. enriquecer o score por dia com continuidade da própria disciplina
2. adicionar `future_day_coverage_bonus`
3. adicionar penalidade de fragmentação para não híbridas

### Critério de aceite

- quando a disciplina não puder ser totalmente consolidada, o fallback parcial ainda tende a minimizar o número de salas usadas

## Fase D: âncora do professor

1. resolver âncora por semestre atual ou histórico
2. aplicar bônus de sala, prédio e tipo
3. recalcular âncoras após commits relevantes

### Critério de aceite

- disciplinas compatíveis do mesmo professor tendem a convergir para a mesma sala sem reduzir desnecessariamente a taxa de alocação

---

## Estratégia de testes

## Unit tests

### Planner

- perfil identifica corretamente disciplina híbrida e não híbrida
- cálculo de salas viáveis integra disponibilidade, hard rules e conflitos
- ordenação por restritividade respeita a política definida
- resolução de âncora por professor funciona com semestre atual e histórico

### Scorer

- bônus de continuidade da disciplina é aplicado apenas quando faz sentido
- bônus de âncora do professor é aplicado por ordem correta: sala > prédio > tipo
- penalidade de fragmentação não afeta disciplinas híbridas
- `future_day_coverage_bonus` diferencia duas salas com score local igual

## Integration tests

- disciplina não híbrida em dois dias é alocada na mesma sala quando existe solução integral
- disciplina híbrida continua podendo splitar
- disciplina parcialmente alocada tenta completar na mesma sala já usada antes de abrir nova sala
- duas disciplinas do mesmo professor tendem a cair na mesma sala quando não há impedimentos
- hard rules continuam absolutas mesmo com bônus de continuidade

## Regression tests

- manter os testes já criados para hard rules, soft rules, híbridas e retomada de parciais

---

## Métricas operacionais sugeridas

Para validar a melhoria na prática, registrar no relatório/autonomous log:

- `% de disciplinas não híbridas alocadas em sala única`
- `média de salas por disciplina`
- `% de disciplinas do mesmo professor concentradas na mesma sala`
- `% de fallback parcial após tentativa de consolidação`
- `ganho/perda na taxa geral de alocação`

Essas métricas são essenciais para calibrar pesos sem adivinhar.

---

## Riscos e mitigação

### Risco 1: bônus excessivos degradarem taxa de alocação

Mitigação:

- tratar continuidade por professor como preferência, não como obrigação
- manter hard rules e viabilidade como critérios superiores

### Risco 2: fase 1.5 aumentar custo computacional

Mitigação:

- reutilizar batch conflict checking e filtros já existentes
- calcular perfis uma vez por lote
- limitar look-ahead ao conjunto de dias pendentes da própria disciplina

### Risco 3: acoplamento excessivo entre planner e scorer

Mitigação:

- planner prepara contexto e ordena
- scorer só calcula pontuação
- service orquestra commits

---

## Recomendação final

### Melhor primeiro passo

Implementar primeiro a Phase 1.5 de consolidação de disciplina não híbrida.

Razões:

- maior impacto prático imediato
- menor risco arquitetural
- resolve a principal deficiência do fluxo atual
- cria a base certa para depois adicionar a âncora do professor com segurança

### Segundo passo ideal

Adicionar continuidade da própria disciplina e `future_day_coverage_bonus` no fallback parcial.

### Terceiro passo ideal

Adicionar a sala âncora do professor com bônus calibráveis e métricas de acompanhamento.

---

## Resumo executivo

O modo parcial atual não precisa ser substituído. Ele precisa ser enquadrado por uma fase anterior de consolidação e enriquecido com contexto de continuidade.

Arquitetura proposta:

- `AllocationContinuityPlanner` prepara perfis e âncoras
- `OptimizedAutonomousAllocationService` passa a executar uma nova phase 1.5
- `RoomScoringService` recebe contexto de continuidade e continua sendo o motor de score

Com isso, o sistema passa a:

- preferir sala única para disciplinas não híbridas
- minimizar fragmentação quando split for inevitável
- favorecer continuidade espacial por professor
- preservar hard rules, híbridas e retomada de parciais
