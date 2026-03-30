from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
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


def task_time_sort_key(task: "Task") -> tuple[int, str]:
    """Build a deterministic key for ordering tasks by preferred time then title.

    Tasks without a preferred time window are placed after timed tasks by using
    a sentinel hour value of 24.
    """
    if task.preferred_window is None:
        return (24, task.title.lower())
    return (task.preferred_window.start_hour, task.title.lower())


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
    time: Optional[str] = None
    due_date: Optional[date] = None
    frequency: Optional[str] = None
    preferred_window: Optional[TimeWindow] = None
    required: bool = False
    task_id: UUID = field(default_factory=uuid4)

    def validate(self) -> bool:
        """Validate task fields and optional preferred time window bounds."""
        if self.duration_minutes < 0:
            return False
        if self.priority < 0 or self.importance < 0:
            return False
        if self.frequency is not None and self.frequency.lower() not in {"daily", "weekly"}:
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

    def mark_complete(self, completed_on: Optional[date] = None) -> Optional["Task"]:
        """Complete this task and optionally generate the next recurring instance.

        For daily and weekly tasks, this returns a new pending Task with an
        incremented due date. Non-recurring tasks return None.
        """
        self.status = "completed"

        if self.frequency is None:
            return None

        normalized_frequency = self.frequency.lower()
        if normalized_frequency not in {"daily", "weekly"}:
            return None

        if completed_on is None:
            completed_on = date.today()

        day_delta = 1 if normalized_frequency == "daily" else 7
        next_due_date = completed_on + timedelta(days=day_delta)

        return Task(
            title=self.title,
            task_type=self.task_type,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            importance=self.importance,
            status="pending",
            time=self.time,
            due_date=next_due_date,
            frequency=self.frequency,
            preferred_window=self.preferred_window,
            required=self.required,
        )


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

    def mark_task_complete(self, task_id: UUID, completed_on: Optional[date] = None) -> Optional[Task]:
        """Complete a task by id and append the next recurring instance when applicable."""
        for task in self.tasks:
            if task.task_id == task_id:
                next_task = task.mark_complete(completed_on=completed_on)
                if next_task is not None:
                    self.add_task(next_task)
                return next_task
        return None


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

    def sort_by_time(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks by preferred time window start hour, then title.

        Tasks without a preferred time window are placed last.
        """
        return sorted(tasks, key=task_time_sort_key)

    def has_time_conflicts(self, tasks: List[Task]) -> bool:
        """Return True when two or more tasks share the same preferred start hour.

        Untimed tasks are ignored for conflict checks because they do not have a
        fixed scheduled slot.
        """
        seen_start_hours: set[int] = set()
        for task in tasks:
            if task.preferred_window is None:
                continue
            start_hour = task.preferred_window.start_hour
            if start_hour in seen_start_hours:
                return True
            seen_start_hours.add(start_hour)
        return False

    def filter_tasks_by_status(self, owner: Owner, status: str) -> List[Task]:
        """Return all tasks across an owner's pets with a case-insensitive status match."""
        normalized_status = status.strip().lower()
        return [
            task
            for pet in owner.pets
            for task in pet.get_tasks()
            if task.status.lower() == normalized_status
        ]

    def filter_tasks(
        self,
        owner: Owner,
        status: Optional[str] = None,
        pet_name: Optional[str] = None,
    ) -> List[Task]:
        """Filter owner tasks by optional status and pet-name constraints.

        When only status is provided, this delegates to filter_tasks_by_status
        to keep comparison behavior consistent.
        """
        filtered: List[Task] = []
        normalized_pet_name = pet_name.lower().strip() if pet_name else None

        if status is not None and normalized_pet_name is None:
            return self.filter_tasks_by_status(owner=owner, status=status)

        for pet in owner.pets:
            if normalized_pet_name and pet.name.lower() != normalized_pet_name:
                continue
            for task in pet.get_tasks():
                if status is not None and task.status != status:
                    continue
                filtered.append(task)

        return filtered

    def mark_task_complete(self, pet: Pet, task_id: UUID, completed_on: Optional[date] = None) -> Optional[Task]:
        """Complete a pet task and trigger recurrence rollover when configured."""
        return pet.mark_task_complete(task_id=task_id, completed_on=completed_on)
