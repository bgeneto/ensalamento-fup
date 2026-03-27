# Demanda Sync Reconciliation Plan

Plano técnico incremental para tornar a API do Sistema de Oferta a fonte de verdade do dado importado, sem sobrescrever automaticamente ajustes locais já feitos no sistema.

Este plano foi desenhado para o estado atual do repositório, especialmente:

- `pages/6_🧭_Demanda.py`
- `src/services/semester_service.py`
- `src/repositories/disciplina.py`
- `src/models/academic.py`
- `src/schemas/academic.py`
- `src/db/migrations.py`

---

## Objetivo

Resolver o conflito entre dois requisitos operacionais legítimos:

1. a API deve ser a fonte de verdade para ofertas importadas
2. edições e criações locais não podem ser perdidas em uma nova sincronização

O plano também cobre remoções da API, preservação de alocações existentes e rollout seguro.

---

## Diagnóstico do estado atual

Hoje a sincronização em `src/services/semester_service.py:sync_semester_from_api()` faz apenas:

- leitura da API
- filtro por cursos ignorados
- criação de novas demandas quando `id_oferta_externo` ainda não existe no semestre
- criação idempotente de professores

Ela **não faz**:

- update de demandas já importadas
- reconciliação por campo
- marcação de ofertas removidas da API
- distinção explícita entre dado importado e override local

Isso significa que o comportamento atual é seguro contra overwrite, mas insuficiente para manter a API como fonte de verdade em mudanças posteriores.

---

## Estratégia recomendada para este repositório

### Recomendação principal

Para este código, a estratégia mais pragmática e incremental é:

- manter `Demanda` como a entidade efetiva consumida pela UI e pelo motor de alocação
- adicionar metadados de sincronização e snapshot importado à própria `Demanda`
- registrar overrides locais por campo
- mudar a sincronização para reconciliação, não mais criação cega

### Por que esta abordagem é a melhor aqui

Porque ela preserva os pontos fortes da arquitetura atual:

- repositórios e serviços já assumem `Demanda` como entidade central
- o motor de alocação e a UI já leem diretamente `Demanda`
- evita uma refatoração grande com tabela paralela ou view materializada logo de início

Em vez de criar já uma segunda entidade “snapshot + entidade efetiva”, o plano propõe um meio-termo robusto:

- `Demanda` continua sendo a linha de trabalho
- mas passa a carregar de forma explícita:
  - o último snapshot importado da API
  - os campos localmente sobrescritos
  - o status de sincronização com a API

---

## Modelo de dados proposto

## Extensões em `Demanda`

Adicionar os seguintes campos em `src/models/academic.py`:

### Metadados de origem

- `origem` — `api` ou `manual`
- `sync_status` — `active`, `changed_in_api`, `removed_in_api`, `manual`, `manual_linked`

### Metadados de sincronização

- `id_oferta_externo` — já existe e continua sendo a chave de reconciliação principal
- `api_payload_hash` — hash estável do conteúdo importado relevante
- `last_seen_in_api_at` — timestamp da última sync em que a oferta apareceu
- `last_synced_at` — timestamp da última reconciliação local
- `removed_from_api_at` — timestamp quando a oferta deixou de aparecer na API

### Snapshot importado

- `api_snapshot_json` — JSON com os campos importados normalizados

### Overrides locais

- `local_overrides_json` — JSON com apenas os campos que foram alterados localmente

### Controle operacional

- `preservar_local_em_remocao_api` — bool
- `revalidation_required` — bool para casos em que a API mudou após alocação existente

---

## Representação recomendada do snapshot

O `api_snapshot_json` deve conter apenas os campos de negócio relevantes para a demanda:

```json
{
  "codigo_curso": "CND",
  "codigo_disciplina": "FUP0011",
  "nome_disciplina": "CALCULO I",
  "turma_disciplina": "1",
  "vagas_disciplina": 40,
  "professores_disciplina": "João Silva, Maria Santos",
  "horario_sigaa_bruto": "24M12 6T34"
}
```

O `local_overrides_json` deve conter apenas os campos explicitamente sobrescritos localmente:

```json
{
  "vagas_disciplina": 35,
  "professores_disciplina": "João Silva"
}
```

---

## Regra de valor efetivo

Para cada campo relevante da demanda:

- se existir override local, o valor efetivo é o override
- senão, o valor efetivo vem do snapshot importado

Campos afetados:

- `codigo_curso`
- `codigo_disciplina`
- `nome_disciplina`
- `turma_disciplina`
- `vagas_disciplina`
- `professores_disciplina`
- `horario_sigaa_bruto`

### Decisão importante

No curto prazo, para reduzir impacto, a própria linha `Demanda` continuará armazenando os valores efetivos nas colunas já existentes.

Assim:

- `api_snapshot_json` guarda a base importada
- `local_overrides_json` guarda o delta local
- as colunas atuais continuam materializando o valor efetivo

Isso evita ter que reescrever toda a UI e todos os serviços de leitura imediatamente.

---

## Política de sincronização desejada

## Regras principais

1. A API manda no snapshot importado.
2. Overrides locais nunca são apagados automaticamente.
3. Demandas manuais nunca são removidas por ausência na API.
4. Demandas importadas removidas da API passam para estado `removed_in_api`, não são deletadas automaticamente.
5. Demandas com alocação existente nunca são deletadas automaticamente.

---

## Fluxo de reconciliação proposto

Para cada oferta retornada pela API:

1. normalizar campos da oferta
2. montar `snapshot_dict`
3. calcular `payload_hash`
4. procurar demanda por `semestre_id + id_oferta_externo`

### Caso A: oferta nova

Se não existe demanda com esse `id_oferta_externo`:

- criar `Demanda` com:
  - `origem='api'`
  - colunas efetivas preenchidas com o snapshot
  - `api_snapshot_json` com o snapshot
  - `local_overrides_json = {}`
  - `sync_status='active'`

### Caso B: oferta já conhecida e inalterada

Se o hash novo é igual ao `api_payload_hash` salvo:

- atualizar `last_seen_in_api_at`
- manter todo o resto como está

### Caso C: oferta já conhecida e alterada

Se o hash mudou:

- atualizar `api_snapshot_json`
- atualizar `api_payload_hash`
- recalcular os campos efetivos somente para os campos **sem override local**
- manter intactos os campos com override local
- marcar `sync_status='changed_in_api'` se houve divergência entre snapshot novo e valores efetivos

### Caso D: oferta removida da API

Ao final da sync, toda demanda `origem='api'` do semestre que não foi vista nesta execução deve ser marcada com:

- `sync_status='removed_in_api'`
- `removed_from_api_at=now()`

Sem deleção física automática.

---

## Tratamento de edições manuais

## Regra funcional

Toda edição local em demanda importada deve atualizar `local_overrides_json`.

Exemplo:

- usuário altera `vagas_disciplina`
- o sistema compara o novo valor com o valor do `api_snapshot_json`
- se são diferentes, grava override nesse campo
- se o usuário restaurar exatamente o valor vindo da API, remove o override desse campo

### Benefício

Isso permite que a API continue atualizando os campos não tocados localmente, sem perder as correções feitas no sistema.

---

## Tratamento de demandas manuais

Demandas criadas pela UI sem `id_oferta_externo` devem ter:

- `origem='manual'`
- `sync_status='manual'`
- `api_snapshot_json = null` ou `{}`
- `local_overrides_json = {}`

Essas demandas:

- não entram na lógica de remoção por ausência na API
- não são atualizadas pela sync

### Evolução futura opcional

Pode-se adicionar uma ação manual de “vincular demanda manual a oferta da API”, mas isso não deve entrar na primeira fase.

---

## Tratamento de alocações já salvas

## Regra operacional

Se uma demanda com alocação já existente sofrer mudança relevante na API, o sistema não deve apagar a alocação.

Deve apenas:

- manter a demanda
- atualizar snapshot importado
- marcar `revalidation_required=True`
- expor aviso na UI e, futuramente, no fluxo de ensalamento

### Mudanças relevantes para revalidação

- alteração de `horario_sigaa_bruto`
- alteração de `vagas_disciplina`
- remoção da oferta na API

### Mudanças não críticas

- ajuste de nome da disciplina
- ajuste de lista textual de professores

Essas podem atualizar snapshot sem necessariamente invalidar alocação.

---

## Mudanças por camada

## 1. Modelos

Arquivos:

- `src/models/academic.py`
- `src/schemas/academic.py`

### Alterações

- adicionar novos campos de sync/override em `Demanda`
- expor esses campos nos schemas de leitura e atualização quando fizer sentido
- manter compatibilidade com os campos atuais consumidos pela UI

---

## 2. Banco e migração

Arquivos:

- `src/db/migrations/`
- possivelmente `docs/schema.sql` depois do rollout

### Estratégia

Adicionar uma migration SQL incremental, não reset completo.

### Mudanças sugeridas

- `ALTER TABLE demandas ADD COLUMN origem TEXT DEFAULT 'api'`
- `ALTER TABLE demandas ADD COLUMN sync_status TEXT DEFAULT 'active'`
- `ALTER TABLE demandas ADD COLUMN api_payload_hash TEXT`
- `ALTER TABLE demandas ADD COLUMN api_snapshot_json TEXT`
- `ALTER TABLE demandas ADD COLUMN local_overrides_json TEXT`
- `ALTER TABLE demandas ADD COLUMN last_seen_in_api_at TEXT`
- `ALTER TABLE demandas ADD COLUMN last_synced_at TEXT`
- `ALTER TABLE demandas ADD COLUMN removed_from_api_at TEXT`
- `ALTER TABLE demandas ADD COLUMN preservar_local_em_remocao_api INTEGER DEFAULT 0`
- `ALTER TABLE demandas ADD COLUMN revalidation_required INTEGER DEFAULT 0`

### Backfill inicial

- `origem='manual'` para demandas sem `id_oferta_externo`
- `origem='api'` para demandas com `id_oferta_externo`
- `api_snapshot_json` inicial montado a partir do valor atual das colunas para as demandas `origem='api'`
- `local_overrides_json='{}'` inicialmente

---

## 3. Repositório de demanda

Arquivo:

- `src/repositories/disciplina.py`

### Novos métodos sugeridos

```python
def get_api_demands_by_semestre(self, semestre_id: int) -> list[DemandaRead]
def get_manual_demands_by_semestre(self, semestre_id: int) -> list[DemandaRead]
def mark_removed_from_api(self, demanda_id: int) -> None
def apply_api_snapshot(self, demanda_id: int, snapshot: dict, payload_hash: str) -> DemandaRead
def set_local_override(self, demanda_id: int, field_name: str, value: Any) -> DemandaRead
def clear_local_override(self, demanda_id: int, field_name: str) -> DemandaRead
def get_effective_field(self, demanda: Demanda, field_name: str) -> Any
```

### Função chave

Implementar a lógica central de reconciliação por campo no repositório ou em um serviço especializado, não na page.

---

## 4. Novo serviço de reconciliação

Arquivo novo sugerido:

- `src/services/demanda_sync_service.py`

### Responsabilidades

- normalizar payload da API
- calcular hash estável
- reconciliar snapshot importado com overrides locais
- marcar remoções
- devolver sumário rico da sync

### Métodos sugeridos

```python
def sync_semester(self, cod_semestre: str, cursos_ignorados: list[str] | None = None) -> SyncSummary
def reconcile_oferta(self, semestre_id: int, oferta_key: str, oferta_payload: dict) -> ReconcileResult
def mark_missing_offers_as_removed(self, semestre_id: int, seen_external_ids: set[str]) -> int
def apply_manual_edit(self, demanda_id: int, changed_fields: dict[str, Any]) -> DemandaRead
```

### Decisão de design

Mover a complexidade da função `sync_semester_from_api()` atual para esse novo serviço.

O método antigo pode virar apenas um adaptador fino para manter compatibilidade com a UI inicial.

---

## 5. Page de Demanda

Arquivo:

- `pages/6_🧭_Demanda.py`

### Alterações necessárias

#### Edição inline

Ao editar uma demanda importada via tabela:

- não chamar update cego apenas nas colunas efetivas
- chamar o serviço de edição manual, que:
  - compara contra `api_snapshot_json`
  - grava override quando houver diferença real
  - remove override quando o valor voltar ao original da API
  - atualiza as colunas efetivas

#### Formulário manual

Demandas criadas pelo formulário devem nascer com `origem='manual'`.

#### UI adicional recomendada

Adicionar colunas/indicadores visuais:

- Origem: API ou Manual
- Status de sync
- Possui overrides locais
- Removida na API
- Revalidação necessária

#### Ações novas recomendadas

- “Restaurar campo para valor da API”
- “Restaurar todos os overrides locais”
- “Arquivar demanda removida na API”

---

## 6. Serviço de sincronização atual

Arquivo:

- `src/services/semester_service.py`

### Mudança de papel

Hoje ele é um criador incremental. Ele deve virar uma camada de compatibilidade, delegando para `DemandaSyncService`.

### Resultado desejado

O sumário de sync deve passar a conter, além de `demandas` e `skipped`:

- `created`
- `updated_from_api`
- `unchanged`
- `removed_in_api`
- `manual_preserved`
- `revalidation_required`

---

## 7. Ensalamento e integridade operacional

Arquivos impactados depois:

- `src/services/manual_allocation_service.py`
- `src/services/optimized_autonomous_allocation_service.py`
- páginas de ensalamento/visualização

### Alterações futuras mínimas

- ignorar por padrão demandas `removed_in_api` apenas quando não tiverem alocação
- exibir aviso forte para `revalidation_required=True`
- bloquear ou exigir confirmação ao alocar demanda cuja API mudou após alocação existente

Isso pode entrar depois da primeira entrega da reconciliação.

---

## Plano incremental de execução

## Fase 1: metadados de sync sem mudar comportamento funcional

### Objetivo

Criar os campos e estruturas de suporte sem alterar ainda a lógica de sync.

### Arquivos

- `src/models/academic.py`
- `src/schemas/academic.py`
- migration SQL em `src/db/migrations/`

### Entrega

- novos campos existem
- backfill inicial concluído
- tudo continua funcionando como hoje

### Testes

- migration aplica sem perder dados
- demandas manuais vs importadas recebem `origem` correta

---

## Fase 2: snapshot importado + overrides locais

### Objetivo

Introduzir a distinção entre base importada e override local.

### Arquivos

- `src/repositories/disciplina.py`
- novo `src/services/demanda_sync_service.py`

### Entrega

- service consegue registrar snapshot
- service consegue aplicar e limpar overrides por campo

### Testes

- editar campo cria override
- voltar ao valor da API remove override
- demanda manual não entra em reconciliação API

---

## Fase 3: sync com update incremental por campo

### Objetivo

Trocar a sync de “create-only” para reconciliação.

### Arquivos

- `src/services/semester_service.py`
- `src/services/demanda_sync_service.py`

### Entrega

- cria novas ofertas
- atualiza snapshot de ofertas alteradas
- preserva overrides locais
- não sobrescreve edições manuais

### Testes

- oferta nova é criada
- oferta alterada na API atualiza apenas campos sem override
- oferta inalterada não muda nada

---

## Fase 4: marcação de remoções da API

### Objetivo

Detectar ofertas que sumiram da API sem deletar fisicamente a demanda.

### Arquivos

- `src/services/demanda_sync_service.py`
- `pages/6_🧭_Demanda.py`

### Entrega

- demandas ausentes passam para `removed_in_api`
- UI mostra esse estado
- nenhuma demanda com alocação é apagada automaticamente

### Testes

- demanda ausente é marcada como removida
- demanda manual não é afetada
- demanda com alocação segue visível e preservada

---

## Fase 5: edição manual consciente de override

### Objetivo

Fazer a page de Demanda gravar override corretamente, não apenas update bruto.

### Arquivos

- `pages/6_🧭_Demanda.py`
- `src/services/demanda_sync_service.py`

### Entrega

- edição inline cria override local
- restauração para valor da API limpa override
- formulário manual cria `origem='manual'`

### Testes

- edição via tabela preserva override após nova sync
- campo restaurado volta a seguir a API

---

## Fase 6: proteção operacional com alocações

### Objetivo

Evitar inconsistências silenciosas entre sync e ensalamento já salvo.

### Arquivos

- `src/services/demanda_sync_service.py`
- serviços de alocação
- páginas de ensalamento/visualização

### Entrega

- mudanças críticas da API marcam `revalidation_required`
- UI informa claramente o risco

### Testes

- alteração de horário após alocação marca revalidação
- remoção da API após alocação não apaga a demanda

---

## Estratégia de rollout

### Etapa 1

Deploy apenas com novos campos e backfill. Sem mudar UX.

### Etapa 2

Ativar nova sync reconciliadora sob feature flag simples, por exemplo:

- `USE_DEMANDA_RECONCILIATION_SYNC=true`

### Etapa 3

Ativar indicadores visuais na page de demanda.

### Etapa 4

Ativar marcação de `revalidation_required` no fluxo operacional.

---

## Testes recomendados

## Unit tests

- normalização de payload da API
- cálculo de hash estável
- merge entre snapshot e overrides
- limpeza de override ao voltar ao valor original

## Integration tests

- sync inicial cria demandas API
- sync posterior altera apenas campos não sobrescritos
- remoção da API marca demanda como removida
- demanda manual não é tocada
- demanda com alocação não é apagada

## Regressão

- importação atual continua funcionando para casos simples
- edição manual pela page não quebra
- leitura de demandas por semestre continua compatível

---

## Riscos e mitigação

### Risco 1: aumentar demais a complexidade em `Demanda`

Mitigação:

- concentrar a lógica de reconciliação em um serviço próprio
- manter a page o mais fina possível

### Risco 2: inconsistência entre snapshot e colunas efetivas

Mitigação:

- toda escrita passar por serviço único de reconciliação/override
- nunca editar diretamente `api_snapshot_json` e colunas efetivas em múltiplos lugares

### Risco 3: remoção automática causar perda operacional

Mitigação:

- usar somente remoção lógica na primeira versão
- nunca deletar fisicamente demandas com alocação ou override local

---

## Recomendação final

Para este repositório, a melhor estratégia incremental não é uma refatoração pesada com nova entidade efetiva logo de início.

A melhor estratégia é:

1. enriquecer `Demanda` com snapshot importado e overrides
2. mover a sync para reconciliação por campo
3. marcar remoções logicamente
4. preservar manualmente o que foi editado ou alocado

Isso entrega o comportamento desejado com risco menor, aproveitando a arquitetura existente e sem obrigar refatoração ampla da UI e do motor de alocação no primeiro passo.