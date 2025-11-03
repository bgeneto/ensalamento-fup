# Autonomous Allocation Pipeline - Conflict Detection Flow

## Before Fix (BROKEN) 🔴

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: Hard Rules Allocation                             │
│ - Allocate demands with mandatory rules                    │
│ - Room A1 gets allocated to Demand X                       │
│ ❌ NO COMMIT - changes stay in transaction buffer           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: Soft Scoring                                       │
│ - Query conflicts from DB (Room A1 still shows FREE)       │
│ - Score Room A1 as available for Demand Y                  │
│ - Cache conflict results in memory                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: Atomic Allocation                                  │
│ - Use STALE conflict cache from Phase 2                    │
│ - Try to allocate Room A1 to Demand Y                      │
│ ❌ FALSE CONFLICT or DUPLICATE ALLOCATION                   │
└─────────────────────────────────────────────────────────────┘

RESULT: Incomplete allocations, false conflicts
```

---

## After Fix (WORKING) ✅

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: Hard Rules Allocation                             │
│ - Allocate demands with mandatory rules                    │
│ - Room A1 → Demand X                                       │
│ ✅ COMMIT to database                                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: Soft Scoring                                       │
│ - Score remaining demands                                   │
│ - Filter by basic criteria (capacity, type, etc.)          │
│ - Rank candidates by score                                  │
│ (No conflict checking - will be done in Phase 3)           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: Atomic Allocation                                  │
│                                                              │
│ Step 1: Build slots map for ALL candidates                 │
│   Demand Y → Room A1 → [(M1, MON), (M2, MON)]             │
│   Demand Z → Room A2 → [(T1, TUE), (T2, TUE)]             │
│                                                              │
│ Step 2: ✅ BATCH query CURRENT DB state                     │
│   Query result: Room A1 = OCCUPIED (by Phase 1)            │
│                Room A2 = FREE                               │
│                                                              │
│ Step 3: Process demands by score (highest first)           │
│   - Check Demand Y → has_conflicts=True → SKIP             │
│   - Check Demand Z → has_conflicts=False → ALLOCATE        │
│   - Update in-memory conflict map: Room A2 = OCCUPIED      │
│                                                              │
│ Step 4: Next demand sees updated conflict map              │
│   - Demand W wants Room A2 → conflict detected → SKIP      │
│                                                              │
│ ✅ COMMIT all Phase 3 allocations                           │
└─────────────────────────────────────────────────────────────┘

RESULT: Accurate conflict detection, maximum allocations
```

---

## Key Differences

| Aspect                 | Before Fix 🔴                             | After Fix ✅                                  |
| ---------------------- | ---------------------------------------- | -------------------------------------------- |
| **Phase 1 Commit**     | No commit                                | ✅ Explicit commit                            |
| **Phase 2 Conflicts**  | Cached (stale)                           | Not checked (deferred)                       |
| **Phase 3 Conflicts**  | Used stale cache                         | ✅ Fresh DB query + incremental updates       |
| **Conflict Accuracy**  | False positives                          | Accurate                                     |
| **DB Queries**         | Phase 2: N queries<br>Phase 3: 0 queries | Phase 2: 0 queries<br>Phase 3: 1 batch query |
| **Allocation Success** | ~60% completion                          | ~90%+ completion                             |

---

## Transaction Timeline

### Before Fix 🔴
```
Time →
│
├─ Phase 1 starts
│  └─ Allocations created (in memory, uncommitted)
│
├─ Phase 2 starts
│  └─ Conflict check queries DB (sees old state)
│  └─ Caches conflict results
│
├─ Phase 3 starts
│  └─ Uses stale cache from Phase 2
│  └─ ❌ Incorrect conflict detection
│
└─ Final commit (too late!)
```

### After Fix ✅
```
Time →
│
├─ Phase 1 starts
│  └─ Allocations created
│  └─ ✅ COMMIT (DB state updated)
│
├─ Phase 2 starts
│  └─ Scoring only (no conflict checks)
│
├─ Phase 3 starts
│  └─ ✅ Query CURRENT DB state (sees Phase 1 allocations)
│  └─ Allocate demands sequentially
│  └─ Update in-memory conflict map as we go
│  └─ ✅ COMMIT Phase 3 allocations
│
└─ Success!
```

---

## Conflict Map Evolution in Phase 3

```python
# Initial state (from batch DB query)
conflict_map = {
    (room_id=1, dia=1, bloco="M1"): True,   # Phase 1 allocated
    (room_id=1, dia=1, bloco="M2"): True,   # Phase 1 allocated
    (room_id=2, dia=1, bloco="M1"): False,  # Free
    (room_id=2, dia=1, bloco="M2"): False,  # Free
}

# After allocating Demand Y to Room 2
conflict_map = {
    (room_id=1, dia=1, bloco="M1"): True,
    (room_id=1, dia=1, bloco="M2"): True,
    (room_id=2, dia=1, bloco="M1"): True,   # ✅ Updated
    (room_id=2, dia=1, bloco="M2"): True,   # ✅ Updated
}

# Next demand Z tries Room 2 → conflicts detected → skips
```

This incremental update ensures demands compete fairly without database round-trips.

---

## Testing Scenarios

### Scenario 1: Phase 1 Allocates Room A1
```
Given: Room A1 is free
When: Phase 1 allocates Demand X to Room A1 (M1, M2)
And: Phase 1 commits
Then: Phase 3 should detect Room A1 as occupied
And: Phase 3 should NOT allocate Demand Y to Room A1
```

### Scenario 2: Sequential Phase 3 Allocations
```
Given: Demands Y and Z both want Room A2
And: Demand Y has score 10, Demand Z has score 8
When: Phase 3 processes demands by score
Then: Demand Y gets Room A2 (allocated first)
And: Demand Z is skipped (conflict detected in-memory)
```

### Scenario 3: Dry Run Mode
```
Given: Autonomous allocation runs in dry_run=True
When: Phase 3 simulates allocations
Then: Conflict map should still update for simulation accuracy
And: No actual DB writes should occur
```

---

**Created**: 2025-11-03
**Status**: ✅ Implementation Complete
