"""
Room Utilities - Shared utility functions for room operations.

Provides common room-related functionality used across multiple services
to eliminate code duplication and ensure consistency.
"""

import logging
from typing import Optional

from src.repositories.alocacao import AlocacaoRepository

logger = logging.getLogger(__name__)


def get_room_occupancy(alocacao_repo: AlocacaoRepository, room_id: int, semester_id: int) -> int:
    """
    Get current occupancy count for a room in the specified semester.
    
    Uses current semester occupancy count, with historical data as fallback.
    Loops through previous semesters until finding allocations or reaching semester 0.
    
    Args:
        alocacao_repo: AlocacaoRepository instance for database access
        room_id: Room ID to check occupancy for
        semester_id: Current semester ID
        
    Returns:
        int: Number of allocations for this room in the semester
    """
    try:
        # Get current semester occupancy
        current_allocations = alocacao_repo.get_by_sala_and_semestre(room_id, semester_id)
        current_count = len(current_allocations) if current_allocations else 0
        
        # If current semester has allocations, use that
        if current_count > 0:
            return current_count
        
        # Fallback: try previous semesters in a loop until we find allocations
        # This helps with optimization early in allocation process
        try:
            # Assuming semester IDs are sequential (e.g., 1, 2, 3 etc.)
            # Keep trying previous semesters until we find allocations or reach 0
            prev_semester_id = semester_id - 1
            while prev_semester_id > 0:
                prev_allocations = alocacao_repo.get_by_sala_and_semestre(room_id, prev_semester_id)
                if prev_allocations and len(prev_allocations) > 0:
                    return len(prev_allocations)
                prev_semester_id -= 1
        except Exception:
            # If fallback fails, just return 0
            pass
            
        return 0
        
    except Exception as e:
        # Log error but don't break the allocation process
        logger.warning(f"Error calculating occupancy for room {room_id}: {e}")
        return 0
