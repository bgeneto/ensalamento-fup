"""
IMPLEMENTATION GUIDE: Fixing Service Methods to Prevent DetachedInstance Errors

This guide shows how to update service methods to prevent the errors you were experiencing.
"""

# ============================================================================
# PATTERN 1: Return Dictionaries (RECOMMENDED - Most Flexible)
# ============================================================================

"""
Best for: Large result sets, complex nested data, API-style returns
Pros: Safe, serializable, lightweight, easy to cache
Cons: Requires manual mapping of all fields
"""

# BEFORE - Returns detached objects ❌
class InventoryServiceOLD:
    @classmethod
    def get_all_salas(cls):
        with DatabaseSession() as session:
            return session.query(Sala).all()  # ❌ Objects become detached!


# AFTER - Returns dictionaries ✅
class InventoryServiceNEW:
    @classmethod
    def get_all_salas(cls) -> List[Dict]:
        """Get all rooms as dictionaries (safe, no detached objects)"""
        try:
            with DatabaseSession() as session:
                salas = session.query(Sala).all()

                # Convert to dictionaries while still in session
                return [{
                    'id': sala.id,
                    'nome': sala.nome,
                    'codigo': sala.codigo,
                    'capacidade': sala.capacidade,
                    'andar': sala.andar,
                    'tipo_assento': sala.tipo_assento,
                    # ✅ Access relationships HERE while session is open
                    'predio_nome': sala.predio.nome if sala.predio else None,
                    'predio_id': sala.predio_id,
                    'tipo_sala_nome': sala.tipo_sala.nome if sala.tipo_sala else None,
                    'tipo_sala_id': sala.tipo_sala_id,
                    'caracteristicas': [
                        {'id': c.id, 'nome': c.nome}
                        for c in sala.caracteristicas
                    ],
                } for sala in salas]

        except Exception as e:
            logger.error(f"Error getting salas: {e}")
            return []


# ============================================================================
# PATTERN 2: Eager Load Relationships (GOOD - Reduces queries)
# ============================================================================

"""
Best for: When you need full objects but want to avoid lazy loading
Pros: Returns actual model objects, prevents N+1 queries
Cons: Need to know relationships in advance
"""

from sqlalchemy.orm import joinedload, subqueryload

class AllocationServiceNEW:
    @classmethod
    def get_allocation_rules(cls) -> List[Regra]:
        """Get allocation rules with eager-loaded relationships"""
        try:
            with DatabaseSession() as session:
                # Use joinedload to eagerly load related data
                rules = session.query(Regra)\
                    .options(joinedload(Regra.semestre))\
                    .order_by(Regra.prioridade.desc())\
                    .all()

                # ✅ Objects still have their relationships loaded
                # Relationships won't fail when accessed outside session
                return rules

        except Exception as e:
            logger.error(f"Error getting allocation rules: {e}")
            return []


# ============================================================================
# PATTERN 3: Expunge from Session (ADVANCED - For complex objects)
# ============================================================================

"""
Best for: When you need to return model objects but ensure they're independent
Pros: Works with complex relationships, preserves object identity
Cons: Can use more memory, not recommended for large datasets
"""

from sqlalchemy import inspect
from sqlalchemy.orm import make_transient

class InventoryServiceADVANCED:
    @classmethod
    def get_sala_with_relationships(cls, sala_id: int) -> Optional[Sala]:
        """Get room with all relationships, expunged from session"""
        try:
            with DatabaseSession() as session:
                sala = session.query(Sala).filter(Sala.id == sala_id).first()

                if sala:
                    # Force load all relationships while in session
                    _ = sala.predio.nome
                    _ = sala.tipo_sala.nome
                    _ = len(sala.caracteristicas)

                    # Expunge the object from the session
                    session.expunge(sala)

                return sala

        except Exception as e:
            logger.error(f"Error getting sala: {e}")
            return None


# ============================================================================
# PRACTICAL EXAMPLE: Fixing the Rooms Page
# ============================================================================

"""
Original error scenario:
1. get_all_salas() returns detached Sala objects
2. Page tries to access room.predio.nome
3. SQLAlchemy throws DetachedInstance error
"""

# ✅ SOLUTION USING PATTERN 1 (Recommended)
class InventoryServiceFIXED:
    @classmethod
    def get_all_salas(cls) -> List[Dict]:
        """Get all rooms with their relationships as dictionaries"""
        try:
            with DatabaseSession() as session:
                salas = session.query(Sala)\
                    .order_by(Sala.predio_id, Sala.nome)\
                    .all()

                sala_list = []
                for sala in salas:
                    # Access relationships while in session
                    predio_info = {
                        'id': sala.predio.id,
                        'nome': sala.predio.nome,
                        'campus_id': sala.predio.campus_id,
                    } if sala.predio else None

                    tipo_info = {
                        'id': sala.tipo_sala.id,
                        'nome': sala.tipo_sala.nome,
                    } if sala.tipo_sala else None

                    sala_list.append({
                        'id': sala.id,
                        'nome': sala.nome,
                        'codigo': sala.codigo,
                        'capacidade': sala.capacidade,
                        'andar': sala.andar,
                        'predio': predio_info,
                        'tipo_sala': tipo_info,
                        'caracteristicas': [
                            {'id': c.id, 'nome': c.nome}
                            for c in sala.caracteristicas
                        ],
                    })

                return sala_list

        except Exception as e:
            logger.error(f"Error getting salas: {e}")
            DatabaseErrorHandler.log_database_error(e, "get_all_salas")
            return []

    @classmethod
    def get_salas_by_campus(cls, campus_id: int) -> List[Dict]:
        """Get rooms by campus with safe detached data"""
        try:
            with DatabaseSession() as session:
                salas = session.query(Sala)\
                    .join(Predio)\
                    .filter(Predio.campus_id == campus_id)\
                    .all()

                return [{
                    'id': s.id,
                    'nome': s.nome,
                    'capacidade': s.capacidade,
                    'predio_nome': s.predio.nome,
                    'tipo_sala_nome': s.tipo_sala.nome,
                } for s in salas]

        except Exception as e:
            logger.error(f"Error getting salas by campus: {e}")
            return []


# ============================================================================
# PRACTICAL EXAMPLE: Fixing the Allocations Page
# ============================================================================

class AllocationServiceFIXED:
    @classmethod
    def get_allocation_statistics(cls, semestre_id: int) -> Optional[Dict]:
        """Get allocation statistics (safe version)"""
        try:
            with DatabaseSession() as session:
                # Query with eager loading
                from sqlalchemy.orm import joinedload

                allocations = session.query(AlocacaoSemestral)\
                    .filter(AlocacaoSemestral.semestre_id == semestre_id)\
                    .options(
                        joinedload(AlocacaoSemestral.demanda),
                        joinedload(AlocacaoSemestral.sala),
                        joinedload(AlocacaoSemestral.dia_semana),
                        joinedload(AlocacaoSemestral.horario_bloco),
                    )\
                    .all()

                if not allocations:
                    return None

                # Build statistics while in session
                stats = {
                    'total_allocations': len(allocations),
                    'rooms_used': len(set(a.sala_id for a in allocations)),
                    'demands_allocated': len(set(a.demanda_id for a in allocations)),
                    'utilization': [],
                }

                # Calculate utilization for each room (access relationships HERE)
                for allocation in allocations:
                    if allocation.sala and allocation.demanda:
                        stats['utilization'].append({
                            'room_name': allocation.sala.nome,
                            'demand_code': allocation.demanda.codigo_disciplina,
                            'utilization_rate': (
                                allocation.demanda.vagas_disciplina /
                                allocation.sala.capacidade * 100
                            ) if allocation.sala.capacidade > 0 else 0,
                        })

                return stats

        except Exception as e:
            logger.error(f"Error getting allocation statistics: {e}")
            DatabaseErrorHandler.log_database_error(e, "get_allocation_statistics")
            return None


# ============================================================================
# TESTING THE FIXES
# ============================================================================

"""
To test if your fixes work:

1. In a Python shell or test file:

    from src.services.inventory_service import InventoryService
    from src.utils.error_handler import DatabaseErrorHandler

    try:
        rooms = InventoryService.get_all_salas()
        print(f"✅ Got {len(rooms)} rooms")
        print(f"First room: {rooms[0]}")
        # Should print a dict, not raise an error
    except Exception as e:
        DatabaseErrorHandler.log_database_error(e, "Test")
        print(f"❌ Error: {e}")

2. Test in Streamlit page:
    - Navigate to the admin page
    - Check if it loads without errors
    - Try filtering/sorting
    - Check /logs/ for any error logs

3. Look for these patterns in logs:
    ✅ Good: "Got X items" messages
    ❌ Bad: "DetachedInstance" error messages
"""


# ============================================================================
# SUMMARY: Key Changes
# ============================================================================

"""
BEFORE (Causes DetachedInstance errors):
    ❌ Service returns SQLAlchemy objects
    ❌ Objects' relationships accessed outside session
    ❌ Lazy loading triggers on detached objects
    ❌ Error: "Instance X is detached from session"

AFTER (Safe):
    ✅ Service returns dictionaries or eager-loaded objects
    ✅ All relationships accessed within session context
    ✅ No lazy loading on detached objects
    ✅ Clean error logging and user messages
    ✅ Streamlit pages work reliably

PERFORMANCE:
    • Dictionary return: Fastest, most flexible
    • Eager loading: Reduces N+1 queries
    • Expunging: Memory efficient for small datasets

RECOMMENDED APPROACH:
    Use Pattern 1 (Dictionaries) for most services
    Use Pattern 2 (Eager loading) for complex queries
    Use Pattern 3 (Expunging) only when necessary
"""
