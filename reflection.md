# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.

    - My initial UML design centered on `Owner`, `Pet`, `Task`, and `Scheduler` as the core classes. `Owner` and `Pet` capture profile and availability context, while each `Task` stores duration, priority, importance, and optional time-window constraints. The `Scheduler` ranks tasks using a weighted score and produces a `DailyPlan` made of `ScheduleItem`s, including brief explanations for why higher-priority care actions were scheduled first.

```mermaid
classDiagram
direction LR

class Owner {
  +UUID owner_id
  +string name
  +int daily_available_minutes
  +map<string,string> preferences
  +add_pet(pet: Pet) void
  +update_preferences(prefs: map<string,string>) void
}

class Pet {
  +UUID pet_id
  +string name
  +string species
  +int age_years
  +float weight_kg
  +add_task(task: Task) void
  +remove_task(task_id: UUID) void
  +get_tasks() List~Task~
}

class Task {
  +UUID task_id
  +string title
  +TaskType task_type
  +int duration_minutes
  +int priority
  +int importance
  +TimeWindow preferred_window
  +bool required
  +validate() bool
  +score(now_slot: int) float
}

class TimeWindow {
  +int start_hour
  +int end_hour
  +contains(hour: int) bool
}

class ScheduleItem {
  +UUID schedule_item_id
  +Task task
  +int start_minute
  +int end_minute
  +string explanation
}

class DailyPlan {
  +date plan_date
  +List~ScheduleItem~ items
  +int total_minutes
  +is_overbooked() bool
  +to_structured_list() List~string~
}

class Scheduler {
  +float time_penalty_weight
  +build_plan(owner: Owner, pet: Pet, date: date) DailyPlan
  +rank_tasks(tasks: List~Task~, current_minute: int) List~Task~
  +compute_score(task: Task, current_minute: int) float
  +fits_in_day(plan: DailyPlan, task: Task) bool
  +generate_explanation(task: Task, score: float) string
  +validate_inputs(owner: Owner, tasks: List~Task~) void
}

class TaskType {
  <<enumeration>>
  FEEDING
  MEDICATION
  WALK
  ENRICHMENT
  GROOMING
  TRAINING
  OTHER
}

Owner "1" --> "0..*" Pet : owns
Pet "1" --> "0..*" Task : has
Task "1" --> "1" TimeWindow : preferred_in
DailyPlan "1" --> "0..*" ScheduleItem : contains
ScheduleItem "1" --> "1" Task : scheduled_for
Scheduler ..> Owner : reads constraints
Scheduler ..> Pet : reads tasks
Scheduler ..> Task : scores and orders
Scheduler ..> DailyPlan : produces

note for Scheduler "Scoring: 
Score = priority * importance - time_penalty 
Safety rule: MEDICATION and FEEDING outrank ENRICHMENT
Validation: reject negative duration and impossible time windows"

```


- What classes did you include, and what responsibilities did you assign to each?
    - I included these classes and responsibilities:

        **Owner**: Stores owner profile, daily time availability, and care preferences; serves as the top-level context for planning.

        **Pet**: Stores pet details and owns the list of care tasks that need scheduling.

        **Task**: Represents one care activity (feeding, meds, walk, etc.) with duration, priority, importance, and preferred time window.

        **TimeWindow**: Encapsulates allowed time ranges for a task and validates whether a slot is acceptable.
        
        **Scheduler**: Core planning engine; validates inputs, scores/ranks tasks, applies safety rules, and builds the daily schedule.

        **DailyPlan**: Holds the final day-level output (all scheduled items) and checks if the plan is overbooked.
        
        **ScheduleItem**: One scheduled task instance with start/end times plus a short explanation of why it was placed there.

        **TaskType** (enum): Standardizes task categories so safety/priority rules can be applied consistently.  

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
