"""
PawPal+ — Logic Layer
All backend classes for the pet care scheduling system.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    title: str
    category: str                        # walk, feeding, medication, grooming, enrichment
    duration_minutes: int
    priority: str                        # low | medium | high
    preferred_time: Optional[str] = None # morning | afternoon | evening | None
    is_recurring: bool = True

    def to_dict(self) -> dict:
        """Return a plain dict representation suitable for display."""
        pass


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    name: str
    species: str                         # dog | cat | other
    age_years: float
    breed: Optional[str] = None
    special_needs: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Return a human-readable description of the pet."""
        pass


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

class Owner:
    def __init__(
        self,
        name: str,
        available_minutes: int,
        preferred_schedule: str = "spread-out",  # morning-heavy | evening-heavy | spread-out
    ) -> None:
        self.name = name
        self.available_minutes = available_minutes
        self.preferred_schedule = preferred_schedule
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to the owner's list."""
        pass

    def remove_pet(self, pet_name: str) -> None:
        """Remove a pet by name."""
        pass

    def total_pets(self) -> int:
        """Return the number of pets the owner has."""
        pass


# ---------------------------------------------------------------------------
# DailyPlan
# ---------------------------------------------------------------------------

class DailyPlan:
    def __init__(
        self,
        scheduled_tasks: list[Task],
        skipped_tasks: list[Task],
    ) -> None:
        self.scheduled_tasks = scheduled_tasks
        self.skipped_tasks = skipped_tasks
        self.total_duration_minutes: int = sum(t.duration_minutes for t in scheduled_tasks)
        self.generated_at: datetime = datetime.now()

    def explain(self) -> str:
        """Narrate why each task was included or skipped."""
        pass

    def display_table(self) -> list[dict]:
        """Return scheduled tasks as a list of dicts for st.table()."""
        pass


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    def __init__(self, owner: Owner) -> None:
        self.owner = owner
        self.tasks: list[Task] = []

    def add_task(self, task: Task) -> None:
        """Add a task to the scheduler."""
        pass

    def remove_task(self, title: str) -> None:
        """Remove a task by title."""
        pass

    def generate_plan(self) -> DailyPlan:
        """Select and order tasks that fit within the owner's available time."""
        pass

    def _sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted high → medium → low priority."""
        pass

    def _fits_in_time(self, task: Task, remaining_minutes: int) -> bool:
        """Return True if the task fits within the remaining time budget."""
        pass

