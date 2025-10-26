# Autonomous Allocation Scoring System - RF-006

This document details the complete scoring system used by the autonomous allocation algorithm, including all point attributions, rule types, and preference calculations.

## Overview

The autonomous allocation algorithm uses a comprehensive scoring system across three phases:

1. **Hard Rules Phase** - Mandatory constraints (prioritize by restrictiveness)
2. **Soft Scoring Phase** - Weighted preferences with historical frequency
3. **Atomic Allocation Phase** - Highest-scored conflict-free candidates

## Scoring Components

### 1. Hard Rules (Phase 1) - Priority-Based Allocation

Hard rules are **mandatory constraints** that must be satisfied. Demands are prioritized by restrictiveness:

**Priority Scoring Formula:**
```
Base Score = (Number of Hard Rules × 10)
Specific Room Bonus = +50 points (if DISCIPLINA_SALA constraint exists)
Professor Mobility Bonus = +5 points (if professor has baixa_mobilidade + demand has professor)
```

**Priority Order (Highest to Lowest):**
1. **Specific Room Constraints** (50+ points): Demands requiring exact room assignments
2. **Multiple Hard Rules** (20+ points): Demands with 2+ hard constraints
3. **Single Hard Rules** (10+ points): Demands with 1 hard constraint
4. **Professor Mobility** (+5 bonus): Additional priority for mobility-restricted professors
5. **No Hard Rules** (0 points): Standard demands allocated in Phase 3

**Hard Rule Types (prioridade = 0):**

| Rule Type                   | Description            | Points | Example                          |
| --------------------------- | ---------------------- | ------ | -------------------------------- |
| `DISCIPLINA_SALA`           | Specific room required | 50+    | "Mathematics must be in Room A1" |
| `DISCIPLINA_TIPO_SALA`      | Room type required     | 10+    | "Labs must be in Lab rooms"      |
| `DISCIPLINA_CARACTERISTICA` | Room feature required  | 10+    | "Courses need projector"         |

### 2. Soft Scoring (Phase 2) - Weighted Preferences

Soft rules provide **scoring bonuses** but don't prevent allocation. All room candidates are scored for each demand.

**Total Soft Score Formula:**
```
Total Score = Hard Rule Compliance + Professor Preferences + Capacity Match + Historical Frequency
```

**Detailed Scoring Breakdown:**

#### 2.1 Hard Rule Compliance (4 points per hard rule)
- ✅ **+4 points per hard rule satisfied**
- ❌ **0 points if any hard rule violated**
- **Example**: Demand with 2 hard rules → Max 8 points

#### 2.2 Professor Preferences (2 points per preference)
**Room Preferences (+2 points each):**
- Professor's preferred rooms (from `professor_prefere_sala`)
- Multiple preferences allowed (cumulative)

**Characteristic Preferences (+2 points each):**
- Professor's preferred features (from `professor_prefere_caracteristica`)
- Matches room characteristics (projector, accessibility, etc.)
- Multiple preferences allowed (cumulative)

#### 2.3 Capacity Match (1 point)
- ✅ **+1 point**: Room capacity ≥ demand vagas
- ❌ **0 points**: Insufficient capacity
- **Example**: Room capacity 40, demand needs 35 → +1 point

#### 2.4 Historical Frequency Bonus (RF-006.6) - Variable points
**NEW FEATURE**: Dynamically calculated from past allocations

```
Historical Bonus = Number of times this discipline was allocated to this room in previous semesters
```

- **Direct 1:1 relationship**: 1 past allocation = +1 bonus point
- **Excludes current semester**: Only counts historical data
- **Cumulative across all past semesters**
- **Example**: MAT101 allocated to Room A1 in 3 previous semesters → +3 bonus points

**Database Query:**
```sql
SELECT COUNT(*)
FROM alocacao_semestral a
JOIN disciplina d ON a.demanda_id = d.id
WHERE d.codigo_disciplina = ?
  AND a.sala_id = ?
  AND a.semestre_id != ?  -- Exclude current semester
```

### 3. Final Candidate Ranking

**Room candidates are ranked by:**
1. **Total Score** (highest first)
2. **Tiebreaker**: Room ID (ascending - favors lower room numbers)

**Selection Process:**
1. Calculate scores for ALL room × demand combinations
2. Filter out candidates with atomic block conflicts
3. Select highest-scoring conflict-free candidate
4. Allocate if no conflicts detected

## Scoring Examples

### Example 1: High-Priority Hard Rule Demand
**Demand:** Calculus (MAT201), Room Type: "Lecture Hall", Professor: Dr. Silva

**Room A (Lecture Hall, capacity 80):**
- Hard Rule: ✅ Room type matches (+4)
- Professor: ✅ Preferred room (+2)
- Capacity: ✅ 80 ≥ demand (35) (+1)
- History: ✅ MAT201 allocated here 2 times (+2)
- **TOTAL: 4 + 2 + 1 + 2 = 9 points**

**Room B (Standard, capacity 40):**
- Hard Rule: ❌ Wrong room type (0 - fails hard rules)
- Professor: ✅ Preferred room (+2)
- Capacity: ✅ 40 ≥ 35 (+1)
- History: ✅ MAT201 allocated here 1 time (+1)
- **TOTAL: 0 + 2 + 1 + 1 = 4 points** (but 0 hard rule score disqualifies)

**Result:** Room A selected (hard rules satisfied + highest score)

### Example 2: Soft Rules Only Demand
**Demand:** History (HIS101), No hard rules, Professor: Prof. Santos (prefers rooms 5, 10)

**Room 5 (capacity 50):**
- Hard Rule: ✅ No hard rules (neutral)
- Professor: ✅ Preferred room (+2)
- Capacity: ✅ 50 ≥ 40 (+1)
- History: ❌ Never allocated (+0)
- **TOTAL: 0 + 2 + 1 + 0 = 3 points**

**Room 15 (capacity 60):**
- Hard Rule: ✅ No hard rules (neutral)
- Professor: ❌ Not preferred (+0)
- Capacity: ✅ 60 ≥ 40 (+1)
- History: ✅ HIS101 allocated here 3 times (+3)
- **TOTAL: 0 + 0 + 1 + 3 = 4 points**

**Result:** Room 15 selected (higher score from historical frequency)

### Example 3: Capacity-Limited Demand
**Demand:** Large Lecture (PHY301), 120 students, No preferences

**Room A (capacity 100):**
- Capacity: ❌ 100 < 120 (0)
- **TOTAL: 0 points**

**Room B (capacity 150):**
- Capacity: ✅ 150 ≥ 120 (+1)
- History: ✅ PHY301 allocated here twice (+2)
- **TOTAL: 1 + 2 = 3 points**

**Result:** Room B selected (only room with sufficient capacity)

## Phase 1 Priority Examples

### High Priority Allocation (60+ points)
**Demand:** Advanced Chemistry Lab
- Specific room constraint (Room L2 only) → +50
- Room type constraint (Lab) → +10
- **Total Priority:** 60 (allocated first)

### Medium Priority Allocation (10-20 points)
**Demand:** Standard Lecture
- Room type constraint (Lecture Hall) → +10
- Professor with mobility restrictions → +5
- **Total Priority:** 15

### Low Priority Allocation (0 points)
**Demand:** Elective Course
- No hard rules
- No special constraints
- **Total Priority:** 0 (allocated in Phase 3)

## Conflict Detection Integration

All scoring operates within conflict-free boundaries:

1. **Phase 1**: Check conflicts before allocating hard rule demands
2. **Phase 2**: Score candidates but filter out those with conflicts
3. **Phase 3**: Use atomic block allocation (prevents conflicts by construction)

**Conflict Types Detected:**
- Room + Time slot overlaps
- Professor + Time slot overlaps (future enhancement)
- Hard rule violations

## Performance Considerations

**Scoring Optimization:**
- Batch all room queries (single `get_all()` per semester)
- Cache professor lookups for demands with multiple preferences
- Use indexed database queries for historical frequency

**Memory Usage:**
- Candidate scoring: O(rooms × demands) temporary objects
- Atomic blocks pre-parsed once per demand
- Results stored as compact summaries

## Configuration and Extensibility

**Hard Rule Types** (easily extensible):
```json
{
  "DISCIPLINA_SALA": {"sala_id": 123},
  "DISCIPLINA_TIPO_SALA": {"tipo_sala_id": 5},
  "DISCIPLINA_CARACTERISTICA": {"caracteristica_nome": "Projetor"},
  "PROFESSOR_MOBILIDADE": {"baixa_mobilidade": true}
}
```

**Scoring Weights** (configurable):
- Hard rule compliance: 4 points
- Professor preferences: 2 points
- Capacity match: 1 point
- Historical frequency: 1 point per allocation

## Monitoring and Debugging

**Detailed Logging:**
- Phase execution times
- Scoring breakdowns per candidate
- Conflict detection results
- Allocation success/failure reasons

**UI Feedback:**
- Real-time progress during execution
- Phase-by-phase result summaries
- Conflict details and skipped demands
- Success percentages and next steps

## Future Enhancements

**Advanced Scoring Opportunities:**
- Time preference weighting (morning vs. afternoon preferences)
- Room adjacency bonuses (related courses near each other)
- Equipment-specific bonuses (projector for presentation-heavy courses)
- Student concentration patterns
- Professor teaching load balancing

**Machine Learning Integration:**
- Historical success rate predictions
- Dynamic weight adjustments based on past allocation outcomes
- Automated constraint discovery from allocation patterns

---

**Implementation Reference:**
- **Service:** `src/services/autonomous_allocation_service.py`
- **Tests:** `tests/test_autonomous_allocation_service.py`
- **UI:** `pages/7_✅_Ensalamento.py` (Autonomous Allocation button)
