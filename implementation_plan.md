# Implementation Plan

## Overview
Build a comprehensive room scheduling system for FUP/UnB using Streamlit that automates room allocation for semester courses and manages sporadic reservations, featuring authentication, rule-based optimization, and unified reporting.

This implementation will create a full-featured Sistema de Ensalamento that serves both administrative users for semester planning and regular users for room reservations, with a clean Brazilian Portuguese interface following all requirements from the SRS document.

## Types
Core data structures for the room scheduling system using Pydantic models and SQLAlchemy ORM.

### Pydantic Models
- **BaseModel**: Abstract base class with common fields (id, created_at, updated_at)
- **Campus**: id, nome, descricao
- **Predio**: id, nome, campus_id, campus (relationship)
- **TipoSala**: id, nome, descricao
- **Sala**: id, nome, predio_id, tipo_sala_id, capacidade, andar, tipo_assento, predio, tipo_sala, caracteristicas (relationship)
- **Caracteristica**: id, nome
- **SalaCaracteristica**: sala_id, caracteristica_id, sala, caracteristica (relationships)
- **DiaSemana**: id_sigaa, nome (pré-populado)
- **HorarioBloco**: codigo_bloco, turno, horario_inicio, horario_fim (pré-populado)
- **Semestre**: id, nome, status
- **Demanda**: id, semestre_id, codigo_disciplina, nome_disciplina, professores_disciplina, turma_disciplina, vagas_disciplina, horario_sigaa_bruto, nivel_disciplina, semestre
- **Regra**: id, descricao, tipo_regra, config_json, prioridade
- **AlocacaoSemestral**: id, demanda_id, sala_id, dia_semana_id, codigo_bloco, demanda, sala, dia_semana, horario_bloco
- **ReservaEsporadica**: id, sala_id, username_solicitante, titulo_evento, data_reserva, codigo_bloco, status, sala, solicitante, horario_bloco
- **Usuario**: username, password_hash, nome_completo, role

### Database Models (SQLAlchemy)
Corresponding SQLAlchemy models with proper relationships, foreign keys, and constraints following the schema.sql structure.

## Files
Complete file structure for the modular Streamlit application.

### New Files to Create
- **home.py**: Main entry point with navigation and public dashboard
- **database.py**: SQLAlchemy setup, database initialization, and connection management
- **models.py**: Pydantic models for data validation and API responses
- **services/auth_service.py**: Authentication wrapper for streamlit-authenticator
- **services/database_service.py**: Database CRUD operations and business logic
- **services/allocation_service.py**: Room allocation engine with rule processing
- **services/sigaa_parser_service.py**: Sigaa schedule parsing logic (based on docs/sigaa_parser.py)
- **services/api_service.py**: External API integration for semester data import
- **services/reservation_service.py**: Conflict checking and reservation management
- **services/setup_service.py**: Initial database setup and seeding
- **config.py**: Application configuration and environment variables
- **utils.py**: Helper functions and utilities
- **pages/admin/admin_dashboard.py**: Admin main dashboard
- **pages/admin/inventory.py**: Campus, building, and room management
- **pages/admin/tipos_sala.py**: Room type management
- **pages/admin/caracteristicas.py**: Room features management
- **pages/admin/semestre.py**: Semester management and API synchronization
- **pages/admin/regras.py**: Allocation rule management
- **pages/admin/alocacao.py**: Allocation execution and manual adjustments
- **pages/admin/relatorios.py**: Report generation and export
- **pages/admin/usuarios.py**: User management
- **pages/reservations/reservar.py**: Room reservation interface for users
- **pages/reservas/minhas_reservas.py**: User's reservation management
- **pages/visualizacao/grade_horarios.py**: Unified schedule visualization
- **pages/visualizacao/busca.py**: Search functionality
- **pages/visualizacao/tv_mode.py**: Simplified display for TVs/public viewing
- **data/seeds.py**: Database seeding scripts
- **data/seeds/tipos_sala.json**: Initial room types data
- **data/seeds/caracteristicas.json**: Initial room characteristics data
- **data/seeds/horarios_bloco.json**: Sigaa time blocks data
- **data/seeds/dias_semana.json**: Week days mapping data
- **tests/test_allocation.py**: Allocation engine tests
- **tests/test_sigaa_parser.py**: Sigaa parser tests
- **tests/test_reservations.py**: Reservation conflict tests

### Files to Update
- **Dockerfile**: Already configured correctly with home.py as entry point
- **requirements.txt**: Already complete with all necessary dependencies
- **compose.yaml**: Already configured for production deployment
- **.env.example**: Already complete with all environment variables

## Functions
Core application functions organized by service layer.

### Database Service Functions
- **init_database()**: Initialize database schema and foreign key support
- **create_session()**: Create database session with proper error handling
- **seed_database()**: Populate initial data (room types, characteristics, time blocks)
- **check_database_exists()**: Verify if database file exists and is valid

### Auth Service Functions
- **init_authenticator()**: Initialize streamlit-authenticator with config
- **create_initial_admin()**: Create first admin user if none exists
- **get_current_user()**: Get current authenticated user information
- **check_admin_access()**: Verify user has admin privileges
- **update_auth_config()**: Save authentication configuration changes

### Inventory Management Functions
- **CRUD operations**: create_campus, get_campus, update_campus, delete_campus (and similar for predios, salas, tipos_sala, caracteristicas)
- **get_salas_by_tipo()**: Filter rooms by type
- **get_salas_disponiveis()**: Get available rooms for specific time blocks
- **validate_sala_constraints()**: Check room capacity and feature requirements

### Semester Management Functions
- **sync_semestre_from_api()**: Import semester data from external API
- **parse_demandas()**: Process and validate imported demand data
- **get_semestre_ativo()**: Get current active semester
- **create_semestre()**: Create new semester

### Allocation Engine Functions
- **parse_horario_sigaa()**: Convert Sigaa time codes to atomic blocks
- **apply_regras_estaticas()**: Apply static allocation rules
- **apply_regras_dinamicas()**: Apply dynamic preferences and priorities
- **check_conflito_alocacao()**: Verify allocation conflicts
- **executar_alocacao()**: Main allocation algorithm
- **ajuste_manual_alocacao()**: Manual adjustment of allocations

### Reservation Service Functions
- **check_disponibilidade_sala()**: Real-time availability checking
- **create_reserva()**: Create new sporadic reservation
- **get_reservas_usuario()**: Get user's reservations
- **cancel_reserva()**: Cancel reservation with conflict checking
- **validate_reserva_constraints()**: Validate reservation requirements

### Visualization Functions
- **get_grade_horarios()**: Get unified schedule view
- **format_horario_display()**: Format time blocks for display
- **export_pdf_grade()**: Generate PDF reports
- **search_reservas_alocacoes()**: Global search functionality

### API Service Functions
- **fetch_semestre_data()**: Get data from external API
- **mock_api_data()**: Generate mock data for development
- **validate_api_response()**: Validate API response format

## Classes
Main application classes organized by responsibility.

### Database Classes
- **DatabaseManager**: Singleton for database connection management
- **BaseModel**: SQLAlchemy declarative base with common fields

### Service Classes
- **AuthService**: Wrapper for streamlit-authenticator functionality
- **AllocationEngine**: Core allocation algorithm implementation
- **SigaaParser**: Schedule parsing logic (extending docs/sigaa_parser.py)
- **ReservationValidator**: Conflict checking and validation
- **ReportGenerator**: PDF and Excel export functionality

### UI Classes
- **PageBase**: Base class for Streamlit pages with common functionality
- **DataEditor**: Enhanced Streamlit data editor with validation
- **ScheduleGrid**: Custom schedule visualization component

### Model Classes (Pydantic)
- **Request/Response Models**: For API-like internal communication
- **Validation Models**: For form validation and data integrity

## Dependencies
All dependencies are already specified in requirements.txt.

### Core Dependencies
- **streamlit**: Web framework
- **streamlit-authenticator**: Authentication
- **sqlalchemy**: Database ORM
- **pydantic**: Data validation
- **python-dotenv**: Environment configuration
- **requests**: HTTP client for API integration

### Development Dependencies
- **pytest**: Testing framework
- **black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting

## Testing
Comprehensive testing strategy for all critical components.

### Unit Tests
- **Sigaa Parser Tests**: Verify time code parsing accuracy
- **Allocation Engine Tests**: Test rule application and conflict detection
- **Reservation Conflict Tests**: Test real-time conflict checking
- **Database CRUD Tests**: Test all database operations
- **Authentication Tests**: Test user management and access control

### Integration Tests
- **API Integration Tests**: Test external data import
- **End-to-End Workflows**: Test complete user journeys
- **Database Migration Tests**: Test schema changes and data integrity

### Test Coverage
- Target 90%+ code coverage for critical business logic
- Mock external dependencies for isolated testing
- Test database operations in memory SQLite

## Implementation Order
Logical sequence to build the application incrementally.

### Phase 1: Foundation (Days 1-2)
1. **Database Setup**: Create database.py, models.py, and initialize SQLite with schema
2. **Configuration**: Setup config.py and environment variable handling
3. **Basic Services**: Implement database_service.py with basic CRUD operations
4. **Database Seeding**: Create setup_service.py and seed initial data (room types, characteristics, time blocks)
5. **Main Entry Point**: Create home.py with basic Streamlit navigation structure

### Phase 2: Authentication & Users (Days 3-4)
6. **Authentication Service**: Implement auth_service.py with streamlit-authenticator
7. **Initial Admin Setup**: Create automated admin user creation on first run
8. **User Management**: Create admin/usuarios.py page for user administration
9. **Access Control**: Implement role-based access control throughout the application

### Phase 3: Inventory Management (Days 5-6)
10. **Campus/Building Management**: Create inventory.py for campus and building CRUD
11. **Room Management**: Extend inventory.py for room CRUD with characteristics
12. **Room Types**: Create tipos_sala.py for room type management
13. **Room Characteristics**: Create caracteristicas.py for feature management
14. **Mock API Service**: Implement api_service.py with mock data for development

### Phase 4: Semester & Demand Management (Days 7-8)
15. **Semester Management**: Create semestre.py for semester administration
16. **API Integration**: Implement actual API data import functionality
17. **Demand Processing**: Parse and validate imported semester data
18. **Sigaa Parser**: Implement sigaa_parser_service.py based on docs/sigaa_parser.py

### Phase 5: Allocation Engine (Days 9-11)
19. **Rule Management**: Create regras.py for allocation rule configuration
20. **Allocation Algorithm**: Implement allocation_service.py core engine
21. **Static Rules**: Implement hard allocation rules (professor-room, discipline-room type)
22. **Dynamic Rules**: Implement soft preferences and priorities
23. **Allocation Execution**: Create alocacao.py for running allocation process
24. **Manual Adjustments**: Implement manual allocation adjustment functionality

### Phase 6: Reservations System (Days 12-13)
25. **Reservation Interface**: Create reservar.py for user reservation creation
26. **Conflict Checking**: Implement real-time availability validation
27. **My Reservations**: Create minhas_reservas.py for user reservation management
28. **Admin Reservation Management**: Extend reservation management for admins

### Phase 7: Visualization & Reporting (Days 14-15)
29. **Schedule Grid**: Create grade_horarios.py with unified schedule view
30. **Search Functionality**: Create busca.py for global search
31. **TV Mode**: Create tv_mode.py for simplified public display
32. **PDF Reports**: Implement PDF generation in relatorios.py
33. **Export Functions**: Add Excel and CSV export capabilities

### Phase 8: Testing & Polish (Days 16-17)
34. **Unit Tests**: Write comprehensive tests for all services
35. **Integration Tests**: Test complete workflows and user journeys
36. **UI Polish**: Refine user interface and add error handling
37. **Performance Optimization**: Optimize database queries and allocation algorithm
38. **Documentation**: Update inline documentation and create user guides

### Phase 9: Deployment & Finalization (Day 18)
39. **Production Testing**: Test in Docker environment
40. **Final Review**: Comprehensive testing of all features
41. **Deployment Preparation**: Final configuration and deployment checks
42. **Documentation**: Complete setup and deployment documentation

This implementation plan covers all requirements from the SRS document and creates a production-ready room scheduling system with comprehensive features for both administrative and regular users.
