#!/usr/bin/env python3
"""
QUICK TEST SCRIPT - Validate Repository Pattern Implementation

This script tests all the newly created repositories and schemas
to ensure they work correctly without DetachedInstance errors.

Run this to verify:
1. All repositories load without errors
2. DTOs convert correctly from ORM objects
3. No DetachedInstance errors on nested access
4. All relationships are eager-loaded

Usage:
    python verify_repositories.py

Expected Output:
    ✓ All tests pass
    ✓ No errors in logs
    ✓ No DetachedInstance errors
"""

import sys
import logging
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_sala_repository():
    """Test Sala repository"""
    print("\n" + "=" * 60)
    print("TESTING SALA REPOSITORY")
    print("=" * 60)

    try:
        from src.repositories.sala import get_sala_repository
        from src.schemas.sala import SalaDTO

        repo = get_sala_repository()
        print("✓ SalaRepository imported successfully")

        # Test get_all_with_eager_load
        rooms = repo.get_all_with_eager_load()
        if len(rooms) > 5:
            rooms = rooms[:5]
        print(f"✓ get_all_with_eager_load() returned {len(rooms)} rooms")

        if rooms:
            room = rooms[0]
            print(f"  Room DTO type: {type(room).__name__}")
            assert isinstance(room, SalaDTO), "Should return SalaDTO"
            print(f"✓ First room: {room.nome}")

            # Test nested access (this used to fail)
            if room.predio:
                print(f"✓ Nested access: Building = {room.predio.nome}")

            if room.tipo_sala:
                print(f"✓ Nested access: Type = {room.tipo_sala.nome}")

            if room.caracteristicas:
                print(f"✓ Characteristics: {len(room.caracteristicas)} items")

            # Test by_id
            room_id = rooms[0].id
            room = repo.get_by_id(room_id)
            if room:
                print(f"✓ get_by_id({room_id}): {room.nome}")
                # Test nested access again
                if room.predio:
                    print(f"✓ Nested access after get_by_id: {room.predio.nome}")
        else:
            print("ℹ️  Database is empty (this is OK for initial testing)")
            print("✓ Repository methods executed without errors")

        print("\n✅ SALA REPOSITORY TESTS PASSED")
        return True

    except Exception as e:
        print(f"\n❌ SALA REPOSITORY TEST FAILED: {e}")
        logger.exception("Sala repository test error")
        return False


def test_alocacao_repository():
    """Test Alocacao repository"""
    print("\n" + "=" * 60)
    print("TESTING ALOCACAO REPOSITORY")
    print("=" * 60)

    try:
        from src.repositories.alocacao import get_alocacao_repository
        from src.schemas.alocacao import AlocacaoSemestralDTO

        repo = get_alocacao_repository()
        print("✓ AlocacaoRepository imported successfully")

        # Test get_all_with_eager_load
        allocations = repo.get_all_with_eager_load()
        if len(allocations) > 5:
            allocations = allocations[:5]
        print(f"✓ get_all_with_eager_load() returned {len(allocations)} allocations")

        if allocations:
            alloc = allocations[0]
            print(f"  Allocation DTO type: {type(alloc).__name__}")
            assert isinstance(
                alloc, AlocacaoSemestralDTO
            ), "Should return AlocacaoSemestralDTO"

            # Test nested access
            print(f"✓ Room: {alloc.sala_nome}")
            print(f"✓ Building: {alloc.predio_nome}")
            print(f"✓ Discipline: {alloc.disciplina_codigo}")
            print(f"✓ Day: {alloc.dia_semana_nome}")
        else:
            print("ℹ️  Database is empty (this is OK for initial testing)")
            print("✓ Repository methods executed without errors")

        print("\n✅ ALOCACAO REPOSITORY TESTS PASSED")
        return True

    except Exception as e:
        print(f"\n❌ ALOCACAO REPOSITORY TEST FAILED: {e}")
        logger.exception("Alocacao repository test error")
        return False


def test_usuario_repository():
    """Test Usuario repository"""
    print("\n" + "=" * 60)
    print("TESTING USUARIO REPOSITORY")
    print("=" * 60)

    try:
        from src.repositories.usuario import get_usuario_repository
        from src.schemas.usuario import UsuarioDTO

        repo = get_usuario_repository()
        print("✓ UsuarioRepository imported successfully")

        # Test get_all
        users = repo.get_all(limit=5)
        print(f"✓ get_all() returned {len(users)} users")

        if users:
            user = users[0]
            print(f"  User DTO type: {type(user).__name__}")
            assert isinstance(user, UsuarioDTO), "Should return UsuarioDTO"
            print(f"✓ User: {user.nome_completo} ({user.role})")

            # Test by_username
            username = user.username
            user2 = repo.get_by_username(username)
            if user2:
                print(f"✓ get_by_username('{username}'): {user2.nome_completo}")

        # Test get_by_role
        admins = repo.get_by_role("admin")
        print(f"✓ get_by_role('admin') returned {len(admins)} admins")

        professors = repo.get_by_role("professor")
        print(f"✓ get_by_role('professor') returned {len(professors)} professors")

        print("\n✅ USUARIO REPOSITORY TESTS PASSED")
        return True

    except Exception as e:
        print(f"\n❌ USUARIO REPOSITORY TEST FAILED: {e}")
        logger.exception("Usuario repository test error")
        return False


def test_semestre_repository():
    """Test Semestre repository"""
    print("\n" + "=" * 60)
    print("TESTING SEMESTRE REPOSITORY")
    print("=" * 60)

    try:
        from src.repositories.semestre import (
            get_semestre_repository,
            get_demanda_repository,
        )
        from src.schemas.semestre import SemestreDTO, DemandaDTO

        sem_repo = get_semestre_repository()
        print("✓ SemestreRepository imported successfully")

        # Test get_all_with_counts
        semesters = sem_repo.get_all_with_counts(limit=5)
        print(f"✓ get_all_with_counts() returned {len(semesters)} semesters")

        if semesters:
            sem = semesters[0]
            print(f"  Semester DTO type: {type(sem).__name__}")
            assert isinstance(sem, SemestreDTO), "Should return SemestreDTO"
            print(f"✓ Semester: {sem.nome} ({sem.status})")
            print(f"  - Demands: {sem.demandas_count}")
            print(f"  - Allocations: {sem.alocacoes_count}")

        # Test DemandaRepository
        dem_repo = get_demanda_repository()
        print("✓ DemandaRepository imported successfully")

        if semesters:
            sem_id = semesters[0].id
            demands = dem_repo.get_by_semestre(sem_id)
            print(f"✓ get_by_semestre({sem_id}) returned {len(demands)} demands")

            if demands:
                demand = demands[0]
                print(f"  Demand DTO type: {type(demand).__name__}")
                assert isinstance(demand, DemandaDTO), "Should return DemandaDTO"
                print(
                    f"✓ Demand: {demand.codigo_disciplina} - {demand.nome_disciplina}"
                )

        print("\n✅ SEMESTRE REPOSITORY TESTS PASSED")
        return True

    except Exception as e:
        print(f"\n❌ SEMESTRE REPOSITORY TEST FAILED: {e}")
        logger.exception("Semestre repository test error")
        return False


def test_services():
    """Test refactored services"""
    print("\n" + "=" * 60)
    print("TESTING REFACTORED SERVICES")
    print("=" * 60)

    try:
        from src.services.inventory_service_refactored import InventoryService
        from src.schemas.sala import SalaDTO

        service = InventoryService()
        print("✓ InventoryService imported successfully")

        # Test get_all_salas
        rooms = service.get_all_salas()
        print(f"✓ get_all_salas() returned {len(rooms)} rooms")

        if rooms:
            room = rooms[0]
            assert isinstance(room, SalaDTO), "Should return SalaDTO"
            print(f"✓ First room: {room.nome}")

            # Test nested access
            if room.predio:
                print(f"✓ Nested access in service: {room.predio.nome}")

        # Test get_all_salas_by_campus
        campuses = service.get_all_campus()
        if campuses:
            campus_id = campuses[0].id
            rooms_campus = service.get_all_salas_by_campus(campus_id)
            print(
                f"✓ get_all_salas_by_campus({campus_id}) returned {len(rooms_campus)} rooms"
            )

        print("\n✅ REFACTORED SERVICES TESTS PASSED")
        return True

    except Exception as e:
        print(f"\n❌ REFACTORED SERVICES TEST FAILED: {e}")
        logger.exception("Services test error")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("REPOSITORY PATTERN - VERIFICATION TESTS")
    print("=" * 60)
    print("\nTesting all newly created repositories and services...")

    tests = [
        ("Sala Repository", test_sala_repository),
        ("Alocacao Repository", test_alocacao_repository),
        ("Usuario Repository", test_usuario_repository),
        ("Semestre Repository", test_semestre_repository),
        ("Refactored Services", test_services),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.exception(f"Error running {test_name}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Repository pattern is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check logs for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
