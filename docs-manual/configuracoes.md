# Configurações do Sistema

O módulo **⚙️ Configurações** permite ajustar parâmetros globais que afetam o funcionamento de todo o sistema.

## Abas de Configuração

### 1. 📝 Semestres
Aqui você gerencia os períodos letivos.
*   **Criar Semestre:** Adicione novos semestres (ex: "2024.1", "2024.2").
*   **Semestre Ativo:** Você deve marcar **um** semestre como "Ativo".
    *   O semestre ativo determina quais dados (demandas, alocações) são exibidos na Home e utilizados nos cálculos de ensalamento.
    *   Ao mudar o semestre ativo, todo o sistema passa a operar no contexto desse novo período.

### 2. 🎯 Pontuação (Pesos)
Define como o algoritmo de alocação prioriza diferentes critérios. Você pode atribuir pesos (valores numéricos) para:
*   **Atendimento de Preferências:** Quanto vale atender uma preferência "suave" de um professor?
*   **Otimização de Espaço:** Quão importante é não colocar uma turma pequena em uma sala gigante?
*   **Consistência:** Peso para manter a mesma sala para a mesma disciplina em dias diferentes.
*   Ajuste esses valores para "tunar" o comportamento do robô de alocação conforme a política da instituição.

> [!WARNING]
> Alterações drásticas nos pesos de pontuação podem mudar completamente o resultado do ensalamento. Recomenda-se testar as mudanças em um ambiente controlado.
