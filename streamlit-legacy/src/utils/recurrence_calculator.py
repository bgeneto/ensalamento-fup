"""
Utility class for expanding recurrence rules into specific dates.

Supports daily, weekly, and monthly recurrence patterns with
one-year maximum limit enforcement.
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Any
from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR, SA

from src.schemas.allocation import (
    RegraRecorrencia,
    TipoRecorrencia,
    RegraUnica,
    RegraDiaria,
    RegraSemanal,
    RegraMensalDia,
    RegraMensalPosicao,
)


class RecurrenceCalculator:
    """
    Utility class for calculating recurrence dates from rules.

    This class handles the business logic of expanding recurrence rules
    into specific dates while enforcing the one-year maximum limit.
    """

    # Mapping of SIGAA day numbers to Python weekday constants
    SIGAA_TO_WEEKDAY = {
        2: MO,  # Monday
        3: TU,  # Tuesday
        4: WE,  # Wednesday
        5: TH,  # Thursday
        6: FR,  # Friday
        7: SA,  # Saturday
    }

    @staticmethod
    def expand_recurrence(rule: RegraRecorrencia, start_date: date) -> List[date]:
        """
        Expand a recurrence rule into specific dates.

        Args:
            rule: Recurrence rule object
            start_date: Start date for the recurrence

        Returns:
            List of dates when the event occurs
        """
        if isinstance(rule, RegraUnica):
            return RecurrenceCalculator._expand_unique()
        elif isinstance(rule, RegraDiaria):
            return RecurrenceCalculator._expand_daily(rule, start_date)
        elif isinstance(rule, RegraSemanal):
            return RecurrenceCalculator._expand_weekly(rule, start_date)
        elif isinstance(rule, RegraMensalDia):
            return RecurrenceCalculator._expand_monthly_day(rule, start_date)
        elif isinstance(rule, RegraMensalPosicao):
            return RecurrenceCalculator._expand_monthly_position(rule, start_date)
        else:
            raise ValueError(f"Unsupported recurrence rule type: {type(rule)}")

    @staticmethod
    def _expand_unique() -> List[date]:
        """Expand unique (single occurrence) rule."""
        return []  # Unique events don't need date expansion

    @staticmethod
    def _expand_daily(rule: RegraDiaria, start_date: date) -> List[date]:
        """
        Expand daily recurrence rule.

        Args:
            rule: Daily recurrence rule
            start_date: Start date

        Returns:
            List of occurrence dates
        """
        end_date = RecurrenceCalculator._parse_date(rule.fim)
        one_year_later = start_date + timedelta(days=365)
        effective_end = min(end_date, one_year_later)

        dates = []
        current_date = start_date

        while current_date <= effective_end:
            dates.append(current_date)
            current_date += timedelta(days=rule.intervalo)

        return dates

    @staticmethod
    def _expand_weekly(rule: RegraSemanal, start_date: date) -> List[date]:
        """
        Expand weekly recurrence rule.

        Args:
            rule: Weekly recurrence rule
            start_date: Start date

        Returns:
            List of occurrence dates
        """
        end_date = RecurrenceCalculator._parse_date(rule.fim)
        one_year_later = start_date + timedelta(days=365)
        effective_end = min(end_date, one_year_later)

        dates = []
        current_date = start_date

        # Find the first occurrence
        while (
            current_date.weekday() + 2 not in rule.dias
            and current_date <= effective_end
        ):
            current_date += timedelta(days=1)

        while current_date <= effective_end:
            if current_date.weekday() + 2 in rule.dias:
                dates.append(current_date)

            current_date += timedelta(days=1)

            # Skip to next week if we've passed all specified days
            if current_date.weekday() + 2 > max(rule.dias):
                # Find next Monday
                days_to_next_monday = (7 - current_date.weekday()) % 7
                current_date += timedelta(days=days_to_next_monday)

        return dates

    @staticmethod
    def _expand_monthly_day(rule: RegraMensalDia, start_date: date) -> List[date]:
        """
        Expand monthly recurrence by day of month.

        Args:
            rule: Monthly recurrence rule
            start_date: Start date

        Returns:
            List of occurrence dates
        """
        end_date = RecurrenceCalculator._parse_date(rule.fim)
        one_year_later = start_date + timedelta(days=365)
        effective_end = min(end_date, one_year_later)

        dates = []
        current_date = start_date

        # Adjust to the specified day of month for the first occurrence
        if current_date.day != rule.dia_mes:
            current_date = current_date.replace(day=rule.dia_mes)
            if current_date < start_date:
                current_date += relativedelta(months=1)

        while current_date <= effective_end:
            # Handle cases where the day doesn't exist (e.g., Feb 31)
            try:
                dates.append(current_date)
            except ValueError:
                # Skip this month if the day doesn't exist
                pass

            current_date += relativedelta(months=1)

        return dates

    @staticmethod
    def _expand_monthly_position(
        rule: RegraMensalPosicao, start_date: date
    ) -> List[date]:
        """
        Expand monthly recurrence by nth-day pattern.

        Args:
            rule: Monthly recurrence rule
            start_date: Start date

        Returns:
            List of occurrence dates
        """
        end_date = RecurrenceCalculator._parse_date(rule.fim)
        one_year_later = start_date + timedelta(days=365)
        effective_end = min(end_date, one_year_later)

        dates = []
        current_date = start_date

        weekday = RecurrenceCalculator.SIGAA_TO_WEEKDAY[rule.dia_semana]

        while current_date <= effective_end:
            occurrence_date = RecurrenceCalculator._find_nth_weekday(
                current_date.year, current_date.month, weekday, rule.posicao
            )

            if occurrence_date and occurrence_date >= start_date:
                dates.append(occurrence_date)

            current_date += relativedelta(months=1)

        return dates

    @staticmethod
    def _find_nth_weekday(year: int, month: int, weekday, position: int) -> date:
        """
        Find the nth weekday of a given month and year.

        Args:
            year: Year
            month: Month (1-12)
            weekday: Python weekday constant
            position: Position (1=first, 2=second, 3=third, 4=fourth, 5=last)

        Returns:
            Date of the nth weekday or None if not found
        """
        if position == 5:  # Last occurrence
            # Start from the end of the month
            last_day = date(year, month + 1, 1) - timedelta(days=1)

            # Find the last occurrence of the weekday
            days_back = (last_day.weekday() - weekday) % 7
            return last_day - timedelta(days=days_back)
        else:
            # Start from the beginning of the month
            first_day = date(year, month, 1)

            # Find the first occurrence of the weekday
            days_ahead = (weekday - first_day.weekday()) % 7
            first_occurrence = first_day + timedelta(days=days_ahead)

            # Add (position - 1) weeks to get the nth occurrence
            return first_occurrence + timedelta(weeks=position - 1)

    @staticmethod
    def _parse_date(date_str: str) -> date:
        """
        Parse date string in YYYY-MM-DD format.

        Args:
            date_str: Date string

        Returns:
            Date object

        Raises:
            ValueError: If date format is invalid
        """
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError as e:
            raise ValueError(
                f"Invalid date format: {date_str}. Expected YYYY-MM-DD"
            ) from e

    @staticmethod
    def validate_recurrence_rule(rule: Dict[str, Any]) -> bool:
        """
        Validate a recurrence rule dictionary.

        Args:
            rule: Recurrence rule dictionary

        Returns:
            True if valid, False otherwise
        """
        try:
            tipo = rule.get("tipo")
            if not tipo:
                return False

            if tipo == TipoRecorrencia.UNICA:
                return True

            if tipo == TipoRecorrencia.DIARIA:
                return (
                    "intervalo" in rule
                    and 1 <= rule["intervalo"] <= 365
                    and "fim" in rule
                )

            if tipo == TipoRecorrencia.SEMANAL:
                return (
                    "dias" in rule
                    and isinstance(rule["dias"], list)
                    and 1 <= len(rule["dias"]) <= 7
                    and all(2 <= dia <= 7 for dia in rule["dias"])
                    and "fim" in rule
                )

            if tipo == TipoRecorrencia.MENSAL:
                if "dia_mes" in rule:
                    return 1 <= rule["dia_mes"] <= 31 and "fim" in rule
                elif "posicao" in rule and "dia_semana" in rule:
                    return (
                        1 <= rule["posicao"] <= 5
                        and 2 <= rule["dia_semana"] <= 7
                        and "fim" in rule
                    )

            return False
        except Exception:
            return False

    @staticmethod
    def expand_dates_with_blocks(
        rule: RegraRecorrencia, start_date: date, time_blocks: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Expand recurrence rule with time blocks included.

        Args:
            rule: Recurrence rule
            start_date: Start date
            time_blocks: List of time block codes

        Returns:
            List of dictionaries with date and block information
        """
        if isinstance(rule, RegraUnica):
            # For unique events, only use the start date
            return [
                {"data_reserva": start_date.strftime("%Y-%m-%d"), "codigo_bloco": bloco}
                for bloco in time_blocks
            ]

        dates = RecurrenceCalculator.expand_recurrence(rule, start_date)
        result = []

        for occurrence_date in dates:
            for bloco in time_blocks:
                result.append(
                    {
                        "data_reserva": occurrence_date.strftime("%Y-%m-%d"),
                        "codigo_bloco": bloco,
                    }
                )

        return result
