# QA Agent Consolidation — Shared Visual Suite + Mobile Check Hardening

**Status:** Planned
**Scope:** Consolidate `strava-qa` / `running-log-qa` onto one rendered-check suite, close four
mobile-QA gaps, and make the browser transport environment-adaptive
**Effort:** ~1–1.5 days, phased (each phase lands independently)

## Context

The `/dashboard <target>` pipeline was unified across both dashboards, but QA was left as two
independent agents — `.claude/agents/strava-qa.md` (383 lines) and
`.claude/agents/running-log-qa.md` (304 lines). Roughly **200 lines of embedded JavaScript are
byte-for-byte identical** between them (label-overlap, edge-clipping, theme-contrast), and they
have **already drifted**: `strava-qa` gained a width-fill check (§6.5c) the running-log agent
never got, and `running-log-qa` gained the "Preview MCP can't reach a local server here, fall
back to `tools/mobile_preview.py`" note that `strava-qa` never got.

That second divergence is the more consequential one, and it is **not** simply a missing note.
This repo is worked on from several Claude Code environments — local desktop, the mobile app,
web/remote-control containers — and browser tooling differs in each: Preview MCP is provisioned
in some and not others, and where it is provisioned it cannot always reach a local
`http.server` (on the desktop machine its Chromium lands on `chrome-error://`, which is why
`tools/mobile_preview.py` exists). Playwright plus a resolvable Chromium is likewise present in
some environments and absent in others. Today each agent hardcodes a single assumption about
which of these is available — `strava-qa` assumes Preview MCP, `running-log-qa` assumes Preview
MCP with a `mobile_preview.py` fallback — so in any environment whose capabilities don't match
that assumption, the agent silently produces a thinner report without saying so. **The fix is a
transport layer that probes what is actually available and reports which one it used**, not a
new hardcoded default.

Auditing both agents against the four mobile criteria that motivated this work found that
**none of the four is fully covered by either agent**:

| # | Criterion | Status today |
|---|---|---|
| 1 | Labels don't overlap other elements | **Partial (both).** The overlap scan's label set is only `.legend` + `.infolayer .annotation`. Tick labels are absent, so crowded/rotated mobile x-ticks colliding with each other or with the axis title are invisible. |
| 2 | Elements don't overlap in general | **Missing (both).** No DOM-level check exists; scope stops inside each `.js-plotly-plot`. Card vs card, theme toggle vs wordmark, bottom sheet vs content are never tested. |
| 3 | Datatips carrying dark-mode color into light mode | **Missing (both).** Neither agent ever hovers, so `.hoverlayer .hovertext` never exists during the audit. Worse, contrast is the wrong instrument: light text on a leftover dark pill scores *high* contrast and passes. |
| 4 | Whitespace / axes spanning full mobile width | **Partial (strava only).** §6.5c measures the **figure** vs its card. It does not measure the **plot area**, so the autorange blowout documented 3× in `CLAUDE.md` (data crushed into the left ~60%) leaves `fillPct` at 100% and passes clean. Neither agent reads `_fullLayout.xaxis.range`, though `mobile_preview.py`'s `MEASURE_JS` already returns it. |

A related latent defect: running-log's `applyChartTheme()`
(`running-log/dashboard/template.py:1483`) patches only `xaxis`/`yaxis` and skips subplot axes,
annotation recoloring, and `title.font.color` — all three of which Strava's version handles
(`strava-data/dashboard/template.py:1084`). It does not bite today (running-log currently has
zero annotations, zero subplots, and passes no `title` to `tidy_dark` — verified), but the next
view that adds any of them renders dark-on-white in light mode, and per criterion 3 no QA check
would catch it.

**Outcome sought:** one source of truth for the rendered checks, all four criteria genuinely
covered, a transport layer that adapts to whichever environment the pipeline is run from and
says what it could and couldn't verify, and the theme-coverage gap closed before a new view
trips it.

## Decisions taken

1. **Shared suite file**, not a merged agent and not copy-paste. Both agents keep their names and
   target-specific stages; the rendered layer moves to one file they both `Read`. Mirrors the
   existing profile mechanism (`AGENTS.md`: "dashboard-specific facts live in the profile, so the
   agent prompts stay generic"). The orchestrator (`dashboard.md`) and both spec profile blocks
   need **no** changes — `strava-qa` / `running-log-qa` remain the dispatched names.
2. **All four new checks** are in scope.
3. **An environment-adaptive transport layer.** Check JS moves out of markdown into versioned
   `.js` files under `tools/qa-checks/` — which is what makes this possible, since the same file
   can be fed to Preview MCP's `preview_eval` or Playwright's `page.evaluate` unchanged. The
   suite probes which transports are live, uses the best available (and *both*, where each is
   stronger at different checks), and declares the transport and any resulting coverage loss in
   the report.
4. **The `applyChartTheme()` gap is fixed**, in a clearly scoped section.

Out of scope: merging `running-log/qa.py` with anything Strava-side. The static QA scripts stay
separate; Strava has none and does not gain one here.

---

## Phase 1 — Extract the shared visual suite

**New file: `.claude/qa-visual-suite.md`** (agent-facing config, so `.claude/`, not
`Project Docs/`). Claude Code does not auto-load arbitrary `.claude/*.md`, so it stays inert
until an agent reads it — which is what we want.

Give the suite **its own stable check IDs (V0–V8)** rather than inheriting either agent's
numbering. Today the same check is `§6.5` in one agent and `§3.5` in the other; stable IDs end
that mismatch and make report tables comparable across dashboards.

Content, lifted verbatim from the current agents except where noted:

| ID | Check | Source |
|---|---|---|
| V0 | **Transport probe** + viewport sweep contract (settle timings, tab activation, visible-chart filter) | new, replacing both agents' hardcoded transport assumptions — see Phase 3 |
| V1 | Render smoke + console errors | both |
| V2 | Label-overlap (label-vs-data, label-vs-label) | identical in both; **extended in Phase 2** |
| V3 | Edge-clipping / truncation vs `svg.main-svg` | identical in both |
| V4 | Width-fill / under-fill (figure vs card) | `strava-qa` §6.5c — **this is the check running-log is missing** |
| V5 | Theme contrast audit, light + dark | identical in both; **extended in Phase 2** |
| V6 | Axis-range blowout + plot-area fill | **new** (Phase 2) |
| V7 | Hover/datatip theme-mismatch | **new** (Phase 2) |
| V8 | General DOM element overlap | **new** (Phase 2) |

Preserve both agents' hard-won caveats in the shared text — they are the lessons-learned this
work is meant to retain:

- V2's **leader/connector-line false positive** rule (re-run markers-only when a `CHECK` is
  driven by `.js-line` hits). Keep Strava's concrete PCA-biplot example *and* running-log's
  "sparklines / calendars / heatmaps → N/A" note; they are complementary, not redundant.
- V2's **"outside the plot area is fine, outside the figure is a defect"** distinction — Strava's
  phrasing is the sharper of the two; use it.
- V3's **subplot-titles-count** note, including the `tidy_dark` `t=20` default being tight for a
  size-16 title.
- V5's **semi-transparent pill** caveat (computed contrast is approximate; confirm borderline
  cases on a screenshot before failing).

**Parameterization.** The suite must not hardcode either dashboard's tabs or chart ids. Each QA
agent passes a small block when it invokes the suite:

```
target:      strava-data | running-log
page:        /strava.html | /index.html
tabs:        overview, volume, trends, segments, map, exploratory
             | overview, volume, mix, performance, races, patterns
chart ids:   (strava) enumerate from the built page
             (running-log) CHART_IDS in running-log/qa.py
exempt:      charts with no cartesian axis/legend — donuts, sparklines,
             heatmaps, calendars, maps — skip V6 axis checks, keep V4/V8
```

**Then trim both agent files** to their target-specific stages plus a dispatch line:

- `strava-qa.md` keeps §1 build integrity, §2 spec compliance, §2.5 units policy, §3 data
  spot-checks, §4 edge cases, §5 HTML sanity. Its §6/§6.0/§6.5/§6.5b/§6.5c/§6.6 are replaced by
  a §6 that reads the suite and supplies the parameter block above. Keeps its own mobile
  checklist bullets (rangeslider hidden on mobile, bottom sheet).
- `running-log-qa.md` keeps §1 build integrity and §2 `qa.py`. Its §3.x are replaced the same
  way. **Keeps its richer mobile checklist** — ≥40px tap targets named by selector (`.tab`,
  `.hm-toggle`, `.race-tab`, `.theme-toggle button`), spark-card stacking, `#detail-panel`
  bottom sheet with drag handle, and the heatmap (`.hm-month`/`.hm-dow`) + detail-panel
  legibility check. These are genuinely target-specific UI and should not be flattened into the
  shared file.

Net effect: each agent drops to roughly 120–160 lines, and the ~200 duplicated JS lines exist
once.

## Phase 2 — The four new checks

Each becomes a versioned file in **`tools/qa-checks/`**, referenced by the suite. All are
`async () => {...}` expressions so they can drive their own tab iteration —
`mobile_preview.py --eval` routes through Playwright's `page.evaluate`, which awaits a returned
promise.

**V6 — axis-range blowout + plot-area fill** *(criterion 4; the highest-value check)*
`tools/qa-checks/axis-fill.js`. For each visible chart, compute the true data extent from
`el.data` (min/max plotted x across traces) and compare against `el._fullLayout.xaxis.range`.
FAIL when the range overruns the data by more than tolerance — for a date axis, end more than
~10–15% of the span past the last point; for a category axis, outside `[-0.5, ncats-0.5] ± ε`.
This is precisely the failure `CLAUDE.md` records for the running-log pace chart (2003–2007
stretched to ~2010) and Strava's Seasonal Handoff (`[-0.5, 11.5]` → `[-0.5, 17.35]`).
Second half: read `_fullLayout._size` (`l`/`r`/`t`/`b`) and WARN when the plot area is under
~70% of figure width at 390px — margins eating mobile space. `MEASURE_JS` in `mobile_preview.py`
already returns both `xRange` and `size`; reuse its shape rather than inventing a new one.
Also assert `_fullLayout.showlegend` where a legend is expected — the stale-`simplify()`
failure from the Performance redesign.

**V7 — hover/datatip theme mismatch** *(criterion 3)*
`tools/qa-checks/hover-theme.js`. Trigger hover **programmatically** via
`Plotly.Fx.hover(el, {xval, yval}, 'xy')` rather than a synthetic mouse event — Plotly listens on
its drag layer and a dispatched `mousemove` is unreliable, especially under the mobile-emulated
context (`has_touch=True`). Then read `.hoverlayer .hovertext` and check its `path`/`rect` fill
**as a luminance comparison against the page background**, not as a contrast ratio: in light
mode a hover pill whose background is darker than the page is a FAIL regardless of how legible
its text is. Run in both themes. Also apply the same luminance-inversion test to annotation
pills (`rect.bg`) and chart titles, which have the identical failure mode and which the existing
contrast audit likewise waves through.

**V2 extension — tick-label overlap** *(criterion 1)*
Add `.xtick text`, `.ytick text`, and the axis-title groups (`.g-xtitle`, `.g-ytitle`) to the
`labels` array in the existing overlap scan. Report tick-vs-tick and tick-vs-axis-title
collisions as their own row kind so they don't drown the legend/annotation signal. Expect this
to be noisiest at 390px — that is the point; it is what `thinTicks()`/`DENSE` exist to prevent
and nothing currently verifies the result.

**V8 — general DOM element overlap** *(criterion 2)*
`tools/qa-checks/dom-overlap.js`. A page-level pass outside the Plotly SVGs: bounding-box
intersection across visible chrome (`.card`, stat tiles, `.tab` strip, `.theme-toggle`, PR/race
cards, `#detail-panel` when open), plus a horizontal-overflow assertion
(`document.documentElement.scrollWidth <= innerWidth + 2`). Ignore legitimate nesting
(ancestor/descendant pairs) and deliberately stacked overlays (backdrop, open sheet) via an
allowlist so the check stays actionable.

## Phase 3 — Environment-adaptive transport layer

The checks are transport-agnostic by construction: each is a JS expression returning JSON, so it
runs identically under Preview MCP's `preview_eval` and Playwright's `page.evaluate`. Storing
them as `.js` files (Phase 2) is what lets one definition serve every backend — the agent either
passes `--eval @tools/qa-checks/foo.js` to the script, or `Read`s the file and hands its contents
to `preview_eval`.

### The three transports

| | Transport | Requires | Strengths | Blind spots |
|---|---|---|---|---|
| **T1** | Preview MCP (`mcp__Claude_Preview__preview_*`) | the MCP provisioned **and** able to reach the served page | `preview_snapshot` accessibility tree, `preview_click` real interaction, `preview_console_logs`, screenshots | resize only — no true mobile emulation (no touch, DPR 1), so tap-target and touch-affordance checks are approximations |
| **T2** | `tools/mobile_preview.py` (in-process server + Playwright) | Bash, Playwright, a resolvable Chromium, network egress for the plotly CDN | real device emulation (`is_mobile`, `has_touch`, `device_scale_factor=2`), precise geometry, deterministic settle control, screenshots | no accessibility tree; each run is a fresh process |
| **T3** | Static only | nothing beyond `Read`/`Grep`/`Bash` | always available; `running-log/qa.py`, the units grep, HTML sanity | cannot see rendered geometry at all — **V2–V8 are unavailable** |

### The probe (V0)

Order the probe by cost and by what fails loudest, and cache the verdict for the whole run:

1. **Probe T2** — `uv run python tools/mobile_preview.py --eval 'document.title'`. A returned
   title means T2 is live. Two distinguishable failures: a Playwright/Chromium import or launch
   error means T2 is unavailable; a `warning: window.Plotly never appeared` in the report means
   the browser works but the CDN is blocked (sandboxed run) — retry un-sandboxed before
   giving up, since charts cannot render without it.
2. **Probe T1** — `preview_start` on the page, then confirm the resulting URL is not
   `chrome-error://` and a screenshot is non-blank.
3. If neither, **T3**.

### Using them together

Where both T1 and T2 are live, do not pick one — split by strength, because that is where the
information gain is:

| Check | Preferred | Rationale / degraded behavior |
|---|---|---|
| V1 render + console errors | T1 | `preview_console_logs` is richer than scraping; under T2 collect `console` events instead |
| V2 label/tick overlap, V3 edge-clip, V4 width-fill, V6 axis-range | **T2** | pure geometry; needs the exact DPR and emulated width to be trustworthy. Runs on T1 if that is all there is — flag results as *resize-emulated*, since a DPR-1 resize can shift text metrics |
| V5 contrast, V7 hover/datatip theme | either | both read computed style; V7's `Plotly.Fx.hover()` call works on both |
| V8 DOM overlap + tap targets | **T1 + T2** | T2 gives true touch-target geometry; T1's `preview_snapshot` a11y tree additionally catches elements that are visually fine but unreachable. Run both when available |
| Mobile checklist (bottom sheet, swipe-down, spark stacking) | **T2** | needs `has_touch`; under T1 these degrade to visual-only confirmation |

### Reporting contract (this is the part that must not be optional)

Every QA report opens with a transport line and, when degraded, an explicit coverage statement:

```
Transport: T2 (mobile_preview.py, Chromium 3.x, 390x844 @2x, mobile-emulated)
           T1 unavailable (Preview MCP not provisioned in this environment)
Coverage:  V1-V8 full
```
```
Transport: T1 (Preview MCP, 390x844 resize-emulated)
Coverage:  V2-V6 run but resize-emulated (no touch/DPR) - treat geometry as indicative
           V8 tap-target sizing NOT verified - requires T2
```
```
Transport: T3 (static only - no browser available in this environment)
Coverage:  V2-V8 NOT RUN. This is a partial QA pass; the visual layer is unverified.
```
A degraded run is a **legitimate, clearly-labeled result** — never a silent pass, and never a
FAIL merely because a transport was missing.

### `tools/mobile_preview.py` changes

Keep the existing CLI behavior intact; add:

1. **A desktop mode.** The context hardcodes `is_mobile=True, has_touch=True` (line ~156), so the
   mandated 1440×900 desktop pass currently runs under mobile emulation. Add `--desktop`
   (or `--no-mobile-emulation`) flipping those off and defaulting the viewport to 1440×900.
   Without this, "run the suite at both viewports" is not achievable through this tool at all.
2. **Multi-tab iteration.** Today a 6-tab sweep means 6 process launches. Let the check JS
   self-iterate (the `async () => {...}` design already permits it) rather than growing the
   Python surface.
3. **A `--theme` flag** wrapping `--click '.theme-toggle button[data-theme="..."]'` + settle,
   since V5 and V7 both need light/dark passes.
4. **Robust browser resolution across environments.** The script reads `PLAYWRIGHT_CHROMIUM_PATH`
   and otherwise defers to Playwright's own lookup; its inline comment still assumes a Windows
   desktop. Verify it resolves in the web/remote container too (where `PLAYWRIGHT_BROWSERS_PATH`
   points at `/opt/pw-browsers`) and make the failure message name the missing piece, since that
   message is what the V0 probe keys off.

`_resolve_eval` already supports `@path/to/file.js` (line 98), so `--eval @tools/qa-checks/*.js`
works as-is.

Update `CLAUDE.md`'s mobile-preview paragraph — it currently states the Preview-MCP failure as a
flat machine-wide fact rather than an environment-dependent one — and `AGENTS.md`'s QA row, to
describe the transport ladder.

## Phase 4 — Close the `applyChartTheme()` gap (build code)

Port the three behaviors running-log's `applyChartTheme()` lacks, from
`strava-data/dashboard/template.py:1084` into `running-log/dashboard/template.py:1483`:

1. **Dynamic subplot axes** — replace the fixed `xaxis.*`/`yaxis.*` keys with Strava's
   `Object.keys(fl)` loop over `/^[xy]axis\d*$/`.
2. **Annotation recoloring** — port `isGrayText()` / `brandTextVar()` and the
   `annotations[i].font.color` patching.
3. **`'title.font.color': textPrimary`** — `tidy_dark` bakes chart titles `#e6edf3`, invisible on
   white.

This is prophylactic, not a live bug fix: running-log presently uses none of the three. Keep it
in its own commit so it is trivially revertable and obviously separable from the QA work.

## Files

| File | Change |
|---|---|
| `.claude/qa-visual-suite.md` | **new** — V0–V8, the shared rendered suite |
| `tools/qa-checks/axis-fill.js` | **new** — V6 |
| `tools/qa-checks/hover-theme.js` | **new** — V7 |
| `tools/qa-checks/dom-overlap.js` | **new** — V8 |
| `tools/qa-checks/label-overlap.js` | **new** — V2, lifted from the agents + tick extension |
| `tools/qa-checks/edge-clip.js`, `width-fill.js`, `contrast.js` | **new** — V3/V4/V5, lifted verbatim |
| `.claude/agents/strava-qa.md` | trimmed to §1–§5 + suite dispatch; drops its hardcoded Preview-MCP assumption |
| `.claude/agents/running-log-qa.md` | trimmed to §1–§2 + suite dispatch; **gains V4 width-fill** |
| `tools/mobile_preview.py` | `--desktop`, `--theme`, cross-environment browser resolution, probe-friendly failure messages |
| `running-log/dashboard/template.py` | Phase 4 `applyChartTheme()` port |
| `CLAUDE.md`, `AGENTS.md` | point at the shared suite + the transport ladder |

Unchanged: `.claude/commands/dashboard.md`, both `dashboard-spec.md` profile blocks (the
**QA agent** field still names `strava-qa` / `running-log-qa`), and `running-log/qa.py`.

## Verification

Run from the repo root; `mobile_preview.py` must run **un-sandboxed** (it pulls `plotly.js` from
the CDN).

1. **Baseline both dashboards build clean:**
   `uv run python strava-data/build_dashboard.py` and
   `uv run python running-log/visualize_log.py`, then `uv run python running-log/qa.py` (exit 0).
2. **Suite runs green on both targets, both viewports:**
   ```
   uv run python tools/mobile_preview.py --page /strava.html  --eval @tools/qa-checks/axis-fill.js
   uv run python tools/mobile_preview.py --page /index.html   --eval @tools/qa-checks/axis-fill.js
   uv run python tools/mobile_preview.py --desktop --page /strava.html --eval @tools/qa-checks/dom-overlap.js
   ```
   …and the same for each check file, at 375/390 and desktop.
3. **Transport probe behaves correctly per environment** — the check that this rework actually
   landed. Run the QA stage from at least two environments (desktop + web/remote is the most
   informative pair) and confirm each: picks a working transport without manual intervention,
   prints the transport line, and — where a transport is genuinely missing — prints the
   coverage-loss statement rather than a clean-looking pass. Then force each degraded path
   deliberately:
   - Make T2 unavailable (rename the Playwright import target or run where Chromium is
     unresolvable) → probe must fall through to T1, not error out.
   - Make T1 unavailable → probe must select T2 silently and report it.
   - Make both unavailable → must report **T3, static only**, run `qa.py` / the units grep,
     and state plainly that V2–V8 were not run. It must not exit 0 looking like a full pass.
   - Run T2 sandboxed so the plotly CDN is blocked → must surface the "CDN unreachable"
     diagnosis and advise the un-sandboxed rerun, not report empty charts as failures.
4. **Bug-injection regression — the step that proves the new checks actually bite.** Each fault
   is reverted immediately after confirming the FAIL:
   - Remove `range=_PR_X_RANGE` from `chart_pace_timeline` → rebuild → **V6 must FAIL** on
     `chart-pace-timeline` with a blown x-range. (This is the real July 2026 bug.)
   - Re-add the old `template.py` `simplify()` line that hid the pace legend on mobile →
     rebuild → **V6's legend assertion must FAIL**.
   - Hardcode a dark `hoverlabel.bgcolor` on one chart and view in light mode →
     **V7 must FAIL**; confirm the **existing V5 contrast audit still passes it**, demonstrating
     the gap this check closes.
   - Force two `.card`s to overlap via a fixed width → **V8 must FAIL**.
   - Set an x-axis `nticks` high enough to crowd ticks at 390px → **V2's tick extension must
     FAIL** where the pre-change scan passed.
5. **Phase 4:** temporarily add an annotation with a baked gray font color plus a `tidy_dark`
   title to one running-log chart, rebuild, toggle to light mode → text must be legible (it
   would be dark-on-white before the port). Revert the temporary chart change.
6. **End-to-end through the pipeline:** run `/dashboard running-log` and `/dashboard strava-data`
   as far as the QA stage and confirm each agent reads the shared suite, reports V0–V8 with the
   Viewport **and Transport** columns populated for both passes, and that the two reports are
   structurally comparable.
7. **CI untouched:** `deploy.yml` still runs `uv sync --no-dev`; none of the new tooling is
   invoked there (Playwright stays a dev dependency).

## Sequencing

Phases are independently landable. Suggested order: **1 → 3 → 2 → 4** — extracting the suite
first collapses the duplication before new checks are written against it, and landing the
transport layer (Phase 3) before authoring the new JS (Phase 2) means every new check is
verifiable the moment it is written, in whichever environment the work happens to be done from,
rather than only at the end on one machine.

## Related docs

- [CLAUDE.md](../../CLAUDE.md) §"Plotly charts — mobile-safe authoring" — the traps these checks enforce
- [qa-mobile-checks.md](running-log/qa-mobile-checks.md) — the prior, running-log-only proposal;
  this plan supersedes its Phase 2/3 (a shared suite instead of a running-log-specific port) but
  its `qa.py --mobile` / `tools/preview_harness.py` idea remains a valid future consolidation
- [Mobile Redesign Plan](mobile-redesign-plan.md) — the intended mobile UX both checklists assert
- [AGENTS.md](../../AGENTS.md) — pipeline roles and the profile mechanism this design mirrors
