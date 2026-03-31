"""
Tests for core PawPal+ scheduling behaviors.
Run with: python3 -m pytest
"""

import pytest
from datetime import date
from pawpal_system import Task, Pet, Owner, Scheduler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_task() -> Task:
    return Task(title="Morning walk", category="walk", duration_minutes=30, priority="high",
                frequency="daily", due_date=date.today())


@pytest.fixture
def sample_pet() -> Pet:
    return Pet(name="Mochi", species="dog", age_years=3)


@pytest.fixture
def owner_with_pet(sample_pet: Pet) -> Owner:
    owner = Owner(name="Jordan", available_minutes=120)
    owner.add_pet(sample_pet)
    return owner


# ---------------------------------------------------------------------------
# Task: mark_complete
# ---------------------------------------------------------------------------

def test_mark_complete_changes_status(sample_task: Task) -> None:
    """Calling mark_complete() must flip completed from False to True."""
    assert sample_task.completed is False
    sample_task.mark_complete()
    assert sample_task.completed is True


def test_mark_complete_is_idempotent(sample_task: Task) -> None:
    """Calling mark_complete() twice should not raise and should stay True."""
    sample_task.mark_complete()
    sample_task.mark_complete()
    assert sample_task.completed is True


# ---------------------------------------------------------------------------
# Pet: add_task increases count
# ---------------------------------------------------------------------------

def test_add_task_increases_count(sample_pet: Pet, sample_task: Task) -> None:
    """Adding a task to a pet must increase its task list by exactly one."""
    before = len(sample_pet.tasks)
    sample_pet.add_task(sample_task)
    assert len(sample_pet.tasks) == before + 1


def test_add_multiple_tasks(sample_pet: Pet) -> None:
    """Adding three tasks should result in exactly three tasks on the pet."""
    for i in range(3):
        sample_pet.add_task(Task(f"Task {i}", "walk", duration_minutes=10, priority="low"))
    assert len(sample_pet.tasks) == 3


# ---------------------------------------------------------------------------
# Scheduler: priority ordering and time budget
# ---------------------------------------------------------------------------

def test_high_priority_tasks_scheduled_first(owner_with_pet: Owner, sample_pet: Pet) -> None:
    """High-priority tasks must appear in the plan before lower-priority ones."""
    sample_pet.add_task(Task("Low task",  "enrichment", duration_minutes=10, priority="low"))
    sample_pet.add_task(Task("High task", "walk",       duration_minutes=10, priority="high"))

    scheduler = Scheduler(owner_with_pet)
    plan = scheduler.generate_plan()

    titles = [t.title for t in plan.scheduled_tasks]
    assert titles.index("High task") < titles.index("Low task")


def test_tasks_exceeding_budget_are_skipped(sample_pet: Pet) -> None:
    """Tasks that push past the time budget must appear in skipped_tasks."""
    owner = Owner(name="Alex", available_minutes=20)
    owner.add_pet(sample_pet)

    sample_pet.add_task(Task("Long walk", "walk",     duration_minutes=15, priority="high"))
    sample_pet.add_task(Task("Grooming",  "grooming", duration_minutes=15, priority="medium"))

    plan = Scheduler(owner).generate_plan()

    assert len(plan.scheduled_tasks) == 1
    assert len(plan.skipped_tasks) == 1
    assert plan.scheduled_tasks[0].title == "Long walk"


def test_completed_tasks_excluded_from_plan(sample_pet: Pet) -> None:
    """Tasks already marked complete must not appear in the generated plan."""
    task = Task("Breakfast", "feeding", duration_minutes=10, priority="high")
    task.mark_complete()
    sample_pet.add_task(task)

    owner = Owner(name="Sam", available_minutes=60)
    owner.add_pet(sample_pet)

    plan = Scheduler(owner).generate_plan()
    assert task not in plan.scheduled_tasks


# ---------------------------------------------------------------------------
# Scheduler: sort_by_time
# ---------------------------------------------------------------------------

def test_sort_by_time_orders_by_hhmm(sample_pet: Pet, owner_with_pet: Owner) -> None:
    """sort_by_time must order tasks earliest start_time first."""
    t1 = Task("Late task",  "walk",    10, "low")
    t2 = Task("Early task", "feeding", 10, "high")
    t1.start_time = "14:00"
    t2.start_time = "07:30"

    scheduler = Scheduler(owner_with_pet)
    result = scheduler.sort_by_time([t1, t2])
    assert result[0].title == "Early task"
    assert result[1].title == "Late task"


def test_sort_by_time_no_start_time_goes_last(sample_pet: Pet, owner_with_pet: Owner) -> None:
    """Tasks without a start_time should sort to the end."""
    t1 = Task("Timed task",   "walk",    10, "high")
    t2 = Task("Untimed task", "feeding", 10, "low")
    t1.start_time = "08:00"

    scheduler = Scheduler(owner_with_pet)
    result = scheduler.sort_by_time([t2, t1])
    assert result[0].title == "Timed task"
    assert result[1].title == "Untimed task"


# ---------------------------------------------------------------------------
# Scheduler: filter_tasks
# ---------------------------------------------------------------------------

def test_filter_by_pet_name(sample_pet: Pet) -> None:
    """filter_tasks(pet_name=X) must return only tasks belonging to that pet."""
    other_pet = Pet(name="Luna", species="cat", age_years=2)
    t1 = Task("Walk",  "walk",    10, "high")
    t2 = Task("Meds",  "medication", 5, "high")
    sample_pet.add_task(t1)
    other_pet.add_task(t2)

    owner = Owner(name="Alex", available_minutes=60)
    owner.add_pet(sample_pet)
    owner.add_pet(other_pet)

    scheduler = Scheduler(owner)
    result = scheduler.filter_tasks(owner.get_all_tasks(), pet_name="Mochi")
    assert t1 in result
    assert t2 not in result


def test_filter_by_completed_status(sample_pet: Pet, owner_with_pet: Owner) -> None:
    """filter_tasks(completed=False) must exclude completed tasks."""
    done = Task("Done task",    "feeding",    10, "low")
    todo = Task("Pending task", "enrichment", 10, "medium")
    done.mark_complete()
    sample_pet.add_task(done)
    sample_pet.add_task(todo)

    scheduler = Scheduler(owner_with_pet)
    result = scheduler.filter_tasks(owner_with_pet.get_all_tasks(), completed=False)
    assert done not in result
    assert todo in result


# ---------------------------------------------------------------------------
# Scheduler: detect_conflicts
# ---------------------------------------------------------------------------

def test_detect_conflicts_finds_overlap(owner_with_pet: Owner) -> None:
    """detect_conflicts must return a warning when two tasks overlap."""
    t1 = Task("Walk",     "walk",    30, "high")
    t2 = Task("Grooming", "grooming", 20, "low")
    t1.start_time = "07:00"   # ends 07:30
    t2.start_time = "07:15"   # starts inside t1 — overlap

    scheduler = Scheduler(owner_with_pet)
    warnings = scheduler.detect_conflicts([t1, t2])
    assert len(warnings) == 1
    assert "Walk" in warnings[0]
    assert "Grooming" in warnings[0]


def test_detect_conflicts_no_overlap(owner_with_pet: Owner) -> None:
    """detect_conflicts must return empty list when tasks do not overlap."""
    t1 = Task("Walk",      "walk",    30, "high")
    t2 = Task("Breakfast", "feeding", 10, "high")
    t1.start_time = "07:00"   # ends 07:30
    t2.start_time = "07:30"   # starts exactly when t1 ends — not an overlap

    scheduler = Scheduler(owner_with_pet)
    assert scheduler.detect_conflicts([t1, t2]) == []


# ---------------------------------------------------------------------------
# Task: next_occurrence / reset_recurring_tasks
# ---------------------------------------------------------------------------

def test_next_occurrence_advances_due_date(sample_task: Task) -> None:
    """next_occurrence() must return a task due one day later."""
    today = date.today()
    sample_task.due_date = today
    nxt = sample_task.next_occurrence()
    assert nxt is not None
    assert nxt.due_date == today + __import__("datetime").timedelta(days=1)
    assert nxt.completed is False


def test_next_occurrence_none_for_non_recurring() -> None:
    """next_occurrence() must return None for frequency='none'."""
    task = Task("One-off", "grooming", 15, "low", frequency="none", is_recurring=False)
    assert task.next_occurrence() is None


def test_reset_recurring_tasks_replaces_completed(sample_pet: Pet) -> None:
    """reset_recurring_tasks must swap completed recurring tasks for fresh copies."""
    task = Task("Daily walk", "walk", 30, "high", frequency="daily",
                is_recurring=True, due_date=date.today())
    sample_pet.add_task(task)
    task.mark_complete()

    owner = Owner(name="Jordan", available_minutes=60)
    owner.add_pet(sample_pet)
    scheduler = Scheduler(owner)
    count = scheduler.reset_recurring_tasks()

    assert count == 1
    assert task not in sample_pet.tasks          # old completed task removed
    assert any(t.title == "Daily walk" and not t.completed for t in sample_pet.tasks)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_generate_plan_pet_with_no_tasks() -> None:
    """A pet with no tasks must produce an empty plan without raising."""
    empty_pet = Pet(name="Ghost", species="cat", age_years=1)
    owner = Owner(name="Sam", available_minutes=60)
    owner.add_pet(empty_pet)

    plan = Scheduler(owner).generate_plan()
    assert plan.scheduled_tasks == []
    assert plan.skipped_tasks == []
    assert plan.total_duration_minutes == 0


def test_generate_plan_zero_budget_skips_all(sample_pet: Pet) -> None:
    """When available_minutes=0, every task must land in skipped_tasks."""
    sample_pet.add_task(Task("Walk",      "walk",    10, "high"))
    sample_pet.add_task(Task("Breakfast", "feeding",  5, "high"))

    owner = Owner(name="Alex", available_minutes=0)
    owner.add_pet(sample_pet)

    plan = Scheduler(owner).generate_plan()
    assert plan.scheduled_tasks == []
    assert len(plan.skipped_tasks) == 2


def test_detect_conflicts_exact_same_start_time(owner_with_pet: Owner) -> None:
    """Two tasks with the identical start time must be flagged as a conflict."""
    t1 = Task("Walk",  "walk",    20, "high")
    t2 = Task("Meds",  "medication", 10, "high")
    t1.start_time = "08:00"
    t2.start_time = "08:00"   # exact same time — definite overlap

    warnings = Scheduler(owner_with_pet).detect_conflicts([t1, t2])
    assert len(warnings) == 1
