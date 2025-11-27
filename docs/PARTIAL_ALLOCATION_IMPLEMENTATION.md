# Partial/Split Room Allocation Implementation Plan

**Created:** 2025-11-27
**Status:** In Progress
**Feature:** Support for allocating a single discipline to multiple rooms based on per-day/block scoring

---

## Overview

This document details the implementation plan for supporting **partial/split room allocation**, enabling:

1. **Hybrid disciplines** (e.g., theory in lecture hall, lab in laboratory) to be allocated to different rooms
2. **Per-block scoring** based on historical Room + Day patterns
3. **Manual allocation UI** with block-level selection
4. **Autonomous allocation** that naturally handles splits via unified scoring

---

## Design Principles

### Core Insight
> *"The Detection logic is just to strengthen points in different rooms"*

This means:
- **No special "hybrid mode"** in the algorithm
- **Scoring is always per-block-group** (atomic, grouped by day)
- **Hybrid disciplines naturally get different rooms** because historical data gives higher scores to the "correct" room for each day
- **Non-hybrid disciplines naturally get same room** because historical data gives same room high scores for all days

### Block Grouping Rule
- **Same-day blocks MUST stay together:** `3M1, 3M2, 3M3, 3M4` → Single group (all Tuesday morning)
- **Different-day blocks CAN be split:** `3M1, 3M2, 5M1, 5M2` → Group A: `3M1, 3M2` (Tue), Group B: `5M1, 5M2` (Thu)

### Hybrid Detection
Query `RegraAlocacao` for rules with `tipo_regra = 'DISCIPLINA_TIPO_SALA'` and `prioridade = 0` (hard rules) for the same `codigo_disciplina`. If count > 1 with different `tipo_sala_id` values → hybrid discipline (more points in different rooms).

---

## Scoring Configuration Reference

From `data/scoring_config.json`:

| Weight | Value | Description |
|--------|-------|-------------|
| `CAPACITY_ADEQUATE` | 3 | Room fits student count |
| `HARD_RULE_COMPLIANCE` | 20 | Per satisfied hard rule |
| `PREFERRED_ROOM` | 4 | Professor prefers this room |
| `PREFERRED_CHARACTERISTIC` | 4 | Professor prefers a characteristic this room has |
| `HISTORICAL_FREQUENCY_PER_ALLOCATION` | **2** | Per past allocation (Room + Day pattern) |
| `HISTORICAL_FREQUENCY_MAX_CAP` | 20 | Maximum historical bonus |

---

## Implementation Phases

### Phase A: Block-Level Historical Scoring ✅ COMPLETED
**Files:** `src/repositories/alocacao.py`, `src/services/room_scoring_service.py`

**Objective:** Modify historical scoring to consider Room + Day patterns instead of just Room.

**Completed Changes:**
1. ✅ Added `get_discipline_room_day_frequency()` to `AlocacaoRepository`
   - Query: Count allocations for `(codigo_disciplina, sala_id, dia_semana_id)`
   - Excludes current semester (configurable via `HISTORICAL_EXCLUDE_CURRENT_SEMESTER`)

2. ✅ Added `get_discipline_room_day_frequencies_bulk()` for performance optimization
   - Bulk fetch frequencies for multiple room-day combinations in single query

3. ✅ Added `_calculate_historical_frequency_bonus_per_day()` to `RoomScoringService`
   - New signature: `_calculate_historical_frequency_bonus_per_day(disciplina_codigo, sala_id, dia_semana_id, exclude_semester_id)`
   - Returns points for this specific day pattern

4. ✅ Added new dataclasses for block-group level scoring:
   - `BlockGroup`: Represents blocks on the same day
   - `BlockGroupScoringBreakdown`: Detailed scoring for a block group + room
   - `BlockGroupRoomScore`: Complete scoring result for a block group + room

5. ✅ Added new methods for per-block-group scoring:
   - `group_blocks_by_day()`: Groups atomic blocks by day
   - `score_rooms_for_block_group()`: Scores all rooms for a specific block group
   - `score_rooms_for_all_block_groups()`: Convenience method to score all groups
   - `_calculate_block_group_scoring_breakdown()`: Core per-day scoring logic
   - `_check_block_group_conflicts()`: Conflict detection for specific block group

**Backward Compatibility:** ✅ Verified - Non-hybrid disciplines will get same historical score for all days (since past allocations used same room for all days). Original methods preserved.

---

### Phase B: Block-Group Data Structures ✅ COMPLETED
**Files:** `src/schemas/allocation.py`, `src/utils/sigaa_parser.py`

**Objective:** Create Pydantic schemas and parser utilities for block groups.

**Completed Changes:**

1. ✅ Added Pydantic schemas to `src/schemas/allocation.py`:
   - `BlockGroupBase`: Base schema with day_id, day_name, blocks
   - `BlockGroupRead`: Read schema for API responses
   - `BlockGroupScoringBreakdownSchema`: Detailed per-day scoring breakdown
   - `BlockGroupRoomScoreSchema`: Complete scoring result for UI display
   - `PartialAllocationRequest`: Request schema for partial allocation API
   - `PartialAllocationResult`: Result schema for allocation operations

2. ✅ Added new methods to `SigaaScheduleParser`:
   - `group_blocks_by_day()`: Returns `Dict[int, List[str]]` of day→blocks
   - `get_block_groups_with_names()`: Returns list of dicts with day_id, day_name, blocks
   - `get_time_range_for_blocks()`: Returns human-readable time range for blocks

**Verified:**
- All imports work correctly
- BlockGroup schemas serialize/deserialize properly
- Parser methods return correct groupings
- Time range formatting works correctly

---

### Phase C: Autonomous Allocation Refactor ✅ COMPLETED
**Files:** `src/services/optimized_autonomous_allocation_service.py`

**Objective:** Refactor autonomous allocation to process block groups independently.

**Completed Changes:**

1. ✅ Added new dataclasses:
   - `BlockGroupCandidate`: Room candidate for a specific day
   - `BlockGroupAllocationResult`: Result of allocating a block group

2. ✅ Added `_group_demand_blocks_by_day()`:
   - Groups atomic blocks by SIGAA day ID
   - Returns `Dict[day_id, List[(block_code, day_sigaa)]]`

3. ✅ Added `_score_rooms_for_block_group()`:
   - Scores all rooms for a specific day's blocks
   - Uses `RoomScoringService.score_rooms_for_block_group()` for per-day historical scoring
   - Returns `List[BlockGroupCandidate]` sorted by score

4. ✅ Added `_allocate_block_group()`:
   - Allocates a single block group to a room
   - Uses batch atomic allocation for efficiency

5. ✅ Added `_execute_partial_allocation_phase()`:
   - Processes each demand's block-groups independently
   - Allows different days to go to different rooms
   - Returns both `PhaseResult` and `List[BlockGroupAllocationResult]`

6. ✅ Added `execute_autonomous_allocation_partial()`:
   - New entry point for partial allocation mode
   - Phase 1: Hard rules (unchanged)
   - Phase 2/3 combined: Partial allocation by block group
   - Returns detailed results including split statistics

**Algorithm Changes:**
1. ✅ Parse demand schedule into block groups (group by day)
2. ✅ For each block group, score all rooms independently using per-day historical data
3. ✅ Allocate each group to its highest-scoring available room
4. ✅ Track partial allocations (some groups allocated, others pending)
5. ✅ Return detailed per-block-group results

**API Summary:**
```python
# New entry point for partial allocation
service = OptimizedAutonomousAllocationService(session)
result = service.execute_autonomous_allocation_partial(semester_id, dry_run=False)

# Returns:
{
    "mode": "partial_allocation",
    "block_groups_processed": 45,
    "block_groups_allocated": 42,
    "demands_with_split_rooms": 3,  # Demands allocated to multiple rooms
    "block_group_details": [...],   # Per-group breakdown
}
```

---

### Phase D: Manual Allocation Service Refactor ✅ COMPLETED
**Files:** `src/services/manual_allocation_service.py`

**Objective:** Enable partial allocation with block selection.

**Completed Changes:**

1. ✅ Added `allocate_demand_partial()` method:
   - Accepts optional `day_ids` and `block_codes` parameters
   - Filters blocks to allocate based on these parameters
   - Skips already-allocated blocks
   - Returns `PartialAllocationResult` with allocated/remaining blocks

2. ✅ Added `get_block_groups_for_demand()` method:
   - Returns block groups organized by day with allocation status
   - Shows which blocks are allocated, to which room
   - Includes time ranges for UI display

3. ✅ Added `get_suggestions_for_block_group()` method:
   - Gets room suggestions for a specific day (block group)
   - Uses per-day historical scoring from RoomScoringService
   - Returns sorted list with scores and conflict info

4. ✅ Added `get_allocation_status_for_demand()` method:
   - Comprehensive allocation status summary
   - Shows total/allocated/pending blocks
   - Lists all rooms used and which blocks are assigned to each

**API Summary:**
```python
# Partial allocation
allocate_demand_partial(demanda_id, sala_id, day_ids=[2, 4], block_codes=['M1', 'M2'])
→ PartialAllocationResult(allocated_blocks, remaining_blocks, ...)

# Get block groups with status
get_block_groups_for_demand(demanda_id)
→ [{'day_id': 2, 'day_name': 'SEG', 'blocks': ['M1', 'M2'], 'is_allocated': True, ...}, ...]

# Per-day room suggestions
get_suggestions_for_block_group(demanda_id, day_id=2, semester_id)
→ [{'room_id': 5, 'score': 25, 'breakdown': {...}, ...}, ...]

# Allocation status
get_allocation_status_for_demand(demanda_id)
→ {'total_blocks': 4, 'allocated_blocks': 2, 'is_partially_allocated': True, ...}
```

---

### Phase E: Allocation Assistant UI ✅ COMPLETED
**Files:** `pages/components/allocation_assistant.py`

**Objective:** Add block checkboxes for per-block room selection.

**Completed Changes:**

1. ✅ Added `_render_block_group_selection()`:
   - Displays block groups as checkboxes organized by day
   - Shows allocation status per block group (✅ allocated, 🔲 pending)
   - Allows selecting which day-groups to allocate together

2. ✅ Added `_render_block_group_room_card()`:
   - Per-block-group room suggestions with detailed scoring
   - "Alocar Estes Blocos" button for partial allocation
   - Visual indicators for conflicts and score breakdown

3. ✅ Refactored `render_allocation_assistant()`:
   - Integrated block group selection workflow
   - Shows allocation status summary (e.g., "2/4 blocos alocados")
   - Handles both full and partial allocation flows
   - Properly integrates with ManualAllocationService

4. ✅ Added `_render_manual_selection_partial()`:
   - Manual room selection for selected block groups
   - Conflict detection for partial allocations
   - Integration with existing room dropdown

5. ✅ Preserved backward compatibility:
   - Original `_render_suggestions_section()` still available
   - Original `_render_manual_selection()` still available
   - Non-partial allocation flow unchanged

**UI Flow:**
```
📚 Alocando: Química Geral (FUP0321)

Progresso: 2/4 blocos alocados (50%)

📅 Blocos por dia:
┌─────────────────────────────────────────────────┐
│ ✅ SEG (M1, M2) - Alocado em AT-42/30           │
│ ☐ QUA (M1, M2) - Pendente                       │
└─────────────────────────────────────────────────┘

[Mostrar Sugestões para Blocos Selecionados]

Sugestões para QUA (M1, M2):
┌─────────────────────────────────────────────────┐
│ UAC: Lab-01/25 (Cap: 30) - 22 pontos            │
│ [✅ Alocar Estes Blocos]                         │
└─────────────────────────────────────────────────┘
```

---

## Execution Order

| Phase | Description | Dependencies | Status |
|-------|-------------|--------------|--------|
| A | Historical scoring per day | None | ✅ Completed |
| B | Block-group data structures | None | ✅ Completed |
| D | Manual allocation service | A, B | ✅ Completed |
| E | Allocation assistant UI | D | ✅ Completed |
| C | Autonomous allocation | A, B | ✅ Completed |

**Note:** Phase D and E come before C because manual allocation is more critical for immediate user testing.

---

## Testing Strategy

### Unit Tests
- `test_alocacao_repository.py`: Test `get_historical_by_discipline_room_day()`
- `test_room_scoring_service.py`: Test per-block-group scoring
- `test_sigaa_parser.py`: Test `group_blocks_by_day()`
- `test_manual_allocation_service.py`: Test partial allocation

### Integration Tests
- Allocate hybrid discipline manually (split across rooms)
- Run autonomous allocation with hybrid discipline
- Verify non-hybrid disciplines still allocate to single room

### Manual QA
- [ ] Create hybrid discipline with 2 room type rules
- [ ] Verify allocation assistant shows block groups
- [ ] Allocate blocks to different rooms
- [ ] Verify allocation visualization shows split

---

## Migration & Backward Compatibility

- **No schema changes required**: `AlocacaoSemestral` already stores per-block allocations
- **No data migration**: Existing allocations work as-is
- **Algorithm is backward compatible**: Non-hybrid disciplines naturally get same room for all blocks

---

## Progress Log

### 2025-11-27
- [x] Created implementation plan document
- [x] Phase A: Completed implementation
  - [x] Added `get_discipline_room_day_frequency()` to `AlocacaoRepository`
  - [x] Added `get_discipline_room_day_frequencies_bulk()` to `AlocacaoRepository`
  - [x] Added `_calculate_historical_frequency_bonus_per_day()` to `RoomScoringService`
  - [x] Added `BlockGroup`, `BlockGroupScoringBreakdown`, `BlockGroupRoomScore` dataclasses
  - [x] Added `group_blocks_by_day()` method
  - [x] Added `score_rooms_for_block_group()` method
  - [x] Added `score_rooms_for_all_block_groups()` method
  - [x] Added `_calculate_block_group_scoring_breakdown()` method
  - [x] Added `_check_block_group_conflicts()` method
  - [x] Verified imports and basic functionality
  - [x] Verified backward compatibility (original methods preserved)
- [x] Phase B: Completed implementation
  - [x] Added Pydantic schemas to `src/schemas/allocation.py`:
    - `BlockGroupBase`, `BlockGroupRead`
    - `BlockGroupScoringBreakdownSchema`
    - `BlockGroupRoomScoreSchema`
    - `PartialAllocationRequest`, `PartialAllocationResult`
  - [x] Added parser methods to `src/utils/sigaa_parser.py`:
    - `group_blocks_by_day()` - Returns Dict[int, List[str]]
    - `get_block_groups_with_names()` - Returns list with day names
    - `get_time_range_for_blocks()` - Returns human-readable time range
  - [x] Verified all imports and functionality
- [x] Phase D: Completed implementation
  - [x] Added `allocate_demand_partial()` method to `ManualAllocationService`
  - [x] Added `get_block_groups_for_demand()` method
  - [x] Added `get_suggestions_for_block_group()` method
  - [x] Added `get_allocation_status_for_demand()` method
  - [x] Verified imports and instantiation
  - [x] Verified parser integration works correctly
- [x] Phase E: Completed implementation
  - [x] Refactored `render_allocation_assistant()` with block group support
  - [x] Added `_render_block_group_selection()` with checkboxes
  - [x] Added `_render_block_group_room_card()` for per-group suggestions
  - [x] Added `_render_manual_selection_partial()` for partial allocation
  - [x] Added `_render_conflicting_room_brief()` for conflict display
  - [x] Preserved backward compatibility with original functions
  - [x] Verified imports and syntax (11 functions total)
- [x] Phase C: Completed implementation
  - [x] Added `BlockGroupCandidate` and `BlockGroupAllocationResult` dataclasses
  - [x] Added `_group_demand_blocks_by_day()` method
  - [x] Added `_score_rooms_for_block_group()` method
  - [x] Added `_allocate_block_group()` method
  - [x] Added `_execute_partial_allocation_phase()` method
  - [x] Added `execute_autonomous_allocation_partial()` entry point
  - [x] Verified imports and new methods accessible
