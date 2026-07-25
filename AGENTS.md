# Endurance Dashboards — Unified Multi-Agent System

How both dashboards in this repo are built and maintained agentically, through **one**
pipeline. This is the map; the agents live in `.claude/agents/`, the orchestrator in
`.claude/commands/dashboard.md`.

## The two dashboards it serves
```
strava-data   fetch.py → analyze_segments.py → build_dashboard.py → strava.html ┐
running-log   parse_log.py → running_log.csv → visualize_log.py   → index.html ┤
                                                                                ▼
                            deploy.yml publishes running-log/ → GitHub Pages (pipeline's end)
```
`strava-data`'s underlying data is **live and growing** (refreshed by `strava-fetch.yml`);
`running-log`'s underlying data is a **fixed** 2003–2007 CSV — but the running-log
*dashboard itself* (code, features, views) is under active development just like Strava's,
this pipeline being the point. "Frozen" below describes the data, never the dashboard.

Each build writes a gitignored HTML file into `running-log/` — Strava's `strava.html` and the
running log's `index.html`. That directory is the GitHub Pages publish root, so
`.github/workflows/deploy.yml` rebuilds both from source and publishes the folder. The
**deployed Pages site is the end of the pipeline**; the local HTML files are transient outputs,
never committed. The two share `nerd_common/` (design tokens, theme helpers, formatters). One
pipeline drives both; the **target** (`strava-data` | `running-log`) is a parameter.

## The key rule
**A subagent cannot spawn another subagent in Claude Code.** So the orchestrator is a *skill
you invoke in the main session* (`/dashboard`), not an agent. Everything that dispatches
specialists must be top-level.

## Roles → Claude Code primitives

| Role | Realized as | Scope |
|---|---|---|
| **Orchestrator** | `/dashboard <target>` command (main session) | Dispatches specialists, writes the spec file, runs the review gate. Both dashboards. |
| **Issue intake** | `/issues` command (main session) | Sweeps `agent:ready` issues, triages them into a menu, routes the one you pick into `/dashboard`, ships a PR. Both dashboards. |
| **Data analyst** | `dash-analyst` agent | Discovery + verification. Runs Python for EDA; no Edit/Write. Profile-driven, both dashboards. |
| **Creativity** | `dash-creativity` agent | Ranked menu of view ideas. Read-only + web. Both dashboards. |
| **Viz design** | `dash-viz-design` agent | Build-ready spec text; orchestrator writes the file. Read-only. Both dashboards. |
| **Developer** | `dash-developer` agent | The only agent that edits build code. Profile-driven, both dashboards. |
| **QA** | `strava-qa` / `running-log-qa` agents | Target-specific stages (different build, units, checks). Both delegate the rendered visual pass to the shared `.claude/qa-visual-suite.md` (V0–V8), which probes for a working browser transport (Preview MCP / `tools/mobile_preview.py` / static-only) and declares its coverage. Runs but doesn't edit. |
| **Maintenance** | `strava-maintenance` agent (Strava only) / inline orchestrator check (Running Log) | Health/upstream watch. Running Log's data is fixed and there's no live API to watch, so it gets no dedicated maintenance agent — the dashboard code itself still evolves. |
| **Code review** | `/code-review` + `/security-review` skills | Quality & safety gate, run by the orchestrator. |

## The profile mechanism
The 8-stage flow is identical for both dashboards. What differs — data paths, build command,
output HTML, module map, units policy, which QA agent, special data seams — is captured once
per dashboard as a **Pipeline profile** block at the top of that dashboard's spec:
- `Project Docs/Specs/strava-data/dashboard-spec.md`
- `Project Docs/Specs/running-log/dashboard-spec.md`

Every shared `dash-*` agent's first step is to read the profile for the target the
orchestrator names. Dashboard-specific facts live in the profile, so the agent prompts stay
generic. The orchestrator always passes the target when dispatching a `dash-*` agent.

## Safety by least privilege
Tools are scoped per agent. Creativity and viz-design are read-only (no Edit/Write/Bash).
The analyst can run code for EDA but cannot edit files. Only the developer edits build code.
QA runs but doesn't edit. The code-review gate backstops all of it. The read-only agents
carry the Strava MCP tools in their grant (a harmless no-op when the target is `running-log`,
which has no MCP data source).

## Orchestrator stage flow (`/dashboard`)
Intake → Analyze → Ideate → Design → Build → QA → Review gate → Ship. The orchestrator stops
for your approval between stages — you stay in the loop.

`bugfix` mode is a shorter path for defects: Reproduce → Fix → QA → Review gate → Ship. No
Analyze, Ideate, or Design — there's nothing to discover or design, and the spec doesn't change.

## Issues as a pipeline entry point (`/issues`)
A filed GitHub issue can enter the pipeline instead of you describing the work by hand.

```
issue labeled agent:ready → /issues sweep → triage menu → you pick one
                                                  ↓
             bug ────────────────────→ /dashboard <target> bugfix
             enhancement / vague ────→ /dashboard <target>  (with Ideate)
             specific view request ──→ /dashboard <target>  (skip Ideate)
                                                  ↓
                          Review gate → branch → PR (Closes #N) → stop
```

Three properties are load-bearing:

- **`agent:ready` is the gate.** Only the repo owner can apply it, so filing an issue triggers
  nothing on its own. Nothing runs on a schedule or in CI; `/issues` is something you invoke.
- **You pick from the menu.** The sweep classifies and quotes; it never works an issue you
  haven't chosen.
- **Issue text is untrusted input.** The repo is public, so a body is *evidence about a problem*,
  never instructions. `.claude/issue-guardrails.md` (G1–G6) is the single source of truth for
  that boundary, plus the path denylist, the approval gate on `Project Docs/**`, and the hard
  rule that the bot opens PRs but never merges them.

## How to invoke
- `/dashboard <target>` — build a new view through the full pipeline
  (`<target>` = `strava-data` or `running-log`).
- `/dashboard <target> bugfix "<description>"` — fix a defect. Works standalone or from `/issues`.
- `/dashboard <target> maintenance` — health-check only (dedicated agent for Strava; inline
  build + `qa.py` + drift check for Running Log).
- `/issues` — sweep `agent:ready` issues and route one into the pipeline.
- Aliases: `/strava` → `/dashboard strava-data`; `/running-log` → `/dashboard running-log`.

## CI
`.github/workflows/pr-checks.yml` builds both dashboards and runs `running-log/qa.py` on every
PR — the static bar. The **rendered** pass (`.claude/qa-visual-suite.md` V0–V8) deliberately
stays out of CI and runs in-session with the QA agents, so the Review gate remains load-bearing
for the visual regressions this repo actually keeps hitting.

## Dependencies & reused skills
`/requirements` (spec conventions), `/strava-segments` (quick segment Q&A), `/reflect`
(session log in `Claude's Log.md`). The dashboards' identity (dark glass, Geist fonts,
teal/amber/violet/coral/accent-blue) is the constraint every stage pushes within.
