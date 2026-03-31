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
    """A single pet care activity with scheduling metadata."""

    title: str
    category: str                        # walk | feeding | medication | grooming | enrichment
    duration_minutes: int
    priority: str                        # low | medium | high
    preferred_time: Optional[str] = None # morning | afternoon | evening | None
    is_recurring: bool = True
    completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as completed for today."""
        self.completed = True

    def to_dict(self) -> dict:
        """Return a plain dict representation suitable for st.table() display."""
        return {
            "title": self.title,
            "category": self.category,
            "duration (min)": self.duration_minutes,
            "priority": self.priority,
            "preferred time": self.preferred_time or "any",
            "recurring": self.is_recurring,
            "completed": self.completed,
        }


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """An animal with its own list of care tasks."""

    name: str
    species: str                              # dog | cat | other
    age_years: float
    breed: Optional[str] = None
    special_needs: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, title: str) -> None:
        """Remove a task by title, silently ignoring if not found."""
        self.tasks = [t for t in self.tasks if t.title != title]

    def pending_tasks(self) -> list[Task]:
        """Return tasks that have not been completed yet."""
        return [t for t in self.tasks if not t.completed]

    def summary(self) -> str:
        """Return a human-readable one-liner describing the pet."""
        breed_str = f" ({self.breed})" if self.breed else ""
        needs_str = f", special needs: {', '.join(self.special_needs)}" if self.special_needs else ""
        return f"{self.name} — {self.age_years}yr {self.species}{breed_str}{needs_str}"


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

class Owner:
    """A pet owner with a daily time budget and one or more pets."""

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
        """Register a pet with this owner."""
        self.pets.append(pet)

    def remove_pet(self, pet_name: str) -> None:
        """Remove a pet by name, silently ignoring if not found."""
        self.pets = [p for p in self.pets if p.name != pet_name]

    def total_pets(self) -> int:
        """Return the number of pets registered to this owner."""
        return len(self.pets)

    def get_all_tasks(self) -> list[Task]:
        """Aggregate and return every task across all pets."""
        all_tasks: list[Task] = []
        for pet in self.pets:
            all_tasks.extend(pet.tasks)
        return all_tasks

    def get_pending_tasks(self) -> list[Task]:
        """Return only uncompleted tasks across all pets."""
        return [t for t in self.get_all_tasks() if not t.completed]


# ---------------------------------------------------------------------------
# DailyPlan
# ---------------------------------------------------------------------------

class DailyPlan:
    """The output of a scheduling run: scheduled tasks, skipped tasks, and explanations."""

    _PRIORITY_LABEL = {"high": "must-do", "medium": "should-do", "low": "nice-to-have"}

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
        lines: list[str] = [
            f"Daily plan generated at {self.generated_at.strftime('%H:%M')}",
            f"Total scheduled time: {self.total_duration_minutes} min",
            "",
            "SCHEDULED:",
        ]
        for task in self.scheduled_tasks:
            label = self._PRIORITY_LABEL.get(task.priority, task.priority)
            window = task.preferred_time or "any time"
            lines.append(f"  ✓ {task.title} ({task.duration_minutes} min, {label}, {window})")

        if self.skipped_tasks:
            lines += ["", "SKIPPED (not enough time):"]
            for task in self.skipped_tasks:
                lines.append(f"  ✗ {task.title} ({task.duration_minutes} min, priority: {task.priority})")

        return "\n".join(lines)

    def display_table(self) -> list[dict]:
        """Return scheduled tasks as a list of dicts for st.table()."""
        return [t.to_dict() for t in self.scheduled_tasks]


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
_TIME_WINDOW_ORDER = {"morning": 0, "afternoon": 1, "evening": 2}


class Scheduler:
    """Selects and orders pet care tasks to fit within an owner's daily time budget."""

    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def generate_plan(self) -> DailyPlan:
        """Build a DailyPlan by greedily scheduling priority-sorted pending tasks."""
        pending = self.owner.get_pending_tasks()
        sorted_tasks = self._sort_by_priority(pending)

        scheduled: list[Task] = []
        skipped: list[Task] = []
        remaining = self.owner.available_minutes

        for task in sorted_tasks:
            if self._fits_in_time(task, remaining):
                scheduled.append(task)
                remaining -= task.duration_minutes
            else:
                skipped.append(task)

        # Re-order scheduled tasks by preferred time window
        scheduled = self._order_by_time_window(scheduled)
        return DailyPlan(scheduled, skipped)

    def _sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted high → medium → low priority."""
        return sorted(tasks, key=lambda t: _PRIORITY_ORDER.get(t.priority, 99))

    def _fits_in_time(self, task: Task, remaining_minutes: int) -> bool:
        """Return True if the task fits within the remaining time budget."""
        return task.duration_minutes <= remaining_minutes

    def _group_by_time_window(self, tasks: list[Task]) -> dict[str, list[Task]]:
        """Bucket tasks into morning / afternoon / evening / anytime groups."""
        groups: dict[str, list[Task]] = {
            "morning": [], "afternoon": [], "evening": [], "anytime": []
        }
        for task in tasks:
            key = task.preferred_time if task.preferred_time in groups else "anytime"
            groups[key].append(task)
        return groups

    def _order_by_time_window(self, tasks: list[Task]) -> list[Task]:
        """Sort tasks by preferred time window (morning first, anytime last)."""
        groups = self._group_by_time_window(tasks)
        return (
            groups["morning"]
            + groups["afternoon"]
            + groups["evening"]
            + groups["anytime"]
        )
