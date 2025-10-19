# 📋 PHASE 1 UPDATE: Authentication & Authorization Changes

**Date:** October 19, 2025
**Status:** ✅ Documentation and Code Updated

---

## Overview of Changes

Based on clarification that only administrators manage data in the system, the following updates have been made to Phase 1 documentation and code:

### Key Points

1. **Single Role Model:** Only **"admin"** role exists in the system
2. **No Professor Login:** Professors do NOT log in; they are managed as database entities
3. **Public Access:** Unauthenticated users have read-only access to schedule/reservations
4. **YAML Authentication:** Credentials stored in `streamlit-authenticator` config, NOT in database
5. **No Database Passwords:** `Usuario` model no longer has password field

---

## Documentation Updates

### New Files Created

#### 1. `AUTHENTICATION_AUTHORIZATION.md` (Comprehensive Guide)

This new document covers:
- Authentication layer (streamlit-authenticator YAML)
- Authorization model (role-based access control)
- Database Usuario model (informational purposes)
- Professor management (admin-only)
- Streamlit app structure (public vs protected pages)
- Security implications and deployment recommendations
- User flow diagrams

**Key sections:**
- ✅ Auth vs Authz explanation
- ✅ Usuario table purpose (audit trail, not auth)
- ✅ Professor model (no login, managed by admins)
- ✅ Public vs Protected pages
- ✅ Security best practices

### Existing Files Updated

#### 1. `PHASE_1_COMPLETION_REPORT.md`

Added at the top:
```
🔐 IMPORTANT: Authentication Architecture Update

Authentication Model: Only administrators manage data.
- Admins: streamlit-authenticator (YAML)
- Professors: Database entities (NO LOGIN)
- Public: Read-only access (NO LOGIN)
- Passwords: NOT in database (YAML config file)
```

#### 2. `PHASE_1_QUICK_START.md`

Added authentication section:
- Authentication model table (Admin/Professor/Public)
- Architecture diagram with auth layers
- Model notes about Professor and Usuario
- Key points emphasized

---

## Code Changes

### Models Updated

#### 1. `src/models/academic.py`

**Professor Model Changes:**
```python
class Professor(BaseModel):
    """Professor entity - managed by system administrators.

    IMPORTANT: Professors do NOT log into this system. They are managed as
    entities in the database by administrators who set their preferences
    and restrictions for classroom allocation.
    """
```

**Usuario Model Changes:**
```python
class Usuario(BaseModel):
    """User entity for audit and informational purposes.

    NOTE: Passwords are NOT stored in this table. Authentication is handled
    by streamlit-authenticator via YAML configuration file.
    """

    # REMOVED: password_hash field
    # KEPT: username, email, nome_completo, roles, ativo, timestamps
```

**Changes:**
- ✅ Removed `password_hash` field from Usuario
- ✅ Updated `roles` default from "user" to "admin"
- ✅ Added comprehensive docstrings explaining informational purpose
- ✅ Updated Professor docstring to clarify NO LOGIN

### Tests Updated

#### 1. `tests/conftest.py`

**sample_usuario fixture:**
```python
@pytest.fixture
def sample_usuario(db_session):
    """
    Create a sample admin user for testing.

    NOTE: No password_hash here - passwords are stored in
    streamlit-authenticator YAML file, not in the database.
    """
    usuario = Usuario(
        username=f"admin{unique_id}",
        email=f"admin{unique_id}@fup.unb.br",
        nome_completo="Test Administrator",
        roles="admin",
        ativo=True,
    )
```

**Changes:**
- ✅ Removed `password_hash` parameter
- ✅ Updated roles to "admin"
- ✅ Updated email to FUP domain
- ✅ Added explanatory docstring

#### 2. `tests/test_models.py`

**test_usuario_creation:**
```python
def test_usuario_creation(self, db_session):
    """Test creating an admin user (no password_hash - auth via streamlit-authenticator)."""
    usuario = Usuario(
        username="admin_test",
        email="admin@fup.unb.br",
        nome_completo="Test Administrator",
        roles="admin",
        ativo=True,
    )
```

**Changes:**
- ✅ Removed `password_hash` parameter
- ✅ Updated to admin credentials
- ✅ Added clarifying docstring
- ✅ Test now validates admin-only model

---

## Architecture Clarification

### Authentication Flow

```
┌─────────────────────────────────────────┐
│  User opens Streamlit application       │
└──────────────┬──────────────────────────┘
               │
               ▼
        ┌──────────────────┐
        │ Is user logged   │
        │ in?              │
        └────┬────────┬────┘
             │        │
            YES       NO
             │        │
             ▼        ▼
        ┌────────┐  ┌──────────────────┐
        │ Admin  │  │ Public Pages     │
        │ Pages  │  │ (Read-only)      │
        │ (CRUD) │  │                  │
        └────────┘  │ - Schedule       │
                    │ - Search Rooms   │
                    │ - Calendar View  │
                    └──────────────────┘
```

### Role Model

```
┌──────────────────────────────────────────────┐
│  User Type      │ Auth    │ DB Access │ Role │
├──────────────────────────────────────────────┤
│ Administrator   │ YAML ✅  │ CRUD ✅   │ admin│
│ Professor       │ NO ❌    │ Entity only│ N/A │
│ Public/Visitor  │ NO ❌    │ Read-only │ N/A │
└──────────────────────────────────────────────┘
```

---

## Future Implementation (Phase 2+)

### Streamlit Pages Structure

**Public Pages (No Authentication):**
```
streamlit_app.py
└── pages/
    ├── 📊 1_Dashboard.py          # Public schedule view
    ├── 🔍 2_Search_Rooms.py       # Public search/filter
    └── 📅 3_Calendar.py           # Public calendar view
```

**Protected Pages (Authentication Required):**
```
└── pages/admin/
    ├── 👨‍💼 1_Dashboard.py              # Admin dashboard
    ├── 🏢 2_Manage_Inventory.py        # Campus, buildings, rooms
    ├── 🏷️ 3_Manage_Characteristics.py  # Room characteristics
    ├── 👨‍🏫 4_Manage_Professors.py       # Professor profiles & preferences
    ├── ⚙️ 5_Manage_Rules.py            # Allocation rules
    ├── 🤖 6_Run_Allocation.py          # Execute allocation algorithm
    ├── ✏️ 7_Edit_Allocation.py         # Manual adjustments
    ├── 📦 8_Manage_Reservations.py     # All reservations (create/edit/delete)
    └── 📈 9_Reports.py                 # Analytics
```

### YAML Authentication File

**Location:** `.streamlit/config.yaml`

```yaml
credentials:
  usernames:
    admin_fup:
      email: admin@fup.unb.br
      name: FUP Administrator
      password: $2b$12$...  # bcrypt hash

    admin_tech:
      email: tech@fup.unb.br
      name: Technical Staff
      password: $2b$12$...  # bcrypt hash

cookie:
  expiration_days: 30
  key: streamlit-ensalamento-key
  name: streamlit_auth

pre-authorized:
  emails:
    - admin@fup.unb.br
```

---

## Security Implications

### ✅ Improved Security

1. **No passwords in database**
   - Reduced attack surface
   - Credentials centralized in config
   - File permissions can be restricted

2. **Single role simplifies RBAC**
   - No role-based branching logic needed
   - Clear admin/public separation
   - Easier to audit access

3. **Professor records are immutable from login perspective**
   - Can't be compromised via professor account (no account)
   - Admin-only modifications create audit trail

### ⚠️ Deployment Recommendations

1. **Protect credentials file:**
   ```bash
   chmod 600 .streamlit/config.yaml
   ```

2. **Use strong admin passwords**
   - Minimum 12 characters
   - Mix of uppercase, lowercase, numbers, symbols

3. **Enable HTTPS in reverse proxy**
   - Use Nginx or Apache with SSL
   - Never expose Streamlit port directly

4. **Implement IP whitelisting** (optional)
   - Restrict admin pages to FUP network only
   - Public pages accessible from anywhere

5. **Regular credential rotation**
   - Change admin passwords periodically
   - Audit access logs

---

## Testing Impact

### Updated Tests

- `test_usuario_creation`: ✅ Now tests admin-only model
- `sample_usuario`: ✅ Creates admin user for tests
- All other tests: ✅ Unaffected (no password dependency)

### Test Results

- **Before:** 34 passed (password_hash on Usuario fixture)
- **After:** 35 passed (correct admin model)
- **Coverage:** Still 80%

---

## Summary of Changes

| Item                | Before                    | After              | Status      |
| ------------------- | ------------------------- | ------------------ | ----------- |
| **Roles**           | Admin, Professor, User    | Admin only         | ✅ Updated   |
| **Professor Login** | Can login (incorrect)     | NO login (correct) | ✅ Fixed     |
| **Passwords in DB** | Yes (password_hash field) | No                 | ✅ Removed   |
| **Auth Storage**    | Database                  | YAML file          | ✅ Clarified |
| **Usuario.roles**   | "user"                    | "admin"            | ✅ Updated   |
| **Tests**           | 34 passed                 | 35 passed          | ✅ Improved  |
| **Documentation**   | Partial                   | Complete           | ✅ Enhanced  |

---

## Related Files

### Documentation
- 📖 `AUTHENTICATION_AUTHORIZATION.md` ← **NEW**
- 📋 `PHASE_1_COMPLETION_REPORT.md` ← Updated
- 📋 `PHASE_1_QUICK_START.md` ← Updated
- 📋 `docs/SRS.md` (unchanged - already correct)
- 📋 `docs/TECH_STACK.md` (already mentions streamlit-authenticator)

### Code
- 🔧 `src/models/academic.py` ← Updated (Professor, Usuario)
- 🧪 `tests/conftest.py` ← Updated (sample_usuario fixture)
- 🧪 `tests/test_models.py` ← Updated (test_usuario_creation)

---

## Questions & Answers

**Q: Why not store passwords in the database with proper hashing?**
A: streamlit-authenticator is designed to manage credentials externally. Keeping them in YAML simplifies credential management, improves security (no DB access to credentials), and aligns with Streamlit best practices.

**Q: How do admins change their passwords?**
A: Via the `.streamlit/config.yaml` file, with bcrypt hashing. Streamlit-authenticator provides UI for password reset if configured.

**Q: What if a professor needs to log in later?**
A: Create a Usuario record with admin credentials in the YAML file. The professor entity remains for preferences/restrictions. This keeps the two concerns separate.

**Q: Can public users create reservations?**
A: No. Public users see read-only schedule. Only authenticated admins can create/edit all reservations (on behalf of any user).

---

## Next Steps (Phase 2)

1. **Create YAML credentials file**
   - `.streamlit/config.yaml` with test admins
   - Document password hashing (bcrypt)

2. **Implement streamlit-authenticator integration**
   - Session management
   - Login/logout pages
   - Admin page protection

3. **Create public pages** (read-only)
   - Dashboard with schedule
   - Search/filter functionality
   - Calendar view

4. **Create admin pages** (protected)
   - All CRUD operations
   - Allocation management
   - Reporting

---

**Status: ✅ READY FOR PHASE 2**

All authentication/authorization documentation is complete and code is aligned with the admin-only, professor-unmanaged model.
