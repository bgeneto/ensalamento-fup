#!/usr/bin/env python3
"""
Test script for Phase 0 Hybrid Discipline Detection

Run this script to debug the detection query and verify it works with your data.
"""

import sys
import os

# Add project root to path (parent of tests/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.config.database import get_db_session
from src.repositories.alocacao import AlocacaoRepository
from src.services.hybrid_discipline_service import HybridDisciplineDetectionService


def main():
    print("=" * 70)
    print("PHASE 0: HYBRID DISCIPLINE DETECTION - DEBUG TEST")
    print("=" * 70)

    with get_db_session() as session:
        alocacao_repo = AlocacaoRepository(session)
        hybrid_service = HybridDisciplineDetectionService(session)

        # Step 1: Get most recent semester
        most_recent_semester = alocacao_repo.get_most_recent_semester_id()
        print(f"\n1. Most recent semester ID: {most_recent_semester}")

        # Step 1b: Get most recent semester WITH allocations
        semester_with_allocs = alocacao_repo.get_most_recent_semester_with_allocations()
        print(f"   Semester with allocations: {semester_with_allocs}")

        if not semester_with_allocs:
            print("   ❌ ERROR: No semesters with allocations found!")
            return
        
        # Use the semester that has allocations
        detection_semester = semester_with_allocs

        # Step 2: Check total allocations in the semester
        allocations = alocacao_repo.get_by_semestre(detection_semester)
        print(f"\n2. Total allocations in semester {detection_semester}: {len(allocations)}")

        if not allocations:
            print("   ❌ ERROR: No allocations found in this semester!")
            return

        # Step 3: Analyze room usage per discipline
        print(f"\n3. Analyzing discipline → room allocations...")
        
        discipline_rooms = {}  # {codigo: {room_id: tipo_sala_id}}
        
        for alloc in allocations:
            demanda = alloc.demanda
            if demanda:
                codigo = demanda.codigo_disciplina
                sala_id = alloc.sala_id
                
                if codigo not in discipline_rooms:
                    discipline_rooms[codigo] = {}
                
                discipline_rooms[codigo][sala_id] = None  # We'll get tipo later

        print(f"   Found {len(discipline_rooms)} distinct disciplines with allocations")

        # Step 4: Get room types for each discipline's rooms
        from src.repositories.sala import SalaRepository
        sala_repo = SalaRepository(session)
        
        all_rooms = sala_repo.get_all()
        room_types = {r.id: r.tipo_sala_id for r in all_rooms}
        
        print(f"\n4. Checking room types for each discipline's allocations...")
        
        candidates = []
        for codigo, rooms in discipline_rooms.items():
            room_ids = list(rooms.keys())
            types_used = [room_types.get(rid, None) for rid in room_ids]
            
            # Check criteria: 2+ rooms AND at least one non-classroom (tipo != 2)
            has_multiple_rooms = len(room_ids) >= 2
            has_non_classroom = any(t is not None and t != 2 for t in types_used)
            
            if has_multiple_rooms and has_non_classroom:
                candidates.append({
                    'codigo': codigo,
                    'room_ids': room_ids,
                    'types': types_used
                })
            elif has_multiple_rooms:
                print(f"   {codigo}: {len(room_ids)} rooms, but all are classrooms (tipo=2)")
            elif has_non_classroom and len(room_ids) == 1:
                print(f"   {codigo}: Has non-classroom room but only 1 room total")

        print(f"\n5. Hybrid discipline candidates (2+ rooms, at least 1 non-classroom):")
        if candidates:
            for c in candidates:
                print(f"   ✅ {c['codigo']}: rooms={c['room_ids']}, types={c['types']}")
        else:
            print("   ❌ No candidates found!")
            print("\n   This could mean:")
            print("   - All disciplines use only 1 room")
            print("   - Disciplines with multiple rooms all use only classrooms (tipo=2)")
            print("   - No allocations to non-classroom rooms (labs, auditoriums)")

        # Step 5: Run the actual detection query
        print(f"\n6. Running actual detection query...")
        result = hybrid_service.detect_hybrid_disciplines(detection_semester)
        
        print(f"   Detection result: {result.detected_count} hybrid disciplines")
        
        if result.hybrid_disciplines:
            print("\n   Detected hybrid disciplines:")
            for codigo in result.hybrid_disciplines[:10]:
                info = result.details.get(codigo)
                if info:
                    print(f"   - {codigo}:")
                    print(f"       lab_days: {info.lab_days}")
                    print(f"       classroom_days: {info.classroom_days}")
        else:
            print("\n   ❌ No hybrid disciplines detected by the query!")

        # Step 6: Debug - show room type distribution
        print(f"\n7. Room type distribution in allocations:")
        from collections import Counter
        type_counts = Counter()
        for alloc in allocations:
            tipo = room_types.get(alloc.sala_id)
            type_counts[tipo] = type_counts.get(tipo, 0) + 1
        
        # Get tipo_sala names
        from sqlalchemy import text
        tipo_names = {}
        rows = session.execute(text("SELECT id, nome FROM tipos_sala")).fetchall()
        for row in rows:
            tipo_names[row[0]] = row[1]
        
        for tipo_id, count in sorted(type_counts.items()):
            name = tipo_names.get(tipo_id, "Unknown")
            print(f"   - tipo_sala_id={tipo_id} ({name}): {count} allocations")

        print("\n" + "=" * 70)
        print("DETECTION DEBUG COMPLETE")
        print("=" * 70)


if __name__ == "__main__":
    main()
