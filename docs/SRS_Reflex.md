# Especificação de Requisitos de Software (SRS)
# Sistema de Ensalamento FUP/UnB - Reflex Implementation

**Versão:** 1.5 (Reflex Framework Migration)
**Data:** November 14, 2025

---

## 1. Introdução

### 1.1. Propósito

Este documento especifica os requisitos de software (SRS) para a migração do **Sistema de Ensalamento FUP/UnB** da arquitetura Streamlit para **Reflex v0.8.19**. Esta migração transforma uma aplicação multi-página baseada em Streamlit em uma aplicação web reativa moderna baseada em componentes, mantendo toda a lógica de negócio existente e modelos de dados.

### 1.2. Escopo do Produto (MODIFIED FOR REFLEX)

O sistema continua sendo uma aplicação web *interna* que irá gerenciar automaticamente e otimizar alocações de salas de aula e laboratórios (ensalamento) e reservas esporádicas, mas agora implementada como:

**Aplicação Single-Page (SPA)** com Reflex:
- Interface reativa e moderna com atualização automática do estado
- Componentes reutilizáveis baseados em estado
- Roteamento baseado em estado ao invés de multi-página
- Autenticação persistente com LocalStorage/SessionStorage
- Operações assíncronas com feedback visual em tempo real

### 1.3. Definições, Acrônimos e Abreviações (UPDATED)

* **Reflex:** Framework web Python moderno para aplicações reativas
* **SPA:** Single-Page Application
* **State:** Classe centralizada que gerencia dados e lógica da aplicação
* **LocalStorage:** Persistência de dados no navegador do usuário
* **SessionStorage:** Persistência temporária durante sessão do navegador
* **Component:** Função que retorna elementos de UI reutilizáveis
* **Event Handler:** Método assíncrono que responde a interações do usuário
* **Computed Property (`@rx.var`):** Propriedade derivada recalculada automaticamente
* **Defensive Mutation:** Padrão `self.items = list(self.items)` para triggers de UI
* **Yield:** Pausa em métodos async para atualização incremental da UI

*Todos os outros termos mantidos da versão Streamlit (FUP, Sigaa, Bloco Atômico, etc.)*

### 1.4. Referências (UPDATED)

* Documento de Requisitos de Produto Original (`docs/SRS.md`)
* Reflex Architecture Document (`docs/Reflex_Architecture_Document.md`)
* Reflex Agents Guide (`docs/Reflex_Agents_guide.md`)
* Código-fonte do `SigaaScheduleParser` (referência para lógica de parsing de horário).

### 1.5. Visão Geral do Documento (UPDATED)

Este documento mantém a estrutura da versão original mas atualiza todos os requisitos para o framework Reflex:

* **Seção 1 (Introdução):** Descreve propósito, escopo e visão geral da migração
* **Seção 2 (Descrição Geral):** Atualiza contexto para SPA Reflex
* **Seção 3 (Requisitos Específicos):** Mapeia todos os RF/RNF para Reflex patterns

---

## 2. Descrição Geral (UPDATED FOR REFLEX)

### 2.1. Perspectiva do Produto

O sistema permanece como "módulo de otimização" dependente do Sistema de Oferta, mas agora implementado como uma **SPA Reflex** moderna. Benefícios da migração:

**Melhorias de Arquitetura:**
- **Estado Reativo:** UI = f(State) com atualizações automáticas
- **Componentes Reutilizáveis:** Composição baseada em funções puras
- **Performance:** Computed properties e lazy loading
- **Experiência do Usuário:** Feedback visual em tempo real, estados de loading
- **Manutenibilidade:** Separação clara entre estado, componentes e lógica de negócio

### 2.2. Funções do Produto (Mantidas com Reflex Implementation)

1. **Gestão de Inventário de Espaços (Modal-based CRUD)**
2. **Gestão de Tipos de Sala (Component-based CRUD)**
3. **Gestão de Blocos de Horário (Sigaa) - Preserved**
4. **Gestão de Características de Salas (N:N with Real-time Updates)**
5. **Gestão de Professores e Preferências (Reactive Forms)**
6. **Sincronização de Demanda (Async API Integration)**
7. **Gestão de Regras de Alocação (Dynamic Rule Engine)**
8. **Motor de Alocação (Async Operations with Progress)**
9. **Edição Manual (Interactive Allocation Interface)**
10. **Gestão de Reservas Esporádicas (Calendar Components)**
11. **Visualização Unificada (Reactive Dashboard)**
12. **Administração de Usuários (Persistent Auth)**
13. **Relatórios (PDF/Excel Export)**
14. **Busca e Filtros (Real-time)**
15. **Feedback do Sistema (Toast Notifications)**

### 2.3. Características dos Usuários (UPDATED)

| Perfil                                     | Descrição                              | Nível de Acesso                                 | Reflex Capabilities                                                                               |
| :----------------------------------------- | :------------------------------------- | :---------------------------------------------- | :------------------------------------------------------------------------------------------------ |
| **Administrador** (Técnico-Administrativo) | Usuário principal com acesso total     | Acesso total + extra features                   | Toutes les opérations avec feedback visual en temps réel, formulaires validés côté client/serveur |
| **Usuário Padrão** (Professor, Servidor)   | Acesso de consulta + reservas próprias | Leitura + Criação/Gestão Própria + Preferências | Interface réactive avec mises à jour automatiques, formulaires avec validation                    |
| **Visitante** (Aluno, Comunidade)          | Acesso público                         | Acesso apenas à consulta pública                | Application web réactive avec navigation fluide                                                   |

### 2.4. Restrições Gerais (UPDATED FOR REFLEX)

* **RST-01:** O sistema deve ser desenvolvido em **Python**.
* **RST-02:** O framework web deve ser **Reflex v0.8.19**.
* **RST-03:** O banco de dados deve ser **SQLite3**.
* **RST-04:** A autenticação deve usar **LocalStorage/SessionStorage** para persistência.
* **RST-05:** A implantação deve ser **self-hosting** em servidores da FUP/UnB.
* **RST-06:** A interface deve ser responsiva e compatível com browsers modernos.
* **RST-07:** O sistema deve operar internamente com o **modelo de blocos de horário atômicos** (ex: `M1`, `M2`) do Sigaa.
* **RST-08 (NEW):** Todos os componentes devem seguir os patterns de Estado defensivo da Reflex Agents Guide.
* **RST-09 (NEW):** Todas as operações >100ms devem ter indicadores visuais de loading.
* **RST-10 (NEW):** Dados derivados devem usar computed properties (`@rx.var`).

### 2.5. Suposições e Dependências

*Mantidas da versão original* + Novas suposições:

* **SUP-02 (NEW):** Os usuários devem ter browsers modernos com suporte a JavaScript (ES2020+).
* **SUP-03 (NEW):** A aplicação será servida via HTTPS com configuração adequada de CORS.
* **SUP-04 (NEW):** LocalStorage deve estar disponível e habilitado no navegador.

---

## 3. Requisitos Específicos (UPDATED FOR REFLEX)

### 3.1. Requisitos de Interface Externa

#### 3.1.1. Interfaces de Usuário (Reflex SPA)

* **UI-01:** A interface deve ser uma **SPA responsiva** baseada em componentes Reflex.
* **UI-02:** A navegação principal deve ser baseada em **estado global** (não multi-página).
* **UI-03:** O sistema deve ser responsivo e adaptar-se usando **breakpoints responsivos** do Reflex.
* **UI-04:** Deve haver **feedback visual em tempo real** através de toast notifications e estados de loading.
* **UI-05 (NEW):** Componentes devem ser **reativos** - mudanças de estado geram atualizações automáticas da UI.
* **UI-06 (NEW):** Formulários devem ter **validação client-side** com feedback imediato.
* **UI-07 (NEW):** Listas longas devem usar **paginação lazy loading** para performance.

#### 3.1.3. Interfaces de Software (API) - UPDATED

* **API-01:** Consumir API do Sistema de Oferta (mantido).
* **API-02:** Autenticação Bearer Token (mantido).
* **API-03:** Mapeamento de campos (mantido).
* **API-04 (NEW):** Todas as chamadas API devem ser **async** com indicadores de loading.
* **API-05 (NEW):** Erros de rede devem gerar feedback visual adequado.

#### 3.1.4. Interfaces de Comunicação

* A aplicação deve ser servida via **HTTPS** (configurado no proxy reverso/NGINX).
* **COM-01 (NEW):** Reflex gerencia automaticamente WebSocket connections para atualizações de estado.

### 3.2. Requisitos Funcionais (RF) - UPDATED FOR REFLEX PATTERNS

#### RF-001: Gerenciamento de Autenticação e Perfil (TRANSFORMED)

* **RF-001.1:** O sistema deve ter componente de login reativo.
* **RF-001.2:** Deve usar LocalStorage para persistência de sessão.
* **RF-001.3:** Deve diferenciar admin vs usuário padrão via computed property.
* **RF-001.4 (Admin):** Acesso total com componentes protegidos condicionalmente.
* **RF-001.5 (Usuário Padrão):** Acesso de consulta + reservas próprias via computed properties.

#### RF-002: Gestão de Inventário de Espaços (MODAL-BASED CRUD)

* **RF-002.1 (Admin):** Deve permitir CRUD via **modais reativos** com validação real-time.
* **RF-002.2 (Admin):** Deve permitir CRUD de Salas com relacionamento via dropdowns populados dinamicamente.
* **RF-002.3 (Admin):** Ao criar/editar Sala, deve ter seleção visual de Tipo de Sala.
* **RF-002.4 (NEW):** Operações devem ser **async** com feedback de loading e toast notifications.
* **RF-002.5 (NEW):** Listas devem usar **computed properties** para filtros e ordenação automática.

#### RF-002.A: Gestão de Tipos de Sala (COMPONENT-BASED CRUD)

* **RF-002.A.1 (Admin):** Interface baseada em **componentes reutilizáveis**.
* **RF-002.A.2 (Admin):** CRUD com validação em tempo real e feedback visual.
* **RF-002.A.3:** Deve impedir exclusão se houver relacionamentos ativos (via computed property).
* **RF-002.A.4:** Inicialização via seed database (mantido).

#### RF-003: Gestão de Características de Salas (REACTIVE N:N)

* **RF-003.1 (Admin):** Características gerenciadas via **interface N:N reativa**.
* **RF-003.2 (Admin):** Associação/desassociação visual com checkboxes e auto-save.
* **RF-003.3 (Admin):** Inclusão dinâmica de características via formulario inline.
* **RF-003.4 (NEW):** Mudanças refletem **imediatamente** na UI via estado reativo.

#### RF-003.A: Gestão de Professores e Preferências (REACTIVE FORMS)

* **RF-003.A.1 (Admin):** CRUD via **formulários reativos** com validação client-side.
* **RF-003.A.2 (Admin):** Vinculação a usuários via dropdown populado dinamicamente.
* **RF-003.A.3 (Admin):** Preferências gerenciadas via interface N:N reativa.
* **RF-003.A.4 (Usuário Padrão):** Auto-gerenciamento de preferências próprias via estado separado.

#### RF-004: Importação de Demanda (ASYNC INTEGRATION)

* **RF-004.1 (Admin):** Interface para configuração de semestre via componente dedicado.
* **RF-004.2 (Admin):** Botão que dispara **operação async** com progresso visual.
* **RF-004.3:** Consumo da API com tratamento de erros e indicadores de loading.
* **RF-004.4:** Detecção de disciplinas não alocáveis (mantido).

#### RF-005: Gestão de Regras de Alocação (DYNAMIC RULE INTERFACE)

* **RF-005.1 (Admin):** Regras criadas via **formulário reativo** com preview em tempo real.
* **RF-005.2 (Admin):** Regras dinâmicas com interface visual intuitiva.
* **RF-005.3 (NEW):** Validação de conflitos de regras via computed properties.

#### RF-006: Execução do Motor de Alocação (ASYNC WITH PROGRESS)

* **RF-006.1 (Admin):** Execução via botão async com indicador de progresso detalhado.
* **RF-006.2:** Parsing de horário (mantido - lógica de negócio preservada).
* **RF-006.3:** Lookup de professor (mantido).
* **RF-006.4:** Processamento de restrições duras (lógica preservada).
* **RF-006.5:** Alocação por regras suaves com scoring (lógica preservada).
* **RF-006.6:** Algoritmo de frequência usando dados históricos (preservado).
* **RF-006.7:** Salvamento por bloco atômico (preservado).
* **RF-006.8 (NEW):** Progresso reportado via **computed properties** e updates em tempo real.

#### RF-007: Visualização do Ensalamento (REACTIVE DASHBOARD)

* **RF-007.1 (Consolidada):** **Dashboard unificado** mostrando classes + reservas em tempo real.
* **RF-007.2:** Combinação de blocos consecutivos (lógica preservada).
* **RF-007.3:** Vistas filtráveis com **computed properties** para agregação automática.
* **RF-007.4 (NEW):** Atualizações automáticas quando dados mudam.

#### RF-008: Ajuste Manual do Ensalamento (INTERACTIVE INTERFACE)

* **RF-008.1 (Admin):** Interface visual para trocas com **validação em tempo real**.
* **RF-008.2:** Verificação de conflitos automática via computed properties.
* **RF-008.3:** Alertas para violações de regras (preservado).

#### RF-009: Geração de Relatórios (EXPORT WITH PROGRESS)

* **RF-009.1 (Todos os Usuários):** Export PDF/Excel via operações async com progresso.
* **RF-009.2:** Relatório PDF por sala (lógica preservada).
* **RF-009.3:** Visualização simplificada (modo público) com navegação fluida.

#### RF-010: Busca e Filtro (REAL-TIME INTERACTIVE)

* **RF-010.1 (Todos os Usuários):** **Busca debounced** com resultados atualizando em tempo real.
* **RF-010.2:** Busca por múltiplos campos com **computed properties** filtrando dinamicamente.
* **RF-010.3 (NEW):** Interface responsiva com indicadores de "digitando...".

#### RF-011: Gestão de Reservas Esporádicas (CALENDAR COMPONENTS)

* **RF-011.1 (Usuário Logado):** Interface baseada em **componentes de calendário reativos**.
* **RF-011.2 (UI de Blocos):** Seleção de datas/horários via **interface visual intuitiva**.
* **RF-011.3:** Verificação de conflitos **em tempo real** via computed properties.
* **RF-011.4:** Validação com feedback imediato e prevenção de double-submit.
* **RF-011.5:** Gestão própria vs global baseada em permissões.
* **RF-011.6:** Reserva por bloco atômico (preservado).
* **RF-011.7:** Sistema de aprovação opcional (futuro).

#### RF-012 (NEW): Sistema de Feedback Visual

* **RF-012.1:** Todas as operações devem gerar **toast notifications** para sucesso/erro.
* **RF-012.2:** Operações longas devem mostrar **progress indicators**.
* **RF-012.3:** Estados de erro devem ser **recuperáveis** com opções de retry.
* **RF-012.4:** Alterações pendentes devem ser indicadas visualmente.

### 3.3. Requisitos Não Funcionais (RNF) - UPDATED FOR REFLEX

* **RNF-001 (Performance - UPDATED):**
    * RNF-001.1: Importação da API deve ser concluída em menos de 5 minutos (mantido).
    * RNF-001.2: Motor de alocação deve ser concluída em < 10 minutos (mantido).
    * RNF-001.3: Consultas devem ser (< 3 segundos) com **loading states** durante espera.
    * RNF-001.4: SQLite concurrency adequado para aplicação SPA moderna.
    * **RNF-001.5 (NEW):** UI deve ser **responsiva** (<100ms para interações locais).
    * **RNF-001.6 (NEW):** Computations pesadas devem usar **lazy evaluation** via computed vars.

* **RNF-002 (Usabilidade - ENHANCED):**
    * RNF-002.1: Interface deve ser **intuitiva** com feedback visual constante.
    * RNF-002.2: **Progressive enhancement** - funciona sem JavaScript mas melhor com.
    * RNF-002.3: **Accessibility** - navegação por teclado, readers de tela compatíveis.

* **RNF-003 (Confiabilidade - PRESERVED WITH ENHANCEMENTS):**
    * RNF-003.1: Integridade garantida pelo modelo de bloco atômico (mantido).
    * **RNF-003.2 (NEW):** Estado local nunca deve ser perdido via **defensive mutation**.
    * **RNF-003.3 (NEW):** Erros devem ser **gracefully handled** com recovery options.

* **RNF-004 (Segurança - ENHANCED):**
    * RNF-004.1: Senhas usando hash bcrypt (mantido).
    * RNF-004.2: Tokens seguros com LocalStorage restrictions (enhanced).
    * **RNF-004.3 (NEW):** Input sanitization usando bleach para XSS prevention.
    * **RNF-004.4 (NEW):** Rate limiting para operações sensíveis.

* **RNF-005 (Manutenibilidade - IMPROVED):**
    * RNF-005.1: Código seguindo padrões Reflex da Agents Guide.
    * RNF-005.2: Separação clara: Components ↔ States ↔ Services ↔ Database.
    * **RNF-005.3 (NEW):** Componentes reutilizáveis seguindo princípio DRY.
    * **RNF-005.4 (NEW):** Estado organizado por preocupação em arquivos separados.

* **RNF-006 (Compatibilidade - UPDATED):**
    * RNF-006.1: Browsers modernos (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+).
    * RNF-006.2: **PWA capabilities** para offline access futuro.
    * RNF-006.3: **Mobile-first responsive design**.

### 3.4. Requisitos de Banco de Dados (UNCHANGED)

*Todos os requisitos de BD mantidos da versão original.*
* **NOTA:** A migração para Reflex não afeta o schema do banco de dados - apenas a forma como é acessado.

---

## 4. Reflex-Specific Implementation Requirements

### 4.1. State Management Requirements

* **STATE-01:** Todos os dados mutable devem usar **defensive reassignment patterns**.
* **STATE-02:** Propriedades derivadas devem usar **@rx.var computed properties**.
* **STATE-03:** Global state deve ser usado para dados compartilhados entre páginas.
* **STATE-04:** Local state deve ser usado para dados temporários de formulários.
* **STATE-05:** Persistência deve usar LocalStorage para dados críticos, SessionStorage para temporários.

### 4.2. Component Architecture Requirements

* **COMP-01:** Componentes devem ser **funções puras** retornando rx.Component.
* **COMP-02:** Componentes complexos devem ser **quebrados em sub-componentes menores**.
* **COMP-03:** Props devem ser **type-hinted** e opcionalmente validadas.
* **COMP-04:** Componentes de layout devem usar **responsive breakpoints**.
* **COMP-05:** Renderização condicional deve usar **rx.cond** ao invés de Python if/else.

### 4.3. Event Handling Requirements

* **EVENT-01:** Handlers devem ser **async** para operações >100ms.
* **EVENT-02:** Operações blocking devem usar **asyncio.to_thread**.
* **EVENT-03:** Feedback deve usar **yield** para atualizações progressivas.
* **EVENT-04:** Erros devem ser **caught** e apresentados via toast notifications.
* **EVENT-05:** Loading states devem prevenir **consecutive operations**.

### 4.4. Navigation & Routing Requirements

* **NAV-01:** Routing deve ser **state-based** não file-based.
* **NAV-02:** Navegação deve atualizar estado global **atomically**.
* **NAV-03:** Breadcrumbs devem ser gerenciados via **computed properties**.
* **NAV-04:** Deep linking deve ser suportado via **router state**.

### 4.5. Performance Requirements

* **PERF-01:** Listas >100 items devem usar **pagination** ou **virtual scrolling**.
* **PERF-02:** Expensive computations devem usar **computed vars com memoization**.
* **PERF-03:** Network requests devem usar **loading indicators**.
* **PERF-04:** Bundle size deve ser **otimizado** via lazy loading de componentes.

---

## 5. Migration Verification Checklist

### 5.1. Business Logic Preservation
- [ ] Allocation engine funciona identicamente
- [ ] Conflict detection rules preserved
- [ ] Professor preferences applied correctly
- [ ] Reservation recurrence patterns work
- [ ] Scoring algorithm produces same results
- [ ] PDF/Excel export formats maintained

### 5.2. UI/UX Improvements
- [ ] Real-time feedback for all operations
- [ ] Loading states prevent user confusion
- [ ] Form validation works client-side
- [ ] Error recovery options available
- [ ] Mobile responsiveness improved
- [ ] Accessibility enhanced

### 5.3. Technical Excellence
- [ ] Defensive mutation patterns used everywhere
- [ ] Computed properties optimize performance
- [ ] Async operations properly handled
- [ ] State properly scoped (global vs local)
- [ ] Persistence works across sessions
- [ ] Error boundaries prevent crashes

### 5.4. Production Readiness
- [ ] No console errors in production
- [ ] Bundle size within reasonable limits
- [ ] Memory leaks prevented
- [ ] Offline/slow network handling
- [ ] Security headers configured
- [ ] HTTPS properly configured

Este SRS garante que a migração para Reflex preserva toda a funcionalidade crítica enquanto adiciona capacidades modernas de UI reativa e experiência do usuário aprimorada.
