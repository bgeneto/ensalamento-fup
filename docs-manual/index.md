# Sistema de Ensalamento FUP/UnB - Manual do Usuário

Bem-vindo ao Manual do Usuário do **Sistema de Ensalamento FUP/UnB**. Este documento tem como objetivo servir como um guia completo para a utilização do sistema, cobrindo desde o acesso inicial até a execução dos algoritmos de alocação de salas e gerenciamento do inventário.

## O que é o Sistema?

O Sistema de Ensalamento da FUP (Faculdade UnB Planaltina) é uma solução web desenvolvida para auxiliar a gestão acadêmica no processo de alocação de disciplinas em salas de aula. Ele utiliza algoritmos de otimização para tentar encontrar a melhor distribuição possível, respeitando:

*   Capacidade das salas
*   Necessidades das disciplinas (Projetor, Laboratório, etc.)
*   Preferências dos professores (Mobilidade reduzida, localizações, horários)
*   Conflitos de horário (impedindo que um professor dê aula em dois lugares ao mesmo tempo, ou que uma sala seja usada duplamente)

## Principais Funcionalidades

O sistema está dividido em módulos funcionais acessíveis através da barra lateral de navegação:

*   **🏠 Home:** Visão geral e pública do ensalamento atual (grades horárias).
*   **⚙️ Configurações:** Definição do semestre ativo, pesos de pontuação para o algoritmo e configurações gerais.
*   **🏢 Inventário:** Gestão da infraestrutura física (Campi, Prédios e Salas).
*   **👨‍🏫 Professores:** Cadastro de docentes e controle de suas necessidades especiais (ex: mobilidade).
*   **📌 Regras:** Definição de preferências (suaves) e restrições (rígidas) de alocação para professores e disciplinas.
*   **🧭 Demanda:** Importação e gestão da oferta de disciplinas do semestre.
*   **✅ Ensalamento:** Execução do motor de alocação e verificação de conflitos.
*   **👁️ Visualização:** Relatórios detalhados, mapas de calor e exportação de resultados.
*   **📅 Reservas:** Gestão de reservas esporádicas de salas.

## Público Alvo

Este manual é destinado a:
*   **Administradores do Sistema:** Responsáveis pela configuração global e manutenção do inventário.
*   **Coordenadores de Curso:** Responsáveis por revisar as demandas e validar o ensalamento.
*   **Secretaria Acadêmica:** Operadores do dia-a-dia que importam dados e geram relatórios.

> [!NOTE]
> Este manual reflete a versão atual do sistema. Como o software está em evolução contínua, algumas telas podem apresentar pequenas diferenças em relação à documentação.
