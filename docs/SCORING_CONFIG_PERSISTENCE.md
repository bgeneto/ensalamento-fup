## Persistência de Configurações no Docker

### Diagnóstico

O arquivo `data/scoring_config.json` era usado como configuração editável do usuário e também estava versionado no Git.

Isso criava dois comportamentos arriscados:

1. Um update do código no host podia sobrescrever o arquivo antes do `docker compose up`.
2. O container novo podia subir com a versão do repositório em vez do override esperado do usuário.

### Ajuste aplicado

- `src/config/scoring_config.py` agora separa:
  - `data/scoring_defaults.json`: defaults versionados do sistema
  - `data/runtime/scoring_config.json`: override persistente do usuário
- O loader prefere `data/runtime/scoring_config.json`.
- Se o override ainda não existir, ele faz bootstrap a partir do arquivo legado ou dos defaults.
- A tela de configuração salva sempre no caminho de runtime.
- `data/runtime/` foi adicionado ao `.gitignore`.

### Efeito no deploy

Com `compose.yaml` montando `./data:/app/data`, o arquivo `data/runtime/scoring_config.json` passa a sobreviver a:

- `docker build`
- recriação do container
- `docker compose up`

Mesmo que o repositório seja atualizado, os defaults continuam versionados e o override do usuário permanece separado.

### Observação

Outras configurações merecem atenção semelhante se forem editáveis em produção e estiverem dentro da árvore versionada. Hoje o caso confirmado é a configuração de pontuação.
