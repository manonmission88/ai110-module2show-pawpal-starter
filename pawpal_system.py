"""
PawPal+ — Logic Layer
All backend classes for the pet care scheduling system.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

# First available start minute (offset from midnight) for each time window
_WINDOW_START_MINUTE = {"morning": 7 * 60, "afternoon": 12 * 60, "evening": 17 * 60, "anytime": 9 * 60}


def _minutes_to_hhmm(total_minutes: int) -> str:
    """Convert an offset in minutes-from-midnight to 'HH:MM' string."""
    h, m = divmod(total_minutes % (24 * 60), 60)
    return f"{h:02d}:{m:02d}"


def _hhmm_to_minutes(hhmm: str) -> int:
    """Parse 'HH:MM' into minutes-from-midnight; returns 0 on bad input."""
    try:
        h, m = hhmm.split(":")
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return 0


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A single pet care activity with scheduling metadata."""

    title: str
    category: str                             # walk | feeding | medication | grooming | enrichment
    duration_minutes: int
    priority: str                             # low | medium | high
    preferred_time: Optional[str] = None      # morning | afternoon | evening | None
    is_recurring: bool = True
    frequency: str = "daily"                  # daily | weekly | none
    completed: bool = False
    start_time: Optional[str] = None          # HH:MM — set by Scheduler.generate_plan()
    due_date: Optional[date] = None           # date this task is next due

    def mark_complete(self) -> None:
        """Mark this task as completed for today."""
        self.completed = True

    def next_occurrence(self) -> Optional[Task]:
        """Return a fresh copy of this task due on the next occurrence date.

        Returns None if the task is not recurring (frequency == 'none').
        The returned task is not yet completed and has no assigned start_time.
        """
        if self.frequency == "none" or not self.is_recurring:
            return None
        delta = timedelta(days=1) if self.frequency == "daily" else timedelta(weeks=1)
        base = self.due_date if self.due_date else date.today()
        return Task(
            title=self.title,
            category=self.category,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            preferred_time=self.preferred_time,
            is_recurring=self.is_recurring,
            frequency=self.frequency,
            completed=False,
            start_time=None,
            due_date=base + delta,
        )

    def to_dict(self) -> dict:
        """Return a plain dict representation suitable for st.table() display."""
        return {
            "title": self.title,
            "category": self.category,
            "start time": self.start_time or "—",
            "duration (min)": self.duration_minutes,
            "priority": self.priority,
            "preferred time": self.preferred_time or "any",
            "frequency": self.frequency,
            "due date": str(self.due_date) if self.due_date else "—",
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

    def find_pet_for_task(self, task: Task) -> Optional[Pet]:
        """Return the Pet that owns the given task, or None if not found."""
        for pet in self.pets:
            if task in pet.tasks:
                return pet
        return None


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
        conflicts: list[str],
    ) -> None:
        self.scheduled_tasks = scheduled_tasks
        self.skipped_tasks = skipped_tasks
        self.conflicts = conflicts
        self.total_duration_minutes: int = sum(t.duration_minutes for t in scheduled_tasks)
        self.generated_at: datetime = datetime.now()

    def explain(self) -> str:
        """Narrate why each task was included or skipped, and list any conflicts."""
        lines: list[str] = [
            f"Daily plan generated at {self.generated_at.strftime('%H:%M')}",
            f"Total scheduled time: {self.total_duration_minutes} min",
            "",
            "SCHEDULED:",
        ]
        for task in self.scheduled_tasks:
            label = self._PRIORITY_LABEL.get(task.priority, task.priority)
            window = task.preferred_time or "any time"
            time_str = f" @ {task.start_time}" if task.start_time else ""
            lines.append(f"  ✓ {task.title}{time_str} ({task.duration_minutes} min, {label}, {window})")

        if self.skipped_tasks:
            lines += ["", "SKIPPED (not enough time):"]
            for task in self.skipped_tasks:
                lines.append(f"  ✗ {task.title} ({task.duration_minutes} min, priority: {task.priority})")

        if self.conflicts:
            lines += ["", "⚠ CONFLICTS DETECTED:"]
            for warning in self.conflicts:
                lines.append(f"  ! {warning}")

        return "\n".join(lines)

    def display_table(self) -> list[dict]:
        """Return scheduled tasks as a list of dicts for st.table()."""
        return [t.to_dict() for t in self.scheduled_tasks]


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """Selects and orders pet care tasks to fit within an owner's daily time budget."""

    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_plan(self) -> DailyPlan:
        """Build a DailyPlan by greedily scheduling priority-sorted pending tasks.

        Tasks are selected in priority order (high → medium → low), then
        reordered by preferred time window and assigned concrete HH:MM start
        times so that conflict detection has timestamps to compare.
        """
        pending = self.owner.get_pending_tasks()
        priority_sorted = self._sort_by_priority(pending)

        scheduled: list[Task] = []
        skipped: list[Task] = []
        remaining = self.owner.available_minutes

        for task in priority_sorted:
            if self._fits_in_time(task, remaining):
                scheduled.append(task)
                remaining -= task.duration_minutes
            else:
                skipped.append(task)

        # Reorder by time window, then stamp HH:MM start times
        scheduled = self._order_by_time_window(scheduled)
        self._assign_start_times(scheduled)

        conflicts = self.detect_conflicts(scheduled)
        return DailyPlan(scheduled, skipped, conflicts)

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted by their HH:MM start_time (earliest first).

        Tasks without a start_time sort to the end of the list.
        """
        return sorted(
            tasks,
            key=lambda t: _hhmm_to_minutes(t.start_time) if t.start_time else 24 * 60,
        )

    def filter_tasks(
        self,
        tasks: list[Task],
        pet_name: Optional[str] = None,
        completed: Optional[bool] = None,
    ) -> list[Task]:
        """Filter tasks by optional pet name and/or completion status.

        Pass pet_name to keep only tasks owned by that pet.
        Pass completed=True/False to filter by status.
        Omit a parameter (leave None) to skip that filter.
        """
        result = tasks
        if pet_name is not None:
            owned = [
                task
                for pet in self.owner.pets
                if pet.name == pet_name
                for task in pet.tasks
            ]
            result = [t for t in result if t in owned]
        if completed is not None:
            result = [t for t in result if t.completed == completed]
        return result

    def detect_conflicts(self, tasks: list[Task]) -> list[str]:
        """Return a list of human-readable warnings for any overlapping tasks.

        Two tasks conflict when their time windows overlap:
            task A end time > task B start time (for B starting after A).
        Only tasks with an assigned start_time are checked.
        """
        timed = [t for t in tasks if t.start_time]
        timed_sorted = sorted(timed, key=lambda t: _hhmm_to_minutes(t.start_time))  # type: ignore[arg-type]

        warnings: list[str] = []
        for i, a in enumerate(timed_sorted):
            a_start = _hhmm_to_minutes(a.start_time)  # type: ignore[arg-type]
            a_end = a_start + a.duration_minutes
            for b in timed_sorted[i + 1:]:
                b_start = _hhmm_to_minutes(b.start_time)  # type: ignore[arg-type]
                if b_start < a_end:
                    warnings.append(
                        f"'{a.title}' ({a.start_time}–{_minutes_to_hhmm(a_end)}) "
                        f"overlaps with '{b.title}' ({b.start_time})"
                    )
                else:
                    break   # list is sorted; no further overlaps with a

        return warnings

    def reset_recurring_tasks(self) -> int:
        """Replace each completed recurring task with its next occurrence.

        Walks every pet's task list, calls next_occurrence() on completed
        recurring tasks, and swaps the old instance for the new one in-place.
        Returns the count of tasks that were reset.
        """
        reset_count = 0
        for pet in self.owner.pets:
            new_tasks: list[Task] = []
            for task in pet.tasks:
                if task.completed and task.is_recurring and task.frequency != "none":
                    successor = task.next_occurrence()
                    if successor:
                        new_tasks.append(successor)
                        reset_count += 1
                    # drop the completed task — replaced by successor
                else:
                    new_tasks.append(task)
            pet.tasks = new_tasks
        return reset_count

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

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
        """Sort tasks by preferred time window (morning → afternoon → evening → anytime)."""
        groups = self._group_by_time_window(tasks)
        return (
            groups["morning"]
            + groups["afternoon"]
            + groups["evening"]
            + groups["anytime"]
        )

    def _assign_start_times(self, tasks: list[Task]) -> None:
        """Set start_time on each task sequentially within its time window.

        Tasks in the same window are stacked back-to-back starting from the
        window's nominal open time (morning=07:00, afternoon=12:00,
        evening=17:00, anytime=09:00).  Mutates tasks in place.
        """
        # Track the next available minute per window
        cursor: dict[str, int] = dict(_WINDOW_START_MINUTE)
        for task in tasks:
            window = task.preferred_time if task.preferred_time in cursor else "anytime"
            task.start_time = _minutes_to_hhmm(cursor[window])
            cursor[window] += task.duration_minutes
