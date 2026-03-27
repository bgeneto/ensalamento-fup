# Allocation Scoring System

Code-accurate description of the scoring logic currently implemented in the repository.

This document intentionally describes the behavior of the code as it exists today, even when that behavior differs from older design docs or from the intended product rules.

---

## Scope

The scoring logic lives mainly in:

- `src/services/room_scoring_service.py`
- `src/config/scoring_config.py`
- `data/scoring_defaults.json`
- `data/scoring_config.json`

There are two scoring paths in the codebase:

1. **Full-demand scoring**
   - Scores one room against all atomic blocks of a demand.
   - Used by the legacy full autonomous pipeline and by legacy manual suggestion helpers.

2. **Block-group scoring**
   - Scores one room against a single day-group of a demand.
   - Used by the current partial/split allocation flow.

---

## Effective Weights

The effective runtime weights come from the merge of:

- `data/scoring_defaults.json`
- `data/scoring_config.json`

Current effective values:

| Weight | Effective value | Notes |
| --- | ---: | --- |
| `CAPACITY_ADEQUATE` | 3 | Adequate capacity |
| `HARD_RULE_COMPLIANCE` | 20 | Per satisfied hard rule |
| `PREFERRED_ROOM` | 4 | Professor prefers this room |
| `PREFERRED_CHARACTERISTIC` | 4 | Professor prefers a characteristic present in the room |
| `HISTORICAL_FREQUENCY_PER_ALLOCATION` | 2 | Per historical allocation row |
| `HISTORICAL_FREQUENCY_MAX_CAP` | 20 | Maximum historical points |
| `HYBRID_ROOM_TYPE_MATCH` | 15 | Comes from defaults because user config does not override it |

Important detail:

- Historical frequency is counted from `alocacoes_semestrais` rows, not from distinct semesters.
- Because allocations are stored by atomic block, one historically allocated discipline can contribute multiple historical counts in the same semester.

---

## Candidate Filtering Before Scoring

Before a room is scored, the code filters candidates to rooms that:

- are active
- are enabled for all required atomic blocks of the demand or block-group

This filtering is done through `SalaRepository.get_available_for_allocation()` and `SalaRepository.is_room_enabled_for_blocks()`.

Conflict detection is separate from availability filtering:

- full-demand scoring checks conflicts for all atomic blocks in the current semester
- block-group scoring checks conflicts only for the selected day-group in the current semester

---

## Atomic Blocks And Time Slots

The system does not allocate a discipline as one opaque schedule.

It first parses the SIGAA code into atomic tuples:

- input example: `24M12`
- parsed tuples: `('M1', 2)`, `('M2', 2)`, `('M1', 4)`, `('M2', 4)`

Each tuple becomes one row in `alocacoes_semestrais`:

- `semestre_id`
- `demanda_id`
- `sala_id`
- `dia_semana_id`
- `codigo_bloco`

The database enforces a unique constraint on:

- `(semestre_id, sala_id, dia_semana_id, codigo_bloco)`

That is the real collision rule for a room time slot.

---

## Hard Rules

Only rules with `prioridade == 0` are used by the scoring logic.

Supported rule types:

| Rule type | Meaning |
| --- | --- |
| `DISCIPLINA_TIPO_SALA` | Room must have a specific `tipo_sala_id` |
| `DISCIPLINA_SALA` | Room must be one specific room |
| `DISCIPLINA_CARACTERISTICA` | Room must contain a characteristic with the configured name |

Current behavior:

- every satisfied hard rule adds `+20`
- if any hard rule fails, the room gets `0` hard-rule points
- when a hard rule fails, the room also skips professor-preference scoring

Important limitation in the current code:

- outside the dedicated hard-rules allocation phase, hard-rule violation does **not** remove the candidate from consideration
- it only removes hard-rule points and professor-preference points
- capacity, historical points, and hybrid bonus can still make that room win later

So in the current implementation, hard rules behave as a strict filter only in **Phase 1** of the autonomous pipeline, not in every later scoring decision.

---

## Professor Preferences

Professor preferences come from:

- `professor_prefere_sala`
- `professor_prefere_caracteristica`

Current scoring:

- preferred room: `+4`
- one matching preferred characteristic: `+4`

Current behavior detail:

- professor preferences are evaluated only when `hard_rules_satisfied` is non-empty
- this means a demand with **no hard rules at all** currently receives `0` preference points

This is a code behavior detail, not a documentation mistake.

Also important:

- rules with `prioridade > 0` are **not** currently used as scored soft rules
- the code shows them in some reports and debug output, but they do not participate in the actual score
- in practice, the only real "soft preferences" used today are professor room/characteristic preferences

---

## Historical Frequency

### Full-demand scoring

Formula:

```text
historical_points = min(
    frequency_rows * HISTORICAL_FREQUENCY_PER_ALLOCATION,
    HISTORICAL_FREQUENCY_MAX_CAP
)
```

Where `frequency_rows` is the number of historical rows in `alocacoes_semestrais` for:

- same `codigo_disciplina`
- same `sala_id`
- excluding the current semester

This is not a count of "times in previous semesters" in the human sense. It is a count of stored allocation rows.

### Block-group scoring

The partial/split flow uses a day-specific variant:

```text
historical_points_for_day = min(
    frequency_rows_for_same_day * HISTORICAL_FREQUENCY_PER_ALLOCATION,
    HISTORICAL_FREQUENCY_MAX_CAP
)
```

Where the historical count is filtered by:

- same `codigo_disciplina`
- same `sala_id`
- same `dia_semana_id`
- excluding the current semester

This is what allows different days of the same discipline to naturally prefer different rooms.

---

## Hybrid Detection And Hybrid Bonus

Hybrid behavior is explicit in the current autonomous partial pipeline.

A discipline is detected as hybrid when, in the most recent historical semester with allocations:

- it used at least 2 distinct rooms
- and at least one of those rooms is not a regular classroom

The code assumes:

- regular classroom type id = `2`

For detected hybrid disciplines, block-group scoring adds `+15` when:

- a non-classroom room is scored on a historical lab day
- or a regular classroom is scored on a historical classroom-only day

Formula used in block-group scoring:

```text
block_group_score =
    capacity_points
    + hard_rules_points
    + soft_preference_points
    + historical_frequency_points_for_day
    + hybrid_bonus_points
```

---

## Current Formulas

### Full-demand scoring

```text
total_score =
    capacity_points
    + hard_rules_points
    + soft_preference_points
    + historical_frequency_points
```

### Block-group scoring

```text
total_score =
    capacity_points
    + hard_rules_points
    + soft_preference_points
    + historical_frequency_points_for_day
    + hybrid_bonus_points
```

---

## Sorting And Tie-Breaks

### Full-demand candidates

Candidates are sorted by:

1. higher score
2. conflict-free rooms before conflicting rooms
3. higher current occupancy as a tie-break

That occupancy tie-break comes from `src/utils/room_utils.py`.

### Block-group candidates

Candidates are sorted by:

1. higher score
2. conflict-free rooms before conflicting rooms

There is no occupancy tie-break in the block-group score list.

---

## Manual Vs Autonomous Consistency

The formulas are centralized in `RoomScoringService`, but the flows are not fully identical.

What is aligned:

- capacity scoring
- hard-rule scoring
- professor-preference scoring
- historical scoring formulas

What is not fully aligned today:

- the autonomous partial pipeline injects hybrid detection into `RoomScoringService`
- the manual allocation service currently instantiates `RoomScoringService` without that injected hybrid service
- as a result, manual block-group suggestions can diverge from autonomous partial scoring for hybrid disciplines

The manual UI also does not currently expose hybrid bonus details in the block-group scoring breakdown.

---

## Important Caveats

These are the most important code-accurate caveats to know:

1. **`prioridade > 0` rules are not part of the runtime score.**
2. **Professor preferences are only scored when at least one hard rule is satisfied.**
3. **Historical counts are row-based at atomic-block level, not distinct-semester counts.**
4. **Hard-rule violations can still win in later scoring phases if other points compensate.**
5. **Hybrid bonus is present in autonomous partial scoring but not reliably present in manual block-group suggestions.**

---

## Related Docs

- `docs/UPDATED_ALLOCATION_SCORING_SYSTEM.md`
- `docs/PARTIAL_ALLOCATION_IMPLEMENTATION.md`
- `docs/PDF_REPORT_SYSTEM.md`
