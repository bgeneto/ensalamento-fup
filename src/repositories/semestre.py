from typing import Optional

from sqlalchemy.orm import Session

from src.models.academic import Semestre
from src.repositories.base import BaseRepository
from src.schemas.academic import SemestreCreate, SemestreRead


class SemestreRepository(BaseRepository[Semestre, SemestreRead]):
    def __init__(self, session: Session):
        super().__init__(session, Semestre)

    def orm_to_dto(self, orm_obj: Semestre) -> SemestreRead:
        return SemestreRead(
            id=orm_obj.id,
            nome=orm_obj.nome,
            status=orm_obj.status,
            data_inicial=orm_obj.data_inicial,
            data_final=orm_obj.data_final,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def dto_to_orm_create(self, dto: SemestreCreate) -> Semestre:
        return Semestre(
            nome=dto.nome,
            status=dto.status,
            data_inicial=dto.data_inicial,
            data_final=dto.data_final,
        )

    def get_by_name(self, nome: str) -> Optional[SemestreRead]:
        orm_obj = self.session.query(Semestre).filter(Semestre.nome == nome).first()
        if orm_obj:
            return self.orm_to_dto(orm_obj)
        return None

    def create(self, dto: dict):
        # Accept dict style create for convenience
        obj = Semestre(
            nome=dto.get("nome"),
            status=dto.get("status", 1),
            data_inicial=dto.get("data_inicial"),
            data_final=dto.get("data_final"),
        )
        self.session.add(obj)
        self.session.commit()
        return self.orm_to_dto(obj)

    def get_active(self) -> Optional[SemestreRead]:
        """Return the currently active semester, if any."""
        orm_obj = self.session.query(Semestre).filter(Semestre.status.is_(True)).first()
        if orm_obj:
            return self.orm_to_dto(orm_obj)
        return None

    def activate_highest_id_semester(self) -> Optional[SemestreRead]:
        """
        Activate the semester with the highest ID and deactivate all others.
        This ensures only one semester is active at a time.

        Returns:
            SemestreRead: The activated semester DTO, or None if no semesters exist
        """
        # First, deactivate ALL semesters
        self.session.query(Semestre).update({"status": False})

        # Get semester with highest ID
        highest = self.session.query(Semestre).order_by(Semestre.id.desc()).first()

        if highest:
            # Activate it
            highest.status = True
            self.session.commit()
            return self.orm_to_dto(highest)

        self.session.commit()
        return None
