"""
Inventory management service for Sistema de Ensalamento FUP/UnB
Handles campuses, buildings, rooms, and their characteristics
"""

from typing import List, Dict, Optional, Any
from database import (
    DatabaseSession,
    Campus,
    Predio,
    Sala,
    TipoSala,
    Caracteristica,
    SalaCaracteristica,
)
from models import (
    CampusCreate,
    CampusUpdate,
    PredioCreate,
    PredioUpdate,
    SalaCreate,
    SalaUpdate,
    TipoSalaCreate,
    TipoSalaUpdate,
    CaracteristicaCreate,
    CaracteristicaUpdate,
)
from utils import generate_room_code


class InventoryService:
    """Service class for inventory management operations"""

    # CAMPUS MANAGEMENT
    @classmethod
    def create_campus(cls, campus_data: CampusCreate) -> Optional[Campus]:
        """Create a new campus"""
        try:
            with DatabaseSession() as session:
                new_campus = Campus(
                    nome=campus_data.nome, descricao=campus_data.descricao
                )
                session.add(new_campus)
                session.flush()
                return new_campus
        except Exception as e:
            print(f"Error creating campus: {e}")
            return None

    @classmethod
    def get_all_campus(cls) -> List[Campus]:
        """Get all campuses"""
        try:
            with DatabaseSession() as session:
                return session.query(Campus).order_by(Campus.nome).all()
        except Exception as e:
            print(f"Error getting campuses: {e}")
            return []

    @classmethod
    def get_campus_by_id(cls, campus_id: int) -> Optional[Campus]:
        """Get campus by ID"""
        try:
            with DatabaseSession() as session:
                return session.query(Campus).filter(Campus.id == campus_id).first()
        except Exception as e:
            print(f"Error getting campus: {e}")
            return None

    @classmethod
    def update_campus(
        cls, campus_id: int, campus_data: CampusUpdate
    ) -> Optional[Campus]:
        """Update campus information"""
        try:
            with DatabaseSession() as session:
                campus = session.query(Campus).filter(Campus.id == campus_id).first()
                if not campus:
                    return None

                if campus_data.nome is not None:
                    campus.nome = campus_data.nome
                if campus_data.descricao is not None:
                    campus.descricao = campus_data.descricao

                return campus
        except Exception as e:
            print(f"Error updating campus: {e}")
            return None

    @classmethod
    def delete_campus(cls, campus_id: int) -> bool:
        """Delete a campus (only if no buildings associated)"""
        try:
            with DatabaseSession() as session:
                campus = session.query(Campus).filter(Campus.id == campus_id).first()
                if not campus:
                    return False

                # Check if campus has buildings
                building_count = (
                    session.query(Predio).filter(Predio.campus_id == campus_id).count()
                )
                if building_count > 0:
                    return False

                session.delete(campus)
                return True
        except Exception as e:
            print(f"Error deleting campus: {e}")
            return False

    # BUILDING MANAGEMENT
    @classmethod
    def create_predio(cls, predio_data: PredioCreate) -> Optional[Predio]:
        """Create a new building"""
        try:
            with DatabaseSession() as session:
                # Verify campus exists
                campus = (
                    session.query(Campus)
                    .filter(Campus.id == predio_data.campus_id)
                    .first()
                )
                if not campus:
                    return None

                new_predio = Predio(
                    nome=predio_data.nome,
                    descricao=predio_data.descricao,
                    campus_id=predio_data.campus_id,
                )
                session.add(new_predio)
                session.flush()
                return new_predio
        except Exception as e:
            print(f"Error creating building: {e}")
            return None

    @classmethod
    def get_all_predios(cls) -> List[Predio]:
        """Get all buildings with campus information"""
        try:
            with DatabaseSession() as session:
                return (
                    session.query(Predio)
                    .join(Campus)
                    .order_by(Campus.nome, Predio.nome)
                    .all()
                )
        except Exception as e:
            print(f"Error getting buildings: {e}")
            return []

    @classmethod
    def get_predios_by_campus(cls, campus_id: int) -> List[Predio]:
        """Get buildings for a specific campus"""
        try:
            with DatabaseSession() as session:
                return (
                    session.query(Predio)
                    .filter(Predio.campus_id == campus_id)
                    .order_by(Predio.nome)
                    .all()
                )
        except Exception as e:
            print(f"Error getting buildings: {e}")
            return []

    @classmethod
    def get_predio_by_id(cls, predio_id: int) -> Optional[Predio]:
        """Get building by ID with campus information"""
        try:
            with DatabaseSession() as session:
                return (
                    session.query(Predio)
                    .join(Campus)
                    .filter(Predio.id == predio_id)
                    .first()
                )
        except Exception as e:
            print(f"Error getting building: {e}")
            return None

    @classmethod
    def update_predio(
        cls, predio_id: int, predio_data: PredioUpdate
    ) -> Optional[Predio]:
        """Update building information"""
        try:
            with DatabaseSession() as session:
                predio = session.query(Predio).filter(Predio.id == predio_id).first()
                if not predio:
                    return None

                if predio_data.nome is not None:
                    predio.nome = predio_data.nome
                if predio_data.descricao is not None:
                    predio.descricao = predio_data.descricao
                if predio_data.campus_id is not None:
                    # Verify campus exists
                    campus = (
                        session.query(Campus)
                        .filter(Campus.id == predio_data.campus_id)
                        .first()
                    )
                    if campus:
                        predio.campus_id = predio_data.campus_id

                return predio
        except Exception as e:
            print(f"Error updating building: {e}")
            return None

    @classmethod
    def delete_predio(cls, predio_id: int) -> bool:
        """Delete a building (only if no rooms associated)"""
        try:
            with DatabaseSession() as session:
                predio = session.query(Predio).filter(Predio.id == predio_id).first()
                if not predio:
                    return False

                # Check if building has rooms
                room_count = (
                    session.query(Sala).filter(Sala.predio_id == predio_id).count()
                )
                if room_count > 0:
                    return False

                session.delete(predio)
                return True
        except Exception as e:
            print(f"Error deleting building: {e}")
            return False

    # ROOM TYPE MANAGEMENT
    @classmethod
    def create_tipo_sala(cls, tipo_data: TipoSalaCreate) -> Optional[TipoSala]:
        """Create a new room type"""
        try:
            with DatabaseSession() as session:
                new_tipo = TipoSala(nome=tipo_data.nome, descricao=tipo_data.descricao)
                session.add(new_tipo)
                session.flush()
                return new_tipo
        except Exception as e:
            print(f"Error creating room type: {e}")
            return None

    @classmethod
    def get_all_tipos_sala(cls) -> List[TipoSala]:
        """Get all room types"""
        try:
            with DatabaseSession() as session:
                return session.query(TipoSala).order_by(TipoSala.nome).all()
        except Exception as e:
            print(f"Error getting room types: {e}")
            return []

    @classmethod
    def update_tipo_sala(
        cls, tipo_id: int, tipo_data: TipoSalaUpdate
    ) -> Optional[TipoSala]:
        """Update room type information"""
        try:
            with DatabaseSession() as session:
                tipo = session.query(TipoSala).filter(TipoSala.id == tipo_id).first()
                if not tipo:
                    return None

                if tipo_data.nome is not None:
                    tipo.nome = tipo_data.nome
                if tipo_data.descricao is not None:
                    tipo.descricao = tipo_data.descricao

                return tipo
        except Exception as e:
            print(f"Error updating room type: {e}")
            return None

    @classmethod
    def delete_tipo_sala(cls, tipo_id: int) -> bool:
        """Delete a room type (only if no rooms associated)"""
        try:
            with DatabaseSession() as session:
                tipo = session.query(TipoSala).filter(TipoSala.id == tipo_id).first()
                if not tipo:
                    return False

                # Check if room type has rooms
                room_count = (
                    session.query(Sala).filter(Sala.tipo_sala_id == tipo_id).count()
                )
                if room_count > 0:
                    return False

                session.delete(tipo)
                return True
        except Exception as e:
            print(f"Error deleting room type: {e}")
            return False

    # CHARACTERISTICS MANAGEMENT
    @classmethod
    def create_caracteristica(
        cls, caract_data: CaracteristicaCreate
    ) -> Optional[Caracteristica]:
        """Create a new characteristic"""
        try:
            with DatabaseSession() as session:
                new_caract = Caracteristica(nome=caract_data.nome)
                session.add(new_caract)
                session.flush()
                return new_caract
        except Exception as e:
            print(f"Error creating characteristic: {e}")
            return None

    @classmethod
    def get_all_caracteristicas(cls) -> List[Caracteristica]:
        """Get all characteristics"""
        try:
            with DatabaseSession() as session:
                return session.query(Caracteristica).order_by(Caracteristica.nome).all()
        except Exception as e:
            print(f"Error getting characteristics: {e}")
            return []

    @classmethod
    def get_caracteristica_by_id(cls, caract_id: int) -> Optional[Caracteristica]:
        """Get characteristic by ID"""
        try:
            with DatabaseSession() as session:
                return (
                    session.query(Caracteristica)
                    .filter(Caracteristica.id == caract_id)
                    .first()
                )
        except Exception as e:
            print(f"Error getting characteristic: {e}")
            return None

    @classmethod
    def delete_caracteristica(cls, caract_id: int) -> bool:
        """Delete a characteristic"""
        try:
            with DatabaseSession() as session:
                caract = (
                    session.query(Caracteristica)
                    .filter(Caracteristica.id == caract_id)
                    .first()
                )
                if not caract:
                    return False

                session.delete(caract)
                return True
        except Exception as e:
            print(f"Error deleting characteristic: {e}")
            return False

    # ROOM MANAGEMENT
    @classmethod
    def create_sala(cls, sala_data: SalaCreate) -> Optional[Sala]:
        """Create a new room with characteristics"""
        try:
            with DatabaseSession() as session:
                # Verify building exists
                predio = (
                    session.query(Predio)
                    .filter(Predio.id == sala_data.predio_id)
                    .first()
                )
                if not predio:
                    return None

                # Verify room type exists
                tipo_sala = (
                    session.query(TipoSala)
                    .filter(TipoSala.id == sala_data.tipo_sala_id)
                    .first()
                )
                if not tipo_sala:
                    return None

                # Generate room code
                room_code = generate_room_code(predio.nome, sala_data.nome)

                new_sala = Sala(
                    nome=sala_data.nome,
                    capacidade=sala_data.capacidade,
                    andar=sala_data.andar,
                    predio_id=sala_data.predio_id,
                    tipo_sala_id=sala_data.tipo_sala_id,
                    codigo=room_code,
                )
                session.add(new_sala)
                session.flush()

                # Add characteristics if provided
                if sala_data.caracteristicas:
                    for caract_id in sala_data.caracteristicas:
                        # Verify characteristic exists
                        caract = (
                            session.query(Caracteristica)
                            .filter(Caracteristica.id == caract_id)
                            .first()
                        )
                        if caract:
                            sala_caract = SalaCaracteristica(
                                sala_id=new_sala.id, caracteristica_id=caract.id
                            )
                            session.add(sala_caract)

                return new_sala
        except Exception as e:
            print(f"Error creating room: {e}")
            return None

    @classmethod
    def get_all_salas(cls) -> List[Sala]:
        """Get all rooms with relationships loaded"""
        try:
            with DatabaseSession() as session:
                return (
                    session.query(Sala)
                    .join(Predio)
                    .join(Campus)
                    .order_by(Campus.nome, Predio.nome, Sala.nome)
                    .all()
                )
        except Exception as e:
            print(f"Error getting rooms: {e}")
            return []

    @classmethod
    def get_salas_by_predio(cls, predio_id: int) -> List[Sala]:
        """Get rooms for a specific building"""
        try:
            with DatabaseSession() as session:
                return (
                    session.query(Sala)
                    .filter(Sala.predio_id == predio_id)
                    .order_by(Sala.andar, Sala.nome)
                    .all()
                )
        except Exception as e:
            print(f"Error getting rooms: {e}")
            return []

    @classmethod
    def get_sala_by_id(cls, sala_id: int) -> Optional[Sala]:
        """Get room by ID with all relationships"""
        try:
            with DatabaseSession() as session:
                return (
                    session.query(Sala)
                    .join(Predio)
                    .join(Campus)
                    .filter(Sala.id == sala_id)
                    .first()
                )
        except Exception as e:
            print(f"Error getting room: {e}")
            return None

    @classmethod
    def update_sala(cls, sala_id: int, sala_data: SalaUpdate) -> Optional[Sala]:
        """Update room information"""
        try:
            with DatabaseSession() as session:
                sala = session.query(Sala).filter(Sala.id == sala_id).first()
                if not sala:
                    return None

                # Update basic fields
                if sala_data.nome is not None:
                    sala.nome = sala_data.nome
                    # Regenerate room code
                    if sala.predio:
                        sala.codigo = generate_room_code(
                            sala.predio.nome, sala_data.nome
                        )

                if sala_data.capacidade is not None:
                    sala.capacidade = sala_data.capacidade
                if sala_data.andar is not None:
                    sala.andar = sala_data.andar
                if sala_data.tipo_sala_id is not None:
                    # Verify room type exists
                    tipo = (
                        session.query(TipoSala)
                        .filter(TipoSala.id == sala_data.tipo_sala_id)
                        .first()
                    )
                    if tipo:
                        sala.tipo_sala_id = sala_data.tipo_sala_id

                # Update characteristics if provided
                if sala_data.caracteristicas is not None:
                    # Remove existing characteristics
                    session.query(SalaCaracteristica).filter(
                        SalaCaracteristica.sala_id == sala_id
                    ).delete()

                    # Add new characteristics
                    for caract_id in sala_data.caracteristicas:
                        caract = (
                            session.query(Caracteristica)
                            .filter(Caracteristica.id == caract_id)
                            .first()
                        )
                        if caract:
                            sala_caract = SalaCaracteristica(
                                sala_id=sala_id, caracteristica_id=caract_id
                            )
                            session.add(sala_caract)

                return sala
        except Exception as e:
            print(f"Error updating room: {e}")
            return None

    @classmethod
    def delete_sala(cls, sala_id: int) -> bool:
        """Delete a room"""
        try:
            with DatabaseSession() as session:
                sala = session.query(Sala).filter(Sala.id == sala_id).first()
                if not sala:
                    return False

                session.delete(sala)
                return True
        except Exception as e:
            print(f"Error deleting room: {e}")
            return False

    # SEARCH AND FILTER
    @classmethod
    def search_salas(cls, filters: Dict[str, Any]) -> List[Sala]:
        """Search rooms with filters"""
        try:
            with DatabaseSession() as session:
                query = session.query(Sala).join(Predio).join(Campus).join(TipoSala)

                # Apply filters
                if "campus_id" in filters:
                    query = query.filter(Campus.id == filters["campus_id"])

                if "predio_id" in filters:
                    query = query.filter(Predio.id == filters["predio_id"])

                if "tipo_sala_id" in filters:
                    query = query.filter(TipoSala.id == filters["tipo_sala_id"])

                if "capacidade_min" in filters:
                    query = query.filter(Sala.capacidade >= filters["capacidade_min"])

                if "capacidade_max" in filters:
                    query = query.filter(Sala.capacidade <= filters["capacidade_max"])

                if "andar" in filters:
                    query = query.filter(Sala.andar == filters["andar"])

                # Order by campus, building, floor, then room name
                return query.order_by(
                    Campus.nome, Predio.nome, Sala.andar, Sala.nome
                ).all()

        except Exception as e:
            print(f"Error searching rooms: {e}")
            return []

    # STATISTICS
    @classmethod
    def get_inventory_stats(cls) -> Dict[str, int]:
        """Get inventory statistics"""
        try:
            with DatabaseSession() as session:
                stats = {
                    "campus": session.query(Campus).count(),
                    "predios": session.query(Predio).count(),
                    "salas": session.query(Sala).count(),
                    "tipos_sala": session.query(TipoSala).count(),
                    "caracteristicas": session.query(Caracteristica).count(),
                }

                # Get capacity statistics
                total_capacity = (
                    session.query(Sala).with_entities(Sala.capacidade).all()
                )
                if total_capacity:
                    stats["capacidade_total"] = sum(cap[0] for cap in total_capacity)
                    stats["capacidade_media"] = stats["capacidade_total"] // len(
                        total_capacity
                    )
                else:
                    stats["capacidade_total"] = 0
                    stats["capacidade_media"] = 0

                return stats
        except Exception as e:
            print(f"Error getting inventory stats: {e}")
            return {}
