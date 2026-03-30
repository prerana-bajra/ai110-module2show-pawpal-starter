from pathlib import Path
import sys
from datetime import date

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pawpal_system import Owner, Pet, Scheduler, Task, TaskType, TimeWindow, task_time_sort_key


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


def test_tasks_sort_by_preferred_start_time() -> None:
    tasks = [
        Task(
            title="Anytime Task",
            task_type=TaskType.OTHER,
            duration_minutes=10,
            priority=1,
            importance=1,
        ),
        Task(
            title="Evening Walk",
            task_type=TaskType.WALK,
            duration_minutes=20,
            priority=5,
            importance=6,
            preferred_window=TimeWindow(start_hour=18, end_hour=20),
        ),
        Task(
            title="Morning Feeding",
            task_type=TaskType.FEEDING,
            duration_minutes=10,
            priority=7,
            importance=8,
            preferred_window=TimeWindow(start_hour=7, end_hour=9),
        ),
    ]

    sorted_titles = [task.title for task in sorted(tasks, key=task_time_sort_key)]

    assert sorted_titles == ["Morning Feeding", "Evening Walk", "Anytime Task"]


def test_scheduler_sort_by_time_uses_preferred_windows() -> None:
    scheduler = Scheduler()
    tasks = [
        Task(
            title="Anytime",
            task_type=TaskType.FEEDING,
            duration_minutes=10,
            priority=1,
            importance=1,
        ),
        Task(
            title="Evening Walk",
            task_type=TaskType.FEEDING,
            duration_minutes=10,
            priority=1,
            importance=1,
            preferred_window=TimeWindow(start_hour=18, end_hour=20),
        ),
        Task(
            title="Morning Feed",
            task_type=TaskType.WALK,
            duration_minutes=20,
            priority=1,
            importance=1,
            preferred_window=TimeWindow(start_hour=7, end_hour=9),
        ),
    ]

    sorted_titles = [task.title for task in scheduler.sort_by_time(tasks)]

    assert sorted_titles == ["Morning Feed", "Evening Walk", "Anytime"]


def test_scheduler_filter_tasks_by_status_and_pet_name() -> None:
    scheduler = Scheduler()
    owner = Owner(name="Maya", daily_available_minutes=180)
    luna = Pet(name="Luna", species="Dog", age_years=3, weight_kg=18.5)
    milo = Pet(name="Milo", species="Cat", age_years=6, weight_kg=5.2)
    owner.add_pet(luna)
    owner.add_pet(milo)

    luna.add_task(
        Task(
            title="Luna meds",
            task_type=TaskType.MEDICATION,
            duration_minutes=5,
            priority=10,
            importance=10,
            status="pending",
        )
    )
    luna.add_task(
        Task(
            title="Luna play",
            task_type=TaskType.ENRICHMENT,
            duration_minutes=15,
            priority=3,
            importance=3,
            status="completed",
        )
    )
    milo.add_task(
        Task(
            title="Milo feeding",
            task_type=TaskType.FEEDING,
            duration_minutes=10,
            priority=8,
            importance=8,
            status="pending",
        )
    )

    filtered = scheduler.filter_tasks(owner=owner, status="pending", pet_name="Luna")

    assert len(filtered) == 1
    assert filtered[0].title == "Luna meds"


def test_scheduler_filter_tasks_by_status_case_insensitive() -> None:
    scheduler = Scheduler()
    owner = Owner(name="Maya", daily_available_minutes=180)
    luna = Pet(name="Luna", species="Dog", age_years=3, weight_kg=18.5)
    owner.add_pet(luna)

    luna.add_task(
        Task(
            title="Morning meds",
            task_type=TaskType.MEDICATION,
            duration_minutes=5,
            priority=10,
            importance=10,
            status="completed",
        )
    )
    luna.add_task(
        Task(
            title="Evening walk",
            task_type=TaskType.WALK,
            duration_minutes=20,
            priority=6,
            importance=7,
            status="pending",
        )
    )

    filtered = scheduler.filter_tasks_by_status(owner=owner, status="Completed")

    assert len(filtered) == 1
    assert filtered[0].title == "Morning meds"


def test_mark_complete_daily_creates_next_occurrence() -> None:
    task = Task(
        title="Breakfast",
        task_type=TaskType.FEEDING,
        duration_minutes=10,
        priority=8,
        importance=8,
        frequency="daily",
        due_date=date(2026, 3, 29),
    )

    next_task = task.mark_complete(completed_on=date(2026, 3, 29))

    assert task.status == "completed"
    assert next_task is not None
    assert next_task.status == "pending"
    assert next_task.due_date == date(2026, 3, 30)
    assert next_task.frequency == "daily"


def test_scheduler_mark_task_complete_weekly_creates_new_instance() -> None:
    scheduler = Scheduler()
    pet = Pet(name="Luna", species="Dog", age_years=3, weight_kg=18.5)
    recurring = Task(
        title="Weekly Grooming",
        task_type=TaskType.GROOMING,
        duration_minutes=30,
        priority=6,
        importance=7,
        frequency="weekly",
        due_date=date(2026, 3, 29),
    )
    pet.add_task(recurring)

    next_task = scheduler.mark_task_complete(
        pet=pet,
        task_id=recurring.task_id,
        completed_on=date(2026, 3, 29),
    )

    assert recurring.status == "completed"
    assert next_task is not None
    assert next_task.due_date == date(2026, 4, 5)
    assert next_task.frequency == "weekly"
    assert len(pet.get_tasks()) == 2


def test_sort_by_time_handles_empty_task_list() -> None:
    scheduler = Scheduler()

    assert scheduler.sort_by_time([]) == []


def test_sort_by_time_tie_breaks_by_title_for_same_start_hour() -> None:
    scheduler = Scheduler()
    tasks = [
        Task(
            title="Bravo Walk",
            task_type=TaskType.WALK,
            duration_minutes=20,
            priority=3,
            importance=3,
            preferred_window=TimeWindow(start_hour=8, end_hour=9),
        ),
        Task(
            title="Alpha Feed",
            task_type=TaskType.FEEDING,
            duration_minutes=10,
            priority=5,
            importance=6,
            preferred_window=TimeWindow(start_hour=8, end_hour=10),
        ),
    ]

    sorted_titles = [task.title for task in scheduler.sort_by_time(tasks)]

    assert sorted_titles == ["Alpha Feed", "Bravo Walk"]


def test_scheduler_detects_duplicate_preferred_start_times() -> None:
    scheduler = Scheduler()
    tasks = [
        Task(
            title="Morning Feed",
            task_type=TaskType.FEEDING,
            duration_minutes=10,
            priority=8,
            importance=8,
            preferred_window=TimeWindow(start_hour=7, end_hour=8),
        ),
        Task(
            title="Morning Meds",
            task_type=TaskType.MEDICATION,
            duration_minutes=5,
            priority=10,
            importance=10,
            preferred_window=TimeWindow(start_hour=7, end_hour=9),
        ),
    ]

    assert scheduler.has_time_conflicts(tasks) is True


def test_scheduler_no_conflicts_when_preferred_start_times_are_unique() -> None:
    scheduler = Scheduler()
    tasks = [
        Task(
            title="Morning Feed",
            task_type=TaskType.FEEDING,
            duration_minutes=10,
            priority=8,
            importance=8,
            preferred_window=TimeWindow(start_hour=7, end_hour=8),
        ),
        Task(
            title="Evening Walk",
            task_type=TaskType.WALK,
            duration_minutes=20,
            priority=6,
            importance=6,
            preferred_window=TimeWindow(start_hour=18, end_hour=20),
        ),
    ]

    assert scheduler.has_time_conflicts(tasks) is False
