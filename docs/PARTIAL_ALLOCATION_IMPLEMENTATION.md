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

- same-day blocks are grouped together
- each day-group can be allocated to a different room
- already allocated day-groups can be left untouched while only pending blocks are resumed
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
4. for remaining pending work, process one pending day-group at a time
5. score rooms per day-group
6. allocate the best currently conflict-free and hard-rule-compliant room

This is a greedy algorithm. It is not a global optimizer and it does not backtrack.

---

## Hybrid Detection In The Current Code

The original plan assumed hybrid behavior would emerge only from per-day scoring. That is no longer the whole story.

The code now has an explicit hybrid-detection phase based on historical allocations.

A discipline is treated as hybrid when, in the selected historical semester:

- it used at least 2 distinct rooms
- and at least one room was not a regular classroom

The current manual and autonomous flows both use the same detection-semester resolution:

- prefer the most recent semester with allocations excluding the current semester
- if none exists, fall back to the most recent semester with allocations overall

Both flows inject this hybrid information into `RoomScoringService`.

This enables a real hybrid bonus:

- non-classroom room on a historical lab day: `+15`
- regular classroom on a historical classroom-only day: `+15`

Important:

- hybrid detection is based on historical allocations
- it is **not** based on multiple hard room-type rules as an inference rule

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

- viewing block groups per day
- selecting which days to allocate
- allocating selected day-groups to one room
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
- the partial phase groups only pending atomic blocks by day
- autonomous reruns therefore continue unfinished demands instead of treating them as done

---

## What The Feature Does Well Today

- supports split allocations without schema changes
- uses day-specific historical scoring
- respects room block availability
- performs semester-scoped conflict checks
- resumes partially allocated demands automatically on later autonomous runs
- keeps manual and autonomous hybrid-aware scoring aligned
- enables hybrid disciplines to end up in different room types across days

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
