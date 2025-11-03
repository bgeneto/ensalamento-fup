#!/usr/bin/env python3
"""
Convert markdown schedule file to CSV format compatible with load_historical_allocations.py

This script parses the markdown file containing HTML tables with room schedules
and converts it to the CSV format expected by the historical allocation loader.

Usage:
    python convert_md_to_csv.py [--output OUTPUT_FILE] [--year YEAR] [--semester SEMESTER]
"""

import re
import csv
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from argparse import ArgumentParser


class TimeSlotMapper:
    """Maps time ranges to the slot format used in the CSV."""
    
    def __init__(self):
        # Map time ranges to slot codes based on sigaa_parser.py valid slots
        # Support both formats: 08:00-09:50 (2024.1) and 08:00/09:50 (2024.2)
        self.time_to_slot = {
            "08:00-09:50": "12",  # M1-M2
            "08:00/09:50": "12",  # M1-M2 (2024.2 format)
            "10:00-11:50": "34",  # M3-M4
            "10:00/11:50": "34",  # M3-M4 (2024.2 format)
            "12:00-14:00": "56",  # M5-T1 (lunch period)
            "12:00/14:00": "56",  # M5-T1 (lunch period, 2024.2 format)
            "14:00-15:50": "23",  # T2-T3
            "14:00/15:50": "23",  # T2-T3 (2024.2 format)
            "16:00-17:50": "45",  # T4-T5
            "16:00/17:50": "45",  # T4-T5 (2024.2 format)
            "18:00-19:00": "6",   # T6-N1 (transition period)
            "18:00/19:00": "6",   # T6-N1 (transition period, 2024.2 format)
            "19:00-20:40": "12",  # N1-N2
            "19:00/20:40": "12",  # N1-N2 (2024.2 format)
            "20:50-22:30": "34",  # N3-N4
            "20:50/22:30": "34",  # N3-N4 (2024.2 format)
        }
        
        # Map days to SIGAA numbers
        self.day_to_sigaa = {
            "SEGUNDA": 2,
            "TERÇA": 3,
            "QUARTA": 4,
            "QUINTA": 5,
            "SEXTA": 6,
            "SÁBADO": 7,
        }
        
        # Map time ranges to periods - support both formats
        self.time_to_period = {
            "08:00-09:50": "M",
            "08:00/09:50": "M",  # 2024.2 format
            "10:00-11:50": "M",
            "10:00/11:50": "M",  # 2024.2 format
            "12:00-14:00": "T",  # Afternoon period
            "12:00/14:00": "T",  # Afternoon period, 2024.2 format
            "14:00-15:50": "T",
            "14:00/15:50": "T",  # 2024.2 format
            "16:00-17:50": "T",
            "16:00/17:50": "T",  # 2024.2 format
            "18:00-19:00": "N",  # Night period starts
            "18:00/19:00": "N",  # Night period starts, 2024.2 format
            "19:00-20:40": "N",
            "19:00/20:40": "N",  # 2024.2 format
            "20:50-22:30": "N",
            "20:50/22:30": "N",  # 2024.2 format
        }
    
    def time_range_to_block(self, time_range: str, day: str) -> Optional[str]:
        """Convert time range and day to block format like '2M12'."""
        if time_range not in self.time_to_slot or day not in self.day_to_sigaa:
            return None
            
        day_num = self.day_to_sigaa[day]
        period = self.time_to_period[time_range]
        slots = self.time_to_slot[time_range]
        
        return f"{day_num}{period}{slots}"


class MarkdownToCSVConverter:
    """Converts markdown schedule to CSV format."""
    
    def __init__(self):
        self.time_mapper = TimeSlotMapper()
        # Fixed regex to capture full course name properly
        # Pattern: CODE / NAME (can contain slashes) / Turma X / Prof...
        # Use non-greedy matching to stop at "Turma" or "Prof"
        self.course_pattern = re.compile(
            r"^([A-Z]{3,9}\d{4})\s*/\s*([^/]+?)(?:\s*/\s*Turma\s*(\d+))?", 
            re.IGNORECASE
        )
        
    def extract_room_name(self, room_header: str) -> Optional[str]:
        """Extract room name from header like 'Sala: AT-78/46 - Laboratório...'"""
        match = re.search(r"Sala:\s*([A-Z0-9\-\/]+)", room_header)
        return match.group(1).strip() if match else None
    
    def parse_course_cell(self, cell_content: str) -> Optional[Dict[str, str]]:
        """Parse a cell containing course information."""
        if not cell_content or cell_content.strip() == "":
            return None
            
        cell_content = cell_content.strip()
        
        # Clean up HTML tags and extra whitespace
        cell_content = re.sub(r'<br[^>]*>', ' ', cell_content)  # Replace <br> with space
        cell_content = re.sub(r'<[^>]+>', '', cell_content)  # Remove other HTML tags
        cell_content = re.sub(r'\s+', ' ', cell_content).strip()  # Normalize whitespace
        
        # Skip reservation patterns
        if any(pattern in cell_content.lower() for pattern in [
            "reservar", "ledoc", "em reforma", "ver cronograma", "biblioteca", 
            "auditório", "educ ação", "técnicos do laboratório", "curso preparatório"
        ]):
            return None
            
        # Try both formats: 2024.1 uses '/', 2024.2 uses '-'
        # First try 2024.1 format: CODE / NAME / Turma XX / Prof...
        if '/' in cell_content:
            parts = [part.strip() for part in cell_content.split('/') if part.strip()]
        # Then try 2024.2 format: CODE - NAME - Turma XX - Prof...
        elif '-' in cell_content:
            parts = [part.strip() for part in cell_content.split('-') if part.strip()]
        else:
            return None
        
        if len(parts) < 2:
            return None
            
        # First part should be the course code
        codigo = parts[0].upper()
        if not re.match(r'^[A-Z]{3,9}\d{4}$', codigo):
            return None
            
        # Find the turma number if it exists
        turma = "1"
        nome_parts = []
        
        for i, part in enumerate(parts[1:], 1):
            part_lower = part.lower()
            if part_lower.startswith("turma ") and len(part.split()) >= 2:
                turma = part.split()[1]
                # Don't include "Turma XX" in the course name
                break
            elif part_lower.startswith("prof. "):
                # Don't include professor info in course name
                break
            else:
                nome_parts.append(part)
        
        # Join the name parts using the original separator
        if '/' in cell_content:
            nome = " / ".join(nome_parts).strip()
        else:
            nome = " - ".join(nome_parts).strip()
        
        if not nome:
            return None
            
        return {
            "codigo": codigo,
            "nome": nome,
            "turma": turma,
            "original": cell_content
        }
    
    def parse_html_table(self, table_html: str, room_name: str) -> List[Tuple[str, Dict[str, str]]]:
        """Parse an HTML table using regex and extract schedule data."""
        # Extract the table structure using regex
        
        # Find all rows in the table body
        row_pattern = r'<tr>(.*?)</tr>'
        rows = re.findall(row_pattern, table_html, re.DOTALL)
        
        if not rows:
            print(f"    🐛 Debug: No rows found in table for {room_name}")
            return []
        
        print(f"    🐛 Debug: Found {len(rows)} rows in table for {room_name}")
        
        # Extract headers from first row (skip if it's a header row with colspan)
        day_headers = []
        
        # Check if first row has a colspan header (room name inside table)
        first_row_has_colspan = bool(re.search(r'<th[^>]*colspan="7"', rows[0]))
        
        if first_row_has_colspan:
            # Room name is in first row, use second row for day headers
            if len(rows) > 1:
                header_cells = re.findall(r'<th[^>]*>(.*?)</th>', rows[1], re.DOTALL)
                print(f"    🐛 Debug: Skipping colspan header row, using row 2 for headers")
            else:
                print(f"    🐛 Debug: Found colspan header but no second row for day headers")
                return []
        else:
            # Normal format, use first row for day headers
            header_cells = re.findall(r'<th[^>]*>(.*?)</th>', rows[0], re.DOTALL)
        
        print(f"    🐛 Debug: Found {len(header_cells)} header cells")
        
        for cell_text in header_cells[1:]:  # Skip first "HORÁRIO" column
            day_text = re.sub(r'<[^>]+>', '', cell_text).strip()  # Remove any HTML tags
            if day_text in self.time_mapper.day_to_sigaa:
                day_headers.append(day_text)
        
        print(f"    🐛 Debug: Found {len(day_headers)} valid day headers: {day_headers}")
        
        # Process data rows (skip header row(s))
        schedule_data = []
        start_row = 2 if first_row_has_colspan else 1
        for row_idx, row in enumerate(rows[start_row:], start_row):
            # Extract all cells in this row
            cell_pattern = r'<td[^>]*>(.*?)</td>'
            cells = re.findall(cell_pattern, row, re.DOTALL)
            
            if len(cells) < 2:
                continue
            
            # First cell is time range
            time_range = re.sub(r'<[^>]+>', '', cells[0]).strip()
            
            # Normalize time range format to handle both 2024.1 and 2024.2 formats
            # 2024.1: "08:00 - 09:50" -> "08:00-09:50"
            # 2024.2: "08:00/09:50" -> "08:00/09:50" (already correct)
            time_range = re.sub(r'\s*-\s*', '-', time_range)  # Remove spaces around dash
            
            if not time_range:
                continue
                
            print(f"    🐛 Debug: Row {row_idx} has time range: {time_range}")
            
            # Process each day's cell
            for i, cell_content in enumerate(cells[1:]):
                if i >= len(day_headers):
                    continue
                
                day = day_headers[i]
                clean_content = re.sub(r'<[^>]+>', '', cell_content).strip()
                
                # Parse course information
                course_info = self.parse_course_cell(clean_content)
                if course_info:
                    # Convert to block format
                    block = self.time_mapper.time_range_to_block(time_range, day)
                    if block:
                        schedule_data.append((block, course_info))
                        print(f"    🐛 Debug: Found course {course_info['codigo']} at {block}")
        
        return schedule_data
    
    def parse_markdown_file(self, file_path: str) -> Dict[str, List[Tuple[str, Dict[str, str]]]]:
        """Parse the entire markdown file and extract all schedule data."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📄 File loaded, size: {len(content)} characters")
        
        # Find all tables first, then extract room names from them
        table_pattern = r'<table[^>]*>(.*?)</table>'
        table_matches = list(re.finditer(table_pattern, content, re.DOTALL))
        
        print(f"🔍 Found {len(table_matches)} tables")
        
        all_schedule_data = {}
        processed_rooms = set()
        
        for i, table_match in enumerate(table_matches):
            table_html = table_match.group(0)
            table_content = table_match.group(1)
            table_start = table_match.start()
            
            room_name = None
            
            # Format 1: Room name inside table header (colspan format)
            # Look for: <th colspan="7">Sala: AT-79/11</th> or similar
            colspan_match = re.search(r'<th[^>]*colspan="7"[^>]*>.*?Sala:\s*([A-Z0-9\-\/]+)', table_content, re.DOTALL)
            if colspan_match:
                room_name = colspan_match.group(1).strip()
                print(f"  📍 Processing table {i+1}/{len(table_matches)}: {room_name} (inside header)")
            
            # Format 2: Room name outside table (before <table> tag)
            if not room_name:
                # Look backwards from table start to find the last "Sala:" that hasn't been used
                preceding_text = content[:table_start]
                room_matches = list(re.finditer(r'Sala:\s*([A-Z0-9\-\/]+)', preceding_text))
                
                # Find the last room that hasn't been processed yet
                for room_match in reversed(room_matches):
                    potential_room = room_match.group(1).strip()
                    if potential_room not in processed_rooms:
                        room_name = potential_room
                        print(f"  📍 Processing table {i+1}/{len(table_matches)}: {room_name} (outside table)")
                        break
            
            if room_name:
                schedule_data = self.parse_html_table(table_html, room_name)
                if schedule_data:
                    all_schedule_data[room_name] = schedule_data
                    print(f"    ✅ Found {len(schedule_data)} course allocations")
                    processed_rooms.add(room_name)
                else:
                    print(f"    ⚠️ No course allocations found")
                    processed_rooms.add(room_name)  # Mark as processed even if no data
            else:
                print(f"  ❌ Could not determine room name for table {i+1}")
        
        print(f"📊 Total rooms with data: {len(all_schedule_data)}")
        return all_schedule_data
    
    def generate_csv_data(self, schedule_data: Dict[str, List[Tuple[str, Dict[str, str]]]]) -> List[List[str]]:
        """Generate CSV rows from schedule data."""
        # Collect all unique rooms and blocks
        all_rooms = sorted(schedule_data.keys())
        all_blocks = set()
        
        for room_data in schedule_data.values():
            for block, _ in room_data:
                all_blocks.add(block)
        
        # Sort blocks by day and time for consistency
        sorted_blocks = sorted(all_blocks, key=lambda x: (int(x[0]), x[1], x[2:]))
        
        # Create header row
        header = [""] + all_rooms
        
        # Create data rows
        rows = [header]
        
        # Create a mapping of (block, room) -> course info
        block_room_to_course = {}
        for room_name, room_data in schedule_data.items():
            for block, course_info in room_data:
                block_room_to_course[(block, room_name)] = course_info
        
        # Generate rows for each block
        for block in sorted_blocks:
            row = [block]
            
            for room in all_rooms:
                course_info = block_room_to_course.get((block, room))
                if course_info:
                    # Format as "CODE - NAME - T1"
                    course_str = f"{course_info['codigo']} - {course_info['nome'].upper()} - T{course_info['turma']}"
                    row.append(course_str)
                else:
                    row.append("")
            
            rows.append(row)
        
        return rows
    
    def convert_to_csv(self, input_file: str, output_file: str):
        """Main conversion function."""
        print(f"🔍 Parsing markdown file: {input_file}")
        
        # Parse the markdown file
        schedule_data = self.parse_markdown_file(input_file)
        
        if not schedule_data:
            print("❌ No schedule data found in the markdown file")
            return False
        
        print(f"📊 Found {len(schedule_data)} rooms:")
        for room_name, room_data in schedule_data.items():
            print(f"  - {room_name}: {len(room_data)} course allocations")
        
        # Generate CSV data
        csv_rows = self.generate_csv_data(schedule_data)
        
        # Write to CSV file
        print(f"💾 Writing CSV file: {output_file}")
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerows(csv_rows)
        
        print(f"✅ Conversion completed successfully!")
        print(f"📈 Generated {len(csv_rows)-1} time blocks with {sum(len(data) for data in schedule_data.values())} course allocations")
        
        return True


def main():
    parser = ArgumentParser(description="Convert markdown schedule to CSV format")
    parser.add_argument("input_file", 
                       help="Input markdown file to convert")
    parser.add_argument("--output", "-o", default="docs/Ensalamento Convertido-2024.1.csv",
                       help="Output CSV file (default: docs/Ensalamento Convertido-2024.1.csv)")
    
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        return 1
    
    # Create output directory if needed
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert the file
    converter = MarkdownToCSVConverter()
    success = converter.convert_to_csv(str(input_path), str(output_path))
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
