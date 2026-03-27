# Partial And Split Room Allocation

Current implementation notes for the partial/split allocation feature.

This document replaces the older implementation-plan wording and reflects the code that is currently in the repository.

---

## Status

- Feature status: implemented
- Main autonomous UI path: enabled
- Manual UI support: enabled
- Important caveats: still present

---

## What Partial Allocation Means In This Project

The system stores allocations by atomic block, so a discipline can be split across multiple rooms without schema changes.

In the current implementation:

- same-day blocks are grouped together
- each day-group can be allocated to a different room
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
3. for remaining demands, process one day-group at a time
4. score rooms per day-group
5. allocate the best currently conflict-free room

This is a greedy algorithm. It is not a global optimizer and it does not backtrack.

---

## Hybrid Detection In The Current Code

The original plan assumed hybrid behavior would emerge only from per-day scoring. That is no longer the whole story.

The code now has an explicit hybrid-detection phase based on historical allocations.

A discipline is treated as hybrid when, in the selected historical semester:

- it used at least 2 distinct rooms
- and at least one room was not a regular classroom

The autonomous partial flow then injects this hybrid information into `RoomScoringService`.

This enables a real hybrid bonus:

- non-classroom room on a historical lab day: `+15`
- regular classroom on a historical classroom-only day: `+15`

Important:

- hybrid detection is based on historical allocations
- it is **not** based on "multiple hard room-type rules" as an inference rule

---

## Scoring Used By Partial Allocation

Per day-group, the score is:

```text
score =
    capacity_points
    + hard_rules_points
    + professor_preference_points
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
- hard-rule failures zero out hard-rule points and professor-preference points
- later scoring still keeps the room as a candidate unless it conflicts in time

---

## Manual UI Support

The allocation assistant supports:

- viewing block groups per day
- selecting which days to allocate
- allocating selected day-groups to one room
- continuing a partially allocated demand later

The manual service provides:

- `allocate_demand_partial()`
- `get_block_groups_for_demand()`
- `get_suggestions_for_block_group()`
- `get_allocation_status_for_demand()`

This lets a user complete split allocations interactively.

---

## Important Caveat: Manual Suggestions Vs Autonomous Suggestions

The manual block-group suggestion path currently instantiates `RoomScoringService` without injecting the hybrid-detection service.

Practical effect:

- autonomous partial allocation can use the hybrid bonus
- manual block-group suggestions may not use that same bonus

So the manual UI and autonomous partial pipeline are structurally similar, but not fully identical for hybrid disciplines.

---

## Important Caveat: Partial Demands And Future Autonomous Runs

In the current code, a demand is treated as "allocated" as soon as it has at least one allocation row.

Practical effect:

- if only some day-groups are allocated
- the demand is partially allocated
- but it is no longer returned by `get_unallocated_demands()`

This means a new autonomous run does not automatically resume partially completed demands.

The manual UI can still continue them because it inspects block-level status directly.

---

## What The Feature Does Well Today

- supports split allocations without schema changes
- uses day-specific historical scoring
- respects room block availability
- performs semester-scoped conflict checks
- enables hybrid disciplines to end up in different room types across days

---

## What The Feature Does Not Do Yet

- it does not perform global optimization across all demands
- it does not backtrack after a greedy choice
- it does not automatically resume partially allocated demands in a new autonomous run
- it does not fully align manual hybrid-aware scoring with autonomous hybrid-aware scoring
- it does not generate PDF output in the main UI path

---

## Related Docs

- `docs/UPDATED_ALLOCATION_SCORING_SYSTEM.md`
- `docs/ALLOCATION SCORING SYSTEM.md`
- `docs/PDF_REPORT_SYSTEM.md`
