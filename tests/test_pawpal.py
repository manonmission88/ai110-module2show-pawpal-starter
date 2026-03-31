"""
Tests for core PawPal+ scheduling behaviors.
Run with: python -m pytest
"""

import pytest
from pawpal_system import Task, Pet, Owner, Scheduler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_task() -> Task:
    return Task(title="Morning walk", category="walk", duration_minutes=30, priority="high")


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

    sample_pet.add_task(Task("Long walk", "walk",    duration_minutes=15, priority="high"))
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
