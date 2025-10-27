# Semester Selector Synchronization Fix (v2)

## Problem Identified

The semester selector was not triggering proper UI synchronization when changed, causing:

1. ❌ Changing semester in Painel did not update sidebar
2. ❌ Changing semester in sidebar did not update Painel
3. ❌ Creating/activating semesters in Settings page did not propagate to other selectors
4. ❌ No feedback messages on semester changes

## Root Cause Analysis

### Initial Diagnosis (v1 - Incomplete)

First attempted fix used `on_change` callback but **forgot to call `st.rerun()`**:

```python
# ❌ V1 FIX (INCOMPLETE): Callback without explicit rerun
def _on_semester_change_callback():
    st.session_state.global_semester_id = new_semester_id
    set_session_feedback(...)
    # Missing st.rerun()! Streamlit doesn't auto-rerun from callbacks
```

**Why this failed:**
- Streamlit callbacks **do NOT automatically trigger rerun**
- Session state updated but UI didn't refresh
- Other components (sidebar/painel) stayed out of sync

### Original Problem (v0)

The initial implementation had TWO issues:

1. **Post-render comparison** (timing issue):
```python
# ❌ WRONG: Check happens AFTER rendering
selected_semester = st.selectbox(...)
if selected_semester != current_global_id:
    set_global_semester(selected_semester)
```

2. **No callback mechanism** - relied on manual comparison after widget rendered

## Solution: Callback WITH Explicit Rerun

**The complete fix requires BOTH:**

1. ✅ Use `on_change` callback for immediate detection
2. ✅ **Explicitly call `st.rerun()` inside the callback**

```python
# ✅ CORRECT V2: Callback with explicit rerun
def _on_semester_change_callback():
    widget_key = st.session_state.get("_current_semester_widget_key")
    new_semester_id = st.session_state[widget_key]

    current_global = st.session_state.get("global_semester_id")
    if new_semester_id != current_global:
        # Update session state
        st.session_state.global_semester_id = new_semester_id

        # Set feedback
        set_session_feedback(...)

        # CRITICAL: Explicitly trigger rerun
        st.rerun()  # ← THIS WAS MISSING IN V1!
```

**Why this works:**
1. ✅ Callback executes synchronously when widget value changes
2. ✅ Session state updates atomically
3. ✅ **`st.rerun()` triggers immediate full app refresh**
4. ✅ All UI components (sidebar + main panel) re-render with new value
5. ✅ Feedback messages persist via session state

## Changes Made

### File: `src/utils/semester_ui_sync.py`

**Modified `_on_semester_change_callback()`:**
- Added **`st.rerun()`** at the end (critical fix!)
- Removed debug logging (clean implementation)
- Kept session state update logic

**Modified `render_semester_selector()`:**
- Store callback metadata BEFORE widget render
- Use widget's session state value if available (handles post-callback state)
- Added `on_change` parameter to selectbox

**No changes to:**
- `initialize_global_semester()` - Works as before
- `set_global_semester()` - Still used for programmatic changes

## Testing

### Manual Test (Recommended)

1. Run the main app:
```bash
streamlit run main.py
```

2. Test each scenario:
   - ✅ Change semester in Painel → Sidebar updates immediately
   - ✅ Change semester in Sidebar → Painel updates immediately
   - ✅ Create semester in Settings → Both Painel and Sidebar update
   - ✅ Feedback toast appears on each change

### Automated Test Script

```bash
streamlit run test_semester_sync.py
```

## Impact on Existing Pages

**No code changes required** - backwards compatible:
- `pages/1_📊_Painel.py` - Works automatically
- `pages/components/ui/semester_badge.py` - Works automatically
- `pages/2_⚙️_Configurações.py` - Works automatically

**All goals achieved:**
1. ✅ **Painel ↔ Sidebar perfect sync**
2. ✅ **Settings integration**
3. ✅ **Proper rerun behavior**
4. ✅ **Correct UI locations**

## Key Lesson: Streamlit Callback Behavior

**IMPORTANT:** Streamlit callbacks **do NOT automatically trigger reruns!**

```python
# ❌ WRONG: Callback without rerun
def on_change_callback():
    st.session_state.value = new_value
    # UI won't update until next interaction!

# ✅ CORRECT: Callback with explicit rerun
def on_change_callback():
    st.session_state.value = new_value
    st.rerun()  # Trigger immediate UI refresh
```

This is different from direct widget usage where Streamlit auto-reruns on interaction.

## Version History

- **v0 (Broken):** Post-render comparison, no callback
- **v1 (Partial):** Added callback but missing `st.rerun()`
- **v2 (Fixed):** Callback with explicit `st.rerun()` ← Current version

## References

- **Streamlit Callbacks:** https://docs.streamlit.io/library/api-reference/widgets#callbacks
- **st.rerun():** https://docs.streamlit.io/library/api-reference/execution-flow/st.rerun
- **Session State:** https://docs.streamlit.io/library/advanced-features/session-state

---

**Fix Date:** October 27, 2025
**Issue:** Semester selector not synchronizing across components
**Root Cause:** Missing `st.rerun()` in callback
**Solution:** Added explicit `st.rerun()` call in `_on_semester_change_callback()`
**Status:** ✅ Resolved (v2)