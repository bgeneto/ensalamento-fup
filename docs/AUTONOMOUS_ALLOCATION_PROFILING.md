# Profiling da Alocação Autônoma Parcial

Este documento descreve como perfilar a rotina usada pelo botão `Executar Alocação Autônoma` da página `7_✅_Ensalamento.py`.

## Fluxo real analisado

O botão chama `OptimizedAutonomousAllocationService.execute_autonomous_allocation_partial()`.

Hoje a rotina executa, em alto nível:

1. carregar demandas pendentes
2. detectar disciplinas híbridas
3. fase 1 de regras rígidas
4. preparar perfis de continuidade
5. fase 1.5 de consolidação em sala única
6. preparar novamente perfis de continuidade
7. fase parcial por bloco/dia

O serviço agora expõe um campo `performance` no resultado com tempos por fase para reduzir o tempo de diagnóstico inicial.

## Suspeitas principais de custo

Os pontos abaixo são os candidatos mais fortes para explicar execuções perto de 2 minutos em bases maiores.

### 1. Perfil de continuidade com padrão N x consultas

Arquivo: `src/services/allocation_continuity_planner.py`

Suspeitas:

- `build_demand_profiles()` faz, por demanda, chamadas para:
  - `get_by_demanda()`
  - `find_rules_by_disciplina()`
  - `resolve_professor_anchor()`
  - `get_full_compatible_rooms()`
- `resolve_professor_anchor()` faz query de alocações e varre resultados para inferir âncora do professor.

Isso escala mal quando há muitas demandas e muito histórico.

### 2. Contexto de continuidade por dia/sala com explosão combinatória

Arquivo: `src/services/optimized_autonomous_allocation_service.py`

Suspeita principal:

- `_build_block_group_continuity_context()` chama `count_future_day_coverage()` para cada sala candidata.

Arquivo relacionado: `src/services/allocation_continuity_planner.py`

- `count_future_day_coverage()` faz verificações por sala, por dia futuro e por bloco:
  - `is_room_enabled_for_blocks()`
  - `check_conflict()`

Na prática isso pode virar algo próximo de:

`demandas x dias x salas x dias_futuros x blocos`

### 3. Ordenação com ocupação de sala consultada repetidamente

Arquivo: `src/services/room_scoring_service.py`

- os candidatos são ordenados usando `get_room_occupancy(...)`

Arquivo relacionado: `src/utils/room_utils.py`

- `get_room_occupancy()` consulta semestre atual e pode iterar por semestres anteriores
- isso acontece durante ordenações de listas de candidatos

Se houver dezenas de salas por demanda, o custo acumulado pode ser alto.

### 4. Verificações repetidas de regras, professor e demanda

Arquivos:

- `src/services/room_scoring_service.py`
- `src/services/optimized_autonomous_allocation_service.py`

Pontos suspeitos:

- `find_rules_by_disciplina()` repetido para a mesma disciplina
- `get_by_nome_completo()` repetido na resolução de professor
- `get_by_id()` repetido para a mesma demanda em fases diferentes

## Ferramenta adicionada

Foi adicionado o script:

- `profile_autonomous_allocation.py`

Ele executa `cProfile` diretamente na rotina parcial.

## Uso básico

### 1. Profiling seguro sem gravar no banco

```bash
python profile_autonomous_allocation.py --semester 5
```

Por padrão o script roda com `dry_run=True`.

### 2. Profiling do comportamento real com commits

```bash
python profile_autonomous_allocation.py --semester 5 --no-dry-run
```

Use isso apenas em cópia do banco ou ambiente controlado.

### 3. Salvar `.prof` para análise visual

```bash
python profile_autonomous_allocation.py --semester 5 --dump data/reports/allocation.prof
```

Depois você pode abrir com ferramentas como:

```bash
snakeviz data/reports/allocation.prof
```

### 4. Ordenar pelo tempo exclusivo

```bash
python profile_autonomous_allocation.py --semester 5 --sort tottime --limit 80
```

## Como interpretar o resultado

O script imprime duas saídas.

### 1. Resumo funcional

Inclui:

- `execution_time`
- `allocations_completed`
- `block_groups_processed`
- `performance`

O campo `performance` mostra o tempo agregado por etapa, por exemplo:

- `load_unallocated_demands`
- `phase0_hybrid_detection`
- `phase1_hard_rules`
- `prepare_continuity_profiles_phase1_5`
- `phase1_5_continuity`
- `prepare_continuity_profiles_partial`
- `phase_partial`
- `total_execution_time`

### 2. Top funções do `cProfile`

Priorize olhar:

- `cumtime`: onde o sistema gasta tempo total incluindo chamadas filhas
- `tottime`: onde a própria função gasta CPU diretamente

## Hipóteses de otimização

Se o profiling confirmar os suspeitos acima, as otimizações mais promissoras são:

### 1. Cache por execução

Criar caches em memória para a duração de uma execução de alocação:

- regras por `codigo_disciplina`
- professor por nome
- demanda por id
- ocupação por sala/semestre
- blocos habilitados por sala

### 2. Substituir consultas pontuais por batch

Especialmente para:

- `get_by_demanda()` em lote
- `find_rules_by_disciplina()` em lote
- conflitos por bloco em lote
- ocupação de salas em lote

### 3. Evitar recomputar perfis de continuidade completos duas vezes

Hoje a rotina monta perfis antes da fase 1.5 e novamente antes da fase parcial.
Se o profiling mostrar custo alto aqui, vale recalcular apenas para demandas afetadas.

### 4. Evitar `check_conflict()` em loops profundos

Trocar por verificações batch usando estruturas pré-carregadas na memória ou queries agregadas.

### 5. Paralelização seletiva

Paralelização só vale a pena depois de reduzir N+1.

Os melhores candidatos seriam partes puramente de leitura e scoring, por exemplo:

- construção de contextos por demanda
- score de salas por bloco-grupo

Não paralelize a fase de commit/alocação sem redesenhar controle de conflitos e transação.

## Recomendação prática

Antes de tentar paralelizar, faça nesta ordem:

1. rodar o script com `--sort cumtime`
2. identificar top 20 funções por tempo acumulado
3. confirmar se o gargalo é banco, Python puro, ou ambos
4. eliminar N+1 com batch/cache
5. só depois reavaliar paralelização