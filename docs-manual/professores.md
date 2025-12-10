# Gerenciamento de Professores

O módulo **👨‍🏫 Professores** mantém o cadastro do corpo docente. Esses dados são essenciais para evitar conflitos de horário (o mesmo professor em duas salas) e para atender preferências individuais.

## Abas Disponíveis

### 📋 Lista de Professores
Visualização em tabela de todos os docentes cadastrados.
*   **Edição Rápida:** Você pode editar os dados diretamente na tabela (estilo planilha).
*   **Mobilidade Reduzida:** Coluna importante! Marque a caixa de seleção **♿ Mobilidade Reduzida** se o professor necessita de salas acessíveis (térreo ou com elevador). O algoritmo tratará isso como prioridade máxima.
*   **Username:** O "nome de usuário" é usado para integração com sistemas externos (SIGAA) e para login (caso o professor venha a ter acesso direto).

### 📥 Importar
Facilita o cadastro em massa.
*   **Upload CSV:** Carregue um arquivo `.csv` contendo uma lista de professores (Username; Nome Completo).
    *   Formato esperado: `username_login;nome_completo`
    *   Separador: ponto-e-vírgula (`;`)
*   **Importação Manual:** Formulário simples para adicionar um único professor caso não queira usar planilha.

> [!TIP]
> Periodicamente, revise a lista de professores para remover inativos ou atualizar restrições de mobilidade.
