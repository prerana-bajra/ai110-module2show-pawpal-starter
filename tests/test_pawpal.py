from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pawpal_system import Pet, Task, TaskType


def make_task(title: str = "Sample Task") -> Task:
    return Task(
        title=title,
        task_type=TaskType.FEEDING,
        duration_minutes=10,
        priority=5,
        importance=5,
    )


def test_task_completion_changes_status() -> None:
    task = make_task("Morning Medication")
    task.status = "pending"

    task.mark_complete()

    assert task.status == "completed"


def test_adding_task_increases_pet_task_count() -> None:
    pet = Pet(name="Luna", species="Dog", age_years=3, weight_kg=18.5)
    initial_count = len(pet.get_tasks())

    pet.add_task(make_task("Breakfast"))

    assert len(pet.get_tasks()) == initial_count + 1
