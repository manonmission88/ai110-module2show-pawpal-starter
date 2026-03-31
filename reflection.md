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
#### What constraints does your scheduler consider (for example: time, priority, preferences)?
The scheduler considers three main constraints. The first is the owner's daily time budget, which is the hard ceiling. No matter how many tasks exist, the total scheduled time can never exceed `available_minutes`. The second is task priority, which is how the scheduler decides what to include when it can't fit everything. High priority tasks like medication and feeding get picked first, medium ones like walks get considered next, and low priority ones like enrichment or grooming only make it in if there's room left. The third is the preferred time window on each task. This doesn't affect which tasks get scheduled but it does affect when they appear in the plan. A morning walk should show up at 07:00 not 17:00 even if both slots have space.
#### How did you decide which constraints mattered most?
I decided the time budget was the most important constraint because it's the one that actually reflects the real world. An owner who only has 60 minutes genuinely cannot do 120 minutes of tasks no matter how much they want to. Priority came second because in pet care the stakes are real. Skipping a grooming session is fine. Skipping a diabetic cat's insulin is not. Time window came last because it's more of a preference than a hard rule. If a task has no preferred time the scheduler just fits it wherever it makes sense, and the plan still works.

**b. Tradeoffs**

The scheduler uses a greedy, priority-first selection strategy. It sorts all pending tasks from high to low priority then picks each one if it fits in the remaining time budget, skipping anything that doesn't fit and moving on. Once a task is skipped it is never reconsidered, even if a later combination of smaller tasks would have used the budget more efficiently.

For example if the budget is 20 minutes and the task list has a high/15 min task, a medium/15 min task, and a low/10 min task, the greedy approach schedules only the high priority task (15 min used, 5 min wasted) and skips the rest. Even though the low priority 10 minute task would fit in the remaining 5 minutes, it never gets a second look.

This is reasonable for a pet care app because high priority tasks like medication and feeding are genuinely more important than filling every minute. A busy owner also needs a predictable plan they can trust. Optimal bin-packing would sometimes produce counterintuitive results like skipping a high priority task to squeeze in two low priority ones. And the tradeoff is at least honest: skipped tasks show up in the plan explanation so the owner can see exactly what didn't make it and why.

---

## 3. AI Collaboration

**a. How you used AI**

 I started by just asking Copilot to "generate my classes" and the first thing it gave me was everything in one giant file with no separation between the data layer and the logic layer. I didn't love that so I kept pushing it , I'd say something like "ok but can the Pet own its own tasks instead of the Owner holding everything" and then it would regenerate and I'd look at it and think ok that's cleaner.

The features I found most useful:

- **Inline chat on a single method** — like I'd highlight `generate_plan` and just ask "what's missing here" and it would point out that I was sorting by priority but never actually using the `preferred_time` field, which was a real gap I hadn't noticed
- **`#file:pawpal_system.py` in chat**  this was genuinely helpful because it would look at my actual code instead of guessing. I'd ask "based on my file, how should the Scheduler talk to the Owner to get tasks" and the answer matched what I already had which was reassuring
- **Generating test stubs**  I described what I wanted to test in plain English and it gave me the structure, then I'd fill in the assertions myself because I wanted to make sure I actually understood what was being checked

The most useful prompts were weirdly the vague ones like "what edge cases am I missing for a pet scheduler" got me thinking about zero-budget owners and empty pets, which I then actually wrote tests for.

**b. Judgment and verification**

At one point I asked Copilot to suggest a conflict detection strategy and it came back with something that raised a `ValueError` when it found an overlap. I read that and thought no, a pet owner doesn't want the app to crash because two tasks overlap, they just want a warning. So I changed it to return a list of strings instead. The app keeps running, the warnings show up in the UI with `st.warning` / `st.error`, and the user can just look at them and decide what to do. I verified it worked by manually setting two tasks to `07:00` in `main.py` and checking that the warning printed without any exception.

Another one: Copilot suggested I use a `set` to build the list of tasks owned by a pet in `filter_tasks`. That crashed immediately because `Task` is a mutable dataclass and you can't hash it. I switched it to a plain list comprehension — simple fix, but it reminded me that AI suggestions aren't always tested against the actual types in your code.

**c. Separate chat sessions**

I used a new chat session for each phase  one for UML brainstorming, one for test planning, one for the scheduling algorithms. It genuinely helped. When I had everything in one long chat the suggestions started drifting  like it would reference an old version of a class I had already changed. Starting fresh each phase meant Copilot was looking at the current state of things, not some earlier draft.

**d. Being the "lead architect"**

The thing I kept learning over and over is that Copilot is really fast at writing code but it doesn't know what you actually want. It'll give you something that works but it won't push back on your design. So if I asked a bad question I'd get a technically correct but wrong answer. The times things went well were when I already had a rough idea  like "I want Pet to own its tasks, not Owner"  and then used AI to fill in the implementation details. The times things got messy were when I just said "build me a scheduler" with no opinion of my own.

Basically: AI is good at the "how," you still have to own the "what" and "why."

---

## 4. Testing and Verification

**a. What you tested**

I ended up with 19 tests total. The ones I felt were most important:

- **`mark_complete` changes status** — felt obvious but I wanted to lock it down because the whole recurring task system depends on it. If that flag doesn't flip correctly everything downstream breaks silently.
- **High-priority tasks scheduled first** — this is the core promise of the app. I added a low task and a high task in the wrong order and checked that the plan always puts high first. If this fails the whole priority system is broken.
- **Budget enforcement** — I made a task list that overflows the time budget on purpose and checked that the extras land in `skipped_tasks` not `scheduled_tasks`. Without this I wouldn't have caught a case where the loop was quietly ignoring the limit.
- **Conflict detection finds overlap** — I manually set two tasks to `07:00` and `07:15` and checked a warning came back. This matters because if conflict detection silently misses overlaps it's worse than not having it — the owner would trust the plan and then have a chaotic morning.
- **Edge cases: empty pet, zero budget** — I added these after asking Copilot "what am I probably not testing." Both are real situations. An owner who hasn't added tasks yet, or sets available time to zero, should get a clean empty plan not a crash.

**b. Confidence**

I'd say 3.5 out of 5. The core happy paths work well — I've run the demo many times and the scheduling, sorting, and recurrence all behave how I'd expect. What I'm less confident about:

- **Weekly recurrence across a month boundary** — I tested daily recurrence but never ran a full week of resets in sequence. There might be an off-by-one in the `timedelta` logic I just haven't hit yet.
- **Tasks whose duration exactly equals the remaining budget** — I tested overflow but not the exact-fit case. It should work because I use `<=` in `_fits_in_time` but it deserves its own test.
- **Two tasks with the same title on the same pet** — `remove_task` filters by title so if you added "Morning walk" twice they'd both get deleted. That's probably a bug I haven't addressed.
- **Owner with no pets at all** — the UI stops you with `st.stop()` but the logic layer has no guard. Calling `generate_plan` on an empty owner returns an empty plan which is probably fine, but I haven't formally tested it.

---

## 5. Reflection

**a. What went well**

The part I'm most satisfied with is `DailyPlan.explain()`. It sounds like a small thing but the first time I ran `python3 main.py` and saw "Morning walk @ 07:00 (30 min, must-do)" instead of a list of object references it actually felt like a real app. Getting the backend to produce readable output before touching the UI made wiring up Streamlit way easier — I basically just called `plan.explain()` and `plan.display_table()` and most of the UI was done.

I'm also happy with how the tests grew naturally. I didn't plan 19 tests upfront — I just kept asking "what could go wrong" and the list built itself from there.

**b. What you would improve**

If I had another iteration I'd redesign how tasks connect to pets. Right now a `Task` has no hard reference to which pet it belongs to — you have to call `Owner.find_pet_for_task()` to trace it back. I'd add a `pet_name` field directly on `Task` so the schedule can say "Luna: Thyroid meds @ 08:00" instead of just "Thyroid meds @ 08:00."

I'd also add a real date system. Right now "today's schedule" is just whatever tasks are currently pending — there's no calendar. If I rebuilt this I'd want tasks tied to specific dates so you could plan a week ahead and see what's coming.

**c. Key takeaway**

Writing the design down in plain English before touching any code made the AI collaboration way more useful. When I had a clear opinion — like "Pet owns its tasks, not Owner" — I could give Copilot a specific direction and check its output against something concrete. When I didn't have an opinion and just asked "how should I design this" I got something technically correct but that didn't feel like mine, and I'd usually end up rewriting it anyway.

The design is the part AI can't do for you. It can write the code fast once you know what you want — but figuring out what you actually want is still your job.
