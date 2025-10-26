# Allocation Scoring System - RF-006

This document details the complete scoring system used by the autonomous and manual allocation algorithm, including all point attributions, rule types, and preference calculations.

## System Architecture

### Core Components
The scoring system is implemented through three main components:

1. **RoomScoringService** (`src/services/room_scoring_service.py`)
   - Unified scoring engine for both manual and autonomous allocation
   - Single source of truth for all scoring logic
   - Semester-isolated conflict detection

2. **ManualAllocationService** (`src/services/manual_allocation_service.py`)
   - Integrated with RoomScoringService for consistent suggestions
   - Provides detailed breakdown for UI transparency

3. **AutonomousAllocationService** (`src/services/autonomous_allocation_service.py`)
   - Uses same scoring logic for automatic allocation decisions
   - Implements three-phase algorithm with prioritization

## Scoring Breakdown

### Point Categories

The scoring system awards points across four main categories:

#### 1. Capacity Score (+1 point)
- **Requirement**: Room capacity ≥ Demand student count
- **Points**: 1 point if capacity adequate, 0 if insufficient
- **Purpose**: Basic requirement check for room size

#### 2. Hard Rules Compliance (+4 points each)
- **Priority**: Rule priority = 0 (hard rules)
- **Points**: 4 points per satisfied hard rule
- **Failure Cascades**: If ANY hard rule fails, scores 0 for hard rules AND soft preferences are not checked
- **Rule Types**:

  | Rule Type                   | Description                       | Example                         |
  | --------------------------- | --------------------------------- | ------------------------------- |
  | `DISCIPLINA_TIPO_SALA`      | Room must be specific type        | Lab, Lecture Hall, Seminar Room |
  | `DISCIPLINA_SALA`           | Must use specific room            | "Room B203 only"                |
  | `DISCIPLINA_CARACTERISTICA` | Must have specific characteristic | "Projector required"            |

#### 3. Professor Preferences (+2 points each category)
- **Priority**: Only checked if hard rules pass
- **Points**: 2 points per satisfied preference category
- **Categories**:
  - **Room Preferences**: Professor's preferred room (must match exactly)
  - **Characteristic Preferences**: Professor's preferred room characteristics (any match counts)

#### 4. Historical Frequency Bonus (+1 point per allocation)
- **Algorithm**: RF-006.6 - Direct bonus for previous allocations
- **Points**: 1 point × number of times this discipline was allocated to this room in previous semesters
- **Purpose**: Continuity and room familiarity

### Total Score Calculation
```python
total_score = capacity_points + hard_rules_points + soft_preference_points + historical_points
```

**Example Score Calculation:**
```
Room Score: 12 points
- Capacity: ✅ Adequate (+1)
- Hard Rules: ✅ Lab Required + Projector Required (+8 total)
- Preferences: ✅ AC Characteristic (+2)
- Historical: 📈 3x allocated (+3)
= 12 total points
```

## Implementation Details

### Data Structures

#### ScoringBreakdown Dataclass
```python
@dataclass
class ScoringBreakdown:
    total_score: int
    capacity_points: int
    hard_rules_points: int
    soft_preference_points: int
    historical_frequency_points: int

    # Details for UI
    capacity_satisfied: bool
    hard_rules_satisfied: List[str]  # Names of satisfied rules
    soft_preferences_satisfied: List[str]  # Satisfied preference descriptions
    historical_allocations: int  # Count of previous allocations
```

### UI Transparency Features

#### Detailed Breakdown Display
The UI shows each scoring component with full transparency:

```
🟢 Pontuação: 12
▼ 📊 Detalhes da Pontuação

Capacidade:
✅ Adequada (+1)

Regras Obrigatórias:
✅ Atendidas (+8): Tipo de sala: Laboratório; Característica: Projetor
• "Tipo de sala: Laboratório"
• "Característica: Projetor"

Preferências Professor:
✅ Atendidas (+2): Característica preferida: Ar Condicionado
• "Característica preferida: Ar Condicionado"

Frequência Histórica:
📈 Alocada 3x aqui (+3)

────────────────────────────
**Total: 12 pontos**
```

#### Scoring Flow Logic
1. **Capacity Check**: Basic room size validation
2. **Hard Rules**: High-priority constraints (must all pass)
3. **Soft Preferences**: Professor preferences (only if hard rules pass)
4. **Historical Bonus**: Frequency-based scoring
5. **Semester Conflict**: Final conflict check within current semester only

### semesters-isolated Conflict Detection

- **Architecture**: RF-006.2 - Semester scope isolation
- **Implementation**: Only checks conflicts within the specified semester
- **Performance**: Prevents cross-semester interference
- **Accuracy**: Ensures current semester scheduling integrity

## Usage Examples

### Basic Scoring Example
```python
# Get scored candidates
candidates = scoring_service.score_room_candidates_for_demand(
    demanda_id=123,
    semester_id=4  # Current semester
)

# Each candidate has:
# - candidate.score (total points)
# - candidate.scoring_breakdown (detailed breakdown)
```

### Manual Allocation Integration
The ManualAllocationService integrates detailed scoring:

```python
suggestions = alloc_service.get_suggestions_for_demand(demanda_id, semester_id)
# Each suggestion.room_suggestion includes scoring_breakdown dict
```

## Performance Characteristics

### Key Metrics
- **Consistency**: 100% consistent between autonomous and manual allocation
- **Transparency**: Full scoring breakdown available in UI
- **Extensibility**: Easy to add new scoring rules
- **Semester Isolation**: No cross-semester interference

### Scalability
- Single scoring service reduces code duplication
- Shared logic ensures maintenance efficiency
- Modular design supports future enhancements

## Architecture Decisions

### Single Source of Truth
- **RoomScoringService**: Centralized scoring logic
- **Prevents divergence**: Manual vs autonomous allocation always use same algorithm
- **Maintenance**: Changes in one place affect entire system

### Semester Boundary Isolation
- **RF-006.2**: Semester-scoped conflict detection
- **Accuracy**: Prevents conflicts with wrong semester
- **Performance**: Simpler queries, better indexing

### UI Transparency
- **Detailed Breakdown**: Shows exactly how each point earned
- **User Confidence**: Builds trust in algorithm recommendations
- **Educational**: Helps users understand scoring logic

## Future Extensions

### Potential Scoring Enhancements
1. **Time-of-Day Preferences**: Professor preferred times
2. **Building Proximity**: Distance-based preferences
3. **Equipment Availability**: Booking conflicts for equipment
4. **Student Accessibility**: Handicap-accessible preferences

### Algorithm Improvements
- Dynamic preference learning
- Time-based weight adjustments
- Multi-objective optimization

## References

- **RF-006**: Autonomous Allocation Algorithm specification
- **RF-006.6**: Historical frequency bonus requirement
- **RoomScoringService**: Implementation in `src/services/room_scoring_service.py`
- **ManualAllocationService**: Integration in `src/services/manual_allocation_service.py`
