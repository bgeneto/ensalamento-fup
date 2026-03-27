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
2. Phase 1: hard-rule single-room allocation
3. Partial allocation phase by pending day-group

The legacy full optimized pipeline still exists in the codebase, but it is not the path used by the page button today.

---

## Core Data Model

### Atomic time slots

A SIGAA schedule is broken into atomic tuples:

- `(codigo_bloco, dia_semana_id)`

Example:

- `24M12` becomes `('M1', 2)`, `('M2', 2)`, `('M1', 4)`, `('M2', 4)`

Each tuple becomes one row in `alocacoes_semestrais`.

The actual collision rule is enforced in the database by the unique key on:

- `(semestre_id, sala_id, dia_semana_id, codigo_bloco)`

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

1. resolve the most recent semester that actually has allocations
2. exclude the current semester when possible
3. detect disciplines that:
   - used at least 2 distinct rooms
   - and used at least one non-classroom room
4. cache which days were historically lab days vs classroom-only days

Important implementation details:

- regular classroom type id is assumed to be `2`
- hybrid detection is based on historical allocations, not on rule definitions
- the same detection-semester resolver is now shared by autonomous and manual flows

Output of this phase:

- cached hybrid discipline info
- lab days per discipline
- classroom-only days per discipline

That cache is injected into the scoring service for both autonomous partial scoring and manual block-group suggestions.

---

## Phase 1: Hard Rules Allocation

Purpose:

- allocate demands with `prioridade == 0` rules to one room covering all their atomic blocks when that is possible

What Phase 1 does:

1. collect hard rules for every pending demand
2. keep only demands that actually have hard rules
3. skip demands that already have any allocation rows, so partial reruns do not retry them as full single-room candidates
4. parse the full demand schedule into atomic blocks
5. filter rooms to active rooms that are enabled for all required blocks
6. keep only rooms that satisfy every hard rule
7. batch-check conflicts for all candidate room-slot pairs in the current semester
8. allocate the first room with no conflicts

Important current behavior:

- in the optimized partial pipeline used by the UI, Phase 1 does **not** use the legacy demand-priority ordering from `AutonomousAllocationService._prioritize_demands_for_hard_rules()`
- it processes the demands returned by `ManualAllocationService.get_unallocated_demands()`
- those demands are now defined as demands with pending atomic blocks, not merely demands with zero allocation rows
- room choice within the filtered candidate list effectively follows the room ordering returned by `SalaRepository.get_available_for_allocation()`

So Phase 1 is deterministic, but simpler than the older design docs suggested.

---

## Partial Allocation By Pending Day-Group

Purpose:

- allocate remaining demands day by day instead of forcing a single room for the whole demand
- resume partially allocated demands instead of discarding them from later autonomous runs

For each remaining demand:

1. compute only the atomic blocks that are still pending
2. group those pending blocks by day
3. for each pending day-group, score all eligible rooms independently
4. exclude rooms that violate hard rules before ranking
5. check semester conflicts for that specific day-group
6. allocate the best currently valid room
7. move to the next pending day-group

Important properties:

- different days of the same discipline may end up in different rooms
- if one day was already allocated earlier, reruns only process the remaining days
- no global optimizer is used
- there is no backtracking
- allocation is greedy and local to the current demand and current day-group

This is why the current UI can produce split allocations naturally while still resuming unfinished work.

---

## Scoring Used In The Partial Flow

For each room candidate of a day-group:

```text
score =
    capacity_points
    + hard_rules_points
    + soft_rule_points_and_professor_preferences
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

Important nuances:

- historical frequency counts atomic allocation rows, not distinct semesters
- day-specific historical scoring uses the same day of week as the current block-group
- `Regra.prioridade > 0` now contributes points directly using the rule priority value
- professor preferences are scored whenever the room is hard-rule compliant, including the common case where there are no hard rules at all

---

## What "Soft" Means In The Current Code

The current code now treats two categories as soft score contributors:

- `Regra` entries with `prioridade > 0`
- professor room and characteristic preferences

In practice:

- hard rules come from `Regra` with `prioridade == 0`
- soft rules use the same rule-compliance engine, but add `rule.prioridade` points instead of acting as a mandatory filter
- professor preferences are additive bonuses layered on top of hard-rule-compliant candidates

This aligns the runtime behavior with the intended distinction between mandatory and scored constraints.

---

## Conflict Handling

Conflict checks are semester-isolated:

- only the current semester is checked for autonomous allocation conflicts

The conflict query is based on:

- room id
- day id
- atomic block code
- semester id

Reservations are still not part of the autonomous allocation conflict path.

---

## Result Semantics

In the current partial pipeline, the output metrics are not all demand-based.

Important counters:

- `allocations_completed`
  - phase 1 counts one successful demand allocation
  - partial phase counts one successful block-group allocation
- `block_groups_processed`
  - number of pending day-groups evaluated
- `block_groups_allocated`
  - number of pending day-groups successfully assigned
- `demands_with_split_rooms`
  - number of demands whose allocated day-groups ended in more than one room
- `progress_percentage`
  - in partial mode, this is based on allocated block-groups over processed block-groups

So partial-mode progress is not the same thing as percentage of demands fully completed.

At the service layer, however, queue and manual-progress views now distinguish clearly between:

- fully allocated demands
- partially allocated demands
- demands with pending blocks

---

## Current Guarantees

These points now hold in the runtime code:

1. Partially allocated demands remain pending and are resumed on later autonomous runs.
2. Hard rules are absolute across the scoring pipeline because non-compliant rooms are excluded before ranking.
3. Manual block-group suggestions and autonomous partial scoring use the same hybrid detection semester resolution.
4. Manual block-group suggestions expose the hybrid bonus in the UI breakdown.

---

## Remaining Limitations

### 1. No global optimization

The algorithm is greedy:

- it does not reconsider earlier allocations
- it does not search for a globally optimal semester-wide arrangement

### 2. Conflict checks still ignore reservations

Autonomous scoring and allocation check semester allocations only.

Ad-hoc reservations are not yet merged into the same conflict path.

### 3. Historical scoring is row-based

Historical frequency counts atomic allocation rows, not distinct historical semesters.

This means a historically repeated multi-block allocation can accumulate more points than a semester-level interpretation would suggest.

### 4. The regular-classroom type id is still hardcoded

Hybrid detection still assumes:

- regular classroom type id = `2`

If that convention changes in seeded data, the hybrid bonus logic must be updated too.

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
