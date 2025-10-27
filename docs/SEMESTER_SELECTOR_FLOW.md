# Semester Selector Synchronization Flow

## Before Fix (Broken) ❌

```
User changes selectbox in Painel
         ↓
on_change callback fires
         ↓
session_state.global_semester_id = new_value
         ↓
set_session_feedback(...)
         ↓
[MISSING st.rerun()!] ← Problem here!
         ↓
Callback ends
         ↓
Script continues running with OLD UI state
         ↓
Sidebar shows OLD semester (not synced)
         ↓
Painel shows NEW semester in widget but OLD everywhere else
         ↓
❌ Result: Out of sync, no feedback visible
```

## After Fix (Working) ✅

```
User changes selectbox in Painel
         ↓
on_change callback fires
         ↓
session_state.global_semester_id = new_value
         ↓
set_session_feedback(...)
         ↓
st.rerun() ← FIX: Explicitly trigger rerun
         ↓
Streamlit stops current script execution
         ↓
Full app rerun with NEW session state
         ↓
Painel re-renders with new semester
         ↓
Sidebar re-renders with new semester (synced!)
         ↓
Feedback toast displays
         ↓
✅ Result: Perfect sync across all components
```

## Code Comparison

### Before (V1 - Broken)
```python
def _on_semester_change_callback():
    widget_key = st.session_state.get("_current_semester_widget_key")
    new_semester_id = st.session_state[widget_key]

    current_global = st.session_state.get("global_semester_id")
    if new_semester_id != current_global:
        st.session_state.global_semester_id = new_semester_id
        set_session_feedback(...)
        # ← Missing st.rerun() here!
```

### After (V2 - Fixed)
```python
def _on_semester_change_callback():
    widget_key = st.session_state.get("_current_semester_widget_key")
    new_semester_id = st.session_state[widget_key]

    current_global = st.session_state.get("global_semester_id")
    if new_semester_id != current_global:
        st.session_state.global_semester_id = new_semester_id
        set_session_feedback(...)
        st.rerun()  # ✅ CRITICAL FIX
```

## Component Interaction

```
┌─────────────────────────────────────────────────────────┐
│                    Session State                         │
│  global_semester_id: 5 → 4 (updated by callback)       │
└─────────────────────────────────────────────────────────┘
                            ↓
                      st.rerun()
                            ↓
┌──────────────────┬────────────────────┬─────────────────┐
│                  │                    │                 │
│  Painel Page     │   Sidebar Badge    │  Settings Page  │
│  (main content)  │   (all pages)      │  (admin)        │
│                  │                    │                 │
│  Selectbox: 4 ✅ │   Selectbox: 4 ✅  │  Table: 4 ✅    │
│  Shows semester  │   Shows semester   │  Shows active   │
│  #4              │   #4               │  semester #4    │
│                  │                    │                 │
└──────────────────┴────────────────────┴─────────────────┘
                            ↓
                    All components synchronized!
```

## Timeline of Discovery

1. **Initial Issue**: Post-render comparison (race condition)
2. **V1 Fix Attempt**: Added `on_change` callback
3. **V1 Result**: Still broken - no UI updates
4. **Investigation**: Why doesn't callback trigger updates?
5. **Discovery**: Streamlit callbacks don't auto-rerun!
6. **V2 Fix**: Added explicit `st.rerun()` in callback
7. **V2 Result**: ✅ Perfect synchronization achieved

## Key Insight

> **Streamlit Callback Rule:**
> Callbacks update session state but **DO NOT** automatically trigger UI refresh.
> You **MUST** call `st.rerun()` explicitly if you want immediate visual updates.

This is documented but easy to miss in the Streamlit docs!

---

**Moral of the story:** Always test UI synchronization after implementing callbacks, and don't assume Streamlit will auto-rerun. When in doubt, add `st.rerun()`!
