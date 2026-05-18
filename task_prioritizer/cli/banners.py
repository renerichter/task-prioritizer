"""Static banner / help-text constants used by the CLI."""

HELP_EPILOG = """
╭─────────────────────────────────────────────────────────────╮
│  "calculations" = choosing what to work on                  │
│  "stop-rule"    = knowing when to stop, when good enough is │
│                   good enough                               │
╰─────────────────────────────────────────────────────────────╯

Phase 1: Capture tasks roughly. Uncertainty (🎁) is expected.
Phase 2: Refine estimates. Remove 🎁 as clarity emerges.

Stop-Rule: If actual time exceeds 1.5× your estimate, pause.
           Reflect on why—then adjust your next estimate.

    Ratings order: L,Conf,G,P,D,C,T,R,F,S,Pl,Rec
      L=Leverage, Conf=Confidence, G=Goals, P=Priority, D=Deadline,
      C=Complex, T=Time, R=Risk, F=Fun, S=Surprise, Pl=Planned,
      Rec=Recurrent

    This tool trusts you. You're doing fine.
    """

SURPRISE_REMINDER = """
    ┌─────────────────────────────────────────────────────────────┐
    │  🎁 appears when clarity is low.                            │
    │     In phase 1, this is natural.                            │
    │     As you learn, 🎁 fades.                                  │
    │     Trust the process.                                       │
    └─────────────────────────────────────────────────────────────┘
    """

VERSION = "0.2.12"
AUTHOR = "Task Prioritizer Contributors"

STARTUP_BANNER = """
    ╭─────────────────────────────────────────────────────────────╮
    │                                                             │
    │   Task Prioritizer 🌱  v{version}                            │
    │   A calm tool for mindful productivity                      │
    │                                                             │
    │   Choose what to work on │ Know when to stop                │
    │                                                             │
    ╰─────────────────────────────────────────────────────────────╯

    WHY THIS WORKS:
    ───────────────
    • High Impact + Low Execution  = Quick wins (do first)
    • High Impact + High Execution = Strategic investments (schedule)
    • Low Impact + Low Execution   = Delegate or batch
    • Low Impact + High Execution  = Avoid or eliminate

    SYMBOLS AT A GLANCE:
    ────────────────────
      ⭐️⭐️⭐️ = High impact       🚨 = Urgent          🥵 = Hard
      ⭐️⭐️   = Medium impact     🐢 = Calm            🍭 = Easy
      ⭐️     = Low impact        🎁 = Unclear (ok!)   🗓️ = Planned
                                  🎲 = Spontaneous     🔁 = Recurrent

    SCALE: 0=none │ 1=low │ 2=medium │ 3=high
    """

WELCOME_MESSAGE = """
╭─────────────────────────────────────────────────────────────╮
│                                                             │
│   Welcome to Task Prioritizer 🌱                            │
│                                                             │
│   This tool helps you:                                      │
│   • Choose what to work on (by scoring impact & effort)     │
│   • Know when to stop (the 1.5× stop-rule)                  │
│                                                             │
│   How it works:                                             │
│   1. You'll rate each factor from 0 to 3                    │
│   2. The tool calculates priority and shows symbols         │
│   3. Copy the result to your task list                      │
│                                                             │
│   Scale: 0=none, 1=low, 2=medium, 3=high                    │
│                                                             │
│   When 🎁 appears, that's okay—it means the task is         │
│   still unclear. Clarity comes with time.                   │
│                                                             │
│   Let's try your first task...                              │
│                                                             │
╰─────────────────────────────────────────────────────────────╯
"""

LOOP_HELP = """
╭─────────────────────────────────────────────────────────────╮
│  Quick Reference                                            │
├─────────────────────────────────────────────────────────────┤
│  Enter a task string to prioritize it.                      │
│                                                             │
│  Commands (type / for menu):                                │
│    /help, /h          Show this help                        │
│    /mode batch, /m b  Switch to batch mode (grouped input)  │
│    /mode detail, /m d Switch to detail mode (explanations)  │
│    /abbr              Show abbreviations vocabulary         │
│    /quit, /q          Exit the program                      │
│    Ctrl+C/D           Exit the program                      │
│                                                             │
│  Task format:                                               │
│    {p0:45} task description   (45 min planned time)         │
│    {P:Tag} task description   (custom tag preserved)        │
│                                                             │
│  Rating scale: 0=none, 1=low, 2=medium, 3=high              │
│                                                             │
│  Categories:                                                │
│    Impact    (L,Conf,G)  - Leverage, Confidence, Goals      │
│    Urgency   (P,D)       - Priority, Deadline               │
│    Execution (C,T,R,F)   - Complex, Time, Risk, Fun         │
│    Clarity   (S,Pl)      - Surprise, Planned                │
╰─────────────────────────────────────────────────────────────╯
"""

DETAIL_EXPLANATION = """
╭─────────────────────────────────────────────────────────────╮
│  Understanding the Rating System                            │
╰─────────────────────────────────────────────────────────────╯

This prioritization system scores tasks across 4 categories to help
you identify what truly matters and how much effort it requires.

┌─ IMPACT ─────────────────────────────────────────────────────┐
│  Measures the value and return on investment of the task.   │
│                                                              │
│  • Leverage (L): How much output per unit of input?          │
│    0=no leverage, 3=massive multiplier effect                │
│    Ask: "Will this make future work easier?"                 │
│                                                              │
│  • Confidence (Conf): How sure are you it will work?         │
│    0=pure guess, 3=proven approach                           │
│    Ask: "Have I done this before? Is the path clear?"        │
│                                                              │
│  • Goals (G): How aligned with your objectives?              │
│    0=off-track, 3=directly advances key goal                 │
│    Ask: "Does this move the needle on what matters?"         │
└──────────────────────────────────────────────────────────────┘

┌─ URGENCY ────────────────────────────────────────────────────┐
│  Measures time pressure and external constraints.            │
│                                                              │
│  • Priority (P): How important relative to other tasks?      │
│    0=can wait indefinitely, 3=must do before anything else   │
│    Ask: "What happens if I don't do this today?"             │
│                                                              │
│  • Deadline (D): How close is the due date?                  │
│    0=no deadline, 3=due today/overdue                        │
│    Ask: "When does this absolutely need to be done?"         │
└──────────────────────────────────────────────────────────────┘

┌─ EXECUTION ──────────────────────────────────────────────────┐
│  Measures effort, friction, and resistance.                  │
│                                                              │
│  • Complexity (C): How mentally demanding?                   │
│    0=trivial, 3=requires deep focus and expertise            │
│    Ask: "Will I need to think hard or can I autopilot?"      │
│                                                              │
│  • Time (T): How long will it take?                          │
│    0=<30min, 1=30-90min, 2=90-150min, 3=>150min              │
│    (Auto-filled if you provide {pH:MM} tag)                  │
│    (If auto-estimated, result rounds up to nearest 5m)       │
│                                                              │
│  • Risk (R): What can go wrong?                              │
│    0=safe, 3=high chance of blockers or failure              │
│    Ask: "Are there unknowns that could derail this?"         │
│                                                              │
│  • Fun (F): How enjoyable is this task?                      │
│    0=dread it, 3=looking forward to it                       │
│    (Higher fun = easier execution, less procrastination)     │
└──────────────────────────────────────────────────────────────┘

┌─ CLARITY ────────────────────────────────────────────────────┐
│  Measures how well-defined the task is.                      │
│                                                              │
│  • Surprise (S): How much uncertainty remains?               │
│    0=fully understood, 3=many unknowns (🎁 appears)          │
│    Ask: "Do I know exactly what 'done' looks like?"          │
│                                                              │
│  • Planned (Pl): Was this scheduled or spontaneous?          │
│    0=just popped up, 3=on the roadmap for weeks              │
│    Ask: "Did I decide to do this, or did it decide for me?"  │
└──────────────────────────────────────────────────────────────┘

WHY THIS WORKS:
───────────────
• High Impact + Low Execution = Quick wins (do first)
• High Impact + High Execution = Strategic investments (schedule)
• Low Impact + Low Execution = Delegate or batch
• Low Impact + High Execution = Avoid or eliminate

The symbols help you scan your task list at a glance:
  ⭐️⭐️⭐️ = High impact, prioritize this
  🚨 = Urgent, time-sensitive
  🐢 = Calm, no rush
  🥵 = Hard, high friction
  🍭 = Easy, low friction
  🎁 = Unclear, refine later (normal in Phase 1)
  🗓️ = Planned work
  🎲 = Spontaneous/reactive

"""

DETAIL_EXAMPLES = """
╭─────────────────────────────────────────────────────────────╮
│  Examples                                                   │
╰─────────────────────────────────────────────────────────────╯

┌─ EXAMPLE A: High Priority Task ──────────────────────────────┐
│                                                              │
│  Input: "{p1:30} prepare quarterly presentation"             │
│                                                              │
│  Ratings:                                                    │
│    Impact:    L=3, Conf=2, G=3  (high leverage, aligns well) │
│    Urgency:   P=3, D=3          (due today, top priority)    │
│    Execution: C=2, T=_, R=1, F=1 (moderate effort)           │
│    Clarity:   S=0, Pl=3         (well-planned, clear scope)  │
│                                                              │
│  Output: ⭐️⭐️⭐️--🗓️{p1:30} prepare quarterly presentation  │
│  Category: 🚨 & 🥵 (urgent and demanding)                    │
│                                                              │
│  → This gets three stars (high impact), scheduled symbol,    │
│    and shows as urgent. Do this first.                       │
└──────────────────────────────────────────────────────────────┘

┌─ EXAMPLE B: Low Priority Task ───────────────────────────────┐
│                                                              │
│  Input: "reorganize desktop files"                           │
│                                                              │
│  Ratings:                                                    │
│    Impact:    L=0, Conf=3, G=0  (no leverage, off-goal)      │
│    Urgency:   P=0, D=0          (no deadline, low priority)  │
│    Execution: C=0, T=1, R=0, F=1 (easy but not fun)          │
│    Clarity:   S=2, Pl=0         (vague scope, unplanned)     │
│                                                              │
│  Output: 🎁--🎲 reorganize desktop files                     │
│  Category: 🐢 & 🍭 (calm and easy)                           │
│  Estimated time: ~58 min (auto-calculated)                   │
│                                                              │
│  → No stars (low impact), surprise symbol (unclear scope),   │
│    spontaneous. You might feel like doing this, but the      │
│    system correctly identifies it as low-value busywork.     │
│    Either clarify scope or skip it entirely.                 │
└──────────────────────────────────────────────────────────────┘
"""
