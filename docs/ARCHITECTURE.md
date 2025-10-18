* # Arquitetura e Stack de Tecnologia: Sistema de Ensalamento FUP/UnB

  Este documento descreve a arquitetura de software e as tecnologias para o Sistema de Ensalamento, adaptado para incluir reservas esporádicas e usar SQLite3.

  ## 1. Arquitetura de Alto Nível

  A arquitetura será um **Monólito Modularizado** (Modular Monolith) servido via **Streamlit**. Toda a aplicação (frontend, backend, lógica de negócio) é executada como um único processo Python. O uso do SQLite3 reforça essa abordagem, pois o banco de dados é um arquivo local gerenciado diretamente pela aplicação, eliminando a necessidade de um servidor de banco de dados separado.

  ## 2. Stack de Tecnologia (Tech Stack)

  | Componente                                | Tecnologia Escolhida         | Justificativa                                                |
  | :---------------------------------------- | :--------------------------- | :----------------------------------------------------------- |
  | **Framework Web (Frontend/Backend)**      | **Streamlit**                | Requisito do cliente para desenvolvimento rápido. Ideal para painéis administrativos e aplicações internas. |
  | **Linguagem de Programação**              | **Python 3.10+**             | Base do Streamlit e excelente ecossistema para manipulação de dados. |
  | **Banco de Dados Relacional (RDBMS)**     | **SQLite3**                  | **Mudança de Requisito:** O cliente optou por SQLite3 em vez de MariaDB. **Vantagem:** Simplifica drasticamente a implantação (self-hosting), pois o BD é um arquivo único, sem necessidade de servidor. Adequado para a escala e concorrência esperada (baixa concorrência de escrita). |
  | **Autenticação**                          | **streamlit-authenticator**  | Requisito do cliente. Padrão da comunidade Streamlit para login/logout. |
  | **Manipulação de Dados / Otimização**     | **Pandas**                   | Usado para carregar e manipular dados da API e como estrutura para o motor de alocação semestral. |
  | **Acesso ao Banco de Dados (ORM/Driver)** | **SQLAlchemy** (Core ou ORM) | Melhor forma de interagir com o banco de dados (SQLite3 ou outros) de forma segura, estruturada e prevenindo SQL Injection. |
  | **Comunicação API**                       | **Requests**                 | Biblioteca padrão do Python para consumir a API REST do Sistema de Oferta FUP/UnB. |

  ## 3. Hospedagem e Implantação (Deployment)

  * **Plataforma:** **Self-Hosting (Servidor Interno FUP/UnB)**.
  * **Containerização (Recomendado):** Usar **Docker** e **Docker Compose** para encapsular a aplicação Python e suas dependências. O banco de dados (`ensalamento.db`) será um arquivo dentro de um volume do Docker para persistência.
  * **Servidor Web (Proxy Reverso):** **Caddy** na frente da aplicação Streamlit para lidar com HTTPS (SSL) e cache.

  ## 4. Integrações

  * **Sistema de Oferta (Entrada de Dados):**
    * **Método:** Integração unilateral (leitura) via API REST para buscar dados do *semestre*.
    * **Fluxo:** Disparado manualmente ("Sincronizar Semestre") pelo Admin.

  

## 5. Design de Dados (Conceitual)

O banco de dados SQLite3 armazenará o estado. A principal mudança é a criação da tabela `tipos_sala` e a atualização da tabela `salas` para usar uma chave estrangeira (FK).

* `campus` (id, nome)
* `predios` (id, nome, campus_id)
* **`tipos_sala`**
    * `id` (PK)
    * `nome` (TEXT, unique, not null) - Ex: "Sala de Aula", "Laboratório de Física", "Auditório"
    * `descricao` (TEXT, nullable)
* `salas` (TABELA ATUALIZADA)
    * `id` (PK)
    * `nome` (TEXT)
    * `predio_id` (FK para predios.id)
    * `capacidade` (INTEGER)
    * `andar` (TEXT)
    * `tipo_assento` (TEXT)
    * **`tipo_sala_id` (FK para tipos_sala.id)**
* `caracteristicas` (id, nome)
* `sala_caracteristicas` (sala_id, caracteristica_id)
* `semestres` (id, ano, semestre, status)
* `demandas` (id, semestre_id, codigo_disciplina, nome_disciplina, professores, vagas, horario, nivel)
* `regras` (id, tipo_regra, prioridade, config_json)
* `alocacoes_semestrais` (id, demanda_id, sala_id, status)
* `reservas_esporadicas` (id, sala_id, username_solicitante, titulo_evento, data_inicio, data_fim, status)
* `usuarios` (username, password_hash, role - sempre seguindo a documentação/regras do módulo streamlit-authenticator)