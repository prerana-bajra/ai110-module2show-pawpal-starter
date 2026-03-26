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
        return self.start_hour <= hour < self.end_hour


@dataclass
class Task:
    title: str
    task_type: TaskType
    duration_minutes: int
    priority: int
    importance: int
    preferred_window: Optional[TimeWindow] = None
    required: bool = False
    task_id: UUID = field(default_factory=uuid4)

    def validate(self) -> bool:
        if self.duration_minutes < 0:
            return False
        if self.priority < 0 or self.importance < 0:
            return False
        if self.preferred_window and self.preferred_window.end_hour <= self.preferred_window.start_hour:
            return False
        return True

    def score(self, now_slot: int) -> float:
        base_score = float(self.priority * self.importance)
        if not self.preferred_window:
            return base_score

        if self.preferred_window.contains(now_slot):
            return base_score

        return base_score - 1.0


@dataclass
class Pet:
    name: str
    species: str
    age_years: int
    weight_kg: float
    pet_id: UUID = field(default_factory=uuid4)
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)

    def remove_task(self, task_id: UUID) -> None:
        self.tasks = [task for task in self.tasks if task.task_id != task_id]

    def get_tasks(self) -> List[Task]:
        return list(self.tasks)


@dataclass
class Owner:
    name: str
    daily_available_minutes: int
    preferences: Dict[str, str] = field(default_factory=dict)
    owner_id: UUID = field(default_factory=uuid4)
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        self.pets.append(pet)

    def update_preferences(self, prefs: Dict[str, str]) -> None:
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
        return sum(item.end_minute - item.start_minute for item in self.items)

    def is_overbooked(self) -> bool:
        return self.total_minutes > 24 * 60

    def to_structured_list(self) -> List[str]:
        structured = []
        for item in self.items:
            structured.append(
                f"{item.start_minute:04d}-{item.end_minute:04d}: "
                f"{item.task.title} ({item.task.task_type.value})"
            )
        return structured


class Scheduler:
    def __init__(self, time_penalty_weight: float = 1.0) -> None:
        self.time_penalty_weight = time_penalty_weight

    def build_plan(self, owner: Owner, pet: Pet, plan_date: date) -> DailyPlan:
        raise NotImplementedError

    def rank_tasks(self, tasks: List[Task], current_minute: int) -> List[Task]:
        raise NotImplementedError

    def compute_score(self, task: Task, current_minute: int) -> float:
        raise NotImplementedError

    def fits_in_day(self, plan: DailyPlan, task: Task) -> bool:
        raise NotImplementedError

    def generate_explanation(self, task: Task, score: float) -> str:
        raise NotImplementedError

    def validate_inputs(self, owner: Owner, tasks: List[Task]) -> None:
        raise NotImplementedError
