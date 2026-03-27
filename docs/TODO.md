Sugestões para aprimorar o sistema de ensalamento:



- Única forma de desfazer o ensalamento é removendo todas as demandas, seria possível criar uma forma de desfazer o ensalamento completamente sem mexer nas demandas? 

- A ação de sincronizar a demanda com a API do sistema de oferta desfaz toda a demanda, inclusive as demandas acrescentadas e/ou alteradas manualmente.

- Depois de travar uma sala ela fica indisponível p/ novas alocações.

- Pesquisa/filtro de disciplina na página Ensalamento 

- ~~Preferir alocar as disciplinas diferentes de um mesmo professor na mesma sala sempre que possível~~

- ~~Preferir preencher todos os horários (time slots) de uma disciplina na mesma sala, isto é, sempre que possível (e a disciplina não for híbrida) alocar todos os slots de uma disciplina, mesmo que em dias diferentes, na mesma sala.~~  

- ~~Iniciar a distribuição pelas disciplinas que tenham horários em dias diferentes, depois as blocadas.~~ 

- Verificar se um update/deploy do sistema mantém as configs de pontuação contidas no arquivos de config



---

Prompt:

No modo parcial, blocos do mesmo dia ficam juntos; dias diferentes podem ir para salas diferentes. Esse agrupamento por dia é a base do split allocation: sigaa_parser.py (line 191) e optimized_autonomous_allocation_service.py (line 235). Isso dificulta os seguintes pontos/exigências: 

- Preferir preencher todos os horários (time slots) de uma disciplina na mesma sala, isto é, sempre que possível (e a disciplina não for híbrida) alocar todos os slots de uma disciplina, mesmo que em dias diferentes, na mesma sala.  
- preferir alocar as disciplinas diferentes de um mesmo professor na mesma sala sempre que possível (que não hajam regras impedindo)



Como podemos adaptar/melhorar o fluxo do modo de alocação utilizado (parcial) a fim de garantir essas duas exigências? talvez seja melhor escolher por onde começar a alocação, talvez seja melhor iniciar a distribuição pelas disciplinas que tenham horários em dias diferentes, a fim de garantir que mesmo em dias diferentes elas sejam alocadas na mesma sala (se não for disciplina híbrida) e somente depois alocar as disciplinas blocadas (todos os time slots no mesmo dia). o que você acha, o que você sugere para otimizar a alocação de maneira eficiente, profissional e robusta?



---



Prompt:



