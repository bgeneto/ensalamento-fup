from typing import Dict, Set, Any, List
import logging
from sqlalchemy.exc import IntegrityError

from src.config.database import get_db_session
import re
from src.services.oferta_api import fetch_ofertas, OfertaAPIError
from src.repositories.semestre import SemestreRepository
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.professor import ProfessorRepository
from src.schemas.academic import DemandaCreate, ProfessorCreate, SemestreCreate
from src.utils.sigaa_parser import SigaaScheduleParser


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
    Create a new semester and set it as active, deactivating all others.

    Args:
        semester_name: Name of the semester in format "YEAR-SEMI" (e.g., "2025-2")

    Returns:
        Dict with 'success', 'message', and 'semester' keys if successful

    Raises:
        ValueError: If validation fails
        RuntimeError: If operation fails
    """
    # Validate seminar format - should be YEAR-SEMI (e.g., 2026-1, 2026-2)
    if not re.match(r"^\d{4}-\d+$", semester_name.strip()):
        raise ValueError("Formato inválido. Use o formato ANO-SEM (ex: 2026-2)")

    # Check length constraints
    clean_name = semester_name.strip()
    if len(clean_name) < 5:
        raise ValueError("Nome do semestre deve ter pelo menos 5 caracteres")
    if len(clean_name) > 50:
        raise ValueError("Nome do semestre deve ter no máximo 50 caracteres")

    logger = logging.getLogger(__name__)

    with get_db_session() as session:
        repo = SemestreRepository(session)

        # Check if semester already exists
        existing = repo.get_by_name(clean_name)
        if existing:
            raise ValueError(f"Semestre '{clean_name}' já existe")

        try:
            # Create new semester with active status
            new_semester = repo.create({"nome": clean_name, "status": True})
            logger.info(f"Created new semester: {clean_name} (ID: {new_semester.id})")

            # Deactivate all existing semesters
            all_semesters = repo.get_all()
            deactivated_count = 0

            for sem in all_semesters:
                if sem.nome != clean_name and sem.status == True:
                    update_dto = SemestreUpdate(status=False)
                    repo.update(sem.id, update_dto)
                    deactivated_count += 1
                    logger.info(f"Deactivated semester: {sem.nome} (ID: {sem.id})")

            return {
                "success": True,
                "message": f"Semestre '{clean_name}' criado e definido como ativo. {deactivated_count} semestres anteriores foram desativados.",
                "semester": new_semester,
            }

        except Exception as e:
            logger.error(f"Failed to create semester '{clean_name}': {str(e)}")
            session.rollback()
            raise RuntimeError(f"Erro ao criar semestre: {str(e)}")
