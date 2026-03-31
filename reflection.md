# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

Three core actions a user should be able to perform:

1. **Set up a pet profile** — The user enters basic information about themselves and their pet (pet name, species/breed, owner name, available time per day). This anchors all scheduling decisions to a specific pet's needs and the owner's real-world constraints.

2. **Add and manage care tasks** — The user creates tasks (walks, feeding, medication, grooming, enrichment, etc.), each with at minimum a duration and a priority level. The user can also edit or remove existing tasks. This gives the scheduler the raw material it needs to build a plan.

3. **Generate and view a daily care plan** — The user triggers the scheduler, which selects and orders tasks that fit within the owner's available time, weighted by priority. The app displays the resulting plan clearly and explains why each task was included or excluded, so the owner understands and trusts the output.

The initial design has five classes arranged in a clear data → logic → output pipeline.

- **`Task` (dataclass)** — holds everything about one care activity: its title, category, duration, priority, an optional preferred time window, and whether it recurs daily. It is a pure data object with one helper method (`to_dict`) for display.
- **`Pet` (dataclass)** — stores the animal's identifying information (name, species, breed, age, special needs). It is also a data object; its only method (`summary`) produces a human-readable description.
- **`Owner`** — represents the person doing the caring. It holds the daily time budget, a scheduling preference (morning-heavy, evening-heavy, or spread-out), and the list of pets. It manages its own pet list via `add_pet` / `remove_pet`.
- **`Scheduler`** — the core logic layer. It takes an `Owner` and a list of `Task` objects and produces a `DailyPlan`. It uses private helpers to sort by priority and check whether a task fits in the remaining time budget.
- **`DailyPlan`** — the output artifact. It separates tasks into scheduled vs. skipped, records the total duration and generation timestamp, and provides `explain()` and `display_table()` for the UI.

**b. Design changes**

Two changes were made after reviewing the skeleton against the UML:

1. **Added `pet: Optional[Pet]` to `Task`.**
   The original design had no link between a task and the specific pet it is for. Without this, a multi-pet household would have no way to know which walk belongs to which animal. Adding an optional `pet` field on `Task` makes the relationship explicit while keeping it optional for single-pet users.

2. **Added `_group_by_time_window()` to `Scheduler`.**
   `Task.preferred_time` (morning / afternoon / evening) was stored but never used by any scheduler method — a silent dead attribute. Adding this private helper closes the gap: `generate_plan()` can now bucket tasks into time windows and order them accordingly, honoring the owner's time preferences rather than ignoring them.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

The scheduler uses a **greedy, priority-first selection** strategy: it sorts all pending tasks high → medium → low, then greedily picks each task if it fits in the remaining time budget, skipping any that don't fit and moving on. Once a task is skipped it is never reconsidered, even if a later combination of smaller tasks would have used the budget more efficiently.

For example: if the budget is 20 minutes and the task list is [high/15 min, medium/15 min, low/10 min], the greedy approach schedules only the high-priority task (15 min used, 5 min wasted) and skips everything else — even though the low-priority 10-minute task would fit in the remaining 5 minutes.

This is reasonable for a pet care app because:
- High-priority tasks (medication, feeding) are genuinely more important than filling every minute, so correctness of priority order matters more than maximal time utilization.
- A busy owner needs a predictable, easy-to-trust plan — optimal bin-packing would sometimes produce counterintuitive results (e.g., skipping a "high" task to fit two "low" tasks).
- The tradeoff is honest: skipped tasks are surfaced explicitly in the plan's explanation, so the owner can see what didn't make it and why.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
