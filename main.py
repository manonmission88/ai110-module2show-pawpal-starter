"""
PawPal+ demo script — run with: python main.py
Verifies that the logic layer works end-to-end in the terminal.
"""

from pawpal_system import Task, Pet, Owner, Scheduler


def main() -> None:
    # --- Pets ---
    mochi = Pet(name="Mochi", species="dog", age_years=3, breed="Shiba Inu")
    luna = Pet(name="Luna", species="cat", age_years=5, special_needs=["hyperthyroid meds"])

    # --- Tasks for Mochi ---
    mochi.add_task(Task("Morning walk",    "walk",       duration_minutes=30, priority="high",   preferred_time="morning"))
    mochi.add_task(Task("Breakfast",       "feeding",    duration_minutes=10, priority="high",   preferred_time="morning"))
    mochi.add_task(Task("Evening walk",    "walk",       duration_minutes=25, priority="medium", preferred_time="evening"))
    mochi.add_task(Task("Puzzle toy",      "enrichment", duration_minutes=15, priority="low",    preferred_time="afternoon"))

    # --- Tasks for Luna ---
    luna.add_task(Task("Thyroid meds",     "medication", duration_minutes=5,  priority="high",   preferred_time="morning"))
    luna.add_task(Task("Playtime",         "enrichment", duration_minutes=20, priority="medium", preferred_time="evening"))
    luna.add_task(Task("Brushing",         "grooming",   duration_minutes=10, priority="low"))

    # --- Owner ---
    jordan = Owner(name="Jordan", available_minutes=90, preferred_schedule="spread-out")
    jordan.add_pet(mochi)
    jordan.add_pet(luna)

    # --- Schedule ---
    scheduler = Scheduler(jordan)
    plan = scheduler.generate_plan()

    # --- Output ---
    print("=" * 55)
    print("        PawPal+  —  Today's Schedule")
    print("=" * 55)
    print(plan.explain())
    print()
    print(f"Owner : {jordan.name}")
    print(f"Pets  : {', '.join(p.name for p in jordan.pets)}")
    print(f"Budget: {jordan.available_minutes} min  |  Used: {plan.total_duration_minutes} min  |  Free: {jordan.available_minutes - plan.total_duration_minutes} min")
    print("=" * 55)


if __name__ == "__main__":
    main()
