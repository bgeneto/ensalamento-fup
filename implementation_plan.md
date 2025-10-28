# Implementation Plan - RF-011 Recurring Reservations Calendar

## Overview

This plan transforms RF-011 (Reservas Esporádicas) into a complete calendar-like application similar to Google Calendar/Outlook, supporting recurring reservations with a Parent/Instance design pattern while maintaining the existing `reservas_esporadicas` system unchanged.

The implementation will introduce a new dual-table design with `reservas_eventos` (parent events) and `reservas_ocorrencias` (instances), providing efficient recurrence support and conflict detection while preserving all existing functionality.

## Types

**ReservaEvento Model (Parent Table)**:
- `id`: Primary key (inherited from BaseModel)
- `sala_id`: Foreign key to rooms
- `titulo_evento`: Event title (max 255 chars)
- `username_criador`: Creator username (FK to usuarios)
- `nome_solicitante`: Requester name (optional, for external guests)
- `nome_responsavel`: Responsible person name (optional)
- `regra_recorrencia_json`: JSON recurrence rule (e.g., {"tipo": "semanal", "dias": [2, 4], "fim": "2025-12-31"})
- `status`: Event status (default "Aprovada")
- `created_at`, `updated_at`: Timestamps (inherited)

**ReservaOcorrencia Model (Instance Table)**:
- `id`: Primary key (inherited from BaseModel)
- `evento_id`: Foreign key to reservas_eventos
- `data_reserva`: Specific date (YYYY-MM-DD)
- `codigo_bloco`: Time block code (e.g., "M1", "T2")
- `status_excecao`: Optional exception status (e.g., "Cancelada")

## Files

**New Files to Create**:
- `src/services/reserva_evento_service.py`: Business logic for recurring reservations
- `src/repositories/reserva_evento.py`: Repository for ReservaEvento
- `src/repositories/reserva_ocorrencia.py`: Repository for ReservaOcorrencia
- `src/utils/recurrence_calculator.py`: Utility for expanding recurrence rules
- `tests/test_reserva_evento.py`: Unit tests for new functionality

**Existing Files to Modify**:
- `src/models/allocation.py`: Add ReservaEvento and ReservaOcorrencia ORM models
- `src/schemas/allocation.py`: Add corresponding Pydantic schemas
- `src/repositories/__init__.py`: Export new repositories
- `src/config/database.py`: Import new models
- `pages/9_📅_Reservas.py`: Complete UI implementation with calendar view and forms
- `tests/conftest.py`: Add fixtures for new models

## Implementation Order

**Phase 1: Foundation (Backend Core)**
1. Add ReservaEvento and ReservaOcorrencia ORM models to `src/models/allocation.py`
2. Create corresponding Pydantic schemas in `src/schemas/allocation.py`
3. Implement ReservaEventoRepository with basic CRUD operations
4. Implement ReservaOcorrenciaRepository with bulk operations
5. Update database configuration imports

**Phase 2: Business Logic**
6. Create RecurrenceCalculator utility class with all pattern support
7. Implement ReservaEventoService with creation and conflict detection
8. Add comprehensive error handling and validation
9. Write unit tests for business logic layer

**Phase 3: UI Implementation**
10. Complete pages/9_📅_Reservas.py with calendar view using AgGrid
11. Create recurrence form components (pattern selection, date pickers, block checkboxes)
12. Implement conflict detection UI with clear error messages
13. Add management interface (edit/delete recurring series)
14. Integrate with existing authentication and feedback patterns

**Phase 4: Integration & Testing**
15. Write comprehensive integration tests
16. Test conflict scenarios with existing semester allocations
17. Verify one-year limit enforcement
18. Performance testing for large recurrence series
19. User acceptance testing for all recurrence patterns

**Phase 5: Polish & Documentation**
20. Add inline documentation and type hints
21. Update user interface help text and tooltips
22. Create documentation for recurrence patterns
23. Final testing and bug fixes
