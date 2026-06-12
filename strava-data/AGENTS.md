# Strava Dashboard — Multi-Agent System

How this project is built and maintained agentically. This is the map; the agents live in
`.claude/agents/` and the orchestrator in `.claude/commands/strava.md`.

## The pipeline it serves
```
fetch.py  →  analyze_segments.py  →  build_dashboard.py  →  strava-data/strava.html
(Strava API)  (segment rollups)      (Plotly charts)        └→ Running Log/strava.html → deploy (.github/workflows/deploy.yml)
```

## Roles → Claude Code primitives

| Role | Realized as | Notes |
|---|---|---|
| **Orchestrator** | Skill `/strava` (runs in the main session) | Dispatches the specialists. Must be top-level — see the key rule below. |
| **Maintenance** | `strava-maintenance` agent | Breakage + upstream + dep/code health. Read-only + web research; proposes, never fixes. |
| **Data analyst** | `strava-data-analyst` agent | Discovery (what's interesting) + verification (transform recipe). Runs Python for EDA; no Edit/Write. |
| **Creativity** | `strava-creativity` agent | Ranked menu of view ideas. Read-only + web. |
| **Viz design** | `strava-viz-design` agent | Build-ready spec. Read-only; returns spec text, orchestrator writes the file. Uses the `frontend-design` skill. |
| **Developer** | `strava-developer` agent | The only agent that edits `build_dashboard.py`. |
| **QA** | `strava-qa` agent | Build/spec/data/edge/HTML + visual smoke test (Preview MCP). Runs but doesn't edit. |
| **Code review** | `/code-review` + `/security-review` skills | Quality & safety gate, run by the orchestrator. No agent file. |

## The key rule
**A subagent cannot spawn another subagent in Claude Code.** So the orchestrator is a *skill
you invoke in the main session*, not an agent. Everything that dispatches specialists must be
top-level.

## Safety by least privilege
Tools are scoped per agent. Creativity and viz-design are read-only (no Edit/Write/Bash). The
analyst can run code for EDA but cannot edit files. Only the developer edits build code. QA
runs but doesn't edit. The code-review gate backstops all of it.

## Orchestrator stage flow (`/strava`)
Intake → Analyze → Ideate → Design → Build → QA → Review gate → Ship. The orchestrator stops
for your approval between stages — you stay in the loop.

## How to invoke
- `/strava` — build a new view through the full pipeline.
- `/strava maintenance` — run just the health-check agent.

## Dependency
Enable the official **frontend-design** plugin via `/plugin` so the ideation agents can use
its aesthetic guidance (it's already in the local marketplace cache). The dashboard's identity
(dark glass, Geist fonts, teal/amber/slate/violet) is the constraint the skill pushes within.

## Reused skills
`/requirements` (spec conventions), `/strava-segments` (quick segment Q&A), `/reflect`
(session log in `Claude's Log.md`).
