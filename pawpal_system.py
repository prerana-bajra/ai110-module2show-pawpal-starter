from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4


class TaskType(str, Enum):
    FEEDING = "FEEDING"
    MEDICATION = "MEDICATION"
    WALK = "WALK"
    ENRICHMENT = "ENRICHMENT"
    GROOMING = "GROOMING"
    TRAINING = "TRAINING"
    OTHER = "OTHER"


@dataclass
class TimeWindow:
    start_hour: int
    end_hour: int

    def contains(self, hour: int) -> bool:
        """Return whether the given hour falls within this time window."""
        return self.start_hour <= hour < self.end_hour


@dataclass
class Task:
    title: str
    task_type: TaskType
    duration_minutes: int
    priority: int
    importance: int
    status: str = "pending"
    preferred_window: Optional[TimeWindow] = None
    required: bool = False
    task_id: UUID = field(default_factory=uuid4)

    def validate(self) -> bool:
        """Validate task fields and optional preferred time window bounds."""
        if self.duration_minutes < 0:
            return False
        if self.priority < 0 or self.importance < 0:
            return False
        if self.preferred_window and self.preferred_window.end_hour <= self.preferred_window.start_hour:
            return False
        return True

    def score(self, now_slot: int) -> float:
        """Compute a priority-importance score adjusted for time preference fit."""
        base_score = float(self.priority * self.importance)
        if not self.preferred_window:
            return base_score

        if self.preferred_window.contains(now_slot):
            return base_score

        return base_score - 1.0

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.status = "completed"


@dataclass
class Pet:
    name: str
    species: str
    age_years: int
    weight_kg: float
    pet_id: UUID = field(default_factory=uuid4)
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, task_id: UUID) -> None:
        """Remove a task from this pet by its task identifier."""
        self.tasks = [task for task in self.tasks if task.task_id != task_id]

    def get_tasks(self) -> List[Task]:
        """Return a shallow copy of this pet's tasks."""
        return list(self.tasks)


@dataclass
class Owner:
    name: str
    daily_available_minutes: int
    preferences: Dict[str, str] = field(default_factory=dict)
    owner_id: UUID = field(default_factory=uuid4)
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's list of pets."""
        self.pets.append(pet)

    def update_preferences(self, prefs: Dict[str, str]) -> None:
        """Merge provided preferences into the owner's preferences."""
        self.preferences.update(prefs)


@dataclass
class ScheduleItem:
    task: Task
    start_minute: int
    end_minute: int
    explanation: str = ""
    schedule_item_id: UUID = field(default_factory=uuid4)


@dataclass
class DailyPlan:
    plan_date: date
    items: List[ScheduleItem] = field(default_factory=list)

    @property
    def total_minutes(self) -> int:
        """Return total planned minutes across all schedule items."""
        return sum(item.end_minute - item.start_minute for item in self.items)

    def is_overbooked(self) -> bool:
        """Return whether planned time exceeds a full 24-hour day."""
        return self.total_minutes > 24 * 60

    def to_structured_list(self) -> List[str]:
        """Serialize plan items into compact human-readable time strings."""
        structured = []
        for item in self.items:
            structured.append(
                f"{item.start_minute:04d}-{item.end_minute:04d}: "
                f"{item.task.title} ({item.task.task_type.value})"
            )
        return structured


class Scheduler:
    def __init__(self, time_penalty_weight: float = 1.0) -> None:
        """Initialize scheduler configuration values."""
        self.time_penalty_weight = time_penalty_weight

    def build_plan(self, owner: Owner, pet: Pet, plan_date: date) -> DailyPlan:
        """Build and return a daily plan for the given owner and pet."""
        raise NotImplementedError

    def rank_tasks(self, tasks: List[Task], current_minute: int) -> List[Task]:
        """Rank tasks by desirability at the given minute of the day."""
        raise NotImplementedError

    def compute_score(self, task: Task, current_minute: int) -> float:
        """Compute a scheduler-specific score for a task at a time point."""
        raise NotImplementedError

    def fits_in_day(self, plan: DailyPlan, task: Task) -> bool:
        """Return whether adding the task keeps the plan within day limits."""
        raise NotImplementedError

    def generate_explanation(self, task: Task, score: float) -> str:
        """Generate a short rationale string for a task selection score."""
        raise NotImplementedError

    def validate_inputs(self, owner: Owner, tasks: List[Task]) -> None:
        """Validate owner and task inputs before scheduling begins."""
        raise NotImplementedError
