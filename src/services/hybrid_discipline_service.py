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


@dataclass
class HybridDisciplineInfo:
    """Information about a detected hybrid discipline."""

    codigo_disciplina: str
    lab_days: List[int] = field(default_factory=list)  # Days that historically used labs
    classroom_days: List[int] = field(
        default_factory=list
    )  # Days that only used classrooms
    lab_room_types: Set[int] = field(
        default_factory=set
    )  # tipo_sala_ids for non-classroom rooms
    historical_lab_rooms: Dict[int, List[int]] = field(
        default_factory=dict
    )  # {day_id: [sala_ids used as labs]}
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
            logger.warning("No semesters found for hybrid detection")
            return HybridDetectionResult()

        self._detection_semester_id = detection_semester_id
        logger.info(
            f"Starting hybrid discipline detection for semester {detection_semester_id}"
        )

        # Clear previous cache
        self._cache.clear()

        # Detect hybrid discipline codes
        hybrid_codes = self.alocacao_repo.detect_hybrid_disciplines(
            detection_semester_id, REGULAR_CLASSROOM_TYPE_ID
        )

        logger.info(f"Found {len(hybrid_codes)} hybrid disciplines")

        # Build detailed info for each hybrid discipline
        for codigo in hybrid_codes:
            info = self._build_hybrid_info(codigo, detection_semester_id)
            self._cache[codigo] = info

        self._is_initialized = True

        return HybridDetectionResult(
            detected_count=len(hybrid_codes),
            hybrid_disciplines=hybrid_codes,
            detection_semester_id=detection_semester_id,
            details=self._cache.copy(),
        )

    def _build_hybrid_info(
        self, codigo_disciplina: str, semester_id: int
    ) -> HybridDisciplineInfo:
        """
        Build detailed hybrid discipline info with per-day room type analysis.

        Args:
            codigo_disciplina: Discipline code
            semester_id: Semester used for detection

        Returns:
            HybridDisciplineInfo with detailed day-by-day analysis
        """
        # Get per-day room type info
        day_room_types = self.alocacao_repo.get_hybrid_discipline_day_room_types(
            codigo_disciplina, semester_id, REGULAR_CLASSROOM_TYPE_ID
        )

        lab_days = []
        classroom_days = []
        lab_room_types = set()
        historical_lab_rooms = {}

        for day_id, day_info in day_room_types.items():
            if day_info["is_lab_day"]:
                lab_days.append(day_id)
                historical_lab_rooms[day_id] = day_info["lab_room_ids"]

                # Track all non-classroom room types used
                for tipo_id in day_info["room_types"]:
                    if tipo_id != REGULAR_CLASSROOM_TYPE_ID:
                        lab_room_types.add(tipo_id)
            else:
                classroom_days.append(day_id)

        info = HybridDisciplineInfo(
            codigo_disciplina=codigo_disciplina,
            lab_days=sorted(lab_days),
            classroom_days=sorted(classroom_days),
            lab_room_types=lab_room_types,
            historical_lab_rooms=historical_lab_rooms,
            detection_semester_id=semester_id,
        )

        logger.debug(
            f"Hybrid discipline {codigo_disciplina}: "
            f"lab_days={info.lab_days}, classroom_days={info.classroom_days}"
        )

        return info

    def is_hybrid(self, codigo_disciplina: str) -> bool:
        """
        Check if a discipline code is classified as hybrid.

        Args:
            codigo_disciplina: Discipline code to check

        Returns:
            True if discipline is hybrid, False otherwise
        """
        if not self._is_initialized:
            logger.warning("Hybrid detection not initialized - call detect_hybrid_disciplines() first")
            return False

        return codigo_disciplina in self._cache

    def get_hybrid_info(self, codigo_disciplina: str) -> Optional[HybridDisciplineInfo]:
        """
        Get hybrid discipline info if classified as hybrid.

        Args:
            codigo_disciplina: Discipline code

        Returns:
            HybridDisciplineInfo if hybrid, None otherwise
        """
        return self._cache.get(codigo_disciplina)

    def get_lab_days_for_discipline(self, codigo_disciplina: str) -> List[int]:
        """
        Get days that historically used labs for this discipline.

        Args:
            codigo_disciplina: Discipline code

        Returns:
            List of day IDs (2=MON, 3=TUE, etc.) that are lab days
        """
        info = self._cache.get(codigo_disciplina)
        return info.lab_days if info else []

    def get_classroom_days_for_discipline(self, codigo_disciplina: str) -> List[int]:
        """
        Get days that historically only used classrooms for this discipline.

        Args:
            codigo_disciplina: Discipline code

        Returns:
            List of day IDs (2=MON, 3=TUE, etc.) that are classroom-only days
        """
        info = self._cache.get(codigo_disciplina)
        return info.classroom_days if info else []

    def is_lab_day(self, codigo_disciplina: str, day_id: int) -> bool:
        """
        Check if a specific day is a lab day for a discipline.

        Args:
            codigo_disciplina: Discipline code
            day_id: Day ID (2=MON, 3=TUE, etc.)

        Returns:
            True if this day should use a lab, False otherwise
        """
        info = self._cache.get(codigo_disciplina)
        if not info:
            return False
        return day_id in info.lab_days

    def get_historical_lab_rooms(
        self, codigo_disciplina: str, day_id: int
    ) -> List[int]:
        """
        Get historically used lab room IDs for a discipline on a specific day.

        Args:
            codigo_disciplina: Discipline code
            day_id: Day ID (2=MON, 3=TUE, etc.)

        Returns:
            List of sala_ids that were used as labs on this day
        """
        info = self._cache.get(codigo_disciplina)
        if not info:
            return []
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
                    "lab_days": info.lab_days,
                    "classroom_days": info.classroom_days,
                    "lab_room_types": list(info.lab_room_types),
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
