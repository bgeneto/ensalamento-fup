# Ensalamento: Alocacoes Manuais e Autonomas

Este documento descreve o comportamento introduzido para diferenciar a origem
das alocacoes e controlar o desfazimento do ensalamento sem apagar demandas.

## Objetivo

Permitir desfazer o ensalamento de um semestre preservando, opcionalmente, as
alocacoes realizadas manualmente.

## Campo `origem_alocacao`

Cada registro em `alocacoes_semestrais` passa a armazenar `origem_alocacao`,
com os seguintes valores:

- `manual`: alocacao criada pelo fluxo manual da pagina de ensalamento
- `autonoma`: alocacao criada pelo motor de alocacao autonoma

## Regra de migracao

Ao aplicar a migration `V2026_03_28_01_add_origem_alocacao_to_alocacoes.sql`,
o campo `origem_alocacao` e criado com default `autonoma`.

Regras explicitas:

- novas alocacoes manuais sao gravadas com `origem_alocacao = 'manual'`
- novas alocacoes autonomas sao gravadas com `origem_alocacao = 'autonoma'`
- alocacoes antigas, que nao tinham essa informacao, passam a ser tratadas como
  `origem_alocacao = 'autonoma'`

Essa ultima regra foi adotada de forma intencional para manter comportamento
deterministico em bases ja existentes.

## Comportamento na tela de confirmacao

Na acao `Desfazer Ensalamento do Semestre`, a confirmacao agora oferece o
checkbox:

- `Manter alocacoes manuais existentes`

Quando o checkbox estiver marcado:

- o sistema remove apenas alocacoes com `origem_alocacao != 'manual'`
- alocacoes manuais existentes no semestre sao preservadas

Quando o checkbox estiver desmarcado:

- o sistema remove todas as alocacoes do semestre

O modal tambem informa:

- total de alocacoes do semestre
- quantidade de alocacoes autonomas
- quantidade de alocacoes manuais
- quantidade prevista para remocao

## Aplicacao da migration em banco existente

Para aplicar a mudanca sem apagar o banco:

```bash
docker compose exec ensalamento python init_db.py --init --migrate
```

Observacao: este projeto nao usa Alembic. As migrations SQL sao aplicadas por
`init_db.py` e `src/db/migrations.py`.
