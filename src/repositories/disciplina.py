"""Repository for Demanda (Course Demand) operations."""

from typing import List, Optional, Set

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.models.academic import Demanda
from src.models.allocation import AlocacaoSemestral
from src.repositories.base import BaseRepository
from src.schemas.academic import DemandaCreate, DemandaRead


class DisciplinaRepository(BaseRepository[Demanda, DemandaRead]):
    """Repository for Demanda CRUD and queries."""

    def __init__(self, session: Session):
        """Initialize DisciplinaRepository.

        Args:
            session: SQLAlchemy session
        """
        super().__init__(session, Demanda)

    def orm_to_dto(self, orm_obj: Demanda) -> DemandaRead:
        """Convert ORM Demanda model to DemandaRead DTO.

        Args:
            orm_obj: Demanda ORM model instance

        Returns:
            DemandaRead DTO
        """
        return DemandaRead(
            id=orm_obj.id,
            semestre_id=orm_obj.semestre_id,
            codigo_disciplina=orm_obj.codigo_disciplina,
            nome_disciplina=orm_obj.nome_disciplina,
            professores_disciplina=orm_obj.professores_disciplina or "",
            turma_disciplina=orm_obj.turma_disciplina or "",
            vagas_disciplina=orm_obj.vagas_disciplina,
            horario_sigaa_bruto=orm_obj.horario_sigaa_bruto,
            id_oferta_externo=orm_obj.id_oferta_externo,
            codigo_curso=orm_obj.codigo_curso or "",
            origem=orm_obj.origem,
            sync_status=orm_obj.sync_status,
            api_payload_hash=orm_obj.api_payload_hash,
            api_snapshot_json=orm_obj.api_snapshot_json or {},
            local_overrides_json=orm_obj.local_overrides_json or {},
            last_seen_in_api_at=orm_obj.last_seen_in_api_at,
            last_synced_at=orm_obj.last_synced_at,
            removed_from_api_at=orm_obj.removed_from_api_at,
            preservar_local_em_remocao_api=orm_obj.preservar_local_em_remocao_api,
            revalidation_required=orm_obj.revalidation_required,
            created_at=getattr(orm_obj, "created_at", None),
            updated_at=getattr(orm_obj, "updated_at", None),
        )

    def dto_to_orm_create(self, dto: DemandaCreate) -> Demanda:
        """Create a Demanda ORM instance from a DemandaCreate DTO or plain dict.

        This method is robust to receiving either a Pydantic model or a dict
        (some callers build dicts). It maps expected fields and returns an
        unsaved Demanda instance ready to be added to a session.
        """

        # helper to support both pydantic models and plain dicts
        def _get(key, default=None):
            if hasattr(dto, key):
                return getattr(dto, key)
            if isinstance(dto, dict):
                return dto.get(key, default)
            return default

        semestre_id = _get("semestre_id")
        codigo = _get("codigo_disciplina")
        nome = _get("nome_disciplina")
        professores = _get("professores_disciplina") or ""
        turma = _get("turma_disciplina") or ""
        vagas = _get("vagas_disciplina") or 0
        horario = _get("horario_sigaa_bruto") or ""
        id_oferta_externo = _get("id_oferta_externo")
        codigo_curso = _get("codigo_curso") or ""
        explicitly_set_fields = getattr(dto, "model_fields_set", set())
        origem = _get("origem") if "origem" in explicitly_set_fields else None
        if not origem:
            origem = "api" if id_oferta_externo else "manual"

        sync_status = (
            _get("sync_status") if "sync_status" in explicitly_set_fields else None
        )
        if not sync_status:
            sync_status = "active" if origem == "api" else "manual"
        api_payload_hash = _get("api_payload_hash")
        api_snapshot_json = _get("api_snapshot_json") or {}
        local_overrides_json = _get("local_overrides_json") or {}
        last_seen_in_api_at = _get("last_seen_in_api_at")
        last_synced_at = _get("last_synced_at")
        removed_from_api_at = _get("removed_from_api_at")
        preservar_local_em_remocao_api = bool(
            _get("preservar_local_em_remocao_api", False)
        )
        revalidation_required = bool(_get("revalidation_required", False))

        return Demanda(
            semestre_id=semestre_id,
            codigo_disciplina=codigo,
            nome_disciplina=nome,
            professores_disciplina=professores,
            turma_disciplina=turma,
            vagas_disciplina=vagas,
            horario_sigaa_bruto=horario,
            id_oferta_externo=id_oferta_externo,
            codigo_curso=codigo_curso,
            origem=origem,
            sync_status=sync_status,
            api_payload_hash=api_payload_hash,
            api_snapshot_json=api_snapshot_json,
            local_overrides_json=local_overrides_json,
            last_seen_in_api_at=last_seen_in_api_at,
            last_synced_at=last_synced_at,
            removed_from_api_at=removed_from_api_at,
            preservar_local_em_remocao_api=preservar_local_em_remocao_api,
            revalidation_required=revalidation_required,
        )

    def set_external_id_for_existing(
        self, semestre_id: int, codigo: str, turma: str, external_id: str
    ) -> bool:
        """If a demanda exists matching semestre+codigo+turma, set its id_oferta_externo and return True.

        Returns True if an update was made, False otherwise.
        """
        orm_obj = (
            self.session.query(Demanda)
            .filter(
                (Demanda.semestre_id == semestre_id)
                & (Demanda.codigo_disciplina == codigo)
                & (Demanda.turma_disciplina == turma)
            )
            .first()
        )
        if not orm_obj:
            return False
        orm_obj.id_oferta_externo = external_id
        self.session.commit()
        return True

    # ========================================================================
    # DOMAIN-SPECIFIC QUERY METHODS
    # ========================================================================

    def get_by_codigo(self, codigo: str) -> Optional[DemandaRead]:
        """Get course demand by course code.

        Args:
            codigo: Course code (e.g., 'CIC0001')

        Returns:
            DemandaRead DTO or None if not found
        """
        orm_obj = (
            self.session.query(Demanda)
            .filter(Demanda.codigo_disciplina == codigo)
            .first()
        )
        if orm_obj:
            return self.orm_to_dto(orm_obj)
        return None

    def get_by_semestre(
        self, semestre_id: int, include_removed: bool = True
    ) -> List[DemandaRead]:
        """Get all course demands in a specific semester.

        Args:
            semestre_id: Semester ID

        Returns:
            List of DemandaRead DTOs sorted by course code
        """
        query = self.session.query(Demanda).filter(Demanda.semestre_id == semestre_id)
        if not include_removed:
            query = query.filter(Demanda.sync_status != "removed_in_api")
        orm_objs = query.order_by(Demanda.codigo_disciplina).all()
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_visible_for_allocation(self, semestre_id: int) -> List[DemandaRead]:
        """Get demands visible to allocation workflows.

        Removed API demands remain visible only when they already have allocations.
        """
        orm_objs = (
            self.session.query(Demanda)
            .outerjoin(AlocacaoSemestral, AlocacaoSemestral.demanda_id == Demanda.id)
            .filter(Demanda.semestre_id == semestre_id)
            .filter(
                or_(
                    Demanda.sync_status != "removed_in_api",
                    AlocacaoSemestral.id.isnot(None),
                )
            )
            .distinct()
            .order_by(Demanda.codigo_disciplina)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_professor_name(self, professor_name: str) -> List[DemandaRead]:
        """Get all course demands for a specific professor.

        Args:
            professor_name: Professor name (partial match)

        Returns:
            List of DemandaRead DTOs sorted by course code
        """
        orm_objs = (
            self.session.query(Demanda)
            .filter(Demanda.professores_disciplina.ilike(f"%{professor_name}%"))
            .order_by(Demanda.codigo_disciplina)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def search(self, query: str) -> List[DemandaRead]:
        """Search courses by code or name (case-insensitive).

        Args:
            query: Search query (partial match)

        Returns:
            List of DemandaRead DTOs sorted by course code
        """
        pattern = f"%{query}%"
        orm_objs = (
            self.session.query(Demanda)
            .filter(
                or_(
                    Demanda.codigo_disciplina.ilike(pattern),
                    Demanda.nome_disciplina.ilike(pattern),
                )
            )
            .order_by(Demanda.codigo_disciplina)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def search_by_name(self, name_pattern: str) -> List[DemandaRead]:
        """Search courses by name (case-insensitive, partial match).

        Args:
            name_pattern: Course name pattern

        Returns:
            List of DemandaRead DTOs sorted by course code
        """
        orm_objs = (
            self.session.query(Demanda)
            .filter(Demanda.nome_disciplina.ilike(f"%{name_pattern}%"))
            .order_by(Demanda.codigo_disciplina)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_large_courses(self, min_vagas: int) -> List[DemandaRead]:
        """Get courses with enrollment above threshold.

        Args:
            min_vagas: Minimum number of students

        Returns:
            List of DemandaRead DTOs sorted by enrollment (highest first)
        """
        orm_objs = (
            self.session.query(Demanda)
            .filter(Demanda.vagas_disciplina >= min_vagas)
            .order_by(Demanda.vagas_disciplina.desc())
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_small_courses(self, max_vagas: int) -> List[DemandaRead]:
        """Get courses with enrollment below threshold.

        Args:
            max_vagas: Maximum number of students

        Returns:
            List of DemandaRead DTOs sorted by enrollment (lowest first)
        """
        orm_objs = (
            self.session.query(Demanda)
            .filter(Demanda.vagas_disciplina <= max_vagas)
            .order_by(Demanda.vagas_disciplina)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def _get_codigos_sem_sala(self) -> Set[str]:
        """Discipline codes excluded from allocation via DISCIPLINA_SEM_SALA rules."""
        from src.repositories.regra import RegraRepository

        return RegraRepository(self.session).get_codigos_sem_sala()

    def get_allocatable(self, semestre_id: int) -> List[DemandaRead]:
        """Get courses that should be allocated.

        Excludes disciplines with a DISCIPLINA_SEM_SALA rule.

        Args:
            semestre_id: Semester ID

        Returns:
            List of allocatable course demands
        """
        visible = self.get_visible_for_allocation(semestre_id)
        excluded = self._get_codigos_sem_sala()
        if not excluded:
            return visible
        return [d for d in visible if d.codigo_disciplina not in excluded]

    def get_by_semestre_and_external_id(
        self, semestre_id: int, id_externo: str
    ) -> Optional[DemandaRead]:
        """Get demanda by semester and external oferta id (id_oferta_externo)."""
        orm_obj = (
            self.session.query(Demanda)
            .filter(
                (Demanda.semestre_id == semestre_id)
                & (Demanda.id_oferta_externo == id_externo)
            )
            .first()
        )
        if orm_obj:
            return self.orm_to_dto(orm_obj)
        return None

    def get_skip_allocation(self, semestre_id: int) -> List[DemandaRead]:
        """Get courses excluded from allocation by DISCIPLINA_SEM_SALA rules.

        Args:
            semestre_id: Semester ID

        Returns:
            List of DemandaRead DTOs whose discipline code does not require a room
        """
        excluded = self._get_codigos_sem_sala()
        if not excluded:
            return []
        return [
            d
            for d in self.get_by_semestre(semestre_id)
            if d.codigo_disciplina in excluded
        ]

    def get_statistics_for_semester(self, semestre_id: int) -> dict:
        """Get course demand statistics for a semester.

        Args:
            semestre_id: Semester ID

        Returns:
            Dictionary with statistics:
            - total_demands: Total number of demands
            - total_vagas: Total enrollment across all courses
            - avg_vagas: Average students per course
            - max_vagas: Largest course enrollment
            - min_vagas: Smallest course enrollment
            - demands_over_50: Number of demands with 50+ students
            - demands_over_100: Number of demands with 100+ students
            - skip_allocation: Number of demands marked to skip
        """
        demands = self.get_by_semestre(semestre_id)

        if not demands:
            return {
                "total_demands": 0,
                "total_vagas": 0,
                "avg_vagas": 0,
                "max_vagas": 0,
                "min_vagas": 0,
                "demands_over_50": 0,
                "demands_over_100": 0,
                "skip_allocation": 0,
            }

        vagas = [d.vagas_disciplina for d in demands]
        skip_count = len(self.get_skip_allocation(semestre_id))

        return {
            "total_demands": len(demands),
            "total_vagas": sum(vagas),
            "avg_vagas": sum(vagas) / len(vagas) if vagas else 0,
            "max_vagas": max(vagas) if vagas else 0,
            "min_vagas": min(vagas) if vagas else 0,
            "demands_over_50": len([v for v in vagas if v >= 50]),
            "demands_over_100": len([v for v in vagas if v >= 100]),
            "skip_allocation": skip_count,
        }

    def get_all_by_semestre_sorted(self, semestre_id: int) -> List[DemandaRead]:
        """Get all course demands in semester, sorted by code.

        Args:
            semestre_id: Semester ID

        Returns:
            List of DemandaRead DTOs
        """
        return self.get_by_semestre(semestre_id)

    def get_unique_course_codes(self) -> List[str]:
        """Get unique course codes from all demandas.

        Returns a list of unique codigo_curso values, sorted alphabetically.
        Used to populate course filtering options.

        Returns:
            List of unique course codes (codigo_curso)
        """
        from sqlalchemy import distinct

        from src.models.academic import Demanda

        result = (
            self.session.query(distinct(Demanda.codigo_curso))
            .filter(Demanda.codigo_curso != "")  # Exclude empty codes
            .filter(Demanda.codigo_curso.isnot(None))  # Exclude null codes
            .order_by(Demanda.codigo_curso)
            .all()
        )

        # Flatten the result (distinct returns tuples)
        return [row[0] for row in result]
