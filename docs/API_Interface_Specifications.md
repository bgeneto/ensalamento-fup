# API Interface Specifications
# Sistema de Ensalamento FUP/UnB - Reflex Frontend-Backend Integration

**Version:** 1.0 (Reflex Migration)
**Date:** November 14, 2025

---

## Executive Summary

This document defines the API interfaces for the **Sistema de Ensalamento FUP/UnB** Reflex migration. While the current Streamlit application has minimal API separation (everything happens in the same Python process), the Reflex migration requires clear boundaries between frontend state management and backend services to ensure proper separation of concerns, async operation handling, and scalable architecture.

## API Design Principles

### Separation of Concerns
- **Frontend (Reflex States):** UI state management, user interactions, real-time updates
- **Backend (Python Services):** Business logic, database operations, external API integrations
- **Clear Boundaries:** Async communication via well-defined interfaces

### Async-First Architecture
- All operations >100ms are async with proper loading states
- Progressive UI updates using `yield` in state methods
- Error handling with retry capabilities and user feedback

### State Synchronization
- Frontend state reflects backend truth via reactive updates
- Defensive mutation patterns prevent UI inconsistency
- Computed properties automatically recalculate derived data

---

## External API Interfaces (PRESERVED)

### Sistema de Oferta Integration

**Base URL:** `${SISTEMA_OFERTA_API_URL}`
**Authentication:** Bearer Token `${SISTEMA_OFERTA_API_TOKEN}`

#### GET /semesters/{semester_id}

**Purpose:** Import course demand data from external system
**Frontend Integration:** Called from `SemesterState.load_demand()`

```python
# core/states/semester_state.py
class SemesterState(rx.State):
    loading_demand: bool = False
    demand_data: list[dict] = []
    import_progress: int = 0

    async def load_demand(self, semester_id: int):
        """Import demand with progress updates"""
        if self.loading_demand:
            return rx.toast.info("Import already in progress")

        self.loading_demand = True
        self.import_progress = 0
        yield

        try:
            # Progress update 1: Starting import
            self.import_progress = 10
            yield rx.toast.info("Starting demand import...")

            # Call service layer
            result = await asyncio.to_thread(
                DemandImportService.import_from_api,
                semester_id
            )

            # Progress updates for large imports
            self.import_progress = 50
            yield

            # Process and save data
            await self._process_imported_data(result)

            self.import_progress = 100
            yield rx.toast.success(f"Imported {len(result)} courses successfully")

        except Exception as e:
            yield rx.toast.error(f"Import failed: {e}")

        finally:
            self.loading_demand = False
            self.import_progress = 0
```

**Response Format:**
```json
[
  {
    "codigo_disciplina": "MAT123",
    "nome_disciplina": "Mathematics I",
    "professores_disciplina": "Dr. João Silva, Dra. Maria Santos",
    "turma_disciplina": "A",
    "vagas_disciplina": 45,
    "horario_sigaa_bruto": "24T12 26T34"
  }
]
```

### Brevo Email Integration (Optional)

**Base URL:** `${BREVO_API_URL}`
**Authentication:** `${BREVO_API_KEY}`

#### POST /smtp/email

**Purpose:** Send notifications for allocation results or reservation confirmations

```python
# Only used for future notification features
# Interface: EmailService.send_allocation_notification(allocation_results)
```

---

## Internal Service Layer Interfaces

### Allocation Service Interface

**Purpose:** Handle complex allocation operations with progress reporting

#### AllocationService.execute_allocation(semester_id: int) -> Dict

**Frontend Usage:** `AllocationState.run_autonomous_allocation()`

```python
class AllocationService:
    @staticmethod
    async def execute_allocation(semester_id: int, progress_callback=None) -> Dict[str, Any]:
        """
        Execute full allocation process with progress updates

        Args:
            semester_id: Semester to allocate
            progress_callback: Optional async function to receive progress updates

        Returns:
            Dict with results and statistics
        """
        service = OptimizedAutonomousAllocationService()

        # If progress callback provided, setup progress reporting
        if progress_callback:
            # This would require modifying the allocation service to accept callbacks
            pass

        result = await asyncio.to_thread(
            service.execute_autonomous_allocation,
            semester_id
        )

        return result
```

**Result Format:**
```python
{
    "success": True,
    "allocations_completed": 45,
    "execution_time": 127.83,
    "phase1_hard_rules": {
        "conflicts": 2,
        "rules_applied": 18
    },
    "phase3_atomic_allocation": {
        "conflicts": 0,
        "iterations": 3
    },
    "pdf_report": b"<pdf_bytes>",  # Optional
    "pdf_filename": "allocation_2025_1.pdf"
}
```

### Room Scoring Service Interface

#### RoomScoringService.calculate_room_scores(demand_id: int, available_rooms: List[Dict]) -> List[Dict]

**Purpose:** Calculate compatibility scores for room allocation suggestions

```python
# core/services/room_scoring_service.py
class RoomScoringService:
    @staticmethod
    def calculate_room_scores(demand_id: int, available_rooms: List[Dict]) -> List[Dict]:
        """
        Calculate scoring for room suggestions

        Returns list of rooms with scores:
        [
            {
                "room_id": 1,
                "room_name": "A1-09",
                "score": 8.5,
                "reasons": ["Hard rule match: Chemistry lab", "Professor prefers this room"],
                "capacity_match": True,
                "characteristics_match": ["Projector", "Sink"]
            }
        ]
        """
        # ... complex scoring logic preserved from Streamlit version
```

### Reservation Service Interface

**Purpose:** Handle reservation creation with conflict checking

#### ReservationService.create_reservation(reservation_data: Dict) -> Dict

```python
# core/services/reservation_service.py
class ReservationService:
    @staticmethod
    async def create_reservation(reservation_data: Dict) -> Dict[str, Any]:
        """
        Create reservation with conflict checking

        Args:
            reservation_data: {
                "sala_id": 1,
                "username_solicitante": "john@unb.br",
                "titulo_evento": "Research Meeting",
                "data_reserva": "2025-11-15",
                "codigo_bloco": "M2",
                "recurrence_rule": {"tipo": "unica"}  # or complex recurrence
            }

        Returns:
            {"success": bool, "reservation_id": int, "conflicts": [...]}
        """
        # Create parent reservation
        parent = await ReservaEvento.create_from_data(reservation_data)

        # Generate occurrences based on recurrence
        occurrences = await parent.generate_occurrences()

        # Check conflicts for each occurrence
        conflicts = []
        for occurrence in occurrences:
            conflict = await occurrence.check_conflicts()
            if conflict:
                conflicts.append(conflict)

        return {
            "success": len(conflicts) == 0,
            "reservation_id": parent.id,
            "conflicts": conflicts
        }
```

---

## State-to-Service Integration Patterns

### Async Service Wrapper Pattern

**Purpose:** Cleanly integrate blocking service operations with async Reflex state

```python
# core/integrations/service_integration.py
class ServiceIntegration:
    """Handles async wrapping of service layer operations"""

    @staticmethod
    async def execute_with_progress(
        operation: Callable,
        progress_state: rx.State,
        progress_field: str = "progress",
        *args,
        **kwargs
    ):
        """
        Execute operation with progress updates

        Args:
            operation: Blocking function to execute
            progress_state: State object to update
            progress_field: Field name for progress in state
        """

        def progress_callback(current: int, total: int):
            """Callback to update progress - runs in service thread"""
            # This needs careful implementation to cross thread boundaries
            # May require queue-based approach for progress updates
            pass

        # Execute operation in thread pool
        result = await asyncio.to_thread(operation, *args, **kwargs)

        # Update state
        if hasattr(progress_state, progress_field):
            setattr(progress_state, progress_field, 100)

        return result

    @staticmethod
    async def execute_with_retry(
        operation: Callable,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        *args,
        **kwargs
    ):
        """Execute with automatic retry on failure"""
        last_error = None

        for attempt in range(max_retries):
            try:
                return await asyncio.to_thread(operation, *args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    continue

        raise last_error
```

### Progress Reporting Pattern

**Purpose:** Provide real-time progress for long-running operations

```python
# core/states/progress_state.py
class ProgressState(rx.State):
    """Manages progress reporting for long operations"""

    current_operation: str = ""
    progress_percentage: int = 0
    operation_steps: list[str] = []
    current_step: int = 0

    @rx.var
    def progress_text(self) -> str:
        if not self.operation_steps:
            return f"{self.current_operation}: {self.progress_percentage}%"

        current_step_text = self.operation_steps[self.current_step] if self.current_step < len(self.operation_steps) else "Complete"
        return f"{self.current_step + 1}/{len(self.operation_steps)}: {current_step_text}"

    @rx.var
    def is_complete(self) -> bool:
        return self.progress_percentage >= 100
```

**Usage in Allocation State:**
```python
class AllocationState(rx.State):
    """Enhanced allocation state with progress"""

    progress_state: ProgressState

    async def run_allocation_with_progress(self, semester_id: int):
        # Setup progress
        self.progress_state.current_operation = "Running Allocation"
        self.progress_state.operation_steps = [
            "Parsing course demands",
            "Loading room constraints",
            "Applying allocation rules",
            "Resolving conflicts",
            "Generating reports"
        ]
        self.progress_state.current_step = 0
        self.progress_state.progress_percentage = 0
        yield

        try:
            # Progress callback function
            def update_progress(step_name: str, percentage: int):
                """Called from allocation service"""
                self.progress_state.current_step = self.progress_state.operation_steps.index(step_name)
                self.progress_state.progress_percentage = percentage

            # Execute allocation
            result = await AllocationService.execute_allocation(
                semester_id,
                progress_callback=update_progress
            )

            yield rx.toast.success("Allocation completed!")

        except Exception as e:
            yield rx.toast.error(f"Allocation failed: {e}")

        finally:
            self.progress_state.progress_percentage = 100
```

---

## Data Transfer Objects (DTOs)

### Request/Response DTOs

**Purpose:** Type-safe data exchange between frontend states and backend services

```python
# core/dtos/allocation_dtos.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class AllocationRequestDTO(BaseModel):
    semester_id: int
    include_hard_rules: bool = True
    include_soft_preferences: bool = True
    max_iterations: int = 100

class AllocationResultDTO(BaseModel):
    success: bool
    allocations_completed: int
    execution_time_seconds: float
    conflicts_found: int
    pdf_report: Optional[bytes] = None
    pdf_filename: Optional[str] = None
    detailed_results: Dict[str, Any]

class RoomScoreDTO(BaseModel):
    room_id: int
    room_name: str
    capacity: int
    building_name: str
    score: float
    reasons: List[str]
    capacity_match: bool
    characteristics_match: List[str]

class ReservationRequestDTO(BaseModel):
    sala_id: int
    username_solicitante: str
    titulo_evento: str
    data_reserva: str  # ISO date string
    codigo_bloco: str
    recurrence_rule: Dict[str, Any]
    solicitante_name: Optional[str] = None
    responsavel_name: Optional[str] = None

class ReservationResponseDTO(BaseModel):
    success: bool
    reservation_id: Optional[int]
    conflicts: List[Dict[str, Any]] = []
    created_occurrences: int = 0
```

### DTO Conversion Patterns

**Frontend to Backend Conversion:**
```python
# core/converters/dto_converters.py
class DTOConverter:
    @staticmethod
    def allocation_request_to_service_params(dto: AllocationRequestDTO) -> Dict[str, Any]:
        """Convert DTO to service-compatible parameters"""
        return {
            "semester_id": dto.semester_id,
            "hard_rules_enabled": dto.include_hard_rules,
            "soft_preferences_enabled": dto.include_soft_preferences,
            "max_iterations": dto.max_iterations,
        }

    @staticmethod
    def service_result_to_allocation_dto(result: Dict[str, Any]) -> AllocationResultDTO:
        """Convert service result to typed DTO"""
        return AllocationResultDTO(
            success=result.get("success", False),
            allocations_completed=result.get("allocations_completed", 0),
            execution_time_seconds=result.get("execution_time", 0.0),
            conflicts_found=sum([
                result.get("phase1_hard_rules", {}).get("conflicts", 0),
                result.get("phase3_atomic_allocation", {}).get("conflicts", 0)
            ]),
            pdf_report=result.get("pdf_report"),
            pdf_filename=result.get("pdf_filename"),
            detailed_results=result
        )
```

---

## Error Handling Interfaces

### Standardized Error Response Format

```python
# core/dtos/error_dtos.py
class ErrorResponseDTO(BaseModel):
    success: bool = False
    error_code: str
    error_message: str
    error_details: Optional[Dict[str, Any]] = None
    retryable: bool = False
    suggested_action: Optional[str] = None
```

### Error Mapping in State Methods

```python
class AllocationState(rx.State):
    async def run_allocation(self):
        try:
            result = await AllocationService.execute_allocation(self.semester_id)

            if not result.success:
                # Convert service error to user-friendly message
                error_dto = DTOConverter.service_error_to_dto(result.error)
                yield rx.toast.error(error_dto.error_message)

                if error_dto.retryable:
                    yield rx.toast.info(error_dto.suggested_action or "Please try again")

                return

            # Success handling
            yield rx.toast.success(f"Allocation completed: {result.allocations_completed} placements")

        except Exception as e:
            # Unexpected errors
            yield rx.toast.error(f"Unexpected error: {str(e)}")
            logging.error("Allocation failed", exc_info=True)
```

---

## Caching and Performance Interfaces

### Frontend Caching Strategy

**Purpose:** Reduce redundant service calls while maintaining data freshness

```python
# core/states/cache_state.py
class CacheState(rx.State):
    """Manages frontend caching of expensive data"""

    room_data_cache: Dict[int, Dict] = {}
    cache_timestamps: Dict[str, datetime] = {}

    CACHE_TTL_SECONDS = 300  # 5 minutes

    def is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still fresh"""
        if cache_key not in self.cache_timestamps:
            return False

        age = datetime.now() - self.cache_timestamps[cache_key]
        return age.total_seconds() < self.CACHE_TTL_SECONDS

    def cache_room_data(self, semester_id: int, room_data: List[Dict]):
        """Cache room data for semester"""
        cache_key = f"rooms_{semester_id}"
        self.room_data_cache[semester_id] = room_data
        self.cache_timestamps[cache_key] = datetime.now()

    async def get_room_data(self, semester_id: int) -> List[Dict]:
        """Get room data with caching"""
        cache_key = f"rooms_{semester_id}"

        if self.is_cache_valid(cache_key):
            return self.room_data_cache.get(semester_id, [])

        # Fetch fresh data
        room_data = await asyncio.to_thread(
            RoomService.get_rooms_for_semester,
            semester_id
        )

        # Cache it
        self.cache_room_data(semester_id, room_data)

        return room_data
```

---

## Security Interfaces

### Authentication Token Management

```python
# core/states/auth_state.py (security additions)
class AuthState(rx.State):
    # ... existing fields ...

    # Secure token storage (server-side only - never sent to client)
    auth_token: str = rx.SessionStorage(default="", name="auth_token_secure")

    # CSRF protection
    csrf_token: str = rx.SessionStorage(default="", name="csrf_token")

    def generate_csrf_token(self):
        """Generate new CSRF token for state-changing operations"""
        import secrets
        self.csrf_token = secrets.token_urlsafe(32)

    async def make_authenticated_request(self, endpoint: str, method: str = "GET", data: Dict = None):
        """Make authenticated API request with CSRF protection"""
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "X-CSRF-Token": self.csrf_token
        }

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"/api/{endpoint}",
                headers=headers,
                json=data
            )

            if response.status_code == 401:
                # Token expired - trigger re-auth
                self.logout()
                return None

            return response.json()
```

---

## Development and Testing Interfaces

### Mock Service Layer for Testing

```python
# tests/mocks/service_mocks.py
class MockAllocationService:
    async def execute_allocation(self, semester_id: int) -> Dict[str, Any]:
        """Mock implementation for testing"""
        await asyncio.sleep(0.1)  # Simulate async operation
        return {
            "success": True,
            "allocations_completed": 42,
            "execution_time": 2.5,
            "phase1_hard_rules": {"conflicts": 0, "rules_applied": 15},
            "phase3_atomic_allocation": {"conflicts": 1, "iterations": 2}
        }

class MockReservationService:
    async def create_reservation(self, data: Dict) -> Dict[str, Any]:
        """Mock reservation creation"""
        await asyncio.sleep(0.05)  # Simulate processing
        return {
            "success": True,
            "reservation_id": 123,
            "conflicts": []
        }
```

### Interface Testing Utilities

```python
# tests/test_interfaces.py
import pytest
from core.dtos.allocation_dtos import AllocationRequestDTO

def test_allocation_dto_validation():
    """Test DTO validation"""
    # Valid request
    dto = AllocationRequestDTO(semester_id=20251)
    assert dto.semester_id == 20251

    # Invalid request - should raise ValidationError
    with pytest.raises(ValidationError):
        AllocationRequestDTO(semester_id="invalid")

async def test_service_integration():
    """Test service integration with mock"""
    with patch('core.services.allocation_service.AllocationService') as mock_service:
        mock_service.execute_allocation.return_value = {"success": True, "allocations_completed": 10}

        state = AllocationState()
        await state.run_autonomous_allocation(20251)

        assert state.last_result["allocations_completed"] == 10
```

This API specification ensures clean separation between frontend state management and backend business logic, enabling the reactive, real-time capabilities of Reflex while preserving all critical allocation and reservation functionality.
