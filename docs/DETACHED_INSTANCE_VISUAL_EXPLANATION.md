# Why Pages 3 & 4 Failed But Page 2 Didn't

## The Problem Visualized

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PAGE 2: USERS (✅ Works)                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  AuthService.get_all_users()                                       │
│    ↓                                                                │
│  with DatabaseSession() as session:                                │
│    users = session.query(Usuario).all()                            │
│    return [{'username': u.username, 'role': u.role}]               │
│           ↑ Only simple fields, NO relationships accessed          │
│  Session closes ✓ Safe!                                            │
│    ↓                                                                │
│  Streamlit displays user data (simple strings)                      │
│    ↓                                                                │
│  ✅ NO ERRORS                                                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────┐
│              PAGE 3 & 4: ROOMS & ALLOCATIONS (❌ Failed)            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  InventoryService.get_all_salas()                                  │
│    ↓                                                                │
│  with DatabaseSession() as session:                                │
│    return session.query(Sala).all()                                │
│           ↑ Returns full SQLAlchemy objects with relationships     │
│  Session closes ✗ Objects are now DETACHED!                        │
│    ↓                                                                │
│  Page tries to access:                                             │
│    - room.predio (Relationship) ❌ DETACHED!                       │
│    - room.tipo_sala (Relationship) ❌ DETACHED!                    │
│    - room.caracteristicas (List) ❌ DETACHED!                      │
│    ↓                                                                │
│  SQLAlchemy throws:                                                │
│    "Instance {room} is detached from its parent Session"           │
│    ↓                                                                │
│  ❌ "Erro na conexão com o banco de dados"                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Database Session Lifecycle

```
┌──────────────────────────────────────────────────────────────────┐
│ CORRECT: Relationships accessed INSIDE session                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  with DatabaseSession() as session:  ← Session opens            │
│      room = session.query(Sala).first()                          │
│      name = room.predio.nome          ← Access relationship ✓   │
│      data = {                                                    │
│          'nome': room.nome,                                      │
│          'predio': room.predio.nome,   ← Still inside session ✓ │
│      }                                                           │
│      return data                                                 │
│  # Session closes                     ← Safe, we have the data  │
│                                                                  │
│  return data  ✅ WORKS!                                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ WRONG: Relationships accessed OUTSIDE session                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  with DatabaseSession() as session:  ← Session opens            │
│      room = session.query(Sala).first()                          │
│      rooms_list.append(room)                                     │
│  # Session closes                    ← Room is detached NOW!    │
│                                                                  │
│  for room in rooms_list:                                         │
│      print(room.predio.nome)          ← ❌ DETACHED! ERROR!     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## The Fix Applied

### Before (Inconsistent Error Handling)
```python
# Different error detection in each file
if (
    "DetachedInstance" in error_str
    or "detached" in error_str.lower()
    or "not bound to a Session" in error_str
):
    # Show error...
```

### After (Centralized)
```python
# Same logic in one place, reused everywhere
from src.utils.error_handler import DatabaseErrorHandler

if DatabaseErrorHandler.is_detached_instance_error(e):
    st.error("❌ Erro na conexão com o banco de dados.")
    # Show recovery options...
```

## Error Detection Now Covers

✅ "DetachedInstance"
✅ "detached"
✅ "not bound to a Session"
✅ "object is being detached"
✅ "Unexpected state"

## Logging Improvements

```
Before: Silent failures or generic error message

After:
├── Console log: Full exception with context
├── File log: /logs/app.log with timestamp
├── User message: Friendly explanation
├── Recovery button: "Refresh Page"
└── Developer details: Technical stack trace
```

## Three Strategies to Prevent This

### Strategy 1: Serialize to Dictionary (EASIEST)
```python
@classmethod
def get_salas(cls):
    with DatabaseSession() as session:
        return [{
            'id': s.id,
            'nome': s.nome,
            'predio_nome': s.predio.nome,  # Access here
            'capacidade': s.capacidade,
        } for s in session.query(Sala).all()]
```

### Strategy 2: Eager Load Relationships
```python
@classmethod
def get_salas(cls):
    with DatabaseSession() as session:
        from sqlalchemy.orm import joinedload
        return session.query(Sala)\
            .options(joinedload(Sala.predio))\
            .options(joinedload(Sala.tipo_sala))\
            .all()
```

### Strategy 3: Expunge from Session
```python
@classmethod
def get_salas(cls):
    with DatabaseSession() as session:
        salas = session.query(Sala).all()
        for sala in salas:
            session.expunge(sala)
        return salas
```

## Performance Impact

- **Serialization**: ⚡ Fast, reduces payload
- **Eager loading**: ⚡⚡ Reduces round-trips
- **Expunge**: ⚡ Memory-efficient

Choose based on your data volume and access patterns!
