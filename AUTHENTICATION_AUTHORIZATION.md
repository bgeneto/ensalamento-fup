# 🔐 Authentication & Authorization Architecture

## Overview

The Ensalamento FUP system uses a **two-tier authentication and authorization model**:

1. **Authentication (streamlit-authenticator):** Handled via YAML file (not database)
2. **Authorization (role-based access control):** Managed by the application

---

## Authentication Layer

### Mechanism: streamlit-authenticator

- **Storage:** YAML configuration file (`.streamlit/config.yaml`)
- **NOT stored in database:** Credentials are managed externally via Streamlit configuration
- **Role:** Single role for logged-in users = **"admin"**
- **Public access:** Available for unauthenticated visitors (no login required)

### Login Credentials YAML File

Example `.streamlit/config.yaml`:

```yaml
credentials:
  usernames:
    admin_user:
      email: admin@fup.unb.br
      name: Administrator
      password: $2b$12$...  # bcrypt hash
    admin_tech:
      email: tech@fup.unb.br
      name: Technical Staff
      password: $2b$12$...  # bcrypt hash

cookie:
  expiration_days: 30
  key: streamlit-app-key
  name: streamlit-auth-cookie

pre-authorized:
  emails:
    - admin@fup.unb.br
```

---

## Authorization Model

### User Roles

| Role                  | Authentication | Data Modification | Reservations             | Preferences | Public View       |
| --------------------- | -------------- | ----------------- | ------------------------ | ----------- | ----------------- |
| **Admin** (logged in) | ✅ Via YAML     | ✅ Full CRUD       | ✅ Create/Edit/Delete all | ✅ Full      | ✅ Yes             |
| **Public** (no login) | ❌ Anonymous    | ❌ No              | ❌ No                     | ❌ No        | ✅ Yes (read-only) |

### Admin Capabilities

**Authenticated admins can:**
- ✅ Add/edit/delete campuses, buildings, rooms
- ✅ Manage room types and characteristics
- ✅ Import semester demands via API
- ✅ Configure allocation rules
- ✅ Execute allocation algorithm
- ✅ Manually adjust allocations
- ✅ Create/manage ALL reservations (on behalf of users)
- ✅ Manage professor preferences and restrictions
- ✅ View reports and analytics

### Public Access Capabilities

**Unauthenticated visitors can:**
- ✅ View room availability schedule
- ✅ Search and filter available rooms
- ✅ View allocations and reservations (read-only)
- ❌ Cannot create or modify data
- ❌ Cannot create reservations
- ❌ Cannot access admin functions

---

## Database Usuario Model Changes

### Current Implementation

The `Usuario` model in the database now serves **informational purposes only**:

```python
class Usuario(BaseModel):
    """User entity for audit and informational purposes."""

    __tablename__ = "usuarios"

    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    nome_completo = Column(String(255), nullable=False)
    roles = Column(String(255), default="admin")  # Only "admin" role
    ativo = Column(Boolean, default=True)
    # NOTE: password_hash NOT stored here - credentials in YAML file
```

### Purpose

The `Usuario` table is used for:
- **Audit logging:** Track which admin made changes
- **User metadata:** Store admin contact information
- **Relationship tracking:** Link to professor preferences, reservations
- **Informational only:** NOT used for authentication

### No Password Storage

- ✅ Passwords are NOT stored in database
- ✅ Authentication handled by streamlit-authenticator (YAML)
- ✅ This improves security and simplifies credential management

---

## Professors in the System

### Important Note

**Professors do NOT log in to this system.**

Instead:
- Professors are managed as **entities in the database** (Professor model)
- Admins create/edit professor profiles and their preferences
- Professors have no login credentials or access to the system
- Professor preferences (room/characteristic) are managed by admins

### Professor Model

```python
class Professor(BaseModel):
    """Professor entity - managed by admins, no system access."""

    __tablename__ = "professores"

    nome_completo = Column(String(255), nullable=False)
    tem_baixa_mobilidade = Column(Boolean, default=False)  # Hard constraint
    username_login = Column(String(100), nullable=True)  # For reference only

    # Relationships managed by admins
    salas_preferidas = relationship(...)  # Preferred rooms
    caracteristicas_preferidas = relationship(...)  # Preferred characteristics
```

---

## Streamlit Application Structure

### Public Pages (No Authentication)

```
pages/
├── 📊 public_dashboard.py          # Schedule visualization
├── 🔍 public_search.py             # Search and filter rooms
└── 📅 public_calendar.py           # Calendar view
```

### Protected Pages (Authentication Required)

```
pages/
├── 👨‍💼 admin/
│   ├── 🏢 manage_inventory.py       # Campus, buildings, rooms
│   ├── 🏷️ manage_characteristics.py # Room characteristics
│   ├── 👨‍🏫 manage_professors.py      # Professor profiles
│   ├── ⚙️ manage_rules.py           # Allocation rules
│   ├── 🤖 run_allocation.py         # Execute allocation algorithm
│   ├── ✏️ edit_allocation.py        # Manual adjustments
│   ├── 📦 manage_reservations.py    # Create/edit all reservations
│   └── 📈 reports.py               # Analytics and reports
```

---

## Security Implications

### Authentication Security

- ✅ Passwords hashed with bcrypt (streamlit-authenticator default)
- ✅ Session management via secure cookies
- ✅ No passwords in database
- ✅ YAML file should be protected in production (restricted file permissions)

### Authorization Security

- ✅ Public pages are read-only
- ✅ Admin pages require valid session
- ✅ Streamlit handles session validation automatically
- ✅ Audit trail via `created_at`, `updated_at` on all models

### Deployment Recommendations

1. **Protect YAML credentials file:**
   ```bash
   chmod 600 .streamlit/config.yaml
   ```

2. **Use environment variables in production:**
   ```python
   import os
   from pathlib import Path

   # Override credentials from environment if available
   credentials_path = os.getenv("STREAMLIT_CREDENTIALS", ".streamlit/config.yaml")
   ```

3. **Enable HTTPS in reverse proxy** (e.g., Nginx)
4. **Use strong passwords** for admin accounts
5. **Rotate credentials regularly**

---

## Implementation Notes for Phase 2

### Changes to Usuario Model

Remove from database:
- ❌ `password_hash` field (not used)

Keep in database for audit/reference:
- ✅ `username` - for audit trail
- ✅ `email` - for admin contact info
- ✅ `nome_completo` - for records
- ✅ `roles` - always "admin"
- ✅ `ativo` - for disabling access without deletion
- ✅ `created_at`, `updated_at` - for audit trail

### Professor Preferences Management

Admins can:
1. Create professor profiles
2. Assign preferred rooms via N:N relationship
3. Assign preferred characteristics via N:N relationship
4. Mark restrictions (e.g., low mobility)
5. Link professor to demand (via professor name matching)

---

## User Flow Diagrams

### Admin Flow

```
┌─────────────────┐
│  Admin Opens    │
│   Application   │
└────────┬────────┘
         │
         ▼
┌──────────────────────────┐
│ Is user authenticated?   │
│ (Check YAML credentials) │
└────────┬────────┬────────┘
         │        │
        Yes       No
         │        │
         ▼        ▼
    ┌────────┐  ┌──────────────┐
    │ Admin  │  │ Show Login   │
    │ Pages  │  │ Page         │
    └────────┘  └──────────────┘
```

### Public Flow

```
┌──────────────────────┐
│ Visitor Opens App    │
└──────────┬───────────┘
           │
           ▼
    ┌────────────────┐
    │ Public Pages   │
    │ (No login req) │
    │                │
    │ - Schedule     │
    │ - Search       │
    │ - Calendar     │
    └────────────────┘
```

---

## Summary Table

| Aspect                  | Details                             |
| ----------------------- | ----------------------------------- |
| **Authentication**      | streamlit-authenticator (YAML file) |
| **Credentials Storage** | YAML file (NOT database)            |
| **Logged-in Role**      | Admin only                          |
| **Role Count**          | 1 (admin)                           |
| **Public Access**       | Read-only (no login)                |
| **Admin Capabilities**  | Full CRUD for all data              |
| **Professor Login**     | ❌ NO (managed by admins)            |
| **Password Hashing**    | bcrypt (streamlit-authenticator)    |
| **Session Management**  | Streamlit secure cookies            |
| **Audit Trail**         | Database timestamps + username      |

---

## Related Documentation

- 📖 [streamlit-authenticator Documentation](../docs/streamlit-authenticator.md)
- 📋 [SRS: Especificação de Requisitos](../docs/SRS.md)
- 🏗️ [System Architecture](../docs/ARCHITECTURE.md)
- 💾 [Database Schema](../docs/schema.sql)
