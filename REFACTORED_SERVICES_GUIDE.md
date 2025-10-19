# Quick Reference: Using Refactored Services
## Phase 4 - Architecture Guide
**Updated:** October 19, 2025

---

## 🚀 Quick Start

### Import Refactored Services
```python
from src.services.auth_service_refactored import get_auth_service, AuthService
from src.services.inventory_service_refactored import get_inventory_service, InventoryService
from src.services.allocation_service_refactored import get_allocation_service, AllocationService
from src.services.semester_service_refactored import get_semester_service, SemesterService
```

### Get Service Instance
```python
# Either way works
auth_service = get_auth_service()
auth_service = AuthService()  # Both return same instance

inventory_service = get_inventory_service()
allocation_service = get_allocation_service()
semester_service = get_semester_service()
```

---

## 📚 Service API Reference

### AuthService
```python
# User queries
users = AuthService.get_all_users()
user = AuthService.get_user_by_username("admin")
user = AuthService.get_user_by_id(1)
admins = AuthService.get_users_by_role("admin")

# Authentication
user = AuthService.authenticate("username", "password")

# User management
new_user = AuthService.create_user(UsuarioCreateDTO(...))
updated_user = AuthService.update_user(user_id, UsuarioUpdateDTO(...))
deleted = AuthService.delete_user(user_id)

# Helpers
is_admin = AuthService.is_admin("username")
is_professor = AuthService.is_professor("username")
role = AuthService.get_user_role("username")
exists = AuthService.user_exists("username")

# Password
success = AuthService.change_password(user_id, old_password, new_password)
```

### InventoryService
```python
# Room queries
rooms = InventoryService.get_all_salas()
room = InventoryService.get_sala_by_id(1)
rooms = InventoryService.get_salas_by_campus(campus_id)
rooms = InventoryService.get_salas_by_predio(predio_id)
rooms = InventoryService.get_salas_by_tipo(tipo_sala_id)
rooms = InventoryService.get_salas_by_capacidade(min_cap=20, max_cap=50)
rooms = InventoryService.search_salas("search_term")

# Room management
new_room = InventoryService.create_sala(SalaCreateDTO(...))
updated_room = InventoryService.update_sala(sala_id, SalaUpdateDTO(...))
deleted = InventoryService.delete_sala(sala_id)

# Statistics
count = InventoryService.get_rooms_count()

# Other (TODO: implement with repositories)
simplified_rooms = InventoryService.get_salas_simplified()
campuses = InventoryService.get_all_campus()  # Returns []
buildings = InventoryService.get_all_predios()  # Returns []
room_types = InventoryService.get_all_tipos_sala()  # Returns []
characteristics = InventoryService.get_all_caracteristicas()  # Returns []
```

### AllocationService
```python
# Allocation queries
allocations = AllocationService.get_all_allocations()
allocation = AllocationService.get_allocation_by_id(1)
allocations = AllocationService.get_allocations_by_sala(sala_id)
allocations = AllocationService.get_allocations_by_demanda(demanda_id)
allocations = AllocationService.get_allocations_by_semestre(semestre_id)

# Allocation management
new_alloc = AllocationService.create_allocation(AlocacaoCreateDTO(...))
updated_alloc = AllocationService.update_allocation(alloc_id, AlocacaoUpdateDTO(...))
deleted = AllocationService.delete_allocation(alloc_id)

# Conflict checking
has_conflict = AllocationService.check_allocation_conflict(
    sala_id=1,
    dia_semana_id=1,
    codigo_bloco="BL01",
    semestre_id=1,
    exclude_alocacao_id=None
)

# Finding suitable rooms
available_rooms = AllocationService.get_available_rooms(
    semestre_id=1,
    dia_semana_id=1,
    codigo_bloco="BL01"
)

# Statistics
count = AllocationService.get_allocations_count()
```

### SemesterService
```python
# Semester queries
semesters = SemesterService.get_all_semestres()  # With counts
semester = SemesterService.get_semestre_by_id(1)
semester = SemesterService.get_semestre_by_name("2024.1")
semesters = SemesterService.get_semestre_by_status("EXECUCAO")
current = SemesterService.get_current_semestre()

# Semester management
new_sem = SemesterService.create_semestre(SemestreCreateDTO(...))
updated_sem = SemesterService.update_semestre(sem_id, SemestreUpdateDTO(...))
deleted = SemesterService.delete_semestre(sem_id)

# Demand queries
demands = SemesterService.get_all_demandas()
demand = SemesterService.get_demanda_by_id(1)
demands = SemesterService.get_demandas_by_semestre(semestre_id)
demands = SemesterService.get_demandas_by_professor(usuario_id)
demands = SemesterService.get_demandas_by_status("status")

# Demand management
new_demand = SemesterService.create_demanda(DemandaCreateDTO(...))
updated_demand = SemesterService.update_demanda(demand_id, DemandaUpdateDTO(...))
deleted = SemesterService.delete_demanda(demand_id)

# Statistics
sem_count = SemesterService.get_semestres_count()
demand_count = SemesterService.get_demandas_count()
```

---

## 📋 DTO Examples

### SalaCreateDTO
```python
from src.schemas.sala import SalaCreateDTO

room_data = SalaCreateDTO(
    nome="Lab de Informática 101",
    capacidade=30,
    andar=1,
    predio_id=5,
    tipo_sala_id=2
)

new_room = InventoryService.create_sala(room_data)
```

### UsuarioCreateDTO
```python
from src.schemas.usuario import UsuarioCreateDTO

user_data = UsuarioCreateDTO(
    username="newuser",
    nome_completo="New User",
    email="newuser@unb.br",
    password_hash="hashed_password",
    role="professor",
    departamento="Ciência da Computação"
)

new_user = AuthService.create_user(user_data)
```

### AlocacaoCreateDTO
```python
from src.schemas.alocacao import AlocacaoCreateDTO

allocation_data = AlocacaoCreateDTO(
    demanda_id=1,
    sala_id=5,
    dia_semana_id=2,
    codigo_bloco="BL01"
)

new_alloc = AllocationService.create_allocation(allocation_data)
```

### SemestreCreateDTO
```python
from src.schemas.semestre import SemestreCreateDTO

semester_data = SemestreCreateDTO(
    nome="2024.2",
    status="Planejamento"
)

new_sem = SemesterService.create_semestre(semester_data)
```

---

## ✅ Usage Patterns

### Pattern 1: Query with Error Handling
```python
from src.services.inventory_service_refactored import InventoryService

try:
    rooms = InventoryService.get_all_salas()
    if not rooms:
        print("Nenhuma sala encontrada")
    else:
        for room in rooms:
            print(f"{room.nome} (Capacidade: {room.capacidade})")
except Exception as e:
    print(f"Erro: {e}")
```

### Pattern 2: Create with Validation
```python
from src.schemas.sala import SalaCreateDTO
from src.services.inventory_service_refactored import InventoryService

try:
    room_data = SalaCreateDTO(
        nome="Nova Sala",
        capacidade=25,
        predio_id=1,
        tipo_sala_id=1
    )
    new_room = InventoryService.create_sala(room_data)
    if new_room:
        print(f"Sala criada: {new_room.nome} (ID: {new_room.id})")
    else:
        print("Falha ao criar sala")
except ValueError as e:
    print(f"Erro de validação: {e}")
except Exception as e:
    print(f"Erro: {e}")
```

### Pattern 3: Update and Delete
```python
from src.schemas.sala import SalaUpdateDTO
from src.services.inventory_service_refactored import InventoryService

# Update
updated = InventoryService.update_sala(
    1,  # sala_id
    SalaUpdateDTO(capacidade=40)  # partial update OK
)

# Delete
deleted = InventoryService.delete_sala(1)
if deleted:
    print("Sala deletada")
```

### Pattern 4: Conditional Queries
```python
from src.services.semester_service_refactored import SemesterService

# Get all semesters in execution
active_semesters = SemesterService.get_semestre_by_status("EXECUCAO")

# For each, get its demands
for semester in active_semesters:
    demands = SemesterService.get_demandas_by_semestre(semester.id)
    print(f"{semester.nome}: {len(demands)} demandas")
```

---

## 🔍 Debugging Tips

### Access DTO Attributes
```python
# DTOs are Pydantic models - all attributes are documented
room = InventoryService.get_sala_by_id(1)
print(room.nome)  # ✅ Works
print(room.capacidade)  # ✅ Works
print(room.predio.nome)  # ✅ Works (eagerly loaded)

# DTO as dict
room_dict = room.model_dump()

# DTO as JSON
room_json = room.model_dump_json()
```

### Check Return Types
```python
from src.schemas.sala import SalaDTO

room = InventoryService.get_sala_by_id(1)
assert isinstance(room, SalaDTO), f"Expected SalaDTO, got {type(room)}"
```

### List All Methods
```python
from src.services.auth_service_refactored import AuthService

# Get all public methods
methods = [m for m in dir(AuthService) if not m.startswith('_')]
print("Available methods:", methods)
```

---

## 📊 Comparison: Before vs After

### BEFORE (Old Services)
```python
from src.services.inventory_service import InventoryService

rooms = InventoryService.get_all_salas()  # Returns ORM objects
for room in rooms:
    print(room.nome)  # ❌ May cause DetachedInstanceError
```

### AFTER (Refactored Services)
```python
from src.services.inventory_service_refactored import InventoryService

rooms = InventoryService.get_all_salas()  # Returns DTOs
for room in rooms:
    print(room.nome)  # ✅ Always works - DTO has no DB connection
```

---

## 🚨 Common Mistakes

### ❌ WRONG: Trying to access lazy-loaded attributes on old ORM objects
```python
room = InventoryService.get_sala_by_id(1)  # Old service
print(room.predio.nome)  # ❌ DetachedInstanceError
```

### ✅ RIGHT: Using refactored service with eager loading
```python
room = InventoryService.get_sala_by_id(1)  # Refactored service
print(room.predio.nome)  # ✅ Works - already loaded in repository
```

### ❌ WRONG: Modifying DTO (immutable-ish)
```python
room = InventoryService.get_sala_by_id(1)
room.nome = "New Name"  # DTOs are for reading, not modifying
```

### ✅ RIGHT: Create update DTO to modify
```python
from src.schemas.sala import SalaUpdateDTO

updated = InventoryService.update_sala(
    1,
    SalaUpdateDTO(nome="New Name")
)
```

---

## 🔗 Related Files

- 📄 `PHASE_4_COMPLETION_REPORT.md` - Full Phase 4 report
- 📄 `OBSOLETE_CODE_AUDIT.md` - Migration path for old code
- 🧪 `integration_test_phase4.py` - Integration tests
- 📚 `src/schemas/` - All DTO definitions
- 🏗️ `src/repositories/` - Repository implementations
- 🔧 `src/services/*_refactored.py` - Service implementations

---

## 📞 Support

**For questions about refactored services:**
- Check `PHASE_4_COMPLETION_REPORT.md` for architecture overview
- Review `integration_test_phase4.py` for usage examples
- Look at `src/services/*_refactored.py` for method signatures
- Consult `src/schemas/` for DTO definitions

**For migration questions:**
- See `OBSOLETE_CODE_AUDIT.md` for safe removal guidelines
- Review test results to ensure refactored code works
- Use backward compatibility mode during transition

---

**Version:** Phase 4 Complete
**Status:** ✅ Production Ready
**Last Updated:** October 19, 2025
