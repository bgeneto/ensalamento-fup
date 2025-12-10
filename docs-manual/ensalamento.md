# Ensalamento (Alocação)

O módulo **✅ Ensalamento** é o coração da aplicação, onde ocorre a distribuição das turmas nas salas.

## Fluxo de Trabalho

### 1. 🚀 Alocação Autônoma
A forma mais eficiente de começar é rodando o algoritmo inteligente.
*   Clique em **🚀 Executar Alocação Autônoma**.
*   O robô processará todas as demandas pendentes, aplicando as Regras Rígidas (obrigatórias) e tentando maximizar as Regras Suaves (preferências) e o histórico.
*   Ao final, ele exibe um resumo do que conseguiu alocar e gera um relatório PDF preliminar com as decisões tomadas.

### 2. 🎯 Alocação Manual / Assistida
Para as demandas que o robô não conseguiu resolver (ou para ajustes finos), use a interface dividida:
*   **Esquerda (Fila):** Lista de disciplinas pendentes (não alocadas). Use os filtros para encontrar turmas específicas.
*   **Direita (Assistente):** Ao clicar em "🎯 Alocar Sala" em uma demanda, o assistente abre.
    *   **Sugestões:** O sistema lista salas compatíveis ordenadas por "Score" (pontuação). O score considera capacidade, preferências do professor, histórico e evita conflitos.
    *   **Conflitos:** Salas ocupadas aparecerão marcadas como indisponíveis.
    *   **Seleção:** Clique no botão de alvo ao lado da sala desejada para confirmar a alocação.

### 3. Edição e Desalocação
*   Para trocar uma sala, basta selecionar a demanda (agora na lista de "Alocadas") e escolher uma nova sala.
*   Para remover uma alocação (voltar para a fila), você pode usar a opção de desalocar.
