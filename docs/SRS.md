# Especificação de Requisitos de Software (SRS)
# Sistema de Ensalamento FUP/UnB

**Versão:** 1.4 (Revisão para incluir Gestão de Professores e Preferências)
**Data:** 18 de outubro de 2025

---

## 1. Introdução

### 1.1. Propósito

Este documento especifica os requisitos de software (SRS) para o Sistema de Ensalamento da FUP/UnB. O propósito deste sistema é duplo:
1.  Automatizar e otimizar a alocação de salas de aula e laboratórios para as disciplinas semestrais (ensalamento).
2.  Gerenciar **reservas esporádicas (avulsas)** de salas, laboratórios e, principalmente, auditórios, feitas por usuários da comunidade.

### 1.2. Escopo do Produto

O sistema é uma aplicação web *interna* que irá:
* Gerenciar o inventário de todos os espaços físicos (salas, laboratórios, auditórios) e seus atributos.
* **Gerenciar uma base de dados de professores e suas preferências/restrições.**
* Importar, via API, a demanda de disciplinas semestrais do "Sistema de Oferta".
* Permitir a configuração de regras de alocação semestral (focadas em disciplinas).
* Executar um algoritmo para gerar uma proposta de ensalamento otimizada que respeite as regras de disciplina **e** as restrições de professores.
* Permitir ajustes manuais na proposta de ensalamento.
* **Permitir que usuários logados (Professores, Técnicos) façam reservas manuais/esporádicas de espaços.**
* Fornecer visualizações e relatórios unificados (ensalamento + reservas) para consulta.

**Fora do Escopo:**
* Este sistema *não* gerencia a oferta de disciplinas (criação de turmas). Ele *consome* esses dados.

### 1.3. Definições, Acrônimos e Abreviações

* **FUP:** Faculdade UnB Planaltina.
* **Ensalamento:** Processo de alocação de disciplinas/turmas em salas/espaços físicos.
* **SRS:** Especificação de Requisitos de Software.
* **Sigaa:** Sistema Integrado de Gestão de Atividades Acadêmicas (Sistema de origem dos dados de horário).
* **Sistema de Oferta:** Sistema externo que gerencia as disciplinas, turmas e horários (fonte dos dados).
* **UI:** Interface de Usuário (User Interface).
* **CRUD:** Create, Read, Update, Delete (Criar, Ler, Atualizar, Deletar).
* **API:** Application Programming Interface.
* **Admin:** Administrador do Sistema (Servidor Técnico-Administrativo).
* **Usuário Consulta:** Professor ou membro da comunidade acadêmica.
* **Bloco Atômico:** A menor unidade de tempo indivisível usada pelo Sigaa para alocação (ex: `M1`, `M2`, `N1`).
* **Professor:** Uma entidade no sistema (tabela `professores`) que possui restrições e preferências de alocação.

### 1.4. Referências

* Documento de Requisitos de Produto (`REQUIREMENTS.md`)
* Documento de Arquitetura (`ARCHITECTURE.md`)
* Código-fonte do `SigaaScheduleParser` (referência para lógica de parsing de horário).

### 1.5. Visão Geral do Documento

Este documento está estruturado da seguinte forma:
* **Seção 1 (Introdução):** Descreve o propósito, escopo e visão geral.
* **Seção 2 (Descrição Geral):** Contextualiza o produto, seus usuários e restrições.
* **Seção 3 (Requisitos Específicos):** Detalha todos os requisitos funcionais, não funcionais, de interface e de dados.

---

## 2. Descrição Geral

### 2.1. Perspectiva do Produto

O sistema será uma aplicação *standalone*, porém dependente do **Sistema de Oferta**. Ele atuará como um "módulo de otimização" que consome dados brutos (demanda) e produz um resultado (alocação), ao mesmo tempo que serve como um sistema de agendamento para reservas avulsas. Ele será desenvolvido em Python com Streamlit, para um ciclo de desenvolvimento rápido, e hospedado internamente (self-hosted) usando um banco de dados **SQLite3** e alinhado com o **modelo de blocos de horário atômicos do Sigaa**.

### 2.2. Funções do Produto (Resumo)

1.  Gestão de Inventário (Campi, Prédios, Salas).
2.  Gestão de Tipos de Sala (CRUD).
3.  Gestão de Blocos de Horário (Sigaa).
4.  Gestão de Características de Salas (CRUD).
5.  Gestão de Professores e Preferências (CRUD).
6.  Sincronização de Demanda (Semestral, via API).
7.  Gestão de Regras (focadas em Disciplinas).
8.  Motor de Alocação (Semestral).
9.  Edição Manual (do ensalamento semestral).
10. Gestão de Reservas Esporádicas (Manual, Avulsa).
11. Visualização Unificada e Relatórios.
12. Administração de Usuários.

### 2.3. Características dos Usuários

| Perfil | Descrição | Nível de Acesso |
| :--- | :--- | :--- |
| **Administrador** (Técnico-Administrativo) | Usuário principal. Gerencia inventário, regras, professores, executa alocação semestral e gerencia *todas* as reservas esporádicas. | Acesso total. |
| **Usuário Padrão** (Professor, Servidor) | Usuário logado. Consulta o ensalamento, pode criar/gerenciar suas próprias reservas esporádicas e, **se vinculado a um perfil de professor (RF-003.A), pode gerenciar suas próprias preferências de sala.** | Acesso de Leitura + Criação/Gestão de Reservas Próprias + Gestão de Preferências Próprias. |
| **Visitante** (Aluno, Comunidade) | Acesso público (sem login). | Acesso apenas à consulta pública (TVs, busca). |

### 2.4. Restrições Gerais

* **RST-01:** O sistema deve ser desenvolvido em **Python**.
* **RST-02:** O framework web deve ser **Streamlit** (preferencial) ou Plotly Dash.
* **RST-03:** O banco de dados deve ser **SQLite3**.
* **RST-04:** A autenticação deve usar a biblioteca `streamlit-authenticator`.
* **RST-05:** A implantação deve ser **self-hosting** em servidores da FUP/UnB.
* **RST-06:** O sistema deve ser responsivo (compatível com computadores, tablets e celulares).
* **RST-07:** O sistema deve operar internamente com o **modelo de blocos de horário atômicos** (ex: `M1`, `M2`, `T1`) do Sigaa para garantir a integridade dos conflitos.

### 2.5. Suposições e Dependências

* **DEP-01:** A API do Sistema de Oferta está disponível, documentada e fornece os dados necessários, incluindo os dados de horário no formato de **código Sigaa** (ex: `'24M12'`) e o **nome textual dos professores** (ex: `'Dr. João Silva'`).
* **SUP-01:** Os usuários Administradores possuem conhecimento básico de informática para operar uma interface web.

---

## 3. Requisitos Específicos

### 3.1. Requisitos de Interface Externa

#### 3.1.1. Interfaces de Usuário (UI)

* **UI-01:** A interface deve ser baseada na web, limpa e intuitiva (padrão Streamlit).
* **UI-02:** A navegação principal deve ser realizada através de um menu lateral (sidebar).
* **UI-03:** O sistema deve ser responsivo e adaptar-se a diferentes tamanhos de tela (desktop, tablet, celular).
* **UI-04:** Deve haver feedback visual claro para ações (ex: "Dados salvos com sucesso", "Erro na alocação").

#### 3.1.2. Interfaces de Hardware

* Nenhum requisito específico além do servidor de hospedagem e dos dispositivos de cliente (computadores, celulares).

#### 3.1.3. Interfaces de Software (API)

* **API-01:** O sistema deve consumir (via `GET`) a API do Sistema de Oferta.
* **API-02:** A autenticação com a API de Oferta deve ser feita (provavelmente via Bearer Token).
* **API-03:** O sistema deve mapear corretamente os seguintes campos recebidos da API para seu banco de dados interno:
    * `código_disciplina`
    * `nome_disciplina`
    * `professores_disciplina` (campo de texto bruto, ex: "Dr. João Silva, Dra. Maria")
    * `turma_disciplina`
    * `vagas_disciplina`
    * `horario_disciplina` (campo bruto, ex: `'2M12 4M12'`)

#### 3.1.4. Interfaces de Comunicação

* A aplicação deve ser servida via **HTTPS** (configurado no proxy reverso/NGINX).

### 3.2. Requisitos Funcionais (RF)

#### RF-001: Gerenciamento de Autenticação e Perfil
* **RF-001.1:** O sistema deve ter uma tela de login.
* **RF-001.2:** O sistema deve usar o `streamlit-authenticator` para gerenciar usuários.
* **RF-001.3:** O sistema deve diferenciar, no mínimo, dois níveis de acesso: **Admin** e **Usuário Padrão** (ex: Professor).
* **RF-001.4 (Admin):** Acesso total a todos os CRUDs, regras, execução e gerenciamento de *todas* as reservas e preferências.
* **RF-001.5 (Usuário Padrão):** Acesso de consulta ao ensalamento, permissão para (`RF-011`) criar/gerenciar *suas próprias* reservas esporádicas e permissão para (`RF-003.A.4`) gerenciar *suas próprias* preferências de professor.

#### RF-002: Gestão de Inventário de Espaços (CRUD)
* **RF-002.1 (Admin):** Deve permitir o CRUD de **Campi**.
* **RF-002.2 (Admin):** Deve permitir o CRUD de **Prédios** (associados a um Campus).
* **RF-002.3 (Admin):** Deve permitir o CRUD de **Salas** (associadas a um Prédio).
* **RF-002.4 (Admin):** Ao criar/editar uma Sala, o Admin deve poder definir:
    * Nome/Número da Sala
    * Prédio (associado)
    * Capacidade (número de assentos)
    * Tipo de Assento
    * Andar
    * **Tipo de Sala (Selecionar de uma lista** populada pela tabela `tipos_sala` - Ver `RF-002.A`).

#### RF-002.A: Gestão de Tipos de Sala (CRUD)
* **RF-002.A.1 (Admin):** O Admin deve ter acesso a uma interface de gerenciamento (CRUD) dedicada para "Tipos de Sala".
* **RF-002.A.2 (Admin):** O Admin deve poder **Criar**, **Editar** e **Deletar** tipos de sala.
* **RF-002.A.3:** O sistema deve impedir a exclusão de um `Tipo de Sala` se houver alguma `Sala` (`RF-002.3`) atualmente associada a ele.
* **RF-002.A.4:** O sistema deve ser inicializado (primeira carga) com os tipos básicos sugeridos (ex: "Sala de Aula", "Laboratório de Física", "Auditório").

#### RF-002.B: Gestão de Horários e Dias (Sigaa)
* **RF-002.B.1:** O sistema deve ter uma tabela (`horarios_bloco`) para armazenar os blocos de horário atômicos do Sigaa (ex: `M1`, `M2`, `N1`, etc.).
* **RF-002.B.2:** Esta tabela deve ser pré-populada (via *seed* de banco de dados) com os 16 blocos padrão (M1-M5, T1-T6, N1-N4) e seus horários de início/fim correspondentes. Esta tabela não necessita de CRUD na UI.
* **RF-002.B.3:** O sistema deve ter uma tabela (`dias_semana`) para mapear os IDs Sigaa (2-7) para os nomes ("SEG", "TER", ...). Esta tabela também deve ser pré-populada.

#### RF-003: Gestão de Características de Salas
* **RF-003.1 (Admin):** O sistema deve permitir o CRUD de **Características Estáticas** (ex: "Projetor", "Quadro de Giz", "Acesso para Cadeirantes").
* **RF-003.2 (Admin):** Na tela de gestão de Salas, o Admin deve poder associar/desassociar essas características a cada sala (relação N:N).
* **RF-003.3 (Admin):** O sistema deve permitir a **inclusão de características dinâmicas** (tags) não previstas inicialmente.

#### RF-003.A: Gestão de Professores e Preferências
* **RF-003.A.1 (Admin):** O Admin deve ter acesso a uma interface de gerenciamento (CRUD) dedicada para **Professores**.
* **RF-003.A.2 (Admin):** O Admin deve poder Criar, Editar e Deletar professores, definindo:
    * `nome_completo`: Este nome deve ser o texto exato que a API do Sistema de Oferta fornece (ex: "Dr. João Silva"), para permitir o *link* automático.
    * `tem_baixa_mobilidade` (Sim/Não): Esta é uma **restrição dura**.
    * `username_login` (Opcional): O Admin pode vincular um perfil de professor a uma conta de `usuario` (da tabela `usuarios`).
* **RF-003.A.3 (Admin):** O Admin deve poder, para qualquer professor, gerenciar suas **preferências suaves** (regras N:N):
    * Associar/desassociar Salas preferidas (tabela `professor_prefere_sala`).
    * Associar/desassociar Características preferidas (tabela `professor_prefere_caracteristica`, ex: "Prefere Projetor").

#### RF-004: Importação de Demanda (Sincronização)
* **RF-004.1 (Admin):** O Admin deve ter uma interface (ex: página "Semestre") para gerenciar os dados do semestre.
* **RF-004.2 (Admin):** O Admin deve poder selecionar o semestre (ex: 2025.2) e clicar em um botão "Sincronizar com Sistema de Oferta".
* **RF-004.3:** Ao sincronizar, o sistema deve consumir a API (`API-03`) e popular a tabela de `demandas`, incluindo o `horario_sigaa_bruto` e o `professores_disciplina` (texto bruto).
* **RF-004.4:** O sistema deve identificar disciplinas que *não* necessitam de sala (ex: "Estágio Supervisionado") e marcá-las como "Não Alocar".

#### RF-005: Gestão de Regras de Alocação (Focadas em Disciplina)
* **RF-005.1 (Admin):** O sistema deve permitir a criação e gestão de **Regras Estáticas** (duras) focadas em *disciplinas*.
    * **RF-005.1.1 (Regra: Disciplina-Tipo de Sala):** Alocar *sempre* uma Disciplina específica (pelo `codigo_disciplina`) em uma Sala de um `Tipo de Sala` específico (ex: "Laboratório de Química").
    * **RF-005.1.2 (Regra: Disciplina-Sala):** Alocar *sempre* uma Disciplina específica em uma Sala específica.
* **RF-005.2 (Admin):** O sistema deve permitir a configuração de **Regras Dinâmicas** (suaves) focadas em *disciplinas*.
    * **RF-005.2.1 (Requisito de Equipamento):** *Tentar* alocar disciplinas (pelo `codigo_disciplina`) em salas que possuam uma `caracteristica` específica.
    * **RF-005.2.2 (Prioridade de Nível):** Priorizar a alocação de disciplinas de Graduação antes de Pós-Graduação.
    * **RF-005.2.3 (Agrupamento de Professor):** Tentar alocar diferentes disciplinas do *mesmo* professor (texto `professores_disciplina`) na *mesma* sala.

#### RF-006: Execução do Motor de Alocação (Semestral)
* **RF-006.1 (Admin):** O Admin deve poder "Executar o Ensalamento" para um semestre selecionado.
* **RF-006.2 (Parsing de Horário):** O motor deve *parsear* o `horario_sigaa_bruto` de cada `demanda` (ex: '24M12') em seus blocos atômicos constituintes (ex: [dia=2, bloco=M1], [dia=2, bloco=M2], [dia=4, bloco=M1], [dia=4, bloco=M2]).
* **RF-006.3 (Lookup de Professor):** Para cada `demanda`, o motor deve ler o texto `professores_disciplina` e tentar encontrar o(s) `id`(s) correspondente(s) na tabela `professores`.
* **RF-006.4 (Alocação de Regras Duras):** O motor deve primeiro alocar as demandas que se enquadram em **Restrições Duras**. A ordem de alocação deve priorizar as demandas mais restritas. As restrições rígidas/duras incluem:
    * Regras de Disciplina (`RF-005.1`).
    * Restrições de Professor (ex: `tem_baixa_mobilidade = true` $\rightarrow$ deve filtrar apenas salas no Térreo ou com `caracteristica` "Acesso para Cadeirantes").
    * Se houver conflito (duas regras duras competindo pelo mesmo bloco/sala), o sistema deve parar e reportar o conflito.
* **RF-006.5 (Alocação de Regras Suaves):** Após alocar as regras duras, o motor deve processar as demais demandas, respeitando as **Prioridades (Suaves)**. O motor deve usar um sistema de pontuação para encontrar a "melhor" sala, onde uma sala ganha pontos se:
    * Atende a uma regra suave de disciplina (`RF-005.2`).
    * Atende a uma preferência suave de professor (`RF-003.A.3`, ex: sala preferida, característica preferida).
    * Atende à capacidade (`RF-005.2.4`, capacidade $\ge$ vagas).
* **RF-006.6 (Regras de Frequência):** O motor deve utilizar o resultado de ensalamento de semestres anteriores na tabela `alocacoes_semestrais` para dar prioridade ao par disciplina<=>sala, isto é, quanto mais vezes uma disciplina tiver sido previamente alocada para uma mesma sala, maior é a sua prioridade. Este é uma regra que deve ser construída dinamicamente, ao ler as alocações (existentes) para dos semestres anteriores. 
* **RF-006.7 (Salvar):** O motor deve salvar o resultado na tabela `alocacoes_semestrais`. Cada *bloco atômico* alocado será uma **linha separada** nesta tabela.

#### RF-007: Visualização do Ensalamento
* **RF-007.1 (Consolidada):** Deve haver uma visualização em formato de Grade de Horário/Calendário que **consolide (mostre juntos)** os dados de:
    * `alocacoes_semestrais` (resultado do `RF-006`).
    * `reservas_esporadicas` (resultado do `RF-011`).
* **RF-007.2 (Combinação de Blocos):** Na UI, o sistema deve *re-combinar* blocos atômicos consecutivos (ex: `M1`, `M2` alocados para a mesma disciplina/reserva) em uma única entrada visual (ex: "08:00/09:50").
* **RF-007.3 (Vistas):** Deve ser possível visualizar a grade por **Sala**, **Professor** ou **Curso/Disciplina**.

#### RF-008: Ajuste Manual do Ensalamento (Semestral)
* **RF-008.1 (Admin):** O Admin deve poder "trocar" uma *alocação semestral* (`RF-006`) de sala.
* **RF-008.2:** Ao fazer o ajuste, o sistema deve validar (em tempo real) se a nova sala/horário/bloco conflita com:
    * Outra alocação semestral.
    * Uma **reserva esporádica** (`RF-011`).
* **RF-008.3 (Validação de Regras):** O sistema deve **alertar** (mas não necessariamente bloquear) o Admin se o ajuste manual violar uma regra dura (ex: mover um professor com baixa mobilidade para o 2º andar) ou uma preferência suave.

#### RF-009: Geração de Relatórios e Exportação
* **RF-009.1 (Todos os Usuários):** O sistema deve permitir a **exportação para PDF** do ensalamento.
* **RF-009.2:** O relatório PDF (por sala) deve **mostrar todos os horários reservados** (aulas e eventos), com os blocos combinados (`RF-007.2`) (Ex: "cada sala/laboratório ocupa exatamente uma página").
* **RF-009.3:** A exibição simplificada (Modo TV) deve também **mostrar a grade unificada** (aulas e eventos).

#### RF-010: Busca e Filtro
* **RF-010.1 (Todos os Usuários):** O sistema deve fornecer uma funcionalidade de busca textual.
* **RF-010.2:** A busca deve permitir encontrar informações por:
    * Nome da Disciplina
    * Nome do Professor
    * Número/Nome da Sala
    * **Título/Motivo da Reserva Esporádica**
    * **Tipo de Sala**

#### RF-011: Gestão de Reservas Esporádicas (Avulsas)
* **RF-011.1 (Usuário Padrão, Admin):** Usuários logados devem ter acesso a uma interface (página "Reservar Sala") para criar reservas avulsas.
* **RF-011.2 (UI de Blocos):** A interface deve permitir ao usuário selecionar/informar:
    * Filtro por `Tipo de Sala` (usando a tabela `tipos_sala`) - Ex: "Mostrar apenas Auditórios".
    * Sala/Espaço desejado (lista filtrada).
    * **Uma data específica** (ex: "2025-10-30").
    * **Um ou mais `Blocos de Horário`** (ex: `M1`, `M2`, `M3`) apresentados de forma amigável (ex: "M1 (08:00-08:55)") em uma lista, checkboxes ou similar.
    * Título/Motivo da Reserva (ex: "Palestra Convidado X").
* **RF-011.3 (Verificação de Conflito):** O sistema deve verificar **em tempo real** a disponibilidade, checando conflitos nas tabelas `alocacoes_semestrais` E `reservas_esporadicas` para a `sala_id`, `data_reserva` (convertendo o dia da semana da alocação semestral para a data específica) e cada `codigo_bloco` selecionado.
* **RF-011.4:** Se houver conflito em *qualquer* um dos blocos selecionados, o sistema deve impedir a reserva e informar o usuário.
* **RF-011.5 (Usuário Padrão):** O usuário pode ver, editar e deletar apenas as reservas que ele mesmo criou.
* **RF-011.6 (Admin):** O Admin pode ver, editar e deletar *todas* as reservas esporádicas.
* **RF-011.7 (Opcional - Admin):** O sistema pode ter um fluxo de "aprovação".
* **RF-011.8 (Armazenamento):** Ao salvar, o sistema deve criar uma linha separada na tabela `reservas_esporadicas` para *cada* `codigo_bloco` selecionado pelo usuário.

### 3.3. Requisitos Não Funcionais (RNF)

* **RNF-001 (Desempenho):**
    * RNF-001.1: A importação da API (`RF-004`) deve ser concluída em menos de 5 minutos.
    * RNF-001.2: A execução do motor de alocação (`RF-006`) deve ser concluída em tempo razoável (ex: < 10 minutos).
    * RNF-001.3: As consultas de grade (`RF-007`) e checagem de conflito (`RF-011.3`) devem ser (< 3 segundos).
    * **RNF-001.4 (Concorrência):** O uso de **SQLite3** implica em bloqueio em nível de arquivo durante operações de escrita. Assume-se que a concorrência de escrita (múltiplos usuários clicando em "Reservar" no exato mesmo segundo) é baixa.
* **RNF-002 (Usabilidade):**
    * RNF-002.1: O fluxo de reserva esporádica (`RF-011`) deve ser intuitivo, e o usuário deve entender facilmente a seleção de blocos de horário (M1, M2, etc.).
* **RNF-003 (Confiabilidade):**
    * RNF-003.1: O sistema deve garantir 100% de integridade dos dados (sem alocações duplicadas, sem conflitos não reportados) através do modelo de bloco atômico.
* **RNF-004 (Segurança):**
    * RNF-004.1: Todas as senhas de usuário devem ser armazenadas usando hash (provido pelo `streamlit-authenticator`).
    * RNF-004.2: O token de acesso à API do Sistema de Oferta deve ser armazenado de forma segura (variáveis de ambiente ou secrets).
* **RNF-005 (Manutenibilidade):**
    * RNF-005.1: O código Python deve seguir as boas práticas (PEP 8) e ser modularizado (ex: `pages/`, `services/`, `database.py`).
    * RNF-005.2: A lógica do "Motor de Alocação" (`RF-006`) e a lógica de "Checagem de Conflito" (`RF-011.3`) devem ser serviços separados.
    * **RNF-005.3 (Parser Sigaa):** O parser de horário Sigaa (para `RF-006.2`) deve ser um módulo Python separado e bem testado.
* **RNF-006 (Compatibilidade):**
    * RNF-006.1: O sistema deve ser compatível com os navegadores modernos (Chrome, Firefox, Safari, Edge).
    * RNF-006.2: A interface deve ser funcional em desktops, tablets e celulares (design responsivo).

### 3.4. Requisitos de Banco de Dados

* **BD-01:** O sistema deve usar **SQLite3**.
* **BD-02:** O esquema do banco de dados deve suportar todas as entidades e relacionamentos, incluindo:
    * `tipos_sala` (CRUD)
    * `dias_semana` (Sigaa, pré-populado)
    * `horarios_bloco` (Sigaa, pré-populado)
    * **`professores` (CRUD, com restrições duras como `tem_baixa_mobilidade`)**
    * **`professor_prefere_sala` (N:N)**
    * **`professor_prefere_caracteristica` (N:N)**
    * `alocacoes_semestrais` (armazenamento por bloco atômico)
    * `reservas_esporadicas` (armazenamento por bloco atômico)
* **BD-03:** O backup do banco de dados será realizado pela infraestrutura de hospedagem através da cópia regular do arquivo `.sqlite3` da aplicação.
* **BD-04:** O esquema deve usar chaves estrangeiras (foreign keys) para garantir a integridade referencial (requer `PRAGMA foreign_keys = ON;` no SQLite3).