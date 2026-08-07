# Sistema de Ensalamento FUP/UnB

Sistema web para gestão de ensalamento (alocação de salas) da FUP/UnB, construído com Streamlit + SQLAlchemy + SQLite.

## Requisitos

- Docker
- Docker Compose
- (Neste projeto) rede Docker externa `proxy`

Se a rede `proxy` ainda não existir:

```bash
docker network create proxy
```

## Configuração Inicial

1. Copie variáveis de ambiente:

```bash
cp .env.example .env
```

2. Copie credenciais de login do Streamlit Authenticator:

```bash
cp .streamlit/secrets.example.yaml .streamlit/secrets.yaml
```

3. Ajuste valores no `.env` e `.streamlit/secrets.yaml` conforme necessário.

## Subir com Docker

```bash
docker compose build
docker compose up -d
```

- App: `http://localhost:8504`
- Docs: `http://localhost:8000`

Também é possível usar `docker compose up -d --build`. Em rebuilds normais, o
BuildKit reutiliza as camadas de dependências e os caches de download. Evite
`--no-cache` e `--pull` no uso cotidiano; essas opções existem justamente para
forçar downloads e reconstrução completa.

## Builds reproduzíveis e cache

- As imagens Python e Nginx estão fixadas por versão e digest no `Dockerfile`.
- O índice dos pacotes nativos usados para gerar o PDF está fixado por data em
  um snapshot imutável do Debian.
- Dependências diretas ficam em `requirements.in`, `requirements-docs.in` e
  `requirements-dev.in`.
- Os arquivos `.txt` correspondentes fixam também todas as dependências
  transitivas e seus hashes.
- Dependências da aplicação e da documentação estão em estágios separados.
  Alterar código Python ou Markdown não reinstala pacotes.
- Downloads de `pip` e `apt` usam cache mounts do BuildKit, sem aumentar a
  imagem final.
- Ferramentas de teste, formatação e documentação não são instaladas na imagem
  da aplicação.

Para atualizar locks intencionalmente, use `uv 0.9.3`, altere as versões diretas
nos arquivos `.in` e regenere os arquivos `.txt`:

```bash
uv pip compile requirements.in --python-version 3.13 --python-platform x86_64-unknown-linux-gnu --generate-hashes --output-file requirements.txt
uv pip compile requirements-docs.in --python-version 3.13 --python-platform x86_64-unknown-linux-gnu --generate-hashes --output-file requirements-docs.txt
uv pip compile requirements-dev.in --python-version 3.13 --python-platform x86_64-unknown-linux-gnu --generate-hashes --output-file requirements-dev.txt
```

O build instala os locks com `--require-hashes`, portanto falha se uma versão ou
artefato não corresponder ao arquivo revisado. Pins devem ser atualizados
periodicamente em uma mudança revisada, junto com o digest das imagens e a data
do snapshot Debian, para incorporar correções de segurança sem perder
reprodutibilidade.

### Cloudflare e módulos JavaScript

O frontend do Streamlit usa módulos ES carregados dinamicamente. O Rocket Loader
do Cloudflare pode reescrever esses scripts e causar erros `Failed to fetch
dynamically imported module`. O `Dockerfile` adiciona o opt-out documentado
`data-cfasync="false"` aos scripts de inicialização como proteção, mas a
configuração recomendada é uma Configuration Rule no Cloudflare para o hostname
`ensalamento.sistema.pro.br` com **Rocket Loader = Off**. Após alterar essa
configuração ou publicar uma nova imagem, limpe o cache HTML do hostname e faça
uma recarga completa no navegador.

## Banco de Dados (SQLite)

Este projeto usa SQLite, configurado por `DATABASE_URL` no `.env`.

Exemplo atual recomendado:

```env
DATABASE_URL=sqlite:///./data/ensalamento.db
```

Com isso, no container o arquivo fica em `/app/data/ensalamento.db`, persistido
no host em `./data/ensalamento.db`. Esse também é o caminho padrão seguro quando
`DATABASE_URL` não é informado.

O diretório `./data` inteiro é montado em `/app/data`. Assim, também persistem:

- configurações da aplicação armazenadas no SQLite, incluindo campos JSON;
- arquivos auxiliares em `data/runtime`, inclusive configurações JSON legadas;
- relatórios gerados em `data/reports`;
- logs em `data/logs`.

Rebuilds e substituições do container não apagam esses arquivos. A configuração
e as credenciais Streamlit ficam no diretório host `./.streamlit`, montado como
somente leitura em `/app/.streamlit`; elas também não entram na imagem Docker.
O `.env` permanece no host e seus valores são injetados pelo Compose.

Antes de uma manutenção importante, pare o app e faça backup de `./data`, do
`.env` e de `.streamlit/secrets.yaml`. Não apague `./data` nem mude
`DATABASE_URL` para um caminho fora de `/app/data` se quiser manter a
persistência.

## Inicialização do Banco (Tabelas/Migrations/Seed)

Em Docker, o container da aplicação agora executa `python init_db.py --init --migrate`
automaticamente no startup antes de subir o Streamlit.

Fora do Docker, o app Streamlit também passou a executar `init + migrate` no boot do
processo. Isso cobre bancos novos e migrations pendentes sem exigir comando manual
antes de abrir o sistema.

Observação: este projeto não usa Alembic. As migrations são SQLs aplicadas por
`init_db.py` + `src/db/migrations.py`.

Se precisar desabilitar esse comportamento em algum cenário específico, use:

```bash
SKIP_DB_MIGRATIONS=1
```

Depois de subir os containers, execute:

1. Criar tabelas + aplicar migrations SQL manualmente quando quiser reparar um banco já existente:

```bash
docker compose exec ensalamento python init_db.py --init --migrate
```

2. Popular dados iniciais (seed):

```bash
docker compose exec ensalamento python init_db.py --seed
```

Opcional: reset completo (apaga tudo e recria):

```bash
docker compose exec ensalamento python init_db.py --all
```

## Login e Senhas

A autenticação de login **não vem do banco SQLite**. Ela vem do arquivo:

`/app/.streamlit/secrets.yaml` (no projeto: `.streamlit/secrets.yaml`)

Estrutura:

```yaml
credentials:
  usernames:
    admin:
      password: admin123
```

Como `.streamlit` é um bind mount, alterações de credenciais não exigem rebuild.
Reinicie apenas a aplicação:

```bash
docker compose restart ensalamento
```

Para verificar sem imprimir credenciais se o arquivo está montado e legível:

```bash
docker compose exec ensalamento test -r /app/.streamlit/secrets.yaml
```

## Manual Online (botão "Manual Online")

O botão usa:

- `DOCS_URL` (se definido), ou
- fallback para `${BASE_URL}/docs/`

Se estiver apontando para `localhost`, ajuste `DOCS_URL` ou `BASE_URL` no `.env`/compose conforme seu ambiente.

## Solução de Problemas

### 1) `Usuário ou senha inválidos`

- Verifique `.streamlit/secrets.yaml` (usuário/senha).
- Reinicie a aplicação após alterar o arquivo (`docker compose restart ensalamento`).
- Confirme que o arquivo está legível no container com o comando `test` acima.

### 2) `sqlalchemy.exc.OperationalError: no such table`

Causa comum: banco novo sem init/migration.

Observação: no fluxo normal isso agora roda automaticamente no boot do app e no
startup do container. Os comandos abaixo continuam úteis para reparo manual.

Execute:

```bash
docker compose exec ensalamento python init_db.py --init --migrate
docker compose exec ensalamento python init_db.py --seed
```

### 3) Banco não persistindo

- Garanta `DATABASE_URL=sqlite:///./data/ensalamento.db`
- Garanta o bind mount `./data` em `/app/data` definido em `compose.yaml`.
- Confirme que o usuário configurado por `HOST_UID` pode escrever em `./data`.

## Estrutura Útil

- App principal: `0_🔓_Login.py`
- Config app: `src/config/settings.py`
- DB init/migrations: `init_db.py` e `src/db/migrations.py`
- Comportamento de alocações manuais/autônomas: `docs/ENSALAMENTO_ALOCACOES_MANUAIS_E_AUTONOMAS.md`
- Docker: `compose.yaml`, `Dockerfile`
- Credenciais login: `.streamlit/secrets.yaml`
