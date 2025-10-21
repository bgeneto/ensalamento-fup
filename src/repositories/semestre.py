from sqlalchemy.orm import Session
from typing import Optional

from src.models.academic import Semestre
from src.schemas.academic import SemestreRead, SemestreCreate
from src.repositories.base import BaseRepository


class SemestreRepository(BaseRepository[Semestre, SemestreRead]):
    def __init__(self, session: Session):
        super().__init__(session, Semestre)

    def orm_to_dto(self, orm_obj: Semestre) -> SemestreRead:
        return SemestreRead(
            id=orm_obj.id,
            nome=orm_obj.nome,
            status=orm_obj.status,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def dto_to_orm_create(self, dto: SemestreCreate) -> Semestre:
        return Semestre(nome=dto.nome, status=dto.status)

    def get_by_name(self, nome: str) -> Optional[SemestreRead]:
        orm_obj = self.session.query(Semestre).filter(Semestre.nome == nome).first()
        if orm_obj:
            return self.orm_to_dto(orm_obj)
        return None

    def create(self, dto: dict):
        # Accept dict style create for convenience
        obj = Semestre(nome=dto.get("nome"), status=dto.get("status", "Planejamento"))
        self.session.add(obj)
        self.session.commit()
        return self.orm_to_dto(obj)
