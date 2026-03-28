# Proposta de Refatoração: Configuração de Scoring no Banco

## Objetivo

Substituir o modelo atual baseado em arquivos:

- `data/scoring_defaults.json`
- `data/scoring_config.json`
- `data/runtime/scoring_config.json`

por um modelo mais robusto, versionado e auditável, adequado para evolução do algoritmo sem risco de configuração legada persistir de forma incorreta após updates.

---

## Diagnóstico do Modelo Atual

Hoje o projeto possui:

- defaults em arquivo JSON
- override do usuário em outro JSON
- merge em runtime em [src/config/scoring_config.py](/home/bgeneto/github/ensalamento-fup/src/config/scoring_config.py)
- escrita da aba de configuração diretamente em arquivo em [pages/components/config/tab_scoring.py](/home/bgeneto/github/ensalamento-fup/pages/components/config/tab_scoring.py)

### Problemas reais do desenho atual

1. O override do usuário tende a virar um snapshot completo, não apenas um diff.
2. Se defaults mudarem em versões futuras, o snapshot legado pode “congelar” valores antigos sem o administrador perceber.
3. Renomear ou remover parâmetros exige lógica manual e frágil de compatibilidade.
4. Não há trilha de auditoria adequada: quem mudou, quando mudou, por quê, e qual era o valor anterior.
5. A UI tem conhecimento duplicado dos parâmetros, rótulos e mapeamentos.
6. O contrato da configuração está implícito em vários lugares ao mesmo tempo.

### Conclusão

Somente “guardar no SQLite” não resolve por si só.

O que resolve é:

- defaults canônicos em código
- overrides persistidos no banco
- schema versionado
- migrações explícitas
- auditoria/histórico
- UI dirigida por um registro central de parâmetros

---

## Decisão Arquitetural Recomendada

### Padrão recomendado

Usar o banco apenas para guardar **overrides do usuário**, não o snapshot completo da configuração.

### Fonte de verdade final

1. **Defaults no código**
   - tipados
   - versionados
   - revisados junto com o algoritmo

2. **Overrides no banco**
   - apenas campos divergentes do default
   - com `schema_version`
   - com histórico

3. **Config efetiva em runtime**
   - `defaults do código + overrides do banco`

Esse desenho evita que valores default antigos fiquem “presos” só porque em algum momento foram copiados para um arquivo persistido.

---

## Proposta de Estrutura

### 1. Registro central de parâmetros no código

Criar um módulo novo, por exemplo:

- `src/config/scoring_registry.py`

Responsabilidade:

- declarar todos os parâmetros suportados
- valor default
- tipo
- faixa permitida
- label
- descrição
- categoria
- ordem de exibição
- versionamento de schema

Exemplo conceitual:

```python
@dataclass(frozen=True)
class ScoringFieldSpec:
    key: str
    section: str
    label: str
    description: str
    value_type: type
    default: int | bool
    min_value: int | None = None
    max_value: int | None = None
    order: int = 0

CURRENT_SCORING_SCHEMA_VERSION = 1

SCORING_FIELD_SPECS = [
    ScoringFieldSpec(
        key="weights.CAPACITY_ADEQUATE",
        section="Base",
        label="Capacidade Adequada",
        description="Pontos quando sala tem capacidade >= vagas da disciplina",
        value_type=int,
        default=3,
        min_value=0,
        max_value=100,
        order=10,
    ),
    ...
]
```

### Benefícios

- elimina duplicação entre backend e UI
- facilita validação
- facilita comparação entre versões
- permite gerar UI automaticamente

---

## Schema das Tabelas

## Opção recomendada para este repositório

Como o projeto já pode ganhar outras configurações globais no futuro, recomendo usar uma estrutura genérica de configuração de aplicação, não algo exclusivo para scoring.

### Tabela principal: `app_configurations`

```sql
CREATE TABLE IF NOT EXISTS app_configurations (
    id INTEGER PRIMARY KEY,
    config_key TEXT NOT NULL UNIQUE,
    schema_version INTEGER NOT NULL,
    overrides_json TEXT NOT NULL DEFAULT '{}',
    defaults_revision TEXT,
    updated_by TEXT,
    change_reason TEXT,
    source TEXT NOT NULL DEFAULT 'ui',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (updated_by) REFERENCES usuarios (username)
);
```

### Uso no caso de scoring

- `config_key = 'scoring'`
- `schema_version = versão estrutural da configuração`
- `overrides_json = apenas campos diferentes do default`
- `defaults_revision = revisão do conjunto de defaults da release`

### Tabela de histórico: `app_configuration_history`

```sql
CREATE TABLE IF NOT EXISTS app_configuration_history (
    id INTEGER PRIMARY KEY,
    config_key TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    overrides_json TEXT NOT NULL DEFAULT '{}',
    effective_config_json TEXT NOT NULL DEFAULT '{}',
    changed_by TEXT,
    change_reason TEXT,
    source TEXT NOT NULL DEFAULT 'ui',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (changed_by) REFERENCES usuarios (username)
);
```

### Por que manter `effective_config_json` no histórico?

Porque facilita:

- auditoria
- debugging
- rollback manual
- comparação entre estados sem precisar reexecutar merge com defaults antigos

### Por que não guardar o effective config na tabela principal?

Porque ele é derivado.
Na linha principal, o que interessa é o override persistido.

---

## ORM / Repositório / Serviço

### Novos arquivos sugeridos

- `src/models/app_configuration.py`
- `src/schemas/app_configuration.py`
- `src/repositories/app_configuration.py`
- `src/services/scoring_configuration_service.py`
- `src/config/scoring_registry.py`

### Responsabilidades

#### `AppConfiguration`

- persistir a configuração ativa

#### `AppConfigurationHistory`

- registrar snapshots auditáveis

#### `AppConfigurationRepository`

- ler por `config_key`
- salvar override
- gravar histórico

#### `ScoringConfigurationService`

- carregar config efetiva
- aplicar migrações de schema
- calcular diff entre default e override
- validar com o registro central
- expor estrutura para a UI

---

## Estratégia de Migração

## Princípio

As migrações devem ser tratadas em dois níveis:

1. **Migração de banco**
   - criar tabelas
   - índices
   - constraints

2. **Migração de conteúdo de configuração**
   - transformar dados entre versões de schema
   - renomear/remover chaves
   - corrigir tipos

### 1. Migração SQL

Como o projeto já usa arquivos em `src/db/migrations/`, a proposta é adicionar algo como:

- `src/db/migrations/V2026_03_28_03_add_app_configurations.sql`

Conteúdo:

```sql
CREATE TABLE IF NOT EXISTS app_configurations (...);
CREATE TABLE IF NOT EXISTS app_configuration_history (...);
CREATE INDEX IF NOT EXISTS ix_app_configuration_history_key_created_at
ON app_configuration_history (config_key, created_at DESC);
```

### 2. Migração de dados

Essa parte deve ser feita em Python, não em SQL, porque envolve:

- leitura de JSON legado
- diff contra defaults
- upgrade de schema
- descarte controlado de chaves desconhecidas

### Local recomendado

Criar uma função chamada durante o bootstrap após `run_sql_migrations()` em [src/db/bootstrap.py](/home/bgeneto/github/ensalamento-fup/src/db/bootstrap.py):

- `ensure_scoring_config_migrated()`

Ela deve:

1. verificar se já existe `config_key='scoring'` no banco
2. se não existir, tentar importar do JSON legado
3. se existir, apenas validar/migrar schema em memória quando carregar

---

## Regras de Evolução para Updates

## Adição de parâmetro

### Com o novo desenho

- adicionar o novo campo no registry com default
- não precisa gravar nada no banco
- usuários passam a receber esse valor automaticamente
- se alterarem na UI, só então nasce override

### Resultado

Sem risco de usuário ficar preso a um snapshot antigo só porque o default mudou.

## Renomeação de parâmetro

### Exemplo

Antes:

- `weights.PREFERRED_CHARACTERISTIC`

Depois:

- `weights.PREFERRED_FEATURE`

### Estratégia

Incrementar `schema_version` e adicionar migrador:

```python
def migrate_v1_to_v2(data: dict) -> dict:
    if "weights.PREFERRED_CHARACTERISTIC" in data:
        data["weights.PREFERRED_FEATURE"] = data.pop("weights.PREFERRED_CHARACTERISTIC")
    return data
```

## Remoção de parâmetro

### Estratégia

- remover do registry
- migrador elimina a chave do override
- registrar em log/histórico que a chave foi descartada

## Mudança de semântica

Esse é o caso mais importante.

Exemplo:

- antes: `HISTORICAL_FREQUENCY_MAX_CAP` significava “máximo de pontos”
- depois: passa a significar “máximo de ocorrências”

### Estratégia

- subir `schema_version`
- criar migrador explícito
- se não houver conversão segura, resetar para default novo
- registrar no histórico que o valor foi normalizado

---

## Estratégia de Merge

### Regra recomendada

A linha no banco guarda apenas o diff:

```python
effective_config = deep_merge(default_config, overrides_json)
```

### Regra crítica

No momento de salvar, o sistema deve recalcular o override como:

```python
overrides = diff(current_effective_config_edited, current_defaults)
```

### Nunca salvar

- snapshot completo da config

### Sempre salvar

- apenas valores que diferem do default atual

Esse é o ponto que mais protege o sistema contra drift entre versões.

---

## Estratégia de Validação

### Validação deve ocorrer em três camadas

1. **Registry**
   - tipo
   - intervalo permitido
   - obrigatoriedade

2. **Schema efetivo**
   - config final resultante do merge
   - validação Pydantic/dataclass

3. **Regras de coerência**
   - ex.: `HISTORICAL_FREQUENCY_MAX_CAP >= HISTORICAL_FREQUENCY_PER_ALLOCATION`

### Política em caso de erro

- se override inválido:
  - logar erro
  - ignorar apenas a chave inválida, não a configuração inteira
  - manter defaults nas chaves problemáticas
- se schema inteiro estiver inconsistente:
  - usar defaults
  - registrar evento de fallback

---

## Como adaptar a aba de configurações

## Problema atual da UI

A aba em [pages/components/config/tab_scoring.py](/home/bgeneto/github/ensalamento-fup/pages/components/config/tab_scoring.py):

- tem lista fixa de poucos campos
- mantém mapeamento manual de labels para keys
- sabe demais sobre a estrutura
- salva diretamente em arquivo

## Novo desenho da UI

### A aba deve passar a depender do serviço

Em vez de importar `SCORING_WEIGHTS` diretamente, a UI deve consumir algo como:

```python
service = ScoringConfigurationService()
view_model = service.get_scoring_config_for_ui()
```

### O `view_model` da UI deve trazer

- chave técnica
- label
- categoria
- descrição
- valor efetivo
- valor default
- origem
  - `default`
  - `override`
- tipo do campo
- min/max
- ordem

### Benefícios

- UI renderiza automaticamente todos os campos registrados
- novos parâmetros aparecem na interface sem duplicação manual
- categorias e descrições vêm da mesma fonte de verdade

## Funcionalidades recomendadas na nova aba

1. Mostrar valor efetivo atual
2. Mostrar valor default de referência
3. Mostrar se o valor veio de default ou override
4. Permitir “Resetar este campo”
5. Permitir “Resetar categoria”
6. Permitir “Resetar tudo para defaults”
7. Mostrar `schema_version`
8. Mostrar último usuário e data de atualização
9. Mostrar diff antes de salvar

## Fluxo de salvar

1. UI edita valores
2. serviço valida
3. serviço gera diff contra defaults
4. serviço grava `app_configurations`
5. serviço grava `app_configuration_history`
6. serviço recarrega cache/configuração runtime

---

## Plano de transição dos JSONs atuais

## Objetivo

Migrar sem quebrar o ambiente atual e sem perder personalizações legítimas.

## Etapa 1: criar a infraestrutura nova

Adicionar:

- tabelas novas
- models/schemas/repository/service
- loader novo com suporte a banco

Nessa etapa, o sistema ainda pode continuar lendo JSON como fallback.

## Etapa 2: importar a configuração legada

### Fonte de importação

Usar a mesma prioridade que o código atual usa:

1. `data/runtime/scoring_config.json`
2. `data/scoring_config.json`
3. `data/scoring_defaults.json`

### Regra de importação correta

Não importar o arquivo inteiro como override.

### Algoritmo recomendado

1. carregar defaults atuais
2. carregar JSON legado ativo
3. migrar o conteúdo legado para o schema atual, se necessário
4. comparar cada campo conhecido contra o default atual
5. persistir no banco apenas os campos diferentes
6. ignorar `_metadata`
7. logar chaves desconhecidas
8. salvar snapshot efetivo no histórico

### Por que isso é importante?

Porque o JSON legado costuma ser uma cópia quase completa dos defaults.
Se ele for importado inteiro, os defaults futuros deixam de surtir efeito.

## Etapa 3: trocar a escrita da UI para o banco

Modificar [pages/components/config/tab_scoring.py](/home/bgeneto/github/ensalamento-fup/pages/components/config/tab_scoring.py) para:

- parar de escrever JSON
- salvar via `ScoringConfigurationService`

## Etapa 4: manter fallback só para leitura

Durante uma janela de transição curta:

- leitura prioritária do banco
- fallback para JSON apenas se não existir linha no banco

## Etapa 5: desativar JSON legado

Depois que a migração estiver estável:

- remover leitura de `data/scoring_config.json`
- remover leitura de `data/runtime/scoring_config.json`
- manter `data/scoring_defaults.json` apenas se quiser compatibilidade temporária

## Etapa 6: remover defaults em arquivo

Etapa final recomendada:

- substituir `data/scoring_defaults.json` por defaults em código no registry

Resultado:

- sem arquivo mutável de configuração
- sem risco de drift silencioso

---

## Estratégia de rollout em fases

## Fase 1

Infraestrutura sem mudar comportamento externo.

### Entregas

- tabelas novas
- registry central
- serviço de leitura do banco
- importer de JSON legado
- fallback para JSON mantido

## Fase 2

UI passa a salvar no banco.

### Entregas

- nova versão da aba de scoring
- histórico de alterações
- reset para default

## Fase 3

Descontinuação do legado.

### Entregas

- remover escrita em JSON
- warning caso JSON legado ainda exista
- comando/manual de limpeza opcional

## Fase 4

Limpeza final.

### Entregas

- remover loader legado
- remover defaults em arquivo
- documentação final

---

## Arquivos do repositório que devem mudar

## Novos

- `src/config/scoring_registry.py`
- `src/models/app_configuration.py`
- `src/schemas/app_configuration.py`
- `src/repositories/app_configuration.py`
- `src/services/scoring_configuration_service.py`
- `src/db/migrations/V2026_03_28_03_add_app_configurations.sql`
- `tests/test_scoring_configuration_service.py`
- `tests/test_scoring_config_migration.py`

## Alterados

- [src/config/scoring_config.py](/home/bgeneto/github/ensalamento-fup/src/config/scoring_config.py)
- [src/db/bootstrap.py](/home/bgeneto/github/ensalamento-fup/src/db/bootstrap.py)
- [pages/components/config/tab_scoring.py](/home/bgeneto/github/ensalamento-fup/pages/components/config/tab_scoring.py)
- `src/config/database.py`
  - para importar o novo módulo de models, se necessário

---

## Recomendação de comportamento do loader

## API sugerida

```python
service = ScoringConfigurationService()
effective = service.get_effective_config()
weights = effective.weights
rules = effective.rules
```

### Métodos importantes

- `get_effective_config()`
- `get_config_for_ui()`
- `save_overrides(edited_values, username, reason)`
- `reset_field(field_key, username)`
- `reset_all(username)`
- `import_legacy_json_if_needed()`
- `migrate_config_to_current_schema(config, from_version)`

---

## Recomendação sobre perfis múltiplos

## Para agora

Não recomendo múltiplos perfis de scoring nesta primeira refatoração.

### Motivo

O uso atual parece ser:

- uma configuração global do algoritmo

Adicionar perfis agora aumentaria:

- complexidade de UI
- complexidade de seleção
- risco operacional

### Mais adequado

Começar com:

- um único registro `config_key='scoring'`

Se no futuro houver necessidade real, a estrutura proposta já permite evoluir.

---

## Resumo Executivo

### O que eu recomendo para este projeto

1. Tirar a configuração viva de scoring dos JSONs.
2. Manter defaults no código, via registry central.
3. Persistir no SQLite apenas overrides.
4. Versionar o schema da configuração.
5. Criar migradores explícitos para renomear/remover/mudar semântica de parâmetros.
6. Adaptar a aba de configurações para ser dirigida pelo registry e salvar no banco.
7. Importar os JSONs legados como diff, nunca como snapshot completo.
8. Manter histórico/auditoria no banco.

### Resposta curta à sua pergunta original

Sim, faz sentido usar o SQLite.

Mas não basta “mover o JSON para o banco”.

O modelo profissional para este caso é:

- **defaults em código**
- **overrides no banco**
- **schema versionado**
- **migrações explícitas**
- **histórico**

Esse é o desenho que melhor protege o sistema exatamente contra os casos que você apontou: adição, alteração e remoção de parâmetros ao longo das atualizações.
