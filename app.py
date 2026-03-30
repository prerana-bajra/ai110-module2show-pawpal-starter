from __future__ import annotations

from datetime import date
from typing import List

import streamlit as st

import pawpal_system as pawpal


class SimpleScheduler(pawpal.Scheduler):
    def __init__(self, time_penalty_weight: float = 1.0) -> None:
        super().__init__(time_penalty_weight=time_penalty_weight)
        self._available_minutes = 24 * 60

    def build_plan(self, owner: pawpal.Owner, pet: pawpal.Pet, plan_date: date) -> pawpal.DailyPlan:
        tasks = [task for task in pet.get_tasks() if task.status != "completed"]
        self.validate_inputs(owner, tasks)
        self._available_minutes = owner.daily_available_minutes

        plan = pawpal.DailyPlan(plan_date=plan_date)
        current_minute = 8 * 60

        for task in self.rank_tasks(tasks, current_minute):
            if not self.fits_in_day(plan, task):
                continue

            score = self.compute_score(task, current_minute)
            start_minute = current_minute
            end_minute = start_minute + task.duration_minutes
            plan.items.append(
                pawpal.ScheduleItem(
                    task=task,
                    start_minute=start_minute,
                    end_minute=end_minute,
                    explanation=self.generate_explanation(task, score),
                )
            )
            current_minute = end_minute

        return plan

    def rank_tasks(self, tasks: List[pawpal.Task], current_minute: int) -> List[pawpal.Task]:
        return sorted(
            tasks,
            key=lambda task: (
                not task.required,
                pawpal.task_time_sort_key(task),
                -self.compute_score(task, current_minute),
                -task.duration_minutes,
            ),
        )

    def compute_score(self, task: pawpal.Task, current_minute: int) -> float:
        current_hour = current_minute // 60
        score = task.score(current_hour)

        if task.required:
            score += 10.0

        if task.preferred_window and not task.preferred_window.contains(current_hour):
            score -= self.time_penalty_weight

        return score

    def fits_in_day(self, plan: pawpal.DailyPlan, task: pawpal.Task) -> bool:
        return plan.total_minutes + task.duration_minutes <= self._available_minutes

    def generate_explanation(self, task: pawpal.Task, score: float) -> str:
        window_note = "with no specific time window"
        if task.preferred_window:
            window_note = (
                f"targeting {task.preferred_window.start_hour:02d}:00-"
                f"{task.preferred_window.end_hour:02d}:00"
            )
        return (
            f"Scheduled because it scored {score:.1f} from priority {task.priority} and "
            f"importance {task.importance}, {window_note}."
        )

    def validate_inputs(self, owner: pawpal.Owner, tasks: List[pawpal.Task]) -> None:
        if owner.daily_available_minutes <= 0:
            raise ValueError("Owner daily available minutes must be positive.")
        for task in tasks:
            if not task.validate():
                raise ValueError(f"Invalid task detected: {task.title}")


def format_minutes(total_minutes: int) -> str:
    hour = total_minutes // 60
    minute = total_minutes % 60
    return f"{hour:02d}:{minute:02d}"


st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

def owner_label(owner: pawpal.Owner) -> str:
    return f"{owner.name} ({owner.daily_available_minutes} min/day)"


def pet_label(pet: pawpal.Pet) -> str:
    return f"{pet.name} ({pet.species})"


def get_pet_by_id(owner: pawpal.Owner, pet_id: str | None) -> pawpal.Pet | None:
    if pet_id is None:
        return owner.pets[0] if owner.pets else None
    for pet in owner.pets:
        if str(pet.pet_id) == pet_id:
            return pet
    return owner.pets[0] if owner.pets else None


if "owners" not in st.session_state:
    default_owner = pawpal.Owner(name="Jordan", daily_available_minutes=120)
    default_pet = pawpal.Pet(name="Mochi", species="dog", age_years=2, weight_kg=8.0)
    default_owner.add_pet(default_pet)

    st.session_state.owners = {str(default_owner.owner_id): default_owner}
    st.session_state.active_owner_id = str(default_owner.owner_id)
    st.session_state.active_pet_id = str(default_pet.pet_id)
if "plans" not in st.session_state:
    st.session_state.plans = {}

st.title("🐾 PawPal+")
st.caption("A pet care planning assistant with prioritization and schedule explanations.")

owner_ids: List[str] = list(st.session_state.owners.keys())
if not owner_ids:
    st.error("No owners available in this session.")
    st.stop()

if st.session_state.active_owner_id not in st.session_state.owners:
    st.session_state.active_owner_id = owner_ids[0]

with st.expander("Owner & Pet Manager", expanded=True):
    selected_owner_id = st.selectbox(
        "Select owner",
        options=owner_ids,
        index=owner_ids.index(st.session_state.active_owner_id),
        format_func=lambda owner_id: owner_label(st.session_state.owners[owner_id]),
    )

    if selected_owner_id != st.session_state.active_owner_id:
        st.session_state.active_owner_id = selected_owner_id
        st.session_state.active_pet_id = None

    active_owner: pawpal.Owner = st.session_state.owners[st.session_state.active_owner_id]

    new_owner_col1, new_owner_col2, new_owner_col3 = st.columns(3)
    with new_owner_col1:
        new_owner_name = st.text_input("New owner name", value="", key="new_owner_name")
    with new_owner_col2:
        new_owner_minutes = st.number_input(
            "New owner minutes/day",
            min_value=15,
            max_value=24 * 60,
            value=120,
            step=15,
            key="new_owner_minutes",
        )
    with new_owner_col3:
        st.write("")
        st.write("")
        if st.button("Add owner", use_container_width=True):
            owner_name_clean = new_owner_name.strip() or f"Owner {len(st.session_state.owners) + 1}"
            created_owner = pawpal.Owner(
                name=owner_name_clean,
                daily_available_minutes=int(new_owner_minutes),
            )
            st.session_state.owners[str(created_owner.owner_id)] = created_owner
            st.session_state.active_owner_id = str(created_owner.owner_id)
            st.session_state.active_pet_id = None
            st.success(f"Added owner: {created_owner.name}")
            st.rerun()

    st.markdown("### Edit Selected Owner")
    col1, col2 = st.columns(2)
    with col1:
        owner_name = st.text_input("Owner name", value=active_owner.name)
        daily_minutes = st.number_input(
            "Daily available minutes",
            min_value=15,
            max_value=24 * 60,
            value=int(active_owner.daily_available_minutes),
            step=15,
            key="active_owner_minutes",
        )

    pet_options = [str(pet.pet_id) for pet in active_owner.pets]
    if pet_options:
        if st.session_state.active_pet_id not in pet_options:
            st.session_state.active_pet_id = pet_options[0]
    else:
        st.session_state.active_pet_id = None

    active_pet = get_pet_by_id(active_owner, st.session_state.active_pet_id)

    with col2:
        if pet_options:
            active_pet_id_value = st.session_state.active_pet_id
            if not isinstance(active_pet_id_value, str):
                active_pet_id_value = pet_options[0]
            selected_pet_id = st.selectbox(
                "Select pet",
                options=pet_options,
                index=pet_options.index(active_pet_id_value),
                format_func=lambda pet_id: pet_label(get_pet_by_id(active_owner, pet_id) or active_owner.pets[0]),
            )
            if selected_pet_id != st.session_state.active_pet_id:
                st.session_state.active_pet_id = selected_pet_id
                active_pet = get_pet_by_id(active_owner, selected_pet_id)
        else:
            st.info("No pets for this owner yet. Add one below.")

    if st.button("Save owner details", use_container_width=True):
        active_owner.name = owner_name.strip() or active_owner.name
        active_owner.daily_available_minutes = int(daily_minutes)
        st.success("Saved owner details.")

    st.markdown("### Add Pet To Selected Owner")
    pet_new_col1, pet_new_col2, pet_new_col3, pet_new_col4 = st.columns(4)
    with pet_new_col1:
        new_pet_name = st.text_input("New pet name", value="", key="new_pet_name")
    with pet_new_col2:
        new_pet_species = st.selectbox("New pet species", ["dog", "cat", "other"], key="new_pet_species")
    with pet_new_col3:
        new_pet_age = st.number_input("New pet age", min_value=0, max_value=40, value=1, key="new_pet_age")
    with pet_new_col4:
        new_pet_weight = st.number_input(
            "New pet weight (kg)",
            min_value=0.5,
            max_value=120.0,
            value=5.0,
            step=0.5,
            key="new_pet_weight",
        )

    if st.button("Add pet", use_container_width=True):
        pet_name_clean = new_pet_name.strip() or f"Pet {len(active_owner.pets) + 1}"
        created_pet = pawpal.Pet(
            name=pet_name_clean,
            species=new_pet_species,
            age_years=int(new_pet_age),
            weight_kg=float(new_pet_weight),
        )
        active_owner.add_pet(created_pet)
        st.session_state.active_pet_id = str(created_pet.pet_id)
        st.success(f"Added pet: {created_pet.name}")
        st.rerun()

    if active_pet is not None:
        st.markdown("### Edit Selected Pet")
        pet_col1, pet_col2 = st.columns(2)
        with pet_col1:
            pet_name = st.text_input("Pet name", value=active_pet.name, key="active_pet_name")
            species = st.selectbox(
                "Species",
                ["dog", "cat", "other"],
                index=["dog", "cat", "other"].index(active_pet.species) if active_pet.species in ["dog", "cat", "other"] else 2,
                key="active_pet_species",
            )
        with pet_col2:
            age_years = st.number_input(
                "Age (years)",
                min_value=0,
                max_value=40,
                value=int(active_pet.age_years),
                key="active_pet_age",
            )
            weight_kg = st.number_input(
                "Weight (kg)",
                min_value=0.5,
                max_value=120.0,
                value=float(active_pet.weight_kg),
                step=0.5,
                key="active_pet_weight",
            )

        if st.button("Save pet details", use_container_width=True):
            active_pet.name = pet_name.strip() or active_pet.name
            active_pet.species = species
            active_pet.age_years = int(age_years)
            active_pet.weight_kg = float(weight_kg)
            st.success("Saved pet details.")

st.divider()

st.subheader("Task Builder")
active_owner = st.session_state.owners[st.session_state.active_owner_id]
active_pet = get_pet_by_id(active_owner, st.session_state.active_pet_id)

if active_pet is None:
    st.info("Add a pet to start creating tasks and schedules.")
    st.stop()

task_col1, task_col2 = st.columns(2)

with task_col1:
    task_title = st.text_input("Task title", value="Morning walk")
    task_type_name = st.selectbox("Task type", [task_type.value for task_type in pawpal.TaskType], index=2)
    duration_minutes = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)

with task_col2:
    priority = st.slider("Priority", min_value=1, max_value=10, value=7)
    importance = st.slider("Importance", min_value=1, max_value=10, value=7)
    frequency_label = st.selectbox("Frequency", ["None", "Daily", "Weekly"], index=0)
    due_date_value = st.date_input("Due date", value=date.today())
    required = st.checkbox("Required task", value=False)

use_window = st.checkbox("Set preferred time window", value=False)
preferred_window = None
if use_window:
    win_col1, win_col2 = st.columns(2)
    with win_col1:
        start_hour = st.number_input("Start hour", min_value=0, max_value=23, value=8)
    with win_col2:
        end_hour = st.number_input("End hour", min_value=1, max_value=24, value=10)

    if int(end_hour) <= int(start_hour):
        st.error("End hour must be greater than start hour.")
    else:
        preferred_window = pawpal.TimeWindow(start_hour=int(start_hour), end_hour=int(end_hour))

if st.button("Add task", use_container_width=True):
    selected_frequency = None if frequency_label == "None" else frequency_label.lower()
    new_task = pawpal.Task(
        title=task_title.strip() or "Untitled task",
        task_type=pawpal.TaskType(task_type_name),
        duration_minutes=int(duration_minutes),
        priority=int(priority),
        importance=int(importance),
        due_date=due_date_value,
        frequency=selected_frequency,
        preferred_window=preferred_window,
        required=required,
    )
    if not new_task.validate():
        st.error("Task is invalid. Please check duration, priority/importance, and time window.")
    else:
        active_pet.add_task(new_task)
        st.success(f"Added task: {new_task.title}")

st.markdown("### Current Tasks")
scheduler_ui = SimpleScheduler(time_penalty_weight=1.0)
show_completed_tasks = st.checkbox("Show completed tasks", value=False)
all_tasks = scheduler_ui.sort_by_time(active_pet.get_tasks())
tasks_list = all_tasks if show_completed_tasks else [task for task in all_tasks if task.status != "completed"]

pending_count = len(scheduler_ui.filter_tasks(owner=active_owner, status="pending", pet_name=active_pet.name))
completed_count = len(scheduler_ui.filter_tasks(owner=active_owner, status="completed", pet_name=active_pet.name))
status_col1, status_col2 = st.columns(2)
with status_col1:
    st.success(f"Pending tasks for {active_pet.name}: {pending_count}")
with status_col2:
    st.info(f"Completed tasks for {active_pet.name}: {completed_count}")

if scheduler_ui.has_time_conflicts(tasks_list):
    conflicting_tasks = [task for task in tasks_list if task.preferred_window is not None]
    conflict_rows = []
    slot_counts: dict[int, int] = {}
    for task in conflicting_tasks:
        start_hour = task.preferred_window.start_hour
        slot_counts[start_hour] = slot_counts.get(start_hour, 0) + 1
    for task in conflicting_tasks:
        start_hour = task.preferred_window.start_hour
        if slot_counts.get(start_hour, 0) > 1:
            conflict_rows.append(
                {
                    "task": task.title,
                    "slot": (
                        f"{task.preferred_window.start_hour:02d}:00-"
                        f"{task.preferred_window.end_hour:02d}:00"
                    ),
                }
            )

    st.warning(
        "Two or more tasks share the same preferred start hour. "
        "Consider adjusting one time window so your pet-care plan is easier to follow."
    )
    if conflict_rows:
        st.table(conflict_rows)

if tasks_list:
    st.table(
        [
            {
                "title": task.title,
                "type": task.task_type.value,
                "duration": task.duration_minutes,
                "priority": task.priority,
                "importance": task.importance,
                "due_date": task.due_date.isoformat() if task.due_date else "Any",
                "frequency": task.frequency or "None",
                "required": task.required,
                "window": (
                    f"{task.preferred_window.start_hour:02d}:00-{task.preferred_window.end_hour:02d}:00"
                    if task.preferred_window
                    else "Any"
                ),
                "status": task.status,
            }
            for task in tasks_list
        ]
    )

    remove_options = {f"{task.title} ({task.task_id})": task.task_id for task in all_tasks}
    selected_label = st.selectbox("Remove a task", list(remove_options.keys()))
    if st.button("Remove selected task"):
        active_pet.remove_task(remove_options[selected_label])
        st.success("Task removed.")
        st.rerun()

    completable_tasks = [task for task in tasks_list if task.status != "completed"]
    if completable_tasks:
        complete_options = {f"{task.title} ({task.task_id})": task.task_id for task in completable_tasks}
        selected_complete_label = st.selectbox("Mark a task complete", list(complete_options.keys()))
        if st.button("Complete selected task"):
            selected_task_id = complete_options[selected_complete_label]
            next_task = scheduler_ui.mark_task_complete(active_pet, selected_task_id)
            if next_task is None:
                st.success("Task marked complete.")
            else:
                st.success(
                    f"Task marked complete. Next recurring task due on {next_task.due_date.isoformat()} and is now pending."
                )
            st.rerun()
    else:
        st.info("All tasks are already completed.")
else:
    if all_tasks:
        st.info("No pending tasks. Enable 'Show completed tasks' to view history.")
    else:
        st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Daily Plan")
penalty_weight = st.slider("Time-window penalty weight", min_value=0.0, max_value=5.0, value=1.0, step=0.5)

if st.button("Generate schedule", use_container_width=True):
    try:
        scheduler = SimpleScheduler(time_penalty_weight=float(penalty_weight))
        generated_plan = scheduler.build_plan(owner=active_owner, pet=active_pet, plan_date=date.today())
        plan_key = f"{active_owner.owner_id}:{active_pet.pet_id}"
        st.session_state.plans[plan_key] = generated_plan
    except ValueError as err:
        st.error(str(err))

current_plan_key = f"{active_owner.owner_id}:{active_pet.pet_id}"
plan_state: pawpal.DailyPlan | None = st.session_state.plans.get(current_plan_key)
if plan_state is not None:
    st.markdown(f"### Plan for {plan_state.plan_date.isoformat()}")
    if not plan_state.items:
        st.warning("No tasks could be scheduled with the current constraints.")
    else:
        for idx, item in enumerate(plan_state.items, start=1):
            st.markdown(
                f"{idx}. {format_minutes(item.start_minute)}-{format_minutes(item.end_minute)} | "
                f"{item.task.title} ({item.task.task_type.value})"
            )
            st.caption(item.explanation)

    st.caption(
        f"Total scheduled minutes: {plan_state.total_minutes} / {active_owner.daily_available_minutes}"
    )
