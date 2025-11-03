#!/usr/bin/env python3
"""
Load historical semester allocations from CSV file.

This script loads historical course/room allocations from a CSV file,
parsing the data and creating AlocacaoSemestral records for the semester
history (RF-006.6 - rules based on historical allocations).

Usage:
    python load_historical_allocations.py [--dry-run] [--force] [--enable-reservations] [--disable-allocation] [CSV_FILE]

Arguments:
    CSV_FILE: Path to CSV file (default: docs/Ensalamento Oferta 2-2025.csv)

Options:
    --dry-run: Show what would be done without making changes
    --force: Overwrite existing allocations for conflicts
    --enable-reservations: Enable creation of ReservaEsporadica records (default: disabled)
    --disable-allocation: Skip creation of AlocacaoSemestral records (only create demandas) (default: disabled)
"""

import csv
import re
from pathlib import Path
from typing import List, Optional, Dict, Tuple, NamedTuple
from collections import defaultdict
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from sqlalchemy.orm import Session

from src.config.database import get_db_session
from src.repositories.semestre import SemestreRepository
from src.repositories.alocacao import AlocacaoRepository
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.sala import SalaRepository
from src.repositories.dia_semana import DiaSemanaRepository
from src.repositories.horario_bloco import HorarioBlocoRepository
from src.repositories.base import BaseRepository
from src.models.allocation import ReservaEsporadica, AlocacaoSemestral

# We'll create our own DTO since the schema files are misaligned with actual models

# Regex patterns for parsing course data
# Course codes: 3-5 letters + 4 digits, may optionally end with dash for no-turma courses
# Format: CODE - NAME - TURMA (where TURMA is optional T followed by number)
COURSE_PATTERN = re.compile(r"^([A-Z]{3,9}\d{4}-?)\s*-\s*([^-\n]+?)(?:\s*-\s*T(\d+))?$")
RESERVATION_PATTERN = re.compile(
    r"^(Ledoc|EducAção|biblioteca|auditório|[A-Z][a-z]{2,})$", re.IGNORECASE
)


class ParsedAllocation(NamedTuple):
    """Parsed allocation data from CSV cell."""

    codigo_disciplina: Optional[str]
    nome_disciplina: Optional[str]
    turma_disciplina: Optional[str]
    is_reservation: bool
    titulo_evento: Optional[str]


class ReservaEsporadicaRepository(BaseRepository):
    """Repository for ReservaEsporadica operations."""

    def __init__(self, session: Session):
        super().__init__(session, ReservaEsporadica)


class CSVAllocator:
    """Handles loading historical allocations from CSV."""

    def __init__(
        self,
        session: Session,
        dry_run: bool = False,
        force: bool = False,
        semester_name: str = "2025-2",
        enable_reservations: bool = False,
        debug: bool = False,
        disable_allocation: bool = False,
    ):
        self.session = session
        self.dry_run = dry_run
        self.force = force
        self.semestre_name = semester_name
        self.enable_reservations = enable_reservations
        self.debug = debug
        self.disable_allocation = disable_allocation

        # Initialize repositories
        self.sem_repo = SemestreRepository(session)
        self.aloc_repo = AlocacaoRepository(session)
        self.reserva_repo = ReservaEsporadicaRepository(session)
        self.demanda_repo = DisciplinaRepository(session)
        self.sala_repo = SalaRepository(session)
        self.dia_repo = DiaSemanaRepository(session)
        self.horario_repo = HorarioBlocoRepository(session)

        # Stats
        self.stats = {
            "rows_processed": 0,
            "allocations_created": 0,
            "reservas_created": 0,
            "demandas_created": 0,
            "conflicts_skipped": 0,
            "errors": 0,
        }

    def get_semestre(self):
        """Get the 2025-2 semester."""
        return self.sem_repo.get_by_name(self.semestre_name)

    def parse_allocation_cell(self, cell_value: str) -> ParsedAllocation:
        """
        Parse a CSV cell containing allocation data.

        First tries to parse as course code, if no valid course code can be inferred,
        treats the whole string as a reservation title.
        """
        if not cell_value or cell_value.strip() == "":
            return ParsedAllocation(None, None, None, False, None)

        cell_value = cell_value.strip()

        # Debug logging for all cells
        if self.debug:
            print(f"DEBUG parse_allocation_cell: Processing '{cell_value}'")

        # First check if it's a known reservation type (Ledoc, EducAção, etc.)
        if RESERVATION_PATTERN.match(cell_value):
            if self.debug:
                print(
                    f"DEBUG parse_allocation_cell: '{cell_value}' matches RESERVATION_PATTERN"
                )
            return ParsedAllocation(None, None, None, True, cell_value)

        # Try to parse as course by splitting on " - "
        parts = cell_value.split(" - ")
        if self.debug:
            print(
                f"DEBUG parse_allocation_cell: '{cell_value}' split into {len(parts)} parts: {parts}"
            )

        if len(parts) >= 2:
            # Get potential code from first part
            codigo_raw = parts[0].strip()
            # Remove trailing dash from code if present (codes should never end with -)
            codigo = codigo_raw.rstrip("-")

            if self.debug:
                print(f"DEBUG parse_allocation_cell: Extracted codigo: '{codigo}'")

            # Verify the code looks valid (3-5 letters + 4 digits, no trailing dash)
            if re.match(r"^[A-Z]{3,5}\d{4}$", codigo):
                if self.debug:
                    print(
                        f"DEBUG parse_allocation_cell: '{codigo}' matches course pattern"
                    )
                # Valid code, parse the rest
                remaining_parts = parts[1:]

                # Check if last part looks like a turma indicator (T followed by digits)
                last_part = remaining_parts[-1].strip() if remaining_parts else ""
                if last_part.startswith("T") and last_part[1:].isdigit():
                    # Last part is turma
                    nome_parts = remaining_parts[:-1]
                    turma_raw = last_part[1:]
                else:
                    # No explicit turma, assume all remaining parts are name
                    nome_parts = remaining_parts
                    turma_raw = ""

                # Join name parts back with " - " (preserves internal dashes)
                nome = " - ".join(part.strip() for part in nome_parts)

                # Clean up name
                nome = nome.strip()

                # If no turma found, use default "1"
                if not turma_raw:
                    turma = "1"
                else:
                    # Ensure turma is numeric only
                    turma = turma_raw if turma_raw.isdigit() else "1"

                if self.debug:
                    print(
                        f"DEBUG parse_allocation_cell: Final result - codigo='{codigo}', nome='{nome}', turma='{turma}'"
                    )
                return ParsedAllocation(codigo, nome, turma, False, None)

        # If no course pattern matches AND not a known reservation type,
        # treat the whole string as a reservation title
        if self.debug:
            print(
                f"DEBUG parse_allocation_cell: '{cell_value}' - no course pattern matched, treating as reservation"
            )
        return ParsedAllocation(None, None, None, True, cell_value)

    def find_demanda(
        self,
        semestre_id: int,
        codigo: str,
        turma: str,
        horario_sigaa: Optional[str] = None,
        nome_disciplina: Optional[str] = None,
    ) -> Optional[int]:
        """
        Find existing demanda ID by semester, code, and turma.

        If horario_sigaa provided, uses it as additional matching criterion.

        If not found and horario_sigaa provided, create new demanda.
        """
        demandas = self.demanda_repo.get_by_semestre(semestre_id)
        if self.debug:
            print(
                f"DEBUG find_demanda: Searching for {codigo} T{turma}, found {len(demandas)} total demandas in semester"
            )

            # NEW: Debug log all demandas in the semester to check if FUP0007 T4 exists
            print(
                f"DEBUG find_demanda: All demandas in semester {semestre_id}: {[f'{d.id}: {d.codigo_disciplina} T{d.turma_disciplina} (horario: {d.horario_sigaa_bruto})' for d in demandas]}"
            )

        print(
            f"    🔍 Searching for demanda: {codigo} T{turma}, horario: {horario_sigaa}"
        )

        # Search through existing demandas
        for demanda in demandas:
            if self.debug:
                print(
                    f"DEBUG find_demanda: Checking demanda ID {demanda.id}: {demanda.codigo_disciplina} T{demanda.turma_disciplina}"
                )

            if (
                demanda.codigo_disciplina == codigo
                and demanda.turma_disciplina == turma
            ):
                if self.debug:
                    print(
                        f"DEBUG find_demanda: Found matching demanda ID {demanda.id} for {codigo} T{turma}"
                    )
                # Check horario match if provided
                if horario_sigaa:
                    if (
                        hasattr(demanda, "horario_sigaa_bruto")
                        and demanda.horario_sigaa_bruto
                    ):
                        # Check if the search horario is contained in the complete aggregated horario
                        if horario_sigaa in demanda.horario_sigaa_bruto:
                            print(
                                f"      ✅ Found matching demanda (ID: {demanda.id}) with same horario: {horario_sigaa}"
                            )
                            return demanda.id
                        else:
                            print(
                                f"      ❌ Horario mismatch - existing: '{demanda.horario_sigaa_bruto}' vs new: '{horario_sigaa}', skipping..."
                            )
                            continue
                    else:
                        print(
                            f"      ❌ No horario found in existing demanda (ID: {demanda.id}), but new has: '{horario_sigaa}', skipping..."
                        )
                        continue
                else:
                    # No horario provided for matching, take first match by code and turma
                    horario_completo = demanda.horario_sigaa_bruto or "no horario"
                    print(
                        f"      ✅ Found demanda (ID: {demanda.id}) with complete horario: '{horario_completo}'"
                    )
                    return demanda.id

        # Not found, create new if horario provided
        if horario_sigaa:
            print(
                f"  ⚠️ Demanda not found for {codigo} T{turma} with horario '{horario_sigaa}', creating..."
            )
            demanda_data = {
                "semestre_id": semestre_id,
                "codigo_disciplina": codigo,
                "nome_disciplina": nome_disciplina
                or f"Disciplina {codigo}",  # Use parsed name or placeholder
                "turma_disciplina": turma,
                "horario_sigaa_bruto": horario_sigaa,
                "vagas_disciplina": 30,  # Default
                "professores_disciplina": "",
            }

            if not self.dry_run:
                demanda = self.demanda_repo.create(demanda_data)
                self.stats["demandas_created"] += 1
                return demanda.id
            else:
                print(
                    f"    [DRY RUN] Would create demanda: {codigo} T{turma} with horario: {horario_sigaa}"
                )
                return None  # In dry run, can't return real ID
        else:
            if self.debug:
                print(
                    f"DEBUG find_demanda: No match found for {codigo} T{turma}, no horario provided for creation"
                )
            print(
                f"  ⚠️ Demanda not found for {codigo} T{turma} (no horario provided for creation)"
            )

        return None

    def process_allocation(
        self,
        semestre_id: int,
        sala_id: int,
        dia_id: int,
        bloco: str,
        allocation: ParsedAllocation,
        demanda_id: Optional[int] = None,
    ):
        """Process a single allocation (course or reservation)."""

        if allocation.is_reservation:
            if not self.enable_reservations:
                print(
                    f"    ⏭️ Skipping reservation creation (disabled): {allocation.titulo_evento}"
                )
                return

            # Create reservation using model fields: sala_id, username_solicitante, titulo_evento, data_reserva, codigo_bloco
            reserva_data = {
                "sala_id": sala_id,
                "username_solicitante": "admin",  # Admin user
                "titulo_evento": allocation.titulo_evento or "Reserva Histórica",
                "data_reserva": f"2025-{(dia_id-2)*7 + 1:02d}-15",  # Fake date based on weekday
                "codigo_bloco": bloco,
            }

            # Check for conflicts within the same semester only
            if self.aloc_repo.check_conflict(
                sala_id, dia_id, bloco, semestre_id=semestre_id
            ):
                if not self.force:
                    print(
                        f"  ⚠️ Skipping reserva conflict: sala {sala_id}, {dia_id}, {bloco}"
                    )
                    self.stats["conflicts_skipped"] += 1
                    return
                else:
                    print(
                        f"  🔄 Force-overwriting reserva conflict: sala {sala_id}, {dia_id}, {bloco}"
                    )

            if not self.dry_run:
                try:
                    # Create reserva object directly since schemas are misaligned
                    reserva_obj = ReservaEsporadica(**reserva_data)
                    self.session.add(reserva_obj)
                    self.session.flush()
                    self.stats["reservas_created"] += 1
                except Exception as e:
                    print(f"  ❌ Error creating reserva: {e}")
                    self.stats["errors"] += 1
            else:
                print(f"    [DRY RUN] Would create reserva: {allocation.titulo_evento}")

        else:
            # For courses, demanda_id should already be provided
            if demanda_id is None:
                print(
                    f"  ❌ No demanda_id provided for course allocation: {allocation.codigo_disciplina}-{allocation.turma_disciplina}"
                )
                return

            aloc_data = {
                "semestre_id": semestre_id,
                "demanda_id": demanda_id,
                "sala_id": sala_id,
                "dia_semana_id": dia_id,
                "codigo_bloco": bloco,
            }

            # Check for conflicts within the same semester only
            if self.aloc_repo.check_conflict(
                sala_id, dia_id, bloco, semestre_id=semestre_id
            ):
                if not self.force:
                    print(
                        f"  ⚠️ Skipping allocation conflict: sala {sala_id}, {dia_id}, {bloco}"
                    )
                    self.stats["conflicts_skipped"] += 1
                    return
                else:
                    print(
                        f"  🔄 Force-overwriting allocation conflict: sala {sala_id}, {dia_id}, {bloco}"
                    )

            if not self.dry_run:
                try:
                    aloc_obj = AlocacaoSemestral(**aloc_data)
                    self.session.add(aloc_obj)
                    self.session.flush()
                    self.stats["allocations_created"] += 1
                except Exception as e:
                    print(f"  ❌ Error creating allocation: {e}")
                    self.stats["errors"] += 1
            else:
                print(
                    f"    [DRY RUN] Would create allocation: {allocation.codigo_disciplina} in sala {sala_id}"
                )

    def process_csv_row(
        self, row: List[str], room_mapping: List[str], semestre_id: int
    ):
        """Process a single CSV row containing time block + allocations."""
        self.stats["rows_processed"] += 1

        # First column is the time block (e.g., "2M12")
        time_slot = row[0].strip()
        if not time_slot:
            print(f"  ⚠️ Skipping empty time slot in row {self.stats['rows_processed']}")
            return

        # Parse time slot: digit(s) + turn + slots
        match = re.match(r"^(\d+)([MTN])(\d+)$", time_slot)
        if not match:
            print(f"  ⚠️ Invalid time slot format: {time_slot}")
            self.stats["errors"] += 1
            return

        dia_sigaa = int(match.group(1))
        turno = match.group(2)  # M, T, or N
        slots_str = match.group(3)  # e.g., "34" (slots 3 and 4)

        # Split into atomic blocks (e.g., "34" -> ["3", "4"] -> ["M3", "M4"])
        atomic_blocks = [f"{turno}{slot}" for slot in slots_str]

        # Get dia_semana ORM object
        dia_obj = self.dia_repo.get_by_id_sigaa(dia_sigaa)
        if not dia_obj:
            print(f"  ⚠️ Day {dia_sigaa} not found")
            self.stats["errors"] += 1
            return

        print(
            f"Processing {time_slot} (dia {dia_sigaa}, atomic blocks: {atomic_blocks})"
        )

        # Process each allocation column (skip first column which is time slot)
        for i, allocation_cell in enumerate(row[1:], 1):
            if i > len(room_mapping):
                break

            sala_nome = room_mapping[i - 1]
            cell_value = allocation_cell.strip()

            if not cell_value:
                continue  # Empty cell, skip

            # Get sala ORM object
            from src.models.inventory import Sala

            sala_orm = self.session.query(Sala).filter(Sala.nome == sala_nome).first()
            if not sala_orm:
                print(f"  ⚠️ Room {sala_nome} not found")
                self.stats["errors"] += 1
                continue
            sala = self.sala_repo.orm_to_dto(sala_orm)

            # Parse the allocation
            allocation = self.parse_allocation_cell(cell_value)

            # Debug logging for all allocations
            if self.debug:
                if allocation.is_reservation:
                    print(
                        f"DEBUG: Cell '{cell_value}' parsed as reservation: {allocation.titulo_evento}"
                    )
                elif allocation.codigo_disciplina:
                    print(
                        f"DEBUG: Cell '{cell_value}' parsed as course: {allocation.codigo_disciplina} T{allocation.turma_disciplina}"
                    )
                else:
                    print(f"DEBUG: Cell '{cell_value}' parsed as unknown reservation")

            if allocation.is_reservation or not allocation.codigo_disciplina:
                if self.debug:
                    if allocation.is_reservation:
                        print(
                            f"DEBUG: Skipping reservation allocation: {allocation.titulo_evento}"
                        )
                    else:
                        print(
                            f"DEBUG: Skipping invalid course allocation: '{cell_value}'"
                        )
                continue

            if not allocation.is_reservation:
                # For courses, ensure demanda exists before creating allocations
                # Use space-separated atomic blocks as horario_sigaa_bruto
                horario_bruto = " ".join(
                    [f"{dia_sigaa}{bloco}" for bloco in atomic_blocks]
                )
                # Since demandas are pre-populated with complete aggregated schedules,
                # just match by code only (no partial horario needed)
                if self.debug:
                    print(
                        f"DEBUG: About to call find_demanda for {allocation.codigo_disciplina} T{allocation.turma_disciplina}"
                    )

                demanda_id = self.find_demanda(
                    semestre_id,
                    allocation.codigo_disciplina,
                    allocation.turma_disciplina,
                    # No horario parameter - match by code only since demands are pre-aggregated
                    nome_disciplina=allocation.nome_disciplina,
                )

                if self.debug:
                    print(
                        f"DEBUG: find_demanda for {allocation.codigo_disciplina} T{allocation.turma_disciplina} returned: {demanda_id}"
                    )

                if not demanda_id:
                    if self.debug:
                        print(
                            f"DEBUG: ❌ Could not find/create demanda for {allocation.codigo_disciplina} T{allocation.turma_disciplina}"
                        )
                    continue

                # Now create allocations for each atomic block
                for bloco in atomic_blocks:
                    if self.debug:
                        print(
                            f"DEBUG: Processing allocation for {allocation.codigo_disciplina} T{allocation.turma_disciplina} in {sala.nome} at {dia_obj.id_sigaa}{bloco}"
                        )
                    self.process_allocation(
                        semestre_id,
                        sala.id,
                        dia_obj.id_sigaa,
                        bloco,
                        allocation,
                        demanda_id,
                    )
            else:
                # For reservations, process each atomic block normally
                for bloco in atomic_blocks:
                    self.process_allocation(
                        semestre_id, sala.id, dia_obj.id_sigaa, bloco, allocation
                    )

    def discover_and_aggregate_demandas(self, csv_path: str, semestre_id: int):
        """
        PHASE 1: Discovery and aggregation.

        Scans entire CSV to discover all unique (codigo_disciplina + turma_disciplina)
        combinations and aggregates their complete horario blocks.

        Pre-populates all demandas with complete horario_sigaa_bruto values.
        """
        print("🔍 PHASE 1: Discovering and aggregating course demands...")

        csv_file = Path(csv_path)
        if not csv_file.exists():
            print(f"❌ CSV file not found: {csv_path}")
            return False

        # Structure: {(codigo, turma): {'nome': str, 'horarios': set()}}
        disciplina_map = defaultdict(lambda: {"nome": None, "horarios": set()})

        with open(csv_file, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f, delimiter=";")

            # Skip header row only - no empty row exists in CSV
            next(reader)  # header

            for row in reader:
                # Skip rows where all cells are empty (e.g., ;; becomes ['', ''])
                if not any(cell.strip() for cell in row):
                    continue

                # Parse time slot
                time_slot = row[0].strip()
                match = re.match(r"^(\d+)([MTN])(\d+)$", time_slot)
                if not match:
                    continue

                dia_sigaa = int(match.group(1))
                turno = match.group(2)
                slots_str = match.group(3)

                # Create atomic blocks
                atomic_blocks = [f"{turno}{slot}" for slot in slots_str]

                # Process each allocation cell
                for allocation_cell in row[1:]:
                    cell_value = allocation_cell.strip()
                    if not cell_value:
                        continue

                    # Parse allocation
                    allocation = self.parse_allocation_cell(cell_value)

                    # Debug logging for FUP0007
                    if self.debug and "FUP0007" in cell_value:
                        print(f"DEBUG FUP0007: Cell value: '{cell_value}'")
                        print(f"DEBUG FUP0007: Parsed allocation: {allocation}")

                    if allocation.is_reservation or not allocation.codigo_disciplina:
                        if self.debug and "FUP0007" in cell_value:
                            print(
                                f"DEBUG FUP0007: Skipping - is_reservation: {allocation.is_reservation}, has_codigo: {bool(allocation.codigo_disciplina)}"
                            )
                        continue

                    # Create unique key and build horario blocks
                    key = (allocation.codigo_disciplina, allocation.turma_disciplina)
                    horario_blocks = [f"{dia_sigaa}{bloco}" for bloco in atomic_blocks]

                    # Update the map
                    if not disciplina_map[key]["nome"]:
                        disciplina_map[key]["nome"] = allocation.nome_disciplina
                    disciplina_map[key]["horarios"].update(horario_blocks)

                    # Debug logging for all courses added to map
                    if self.debug:
                        print(
                            f"DEBUG: Added {allocation.codigo_disciplina} T{allocation.turma_disciplina} to disciplina_map (horario_blocks: {horario_blocks})"
                        )

        # PHASE 2: Check existing DB records and create/update demandas with complete aggregated horarios
        print(
            f"📝 PHASE 2: Processing {len(disciplina_map)} aggregated course demands..."
        )

        # Map to store demanda_id for each (codigo, turma) combination
        demanda_id_map = {}

        for (codigo, turma), data in disciplina_map.items():
            # Debug logging for FUP0007
            if self.debug:
                print(
                    f"DEBUG: Processing {codigo} T{turma} in Phase 2 - nome: '{data['nome']}', horarios: {sorted(data['horarios'])}"
                )

            # Create complete aggregated horario_sigaa_bruto
            horario_sorted = sorted(data["horarios"])  # Sort for consistency
            horario_agg = " ".join(horario_sorted)

            # FIXED: Check if demanda with exact (codigo, turma) already exists (not just codigo + horario)
            existing_demanda = None
            existing_demandas = self.demanda_repo.get_by_semestre(semestre_id)
            for demanda in existing_demandas:
                if (
                    demanda.codigo_disciplina == codigo
                    and demanda.turma_disciplina == turma
                ):
                    existing_demanda = demanda
                    break

            if existing_demanda:
                print(
                    f"    ✅ Found existing demanda (ID: {existing_demanda.id}) for {codigo} T{turma}"
                )
                # Optionally update horario if it differs (though it shouldn't in aggregated data)
                if existing_demanda.horario_sigaa_bruto != horario_agg:
                    print(
                        f"    🔄 Updating horario for demanda ID {existing_demanda.id}: '{existing_demanda.horario_sigaa_bruto}' -> '{horario_agg}'"
                    )
                    if not self.dry_run:
                        existing_demanda.horario_sigaa_bruto = horario_agg
                        self.session.commit()  # Or flush, depending on repo behavior
                demanda_id_map[(codigo, turma)] = existing_demanda.id
            else:
                print(
                    f"    📚 Creating new demanda: {codigo} T{turma} -> '{horario_agg}'"
                )

                demanda_data = {
                    "semestre_id": semestre_id,
                    "codigo_disciplina": codigo,
                    "nome_disciplina": data["nome"] or f"Disciplina {codigo}",
                    "turma_disciplina": turma,
                    "horario_sigaa_bruto": horario_agg,
                    "vagas_disciplina": 30,  # Default
                    "professores_disciplina": "",
                }

                if not self.dry_run:
                    try:
                        demanda = self.demanda_repo.create(demanda_data)
                        self.stats["demandas_created"] += 1
                        demanda_id_map[(codigo, turma)] = demanda.id
                    except Exception as e:
                        print(f"  ❌ Error creating demanda {codigo} T{turma}: {e}")
                        self.stats["errors"] += 1
                else:
                    print(f"    [DRY RUN] Would create demanda: {codigo} T{turma}")
                    # In dry run, we can't assign a real ID, so use a placeholder
                    demanda_id_map[(codigo, turma)] = -1

        if self.debug:
            print(
                f"DEBUG: Phase 2 completed - processed {len(demanda_id_map)} demandas, created {self.stats['demandas_created']} new ones"
            )
        return True

    def load_csv(self, csv_path: str):
        """Load allocations from CSV file in two phases."""

        semestre = self.get_semestre()
        if not semestre:
            print(f"❌ Semester '{self.semestre_name}' not found!")
            return False

        print(
            f"Loading historical allocations for semester {semestre.nome} (ID: {semestre.id})"
        )
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"Force mode: {self.force}")

        csv_file = Path(csv_path)
        if not csv_file.exists():
            print(f"❌ CSV file not found: {csv_path}")
            return False

        # PHASE 1: Discover and pre-populate all demandas with aggregated schedules
        if not self.discover_and_aggregate_demandas(csv_path, semestre.id):
            return False

        # PHASE 3: Process allocations (demandas are now pre-populated)
        if not self.disable_allocation:
            print("🏗️ PHASE 3: Processing room allocations...")

            with open(csv_file, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f, delimiter=";")

                # Read header row with room names
                header_row = next(reader)
                room_mapping = [col.strip() for col in header_row if col.strip()]

                print(f"Found {len(room_mapping)} rooms: {room_mapping[:3]}...")

                # Process each data row for allocations
                for row in reader:
                    if not row or not row[0].strip():
                        continue  # Skip empty rows

                    self.process_csv_row(row, room_mapping, semestre.id)

            print("\n" + "=" * 50)
        else:
            print("⏭️ PHASE 3: Skipping room allocations (disabled by --disable-allocation)")
            print("\n" + "=" * 50)
        print("LOAD RESULTS:")
        print(f"Rows processed: {self.stats['rows_processed']}")
        if not self.disable_allocation:
            print(f"Allocations created: {self.stats['allocations_created']}")
            print(f"Reservas created: {self.stats['reservas_created']}")
            print(f"Conflicts skipped: {self.stats['conflicts_skipped']}")
        print(f"Demandas created: {self.stats['demandas_created']}")
        print(f"Errors: {self.stats['errors']}")

        # After processing all rows, log unallocated demandas
        print("\n🔍 Checking for unallocated demandas...")
        all_demandas = self.demanda_repo.get_by_semestre(semestre.id)
        unallocated = []
        for demanda in all_demandas:
            # Check if this demanda has any AlocacaoSemestral records
            allocations = (
                self.session.query(AlocacaoSemestral)
                .filter(AlocacaoSemestral.demanda_id == demanda.id)
                .all()
            )
            if not allocations:
                unallocated.append(demanda)
                print(
                    f"  ⚠️ Unallocated demanda: {demanda.codigo_disciplina} T{demanda.turma_disciplina} (ID: {demanda.id}, Horario: '{demanda.horario_sigaa_bruto}')"
                )

        if unallocated:
            print(
                f"📊 Total unallocated demandas: {len(unallocated)} out of {len(all_demandas)}"
            )
            # Optional: Write to a log file for further analysis
            log_path = Path(csv_path).parent / "unallocated_demandas.log"
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("Unallocated Demandas:\n")
                for d in unallocated:
                    f.write(
                        f"- {d.codigo_disciplina} T{d.turma_disciplina} (ID: {d.id}, Horario: '{d.horario_sigaa_bruto}')\n"
                    )
            print(f"📝 Detailed log saved to: {log_path}")
        else:
            print("✅ All demandas have allocations.")

        if not self.dry_run and self.stats["errors"] == 0:
            self.session.commit()
            print("✅ All changes committed to database")
        elif self.dry_run:
            print("📋 Dry run completed (no database changes)")

        return self.stats["errors"] == 0


def main():
    """Main entry point."""
    parser = ArgumentParser(
        description="Load historical semester allocations from CSV",
        formatter_class=RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python load_historical_allocations.py --dry-run
  python load_historical_allocations.py --force docs/Ensalamento\\ Oferta\\ 2-2025.csv
  python load_historical_allocations.py --dry-run /path/to/other.csv
        """,
    )

    parser.add_argument(
        "csv_file",
        nargs="?",
        default="docs/Ensalamento Oferta 2-2025.csv",
        help="Path to CSV file (default: docs/Ensalamento Oferta 2-2025.csv)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing allocations for conflicts",
    )

    parser.add_argument(
        "--enable-reservations",
        action="store_true",
        help="Enable creation of ReservaEsporadica records (default: disabled)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging (default: disabled)",
    )

    parser.add_argument(
        "--semester",
        default="2025-2",
        help="Semester name (e.g., '2025-2') (default: 2025-2)",
    )

    parser.add_argument(
        "--disable-allocation",
        action="store_true",
        help="Skip creation of AlocacaoSemestral records (only create demandas) (default: disabled)",
    )

    args = parser.parse_args()

    if args.dry_run and args.force:
        print("❌ Cannot use --dry-run and --force together")
        return 1

    with get_db_session() as session:
        allocator = CSVAllocator(
            session,
            dry_run=args.dry_run,
            force=args.force,
            semester_name=args.semester,
            enable_reservations=args.enable_reservations,
            debug=args.debug,
            disable_allocation=args.disable_allocation,
        )
        success = allocator.load_csv(args.csv_file)

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
