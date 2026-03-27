# Partial Allocation Continuity Execution Checklist

Checklist de execução incremental do plano de continuidade do modo parcial.

Objetivo deste documento:

- quebrar o plano arquitetural em tarefas pequenas e sequenciais
- limitar o escopo de cada alteração
- explicitar arquivos-alvo, testes e critérios de aceite
- facilitar implementação por commits ou PRs curtos

Este roteiro assume o estado atual do código em:

- `src/services/optimized_autonomous_allocation_service.py`
- `src/services/room_scoring_service.py`
- `src/services/manual_allocation_service.py`
- `src/config/scoring_config.py`
- `tests/test_hybrid_manual_alignment.py`

---

## Estratégia de execução

### Regras operacionais

1. Cada tarefa deve preservar compatibilidade com o fluxo atual.
2. Toda mudança comportamental deve vir acompanhada de teste novo.
3. Primeiro introduzir infraestrutura e contexto; só depois alterar decisão algorítmica.
4. Alterações de score devem ser configuráveis via `scoring_config`, nunca hardcoded no fluxo.
5. O fallback parcial atual deve continuar funcionando durante toda a transição.

### Granularidade recomendada

- 1 tarefa = 1 commit lógico pequeno
- 1 tarefa de infraestrutura pode compartilhar commit com seus testes
- evitar misturar fase 1.5, score novo e âncora do professor no mesmo commit

---

## Fase 1: Infraestrutura mínima

## Tarefa 1.1: adicionar pesos de continuidade ao scoring config

### Objetivo

Criar os pesos necessários para continuidade de disciplina e de professor sem ainda alterar o algoritmo.

### Arquivos

- `src/config/scoring_config.py`
- `data/scoring_defaults.json`
- `data/scoring_config.json`

### Alterações

- adicionar pesos novos em `ScoringWeights`
- carregar pesos novos do JSON
- manter defaults conservadores, sem impacto acidental excessivo

### Pesos sugeridos

```python
DISCIPLINE_EXISTING_ROOM_BONUS
PROFESSOR_ANCHOR_ROOM_BONUS
PROFESSOR_ANCHOR_BUILDING_BONUS
PROFESSOR_ANCHOR_ROOM_TYPE_BONUS
FUTURE_DAY_COVERAGE_PER_DAY
NON_HYBRID_FRAGMENTATION_PENALTY
```

### Testes

Adicionar:

- `tests/test_scoring_config_continuity.py`

### Casos de teste

- config default expõe os novos pesos
- loader respeita override em `data/scoring_config.json`
- ausência de override mantém valor default

### Comando de verificação

```bash
pytest tests/test_scoring_config_continuity.py -q
```

### Critério de aceite

- scorer continua carregando normalmente
- nenhum comportamento funcional ainda muda

---

## Tarefa 1.2: criar contexto de score de continuidade

### Objetivo

Preparar o `RoomScoringService` para receber contexto de continuidade sem quebrar chamadas existentes.

### Arquivos

- `src/services/room_scoring_service.py`

### Alterações

- adicionar dataclass `ContinuityScoringContext`
- adicionar campos novos nos breakdowns:
  - `discipline_continuity_points`
  - `professor_anchor_points`
  - `future_coverage_points`
  - `fragmentation_penalty`
- manter os campos novos com default zero

### Testes

Adicionar ou expandir:

- `tests/test_room_scoring_continuity_context.py`

### Casos de teste

- scorer aceita `continuity_context=None`
- scorer aceita `continuity_context` preenchido sem quebrar contratos atuais
- breakdown continua serializável e soma corretamente

### Comando de verificação

```bash
pytest tests/test_room_scoring_continuity_context.py -q
```

### Critério de aceite

- sem regressão na assinatura pública existente
- sem alteração de ranking quando todos os novos pesos forem zero

---

## Tarefa 1.3: criar o planner de continuidade

### Objetivo

Extrair a lógica de preparação e heurística para um serviço próprio.

### Arquivos

- `src/services/allocation_continuity_planner.py`

### Alterações

- criar dataclasses:
  - `DemandContinuityProfile`
  - `ProfessorAnchor`
- criar classe `AllocationContinuityPlanner`
- implementar esqueleto dos métodos públicos

### Métodos mínimos

```python
build_demand_profiles()
resolve_professor_anchor()
get_full_compatible_rooms()
prioritize_demands_for_continuity()
count_future_day_coverage()
```

### Testes

Adicionar:

- `tests/test_allocation_continuity_planner.py`

### Casos de teste

- planner monta profile básico de demanda
- planner calcula `distinct_days` e `pending_blocks_by_day`
- planner detecta salas compatíveis integrais
- ordenação lexicográfica é determinística

### Comando de verificação

```bash
pytest tests/test_allocation_continuity_planner.py -q
```

### Critério de aceite

- novo serviço existe e é testável isoladamente
- nenhuma fase do algoritmo principal ainda muda

---

## Fase 2: Continuidade da disciplina não híbrida

## Tarefa 2.1: integrar o planner no serviço otimizado

### Objetivo

Injetar o planner no `OptimizedAutonomousAllocationService` sem ainda mudar o pipeline principal.

### Arquivos

- `src/services/optimized_autonomous_allocation_service.py`

### Alterações

- instanciar `AllocationContinuityPlanner` no `__init__`
- adicionar helpers internos para:
  - construir profiles
  - obter demandas candidatas à fase 1.5
  - separar demandas para fallback parcial

### Testes

Expandir:

- `tests/test_hybrid_manual_alignment.py`
ou adicionar:
- `tests/test_optimized_partial_continuity_bootstrap.py`

### Casos de teste

- serviço otimizado inicializa planner corretamente
- pipeline ainda produz o mesmo comportamento quando a fase 1.5 não está ativa

### Comando de verificação

```bash
pytest tests/test_optimized_partial_continuity_bootstrap.py -q
```

### Critério de aceite

- mudança apenas estrutural, sem impacto funcional ainda

---

## Tarefa 2.2: implementar alocação integral de blocos pendentes

### Objetivo

Criar a operação que aloca todos os blocos pendentes de uma disciplina em uma única sala.

### Arquivos

- `src/services/optimized_autonomous_allocation_service.py`

### Alterações

- implementar `_allocate_full_pending_demand_to_room()`
- reutilizar `create_batch_atomic()`
- garantir fresh conflict check imediatamente antes do commit

### Testes

Adicionar:

- `tests/test_partial_allocation_full_pending_commit.py`

### Casos de teste

- cria todas as alocações pendentes numa única sala
- ignora blocos já alocados
- falha corretamente se surgir conflito entre score e commit

### Comando de verificação

```bash
pytest tests/test_partial_allocation_full_pending_commit.py -q
```

### Critério de aceite

- operação integral funciona isoladamente
- reruns parciais continuam seguros

---

## Tarefa 2.3: adicionar Phase 1.5 de continuidade da disciplina

### Objetivo

Inserir a nova fase entre hard rules e fallback parcial.

### Arquivos

- `src/services/optimized_autonomous_allocation_service.py`

### Alterações

- implementar `_execute_discipline_continuity_phase()`
- rodar a fase após Phase 1 e antes da fase parcial
- usar apenas demandas:
  - não híbridas
  - com blocos pendentes
  - com `compatible_full_room_ids` não vazio

### Decisão da fase

- 1 sala viável: alocar diretamente
- várias salas viáveis: ranquear por score integral
- nenhuma sala viável: enviar para fallback parcial

### Testes

Adicionar:

- `tests/test_partial_allocation_continuity_phase.py`

### Casos de teste

- disciplina não híbrida multi-dia vai inteira para a mesma sala quando existe solução integral
- disciplina híbrida não entra na fase 1.5
- demanda sem sala integral cai corretamente no fallback

### Comando de verificação

```bash
pytest tests/test_partial_allocation_continuity_phase.py -q
```

### Critério de aceite

- split deixa de acontecer desnecessariamente em disciplinas não híbridas multi-dia

---

## Tarefa 2.4: restaurar ordenação por restritividade real na nova fase

### Objetivo

Ordenar a fase 1.5 por dificuldade real de consolidação, em vez de depender da ordem do repositório.

### Arquivos

- `src/services/allocation_continuity_planner.py`
- `src/services/optimized_autonomous_allocation_service.py`

### Alterações

- implementar a ordenação lexicográfica do profile
- integrar essa ordenação no processamento da fase 1.5

### Testes

Expandir:

- `tests/test_allocation_continuity_planner.py`
- `tests/test_partial_allocation_continuity_phase.py`

### Casos de teste

- demanda com menos salas integrais viáveis é processada antes
- desempates por dias distintos e total de blocos funcionam
- ordem final é determinística

### Comando de verificação

```bash
pytest tests/test_allocation_continuity_planner.py tests/test_partial_allocation_continuity_phase.py -q
```

### Critério de aceite

- a nova fase prioriza corretamente os casos mais frágeis

---

## Fase 3: Melhorar o fallback parcial

## Tarefa 3.1: adicionar bônus de continuidade da própria disciplina

### Objetivo

Quando o split for inevitável, minimizar a abertura de salas adicionais para a mesma disciplina.

### Arquivos

- `src/services/room_scoring_service.py`

### Alterações

- aplicar `DISCIPLINE_EXISTING_ROOM_BONUS`
- usar salas já existentes da própria disciplina no semestre atual
- refletir isso no breakdown

### Testes

Adicionar:

- `tests/test_discipline_room_continuity_scoring.py`

### Casos de teste

- sala já usada pela própria disciplina recebe bônus
- disciplina híbrida não recebe penalidade indevida
- breakdown mostra os pontos corretamente

### Comando de verificação

```bash
pytest tests/test_discipline_room_continuity_scoring.py -q
```

### Critério de aceite

- fallback parcial tende a completar na mesma sala antes de abrir outra

---

## Tarefa 3.2: adicionar penalidade de fragmentação para não híbridas

### Objetivo

Desencorajar abertura de nova sala para disciplina não híbrida quando já existe sala em uso.

### Arquivos

- `src/services/room_scoring_service.py`

### Alterações

- aplicar `NON_HYBRID_FRAGMENTATION_PENALTY`
- ativar a penalidade só para demandas não híbridas
- manter híbridas sem penalidade

### Testes

Expandir:

- `tests/test_discipline_room_continuity_scoring.py`

### Casos de teste

- disciplina não híbrida sofre penalidade ao abrir nova sala
- disciplina híbrida não sofre essa penalidade

### Comando de verificação

```bash
pytest tests/test_discipline_room_continuity_scoring.py -q
```

### Critério de aceite

- split continua possível, mas menos atraente para não híbridas

---

## Tarefa 3.3: adicionar future-day coverage bonus

### Objetivo

Corrigir o viés local do guloso por dia, premiando salas que também servem para outros dias pendentes da mesma disciplina.

### Arquivos

- `src/services/allocation_continuity_planner.py`
- `src/services/room_scoring_service.py`
- `src/services/optimized_autonomous_allocation_service.py`

### Alterações

- calcular `future_day_coverage_count`
- aplicar `FUTURE_DAY_COVERAGE_PER_DAY`
- injetar a contagem no `ContinuityScoringContext`

### Testes

Adicionar:

- `tests/test_future_day_coverage_bonus.py`

### Casos de teste

- entre duas salas com score local semelhante, vence a que cobre mais dias futuros
- contagem futura considera apenas blocos ainda pendentes

### Comando de verificação

```bash
pytest tests/test_future_day_coverage_bonus.py -q
```

### Critério de aceite

- fallback parcial fica menos míope nas primeiras escolhas

---

## Fase 4: Sala âncora do professor

## Tarefa 4.1: resolver âncora por professor

### Objetivo

Criar a lógica de identificação da sala âncora do professor no semestre.

### Arquivos

- `src/services/allocation_continuity_planner.py`

### Alterações

- implementar `resolve_professor_anchor()`
- priorizar semestre atual
- cair para histórico quando não houver alocações atuais

### Testes

Adicionar:

- `tests/test_professor_anchor_resolution.py`

### Casos de teste

- usa sala mais frequente do semestre atual
- usa histórico quando semestre atual ainda não tem alocação
- retorna `None` quando não há evidência suficiente

### Comando de verificação

```bash
pytest tests/test_professor_anchor_resolution.py -q
```

### Critério de aceite

- âncora resolvida de forma estável e auditável

---

## Tarefa 4.2: adicionar bônus de âncora ao score

### Objetivo

Aplicar continuidade espacial do professor no ranking das salas.

### Arquivos

- `src/services/room_scoring_service.py`

### Alterações

- aplicar bônus por:
  - mesma sala
  - mesmo prédio
  - mesmo tipo de sala
- refletir isso no breakdown agregado `professor_anchor_points`

### Testes

Adicionar:

- `tests/test_professor_anchor_scoring.py`

### Casos de teste

- mesma sala > mesmo prédio > mesmo tipo > nenhum vínculo
- bônus não supera hard rule inválida
- bônus convive com preferências explícitas do professor

### Comando de verificação

```bash
pytest tests/test_professor_anchor_scoring.py -q
```

### Critério de aceite

- disciplinas compatíveis do mesmo professor passam a convergir espacialmente sem quebrar viabilidade

---

## Tarefa 4.3: recalcular âncoras ao longo da execução

### Objetivo

Garantir que a âncora acompanhe o estado real do semestre enquanto novas alocações são criadas.

### Arquivos

- `src/services/optimized_autonomous_allocation_service.py`
- `src/services/allocation_continuity_planner.py`

### Alterações

- recalcular âncora ao fim da Phase 1.5
- opcionalmente recalcular por lote na fase parcial

### Testes

Expandir:

- `tests/test_professor_anchor_resolution.py`
- `tests/test_professor_anchor_scoring.py`

### Casos de teste

- nova alocação muda a âncora do professor quando ultrapassa a frequência anterior
- reordenação de escolhas posteriores passa a refletir a nova âncora

### Comando de verificação

```bash
pytest tests/test_professor_anchor_resolution.py tests/test_professor_anchor_scoring.py -q
```

### Critério de aceite

- continuidade do professor usa contexto vivo, não snapshot obsoleto

---

## Fase 5: Integração final e observabilidade

## Tarefa 5.1: enriquecer logs e resultados da alocação

### Objetivo

Dar visibilidade ao motivo da consolidação, fragmentação ou escolha por âncora.

### Arquivos

- `src/services/optimized_autonomous_allocation_service.py`
- `src/utils/allocation_logger.py`
- `src/services/autonomous_allocation_report_service.py`

### Alterações

- logar quando a disciplina foi consolidada integralmente
- logar quando caiu para fallback parcial
- logar quando a âncora do professor influenciou a decisão

### Testes

Adicionar ou expandir:

- `tests/test_allocation_decision_logging_continuity.py`

### Casos de teste

- resultado final contém indicação da fase 1.5
- breakdown/log mostra pontos de continuidade e âncora

### Comando de verificação

```bash
pytest tests/test_allocation_decision_logging_continuity.py -q
```

### Critério de aceite

- comportamento novo fica auditável e calibrável

---

## Tarefa 5.2: regressão integrada do modo parcial

### Objetivo

Executar uma bateria curta e representativa de regressão antes de liberar o novo fluxo.

### Arquivos de teste

- `tests/test_hybrid_manual_alignment.py`
- `tests/test_partial_allocation_continuity_phase.py`
- `tests/test_discipline_room_continuity_scoring.py`
- `tests/test_professor_anchor_scoring.py`
- `tests/test_future_day_coverage_bonus.py`

### Comando de verificação

```bash
pytest \
  tests/test_hybrid_manual_alignment.py \
  tests/test_partial_allocation_continuity_phase.py \
  tests/test_discipline_room_continuity_scoring.py \
  tests/test_professor_anchor_scoring.py \
  tests/test_future_day_coverage_bonus.py -q
```

### Critério de aceite

- continuam válidos os cenários já garantidos:
  - hard rules absolutas
  - soft rules e preferências funcionando
  - bônus híbrido manual/autônomo alinhado
  - retomada de demandas parcialmente alocadas
- novos cenários passam:
  - disciplina não híbrida multi-dia consolida quando possível
  - fallback parcial minimiza fragmentação
  - disciplinas do mesmo professor tendem à mesma sala

---

## Ordem recomendada de execução real

Executar nesta ordem:

1. Tarefa 1.1
2. Tarefa 1.2
3. Tarefa 1.3
4. Tarefa 2.1
5. Tarefa 2.2
6. Tarefa 2.3
7. Tarefa 2.4
8. Tarefa 3.1
9. Tarefa 3.2
10. Tarefa 3.3
11. Tarefa 4.1
12. Tarefa 4.2
13. Tarefa 4.3
14. Tarefa 5.1
15. Tarefa 5.2

---

## Ponto de partida recomendado

Se for começar agora, o melhor primeiro bloco é:

- Tarefa 1.1
- Tarefa 1.2
- Tarefa 1.3

Razão:

- prepara a infraestrutura certa
- não muda ainda o comportamento do algoritmo
- permite validar tipos, contratos e testes isolados antes de alterar a tomada de decisão
