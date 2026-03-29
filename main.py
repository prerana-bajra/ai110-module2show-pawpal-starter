from datetime import date

from pawpal_system import Owner, Pet, Task, TaskType, TimeWindow


def format_window(window: TimeWindow | None) -> str:
    if window is None:
        return "Any time"
    return f"{window.start_hour:02d}:00-{window.end_hour:02d}:00"


def sort_key(task: Task) -> tuple[int, str]:
    if task.preferred_window is None:
        return (24, task.title)
    return (task.preferred_window.start_hour, task.title)


def print_todays_schedule(owner: Owner) -> None:
    print(f"Today's Schedule ({date.today().isoformat()})")
    print(f"Owner: {owner.name}")
    print("=" * 48)

    for pet in owner.pets:
        print(f"\n{pet.name} ({pet.species})")
        print("-" * 48)
        tasks = sorted(pet.get_tasks(), key=sort_key)
        if not tasks:
            print("  No tasks yet.")
            continue

        for task in tasks:
            time_text = format_window(task.preferred_window)
            print(
                f"  {time_text:<13} | {task.title:<18} "
                f"| {task.task_type.value:<10} | {task.duration_minutes:>3} min"
            )


if __name__ == "__main__":
    owner = Owner(name="Maya", daily_available_minutes=180)

    luna = Pet(name="Luna", species="Dog", age_years=3, weight_kg=18.5)
    milo = Pet(name="Milo", species="Cat", age_years=6, weight_kg=5.2)

    luna.add_task(
        Task(
            title="Morning Walk",
            task_type=TaskType.WALK,
            duration_minutes=30,
            priority=6,
            importance=7,
            preferred_window=TimeWindow(start_hour=7, end_hour=9),
        )
    )
    luna.add_task(
        Task(
            title="Breakfast",
            task_type=TaskType.FEEDING,
            duration_minutes=10,
            priority=9,
            importance=9,
            preferred_window=TimeWindow(start_hour=8, end_hour=10),
            required=True,
        )
    )

    milo.add_task(
        Task(
            title="Medication",
            task_type=TaskType.MEDICATION,
            duration_minutes=5,
            priority=10,
            importance=10,
            preferred_window=TimeWindow(start_hour=9, end_hour=11),
            required=True,
        )
    )
    milo.add_task(
        Task(
            title="Evening Play",
            task_type=TaskType.ENRICHMENT,
            duration_minutes=20,
            priority=4,
            importance=5,
            preferred_window=TimeWindow(start_hour=18, end_hour=20),
        )
    )

    owner.add_pet(luna)
    owner.add_pet(milo)

    print_todays_schedule(owner)
