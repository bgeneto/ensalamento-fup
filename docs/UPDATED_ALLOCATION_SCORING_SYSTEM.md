# Current Autonomous Allocation Pipeline

Code-accurate description of the autonomous room-allocation flow currently wired into the Streamlit UI.

This document supersedes older descriptions that assumed the main page was still using the classic full pipeline by default.

---

## Which Entry Point The UI Uses

The main allocation page currently calls:

- `OptimizedAutonomousAllocationService.execute_autonomous_allocation_partial()`

It does **not** call `execute_autonomous_allocation()` from the button used in the page today.

That means the normal UI flow is:

1. Phase 0: hybrid detection
2. Phase 1: hard-rule allocation
3. Combined partial allocation phase by day-group

The legacy full optimized pipeline still exists in the codebase, but it is not the path used by the page button today.

---

## Core Data Model

### Atomic time slots

A SIGAA schedule is broken into atomic tuples:

- `(codigo_bloco, dia_semana_id)`

Example:

- `24M12` becomes `('M1', 2)`, `('M2', 2)`, `('M1', 4)`, `('M2', 4)`

Each tuple becomes one row in `alocacoes_semestrais`.

### Block groups

For partial allocation, atomic blocks are grouped by day:

- same-day blocks must stay together
- different-day groups can go to different rooms

Example:

- `24M12 6T34`
- groups:
  - `SEG`: `M1`, `M2`
  - `QUA`: `M1`, `M2`
  - `SEX`: `T3`, `T4`

---

## Current Pipeline

## Phase 0: Hybrid Detection

Purpose:

- find disciplines that historically split between regular classrooms and specialized rooms

Current detection logic:

1. choose the most recent semester that actually has allocations
2. exclude the current semester when possible
3. detect disciplines that:
   - used at least 2 distinct rooms
   - and used at least one non-classroom room

Important implementation details:

- regular classroom type id is assumed to be `2`
- hybrid detection is based on **historical allocations**, not on rule definitions
- detection also stores which days were historically lab days vs classroom-only days

Output of this phase:

- cached hybrid discipline info
- lab days per discipline
- classroom-only days per discipline

That cache is then injected into the scoring service for autonomous partial scoring.

---

## Phase 1: Hard Rules Allocation

Purpose:

- allocate demands with `prioridade == 0` rules to one room covering all their atomic blocks

What Phase 1 does:

1. collect hard rules for every demand
2. keep only demands that actually have hard rules
3. parse the full demand schedule into atomic blocks
4. filter rooms to active rooms that are enabled for all required blocks
5. keep only rooms that satisfy every hard rule
6. batch-check conflicts for all candidate room-slot pairs in the current semester
7. allocate the first room with no conflicts

Important current behavior:

- in the optimized partial pipeline used by the UI, Phase 1 does **not** use the legacy demand-priority ordering from `AutonomousAllocationService._prioritize_demands_for_hard_rules()`
- it processes the demands in the order returned by `get_unallocated_demands()`
- that order ultimately comes from `DisciplinaRepository.get_by_semestre()`, which sorts by `codigo_disciplina`
- room choice within the filtered candidate list effectively follows the room ordering returned by `SalaRepository.get_available_for_allocation()`, which sorts by room name

So Phase 1 is deterministic, but simpler than the older design docs suggested.

---

## Phase 2/3 Combined: Partial Allocation By Day

Purpose:

- allocate remaining demands day by day instead of forcing a single room for the whole demand

For each remaining demand:

1. group atomic blocks by day
2. for each day-group, score all rooms independently
3. drop candidates that already have conflicts
4. perform a fresh batch conflict check against current database state
5. allocate the best currently valid room
6. move to the next day-group

Important properties:

- different days of the same discipline may end up in different rooms
- no global optimizer is used
- there is no backtracking
- allocation is greedy and local to the current demand and current day-group

This is why the current UI can produce split allocations naturally.

---

## Scoring Used In The Partial Flow

For each room candidate of a day-group:

```text
score =
    capacity_points
    + hard_rules_points
    + professor_preference_points
    + day_specific_historical_points
    + hybrid_bonus_points
```

Current effective weights:

| Weight | Value |
| --- | ---: |
| Capacity adequate | 3 |
| Hard rule compliance | 20 each |
| Preferred room | 4 |
| Preferred characteristic | 4 |
| Historical frequency per allocation row | 2 |
| Historical cap | 20 |
| Hybrid room-type match | 15 |

Important nuance:

- historical frequency counts atomic allocation rows, not distinct semesters
- day-specific historical scoring uses the same day of week as the current block-group

---

## What "Soft" Means In The Current Code

The current code does **not** score `Regra.prioridade > 0` rules.

In practice:

- hard rules come from `Regra` with `prioridade == 0`
- "soft preferences" currently mean professor preferred rooms and preferred characteristics

This is a real divergence from older docs that described scored rule priorities beyond zero.

---

## Conflict Handling

Conflict checks are semester-isolated:

- only the current semester is checked for autonomous allocation conflicts

The conflict query is based on:

- room id
- day id
- atomic block code
- semester id

Reservations are not part of the autonomous allocation conflict path.

---

## Result Semantics

In the current partial pipeline, the output metrics are not all demand-based.

Important counters:

- `allocations_completed`
  - phase 1 counts one successful demand allocation
  - partial phase counts one successful block-group allocation
- `block_groups_processed`
  - number of day-groups evaluated
- `block_groups_allocated`
  - number of day-groups successfully assigned
- `demands_with_split_rooms`
  - number of demands whose allocated day-groups ended in more than one room
- `progress_percentage`
  - in partial mode, this is based on allocated block-groups over processed block-groups

So partial-mode progress is not the same thing as "percentage of demands fully completed".

---

## Important Current Limitations

### 1. Partially allocated demands are excluded from future autonomous runs

`get_unallocated_demands()` treats a demand as allocated as soon as it has at least one allocation row.

Practical consequence:

- if a demand gets only some day-groups allocated
- a later autonomous run will not pick it up again as "unallocated"

The manual UI can still continue the allocation, but the autonomous rerun will not resume it automatically.

### 2. Hard rules are only truly strict in Phase 1

After Phase 1, later scoring does not remove hard-rule-violating candidates from consideration.

Instead:

- violating rooms lose hard-rule points
- professor-preference scoring is skipped
- but capacity, historical, and hybrid points may still leave that room as the top candidate

### 3. Manual and autonomous hybrid behavior can diverge

The autonomous partial flow injects hybrid detection into the scoring service.

The current manual allocation service does not inject that same hybrid service into its own scoring service instance.

Practical consequence:

- manual per-day suggestions can differ from autonomous per-day choices for hybrid disciplines

### 4. No global optimization

The algorithm is greedy:

- it does not reconsider earlier allocations
- it does not search for a globally optimal semester-wide arrangement

### 5. The main UI path does not currently generate PDF reports

PDF generation exists in the legacy full optimized pipeline, not in the partial pipeline currently called by the page button.

See `docs/PDF_REPORT_SYSTEM.md`.

---

## Legacy Full Pipeline Still In The Repository

`execute_autonomous_allocation()` still exists and still documents a more classic:

1. Phase 0
2. Phase 1
3. Phase 2 soft scoring
4. Phase 3 atomic allocation

That full pipeline also generates PDF output.

But that is not the entry point used by the main page today.

---

## Recommended Reading Order

- `docs/ALLOCATION SCORING SYSTEM.md`
- `docs/PARTIAL_ALLOCATION_IMPLEMENTATION.md`
- `docs/PDF_REPORT_SYSTEM.md`
