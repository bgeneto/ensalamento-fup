# Requisitos de Produto: Sistema de Ensalamento FUP/UnB

## 1. Propósito Principal e Proposta de Valor

O **Sistema de Ensalamento FUP/UnB** é uma aplicação web interna projetada para automatizar, gerenciar e otimizar a alocação de salas de aula e laboratórios na instituição.

A principal proposta de valor é substituir o processo de ensalamento manual (presumivelmente complexo e sujeito a erros) por um sistema inteligente que:
1.  **Centraliza** todas as informações de salas, disciplinas e restrições.
2.  **Automatiza** a alocação complexa usando um motor de regras e otimização.
3.  **Resolve conflitos** e garante o cumprimento das regras de negócio (ex: acessibilidade, laboratórios específicos).
4.  **Fornece transparência** à comunidade acadêmica sobre o uso dos espaços.

## 2. Usuários-Alvo e Casos de Uso

| Usuário-Alvo | Casos de Uso Principais |
| :--- | :--- |
| **Servidores Técnico-Administrativos** (Gestores de Espaço, Secretarias) | - Gerenciar o inventário de salas e seus atributos.<br>- **Gerenciar (CRUD) os `Tipos de Sala` (ex: Laboratório, Auditório).**<br>- Importar dados do semestre (via API).<br>- Definir e gerenciar regras de alocação semestral.<br>- Executar o algoritmo de ensalamento automático.<br>- Gerenciar reservas esporádicas.<br>- Gerar relatórios (PDF por sala, planilhas). |
| **Professores** (e outros Servidores Logados) | - Consultar o ensalamento final.<br>- **Solicitar/Reservar salas, laboratórios ou auditórios** (filtrando por tipo) para eventos esporádicos.<br>- Visualizar o calendário completo de uma sala. |
| **Comunidade Acadêmica** (Alunos, Visitantes) | - Consultar o ensalamento público (visualização em TVs, tablets). |

## 3. Funcionalidades Chave (Priorizadas)

1.  **P-0 (Crítico): Integração com Sistema de Oferta**
    * Consumir a API do Sistema de Oferta para buscar (GET) todos os dados do semestre (disciplinas, professores, turmas, vagas, horários, nível).
    * Atuar como a fonte única da verdade para a *demanda* de salas.
    
2.  **P-0 (Crítico): Gestão de Inventário (Salas e Tipos)**
    * CRUD para campi, prédios e salas.
    * **CRUD para `Tipos de Sala` (ex: "Laboratório de Física", "Auditório").**
    * Atribuir um `Tipo de Sala` (da nova tabela) a cada sala criada.
    * Definir atributos (capacidade, andar, características dinâmicas).

3.  **P-0 (Crítico): Motor de Regras e Alocação (Semestral)**
    * Processar regras estáticas (ex: Prof. X sempre na sala Y, Prof. com mobilidade reduzida em andar térreo, Disciplina X em Lab Y).    
    * Processar regras dinâmicas (priorizar graduação, alocar mesmo prof. na mesma sala, etc.).    
    * Gerar um plano de ensalamento otimizado que minimize conflitos e maximize o atendimento às preferências.
    
4.  **P-1 (Essencial): Gestão de Reservas Esporádicas**
    * Interface para usuários logados selecionarem uma sala, data e horário.
    * **Verificação de conflito em tempo real (contra aulas e outras reservas).**
    * **Permitir filtrar salas por `Tipo de Sala` (ex: "Mostrar apenas Auditórios").**

5.  **P-1 (Essencial): Relatórios e Exportação**
    * Visualização simplificada para TVs/Telas pequenas.
    * Exportação para PDF, onde cada sala ocupa exatamente uma página, detalhando todos os seus horários reservados.
    * Funcionalidade de busca (por disciplina, professor, sala).

6.  **P-1 (Essencial): Autenticação de Usuários**
    * Sistema de login para diferenciar administradores (Técnicos - login/auth required) de usuários comuns (Professores/Consulta - sem login/no auth).

7.  **P-2 (Desejável): Histórico e Otimização**
    * Usar dados de semestres anteriores para informar e melhorar o algoritmo de alocação futura. A cada novo semestre o sistema deve ser carregado com os dados dos semestre anterior.

## 4. Critérios de Sucesso

* Redução de 100% dos conflitos de alocação (duas turmas na mesma sala/horário).
* Atendimento de 100% das regras de negócio "duras" (acessibilidade, laboratórios específicos).
* Redução significativa (meta: >90%) do tempo gasto pelos servidores técnico-administrativos no processo de ensalamento.
* Feedback positivo dos gestores sobre a usabilidade da plataforma.

## 5. Restrições e Limitações

* **Tecnologia:** O desenvolvimento deve ser feito em Python, utilizando o framework Streamlit ou Plotly Dash, para desenvolvimento ultra-rápido.
* **Integração:** O sistema é *totalmente dependente* da disponibilidade e da qualidade dos dados fornecidos pela API do Sistema de Oferta.
* **Hospedagem:** A solução deve ser *self-hosted* (auto-hospedada) nos servidores da FUP/UnB.
* **Escopo:** O sistema *não* gerencia a oferta de disciplinas, apenas o seu ensalamento.
* **Orçamento/Prazo:** (A definir pelo cliente) - A escolha por Streamlit/Dash sugere uma preferência por velocidade de entrega (MVP) em detrimento de customização extrema de UI.