from typing import Dict, Set, Any, List
import logging
import re
from sqlalchemy.exc import IntegrityError

from src.config.database import get_db_session
from src.services.oferta_api import fetch_ofertas, OfertaAPIError
from src.repositories.semestre import SemestreRepository
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.professor import ProfessorRepository
from src.models.academic import Semestre
from src.schemas.academic import (
    DemandaCreate,
    ProfessorCreate,
    SemestreCreate,
    SemestreUpdate,
)
from src.utils.sigaa_parser import SigaaScheduleParser


def validate_semester_name(semester_name: str) -> str:
    """
    Validate semester name format and constraints.

    Args:
        semester_name: Semester name to validate

    Returns:
        str: Cleaned semester name if valid

    Raises:
        ValueError: If validation fails with descriptive message

    Format: YEAR-SEMI (e.g., 2026-1, 2026-2)
    """
    if not semester_name or not isinstance(semester_name, str):
        raise ValueError("Nome do semestre é obrigatório")

    clean_name = semester_name.strip()

    # Check length constraints
    if len(clean_name) < 5:
        raise ValueError("Nome do semestre deve ter pelo menos 5 caracteres")
    if len(clean_name) > 50:
        raise ValueError("Nome do semestre deve ter no máximo 50 caracteres")

    # Validate format - should be YEAR-SEMI (e.g., 2026-1, 2026-2)
    if not re.match(r"^\d{4}-\d+$", clean_name):
        raise ValueError(
            "Formato inválido. Use o formato AAAA-N (ex: 2026-1 ou 2025-2)"
        )

    return clean_name


parser = SigaaScheduleParser()


def _normalize_horario(text: str) -> str:
    if not text:
        return ""
    # Replace commas with spaces, collapse multiple spaces
    return " ".join(text.replace(",", " ").split())


def _extract_professores_string(prof_list: Any) -> str:
    names = [p.get("nome_perfil") for p in prof_list if p.get("nome_perfil")]
    return ", ".join(names)


def sync_semester_from_api(
    cod_semestre: str, cursos_ignorados: List[str] = None
) -> Dict[str, int]:
    """
    Sync ofertas for cod_semestre.
    Returns summary: {'created_semestre':0/1,'demandas':N,'professores':M,'skipped':K}
    """
    try:
        payload = fetch_ofertas(cod_semestre)
    except OfertaAPIError as e:
        raise

    semestre_name = payload.get("semestre", cod_semestre)
    ofertas = payload.get("ofertas", {}) or {}

    logger = logging.getLogger(__name__)

    summary = {
        "created_semestre": 0,
        "demandas": 0,
        "professores": 0,
        "skipped": 0,
        "skipped_details": [],
    }

    with get_db_session() as session:
        sem_repo = SemestreRepository(session)
        dem_repo = DisciplinaRepository(session)
        prof_repo = ProfessorRepository(session)

        semestre = sem_repo.get_by_name(semestre_name)
        if not semestre:
            semestre = sem_repo.create(
                {"nome": semestre_name, "status": "Planejamento"}
            )
            summary["created_semestre"] = 1

        # collect all professor names to provision later
        prof_names_to_provision: Set[str] = set()

        for oferta_key, oferta in ofertas.items():
            # Check if course should be ignored (filtering at sync time)
            codigo_curso = oferta.get("cod_curso", "")
            if cursos_ignorados and codigo_curso in cursos_ignorados:
                summary["skipped"] += 1
                detail = {
                    "oferta_key": str(oferta_key),
                    "codigo_curso": codigo_curso,
                    "codigo": oferta.get("cod_disciplina"),
                    "turma": oferta.get("cod_turma")
                    or oferta.get("turma_disciplina")
                    or "",
                    "reason": "curso_ignorado",
                }
                summary["skipped_details"].append(detail)
                logger.debug("Skipped oferta (curso ignorado): %s", detail)
                continue

            # idempotency: use oferta_key as id_oferta_externo (string)
            id_oferta_externo = str(oferta_key)

            codigo = oferta.get("cod_disciplina")
            nome = oferta.get("nome_disciplina")
            turma = oferta.get("cod_turma") or oferta.get("turma_disciplina") or ""
            vagas_text = oferta.get("vagas_turma") or "0"
            try:
                vagas = int(vagas_text)
            except Exception:
                vagas = 0

            horario_raw = oferta.get("horario_turma", "")
            horario = _normalize_horario(horario_raw)
            professores_list = oferta.get("professores", [])
            professores_disciplina = _extract_professores_string(professores_list)
            for p in professores_list:
                nomep = p.get("nome_perfil")
                if nomep:
                    prof_names_to_provision.add(nomep)

            # if demanda with same semestre_id + external id exists -> skip
            if dem_repo.get_by_semestre_and_external_id(semestre.id, id_oferta_externo):
                summary["skipped"] += 1
                detail = {
                    "oferta_key": id_oferta_externo,
                    "codigo": oferta.get("cod_disciplina"),
                    "turma": oferta.get("cod_turma")
                    or oferta.get("turma_disciplina")
                    or "",
                    "reason": "external_id_exists",
                }
                summary["skipped_details"].append(detail)
                logger.debug("Skipped oferta (external id exists): %s", detail)
                continue

            codigo_curso = oferta.get("cod_curso", "")

            dto: Dict[str, Any] = {
                "semestre_id": semestre.id,
                "codigo_disciplina": codigo,
                "nome_disciplina": nome,
                "turma_disciplina": turma,
                "vagas_disciplina": vagas,
                "horario_sigaa_bruto": horario,
                "professores_disciplina": professores_disciplina,
                "id_oferta_externo": id_oferta_externo,
                "codigo_curso": codigo_curso,
            }

            try:
                # Convert dict to DemandaCreate schema so repository dto_to_orm_create
                # can access attributes (expects a DTO-like object)
                demanda_dto = DemandaCreate(**dto)
                dem_repo.create(demanda_dto)
                summary["demandas"] += 1
            except IntegrityError as ie:
                session.rollback()
                summary["skipped"] += 1
                detail = {
                    "oferta_key": id_oferta_externo,
                    "codigo": codigo,
                    "turma": turma,
                    "reason": "integrity_error",
                    "message": str(ie),
                }
                summary["skipped_details"].append(detail)
                logger.warning("IntegrityError creating demanda, skipping: %s", detail)
            except Exception as e:
                # unexpected errors — record and re-raise after collecting
                session.rollback()
                summary["skipped"] += 1
                detail = {
                    "oferta_key": id_oferta_externo,
                    "codigo": codigo,
                    "turma": turma,
                    "reason": "exception",
                    "message": str(e),
                }
                summary["skipped_details"].append(detail)
                logger.exception("Exception while creating demanda: %s", detail)

        # Provision professors (idempotent)
        for nome in sorted(prof_names_to_provision):
            if not prof_repo.get_by_nome_completo(nome):
                prof_dto = ProfessorCreate(
                    nome_completo=nome, tem_baixa_mobilidade=False
                )
                prof_repo.create(prof_dto)
                summary["professores"] += 1

    return summary


def create_and_activate_semester(semester_name: str) -> Dict[str, Any]:
    """
    Create a new semester and set it as active (it will have the highest ID),
    deactivating all others.

    Args:
        semester_name: Name of the semester in format "YEAR-SEMI" (e.g., "2025-2", "2025.1")

    Returns:
        Dict with 'success', 'message', and 'semester' keys if successful

    Raises:
        ValueError: If validation fails
        RuntimeError: If operation fails
    """
    # Use shared validation function
    clean_name = validate_semester_name(semester_name)

    logger = logging.getLogger(__name__)

    with get_db_session() as session:
        repo = SemestreRepository(session)

        # Check if semester already exists
        existing = repo.get_by_name(clean_name)
        if existing:
            raise ValueError(f"Semestre '{clean_name}' já existe")

        try:
            # Deactivate ALL existing semesters first
            deactivated_count = (
                session.query(Semestre)
                .filter(Semestre.status == True)
                .update({"status": False})
            )
            logger.info(f"Deactivated {deactivated_count} existing active semesters")

            # Create the new semester as active (it will have the highest ID)
            new_semester_orm = Semestre(
                nome=clean_name, status=True  # Explicitly set to True
            )
            session.add(new_semester_orm)
            session.commit()  # Force commit
            session.refresh(new_semester_orm)  # Ensure we have the ID

            # Convert to DTO
            new_semester = repo.orm_to_dto(new_semester_orm)

            logger.info(
                f"Created and activated new semester: {clean_name} (ID: {new_semester.id}, Status: {new_semester.status})"
            )

            return {
                "success": True,
                "message": f"Semestre '{clean_name}' criado e definido como ativo. {deactivated_count} semestres anteriores foram desativados.",
                "semester": new_semester,
            }

        except Exception as e:
            logger.error(f"Failed to create semester '{clean_name}': {str(e)}")
            session.rollback()
            raise RuntimeError(f"Erro ao criar semestre: {str(e)}")
