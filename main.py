"""
PawPal+ demo script — run with: python3 main.py
Exercises sorting, filtering, recurring-task reset, and conflict detection.
"""

from datetime import date
from pawpal_system import Task, Pet, Owner, Scheduler


def section(title: str) -> None:
    print(f"\n{'=' * 55}")
    print(f"  {title}")
    print("=" * 55)


def main() -> None:
    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    mochi = Pet(name="Mochi", species="dog", age_years=3, breed="Shiba Inu")
    luna  = Pet(name="Luna",  species="cat", age_years=5, special_needs=["hyperthyroid meds"])

    # Tasks added intentionally OUT of time-window order to test sorting
    mochi.add_task(Task("Evening walk",  "walk",       30, "medium", preferred_time="evening",   frequency="daily",  due_date=date.today()))
    mochi.add_task(Task("Morning walk",  "walk",       30, "high",   preferred_time="morning",   frequency="daily",  due_date=date.today()))
    mochi.add_task(Task("Breakfast",     "feeding",    10, "high",   preferred_time="morning",   frequency="daily",  due_date=date.today()))
    mochi.add_task(Task("Puzzle toy",    "enrichment", 15, "low",    preferred_time="afternoon", frequency="daily",  due_date=date.today()))

    luna.add_task(Task("Thyroid meds",   "medication",  5, "high",   preferred_time="morning",   frequency="daily",  due_date=date.today()))
    luna.add_task(Task("Playtime",       "enrichment", 20, "medium", preferred_time="evening",   frequency="daily",  due_date=date.today()))
    luna.add_task(Task("Brushing",       "grooming",   10, "low",                                frequency="weekly", due_date=date.today()))

    mochi.add_task(Task("Vet call", "medication", 20, "high", preferred_time="morning", frequency="none", due_date=date.today()))

    jordan = Owner(name="Jordan", available_minutes=120, preferred_schedule="spread-out")
    jordan.add_pet(mochi)
    jordan.add_pet(luna)

    scheduler = Scheduler(jordan)

    # ------------------------------------------------------------------
    # 1. Generate plan (assigns start times automatically)
    # ------------------------------------------------------------------
    section("1. Today's Schedule")
    plan = scheduler.generate_plan()
    print(plan.explain())
    print(f"\nBudget: {jordan.available_minutes} min  |  Used: {plan.total_duration_minutes} min  |  Free: {jordan.available_minutes - plan.total_duration_minutes} min")

    # ------------------------------------------------------------------
    # 2. Sort scheduled tasks by HH:MM start time
    # ------------------------------------------------------------------
    section("2. Sorted by Start Time")
    time_sorted = scheduler.sort_by_time(plan.scheduled_tasks)
    for t in time_sorted:
        print(f"  {t.start_time or '??:??'}  {t.title:<20} ({t.duration_minutes} min, {t.priority})")

    # ------------------------------------------------------------------
    # 3. Filter — only Mochi's tasks, only pending
    # ------------------------------------------------------------------
    section("3. Filtered: Mochi's pending tasks")
    all_tasks = jordan.get_all_tasks()
    mochi_pending = scheduler.filter_tasks(all_tasks, pet_name="Mochi", completed=False)
    for t in mochi_pending:
        print(f"  [{t.priority:6}]  {t.title}")

    # ------------------------------------------------------------------
    # 4. Recurring reset — mark a task done, then reset for tomorrow
    # ------------------------------------------------------------------
    section("4. Recurring Task Reset")
    morning_walk = next(t for t in mochi.tasks if t.title == "Morning walk")
    print(f"  Before: '{morning_walk.title}' completed={morning_walk.completed}, due={morning_walk.due_date}")
    morning_walk.mark_complete()
    count = scheduler.reset_recurring_tasks()
    print(f"  {count} recurring task(s) reset for next occurrence.")
    new_walk = next((t for t in mochi.tasks if t.title == "Morning walk"), None)
    if new_walk:
        print(f"  After : '{new_walk.title}' completed={new_walk.completed}, due={new_walk.due_date}")

    # ------------------------------------------------------------------
    # 5. Conflict detection — force two overlapping tasks to prove detection
    # ------------------------------------------------------------------
    section("5. Conflict Detection")
    # Stamp two tasks with overlapping windows manually to simulate a clash
    walk = Task("Morning walk",  "walk",       30, "high", preferred_time="morning")
    bath = Task("Grooming bath", "grooming",   20, "low",  preferred_time="morning")
    walk.start_time = "07:00"   # ends 07:30
    bath.start_time = "07:15"   # starts INSIDE walk — overlap!

    conflicts = scheduler.detect_conflicts([walk, bath])
    if conflicts:
        for warning in conflicts:
            print(f"  ⚠  {warning}")
    else:
        print("  No conflicts detected.")

    # Confirm no conflicts in the auto-generated plan
    plan_conflicts = scheduler.detect_conflicts(plan.scheduled_tasks)
    status = "None (clean schedule)" if not plan_conflicts else str(plan_conflicts)
    print(f"\n  Auto-generated plan conflicts: {status}")


if __name__ == "__main__":
    main()
