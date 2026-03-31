import streamlit as st
from pawpal_system import Task, Pet, Owner, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Session state bootstrap
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None

# ---------------------------------------------------------------------------
# 1. Owner setup
# ---------------------------------------------------------------------------
st.header("1. Owner Info")

with st.form("owner_form"):
    owner_name        = st.text_input("Your name", value="Jordan")
    available_minutes = st.number_input("Minutes available today", min_value=10, max_value=480, value=90, step=5)
    preferred_schedule = st.selectbox("Scheduling preference", ["spread-out", "morning-heavy", "evening-heavy"])
    submitted_owner   = st.form_submit_button("Save owner")

if submitted_owner:
    st.session_state.owner = Owner(
        name=owner_name,
        available_minutes=int(available_minutes),
        preferred_schedule=preferred_schedule,
    )
    st.success(f"Saved: {owner_name} — {available_minutes} min/day ({preferred_schedule})")

if st.session_state.owner is None:
    st.info("Fill in your owner info above to get started.")
    st.stop()

owner: Owner = st.session_state.owner

# ---------------------------------------------------------------------------
# 2. Add a pet
# ---------------------------------------------------------------------------
st.header("2. Add a Pet")

with st.form("pet_form"):
    pet_name          = st.text_input("Pet name", value="Mochi")
    species           = st.selectbox("Species", ["dog", "cat", "other"])
    breed             = st.text_input("Breed (optional)")
    age_years         = st.number_input("Age (years)", min_value=0.0, max_value=30.0, value=3.0, step=0.5)
    special_needs_raw = st.text_input("Special needs (comma-separated, or leave blank)")
    submitted_pet     = st.form_submit_button("Add pet")

if submitted_pet:
    special_needs = [s.strip() for s in special_needs_raw.split(",") if s.strip()]
    owner.add_pet(Pet(
        name=pet_name,
        species=species,
        breed=breed if breed else None,
        age_years=float(age_years),
        special_needs=special_needs,
    ))
    st.success(f"Added {pet_name} ({species}) to {owner.name}'s pets.")

if owner.total_pets() == 0:
    st.info("No pets yet — add one above.")
else:
    cols = st.columns(len(owner.pets))
    for col, pet in zip(cols, owner.pets):
        col.metric(pet.name, pet.species, f"{pet.age_years} yrs")

# ---------------------------------------------------------------------------
# 3. Add a task
# ---------------------------------------------------------------------------
st.header("3. Add a Task")

if owner.total_pets() == 0:
    st.warning("Add at least one pet before adding tasks.")
else:
    pet_names = [p.name for p in owner.pets]

    with st.form("task_form"):
        assigned_pet   = st.selectbox("Assign to pet", pet_names)
        task_title     = st.text_input("Task title", value="Morning walk")
        category       = st.selectbox("Category", ["walk", "feeding", "medication", "grooming", "enrichment"])
        duration       = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        priority       = st.selectbox("Priority", ["high", "medium", "low"])
        preferred_time = st.selectbox("Preferred time", ["morning", "afternoon", "evening", "any"])
        frequency      = st.selectbox("Frequency", ["daily", "weekly", "none"])
        submitted_task = st.form_submit_button("Add task")

    if submitted_task:
        target_pet = next(p for p in owner.pets if p.name == assigned_pet)
        target_pet.add_task(Task(
            title=task_title,
            category=category,
            duration_minutes=int(duration),
            priority=priority,
            preferred_time=preferred_time if preferred_time != "any" else None,
            is_recurring=frequency != "none",
            frequency=frequency,
        ))
        st.success(f"Added '{task_title}' ({priority} priority) to {assigned_pet}.")

    # --- Task list with filter controls ---
    all_tasks = owner.get_all_tasks()
    if all_tasks:
        st.subheader("Current tasks")

        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            filter_pet = st.selectbox("Filter by pet", ["All"] + pet_names, key="filter_pet")
        with filter_col2:
            filter_status = st.selectbox("Filter by status", ["All", "Pending", "Completed"], key="filter_status")

        scheduler_for_filter = Scheduler(owner)
        filtered = all_tasks
        if filter_pet != "All":
            filtered = scheduler_for_filter.filter_tasks(filtered, pet_name=filter_pet)
        if filter_status == "Pending":
            filtered = scheduler_for_filter.filter_tasks(filtered, completed=False)
        elif filter_status == "Completed":
            filtered = scheduler_for_filter.filter_tasks(filtered, completed=True)

        if filtered:
            st.table([t.to_dict() for t in filtered])
        else:
            st.info("No tasks match the current filters.")
    else:
        st.info("No tasks yet — add one above.")

# ---------------------------------------------------------------------------
# 4. Generate schedule
# ---------------------------------------------------------------------------
st.header("4. Today's Schedule")

if st.button("Generate schedule", type="primary"):
    all_tasks = owner.get_all_tasks()
    if not all_tasks:
        st.warning("Add some tasks first.")
    else:
        scheduler = Scheduler(owner)
        plan = scheduler.generate_plan()

        # --- Budget metric ---
        free = owner.available_minutes - plan.total_duration_minutes
        m1, m2, m3 = st.columns(3)
        m1.metric("Budget", f"{owner.available_minutes} min")
        m2.metric("Scheduled", f"{plan.total_duration_minutes} min")
        m3.metric("Free", f"{free} min", delta_color="normal")

        # --- Conflict warnings (shown prominently before the table) ---
        if plan.conflicts:
            st.warning("**Scheduling conflicts detected** — review before your day starts:")
            for warning in plan.conflicts:
                st.error(f"⚠ {warning}")
        else:
            st.success("No scheduling conflicts.")

        # --- Scheduled tasks sorted by start time ---
        st.subheader("Scheduled tasks (by start time)")
        if plan.scheduled_tasks:
            time_sorted = scheduler.sort_by_time(plan.scheduled_tasks)
            st.table([t.to_dict() for t in time_sorted])
        else:
            st.info("No tasks fit within today's time budget.")

        # --- Skipped tasks ---
        if plan.skipped_tasks:
            with st.expander(f"Skipped tasks — {len(plan.skipped_tasks)} didn't fit"):
                st.caption("These tasks were dropped because the time budget ran out. Consider raising your available minutes or lowering task durations.")
                st.table([t.to_dict() for t in plan.skipped_tasks])

        # --- Full explanation ---
        with st.expander("Full plan explanation"):
            st.code(plan.explain(), language=None)

# ---------------------------------------------------------------------------
# 5. Reset recurring tasks (end-of-day action)
# ---------------------------------------------------------------------------
st.header("5. End of Day")
st.caption("Mark all recurring tasks complete and schedule them for tomorrow.")

if st.button("Reset recurring tasks for tomorrow"):
    all_tasks = owner.get_all_tasks()
    if not all_tasks:
        st.warning("No tasks to reset.")
    else:
        # Mark all pending recurring tasks complete first
        for task in owner.get_pending_tasks():
            if task.is_recurring:
                task.mark_complete()

        scheduler = Scheduler(owner)
        count = scheduler.reset_recurring_tasks()
        if count:
            st.success(f"Reset {count} recurring task(s) — they're now scheduled for tomorrow.")
        else:
            st.info("No recurring tasks to reset.")
