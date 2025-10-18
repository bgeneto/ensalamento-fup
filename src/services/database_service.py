"""
Database service for Sistema de Ensalamento FUP/UnB
Handles all CRUD operations and business logic
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, asc
from database import (
    Campus,
    Predio,
    TipoSala,
    Caracteristica,
    Sala,
    SalaCaracteristica,
    DiaSemana,
    HorarioBloco,
    Semestre,
    Demanda,
    Regra,
    AlocacaoSemestral,
    ReservaEsporadica,
    Usuario,
    DatabaseSession,
)
from models import (
    Campus as CampusModel,
    Predio as PredioModel,
    TipoSala as TipoSalaModel,
    Caracteristica as CaracteristicaModel,
    Sala as SalaModel,
    DiaSemana as DiaSemanaModel,
    HorarioBloco as HorarioBlocoModel,
    Semestre as SemestreModel,
    Demanda as DemandaModel,
    Regra as RegraModel,
    AlocacaoSemestral as AlocacaoSemestralModel,
    ReservaEsporadica as ReservaEsporadicaModel,
    Usuario as UsuarioModel,
    SalaFilter,
    ReservaFilter,
)


class DatabaseService:
    """Service class for database operations"""

    # Campus Operations
    @staticmethod
    def create_campus(campus_data: CampusModel) -> Campus:
        """Create a new campus"""
        with DatabaseSession() as session:
            campus = Campus(nome=campus_data.nome, descricao=campus_data.descricao)
            session.add(campus)
            session.flush()  # Get the ID without committing
            return campus

    @staticmethod
    def get_campus_by_id(campus_id: int) -> Optional[Campus]:
        """Get campus by ID"""
        with DatabaseSession() as session:
            return session.query(Campus).filter(Campus.id == campus_id).first()

    @staticmethod
    def get_all_campus() -> List[Campus]:
        """Get all campuses"""
        with DatabaseSession() as session:
            return session.query(Campus).order_by(Campus.nome).all()

    @staticmethod
    def update_campus(campus_id: int, campus_data: CampusModel) -> Optional[Campus]:
        """Update campus"""
        with DatabaseSession() as session:
            campus = session.query(Campus).filter(Campus.id == campus_id).first()
            if campus:
                campus.nome = campus_data.nome
                campus.descricao = campus_data.descricao
                return campus
            return None

    @staticmethod
    def delete_campus(campus_id: int) -> bool:
        """Delete campus"""
        with DatabaseSession() as session:
            campus = session.query(Campus).filter(Campus.id == campus_id).first()
            if campus:
                session.delete(campus)
                return True
            return False

    # Building Operations
    @staticmethod
    def create_predio(predio_data: PredioModel) -> Predio:
        """Create a new building"""
        with DatabaseSession() as session:
            predio = Predio(nome=predio_data.nome, campus_id=predio_data.campus_id)
            session.add(predio)
            session.flush()
            return predio

    @staticmethod
    def get_predio_by_id(predio_id: int) -> Optional[Predio]:
        """Get building by ID"""
        with DatabaseSession() as session:
            return (
                session.query(Predio)
                .options(joinedload(Predio.campus))
                .filter(Predio.id == predio_id)
                .first()
            )

    @staticmethod
    def get_predios_by_campus(campus_id: int) -> List[Predio]:
        """Get buildings by campus"""
        with DatabaseSession() as session:
            return (
                session.query(Predio)
                .filter(Predio.campus_id == campus_id)
                .order_by(Predio.nome)
                .all()
            )

    @staticmethod
    def get_all_predios() -> List[Predio]:
        """Get all buildings"""
        with DatabaseSession() as session:
            return (
                session.query(Predio)
                .options(joinedload(Predio.campus))
                .order_by(Campus.nome, Predio.nome)
                .all()
            )

    @staticmethod
    def update_predio(predio_id: int, predio_data: PredioModel) -> Optional[Predio]:
        """Update building"""
        with DatabaseSession() as session:
            predio = session.query(Predio).filter(Predio.id == predio_id).first()
            if predio:
                predio.nome = predio_data.nome
                predio.campus_id = predio_data.campus_id
                return predio
            return None

    @staticmethod
    def delete_predio(predio_id: int) -> bool:
        """Delete building"""
        with DatabaseSession() as session:
            predio = session.query(Predio).filter(Predio.id == predio_id).first()
            if predio:
                session.delete(predio)
                return True
            return False

    # Room Type Operations
    @staticmethod
    def create_tipo_sala(tipo_data: TipoSalaModel) -> TipoSala:
        """Create a new room type"""
        with DatabaseSession() as session:
            tipo_sala = TipoSala(nome=tipo_data.nome, descricao=tipo_data.descricao)
            session.add(tipo_sala)
            session.flush()
            return tipo_sala

    @staticmethod
    def get_tipo_sala_by_id(tipo_id: int) -> Optional[TipoSala]:
        """Get room type by ID"""
        with DatabaseSession() as session:
            return session.query(TipoSala).filter(TipoSala.id == tipo_id).first()

    @staticmethod
    def get_all_tipos_sala() -> List[TipoSala]:
        """Get all room types"""
        with DatabaseSession() as session:
            return session.query(TipoSala).order_by(TipoSala.nome).all()

    @staticmethod
    def update_tipo_sala(tipo_id: int, tipo_data: TipoSalaModel) -> Optional[TipoSala]:
        """Update room type"""
        with DatabaseSession() as session:
            tipo_sala = session.query(TipoSala).filter(TipoSala.id == tipo_id).first()
            if tipo_sala:
                tipo_sala.nome = tipo_data.nome
                tipo_sala.descricao = tipo_data.descricao
                return tipo_sala
            return None

    @staticmethod
    def delete_tipo_sala(tipo_id: int) -> bool:
        """Delete room type"""
        with DatabaseSession() as session:
            tipo_sala = session.query(TipoSala).filter(TipoSala.id == tipo_id).first()
            if tipo_sala:
                session.delete(tipo_sala)
                return True
            return False

    # Room Characteristic Operations
    @staticmethod
    def create_caracteristica(
        caracteristica_data: CaracteristicaModel,
    ) -> Caracteristica:
        """Create a new room characteristic"""
        with DatabaseSession() as session:
            caracteristica = Caracteristica(nome=caracteristica_data.nome)
            session.add(caracteristica)
            session.flush()
            return caracteristica

    @staticmethod
    def get_caracteristica_by_id(caracteristica_id: int) -> Optional[Caracteristica]:
        """Get characteristic by ID"""
        with DatabaseSession() as session:
            return (
                session.query(Caracteristica)
                .filter(Caracteristica.id == caracteristica_id)
                .first()
            )

    @staticmethod
    def get_all_caracteristicas() -> List[Caracteristica]:
        """Get all characteristics"""
        with DatabaseSession() as session:
            return session.query(Caracteristica).order_by(Caracteristica.nome).all()

    @staticmethod
    def update_caracteristica(
        caracteristica_id: int, caracteristica_data: CaracteristicaModel
    ) -> Optional[Caracteristica]:
        """Update characteristic"""
        with DatabaseSession() as session:
            caracteristica = (
                session.query(Caracteristica)
                .filter(Caracteristica.id == caracteristica_id)
                .first()
            )
            if caracteristica:
                caracteristica.nome = caracteristica_data.nome
                return caracteristica
            return None

    @staticmethod
    def delete_caracteristica(caracteristica_id: int) -> bool:
        """Delete characteristic"""
        with DatabaseSession() as session:
            caracteristica = (
                session.query(Caracteristica)
                .filter(Caracteristica.id == caracteristica_id)
                .first()
            )
            if caracteristica:
                session.delete(caracteristica)
                return True
            return False

    # Room Operations
    @staticmethod
    def create_sala(
        sala_data: SalaModel, caracteristicas_ids: Optional[List[int]] = None
    ) -> Sala:
        """Create a new room"""
        with DatabaseSession() as session:
            sala = Sala(
                nome=sala_data.nome,
                predio_id=sala_data.predio_id,
                tipo_sala_id=sala_data.tipo_sala_id,
                capacidade=sala_data.capacidade,
                andar=sala_data.andar,
                tipo_assento=sala_data.tipo_assento,
            )
            session.add(sala)
            session.flush()  # Get the room ID

            # Add characteristics if provided
            if caracteristicas_ids:
                for caract_id in caracteristicas_ids:
                    sala_caract = SalaCaracteristica(
                        sala_id=sala.id, caracteristica_id=caract_id
                    )
                    session.add(sala_caract)

            return sala

    @staticmethod
    def get_sala_by_id(sala_id: int) -> Optional[Sala]:
        """Get room by ID with relationships"""
        with DatabaseSession() as session:
            return (
                session.query(Sala)
                .options(
                    joinedload(Sala.predio).joinedload(Predio.campus),
                    joinedload(Sala.tipo_sala),
                    joinedload(Sala.caracteristicas),
                )
                .filter(Sala.id == sala_id)
                .first()
            )

    @staticmethod
    def get_salas_by_filter(sala_filter: SalaFilter) -> List[Sala]:
        """Get rooms filtered by criteria"""
        with DatabaseSession() as session:
            query = session.query(Sala).options(
                joinedload(Sala.predio).joinedload(Predio.campus),
                joinedload(Sala.tipo_sala),
                joinedload(Sala.caracteristicas),
            )

            if sala_filter.predio_id:
                query = query.filter(Sala.predio_id == sala_filter.predio_id)

            if sala_filter.tipo_sala_id:
                query = query.filter(Sala.tipo_sala_id == sala_filter.tipo_sala_id)

            if sala_filter.capacidade_min is not None:
                query = query.filter(Sala.capacidade >= sala_filter.capacidade_min)

            if sala_filter.capacidade_max is not None:
                query = query.filter(Sala.capacidade <= sala_filter.capacidade_max)

            if sala_filter.caracteristicas:
                # Filter by characteristics (room must have ALL specified characteristics)
                for caract_id in sala_filter.caracteristicas:
                    query = query.filter(
                        Sala.caracteristicas.any(Caracteristica.id == caract_id)
                    )

            return query.order_by(Predio.campus_id, Predio.nome, Sala.nome).all()

    @staticmethod
    def get_all_salas() -> List[Sala]:
        """Get all rooms"""
        with DatabaseSession() as session:
            return (
                session.query(Sala)
                .options(
                    joinedload(Sala.predio).joinedload(Predio.campus),
                    joinedload(Sala.tipo_sala),
                    joinedload(Sala.caracteristicas),
                )
                .order_by(Predio.campus_id, Predio.nome, Sala.nome)
                .all()
            )

    @staticmethod
    def update_sala(
        sala_id: int,
        sala_data: SalaModel,
        caracteristicas_ids: Optional[List[int]] = None,
    ) -> Optional[Sala]:
        """Update room"""
        with DatabaseSession() as session:
            sala = session.query(Sala).filter(Sala.id == sala_id).first()
            if sala:
                sala.nome = sala_data.nome
                sala.predio_id = sala_data.predio_id
                sala.tipo_sala_id = sala_data.tipo_sala_id
                sala.capacidade = sala_data.capacidade
                sala.andar = sala_data.andar
                sala.tipo_assento = sala_data.tipo_assento

                # Update characteristics
                if caracteristicas_ids is not None:
                    # Remove existing characteristics
                    session.query(SalaCaracteristica).filter(
                        SalaCaracteristica.sala_id == sala_id
                    ).delete()

                    # Add new characteristics
                    for caract_id in caracteristicas_ids:
                        sala_caract = SalaCaracteristica(
                            sala_id=sala_id, caracteristica_id=caract_id
                        )
                        session.add(sala_caract)

                return sala
            return None

    @staticmethod
    def delete_sala(sala_id: int) -> bool:
        """Delete room"""
        with DatabaseSession() as session:
            sala = session.query(Sala).filter(Sala.id == sala_id).first()
            if sala:
                session.delete(sala)
                return True
            return False

    # Semester Operations
    @staticmethod
    def create_semestre(semestre_data: SemestreModel) -> Semestre:
        """Create a new semester"""
        with DatabaseSession() as session:
            semestre = Semestre(nome=semestre_data.nome, status=semestre_data.status)
            session.add(semestre)
            session.flush()
            return semestre

    @staticmethod
    def get_semestre_by_id(semestre_id: int) -> Optional[Semestre]:
        """Get semester by ID"""
        with DatabaseSession() as session:
            return session.query(Semestre).filter(Semestre.id == semestre_id).first()

    @staticmethod
    def get_semestre_ativo() -> Optional[Semestre]:
        """Get current active semester"""
        with DatabaseSession() as session:
            return (
                session.query(Semestre)
                .filter(Semestre.status.in_(["Planejamento", "Execução"]))
                .order_by(desc(Semestre.id))
                .first()
            )

    @staticmethod
    def get_all_semestres() -> List[Semestre]:
        """Get all semesters"""
        with DatabaseSession() as session:
            return session.query(Semestre).order_by(desc(Semestre.nome)).all()

    @staticmethod
    def update_semestre(
        semestre_id: int, semestre_data: SemestreModel
    ) -> Optional[Semestre]:
        """Update semester"""
        with DatabaseSession() as session:
            semestre = (
                session.query(Semestre).filter(Semestre.id == semestre_id).first()
            )
            if semestre:
                semestre.nome = semestre_data.nome
                semestre.status = semestre_data.status
                return semestre
            return None

    @staticmethod
    def delete_semestre(semestre_id: int) -> bool:
        """Delete semester"""
        with DatabaseSession() as session:
            semestre = (
                session.query(Semestre).filter(Semestre.id == semestre_id).first()
            )
            if semestre:
                session.delete(semestre)
                return True
            return False

    # Utility Methods
    @staticmethod
    def check_database_exists() -> bool:
        """Check if database file exists and is valid"""
        from database import get_database_info

        db_info = get_database_info()
        return db_info["is_connected"] and db_info["tables_count"] > 0

    @staticmethod
    def get_database_stats() -> Dict[str, int]:
        """Get database statistics"""
        with DatabaseSession() as session:
            return {
                "campus": session.query(Campus).count(),
                "predios": session.query(Predio).count(),
                "salas": session.query(Sala).count(),
                "tipos_sala": session.query(TipoSala).count(),
                "caracteristicas": session.query(Caracteristica).count(),
                "dias_semana": session.query(DiaSemana).count(),
                "horarios_bloco": session.query(HorarioBloco).count(),
                "semestres": session.query(Semestre).count(),
                "demandas": session.query(Demanda).count(),
                "regras": session.query(Regra).count(),
                "alocacoes_semestrais": session.query(AlocacaoSemestral).count(),
                "reservas_esporadicas": session.query(ReservaEsporadica).count(),
                "usuarios": session.query(Usuario).count(),
            }
