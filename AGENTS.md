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
| **Data analyst** | `dash-analyst` agent | Discovery + verification. Runs Python for EDA; no Edit/Write. Profile-driven, both dashboards. |
| **Creativity** | `dash-creativity` agent | Ranked menu of view ideas. Read-only + web. Both dashboards. |
| **Viz design** | `dash-viz-design` agent | Build-ready spec text; orchestrator writes the file. Read-only. Both dashboards. |
| **Developer** | `dash-developer` agent | The only agent that edits build code. Profile-driven, both dashboards. |
| **QA** | `strava-qa` / `running-log-qa` agents | Target-specific stages (different build, units, checks). Both delegate the rendered visual pass to the shared `.claude/qa-visual-suite.md` (V0–V8). Runs but doesn't edit. |
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

## How to invoke
- `/dashboard <target>` — build a new view through the full pipeline
  (`<target>` = `strava-data` or `running-log`).
- `/dashboard <target> maintenance` — health-check only (dedicated agent for Strava; inline
  build + `qa.py` + drift check for Running Log).
- Aliases: `/strava` → `/dashboard strava-data`; `/running-log` → `/dashboard running-log`.

## Dependencies & reused skills
`/requirements` (spec conventions), `/strava-segments` (quick segment Q&A), `/reflect`
(session log in `Claude's Log.md`). The dashboards' identity (dark glass, Geist fonts,
teal/amber/violet/coral/accent-blue) is the constraint every stage pushes within.
