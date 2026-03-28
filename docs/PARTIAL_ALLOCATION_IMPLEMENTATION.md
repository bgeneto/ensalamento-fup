# Partial And Split Room Allocation

Current implementation notes for the partial/split allocation feature.

This document replaces the older implementation-plan wording and reflects the code that is currently in the repository.

---

## Status

- Feature status: implemented
- Main autonomous UI path: enabled
- Manual UI support: enabled
- Partial-rerun support: enabled

---

## What Partial Allocation Means In This Project

The system stores allocations by atomic block, so a discipline can be split across multiple rooms without schema changes.

In the current implementation:

- blocks are grouped by weekday and turno (`day_id + turno`)
- each block-group can be allocated to a different room
- already allocated block-groups can be left untouched while only pending groups are resumed
- this allows theory/lab splits and other multi-room patterns

Example:

- demand schedule: `24M12`
- groups:
  - `SEG`: `M1`, `M2`
  - `QUA`: `M1`, `M2`

Possible outcome:

- `SEG` in classroom `AT-01`
- `QUA` in lab `UAC-LAB-02`

---

## Current Autonomous Flow

The main page uses:

- `OptimizedAutonomousAllocationService.execute_autonomous_allocation_partial()`

That flow currently works like this:

1. detect hybrid disciplines from historical allocations
2. allocate demands with hard rules to one room when possible
3. skip Phase 1 full-room attempts for demands that are already partially allocated
4. run Phase 1.5 and try to consolidate non-hybrid demands into one room when viable
5. for remaining pending work, process one pending block-group at a time
6. score rooms per block-group
7. allocate the best currently conflict-free and hard-rule-compliant room

This is a greedy algorithm. It is not a global optimizer and it does not backtrack.

---

## Hybrid Detection In The Current Code

The original plan assumed hybrid behavior would emerge only from per-day scoring. That is no longer the whole story.

The code now has an explicit hybrid-detection phase based on historical allocations.

A discipline offering is treated as hybrid by offering key:

- `codigo_disciplina + turma_disciplina`
- it used both regular classrooms and laboratory-family rooms in historical allocations
- and the historical data contains slot-level evidence for both room families

Hybrid requirements are stored per slot:

- key: `(day_id, turno)`
- value: `lab` or `classroom`

This prevents one turma from contaminating another turma of the same discipline code and also prevents different shifts on the same weekday from being merged into one rule.

The current manual and autonomous flows both use the same detection-semester resolution:

- prefer the most recent semester with allocations excluding the current semester
- if none exists, fall back to the most recent semester with allocations overall

Both flows inject this hybrid information into `RoomScoringService`.

This enables slot-aware room-family enforcement and the hybrid bonus:

- laboratory-family room on a historical `lab` slot: `+15`
- regular classroom on a historical `classroom` slot: `+15`

Important:

- hybrid detection is based on historical allocations
- hybrid detection is per offering (`codigo + turma`), not just per discipline code
- hybrid matching is by slot (`day_id + turno`), not just by weekday
- it is **not** based on multiple hard room-type rules as an inference rule

---

## Default Room-Type Eligibility Policy

The current scorer now applies a room-type eligibility filter before ranking rooms.

Current policy:

- regular classrooms are the default eligible room type for ordinary disciplines
- specialized rooms are excluded for ordinary disciplines unless one of these is true:
  - there is an explicit hard or soft room/type override for the discipline
  - the discipline is already partially allocated there and continuity should be preserved
  - the discipline is hybrid and the current slot historically requires that room family

This change closes the old gap where common disciplines could drift into labs or auditoriums purely because of availability or historical frequency.

---

## Operational Room Availability Model

Operational availability is now driven by enabled blocks and turnos, not by the global `Sala.active` flag.

Current behavior:

- `SalaRepository.get_available_for_allocation()` filters rooms by enabled `SalaDisponibilidadeBloco` rows
- `SalaRepository.is_room_enabled_for_blocks()` is the authoritative operational availability check
- the inventory UI manages room operation through M/T/N availability instead of a global active/inactive toggle

In practice, a room is considered operational for allocation if and only if it has the required blocks enabled.

---

## Scoring Used By Partial Allocation

Per day-group, the score is:

```text
score =
    capacity_points
    + hard_rules_points
    + soft_rule_and_preference_points
    + historical_points_for_same_day
    + hybrid_bonus_points
```

Current effective weights:

| Weight | Value |
| --- | ---: |
| `CAPACITY_ADEQUATE` | 3 |
| `HARD_RULE_COMPLIANCE` | 20 |
| `PREFERRED_ROOM` | 4 |
| `PREFERRED_CHARACTERISTIC` | 4 |
| `HISTORICAL_FREQUENCY_PER_ALLOCATION` | 2 |
| `HISTORICAL_FREQUENCY_MAX_CAP` | 20 |
| `HYBRID_ROOM_TYPE_MATCH` | 15 |

Important scoring details:

- historical frequency counts atomic allocation rows, not distinct semesters
- soft rules come from `Regra.prioridade > 0` and add their own priority value as points
- hard-rule failures exclude the room from the candidate list when hard rules exist
- professor preferences are scored whenever the room is hard-rule compliant

---

## Manual UI Support

The allocation assistant supports:

- viewing block groups per day and turno
- selecting which exact block-groups to allocate
- allocating selected block-groups to one room
- continuing a partially allocated demand later
- showing detailed score breakdown, including hybrid bonus

The manual service provides:

- `allocate_demand_partial()`
- `get_block_groups_for_demand()`
- `get_suggestions_for_block_group()`
- `get_allocation_status_for_demand()`

The queue and progress views now distinguish correctly between:

- fully allocated demands
- partially allocated demands
- demands that still have pending blocks

This lets a user complete split allocations interactively without losing partially completed work from the queue.

---

## Partial Demands And Future Autonomous Runs

Partial demands are now resumable by autonomous reruns.

Current behavior:

- `get_unallocated_demands()` returns demands that still have pending blocks
- Phase 1 skips demands that already have some allocations, so it does not retry them as full single-room candidates
- the partial phase groups only pending atomic blocks by `day_id + turno`
- autonomous reruns therefore continue unfinished demands instead of treating them as done

---

## What The Feature Does Well Today

- supports split allocations without schema changes
- uses day-specific historical scoring
- respects room block availability derived from enabled blocks/turnos
- performs semester-scoped conflict checks
- resumes partially allocated demands automatically on later autonomous runs
- keeps manual and autonomous hybrid-aware scoring aligned
- enables hybrid disciplines to end up in different room types across days and shifts

---

## What The Feature Does Not Do Yet

- it does not perform global optimization across all demands
- it does not backtrack after a greedy choice
- it does not include ad-hoc reservations in the autonomous conflict path
- it does not generate PDF output in the main UI path

---

## Related Docs

- `docs/UPDATED_ALLOCATION_SCORING_SYSTEM.md`
- `docs/ALLOCATION SCORING SYSTEM.md`
- `docs/PDF_REPORT_SYSTEM.md`
