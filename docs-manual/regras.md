# Regras e Preferências

O módulo **📌 Regras** é o "cérebro" das restrições do sistema. Aqui você diz ao algoritmo **o que deve acontecer** e **o que seria bom que acontecesse**.

## Tipos de Regras

Existem dois níveis de "força" para as regras:

1.  **🔒 Regras Rígidas (Hard Constraints):**
    *   **Obrigatórias.** O algoritmo *não pode* violá-las sob hipótese alguma. Se não for possível atender, a disciplina ficará "Sem Sala".
    *   Exemplo: "Química Experimental **DEVE** ocorrer em um Laboratório".

2.  **⭐ Regras Suaves (Soft Constraints / Preferências):**
    *   **Desejáveis.** O algoritmo tentará atender, mas pode violar se necessário para fechar o ensalamento. Atender gera pontos; violar perde pontos.
    *   Exemplo: "Professor João **PREFERE** salas com Ar Condicionado".

## Funcionalidades por Aba

### 👨‍🏫 Professores
Define preferências pessoais de cada docente.
1.  Selecione o Professor.
2.  **Salas Preferidas:** Indique se ele gosta de salas específicas (ex: "Gosta da Sala 101").
3.  **Características Preferidas:** Indique atributos gerais (ex: "Precisa de Projetor", "Prefere Térreo").
    *   Ao salvar, essas se tornam "Preferências do Professor" (Soft Constraints).

### 📚 Disciplinas
Define requisitos técnicos das matérias.
*   Aqui você cria as Regras Rígidas e Suaves para as disciplinas.
*   **Nova Regra:**
    *   **Tipo:**
        *   `DISCIPLINA_TIPO_SALA` (Rígida): Ex: Física 1 exige Tipo "Sala de Aula".
        *   `DISCIPLINA_SALA` (Rígida): Ex: A disciplina "Operação de Microscópio" só pode acontecer na "Sala 305".
        *   `DISCIPLINA_CARACTERISTICA` (Suave): Ex: "Seminários" prefere sala com "Palco".
        *   `DISCIPLINA_SEM_SALA` (Rígida): Ex: "Estágio Supervisionado" **não requer sala** e é excluída da alocação autônoma e do assistente. Vale para todas as turmas e semestres daquele código. Alocações já existentes **não** são removidas automaticamente.
    *   **Prioridade:** Para regras suaves, defina de 1 a 10. Quanto maior, mais o algoritmo se esforçará para atender.

> [!NOTE]
> Use **Não requer sala** para disciplinas importadas da demanda que não ocupam espaço físico (estágio, TCC, atividades de campo, etc.). Elas deixam de aparecer como pendentes no ensalamento.

> [!IMPORTANT]
> Cuidado com o excesso de **Regras Rígidas**. Se você criar regras impossíveis (ex: Sala A apenas para Disc X, e Sala A apenas para Disc Y no mesmo horário), o sistema não conseguirá alocar. Use regras suaves sempre que possível.
