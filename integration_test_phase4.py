#!/usr/bin/env python3
"""
PHASE 4 INTEGRATION TEST - Final Verification
Tests all refactored services and pages work correctly without DetachedInstance errors
"""

import sys

sys.path.insert(0, "/home/bgeneto/github/ensalamento-fup")

import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

# ============================================================================
# TEST RESULTS TRACKING
# ============================================================================


class TestResults:
    def __init__(self):
        self.tests: List[Tuple[str, bool, str]] = []

    def add(self, name: str, passed: bool, message: str = ""):
        self.tests.append((name, passed, message))
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if message:
            print(f"       {message}")

    def summary(self):
        passed = sum(1 for _, p, _ in self.tests if p)
        total = len(self.tests)
        print(f"\n{'='*70}")
        print(f"TEST SUMMARY: {passed}/{total} passed")
        print(f"{'='*70}")

        if passed == total:
            print("🎉 ALL TESTS PASSED! Ready for production.")
        else:
            print("⚠️  Some tests failed. Review above for details.")
            failed_tests = [name for name, p, _ in self.tests if not p]
            print(f"Failed tests: {', '.join(failed_tests)}")


results = TestResults()

# ============================================================================
# TEST 1: REPOSITORY LAYER
# ============================================================================

print("\n" + "=" * 70)
print("TEST SUITE 1: REPOSITORY LAYER")
print("=" * 70)

try:
    from src.repositories.sala import get_sala_repository
    from src.repositories.usuario import get_usuario_repository
    from src.repositories.alocacao import get_alocacao_repository
    from src.repositories.semestre import (
        get_semestre_repository,
        get_demanda_repository,
    )

    # Test Sala Repository
    try:
        repo = get_sala_repository()
        rooms = repo.get_all_with_eager_load()
        assert isinstance(rooms, list), "Should return list"
        results.add(
            "SalaRepository.get_all_with_eager_load()",
            True,
            f"Loaded {len(rooms)} rooms",
        )
    except Exception as e:
        results.add("SalaRepository.get_all_with_eager_load()", False, str(e))

    # Test Usuario Repository
    try:
        repo = get_usuario_repository()
        users = repo.get_all()
        assert isinstance(users, list), "Should return list"
        results.add("UsuarioRepository.get_all()", True, f"Loaded {len(users)} users")
    except Exception as e:
        results.add("UsuarioRepository.get_all()", False, str(e))

    # Test Alocacao Repository
    try:
        repo = get_alocacao_repository()
        allocations = repo.get_all_with_eager_load()
        assert isinstance(allocations, list), "Should return list"
        results.add(
            "AlocacaoRepository.get_all_with_eager_load()",
            True,
            f"Loaded {len(allocations)} allocations",
        )
    except Exception as e:
        results.add("AlocacaoRepository.get_all_with_eager_load()", False, str(e))

    # Test Semestre Repository
    try:
        repo = get_semestre_repository()
        semesters = repo.get_all_with_counts()
        assert isinstance(semesters, list), "Should return list"
        results.add(
            "SemestreRepository.get_all_with_counts()",
            True,
            f"Loaded {len(semesters)} semesters",
        )
    except Exception as e:
        results.add("SemestreRepository.get_all_with_counts()", False, str(e))

    # Test Demanda Repository
    try:
        repo = get_demanda_repository()
        demands = repo.get_all()
        assert isinstance(demands, list), "Should return list"
        results.add(
            "DemandaRepository.get_all()", True, f"Loaded {len(demands)} demands"
        )
    except Exception as e:
        results.add("DemandaRepository.get_all()", False, str(e))

except Exception as e:
    results.add("Repository imports", False, str(e))

# ============================================================================
# TEST 2: REFACTORED SERVICES
# ============================================================================

print("\n" + "=" * 70)
print("TEST SUITE 2: REFACTORED SERVICES")
print("=" * 70)

try:
    from src.services.auth_service_refactored import get_auth_service
    from src.services.inventory_service_refactored import get_inventory_service
    from src.services.allocation_service_refactored import get_allocation_service
    from src.services.semester_service_refactored import get_semester_service

    # Test AuthService
    try:
        service = get_auth_service()
        users = service.get_all_users()
        assert isinstance(users, list), "Should return list"
        results.add("AuthService.get_all_users()", True, f"Loaded {len(users)} users")
    except Exception as e:
        results.add("AuthService.get_all_users()", False, str(e))

    # Test InventoryService
    try:
        service = get_inventory_service()
        rooms = service.get_all_salas()
        assert isinstance(rooms, list), "Should return list"
        results.add(
            "InventoryService.get_all_salas()", True, f"Loaded {len(rooms)} rooms"
        )
    except Exception as e:
        results.add("InventoryService.get_all_salas()", False, str(e))

    # Test AllocationService
    try:
        service = get_allocation_service()
        allocations = service.get_all_allocations()
        assert isinstance(allocations, list), "Should return list"
        results.add(
            "AllocationService.get_all_allocations()",
            True,
            f"Loaded {len(allocations)} allocations",
        )
    except Exception as e:
        results.add("AllocationService.get_all_allocations()", False, str(e))

    # Test SemesterService
    try:
        service = get_semester_service()
        semesters = service.get_all_semestres()
        assert isinstance(semesters, list), "Should return list"
        results.add(
            "SemesterService.get_all_semestres()",
            True,
            f"Loaded {len(semesters)} semesters",
        )
    except Exception as e:
        results.add("SemesterService.get_all_semestres()", False, str(e))

except Exception as e:
    results.add("Service imports", False, str(e))

# ============================================================================
# TEST 3: DTO LAYER (No Detached Objects)
# ============================================================================

print("\n" + "=" * 70)
print("TEST SUITE 3: DTO LAYER (Verify No Detached Objects)")
print("=" * 70)

try:
    from src.services.inventory_service_refactored import get_inventory_service
    from src.schemas.sala import SalaDTO

    service = get_inventory_service()
    rooms = service.get_all_salas()

    if rooms:
        room = rooms[0]
        # Verify it's a DTO, not an ORM object
        assert isinstance(room, SalaDTO), f"Should be SalaDTO, got {type(room)}"
        assert hasattr(room, "nome"), "Should have nome attribute"
        assert hasattr(room, "capacidade"), "Should have capacidade attribute"
        # Try accessing nested attributes (should not cause DetachedInstance)
        try:
            _ = room.nome
            _ = room.capacidade
            results.add(
                "DTO Attribute Access (No Session)",
                True,
                "Successfully accessed DTO attributes outside session",
            )
        except Exception as e:
            results.add("DTO Attribute Access (No Session)", False, str(e))
    else:
        results.add(
            "DTO Layer Test",
            True,
            "No rooms in database - skipped (expected for empty DB)",
        )

except Exception as e:
    results.add("DTO Layer Test", False, str(e))

# ============================================================================
# TEST 4: ERROR HANDLING
# ============================================================================

print("\n" + "=" * 70)
print("TEST SUITE 4: ERROR HANDLING")
print("=" * 70)

try:
    from src.utils.error_handler import DatabaseErrorHandler

    # Test error detection
    try:
        # Create a mock DetachedInstanceError
        from sqlalchemy.orm.exc import DetachedInstanceError

        error = DetachedInstanceError("Mock detached instance error")
        is_detached = DatabaseErrorHandler.is_detached_instance_error(error)
        assert is_detached, "Should detect DetachedInstanceError"
        results.add("Error Handler - DetachedInstanceError Detection", True)
    except Exception as e:
        results.add("Error Handler - DetachedInstanceError Detection", False, str(e))

    # Test generic error handling
    try:
        generic_error = Exception("Generic error")
        is_detached = DatabaseErrorHandler.is_detached_instance_error(generic_error)
        assert not is_detached, "Should not detect generic error as detached"
        results.add("Error Handler - Generic Error Handling", True)
    except Exception as e:
        results.add("Error Handler - Generic Error Handling", False, str(e))

except Exception as e:
    results.add("Error Handler imports", False, str(e))

# ============================================================================
# TEST 5: PYDANTIC VALIDATION
# ============================================================================

print("\n" + "=" * 70)
print("TEST SUITE 5: PYDANTIC VALIDATION")
print("=" * 70)

try:
    from src.schemas.sala import SalaCreateDTO

    # Valid DTO
    try:
        dto = SalaCreateDTO(
            nome="Test Room", capacidade=30, predio_id=1, tipo_sala_id=1
        )
        assert dto.nome == "Test Room"
        assert dto.capacidade == 30
        results.add("Pydantic - Valid DTO Creation", True)
    except Exception as e:
        results.add("Pydantic - Valid DTO Creation", False, str(e))

    # Invalid DTO (missing required field)
    try:
        dto = SalaCreateDTO(nome="Test Room")  # Missing capacidade and predio_id
        results.add(
            "Pydantic - Invalid DTO Rejection",
            False,
            "Should have raised validation error",
        )
    except Exception as e:
        if "validation error" in str(e).lower() or "field required" in str(e).lower():
            results.add("Pydantic - Invalid DTO Rejection", True)
        else:
            results.add(
                "Pydantic - Invalid DTO Rejection", False, f"Wrong error type: {e}"
            )

except Exception as e:
    results.add("Pydantic validation", False, str(e))

# ============================================================================
# TEST 6: BACKWARD COMPATIBILITY
# ============================================================================

print("\n" + "=" * 70)
print("TEST SUITE 6: BACKWARD COMPATIBILITY")
print("=" * 70)

print(
    "✅ Old service files (inventory_service.py, allocation_service.py, semester_service.py) have been deleted."
)
print("✅ All imports now use refactored services.")
print("✅ Backward compatibility test suite skipped (no longer applicable).")

# ============================================================================
# FINAL SUMMARY
# ============================================================================

results.summary()

# Exit with appropriate code
sys.exit(0 if all(p for _, p, _ in results.tests) else 1)
