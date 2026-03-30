from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task, TaskType, TimeWindow


def format_window(window: TimeWindow | None) -> str:
    if window is None:
        return "Any time"
    return f"{window.start_hour:02d}:00-{window.end_hour:02d}:00"


def format_task_time(task: Task) -> str:
    if task.time:
        return task.time
    return format_window(task.preferred_window)


def print_todays_schedule(owner: Owner, scheduler: Scheduler) -> None:
    print(f"Today's Schedule ({date.today().isoformat()})")
    print(f"Owner: {owner.name}")
    print("=" * 48)

    for pet in owner.pets:
        print(f"\n{pet.name} ({pet.species})")
        print("-" * 48)
        tasks = scheduler.sort_by_time(pet.get_tasks())
        if not tasks:
            print("  No tasks yet.")
            continue

        for task in tasks:
            time_text = format_task_time(task)
            print(
                f"  {time_text:<13} | {task.title:<18} "
                f"| {task.task_type.value:<10} | {task.duration_minutes:>3} min"
            )


def print_filtered_tasks(owner: Owner, scheduler: Scheduler, status: str | None, pet_name: str | None) -> None:
    filtered = scheduler.filter_tasks(owner=owner, status=status, pet_name=pet_name)
    status_label = status if status is not None else "any"
    pet_label = pet_name if pet_name is not None else "all pets"

    print("\n" + "=" * 48)
    print(f"Filtered Tasks (status={status_label}, pet={pet_label})")
    print("=" * 48)

    if not filtered:
        print("  No matching tasks.")
        return

    for task in scheduler.sort_by_time(filtered):
        print(f"  {format_task_time(task):<13} | {task.title:<18} | {task.status}")


if __name__ == "__main__":
    scheduler = Scheduler()
    owner = Owner(name="Maya", daily_available_minutes=180)

    luna = Pet(name="Luna", species="Dog", age_years=3, weight_kg=18.5)
    milo = Pet(name="Milo", species="Cat", age_years=6, weight_kg=5.2)

    luna.add_task(
        Task(
            title="Evening Walk",
            task_type=TaskType.WALK,
            duration_minutes=30,
            priority=6,
            importance=7,
            time="18:30",
            status="pending",
            preferred_window=TimeWindow(start_hour=18, end_hour=20),
        )
    )
    luna.add_task(
        Task(
            title="Breakfast",
            task_type=TaskType.FEEDING,
            duration_minutes=10,
            priority=9,
            importance=9,
            time="07:30",
            due_date=date.today(),
            frequency="daily",
            status="pending",
            preferred_window=TimeWindow(start_hour=8, end_hour=10),
            required=True,
        )
    )
    luna.add_task(
        Task(
            title="Midday Check-in",
            task_type=TaskType.OTHER,
            duration_minutes=10,
            priority=4,
            importance=5,
            time="12:00",
            status="pending",
        )
    )

    milo.add_task(
        Task(
            title="Medication",
            task_type=TaskType.MEDICATION,
            duration_minutes=5,
            priority=10,
            importance=10,
            time="09:15",
            status="pending",
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
            time="19:00",
            status="completed",
            preferred_window=TimeWindow(start_hour=18, end_hour=20),
        )
    )

    owner.add_pet(luna)
    owner.add_pet(milo)

    breakfast_task = next(task for task in luna.get_tasks() if task.title == "Breakfast")
    next_breakfast = scheduler.mark_task_complete(
        pet=luna,
        task_id=breakfast_task.task_id,
        completed_on=date.today(),
    )

    print_todays_schedule(owner, scheduler)
    print_filtered_tasks(owner, scheduler, status="pending", pet_name="Luna")
    print_filtered_tasks(owner, scheduler, status="completed", pet_name=None)

    print("\n" + "=" * 48)
    print("Recurring Task Demo")
    print("=" * 48)
    if next_breakfast is not None:
        print(
            "  Created next occurrence: "
            f"{next_breakfast.title} due {next_breakfast.due_date.isoformat()} "
            f"({next_breakfast.frequency})"
        )
