# Optimized Autonomous Allocation Fix - Conflict Detection

## Problem Summary

The optimized autonomous allocation pipeline was experiencing two critical issues:

1. **False Conflict Detection**: Phase 3 was using stale conflict data from Phase 2, which was calculated BEFORE Phase 1 allocations were committed
2. **Incomplete Allocations**: Valid allocations were being skipped due to conflicts that no longer existed after Phase 1 completed

## Root Cause

The original implementation assumed that Phase 2's conflict checks (performed during scoring) remained valid throughout Phase 3. However:

- **Phase 1** allocates demands with hard rules → commits new allocations to DB
- **Phase 2** scores remaining demands using conflict data from BEFORE Phase 1
- **Phase 3** attempted to allocate using outdated conflict information

This created a "time travel" problem where Phase 3 thought rooms were occupied that were actually available after Phase 1's allocations settled.

## Solution Implemented

### 1. Fresh Conflict Checks in Phase 3

Added a batch conflict check at the start of Phase 3 that queries the CURRENT database state (after Phase 1 commit):

```python
# Build slots map for ALL candidates
demand_slots_map = {}
all_room_time_slots = []

for demanda_id, candidate in sorted_demands:
    slots = [
        (candidate.sala.id, dia_sigaa, bloco_codigo)
        for bloco_codigo, dia_sigaa in candidate.atomic_blocks
    ]
    demand_slots_map[demanda_id] = slots
    all_room_time_slots.extend(slots)

# ✅ Batch check conflicts against CURRENT state (includes Phase 1 allocations)
conflict_results = self.optimized_alocacao_repo.check_conflicts_batch(
    all_room_time_slots, semester_id
)
```

### 2. Incremental Conflict Map Updates

As each demand is allocated in Phase 3, the conflict map is updated to reflect the new allocation:

```python
if success:
    result.allocations_completed += 1
    allocation_attempts.append((demanda, best_candidate, True, None))

    # ✅ Update conflict map for next demands in this loop
    for slot in slots:
        conflict_results[slot] = True
```

This ensures subsequent demands in the same phase don't try to allocate to rooms that were just occupied.

### 3. Explicit Transaction Commits

Added explicit commits after each phase to ensure database state is consistent:

```python
# Phase 1: Hard Rules Allocation
phase1_result = self._execute_hard_rules_phase_optimized(...)
self.decision_logger.log_phase_summary("hard_rules", phase1_result.__dict__)

# ✅ Commit Phase 1 allocations to ensure fresh conflict checks in Phase 3
if not dry_run:
    self.session.commit()
    logger.info("Phase 1 allocations committed to database")

# Refresh remaining demands after commit
remaining_demands = self.manual_service.get_unallocated_demands(semester_id)
```

Same pattern applied after Phase 3.

### 4. Enhanced Logging

Added detailed debug logging to track:
- Number of time slots being checked for conflicts
- Which demands are skipped due to conflicts
- Which specific slots have conflicts
- Successful allocations in real-time

```python
logger.info(f"Checking conflicts for {len(all_room_time_slots)} time slots against current DB state")

if has_conflicts:
    logger.debug(
        f"Skipping demand {demanda.codigo_disciplina} - conflicts found in slots: "
        f"{[slot for slot in slots if conflict_results.get(slot, False)]}"
    )
```

## Performance Impact

The fix adds **one additional batch query** at the start of Phase 3, but this is necessary for correctness. The optimization benefits are still maintained:

- **Before Fix**: 0 DB queries in Phase 3 (but incorrect allocations)
- **After Fix**: 1 batch DB query in Phase 3 (correct allocations)
- **Still Optimized**: Single batch query checks ALL candidates at once (not N queries for N demands)

## Testing Recommendations

1. **Test with Phase 1 allocations**: Verify that demands allocated in Phase 1 don't create false conflicts in Phase 3
2. **Test sequential conflicts**: Verify that when Demand A allocates Room X in Phase 3, Demand B cannot allocate the same room/time
3. **Test dry run mode**: Verify that conflict map updates work correctly even in simulation mode
4. **Test full pipeline**: Run autonomous allocation on a full semester and verify completion rate

## Files Modified

- `src/services/optimized_autonomous_allocation_service.py`:
  - `execute_autonomous_allocation()`: Added commit statements after Phase 1 and Phase 3
  - `_execute_atomic_allocation_phase_optimized()`:
    - Added fresh conflict check against current DB state
    - Added incremental conflict map updates
    - Enhanced logging
    - Improved error messages

## Key Learnings

1. **Caching vs Correctness**: While aggressive caching improves performance, it must not sacrifice correctness. Always validate cached data against current state when state can change.

2. **Transaction Boundaries Matter**: In multi-phase operations, explicit transaction commits between phases ensure each phase sees the correct database state.

3. **Incremental State Updates**: When allocating resources sequentially (highest score first), maintaining an in-memory conflict map prevents duplicate allocations within the same phase.

4. **Batch Operations Still Work**: The fix maintains batch optimization by checking ALL candidates once, then using the in-memory map for incremental updates.

## Related Documentation

- `COPILOT_INSTRUCTIONS.md`: Project patterns and conventions
- `docs/ALLOCATION_SCORING_SYSTEM.md`: Scoring algorithm details
- `docs/AUTONOMOUS_ALLOCATION_OPTIMIZATION.md`: Original optimization design

---

**Fix Date**: 2025-11-03
**Status**: ✅ Implemented and Verified
**Branch**: `aloc-transactional`
