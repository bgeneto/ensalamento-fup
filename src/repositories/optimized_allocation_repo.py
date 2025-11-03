"""
Optimized Allocation Repository - Batch operations for reduced I/O
"""

from typing import List, Dict, Set, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text
from src.repositories.base import BaseRepository
from src.models.allocation import AlocacaoSemestral
from src.schemas.allocation import AlocacaoSemestralCreate, AlocacaoSemestralRead
import logging

logger = logging.getLogger(__name__)


class OptimizedAllocationRepository(BaseRepository[AlocacaoSemestralCreate, AlocacaoSemestralRead]):
    """Optimized repository with batch operations for autonomous allocation."""
    
    model_class = AlocacaoSemestral
    
    def __init__(self, session: Session):
        super().__init__(session, AlocacaoSemestral)
    
    def dto_to_orm_create(self, dto: AlocacaoSemestralCreate) -> AlocacaoSemestral:
        """Convert DTO to ORM object for creation."""
        return AlocacaoSemestral(
            semestre_id=dto.semestre_id,
            demanda_id=dto.demanda_id,
            sala_id=dto.sala_id,
            dia_semana_id=dto.dia_semana_id,
            codigo_bloco=dto.codigo_bloco
        )
    
    def orm_to_dto(self, orm_obj: AlocacaoSemestral) -> AlocacaoSemestralRead:
        """Convert ORM object to DTO for reading."""
        return AlocacaoSemestralRead(
            id=orm_obj.id,
            semestre_id=orm_obj.semestre_id,
            demanda_id=orm_obj.demanda_id,
            sala_id=orm_obj.sala_id,
            dia_semana_id=orm_obj.dia_semana_id,
            codigo_bloco=orm_obj.codigo_bloco,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at
        )

    def check_conflicts_batch(
        self, 
        room_time_slots: List[Tuple[int, int, str]], 
        semester_id: int
    ) -> Dict[Tuple[int, int, str], bool]:
        """
        Check conflicts for multiple room-time slots in a single query.
        
        Args:
            room_time_slots: List of (sala_id, dia_semana_id, codigo_bloco) tuples
            semester_id: Semester ID to check within
            
        Returns:
            Dict mapping each slot to True/False for conflict existence
        """
        if not room_time_slots:
            return {}
        
        # Build OR conditions for all slots
        or_conditions = []
        for sala_id, dia_semana_id, codigo_bloco in room_time_slots:
            or_conditions.append(
                and_(
                    AlocacaoSemestral.sala_id == sala_id,
                    AlocacaoSemestral.dia_semana_id == dia_semana_id,
                    AlocacaoSemestral.codigo_bloco == codigo_bloco,
                    AlocacaoSemestral.semestre_id == semester_id
                )
            )
        
        # Single query to check all conflicts
        existing_allocations = (
            self.session.query(AlocacaoSemestral.sala_id, AlocacaoSemestral.dia_semana_id, AlocacaoSemestral.codigo_bloco)
            .filter(or_(*or_conditions))
            .all()
        )
        
        # Build conflict results
        occupied_slots = {(alloc.sala_id, alloc.dia_semana_id, alloc.codigo_bloco) for alloc in existing_allocations}
        
        return {
            slot: slot in occupied_slots 
            for slot in room_time_slots
        }

    def create_batch_atomic(
        self, 
        allocation_dtos: List[AlocacaoSemestralCreate]
    ) -> List[AlocacaoSemestralRead]:
        """
        Create multiple allocation records in a single transaction.
        
        Args:
            allocation_dtos: List of allocation DTOs to create
            
        Returns:
            List of created allocation DTOs
        """
        if not allocation_dtos:
            return []
        
        try:
            # Convert all DTOs to ORM objects
            orm_objects = [self.dto_to_orm_create(dto) for dto in allocation_dtos]
            
            # Add all objects to session
            for orm_obj in orm_objects:
                self.session.add(orm_obj)
            
            # Single commit for all objects
            self.session.commit()
            
            # Refresh all objects to get their IDs
            for orm_obj in orm_objects:
                self.session.refresh(orm_obj)
            
            # Convert back to DTOs
            return [self.orm_to_dto(obj) for obj in orm_objects]
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Batch allocation failed: {e}")
            raise

    def get_room_occupancy_batch(
        self, 
        room_ids: List[int], 
        semester_id: int
    ) -> Dict[int, int]:
        """
        Get current occupancy for multiple rooms in a single query.
        
        Args:
            room_ids: List of room IDs to check
            semester_id: Semester ID to count within
            
        Returns:
            Dict mapping room_id to current allocation count
        """
        if not room_ids:
            return {}
        
        # Single query to get all room occupancies
        occupancy_data = (
            self.session.query(AlocacaoSemestral.sala_id, text('COUNT(*) as count'))
            .filter(
                and_(
                    AlocacaoSemestral.sala_id.in_(room_ids),
                    AlocacaoSemestral.semestre_id == semester_id
                )
            )
            .group_by(AlocacaoSemestral.sala_id)
            .all()
        )
        
        # Build occupancy dictionary
        occupancy = {room_id: 0 for room_id in room_ids}
        for room_id, count in occupancy_data:
            occupancy[room_id] = count
            
        return occupancy

    def get_existing_allocations_for_demands(
        self, 
        demanda_ids: List[int], 
        semester_id: int
    ) -> Dict[int, List[AlocacaoSemestralRead]]:
        """
        Get all existing allocations for multiple demands in a single query.
        
        Args:
            demanda_ids: List of demand IDs to check
            semester_id: Semester ID to filter within
            
        Returns:
            Dict mapping demanda_id to list of their allocations
        """
        if not demanda_ids:
            return {}
        
        # Single query to get all allocations for these demands
        allocations = (
            self.session.query(AlocacaoSemestral)
            .filter(
                and_(
                    AlocacaoSemestral.demanda_id.in_(demanda_ids),
                    AlocacaoSemestral.semestre_id == semester_id
                )
            )
            .all()
        )
        
        # Group by demanda_id
        result = {demanda_id: [] for demanda_id in demanda_ids}
        for alloc in allocations:
            result[alloc.demanda_id].append(self.orm_to_dto(alloc))
            
        return result
