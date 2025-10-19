"""
REFACTORED Inventory Service - Using Repository Pattern

This shows how to update an existing service to use repositories.
It maintains the same interface (backward compatible) but internally
uses repositories which return DTOs instead of detached ORM objects.

BEFORE (Returns detached ORM objects):
    def get_all_salas() -> List[Sala]:
        with DatabaseSession() as session:
            return session.query(Sala).all()  # ❌ Returns detached!

AFTER (Returns DTOs - safe):
    def get_all_salas() -> List[SalaDTO]:
        return SalaRepository.get_all_with_eager_load()  # ✅ Returns DTOs!
"""

import logging
from typing import List, Optional, Dict, Any

from src.repositories.sala import get_sala_repository
from src.schemas.sala import (
    SalaDTO,
    SalaSimplifiedDTO,
    SalaCreateDTO,
    SalaUpdateDTO,
    PredioDTO,
    TipoSalaDTO,
    CaracteristicaDTO,
    CampusDTO,
)

logger = logging.getLogger(__name__)


class InventoryService:
    """
    Service class for inventory management operations.

    This version uses the repository pattern to ensure:
    ✓ No detached ORM objects are returned
    ✓ All data is converted to DTOs at the boundary
    ✓ Clean separation of concerns
    ✓ Easy to test and maintain
    """

    # ===== ROOM OPERATIONS =====

    @classmethod
    def get_all_salas(cls) -> List[SalaDTO]:
        """
        Get all rooms

        Returns:
            List of SalaDTO objects (never detached ORM objects)
        """
        try:
            repo = get_sala_repository()
            return repo.get_all_with_eager_load()
        except Exception as e:
            logger.exception(f"Error getting all rooms: {e}")
            return []

    @classmethod
    def get_sala_by_id(cls, sala_id: int) -> Optional[SalaDTO]:
        """
        Get a room by ID

        Args:
            sala_id: Room ID

        Returns:
            SalaDTO or None if not found
        """
        try:
            repo = get_sala_repository()
            return repo.get_by_id(sala_id)
        except Exception as e:
            logger.exception(f"Error getting room by ID {sala_id}: {e}")
            return None

    @classmethod
    def get_salas_by_campus(cls, campus_id: int) -> List[SalaDTO]:
        """
        Get all rooms in a campus

        Args:
            campus_id: Campus ID

        Returns:
            List of SalaDTO objects
        """
        try:
            repo = get_sala_repository()
            return repo.get_by_campus(campus_id)
        except Exception as e:
            logger.exception(f"Error getting rooms by campus {campus_id}: {e}")
            return []

    @classmethod
    def get_salas_by_predio(cls, predio_id: int) -> List[SalaDTO]:
        """
        Get all rooms in a building

        Args:
            predio_id: Building ID

        Returns:
            List of SalaDTO objects
        """
        try:
            repo = get_sala_repository()
            return repo.get_by_predio(predio_id)
        except Exception as e:
            logger.exception(f"Error getting rooms by building {predio_id}: {e}")
            return []

    @classmethod
    def get_salas_by_tipo(cls, tipo_sala_id: int) -> List[SalaDTO]:
        """
        Get all rooms of a specific type

        Args:
            tipo_sala_id: Room type ID

        Returns:
            List of SalaDTO objects
        """
        try:
            repo = get_sala_repository()
            return repo.get_by_tipo_sala(tipo_sala_id)
        except Exception as e:
            logger.exception(f"Error getting rooms by type {tipo_sala_id}: {e}")
            return []

    @classmethod
    def search_salas(cls, search_term: str) -> List[SalaDTO]:
        """
        Search rooms by name

        Args:
            search_term: Search term

        Returns:
            List of matching SalaDTO objects
        """
        try:
            repo = get_sala_repository()
            return repo.search_by_name(search_term)
        except Exception as e:
            logger.exception(f"Error searching rooms with term '{search_term}': {e}")
            return []

    @classmethod
    def get_salas_simplified(cls) -> List[SalaSimplifiedDTO]:
        """
        Get simplified room list for dropdowns

        Returns:
            List of simplified SalaDTO objects
        """
        try:
            repo = get_sala_repository()
            return repo.get_simplified()
        except Exception as e:
            logger.exception(f"Error getting simplified rooms: {e}")
            return []

    @classmethod
    def get_salas_by_capacidade(cls, min_cap: int, max_cap: int) -> List[SalaDTO]:
        """
        Get rooms within a capacity range

        Args:
            min_cap: Minimum capacity
            max_cap: Maximum capacity

        Returns:
            List of matching SalaDTO objects
        """
        try:
            repo = get_sala_repository()
            return repo.get_by_capacidade_range(min_cap, max_cap)
        except Exception as e:
            logger.exception(f"Error getting rooms by capacity range: {e}")
            return []

    @classmethod
    def create_sala(cls, sala_data: SalaCreateDTO) -> Optional[SalaDTO]:
        """
        Create a new room

        Args:
            sala_data: SalaCreateDTO with room data

        Returns:
            Created SalaDTO or None if error
        """
        try:
            repo = get_sala_repository()
            return repo.create(sala_data)
        except Exception as e:
            logger.exception(f"Error creating room: {e}")
            return None

    @classmethod
    def update_sala(cls, sala_id: int, sala_data: SalaUpdateDTO) -> Optional[SalaDTO]:
        """
        Update a room

        Args:
            sala_id: Room ID
            sala_data: SalaUpdateDTO with updated data

        Returns:
            Updated SalaDTO or None if error
        """
        try:
            repo = get_sala_repository()
            return repo.update(sala_id, sala_data)
        except Exception as e:
            logger.exception(f"Error updating room {sala_id}: {e}")
            return None

    @classmethod
    def delete_sala(cls, sala_id: int) -> bool:
        """
        Delete a room

        Args:
            sala_id: Room ID

        Returns:
            True if successful, False otherwise
        """
        try:
            repo = get_sala_repository()
            return repo.delete(sala_id)
        except Exception as e:
            logger.exception(f"Error deleting room {sala_id}: {e}")
            return False

    @classmethod
    def get_rooms_count(cls) -> int:
        """
        Get total count of rooms

        Returns:
            Count of rooms
        """
        try:
            repo = get_sala_repository()
            return repo.count()
        except Exception as e:
            logger.exception(f"Error counting rooms: {e}")
            return 0

    # ===== PLACEHOLDER METHODS FOR OTHER ENTITIES =====
    # These would follow the same pattern with appropriate repositories

    @classmethod
    def get_all_campus(cls) -> List[CampusDTO]:
        """Get all campuses - TODO: Implement with CampusRepository"""
        logger.info("get_all_campus: Will be refactored with CampusRepository")
        return []

    @classmethod
    def get_all_predios(cls) -> List[PredioDTO]:
        """Get all buildings"""
        try:
            from database import DatabaseSession, Predio

            with DatabaseSession() as session:
                predios = session.query(Predio).all()
                return [
                    PredioDTO(
                        id=p.id,
                        nome=p.nome,
                        campus_id=p.campus_id,
                        campus=None,  # Skip nested campus to avoid lazy loading
                    )
                    for p in predios
                ]
        except Exception as e:
            logger.exception(f"Error getting all buildings: {e}")
            return []

    @classmethod
    def get_predios_by_campus(cls, campus_id: int) -> List[PredioDTO]:
        """Get all buildings in a campus"""
        try:
            from database import DatabaseSession, Predio

            with DatabaseSession() as session:
                predios = (
                    session.query(Predio).filter(Predio.campus_id == campus_id).all()
                )
                return [
                    PredioDTO(
                        id=p.id,
                        nome=p.nome,
                        campus_id=p.campus_id,
                        campus=None,  # Skip nested campus to avoid lazy loading
                    )
                    for p in predios
                ]
        except Exception as e:
            logger.exception(f"Error getting buildings by campus {campus_id}: {e}")
            return []

    @classmethod
    def get_all_tipos_sala(cls) -> List[TipoSalaDTO]:
        """Get all room types"""
        try:
            from database import DatabaseSession, TipoSala

            with DatabaseSession() as session:
                tipos = session.query(TipoSala).all()
                return [
                    TipoSalaDTO(id=t.id, nome=t.nome, descricao=t.descricao)
                    for t in tipos
                ]
        except Exception as e:
            logger.exception(f"Error getting all room types: {e}")
            return []

    @classmethod
    def get_all_caracteristicas(cls) -> List[CaracteristicaDTO]:
        """Get all characteristics"""
        try:
            from database import DatabaseSession, Caracteristica

            with DatabaseSession() as session:
                carats = session.query(Caracteristica).all()
                return [CaracteristicaDTO(id=c.id, nome=c.nome) for c in carats]
        except Exception as e:
            logger.exception(f"Error getting all characteristics: {e}")
            return []

    @classmethod
    def get_all_salas_data(cls) -> List[Dict[str, Any]]:
        """
        Get all rooms as dictionaries (for compatibility with UI)
        Returns list of dict representations of SalaDTO objects
        """
        try:
            salas = cls.get_all_salas()
            return [
                sala.model_dump() if hasattr(sala, "model_dump") else sala.__dict__
                for sala in salas
            ]
        except Exception as e:
            logger.exception(f"Error getting all rooms data: {e}")
            return []

    @classmethod
    def get_inventory_stats(cls) -> Dict[str, Any]:
        """Get inventory statistics"""
        try:
            return {
                "total_rooms": cls.get_rooms_count(),
                "total_campuses": len(cls.get_all_campus()),
                "total_buildings": len(cls.get_all_predios()),
                "total_room_types": len(cls.get_all_tipos_sala()),
            }
        except Exception as e:
            logger.exception(f"Error getting inventory stats: {e}")
            return {}

    @classmethod
    def search_salas(cls, filters: Dict[str, Any]) -> List[SalaDTO]:
        """
        Search rooms with filters (compatibility method)
        If filters is dict, extract search_term; if string, use directly
        """
        try:
            if isinstance(filters, dict):
                search_term = filters.get("search_term", "") or filters.get("nome", "")
            else:
                search_term = str(filters)

            if search_term:
                repo = get_sala_repository()
                return repo.search_by_name(search_term)
            else:
                return cls.get_all_salas()
        except Exception as e:
            logger.exception(f"Error searching rooms: {e}")
            return []

    @classmethod
    def create_tipo_sala(cls, tipo_data: Dict[str, Any]) -> Optional[TipoSalaDTO]:
        """Create a room type"""
        try:
            from database import DatabaseSession, TipoSala

            with DatabaseSession() as session:
                new_tipo = TipoSala(
                    nome=tipo_data.get("nome"),
                    descricao=tipo_data.get("descricao"),
                )
                session.add(new_tipo)
                session.flush()
                return TipoSalaDTO(
                    id=new_tipo.id, nome=new_tipo.nome, descricao=new_tipo.descricao
                )
        except Exception as e:
            logger.exception(f"Error creating room type: {e}")
            return None

    @classmethod
    def update_tipo_sala(
        cls, tipo_id: int, tipo_data: Dict[str, Any]
    ) -> Optional[TipoSalaDTO]:
        """Update a room type"""
        try:
            from database import DatabaseSession, TipoSala

            with DatabaseSession() as session:
                tipo = session.query(TipoSala).filter(TipoSala.id == tipo_id).first()
                if not tipo:
                    return None

                if "nome" in tipo_data:
                    tipo.nome = tipo_data["nome"]
                if "descricao" in tipo_data:
                    tipo.descricao = tipo_data["descricao"]

                session.flush()
                return TipoSalaDTO(id=tipo.id, nome=tipo.nome, descricao=tipo.descricao)
        except Exception as e:
            logger.exception(f"Error updating room type {tipo_id}: {e}")
            return None

    @classmethod
    def delete_tipo_sala(cls, tipo_id: int) -> bool:
        """Delete a room type"""
        try:
            from database import DatabaseSession, TipoSala

            with DatabaseSession() as session:
                tipo = session.query(TipoSala).filter(TipoSala.id == tipo_id).first()
                if tipo:
                    session.delete(tipo)
                    return True
                return False
        except Exception as e:
            logger.exception(f"Error deleting room type {tipo_id}: {e}")
            return False

    @classmethod
    def create_caracteristica(
        cls, caract_data: Dict[str, Any]
    ) -> Optional[CaracteristicaDTO]:
        """Create a characteristic"""
        try:
            from database import DatabaseSession, Caracteristica

            with DatabaseSession() as session:
                new_caract = Caracteristica(
                    nome=caract_data.get("nome"),
                )
                session.add(new_caract)
                session.flush()
                return CaracteristicaDTO(id=new_caract.id, nome=new_caract.nome)
        except Exception as e:
            logger.exception(f"Error creating characteristic: {e}")
            return None

    @classmethod
    def delete_caracteristica(cls, caract_id: int) -> bool:
        """Delete a characteristic"""
        try:
            from database import DatabaseSession, Caracteristica

            with DatabaseSession() as session:
                caract = (
                    session.query(Caracteristica)
                    .filter(Caracteristica.id == caract_id)
                    .first()
                )
                if caract:
                    session.delete(caract)
                    return True
                return False
        except Exception as e:
            logger.exception(f"Error deleting characteristic {caract_id}: {e}")
            return False

    @classmethod
    def get_caracteristica_by_id(cls, caract_id: int) -> Optional[CaracteristicaDTO]:
        """Get a characteristic by ID"""
        try:
            from database import DatabaseSession, Caracteristica

            with DatabaseSession() as session:
                caract = (
                    session.query(Caracteristica)
                    .filter(Caracteristica.id == caract_id)
                    .first()
                )
                if caract:
                    return CaracteristicaDTO(id=caract.id, nome=caract.nome)
                return None
        except Exception as e:
            logger.exception(f"Error getting characteristic {caract_id}: {e}")
            return None


# ===== CONVENIENCE FUNCTION =====


def get_inventory_service() -> InventoryService:
    """Get the inventory service"""
    return InventoryService()
