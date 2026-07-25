# Session Retrospective: QA Agent Consolidation

**Date:** 25 July 2026
**Scope of the session this reflects on:** `Project Docs/Plans/qa-agent-consolidation.md` Phases
1–4 (shared visual suite, environment-adaptive transport, four new checks, the
`applyChartTheme` fix), then a deliberately blind `strava-qa` validation run, then this
retrospective. Technical findings from that validation run are banked separately in
`Project Docs/Handoffs/qa-pipeline-test-run-findings.md` — this document is about *process*:
what to take away for prompting and planning next time, not what to fix in the dashboards.

---

## What went well

- **The plan held up structurally.** Four phases of implementation, and none required backing
  out and re-architecting — every self-correction below was tactical, inside a phase, not "the
  approach was wrong." The transport ladder, the shared-suite-file split, the stable check IDs —
  all survived intact from the approved plan to the shipped code.
- **Every claim was checked against evidence, not asserted.** Byte-diffs proved the JS extraction
  was lossless; bug-injection tests forced each new check to actually fire, then got reverted;
  before/after screenshots confirmed the theme fix. That discipline is what caught
  `applyChartTheme` being a complete no-op on both dashboards — the single most valuable find of
  the whole effort — before it went unnoticed indefinitely.
- **The blind test run was a good idea and it worked as designed.** Dispatching `strava-qa` with
  no mention of the three already-known findings, specifically to see whether the rebuilt suite
  would surface them independently, is a genuine validation methodology — not just re-confirming
  what was already known. It rediscovered all three, plus two tooling bugs and one systemic
  dashboard defect nobody asked it to look for.

## Self-corrections: two different things that look the same from outside

A lot of visible mid-session correction happened, concentrated in the phase that wrote four new
detection heuristics against real chart data. Worth separating what caused it, because the two
categories have very different implications for what would have prevented them.

### Empirical calibration — not a planning gap

Some corrections could not have been avoided by better upfront planning, because they're
inherent to building measurement heuristics against real, messy data:

- The plot-area-fill threshold was guessed at 0.70, then real chart data across both dashboards
  showed typical mobile charts sit at 0.59–0.76 — recalibrated to 0.55 based on the actual
  distribution, not a better guess.
- The rotation-aware tick-collision model (measuring the perpendicular gap between rotated
  baselines instead of bounding-box overlap) was only discoverable by testing against an actually
  rotated axis and seeing the naive model call it a 52% overlap when it read perfectly.

No plan document operates at the altitude of "here is the exact false-positive shape of a
bounding-box test against 30°-rotated SVG text." Seeing this class of correction happen live is a
sign the process was appropriately test-driven — build the check, run it against the real
dashboard, see what it says, fix what's wrong — not a sign the plan should have been more
detailed.

### Avoidable oversights — on execution, not on the plan or the prompting

A few corrections genuinely could have been caught earlier with more careful thinking before
writing code:

- A new axis-range check initially flagged running-log's five PR charts as broken, because they
  deliberately pin a shared x-axis range (`_PR_X_RANGE`) wider than any single chart's own data —
  a convention already documented in the running-log spec that had been read earlier in the
  **same session**. The detector wasn't cross-referenced against it before being written.
- A divide-by-zero guard (`Math.max(1, span)`) silently corrupted the measurement on one chart
  with a sub-unit axis range — a numeric edge case that should have been thought through, not
  discovered via calibration testing.
- A tap-target check initially flagged every desktop toolbar button as "too small" — an obvious
  device-scoping miss (mouse vs. touch) that a moment's thought before writing the check would
  have caught.

**The actionable lesson from this half:** for a batch of related detector/validator code, it
helps to explicitly request a discrete step — *"before implementing each check, list what it
must NOT flag, against already-documented conventions"* — rather than leaving that cross-check
implicit. That single step would have caught the pinned-axis issue specifically, and is a cheap
habit to make standard for this class of work.

## Where user input mattered most

The single highest-leverage moment in the whole session was a one-sentence correction **before
Phase 1 even started**: the initial framing was "the Preview MCP transport is dead here, make
`mobile_preview.py` primary" — the correction was that the real situation is several different
working environments (local desktop, mobile app, web/remote containers) with genuinely different
capabilities, and what was needed was detection and adaptation, not picking a favorite tool and
demoting the other.

That's a **framing** correction, not an implementation correction, and framing errors compound
across everything built on top of them. If Phase 3 had shipped with "`mobile_preview.py` is
primary, Preview MCP is optional," every later phase — the reporting contract, the per-check
transport-preference table, the coverage-loss language — would have inherited that wrong
assumption, and unwinding it later would have meant re-touching all four phases instead of one
sentence at the start.

**The general principle:** when reviewing a plan before implementation starts, the highest-value
thing to check for is whether the framing/assumptions are right, not whether the implementation
detail is complete — implementation-level issues (like the empirical-calibration items above)
get caught by testing regardless of how carefully the plan was worded, but a wrong frame doesn't
get caught by testing at all; it gets caught by someone asking "wait, is that actually true?"

## On the long clock time

Two factors, roughly equal weight, and worth distinguishing because they call for different
responses next time.

### Model selection

This session ran on **Opus 5** for nearly its entire length — an explicit "the model has been
changed to Sonnet 5" system message appeared only near the very end, which implies a different
model was active before that point, and is consistent with every commit message written up to
then. Opus is a larger, more deliberately-reasoning model — slower per token by design, in
exchange for depth. Combined with a task this iterative (many small verification round-trips),
that compounds significantly. This is very likely the single biggest driver of the session's
length, ahead of any execution inefficiency below.

**Takeaway:** match the model to the phase. The heavier model earns its cost during plan review
and architectural decisions — exactly the kind of framing check described above. Once past
planning and into high-volume iterative implementation and testing, a faster model trades some
per-step depth for a lot less wall-clock time, and the iterative work in this session (calibrate
a threshold, run it, adjust, run it again) doesn't obviously need Opus-level deliberation per
step. Consider switching deliberately at that transition rather than by coincidence, as happened
here.

### Execution overhead

`tools/mobile_preview.py` launches a fresh Chromium process on **every single invocation** —
there's no persistent browser or server across calls. Dozens of individual invocations were run
across the session testing one check against one chart/tab/theme/viewport combination at a time,
frequently in serial shell loops rather than batching several measurements into a single browser
session. A tighter design would run several checks per page load instead of relaunching the
browser per check — this did happen partway through (the later "sweep" scripts), but not from the
start.

Separately, the dispatched `strava-qa` subagent for the blind validation run — the right call for
genuine isolation — was not free: it took **~30 minutes and 91 tool calls** to sweep two tabs at
two viewports and two themes. That's an appropriate cost for real validation rigor, but worth
naming explicitly as a dial: if a faster sanity check is wanted instead of a rigorous blind
validation next time, say so — dispatching a fresh subagent always re-derives context from
scratch and pays real overhead for the isolation it buys.

## Actionable takeaways

- **Match the model to the phase.** Heavier model for plan review and architectural framing
  checks; switch to a faster model once past planning and into high-volume iterative
  implementation/testing.
- **Spend plan-review attention on framings and assumptions, not implementation completeness.**
  One sentence catching a wrong frame is worth more than an hour of implementation-level review —
  implementation bugs surface via testing regardless; framing bugs don't.
- **For batches of related detectors/validators, explicitly request a "what must this NOT flag"
  pass against documented conventions before implementation.** Cheap, and would have prevented at
  least one real correction here.
- **Dispatching an isolated subagent for validation has a real cost, not just a benefit.** It's
  worth it for genuine blind-test rigor; if speed matters more than isolation, ask for the faster
  path explicitly instead of defaulting to a fresh dispatch.
