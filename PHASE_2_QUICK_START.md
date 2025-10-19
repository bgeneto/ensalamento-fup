# 🚀 PHASE 2: QUICK START GUIDE

**Phase 2 Status:** ✅ Infrastructure & Services Complete
**Ready to Run:** Yes - Full Streamlit App with Admin Dashboard

---

## ⚡ Quick Start (5 minutes)

### 1. Initialize Database

```bash
cd /home/bgeneto/github/ensalamento-fup
python init_db.py --all
```

**Output:**
```
✅ All tables created (12 tables)
✅ All reference data seeded (weekdays, time blocks, room types, characteristics)
✅ Admin users created (2 users: admin, gestor)
```

### 2. Start Streamlit App

```bash
streamlit run main.py
```

**App will be available at:** `http://localhost:8501`

### 3. Login

**Test Credentials:**
- Username: `admin`
- Password: `admin123`

---

## 📊 What's Now Available

### Admin Dashboard ✅

After login, you'll see:
- **Início (Home):** Overview with metrics
- **Inventário:** Manage campi, buildings, rooms
- **Professores:** Professor management
- **Demandas:** Course demand import/management
- **Alocações:** Room allocations & algorithm
- **Reservas:** Ad-hoc room reservations
- **Configurações:** System settings

### Database ✅

All 12 tables created with:
- 6 weekdays (SEG, TER, QUA, QUI, SEX, SAB)
- 15 time blocks (M1-M5, T1-T6, N1-N4)
- 5 room types (Classroom, Lab, Auditorium, etc.)
- 8 room characteristics (Projector, Whiteboard, etc.)
- 2 admin users ready to use

### Mock APIs ✅

Available for development:
- **Sistema de Oferta API:** 8 mock courses
- **Brevo API:** Email notification simulation

---

## 🔧 Database Management

### Full Reset (Drop + Create + Seed)

```bash
python init_db.py --all
```

### Just Seed Data (Keep Tables)

```bash
python init_db.py --seed
```

### Drop All Tables

```bash
python init_db.py --drop
```

### Create Empty Tables (No Seed)

```bash
python init_db.py --init
```

---

## 📁 Key Files

### New in Phase 2

| File                         | Purpose                                             | Lines |
| ---------------------------- | --------------------------------------------------- | ----- |
| `src/schemas/inventory.py`   | Campus, Predio, Sala schemas                        | 168   |
| `src/schemas/academic.py`    | Semestre, Demanda, Professor, Usuario schemas       | 163   |
| `src/schemas/horario.py`     | DiaSemana, HorarioBloco schemas                     | 73    |
| `src/schemas/allocation.py`  | Regra, AlocacaoSemestral, ReservaEsporadica schemas | 127   |
| `src/services/api_client.py` | Mock API clients (Sistema de Oferta, Brevo)         | 319   |
| `main.py`                    | Streamlit application with auth                     | 417   |
| `init_db.py`                 | Database initialization script                      | 96    |
| `.streamlit/secrets.yaml`    | Authentication credentials                          | -     |

---

## 🔐 Authentication

### Test Accounts

```yaml
admin:
  Email: admin@fup.unb.br
  Username: admin
  Password: admin123
  Role: admin

gestor:
  Email: gestor@fup.unb.br
  Username: gestor
  Password: (check .streamlit/secrets.yaml)
  Role: admin
```

### How Authentication Works

1. User enters username and password on login screen
2. Credentials checked against `.streamlit/secrets.yaml`
3. On success: Admin dashboard accessible
4. On failure: "Invalid username or password" error
5. Session persists across page reloads
6. Click "Sair" (Logout) to exit

---

## 🧪 Testing Mock APIs

### Test Sistema de Oferta API

```python
from src.services.api_client import sistema_oferta_api

# Get all demands for semester
demands = sistema_oferta_api.get_demands("2025.1")
print(f"Found {len(demands)} courses")
for demand in demands:
    print(f"  - {demand['codigo_disciplina']}: {demand['nome_disciplina']}")
```

**Output:**
```
Found 8 courses
  - CIC0001: Introdução à Computação
  - CIC0002: Programação I
  - CIC0101: Estrutura de Dados
  - ... (5 more courses)
```

### Test Brevo API

```python
from src.services.api_client import brevo_api

# Send test email
response = brevo_api.send_email(
    to="professor@fup.unb.br",
    subject="Test Email",
    html_content="<h1>Hello from Ensalamento!</h1>"
)
print(f"Email sent: {response['messageId']}")
```

**Output:**
```
Email sent: mock_msg_456789
```

---

## 📊 Database Schema Overview

### 12 Tables Organized by Domain

**Inventory (5):**
```
campi (empty)
  └─ predios (empty)
     └─ salas (empty)
        └─ sala_caracteristicas (join table, empty)
caracteristicas (8 seeded)
tipos_sala (5 seeded)
```

**Schedule (2):**
```
dias_semana (6 seeded: SEG-SAB)
horarios_bloco (15 seeded: M1-M5, T1-T6, N1-N4)
```

**Academic (4):**
```
semestres (empty)
demandas (empty)
professores (empty)
usuarios (2 seeded: admin users)
  └─ professor_prefere_sala (join, empty)
  └─ professor_prefere_caracteristica (join, empty)
```

**Allocation (3):**
```
regras (empty)
alocacoes_semestrais (empty)
reservas_esporadicas (empty)
```

---

## 🎯 Next Steps After Phase 2

### Phase 3: UI Implementation

Implement actual CRUD operations for:
- [ ] Inventory management (add/edit rooms)
- [ ] Professor management (import from API)
- [ ] Demand import from Sistema de Oferta
- [ ] Allocation algorithm execution
- [ ] Reservation management

### Phase 4: Business Logic

- [ ] Allocation algorithm
- [ ] Conflict detection
- [ ] Optimization heuristics
- [ ] Reporting & analytics

### Phase 5: Integration

- [ ] Real Sistema de Oferta API
- [ ] Real Brevo API
- [ ] Advanced scheduling
- [ ] Performance optimization

---

## 📝 Architecture Overview

```
┌──────────────────────────────────────────┐
│         Streamlit Frontend               │
│  (main.py - pages, auth, dashboard)      │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────v───────────────────────┐
│  Services Layer (TO BE IMPLEMENTED)      │
│  - Business logic                        │
│  - Allocation algorithm                  │
│  - Data transformation                   │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────v───────────────────────┐
│  Repository Layer (TO BE IMPLEMENTED)    │
│  - CRUD operations                       │
│  - ORM ↔ DTO conversion                  │
│  - Database session management           │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────v───────────────────────┐
│      ORM Models & Schemas                │
│  - 12 ORM models (Phase 1) ✅            │
│  - 30+ DTO schemas (Phase 2) ✅          │
│  - Pydantic validation ✅                │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────v───────────────────────┐
│    SQLite Database                       │
│  - 12 tables created ✅                  │
│  - Reference data seeded ✅              │
│  - Admin users created ✅                │
└──────────────────────────────────────────┘
```

---

## 🔍 Verifying Installation

### Check Database

```bash
# List all tables
sqlite3 data/ensalamento.db ".tables"

# Count records
sqlite3 data/ensalamento.db "SELECT COUNT(*) FROM usuarios;"
```

### Check Imports

```bash
python -c "from src.schemas import inventory, academic; print('✅ Schemas OK')"
python -c "from src.services.api_client import sistema_oferta_api; print('✅ APIs OK')"
```

### Check Admin Users

```bash
python init_db.py --seed  # Will show existing users
```

---

## 🆘 Troubleshooting

### Port Already in Use

```bash
# Kill existing streamlit process
pkill -f streamlit

# Start app on different port
streamlit run main.py --server.port 8502
```

### Database Locked

```bash
# Reset database
rm data/ensalamento.db
python init_db.py --all
```

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt
```

### Authentication Not Working

```bash
# Check credentials file
cat .streamlit/secrets.yaml

# Verify format is YAML (not JSON)
```

---

## 📚 API Usage Examples

### Using Mock Sistema de Oferta

```python
from src.services.api_client import sistema_oferta_api

# Get all demands
demands = sistema_oferta_api.get_demands("2025.1")

# Iterate and display
for demand in demands:
    print(f"{demand['codigo_disciplina']}: {demand['nome_disciplina']}")
    print(f"  Professors: {demand['professores_disciplina']}")
    print(f"  Schedule: {demand['horario_sigaa_bruto']}")
    print(f"  Capacity: {demand['vagas_disciplina']}")
```

### Using Mock Brevo API

```python
from src.services.api_client import brevo_api

# Send allocation notification
response = brevo_api.send_allocation_email(
    recipient_email="prof@fup.unb.br",
    professor_name="Ana Silva",
    discipline_name="Intro to CS",
    room_name="Room 101",
    schedule="Mon/Wed 08:00-09:50"
)

print(f"Message ID: {response['messageId']}")
print(f"Status: {response['status']}")
```

---

## 📋 Checklist Before Phase 3

- [ ] Database initialized: `python init_db.py --all`
- [ ] Streamlit app runs: `streamlit run main.py`
- [ ] Login works with admin/admin123
- [ ] Admin dashboard displays
- [ ] Mock APIs respond correctly
- [ ] All imports work without errors
- [ ] 2 admin users visible in database

---

## 🎓 Key Concepts in Phase 2

### DTO Schemas
- Separate validation from ORM models
- Support for Create/Read/Update operations
- Type hints for all fields
- Pydantic validation

### Mock APIs
- Realistic test data
- No external dependencies needed
- Easy switch to real APIs later
- Proper response formats

### Authentication
- Admin-only system
- YAML-based credentials
- Session management
- Secure password hashing

### Database Initialization
- Automated script for setup
- Reference data seeding
- User account creation
- Multiple operation modes

---

## 🚀 Ready to Go!

Your Phase 2 infrastructure is complete. The application is now ready for:

1. ✅ Admin authentication
2. ✅ Mock API integration
3. ✅ Database persistence
4. ✅ Streamlit UI framework
5. ✅ All foundational services

**Next: Phase 3 - UI Implementation & Business Logic**

---

**Generated:** October 19, 2025
**Version:** Phase 2 Complete
**Status:** Ready for Testing & Phase 3 Development
