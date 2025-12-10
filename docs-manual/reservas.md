# Reservas Esporádicas

O módulo **📅 Reservas** gerencia usos do espaço físico que **não** são aulas regulares do semestre (ex: defesas de TCC, reuniões de departamento, eventos estudantis).

## Navegação

O módulo é dividido em duas abas principais (selecionáveis no topo):

### 1. 📅 Visualizar Reservas
Lista e calendário das reservas já agendadas.
*   **Filtros:** Busque por data, título do evento, sala ou prédio.
*   **Edição:** Dê clique duplo na tabela para alterar o título, solicitante ou responsável.
*   **Exclusão:** Selecione a linha e clique na lixeira para cancelar a reserva.
*   **Merge Automático:** Reservas contínuas (ex: M1, M2 e M3) são exibidas como uma linha só (08:00 - 10:55) para facilitar a leitura.

### 2. ➕ Nova Reserva
Formulário para criar novos agendamentos.

#### Passo a Passo:
1.  **Tipo de Recorrência:** Defina se é um evento único ou se repete.
    *   *Único, Diário, Semanal (ex: toda terça), ou Mensal.*
2.  **Informações:**
    *   **Título:** Nome do evento.
    *   **Solicitante:** Quem pediu a sala (Obrigatório, nome completo).
    *   **Responsável:** Quem estará lá (Opcional).
    *   **Sala:** Escolha a sala desejada.
3.  **Data e Horário:**
    *   Selecione a Data Inicial.
    *   Marque os **Blocos de Horário** (checkboxes). Você pode marcar vários (ex: M1 e M2).
4.  **Configuração de Recorrência** (se aplicável):
    *   Defina até quando a reserva se repete (Data Final).
    *   Para repetição semanal, escolha os dias da semana.
5.  Clique em **✅ Criar Reserva**.

> [!WARNING]
> O sistema de reservas verifica conflitos tanto com outras reservas quanto com as aulas regulares do Ensalamento. Não é possível criar uma reserva ("force") se a sala já estiver ocupada por uma aula.
