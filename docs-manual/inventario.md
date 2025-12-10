# Inventário (Salas e Prédios)

O módulo **🏢 Inventário** é a base do sistema, onde toda a infraestrutura física é cadastrada. Sem salas cadastradas, não é possível realizar alocações.

## Estrutura do Inventário

O inventário é hierárquico:
1.  **Campi** (ex: UNB - Planaltina)
2.  **Prédios** (ex: UAC, Pavilhão)
3.  **Salas** (ex: Sala 01, Lab Informática)

## Funcionalidades por Aba

### 🚪 Salas
Gerenciamento das salas de aula.
*   **Adicionar Sala:** Defina nome, capacidade (número de assentos), tipo (Sala de Aula, Laboratório) e prédio.
*   **Editar/Excluir:** Atualize a capacidade ou remova salas desativadas.
*   **Associação de Características:** Vincule atributos à sala (ex: "Possui Ar Condicionado", "Projetor HDMI", "Acessibilidade"). Isso é crucial para que o algoritmo saiba quais salas atendem às necessidades especiais.

### 🏢 Prédios
Cadastro dos edifícios.
*   Necessário criar os prédios antes de cadastrar as salas.
*   Permite agrupar salas geograficamente.

### 🏫 Campi
Cadastro das unidades maiores (Campus). Utilizado principalmente se o sistema gerenciar múltiplos locais físicos distantes.

### 🔗 Assoc. Características
Gerenciamento centralizado das características disponíveis no sistema (ex: criar nova característica "Lousa Digital" para depois associar às salas).
