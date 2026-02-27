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
docker compose up -d --build
```

- App: `http://localhost:8504`
- Docs: `http://localhost:8000`

## Banco de Dados (SQLite)

Este projeto usa SQLite, configurado por `DATABASE_URL` no `.env`.

Exemplo atual recomendado:

```env
DATABASE_URL=sqlite:///./data/ensalamento.db
```

Com isso, no container o arquivo fica em `/app/data/ensalamento.db`, persistido no host em `./data/ensalamento.db` (por causa do volume `./data:/app/data`).

## Inicialização do Banco (Tabelas/Migrations/Seed)

Depois de subir os containers, execute:

1. Criar tabelas + aplicar migrations SQL:

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

Se alterar credenciais localmente e estiver usando Docker, faça rebuild/restart para garantir que o container use a versão atual:

```bash
docker compose up -d --build
```

Para conferir o arquivo efetivo dentro do container:

```bash
docker compose exec ensalamento sh -lc 'sed -n "1,120p" /app/.streamlit/secrets.yaml'
```

## Manual Online (botão "Manual Online")

O botão usa:

- `DOCS_URL` (se definido), ou
- fallback para `${BASE_URL}/docs/`

Se estiver apontando para `localhost`, ajuste `DOCS_URL` ou `BASE_URL` no `.env`/compose conforme seu ambiente.

## Solução de Problemas

### 1) `Usuário ou senha inválidos`

- Verifique `.streamlit/secrets.yaml` (usuário/senha).
- Confirme que o container está com esse arquivo atualizado (`docker compose up -d --build`).
- Confira conteúdo real no container com o comando `sed` acima.

### 2) `sqlalchemy.exc.OperationalError: no such table`

Causa comum: banco novo sem init/migration.

Execute:

```bash
docker compose exec ensalamento python init_db.py --init --migrate
docker compose exec ensalamento python init_db.py --seed
```

### 3) Banco não persistindo

- Garanta `DATABASE_URL=sqlite:///./data/ensalamento.db`
- Garanta volume `./data:/app/data`

## Estrutura Útil

- App principal: `0_🔓_Login.py`
- Config app: `src/config/settings.py`
- DB init/migrations: `init_db.py` e `src/db/migrations.py`
- Docker: `compose.yaml`, `Dockerfile`
- Credenciais login: `.streamlit/secrets.yaml`
