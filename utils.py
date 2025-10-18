"""
Utility functions for Sistema de Ensalamento FUP/UnB
Common helper functions used across the application
"""

import re
from datetime import datetime, date, time
from typing import List, Dict, Optional, Tuple
from config import SIGAA_TIME_BLOCKS, SIGAA_DAYS_MAPPING


def validate_sigaa_schedule(horario_sigaa: str) -> bool:
    """
    Validate if a SIGAA schedule string is properly formatted

    Args:
        horario_sigaa: SIGAA schedule string (e.g., "24M12 6T34")

    Returns:
        bool: True if valid, False otherwise
    """
    if not horario_sigaa or not isinstance(horario_sigaa, str):
        return False

    # Pattern: [day][turn][block] [day][turn][block] ...
    pattern = r"^[2-7][MTN][1-6](?:\s+[2-7][MTN][1-6])*$"
    return bool(re.match(pattern, horario_sigaa.strip()))


def parse_sigaa_schedule(horario_sigaa: str) -> List[Tuple[int, str]]:
    """
    Parse SIGAA schedule string into list of (day, time_block) tuples

    Args:
        horario_sigaa: SIGAA schedule string (e.g., "24M12 6T34")

    Returns:
        List of tuples: [(day_id, time_block), ...]
    """
    if not validate_sigaa_schedule(horario_sigaa):
        return []

    # Split by whitespace and parse each part
    parts = horario_sigaa.strip().split()
    result = []

    for part in parts:
        if len(part) >= 3:
            day_id = int(part[0])
            turno = part[1]
            block_num = part[2]

            # Convert to block code
            block_code = f"{turno}{block_num}"

            # Validate block exists
            if block_code in [
                b for blocks in SIGAA_TIME_BLOCKS.values() for b in blocks
            ]:
                result.append((day_id, block_code))

    return result


def format_time_display(horario_inicio: time, horario_fim: time) -> str:
    """
    Format time range for display

    Args:
        horario_inicio: Start time
        horario_fim: End time

    Returns:
        Formatted time string (e.g., "07:00 - 07:50")
    """
    return f"{horario_inicio.strftime('%H:%M')} - {horario_fim.strftime('%H:%M')}"


def get_dia_semana_nome(dia_id: int) -> str:
    """
    Get day name by SIGAA day ID

    Args:
        dia_id: SIGAA day ID (2-7)

    Returns:
        Day name (e.g., "SEG", "TER")
    """
    return SIGAA_DAYS_MAPPING.get(dia_id, "")


def format_room_display(sala) -> str:
    """
    Format room name with building for display

    Args:
        sala: Room object with relationships loaded

    Returns:
        Formatted room string (e.g., "Bloco A - Sala 101")
    """
    if sala.predio:
        return f"{sala.predio.nome} - {sala.nome}"
    return sala.nome


def format_capacity_range(capacidade: int) -> str:
    """
    Format capacity with category label

    Args:
        capacidade: Room capacity

    Returns:
        Formatted capacity string (e.g., "40 alunos (Pequena)")
    """
    from config import CAPACITY_TIERS

    if capacidade <= CAPACITY_TIERS["pequena"]:
        categoria = "Pequena"
    elif capacidade <= CAPACITY_TIERS["media"]:
        categoria = "Média"
    elif capacidade <= CAPACITY_TIERS["grande"]:
        categoria = "Grande"
    else:
        categoria = "Auditório"

    return f"{capacidade} alunos ({categoria})"


def get_current_semestre() -> str:
    """
    Get current semester string based on current date

    Returns:
        Semester string (e.g., "2025.1", "2025.2")
    """
    current_year = datetime.now().year
    current_month = datetime.now().month

    if current_month <= 6:
        return f"{current_year}.1"
    else:
        return f"{current_year}.2"


def is_valid_semestre_format(semestre: str) -> bool:
    """
    Validate semester format (YYYY.N where N is 1 or 2)

    Args:
        semestre: Semester string

    Returns:
        bool: True if valid format
    """
    pattern = r"^\d{4}\.[12]$"
    return bool(re.match(pattern, semestre))


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for file system compatibility

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
    # Remove multiple underscores
    sanitized = re.sub(r"_+", "_", sanitized)
    # Remove leading/trailing underscores and spaces
    sanitized = sanitized.strip("_. ")

    return sanitized


def format_duration_minutes(horario_inicio: time, horario_fim: time) -> int:
    """
    Calculate duration in minutes between two times

    Args:
        horario_inicio: Start time
        horario_fim: End time

    Returns:
        Duration in minutes
    """
    start_minutes = horario_inicio.hour * 60 + horario_inicio.minute
    end_minutes = horario_fim.hour * 60 + horario_fim.minute
    return end_minutes - start_minutes


def get_time_blocks_by_turno(turno: str) -> List[str]:
    """
    Get all time blocks for a specific shift

    Args:
        turno: Shift code ('M', 'T', or 'N')

    Returns:
        List of time block codes
    """
    return SIGAA_TIME_BLOCKS.get(turno.upper(), [])


def sort_by_time_and_day(items: List[Dict]) -> List[Dict]:
    """
    Sort list of items by day and time block

    Args:
        items: List of dictionaries with 'dia_semana_id' and 'codigo_bloco'

    Returns:
        Sorted list
    """

    def sort_key(item):
        # Sort by day ID first, then by time block code
        day_order = item.get("dia_semana_id", 0)

        # Extract time block order (M1=1, M2=2, etc.)
        block_code = item.get("codigo_bloco", "")
        if len(block_code) >= 2:
            turno = block_code[0]
            block_num = int(block_code[1])

            # Assign numeric order to turns
            if turno == "M":
                turn_order = 0
            elif turno == "T":
                turn_order = 100
            else:  # 'N'
                turn_order = 200

            block_order = turn_order + block_num
        else:
            block_order = 999

        return (day_order, block_order)

    return sorted(items, key=sort_key)


def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate string to maximum length with suffix

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated string
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def format_currency(value: float) -> str:
    """
    Format currency value in Brazilian Real

    Args:
        value: Monetary value

    Returns:
        Formatted currency string
    """
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def validate_email(email: str) -> bool:
    """
    Validate email format

    Args:
        email: Email address

    Returns:
        bool: True if valid email format
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def generate_room_code(predio_nome: str, sala_nome: str) -> str:
    """
    Generate a unique room code from building and room names

    Args:
        predio_nome: Building name
        sala_nome: Room name

    Returns:
        Room code string
    """
    # Extract initials/short forms
    predio_code = re.sub(r"[^A-Z0-9]", "", predio_nome.upper())[:3]
    sala_code = re.sub(r"[^A-Z0-9]", "", sala_nome.upper())[:3]

    return f"{predio_code}-{sala_code}"


def is_room_available_for_reservation(
    sala_id: int, data: date, codigo_bloco: str
) -> bool:
    """
    Check if a room is available for a specific date and time block
    (This is a simplified version - the full implementation will be in the reservation service)

    Args:
        sala_id: Room ID
        data: Date for reservation
        codigo_bloco: Time block code

    Returns:
        bool: True if available (placeholder implementation)
    """
    # This is a placeholder - the actual implementation will check
    # against semester allocations and existing reservations
    return True


def get_system_info() -> Dict[str, str]:
    """
    Get system information for display

    Returns:
        Dictionary with system information
    """
    return {
        "app_name": "Sistema de Ensalamento FUP/UnB",
        "version": "1.0.0",
        "framework": "Streamlit",
        "database": "SQLite",
        "python_version": f"Python {datetime.now().year}",
        "last_updated": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
