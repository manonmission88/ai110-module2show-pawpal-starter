import streamlit as st
from pawpal_system import Task, Pet, Owner, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Session state bootstrap
# ---------------------------------------------------------------------------
# st.session_state persists across reruns for the life of the browser session.
# We only create the Owner once; every rerun finds it already in the "vault".

if "owner" not in st.session_state:
    st.session_state.owner = None   # set after the owner form is submitted

# ---------------------------------------------------------------------------
# Step 1: Owner setup
# ---------------------------------------------------------------------------

st.header("1. Owner Info")

with st.form("owner_form"):
    owner_name       = st.text_input("Your name", value="Jordan")
    available_minutes = st.number_input("Minutes available today", min_value=10, max_value=480, value=90, step=5)
    preferred_schedule = st.selectbox("Scheduling preference", ["spread-out", "morning-heavy", "evening-heavy"])
    submitted_owner  = st.form_submit_button("Save owner")

if submitted_owner:
    # Replace the stored owner each time the form is re-submitted
    st.session_state.owner = Owner(
        name=owner_name,
        available_minutes=int(available_minutes),
        preferred_schedule=preferred_schedule,
    )
    st.success(f"Owner saved: {owner_name} ({available_minutes} min/day)")

if st.session_state.owner is None:
    st.info("Fill in your owner info above to get started.")
    st.stop()   # nothing below makes sense without an owner

owner: Owner = st.session_state.owner

# ---------------------------------------------------------------------------
# Step 2: Add a pet
# ---------------------------------------------------------------------------

st.header("2. Add a Pet")

with st.form("pet_form"):
    pet_name    = st.text_input("Pet name", value="Mochi")
    species     = st.selectbox("Species", ["dog", "cat", "other"])
    breed       = st.text_input("Breed (optional)")
    age_years   = st.number_input("Age (years)", min_value=0.0, max_value=30.0, value=3.0, step=0.5)
    special_needs_raw = st.text_input("Special needs (comma-separated, or leave blank)")
    submitted_pet = st.form_submit_button("Add pet")

if submitted_pet:
    special_needs = [s.strip() for s in special_needs_raw.split(",") if s.strip()]
    new_pet = Pet(
        name=pet_name,
        species=species,
        breed=breed if breed else None,
        age_years=float(age_years),
        special_needs=special_needs,
    )
    owner.add_pet(new_pet)
    st.success(f"Added {pet_name} to {owner.name}'s pets.")

if owner.total_pets() == 0:
    st.info("No pets yet — add one above.")
else:
    st.write(f"**{owner.name}'s pets:** {', '.join(p.name for p in owner.pets)}")

# ---------------------------------------------------------------------------
# Step 3: Add a task to a pet
# ---------------------------------------------------------------------------

st.header("3. Add a Task")

if owner.total_pets() == 0:
    st.warning("Add at least one pet before adding tasks.")
else:
    pet_names = [p.name for p in owner.pets]

    with st.form("task_form"):
        assigned_pet  = st.selectbox("Assign to pet", pet_names)
        task_title    = st.text_input("Task title", value="Morning walk")
        category      = st.selectbox("Category", ["walk", "feeding", "medication", "grooming", "enrichment"])
        duration      = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        priority      = st.selectbox("Priority", ["high", "medium", "low"])
        preferred_time = st.selectbox("Preferred time", ["morning", "afternoon", "evening", "any"])
        is_recurring  = st.checkbox("Recurring daily?", value=True)
        submitted_task = st.form_submit_button("Add task")

    if submitted_task:
        target_pet = next(p for p in owner.pets if p.name == assigned_pet)
        new_task = Task(
            title=task_title,
            category=category,
            duration_minutes=int(duration),
            priority=priority,
            preferred_time=preferred_time if preferred_time != "any" else None,
            is_recurring=is_recurring,
        )
        target_pet.add_task(new_task)
        st.success(f"Added '{task_title}' to {assigned_pet}'s tasks.")

    # Show all current tasks across pets
    all_tasks = owner.get_all_tasks()
    if all_tasks:
        st.write("**All tasks:**")
        st.table([t.to_dict() for t in all_tasks])
    else:
        st.info("No tasks yet — add one above.")

# ---------------------------------------------------------------------------
# Step 4: Generate schedule
# ---------------------------------------------------------------------------

st.header("4. Generate Today's Schedule")

if st.button("Generate schedule", type="primary"):
    all_tasks = owner.get_all_tasks()
    if not all_tasks:
        st.warning("Add some tasks first.")
    else:
        scheduler = Scheduler(owner)
        plan = scheduler.generate_plan()

        st.subheader("Scheduled tasks")
        if plan.scheduled_tasks:
            st.table(plan.display_table())
        else:
            st.info("No tasks fit within today's time budget.")

        if plan.skipped_tasks:
            with st.expander(f"Skipped tasks ({len(plan.skipped_tasks)})"):
                st.table([t.to_dict() for t in plan.skipped_tasks])

        st.subheader("Plan explanation")
        st.code(plan.explain(), language=None)

        st.metric("Time used", f"{plan.total_duration_minutes} min",
                  delta=f"{owner.available_minutes - plan.total_duration_minutes} min free",
                  delta_color="normal")
