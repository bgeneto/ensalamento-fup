# Demanda Semestral (Disciplinas)

O módulo **🧭 Demanda** é onde o administrador gerencia a "oferta" de disciplinas do semestre, que servirá de insumo para o ensalamento.

## Funcionalidades

### 🔄 Sincronização Automática
A principal forma de alimentar o sistema é através da importação.
1.  **Semestre Global:** Verifique se o semestre exibido é o correto (gerenciado em Configurações).
2.  **Cursos a Ignorar:** Antes de importar, você pode marcar cursos inteiros (ex: "PPG-MADER", "LEDOC") para que suas disciplinas *não* sejam importadas. Isso é útil para limpar a base de dados de turmas que não usam o espaço físico principal.
3.  Clique em **🔄 Sincronizar Demanda**. O sistema conectará à fonte de dados (Planilha de Oferta/SIGAA) e trará as turmas.

### ➕ Adição Manual
Caso alguma disciplina não esteja na fonte oficial, você pode adicioná-la manualmente.
*   Preencha código, nome, turma, horário (formato SIGAA, ex: `24M12`) e número de vagas.

### 📋 Visualização e Edição
A tabela exibe todas as demandas importadas.
*   **Avisos:** O sistema alerta se houver professores na demanda que não estão cadastrados no módulo de Professores.
*   **Edição na Grade:** Você pode corrigir dados (como número de vagas) diretamente na tabela.
*   **Exclusão:** Se uma turma foi cancelada, você pode removê-la da lista para que não ocupe uma sala desnecessariamente.

> [!NOTE]
> O formato de horário SIGAA é essencial. Exemplo: `24M12` significa Segunda e Quarta, Manhã, horários 1 e 2 (08:00 às 09:50).
