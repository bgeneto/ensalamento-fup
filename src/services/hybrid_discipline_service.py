"""
Hybrid Discipline Detection Service - Phase 0 of Allocation Pipeline

Detects and caches information about hybrid disciplines (those requiring
both classroom and lab/specialized room allocations) based on historical data.

This enables proper per-day scoring so that lab time slots are allocated
to labs and classroom time slots to regular classrooms.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from sqlalchemy.orm import Session

from src.repositories.alocacao import AlocacaoRepository

logger = logging.getLogger(__name__)


# Regular classroom type ID (Sala de Aula)
REGULAR_CLASSROOM_TYPE_ID = 2
HYBRID_HISTORY_SEMESTER_LIMIT = 4


@dataclass
class HybridDisciplineInfo:
    """Information about a detected hybrid discipline."""

    codigo_disciplina: str
    turma_disciplina: str = ""
    lab_days: List[int] = field(
        default_factory=list
    )  # Days that historically used labs
    classroom_days: List[int] = field(
        default_factory=list
    )  # Days that only used classrooms
    lab_room_types: Set[int] = field(
        default_factory=set
    )  # tipo_sala_ids for non-classroom rooms
    historical_lab_rooms: Dict[int, List[int]] = field(
        default_factory=dict
    )  # {day_id: [sala_ids used as labs]}
    slot_requirements: Dict[tuple[int, str], str] = field(default_factory=dict)
    lab_room_types_by_slot: Dict[tuple[int, str], Set[int]] = field(
        default_factory=dict
    )
    historical_lab_rooms_by_slot: Dict[tuple[int, str], List[int]] = field(
        default_factory=dict
    )
    detection_semester_id: int = 0  # Semester used for detection


@dataclass
class HybridDetectionResult:
    """Result of the hybrid detection phase."""

    detected_count: int = 0
    hybrid_disciplines: List[str] = field(default_factory=list)
    detection_semester_id: int = 0
    details: Dict[str, HybridDisciplineInfo] = field(default_factory=dict)


class HybridDisciplineDetectionService:
    """
    Service for detecting and caching hybrid discipline information.

    A hybrid discipline is one that:
    1. Has allocations in 2+ different rooms in the most recent semester
    2. At least one of those rooms is NOT a regular classroom (tipo_sala_id != 2)

    This service:
    - Detects hybrid disciplines from the most recent historical semester
    - Caches the results in memory for use during allocation
    - Provides per-day information about which days should use labs vs classrooms
    """

    def __init__(self, session: Session):
        """Initialize with required repositories."""
        self.session = session
        self.alocacao_repo = AlocacaoRepository(session)

        # In-memory cache
        self._cache: Dict[str, HybridDisciplineInfo] = {}
        self._detection_semester_id: Optional[int] = None
        self._is_initialized: bool = False

    def _normalize_turma(self, turma_disciplina: Optional[str]) -> str:
        raw = str(turma_disciplina or "").strip()
        if not raw:
            return ""
        return raw.lstrip("0") or "0"

    def build_offering_key(
        self, codigo_disciplina: str, turma_disciplina: Optional[str] = None
    ) -> str:
        code = str(codigo_disciplina or "").strip().upper()
        turma = self._normalize_turma(turma_disciplina)
        return f"{code}::{turma}" if turma else code

    def _normalize_text(self, text: Optional[str]) -> str:
        return (
            str(text or "")
            .strip()
            .lower()
            .replace("á", "a")
            .replace("à", "a")
            .replace("â", "a")
            .replace("ã", "a")
            .replace("é", "e")
            .replace("ê", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ô", "o")
            .replace("õ", "o")
            .replace("ú", "u")
            .replace("ç", "c")
        )

    def _is_laboratory_type_name(self, tipo_sala_nome: Optional[str]) -> bool:
        normalized = self._normalize_text(tipo_sala_nome)
        return "laboratorio" in normalized

    def _resolve_cache_key(
        self, codigo_disciplina: str, turma_disciplina: Optional[str] = None
    ) -> str:
        if turma_disciplina is None and "::" in str(codigo_disciplina):
            return str(codigo_disciplina)
        return self.build_offering_key(codigo_disciplina, turma_disciplina)

    def _get_historical_semester_ids(self, detection_semester_id: int) -> List[int]:
        """Return the recent semester IDs considered for hybrid detection."""
        return self.alocacao_repo.get_recent_semester_ids_with_allocations(
            up_to_semester_id=detection_semester_id,
            limit=HYBRID_HISTORY_SEMESTER_LIMIT,
        )

    def _fetch_historical_allocations(self, semester_ids: List[int]):
        from src.models.academic import Demanda
        from src.models.allocation import AlocacaoSemestral
        from src.models.inventory import Sala, TipoSala

        if not semester_ids:
            return []

        return (
            self.session.query(
                AlocacaoSemestral.semestre_id,
                Demanda.codigo_disciplina,
                Demanda.turma_disciplina,
                AlocacaoSemestral.dia_semana_id,
                AlocacaoSemestral.codigo_bloco,
                Sala.id.label("sala_id"),
                Sala.tipo_sala_id,
                TipoSala.nome.label("tipo_sala_nome"),
            )
            .join(Demanda, AlocacaoSemestral.demanda_id == Demanda.id)
            .join(Sala, AlocacaoSemestral.sala_id == Sala.id)
            .join(TipoSala, Sala.tipo_sala_id == TipoSala.id)
            .filter(AlocacaoSemestral.semestre_id.in_(semester_ids))
            .all()
        )

    def detect_hybrid_disciplines(
        self, detection_semester_id: Optional[int] = None
    ) -> HybridDetectionResult:
        """
        Detect all hybrid disciplines from the most recent semester.

        Args:
            detection_semester_id: Specific semester to analyze.
                                  If None, uses the most recent semester.

        Returns:
            HybridDetectionResult with detection details
        """
        # Determine detection semester
        if detection_semester_id is None:
            detection_semester_id = self.alocacao_repo.get_most_recent_semester_id()

        if not detection_semester_id:
            self._cache.clear()
            self._detection_semester_id = None
            self._is_initialized = True
            logger.warning("No semesters found for hybrid detection")
            return HybridDetectionResult()

        self._detection_semester_id = detection_semester_id
        logger.info(
            f"Starting hybrid discipline detection for semester {detection_semester_id}"
        )

        # Clear previous cache
        self._cache.clear()

        historical_semester_ids = self._get_historical_semester_ids(
            detection_semester_id
        )
        historical_rows = self._fetch_historical_allocations(historical_semester_ids)

        logger.info(
            "Hybrid detection historical window: last %s semester(s) with allocations up to %s -> %s",
            HYBRID_HISTORY_SEMESTER_LIMIT,
            detection_semester_id,
            historical_semester_ids,
        )

        offerings: Dict[str, Dict] = {}
        for row in historical_rows:
            key = self.build_offering_key(
                row.codigo_disciplina,
                row.turma_disciplina,
            )
            offering = offerings.setdefault(
                key,
                {
                    "codigo_disciplina": row.codigo_disciplina,
                    "turma_disciplina": self._normalize_turma(row.turma_disciplina),
                    "room_ids": set(),
                    "families": set(),
                    "slots": {},
                },
            )

            offering["room_ids"].add(row.sala_id)

            room_family = "other"
            if row.tipo_sala_id == REGULAR_CLASSROOM_TYPE_ID:
                room_family = "classroom"
            elif self._is_laboratory_type_name(row.tipo_sala_nome):
                room_family = "lab"

            if room_family in {"classroom", "lab"}:
                offering["families"].add(room_family)

            slot_key = (row.dia_semana_id, row.codigo_bloco[0])
            slot_history = offering["slots"].setdefault(slot_key, {})
            semester_slot = slot_history.setdefault(
                row.semestre_id,
                {
                    "classroom_count": 0,
                    "lab_count": 0,
                    "lab_room_types": set(),
                    "lab_room_ids": set(),
                },
            )

            if room_family == "classroom":
                semester_slot["classroom_count"] += 1
            elif room_family == "lab":
                semester_slot["lab_count"] += 1
                semester_slot["lab_room_types"].add(row.tipo_sala_id)
                semester_slot["lab_room_ids"].add(row.sala_id)

        for key, offering in offerings.items():
            if len(offering["room_ids"]) < 2:
                continue
            if not {"classroom", "lab"}.issubset(offering["families"]):
                continue

            slot_requirements: Dict[tuple[int, str], str] = {}
            lab_room_types_by_slot: Dict[tuple[int, str], Set[int]] = {}
            historical_lab_rooms_by_slot: Dict[tuple[int, str], List[int]] = {}
            lab_days: Set[int] = set()
            classroom_days: Set[int] = set()

            for slot_key, semester_history in offering["slots"].items():
                relevant_semesters = [
                    semester_id
                    for semester_id, slot_data in semester_history.items()
                    if slot_data["classroom_count"] > 0 or slot_data["lab_count"] > 0
                ]
                if not relevant_semesters:
                    continue

                latest_semester = max(relevant_semesters)
                latest_data = semester_history[latest_semester]

                requirement = None
                if latest_data["lab_count"] > latest_data["classroom_count"]:
                    requirement = "lab"
                elif latest_data["classroom_count"] > latest_data["lab_count"]:
                    requirement = "classroom"
                elif latest_data["lab_count"] > 0:
                    requirement = "lab"
                elif latest_data["classroom_count"] > 0:
                    requirement = "classroom"

                if requirement is None:
                    continue

                slot_requirements[slot_key] = requirement
                if requirement == "lab":
                    lab_days.add(slot_key[0])
                    room_types = set()
                    room_ids = set()
                    for slot_data in semester_history.values():
                        room_types.update(slot_data["lab_room_types"])
                        room_ids.update(slot_data["lab_room_ids"])
                    if room_types:
                        lab_room_types_by_slot[slot_key] = room_types
                    historical_lab_rooms_by_slot[slot_key] = sorted(room_ids)
                else:
                    classroom_days.add(slot_key[0])

            if not {"lab", "classroom"}.issubset(set(slot_requirements.values())):
                continue

            historical_lab_rooms: Dict[int, List[int]] = {}
            lab_room_types: Set[int] = set()
            for slot_key, room_ids in historical_lab_rooms_by_slot.items():
                day_id, _turno = slot_key
                historical_lab_rooms.setdefault(day_id, [])
                historical_lab_rooms[day_id] = sorted(
                    set(historical_lab_rooms[day_id]).union(room_ids)
                )
            for room_types in lab_room_types_by_slot.values():
                lab_room_types.update(room_types)

            self._cache[key] = HybridDisciplineInfo(
                codigo_disciplina=offering["codigo_disciplina"],
                turma_disciplina=offering["turma_disciplina"],
                lab_days=sorted(lab_days),
                classroom_days=sorted(classroom_days),
                lab_room_types=lab_room_types,
                historical_lab_rooms=historical_lab_rooms,
                slot_requirements=slot_requirements,
                lab_room_types_by_slot=lab_room_types_by_slot,
                historical_lab_rooms_by_slot=historical_lab_rooms_by_slot,
                detection_semester_id=detection_semester_id,
            )

        hybrid_keys = sorted(self._cache.keys())

        logger.info(f"Found {len(hybrid_keys)} hybrid disciplines")

        self._is_initialized = True

        return HybridDetectionResult(
            detected_count=len(hybrid_keys),
            hybrid_disciplines=hybrid_keys,
            detection_semester_id=detection_semester_id,
            details=self._cache.copy(),
        )

    def resolve_detection_semester(
        self, current_semester_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Resolve the historical semester that should drive hybrid detection.

        The current semester is excluded when possible because it may be empty or
        partially allocated while the allocation workflow is still in progress.
        """
        detection_semester_id = (
            self.alocacao_repo.get_most_recent_semester_with_allocations(
                exclude_semester_id=current_semester_id
            )
        )

        if detection_semester_id:
            return detection_semester_id

        return self.alocacao_repo.get_most_recent_semester_with_allocations()

    def is_hybrid(
        self, codigo_disciplina: str, turma_disciplina: Optional[str] = None
    ) -> bool:
        """
        Check if a discipline code is classified as hybrid.

        Args:
            codigo_disciplina: Discipline code to check

        Returns:
            True if discipline is hybrid, False otherwise
        """
        if not self._is_initialized:
            logger.warning(
                "Hybrid detection not initialized - call detect_hybrid_disciplines() first"
            )
            return False

        return (
            self._resolve_cache_key(codigo_disciplina, turma_disciplina) in self._cache
        )

    def get_hybrid_info(
        self, codigo_disciplina: str, turma_disciplina: Optional[str] = None
    ) -> Optional[HybridDisciplineInfo]:
        """
        Get hybrid discipline info if classified as hybrid.

        Args:
            codigo_disciplina: Discipline code

        Returns:
            HybridDisciplineInfo if hybrid, None otherwise
        """
        return self._cache.get(
            self._resolve_cache_key(codigo_disciplina, turma_disciplina)
        )

    def is_hybrid_demand(self, demanda: object) -> bool:
        return self.is_hybrid(
            getattr(demanda, "codigo_disciplina", ""),
            getattr(demanda, "turma_disciplina", None),
        )

    def get_hybrid_info_for_demand(
        self, demanda: object
    ) -> Optional[HybridDisciplineInfo]:
        return self.get_hybrid_info(
            getattr(demanda, "codigo_disciplina", ""),
            getattr(demanda, "turma_disciplina", None),
        )

    def get_slot_requirement(
        self,
        codigo_disciplina: str,
        turma_disciplina: Optional[str],
        day_id: int,
        turno: str,
    ) -> Optional[str]:
        info = self.get_hybrid_info(codigo_disciplina, turma_disciplina)
        if not info:
            return None
        return info.slot_requirements.get((day_id, turno))

    def get_lab_room_types_for_slot(
        self,
        codigo_disciplina: str,
        turma_disciplina: Optional[str],
        day_id: int,
        turno: str,
    ) -> Set[int]:
        info = self.get_hybrid_info(codigo_disciplina, turma_disciplina)
        if not info:
            return set()
        return set(info.lab_room_types_by_slot.get((day_id, turno), set()))

    def get_lab_days_for_discipline(
        self, codigo_disciplina: str, turma_disciplina: Optional[str] = None
    ) -> List[int]:
        """
        Get days that historically used labs for this discipline.

        Args:
            codigo_disciplina: Discipline code

        Returns:
            List of day IDs (2=MON, 3=TUE, etc.) that are lab days
        """
        info = self.get_hybrid_info(codigo_disciplina, turma_disciplina)
        return info.lab_days if info else []

    def get_classroom_days_for_discipline(
        self, codigo_disciplina: str, turma_disciplina: Optional[str] = None
    ) -> List[int]:
        """
        Get days that historically only used classrooms for this discipline.

        Args:
            codigo_disciplina: Discipline code

        Returns:
            List of day IDs (2=MON, 3=TUE, etc.) that are classroom-only days
        """
        info = self.get_hybrid_info(codigo_disciplina, turma_disciplina)
        return info.classroom_days if info else []

    def is_lab_day(
        self,
        codigo_disciplina: str,
        day_id: int,
        turma_disciplina: Optional[str] = None,
    ) -> bool:
        """
        Check if a specific day is a lab day for a discipline.

        Args:
            codigo_disciplina: Discipline code
            day_id: Day ID (2=MON, 3=TUE, etc.)

        Returns:
            True if this day should use a lab, False otherwise
        """
        info = self.get_hybrid_info(codigo_disciplina, turma_disciplina)
        if not info:
            return False
        return day_id in info.lab_days

    def get_historical_lab_rooms(
        self,
        codigo_disciplina: str,
        day_id: int,
        turma_disciplina: Optional[str] = None,
        turno: Optional[str] = None,
    ) -> List[int]:
        """
        Get historically used lab room IDs for a discipline on a specific day.

        Args:
            codigo_disciplina: Discipline code
            day_id: Day ID (2=MON, 3=TUE, etc.)

        Returns:
            List of sala_ids that were used as labs on this day
        """
        info = self.get_hybrid_info(codigo_disciplina, turma_disciplina)
        if not info:
            return []
        if turno is not None:
            return info.historical_lab_rooms_by_slot.get((day_id, turno), [])
        return info.historical_lab_rooms.get(day_id, [])

    def get_all_hybrid_codes(self) -> List[str]:
        """
        Get list of all detected hybrid discipline codes.

        Returns:
            List of discipline codes classified as hybrid
        """
        return list(self._cache.keys())

    def get_detection_summary(self) -> Dict:
        """
        Get a summary of the detection results for logging/reporting.

        Returns:
            Dict with detection summary
        """
        if not self._is_initialized:
            return {"initialized": False}

        return {
            "initialized": True,
            "detection_semester_id": self._detection_semester_id,
            "total_hybrid_disciplines": len(self._cache),
            "hybrid_codes": list(self._cache.keys()),
            "details": {
                code: {
                    "turma_disciplina": info.turma_disciplina,
                    "lab_days": info.lab_days,
                    "classroom_days": info.classroom_days,
                    "lab_room_types": list(info.lab_room_types),
                    "slot_requirements": {
                        f"{day_id}_{turno}": requirement
                        for (
                            day_id,
                            turno,
                        ), requirement in info.slot_requirements.items()
                    },
                }
                for code, info in self._cache.items()
            },
        }

    def clear_cache(self):
        """Clear the in-memory cache."""
        self._cache.clear()
        self._detection_semester_id = None
        self._is_initialized = False
        logger.debug("Hybrid discipline cache cleared")
