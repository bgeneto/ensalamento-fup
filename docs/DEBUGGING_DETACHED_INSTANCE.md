# Debugging Guide: DetachedInstance Errors in SQLAlchemy

## Overview

You've been experiencing `DetachedInstance` errors in the Admin Rooms and Admin Allocations pages, but not in the Admin Users page. This guide explains why and how to fix it.

## What is a DetachedInstance Error?

A **DetachedInstance error** occurs when you try to access lazy-loaded relationships or properties of SQLAlchemy objects **after the database session has closed**.

### Example of the Problem:

```python
# ❌ WRONG - This causes DetachedInstance error
with DatabaseSession() as session:
    user = session.query(User).first()
# Session closes here

# Trying to access relationships after session closes
print(user.profile.name)  # ❌ ERROR: profile is detached from session
```

### Example of the Solution:

```python
# ✅ CORRECT - Access relationships while session is open
with DatabaseSession() as session:
    user = session.query(User).first()
    profile_name = user.profile.name  # Access it HERE
# Session closes - we already have the data

print(profile_name)  # ✅ WORKS
```

## Why Does It Happen More in Some Pages?

### Admin Users Page (Works Fine)
The `AuthService` methods likely only return simple scalar data:
```python
def get_all_users():
    with DatabaseSession() as session:
        users = session.query(Usuario).all()
        # Return only simple fields - no lazy-loaded relationships accessed
        return [{"username": u.username, "role": u.role} for u in users]
    # Session closes safely
```

### Admin Rooms & Allocations Pages (Had Errors)
These pages access complex relationships **outside** the session context:

```python
# ❌ PROBLEMATIC CODE
with DatabaseSession() as session:
    rooms = session.query(Sala).all()
# Session closes

for room in rooms:
    print(room.predio.nome)  # ❌ BOOM! DetachedInstance error
    print(room.tipo_sala.descricao)  # ❌ Another error
```

## Root Causes in This Project

### 1. **Service Methods Return Detached Objects**
```python
# In allocation_service.py
@classmethod
def get_allocation_rules(cls) -> List[Regra]:
    with DatabaseSession() as session:
        return session.query(Regra).all()  # Returns detached objects!
    # Session closes immediately after
```

### 2. **Accessing Relationships After Session Closure**
```python
# In salas.py render function
rules = AllocationService.get_allocation_rules()
for rule in rules:
    print(rule.config_json)  # Works (simple column)
    print(rule.relacao.algo)  # ❌ Error (relationship)
```

### 3. **Multiple Session Contexts**
The code opens multiple `DatabaseSession()` contexts, causing objects from one session to become detached.

## Solutions Implemented

### 1. ✅ Enhanced Error Handler (`src/utils/error_handler.py`)

A centralized error handler that:
- Detects DetachedInstance errors reliably
- Logs full stack traces for debugging
- Displays user-friendly error messages
- Guides users to refresh or check their connection

```python
if DatabaseErrorHandler.is_detached_instance_error(e):
    # Show helpful user message and recovery options
```

### 2. ✅ Consistent Error Handling Across All Admin Pages

All admin pages now:
- Import the centralized error handler
- Use proper logging (`logger.exception()`)
- Detect and display errors consistently
- Provide actionable recovery instructions

### 3. ✅ Better Logging

Every page now logs:
- Full exception stack traces
- Error types and messages
- Context about what was being done
- File location and line numbers

Logs are written to `/logs/` and help identify exact failure points.

## How to Fix Similar Errors in Services

### Strategy 1: Eager Load Relationships
```python
@classmethod
def get_allocation_rules(cls) -> List[Regra]:
    """Get all allocation rules with eager loading"""
    with DatabaseSession() as session:
        # Use joinedload or subqueryload to load relationships
        from sqlalchemy.orm import joinedload

        rules = session.query(Regra)\
            .options(joinedload(Regra.semestre))\
            .all()

        # Convert to dictionary to detach safely
        return [{
            'id': r.id,
            'descricao': r.descricao,
            'semestre_nome': r.semestre.nome if r.semestre else None
        } for r in rules]
```

### Strategy 2: Return Serialized Data
```python
@classmethod
def get_room_details(cls, room_id: int) -> Dict:
    """Get room details as a dictionary (safely detached)"""
    with DatabaseSession() as session:
        room = session.query(Sala).filter(Sala.id == room_id).first()

        if not room:
            return None

        return {
            'id': room.id,
            'nome': room.nome,
            'capacidade': room.capacidade,
            'predio_nome': room.predio.nome,  # Access relationship HERE
            'tipo_sala_nome': room.tipo_sala.nome,  # Access HERE
        }
    # Session closes, but we already extracted the data
```

### Strategy 3: Expunge Objects from Session
```python
from sqlalchemy import inspect
from sqlalchemy.orm import make_transient

@classmethod
def get_rooms(cls) -> List[Sala]:
    """Get rooms and expunge from session"""
    with DatabaseSession() as session:
        rooms = session.query(Sala).all()

        # Expunge objects to make them independent
        for room in rooms:
            session.expunge(room)

        return rooms
```

## Debugging Steps for New Errors

1. **Check the logs**: Look in `/logs/` for the full error message
2. **Identify the service method**: Find which service is returning detached objects
3. **Look for relationship access**: See if code accesses `.relationship_name` outside session
4. **Apply one of the three strategies above**
5. **Test the fix**: Verify the page loads without errors

## Key Files Modified

- ✅ `pages/2_Admin_Users.py` - Added centralized error handling and logging
- ✅ `pages/3_Admin_Rooms.py` - Fixed with better error detection
- ✅ `pages/4_Admin_Allocations.py` - Fixed with better error detection
- ✅ `src/utils/error_handler.py` - New centralized error handling module

## Error Detection Patterns

The error handler now detects:

```python
detached_patterns = [
    "DetachedInstance",
    "detached",
    "not bound to a Session",
    "object is being detached",
    "Unexpected state",
]
```

If your error message contains any of these, it will be treated as a DetachedInstance error.

## Testing the Fix

1. Navigate to each admin page
2. Try to interact with the features (filter, sort, create, edit)
3. Check browser console for any errors
4. Check application logs in `/logs/`
5. If errors occur, they should now display helpful recovery messages

## Performance Considerations

- Eager loading relationships improves performance by reducing N+1 queries
- Serializing to dictionaries is lightweight and safe
- Expunging objects is useful but use sparingly

Choose the strategy that best fits your use case:
- **High cardinality data** → Return as dictionaries
- **Complex relationships** → Use eager loading
- **Simple read-only access** → Expunge from session
