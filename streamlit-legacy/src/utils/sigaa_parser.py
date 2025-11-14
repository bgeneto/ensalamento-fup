"""
Módulo de utilitário para parsear códigos de horário do Sigaa (UnB).

Este módulo é uma tradução direta da lógica encontrada no SigaaScheduleParser
em PHP, adaptada para Python.

Funções principais:
- split_to_atomic_array: Pega um código Sigaa (ex: "24M12") e o divide em
  seus componentes atômicos (ex: ['2M1', '2M2', '4M1', '4M2']).
  Útil para salvar no banco de dados.

- parse_to_human_readable: Pega um código Sigaa (ex: "24M12") e o formata
  para exibição humana (ex: "SEG 08:00-09:50, QUA 08:00-09:50").
  Útil para a UI.
"""

import re
from typing import List, Dict, Any, Tuple


class SigaaScheduleParser:
    """
    Fornece funcionalidade para parsear e formatar strings de horário
    do Sigaa (UnB), com base na implementação PHP de referência.
    """

    # Padrão Regex para encontrar blocos de horário Sigaa
    # Grupo 1: Dias ([2-7])
    # Grupo 2: Turno ([MTN])
    # Grupo 3: Slots ([1-7])
    PATTERN: str = r"\b([2-7]{1,5})([MTN])([1-7]{1,7})\b"

    # Mapeamento de dias Sigaa
    MAP_DAYS: Dict[int, str] = {
        2: "SEG",
        3: "TER",
        4: "QUA",
        5: "QUI",
        6: "SEX",
        7: "SAB",
    }

    # Mapeamento dos blocos atômicos para seus horários de relógio
    MAP_SCHEDULE_TIMES: Dict[str, Dict[str, str]] = {
        "M1": {"inicio": "08:00", "fim": "08:55"},
        "M2": {"inicio": "08:55", "fim": "09:50"},
        "M3": {"inicio": "10:00", "fim": "10:55"},
        "M4": {"inicio": "10:55", "fim": "11:50"},
        "M5": {"inicio": "12:00", "fim": "12:55"},
        "T1": {"inicio": "12:55", "fim": "13:50"},
        "T2": {"inicio": "14:00", "fim": "14:55"},
        "T3": {"inicio": "14:55", "fim": "15:50"},
        "T4": {"inicio": "16:00", "fim": "16:55"},
        "T5": {"inicio": "16:55", "fim": "17:50"},
        "T6": {"inicio": "18:00", "fim": "18:55"},
        "N1": {"inicio": "19:00", "fim": "19:50"},
        "N2": {"inicio": "19:50", "fim": "20:40"},
        "N3": {"inicio": "20:50", "fim": "21:40"},
        "N4": {"inicio": "21:40", "fim": "22:30"},
    }

    def __init__(self):
        # Compila o regex para performance
        self.regex_pattern = re.compile(self.PATTERN)

    def _sort_days(self, text: str) -> str:
        """
        Ordena os blocos de horário por dia (ex: 6T1 2M1 vira 2M1 6T1).
        """
        matches = list(self.regex_pattern.finditer(text))

        # Ordena os matches com base no primeiro grupo (dias)
        matches.sort(key=lambda m: m.group(1))

        return " ".join([m.group(0) for m in matches])

    def _join_schedules(self, text: str) -> str:
        """
        Junta blocos atômicos consecutivos.
        Ex: "2M1 2M2 4M1" vira "2M12 4M1".
        """
        matches = self.regex_pattern.finditer(text)

        acc: List[Dict[str, str]] = []

        for curr in matches:
            day, shift, schedule = curr.group(1), curr.group(2), curr.group(3)

            if acc:
                last = acc[-1]
                # Verifica se o bloco atual é consecutivo ao anterior
                # (mesmo dia, mesmo turno, e slot é N+1)
                try:
                    is_consecutive = (
                        last["day"] == day
                        and last["shift"] == shift
                        and (int(last["schedule"][-1]) + 1) == int(schedule[0])
                        and
                        # Garante que não está juntando blocos não-sequenciais (ex: M1 e M3)
                        len(schedule) == 1
                    )
                except (ValueError, IndexError):
                    is_consecutive = False

                if is_consecutive:
                    # Junta o schedule (ex: "1" + "2" = "12")
                    acc[-1]["schedule"] += schedule
                    continue

            # Se não for consecutivo, adiciona como novo item
            acc.append({"day": day, "shift": shift, "schedule": schedule})

        # Reconstrói a string de horário (ex: "2M12", "4M1")
        result = [f"{item['day']}{item['shift']}{item['schedule']}" for item in acc]
        return " ".join(result)

    def _map_schedule_callback(self, match_obj) -> str:
        """
        Função de callback para re.sub. Converte um match (ex: 2M12)
        em um formato legível (ex: "SEG 08:00-09:50").
        """
        try:
            day_code = match_obj.group(1)
            shift = match_obj.group(2)
            slots = match_obj.group(3)  # Ex: "12"

            day_str = self.MAP_DAYS.get(int(day_code))
            if not day_str:
                return match_obj.group(0)  # Retorna original se o dia for inválido

            # Pega o slot de início (ex: "M1") e o slot de fim (ex: "M2")
            start_slot_code = f"{shift}{slots[0]}"
            end_slot_code = f"{shift}{slots[-1]}"

            start_time = self.MAP_SCHEDULE_TIMES[start_slot_code]["inicio"]
            end_time = self.MAP_SCHEDULE_TIMES[end_slot_code]["fim"]

            return f"{day_str} {start_time}-{end_time}"

        except (KeyError, IndexError, TypeError):
            # Em caso de falha (ex: código "N5" não existe), retorna o código original
            return match_obj.group(0)

    # --- Métodos Públicos ---

    def parse_to_human_readable(self, text: str, sort_days: bool = True) -> str:
        """
        Função principal (Frontend): Converte uma string Sigaa bruta em
        formato legível.

        Ex: "6M12 2M12" vira "SEG 08:00-09:50, SAB 08:00-09:50"
        """
        if not text:
            return ""

        value = text
        if sort_days:
            value = self._sort_days(value)

        # Junta blocos (ex: "2M1 2M2" vira "2M12")
        value = self._join_schedules(value)

        # Converte os blocos juntados (ex: "2M12") em strings legíveis
        return self.regex_pattern.sub(self._map_schedule_callback, value)

    def split_to_atomic_array(self, text: str) -> List[str]:
        """
        Função principal (Backend): Converte uma string Sigaa bruta em
        uma lista de seus blocos atômicos.

        Ex: "24M12" vira ['2M1', '2M2', '4M1', '4M2']
        """
        if not text:
            return []

        matches = self.regex_pattern.finditer(text)
        results = []

        for match in matches:
            days = list(match.group(1))  # Ex: "24" -> ['2', '4']
            shift = match.group(2)  # Ex: "M"
            slots = list(match.group(3))  # Ex: "12" -> ['1', '2']

            # Cria todas as combinações atômicas
            for day in days:
                for slot in slots:
                    results.append(f"{day}{shift}{slot}")

        return results

    def split_to_atomic_tuples(self, text: str) -> List[Tuple[str, int]]:
        """
        Converte uma string Sigaa bruta em uma lista de tuplas atômicas (bloco, dia).

        Ex: "24M12" vira [('M1', 2), ('M2', 2), ('M1', 4), ('M2', 4)]
        
        Returns empty list for invalid input to handle errors gracefully.
        """
        if not text or not isinstance(text, str):
            return []
            
        atomic_array = self.split_to_atomic_array(text)
        results = []
        invalid_blocks = []

        for block in atomic_array:
            if len(block) >= 3:
                # Extrai dia e bloco do formato "2M1" -> (dia=2, bloco="M1")
                try:
                    day = int(block[0])
                    code = block[1:]  # "M1"
                    
                    # Validate day range (2-7 for Monday-Saturday)
                    if day < 2 or day > 7:
                        invalid_blocks.append(block)
                        continue
                        
                    # Validate shift and slot
                    if code[0] not in ['M', 'T', 'N']:
                        invalid_blocks.append(block)
                        continue
                        
                    slot_num = int(code[1:])
                    if slot_num < 1 or slot_num > 7:
                        invalid_blocks.append(block)
                        continue
                        
                    results.append((code, day))
                except (ValueError, IndexError) as e:
                    invalid_blocks.append(block)
                    continue
            else:
                invalid_blocks.append(block)

        # Log warnings for invalid blocks (if any)
        if invalid_blocks:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Invalid SIGAA blocks detected and skipped: {invalid_blocks}")

        return results


# --- Exemplo de Uso ---
if __name__ == "__main__":
    parser = SigaaScheduleParser()

    # --- Exemplo 1: String da API (Backend) ---
    print("--- Teste de Backend (split_to_atomic_array) ---")
    api_string = "24M12 6T34"
    atomic_blocks = parser.split_to_atomic_array(api_string)
    print(f"String da API: '{api_string}'")
    print(f"Blocos Atômicos (para BD): {atomic_blocks}")
    # Resultado esperado: ['2M1', '2M2', '4M1', '4M2', '6T3', '6T4']

    print("\n")

    # --- Exemplo 2: String para UI (Frontend) ---
    print("--- Teste de Frontend (parse_to_human_readable) ---")

    # Teste 1: String já combinada
    sigaa_string_1 = "24M12 6T34"
    human_string_1 = parser.parse_to_human_readable(sigaa_string_1)
    print(f"String Sigaa: '{sigaa_string_1}'")
    print(f"Formato UI: {human_string_1}")
    # Resultado esperado: "SEG 08:00-09:50, QUA 08:00-09:50, SAB 14:55-17:50"

    print("-" * 20)

    # Teste 2: String com blocos atômicos separados (precisa de join)
    sigaa_string_2 = "3N1 3N2 5M1 5M2 5M3"
    human_string_2 = parser.parse_to_human_readable(sigaa_string_2)
    print(f"String Sigaa: '{sigaa_string_2}'")
    print(f"Formato UI: {human_string_2}")
    # Resultado esperado: "TER 19:00-20:40, QUI 08:00-10:55"
