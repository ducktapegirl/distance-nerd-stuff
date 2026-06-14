
## 14 June 2026

### CLAUDE.md Refresh + Interactive Inline Review

Reviewed and updated the project's `CLAUDE.md` to fill gaps that would trip up a cold-start agent. Additions included a Python environment table (the critical detail that bare `python` resolves to Python 2 for the Running Log on this machine), Running Log build commands, the `build_dashboard.py` import restriction (no pandas), the full Strava data pipeline in order, Strava dashboard architecture conventions (`tidy_dark`, `fig_html`, `applyChartTheme`), and a consolidated units policy. The Deploy section was corrected to reflect the live GitHub Pages workflow rather than the stale Netlify/placeholder description.

A new interaction pattern emerged: asking Claude to "show it to me so I can interactively comment on it" caused the assistant to render the document section-by-section as an HTML widget with per-section text boxes and a submit button, allowing inline review and delivering all comments in a single follow-up message. No explicit instruction to use a widget was given — it was inferred from the phrasing.

### Iterations

| # | What happened | Root cause | Fix |
|---|---|---|---|
| 1 | Deploy section described Netlify as publish target and called the workflow a placeholder | `deploy.yml` had since been wired up to GitHub Pages; CLAUDE.md wasn't updated | User flagged it; corrected from reading the live `deploy.yml` |

### Prompting lessons

- **Read the actual workflow file before describing deploy setup** — `deploy.yml` is a ground-truth source; describing it from memory or prior context risks stale information, as it was here.
- **"Show it to me so I can interactively comment on it" triggers a widget review UI** — this phrasing causes the assistant to render a document as a per-section HTML form rather than printing raw markdown. Useful for any file edit where you want to give targeted feedback without copying and pasting.

### Summary

| Time | Money | Pain<br>1:😊  5:🤕 |
| ---- | ----- | ------------------- |
| 5 min | $0 | 1/5 — smooth; one stale Deploy section caught by user |

---

## 14 June 2026

### Strava Dashboard: Segment Consistency, Fastest Segments & Grade-vs-Speed Analysis

Added three new visualization groups to the Segments tab. Section 1 produces four
cards (most/least consistently-paced for Running and MTB, ≥3 efforts) with
horizontal box plots of pace/speed distributions, ranked by coefficient of
variation. Section 2 produces six cards showing the top 3 fastest segments by
average pace per sport — name, pace, distance, and grade. Section 3 renders a
conditional scatter plot comparing running vs MTB speed across segment grade, with
linear fits and an annotation marking the grade at which running overtakes biking;
geographic overlap detection (start ≤60m, distance ratio 0.70–1.43) identifies
shared run/MTB trails. All three sections integrated into `build_dashboard.py` and
rebuilt cleanly.

### Iterations

| # | What happened | Root cause | Fix |
|---|---|---|---|
| 1 | Screenshot tool timed out on full 25-chart page | Page renders all charts; tool couldn't capture the full load | Created a lightweight QA page with only the 5 new charts; extracted PNG via Plotly client-side export |
| 2 | `git pull` produces merge conflicts on `strava.html` | `strava-fetch.yml` rebuilds and commits the dashboard remotely on a timer; local feature sessions also commit the built HTML | Discovered mid-session; not resolved this session — structural tension between CI-generated and locally-generated artifacts |

### Prompting lessons

- **State whether CI rebuilds generated artifacts before any local build session** —
  `strava-fetch.yml` commits a rebuilt `strava.html` on every data fetch. A local
  session that also commits the built HTML creates a dual source of truth: `git pull`
  after a remote run will conflict on the generated file. Saying "the fetch action
  also rebuilds the dashboard — here's the conflict risk" at session start prompts a
  decision upfront: either stop committing the HTML locally, or have CI skip the
  rebuild, or treat the HTML as untracked.

### Summary

| Time | Money | Pain<br>1:😊  5:🤕 |
| ---- | ----- | ------------------- |
| 1.5 hrs | — | 2/5 — Session delivered everything asked; friction came from discovering a pre-existing CI/local conflict that Claude was not aware of |

---

## 12 June 2026

### Migration Wrap-Up: GitHub Actions Secrets, Pages Deploy, Nav Link Fixes

Completed the post-migration setup checklist for the `endurance-logs` repo (split from `Experiments` on the same day). Walked through setting GitHub Actions secrets manually via the GitHub UI — `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `STRAVA_REFRESH_TOKEN` sourced from local files, plus a new fine-grained PAT for token rotation. Confirmed the `frontend-design` plugin was already active in `~/.claude/settings.json`. Replaced the deploy placeholder with a working GitHub Pages workflow (`deploy.yml`) triggered on changes to the Running Log HTML files. Fixed two broken nav links between the dashboards after the live deploy exposed them.

### Iterations

| # | What happened | Root cause | Fix |
|---|---|---|---|
| 1 | https://ducktapegirl.github.io/endurance-logs/ returned 404 after enabling Pages | Enabling Pages in the GitHub UI auto-generated `static.yml` deploying the entire repo root — no `index.html` there | Deleted `static.yml`; relied on our `deploy.yml` which correctly publishes `Running Log/` |
| 2 | "My Strava Dashboard" link in `index.html` pointed to wrong URL | `href="/strava.html"` is root-relative — breaks under the `/endurance-logs/` subpath | Changed to relative `href="strava.html"` |
| 3 | "← College Running Log" back-link in `strava.html` was broken | `href="/"` resolved to `https://ducktapegirl.github.io/` | Changed to relative `href="index.html"` |

### Prompting lessons

- **State the deploy target before touching nav links** — knowing "GitHub Pages project repo (subpath `/endurance-logs/`)" upfront would have flagged root-relative hrefs as broken before the first deploy, not after.
- **Warn that enabling GitHub Pages auto-generates a conflicting workflow** — GitHub creates `static.yml` pointing at the repo root when you click "GitHub Actions" as the source. Knowing this would have prompted deleting it immediately rather than discovering it via a 404.

### Summary

| Time | Money | Pain<br>1:😊  5:🤕 |
| ---- | ----- | ------------------- |
| 30 min | — | 3/5 — GitHub Pages setup required several manual correction rounds; nav link fixes only surfaced post-deploy |

---

## 11 June 2026

### Strava Dashboard: SVG Calendar, Elevation Breakdown, Overview Row & Theming Fixes

Six targeted refinements to the Strava dashboard in a single developer pass. The headline change was replacing the Plotly heatmap calendar with a hand-built SVG generator ported from the College Running Log — matching its exact 11×11px cells, single-letter SMTWTFS day labels, left-column year labels, and horizontal data-scaled gradient legend, all themed via CSS variables. The other five changes were smaller but meaningful: the Overview added a second stat row with Longest Run and Longest MTB; the Weekly Elevation chart was rewritten as a 3-color stacked bar mirroring the Volume chart; the Pace/Speed chart dropped its rolling-average trend line; the Volume rangeslider now retints correctly in light mode; and chart titles on hidden tabs (Exploratory, Segments) are re-applied on tab activation so they're legible after a theme switch. Dead code (`CAL_COLORSCALE`, `_rolling_quarterly`, `DOW_SUN`) removed in the code-review pass.

### Iterations

| # | What happened | Root cause | Fix |
|---|---|---|---|
| 1 | QA WARN: Volume chart legend overlapped the rangeslider | Legend was positioned at `y=-0.2`, too close to the slider track | Moved legend lower with `y=-0.45` and added `margin.b=130` |
| 2 | QA WARN: Dark-mode annotation contrast 2.11 after a light→dark theme cycle | `GRAY_TEXT` only included dark-palette grays; light-theme grays (`#424a53`, `rgb(66,74,83)`) were never retinted on switch-back | Added those two values to `GRAY_TEXT` so the retint is reversible in both directions |
| 3 | Commit message had stray `@` at start and end of subject line | PowerShell here-string `@'...'@` syntax injected literal `@` characters into the git message | Wrote the message to a temp file and used `git commit --amend -F` to replace it |

### Prompting lessons

- **Pre-specify the GRAY_TEXT contract as bidirectional** — the annotation retint only prevented light-palette grays from appearing in dark mode; it didn't handle the reverse. Stating "retint must be fully reversible — both `GRAY_TEXT` directions" in the spec would have caught this without a QA cycle.
- **Call out PowerShell here-string quoting before any git commit** — `@'...'@` is correct PowerShell syntax but wraps the message content with literal `@` characters. A note in the workflow ("pass commit messages via `git commit -F <tempfile>`") avoids any shell quoting interaction.

### Summary

| Time | Money | Pain<br>1:😊  5:🤕 |
| ---- | ----- | ------------------- |
| 1–2 hours | — | 1/5 — Smooth; two QA WARNs fixed cleanly, no dead ends |

### Future work

- **Move Netlify deploy to a GitHub Action** — current deploy is a local Netlify Stop-hook that fires when a Claude Code session ends, which means it only deploys if the session ends cleanly on the right machine. The natural replacement is a GitHub Action triggered on pushes that touch `Running Log/index.html` or `Running Log/strava.html`, running `netlify deploy --prod` in CI. New secrets needed: `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID`. The build step (running `build_dashboard.py` locally and committing the HTML) stays local for now; CI just handles the last hop.

---

## 11 June 2026

### Strava Dashboard: Imperial Units, Light/Dark Theming & Overlap-Free Labels (Agentic)

Ran the multi-agent `/strava` framework to fix the Exploratory tab: converted every displayed unit to imperial (running pace **min/mi** on reversed axes, MTB speed **mph**, temperature **°F**), made all eight statistical charts legible in both light and dark mode, and eliminated every label/annotation that overlapped plotted data. The work was driven by upgrades to the agent *definitions* themselves — the `strava-qa` agent gained accurate label-overlap detection (data-mark and label-label intersection, not plot-area bounding boxes), a units-policy grep, and a mandatory light+dark contrast audit; the `strava-developer` agent gained a display-units policy and both-theme/label-placement rules to shrink the QA loop. The theme JS was extended to retint subplot axes, colorbars, annotation pills, and brand-colored text per theme. Committed to `main` as `2700fa6`.

### Iterations

| # | What happened | Root cause | Fix |
|---|---|---|---|
| 1 | First QA pass flagged V3/V8 stat annotations sitting on histogram bars / the suffer-score peak | Annotations were anchored *inside* the plot at `y≈0.97` | Moved both above the plot via paper coords (`y=1.10`/`1.07`) with bumped top margins |
| 2 | A stricter re-scan then caught V2/V4/V6 overlaps the first visual pass had missed | Original detector compared label rects to the whole plot-area box, not to actual data marks | Rewrote the detector to measure label↔data-mark and label↔label intersection; surfaced 3 real overlaps |
| 3 | V2 biplot labels still sat on the dense point cloud after a 12% radial nudge | Short loading-arrows end mid-cloud; a small offset wasn't enough | Ringed all 8 labels at a common outer radius along their arrow directions, with leader lines extended to meet them |
| 4 | The full-tab scan then flagged V2 again as a false positive | The scan samples connector lines as "data," so each label hit its own leader line | Confirmed clean with a markers-only scan; documented the leader-line caveat in the QA agent |
| 5 | Light-mode contrast audit flagged amber/violet annotation text (2.15–2.72) | `applyChartTheme` recolored only *gray* text; brand colors kept their dark-palette hex on white | Added a brand-color remap that swaps teal/amber/violet annotation text to the per-theme variant |

### Prompting lessons

- **Give the QA detector a "what counts as data" definition upfront** — the overlap scan samples *lines* as data marks, which makes leader/connector lines (biplot arrows) read as false overlaps. Stating "a label on its own pointer line is fine; only marker/bar/violin occlusion counts" would have skipped one diagnose-and-document loop.
- **Name the units contract once, globally** — "all user-facing pace = min/mi, speed = mph, temp = °F; data stays metric" belongs in the spec and the developer agent from the start, so per-chart conversions aren't rediscovered chart by chart.
- **"Works in both themes" means brand colors too** — theme code that only retints gray text leaves brand-colored annotations low-contrast on white. A rule that *every* baked color must have a light-mode variant catches this before the audit does.

### Summary

| Time | Money | Pain<br>1:😊  5:🤕 |
| ---- | ----- | ------------------- |
| 1–2 hours | ~$5 overage | 2/5 — minor friction; mostly iterative label/contrast tuning, no dead ends |

---

## 10 June 2026

### Strava Dashboard: Exploratory Tab (Fully Agentic Build) + segment_efforts.csv Bug Fix

Two big workstreams in one session. The first was the main event: a fully autonomous run of the multi-agent pipeline to build a new "Exploratory" tab on the dashboard — the orchestrator self-approved every gate without pausing. The second was a silent data-corruption bug discovered mid-session and fixed the same day.

**Exploratory tab** (commit `45248d8`): ran all 7 pipeline stages (pre-flight → analyze → ideate → design → build → QA → ship) with `claude-fable-5` as orchestrator dispatching `strava-data-analyst`, `strava-creativity`, `strava-viz-design`, `strava-developer`, and `strava-qa`. Landed 8 new displays in a new tab section immediately after Map: monthly volume strip, PCA + k-means effort clusters, HR zone histograms, heat tax on pace (temperature vs. pace regression), seasonal run heatmap, cadence vs pace scatter, segment consistency index, and 7-day training load + monotony. All math that would normally require scipy/sklearn (PCA via SVD, k-means++, Welch t-test p-values via regularized incomplete beta) was implemented in pure numpy/Python to keep `build_dashboard.py` dependency-free. The tab opens with an attribution paragraph naming the model and all five subagents.

**segment_efforts.csv bug** (commit `ffdfee2`): the analyst discovered during Stage 1 EDA that 186 of 1,441 effort rows (13%) were silently dropped by pandas — all efforts since 2026-04-20. Root cause: `fetch.py` had added a `sport_type` field to the schema but `csv_append()` only writes a header for new files, so 186 rows were appended with 21 fields under the old 20-column header. Fixed by migrating the file forward (backfill `sport_type` from `activities.csv` join, rewrite with correct header), adding a schema-mismatch guard to `csv_append()`, fixing a unicode crash in `analyze_segments.py` on cp1252 consoles, and regenerating `segments_summary.csv` (616 → 693 segments). Documented in `KNOWN-ISSUES.md`.

### Iterations

| # | What happened | Root cause | Fix |
|---|---|---|---|
| 1 | V5 seasonal heatmap vrect spanned the wrong month | `x0="Jun"` — June has 3 MTB rides; the blackout is July | Changed to `x0="Jul"` |
| 2 | V3 HR histogram run-mean annotation clipped at bottom | Annotation used a data-axis y-coordinate (153.5) on a count axis topping ~65 | Switched to `yref="paper", y=0.95`; added missing MTB mean annotation |
| 3 | V4 HR t-test annotation showed wrong values | `"HR flat (t=-0.19, p=0.85)"` was hardcoded | Replaced with computed f-string |
| 4 | V6 speed median label order-dependent | `y=spd[0]` assumed first element was the largest | Switched to `yref="paper", y=0.95` |
| 5 | V6 regression annotation and slope/intercept hardcoded | Frozen literals from spec appendix copied verbatim into code | Replaced with computed values via `ols_r_p()` |
| 6 | V1 explicit date range clipped future months | `range=["2024-11-01","2026-06-30"]` hard-coded in chart | Dropped the range; let Plotly autorange |
| 7 | V3 HR histogram bins hardcoded 85–175 | Copied from spec without data-derivation | Derived from data: `lo=floor(min/5)*5-5`, `hi=ceil(max/5)*5+5` → 80–180 |
| 8 | V5 July ride count hardcoded zero | `"MTB blackout - 0 July rides"` frozen in annotation text | Replaced with `f"... {int(mtb_cnt[6])} July rides"` |
| 9 | k-means single-seed gave degenerate 14/54/169 cluster split | One `kmeans_pp_init` call rarely lands at the global optimum for this data | Switched to best-of-50 restarts from a single `default_rng(42)` stream → stable {46, 70, 121} matching sklearn |

### Prompting lessons

- **Pin all literals in the spec, then verify them at build time** — 5 of 9 QA iterations were frozen values (t-stats, date ranges, bin bounds, counts) that the spec had derived correctly but the developer baked in as constants rather than computing. A rule like "any value derived from data must be computed at runtime, not transcribed from the spec" in the developer agent would eliminate this class of bug.
- **State the k-means stability requirement explicitly** — "best-of-N restarts" needs to be in the spec, not left to the developer to infer. A single seeded init looks deterministic but isn't globally optimal; the analyst should pin expected cluster sizes and the developer should match them.
- **The analyst's EDA tool and the build script's reader are different environments** — the analyst recovered all 1,441 effort rows using the csv module; `build_dashboard.py` uses a different read path. Bugs in the data layer that only affect one reader can hide through design and only surface at QA.

### Summary

| Time      | Money         | Pain<br>1:😊  5:🤕                                                                                                               |
| --------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 3–4 hours | $2 in overage | 2/5 — fully autonomous; QA loop had 9 fixes but all were straightforward literals/anchors, no dead ends. Did hit a rate limit :) |

---

## 14 May 2026

### Running Log: Presentation Planning Session

Planned a Reveal.js presentation telling the story of the College Running Log dashboard project for a general audience. The session covered reconstructing the project chronology from `Claude's Log.md`, `Captain's Log.md`, git history, and handoff files; refining the story arc (7 chapters, 6 acts, ~25 slides); and establishing the design system for the slides (matching the dashboard's dark-glass tokens exactly). Ended with a handoff file committed to the feature branch so work can continue in a local Windows session with access to the original `.jsonl` session logs.

### Iterations

| # | What happened | Root cause | Fix |
|---|---|---|---|
| 1 | Plan file still referenced PPTX/PowerPoint after switching to Reveal.js | Three separate references in different sections; only the implementation section was updated initially | Found all three with `grep` and updated each: context line, verification steps, and the advantages list |
| 2 | Chronology described the pace bug as "silently corrupting data since 2003" | Inaccurate framing — the original HTML was human-readable notes, never intended as structured data; the bug only existed from the moment we started parsing | Reframed as a parsing mismatch that only became relevant during this project |
| 3 | "Regular coding is more fun" included as a story beat | Quote was a section heading contrasting a productive session with a frustrating Simscape session the day before — not a meaningful standalone insight | Removed from the story arc |

### Prompting lessons

- **State the target format before the plan is written** — "use Reveal.js, not PowerPoint" at the start would have avoided the PPTX cleanup pass entirely. Format decisions made mid-plan require grep-and-replace passes instead of getting it right once.
- **Clarify data origin and intent before describing bugs** — knowing that the original HTML was human-readable notes (never structured data) changes how bugs get framed. A note like "the source files were personal notes, not a database" at the start sets the right frame.
- **Session environment is fixed at start** — a session started on mobile runs on a remote server for its entire lifetime. Switching to desktop mid-session doesn't give Claude access to the local filesystem; the session root doesn't follow the device. If you need local file access (e.g. reading `.jsonl` session logs), start a new session from the desktop app instead of trying to hand off within the same session.

### Summary

| Time | Money | Pain<br>1:😊  5:🤕 |
| ---- | ----- | ------------------- |
| < 30 min | — | 2/5 — Smooth planning session; minor friction from stale PPTX references and two chronology corrections |

---

## 12 May 2026

### Running Log: Restore Two Missing Charts + Netlify Deploy

Added back two charts dropped during the redesign — *Monthly Mileage by Year* on the Volume tab and *Miles by Workout Type per Season* on the Workout Mix tab — preserving the original behavior (Miles ↔ % of Total toggle, per-year color encoding) while matching the new dark-glass theme. The toggle ended up as a custom HTML button group styled like the existing top-nav theme toggle, driving `Plotly.restyle` from JS, after Plotly's built-in `updatemenus` buttons fought the CSS-variable theming. Branch was merged into `main` and the site was redeployed to `https://ducktape.netlify.app` via the Netlify CLI.

### Iterations

| # | What happened | Root cause | Fix |
|---|---|---|---|
| 1 | Couldn't find the old chart code from `index_orig.html` | The HTML is a Plotly-rendered static snapshot, not source — chart logic isn't in it | Found the pre-redesign `visualize_log.py` at commit `9dc6b15` via `git log` on the file; read it with `git show` (no checkout needed during plan mode) |
| 2 | Legend overlapped rotated x-axis labels | `tidy_dark` sets `legend.y=-0.25, margin.b=40` as defaults | Override legend + margin *after* calling `tidy_dark` (it overwrites whatever was set before) |
| 3 | Toggle text illegible in both states | Original used light bg + dark text, then dark bg + light text — Plotly button "active" state recolors unpredictably and ignores CSS variables, so neither config worked in both light and dark theme | Replaced `updatemenus` with HTML buttons styled with `var(--accent-dim)` / `var(--accent)` (same pattern as `.theme-toggle button.active`); wired `Plotly.restyle` from a small IIFE that reads `data-miles` / `data-pct` JSON attributes |
| 4 | Workout-type colors were nearly indistinguishable | First palette grouped 5 categories (`run`, `pool`, `aquajog`, `pre-meet`, `fartlek`) all in the blue/green/teal family for "semantic similarity" | Re-tuned for hue separation across the 14 categories — teal / violet / blue / amber / pink / lavender / lime / cyan / dark-cyan / slate / gray / forest-green / pale-sky / dark-slate |
| 5 | `git checkout main` blocked by untracked working-tree files | The restored `index_orig.html` / `index_orig_files/` from `git checkout 0541511 -- …` shadowed identical files that exist on main | Deleted them locally before the checkout — main's copy then materialized cleanly |

### Prompting lessons

- **For chart restoration, point at the source-script revision, not the rendered output** — "Re-add these charts; the original lives in `visualize_log.py` at commit `<sha>`" is a one-line prompt. Pointing at a Plotly-rendered HTML file forces a detour: the chart logic isn't in the DOM. For the Strava dashboard port, reference the Python builder (e.g. `build_dashboard.py`), not `dashboard.html`.
- **State the theming contract upfront for any new chart UI** — "All chart-adjacent UI (toggles, legends, custom controls) must use CSS custom properties so the light/dark toggle works." This would have skipped the entire Plotly `updatemenus` detour. The Strava dashboard doesn't yet have a theme toggle — when adding one, every Plotly-embedded interactive control becomes a problem; build HTML controls + `Plotly.restyle` from the start.
- **Specify palette intent: "maximum hue separation" vs "semantic families"** — the first palette tried to keep aqua/pool/pre-meet in the same hue family (water = blue, easy = green) and lost differentiability. For categorical charts with > ~6 categories, optimize for separation first, semantics second.
- **Mention deploy mechanism early if it's manual** — "Site has no auto-deploy; ship via `netlify deploy --prod` from `main`" upfront would let the merge-and-deploy flow be a single plan, not two passes. Site ID lives in `.netlify/state.json` (gitignored).

### Reusable patterns for the Strava dashboard port

- **`tidy_dark`-style theme function**: apply chart-wide defaults, then override per-chart *after* the call. The override-after pattern is essential — calling it before `tidy_dark` silently loses your changes.
- **CSS-variable-driven chart card UI**: every color on chart cards as `var(--…)`; in Python, the dark hex values feed only the Plotly figure layout (regenerated on theme switch via JS).
- **HTML toggle + `Plotly.restyle`**: the durable replacement for `updatemenus`. Encode alternate y-data as `data-*` JSON attributes; one generic IIFE handles all toggles on the page.
- **Reference-fetch pattern**: use `git show <sha>:<path>` to read history without dirtying the working tree — especially valuable in plan mode where checkouts are disallowed.

### Summary

| Time | Money | Pain<br>1:😊  5:🤕 |
| ---- | ----- | ------------------- |
| <30 min | — | 2/5 — Mostly smooth; iteration was on visual polish (toggle contrast, palette differentiability), not architecture |

---

## 12 May 2026

### Running Log: Full Dashboard Rewrite Polish

Worked through all 7 sections of a pre-written `Rewrite Ideas.md` to polish the College Running Log dashboard. Changes included a light/dark/system theme toggle with full CSS custom property coverage, a pace parsing fix for `H:MM:SS` entries that had been silently corrupting long-run paces since ~2003, a `parse_miles()` rewrite that recovered ~57 previously-blank mileage entries from expression-format strings (`4.5+.5`, `~8`, `<4.5`), and a complete client-side race browser with live search/sort/filter. Also added PR progression charts for all distances (step-line HV style), redesigned the sparklines layout, and fixed chart overflow in the Patterns section. `visualize_log.py` was confirmed as the single source of truth — `index.html` is a generated artifact and must never be edited directly.

### Iterations

| # | What happened | Root cause | Fix |
|---|---|---|---|
| 1 | Pace fix appeared to work, then errors returned on next check | Initial fix applied to `index.html` directly; `visualize_log.py` overwrote it on next regeneration | Established rule: `visualize_log.py` is the only edit target; ported all fixes there |
| 2 | Race count showed 100 in Workout Mix but 99 in Races tab | Workout Mix counted raw `is_race=="1"` CSV rows; Races tab used `build_race_records()` which filters unclassifiable entries | Passed `races_by_cat` dict to both `section_workout_mix()` and `chart_workout_donut()` |
| 3 | Bars overlapped on weekly mileage chart at zoom | Bars anchored at first-run-date of each week, not a consistent Monday; adjacent weeks started on different days | Bucketed all weeks by `monday = d - timedelta(days=d.weekday())` |
| 4 | Sparklines overflowed their container | 4-column horizontal grid was too narrow for Plotly charts | Switched to vertical flex stack; each card: `80px label \| 110px stat \| 1fr chart` |
| 5 | Y-axis boundary labels (5:00 / 10:00) appeared with no gridline | `tickvals` included those boundaries; no gridline drawn at exact min/max of axis range | Removed 5.0 and 10.0 from `tickvals`; kept 5.5–9.5 |
| 6 | Blue shading cap appeared above easy pace chart | `fill="tozeroy"` on a reversed y-axis painted fill toward y=0 (top of chart) | Removed `fill` and `fillcolor` from the smooth-line trace |
| 7 | Light mode had low contrast — text and borders barely visible | Initial `:root.light` vars set too close to white; type-category colors used unsaturated values | Darkened secondary text, borders; used more saturated running-type colors (teal, amber, violet) |
| 8 | Detail panel text was illegible in light mode | Detail panel HTML was built with baked-in Python f-string color substitutions (`{TEXT_PRIMARY}` etc.) that always resolve to dark-mode hex values | Global pass replacing all `{CSS_VAR}` substitutions with `var(--css-var)` references |

### Prompting lessons

- **Name the build system at the start** — "The dashboard is generated by `visualize_log.py`; `index.html` is an artifact" would have prevented the first iteration entirely. Any time there's a generator script, say so upfront.
- **CSS-in-Python files need a theming contract** — when a Python script bakes hex colors into HTML via f-strings, those colors can't respond to CSS class changes. The contract should be stated at the start: "all colors must be CSS custom properties so the theme toggle works."
- **List all data format variants for parsed fields** — `parse_minutes()` had silently broken for 4 entries for years because `H:MM:SS` format was never documented. A note like "some times are in H:MM:SS format" at the start would have caught this in the original parse_log.py build.

### Summary

| Time | Money | Pain<br>1:😊  5:🤕 |
| ---- | ----- | ------------------- |
| ~3 hrs | — | 2/5 — Smooth overall; most friction came from not knowing `visualize_log.py` was the source of truth until after the first pace fix was lost |

---

## 10 May 2026

### Running Log: Date Sync, Click-to-Detail Panel, PR Grid

Picked up three open items from the `running-log-redesign` handoff. Cross-chart date sync was restored — zooming any of the five date-axis charts (cumulative, weekly, easy-pace, 5k progression, pace timeline) now keeps the others in lock-step via `plotly_relayout` listeners, with an early-return guard to ignore spurious events. A click-to-detail side panel was added, wired to Plotly chart points, heatmap cells, and race cards; it slides in from the right with full day notes, HTML-escaped content, and Escape/backdrop/× to close. The PR grid was left in its original 4-on-top / 3-on-bottom layout after a brief detour to `auto-fit`. Changes committed on the worktree branch, fast-forwarded to `running-log-redesign`, and pushed to origin.

A first: the Chrome MCP server was used mid-session to attempt visual self-verification of the generated HTML — navigating a browser tab, checking for console errors — without waiting for the user to look. The `file://` scheme turned out to be blocked by the extension API, so `Start-Process` was the fallback, but the attempt itself was new.

### Iterations

| # | What happened | Root cause | Fix |
|---|---|---|---|
| 1 | PR grid `auto-fit` put all 7 cards in a single wide row | `minmax(160px, 1fr)` at a wide viewport means one row fits all 7 | Reverted to `repeat(4, 1fr)` — user preferred the familiar 4+3 feel |
| 2 | Chrome MCP couldn't load the generated dashboard | Browser extensions block `file://` URLs by design | Fell back to `Start-Process index.html` (already in memory from the 4/19 session) |
| 3 | `python src/visualize_log.py` failed with a syntax error | `python` resolved to Anaconda2 (Python 2); the shebang and f-strings are Python 3 | Used full path `C:\Users\Alisha\Anaconda3\python.exe` |

### Prompting lessons

- **Reference the existing layout when asking for a grid fix** — "fix the empty cell but keep the 4-on-top / 3-on-bottom feel" would have skipped the auto-fit detour entirely. "Fix the empty cell" left the interpretation open.
- **Worktree branch ≠ target branch** — Claude Code's plan mode always creates a `claude/<id>` branch in a worktree; if the target branch is already checked out in the main worktree, you'll always end up doing a fast-forward + push at the end. Knowing this upfront, you could skip the local fast-forward and just `git push origin claude/<id>:running-log-redesign` directly.

### Summary

| Time | Money | Pain<br>1:😊  5:🤕 |
| ---- | ----- | ------------------- |
| ~45 min | — | 1/5 — Smooth pickup from a well-written handoff; all three features landed cleanly |

---

## 19 Apr 2026

### Strava Dashboard: Interactive HTML Dashboard from CSV Exports

Built `strava-data/build_dashboard.py`, a Python script that reads `activities.csv` and `segments_summary.csv` and produces a self-contained `dashboard.html` with 7 interactive Plotly charts: an activity calendar (per-year subplots, Sunday-start), weekly volume, heart rate trends, pace/speed trends (dual y-axis, imperial), elevation, segment PRs with sport-type emoji and filter buttons, and an activity map. The session picked up from a handoff file on `origin/main`, iterated through two rounds of visual fixes and one round of QA, then updated the spec to match intentional design decisions before a final clean QA pass. PR [#11](https://github.com/ducktapegirl/experiments-in-mcp/pull/11) merged all work.


### Iterations

| # | What happened | Root cause | Fix |
|---|---|---|---|
| 1 | `SESSION-HANDOFF.md` not found locally | File was committed on `origin/main`; local branch hadn't been synced | `git fetch` + fast-forward merge |
| 2 | OpenStreetMap tiles showed a wiki-blocked error | Plotly's `open-street-map` style fetches tiles from a domain blocked in this environment | Switched to `carto-positron` |
| 3 | Claude Preview tool launched Python 2 (Anaconda2) | `launch.json` resolved the wrong Python; Preview is designed for dev servers, not static files | Abandoned Preview; used `start file.html` on Windows. Saved to memory. |
| 4 | Two separate unit-correction rounds (km→mi, then m→ft) | Unit preference wasn't stated upfront; each surface (stats bar, charts, hover, detail panel) had to be found and fixed one pass at a time | Applied `KM_TO_MI` and `M_TO_FT` constants globally; caught remaining `dist_km` in detail panel via second QA run |

### Prompting lessons

- **State unit preferences upfront** — "I want imperial units (miles, feet) throughout" at the start would have collapsed two separate correction rounds into zero.
- **Name the OS and file-preview method** — "I'm on Windows; open HTML files with `start`" prevents the Preview tool detour entirely.
- **Pre-approve QA agent Python commands before running** — The QA agent issues `cd "..." && python script.py` commands which prompt every time because `python` isn't auto-allowable as a wildcard. Adding the exact build and spot-check commands to `settings.json` before triggering the agent makes it fully autonomous. (The `less-permission-prompts` skill won't catch these automatically since it only allowlists read-only commands.)




### Summary

| Time | Money | Pain<br>1:😊  5:🤕 |
| ---- | ----- | ------------------- |
| ~1 hr | — | 2/5 — Smooth build; friction came from permission prompts during QA agent run |

### Strava Dashboard: Requirements Interview + Failed Developer Subagent

Ran the `/requirements` skill to interview the user and produce a complete `strava-data/dashboard-spec.md` — 7 charts (activity calendar, volume, HR trends, pace/speed, elevation, segment PRs, activity map), global date filter, click-to-detail panel, and the Running Log color palette. Two attempts to spawn a developer subagent to build `build_dashboard.py` both failed with stream idle timeouts. Context filled up before the dashboard could be built in the main session; ended by writing `SESSION-HANDOFF.md` for pickup in a fresh session.

| 1 | Developer subagent timed out: "API Error: Stream idle timeout — partial response received" | Subagent spent ~4 min reading files (`visualize_log.py` 1,517 lines, spec, data headers) before writing any output; idle timeout fires when the output stream is quiet too long | (Not fixed this session) Should pass reference material inline and scope the subagent more narrowly |
| 2 | Switched to Opus model and retried — same failure | Wrong diagnosis: assumed Opus handles longer tasks; root cause was idle timeout, not model capability. Opus has the same timeout limit. | Recognized the error; pivoted to building in main session instead |
| 3 | Context window too full to build the dashboard in the main session | Large reference file reads (`visualize_log.py`) + long session summary consumed context before the build started | Wrote `SESSION-HANDOFF.md` with all key facts to enable a clean fresh session |

### Prompting lessons

- **Pass reference material inline to subagents** — instead of telling the subagent "read `visualize_log.py`," read it in the main session and paste the relevant functions directly into the prompt. Less tool use means faster time to first write, reducing idle timeout risk.
- **Scope subagent tasks narrowly** — "write a 400-line build script" is too large for one subagent pass. Split into "write chart functions" and "write page assembler" so each task completes before the timeout window.
- **Diagnose before switching models** — the Opus switch was a reactive guess, not a reasoned fix. Checking whether the failure was capability vs. timeout would have saved a wasted attempt and several minutes.
- **Plan for context limits on long sessions** — reading large reference files early in a long session crowds out the build work. Either do the build first or accept that a handoff file will be needed.

| ~1 hr | — | 4/5 — Repeated timeout failures with no clear error explanation, a wasted Opus attempt, and context running out before anything was built. |


---

## 18 Apr 2026

### Strava API Expansion: Comprehensive Data Pipeline

Built a full Strava data pipeline on a new branch. `strava-data/fetch.py` is a resumable, rate-limit-aware script that pulls everything the Strava API offers — activity detail, GPS/HR/power streams, laps, segment efforts, athlete profile, and gear — into CSV and JSON files under `strava-data/data/`. A GitHub Actions workflow (`strava-fetch.yml`) runs it on demand, commits new data files back to the repo, and rotates `STRAVA_REFRESH_TOKEN` automatically since Strava issues a new one on every token refresh. Two analysis tools followed: `analyze_segments.py` (segment summary CSV + interactive Plotly map) and a `/strava-segments` slash command for interactive Q&A. The `/reflect` skill was also built this session.

### Iterations

| # | What happened | Root cause | Fix |
|---|---|---|---|
| 1 | `git add .claude/commands/` rejected | `.claude/` was gitignored as a whole directory; negation rules don't work on ignored parents | Restructured `.gitignore` to ignore specific files rather than the directory |
| 2 | `gh workflow run` returned 404 | `workflow_dispatch` requires the workflow file on the default branch; discovered only at test time | Merged feature branch to main before testing |
| 3 | Streams fetch crashed: `TypeError: string indices must be integers` | Python's `requests` serializes `False` (bool) as `"False"` (string); Strava treated it as truthy and returned a keyed dict instead of a list | Changed param to string `"false"`; hardened `flatten_streams` to handle both response formats |
| 4 | Secret rotation returned HTTP 403 | `GH_PAT` was created without Secrets: write permission; setup instructions weren't confirmed step-by-step | User updated PAT permissions; workflow reordered to commit data before rotating, with `continue-on-error: true` on the rotation step |

### Prompting lessons

- **State the execution environment upfront** — "I'm on Claude Code web, I can't run things locally" would have flagged that `gh` wasn't in the sandbox and external HTTP is blocked, preventing two iterations around workflow testing.
- **Settle branch/merge strategy before building a workflow** — the question "does this need to be on main?" only surfaced at test time. It belongs in the planning questions.
- **Confirm external setup steps one at a time** — the PAT permissions issue suggests a list of setup instructions wasn't fully absorbed. Step-by-step confirmation would catch this earlier.

### Summary

| Time | Money | Pain<br>1:😊  5:🤕 |
| ---- | ----- | ------------------- |
| ~1 hr | | 3/5 — Four real iterations on workflow and API edge cases; plan-mode questions at the start prevented larger scope missteps. |

---

## 14 Apr 2026

### Documentation Agent: Auto-Logging Claude Code Sessions

Built a self-contained tool that turns a Claude Code session into a `Claude's Log.md` entry — no API key required.

**`document_work.py`** is the core script. It collects three things and feeds them to an inner Claude instance: recent git commits, the git diff (filtered to text extensions, truncated at 50 KB), and a narrative extracted from the session JSONL transcript. The transcript parser walks `~/.claude/projects/-home-user-experiments-in-mcp/*.jsonl`, picks the newest file, pulls out user messages and assistant text blocks, and stitches them into a readable `[USER] / [ASSISTANT]` log. It filters out skill injections (>800-char blocks that start with known skill headers) and hook feedback lines (lines starting with `[~/.claude/` or `Stop hook feedback`), and caps any single message at 1,500 chars with a 20,000-char total limit, keeping head and tail if it overflows.

Error detection in tool results needed care — the initial heuristic matched keywords like "error" and "exception" too broadly and flagged numbered file reads as errors. Fixed with a line-number detector: if the stripped result's first line starts with `"1\t"` and the block has more than two newlines, it's a file read, not an error.

**No API key:** The initial version used the Anthropic Python SDK, which immediately failed with `Could not resolve authentication method`. Switched to `subprocess.Popen(["claude", "--print", "--system-prompt", ..., "--tools", "", "--output-format", "text"])` — the Claude Code CLI handles auth via OAuth, so no key needed.

**The recursive confusion problem:** Multiple dry-runs showed the inner Claude outputting git commands and explanations instead of a markdown entry. Root cause: the git diff of `document_work.py` contains the script's own `SYSTEM_PROMPT` string verbatim. So the inner Claude was reading its own instructions back as data and getting confused about its role. Fixes tried: stricter system prompt wording, an XML `<work_data>` wrapper around the user prompt, a `## {today}` anchor at the end to force output to start with the date header. These helped in principle but not in this specific session, because the problem is structural — the tool being built *is* the thing being diffed.

**Resolution: the Skill.** Rather than keep fighting the subprocess, the better fix was to teach Claude *when not to use the script*. The `document-work` Skill (`/root/.claude/skills/document-work/SKILL.md`) now defines two explicit modes: when a user asks inside an active Claude Code session, Claude does it directly with its own tools (git log, read JSONL, write to the log file). When run from a terminal or hook with no active session, it calls `document_work.py`. The entry you're reading was produced using Mode 1.

### Summary 4/14/26

| Time | Money | Pain<br>1:😊  5:🤕 |
| ---- | ----- | ------------------- |
| ~3 hrs | | 3/5 - The subprocess approach was the right idea but hit a genuinely weird edge case: the tool being built appears in its own diff. The two-mode Skill design is cleaner anyway. |

To explore:
* [ ] Test `document_work.py` on a future session where it's *not* being modified — that's the normal case and should work fine
* [ ] Consider stripping the script's own file from the diff when it's being changed
---

## 11 Apr 2026

### Stock Market Drop Alerts

Built a service that watches the S&P 500 and Dow Jones during market hours and sends an email alert when either index drops 2% or 5% from its opening price on a given day.

The implementation has two parts:

**`stock-alerts/monitor.py`** — a long-running Python script intended for local use. Polls `^GSPC` and `^DJI` via `yfinance` (free, no API key) every 60 seconds, Mon–Fri 9:30 AM–4:00 PM ET. Tracks which alerts have already fired so each threshold only triggers once per day per index. Email delivery via Gmail SMTP, configured through a `.env` file (gitignored).

**`stock-alerts/check_once.py` + `.github/workflows/stock-alerts.yml`** — the cloud version. GitHub Actions runs `check_once.py` every 5 minutes during market hours without needing the Captain's computer to be on. State is persisted between runs using `actions/cache` with a date-scoped key, so deduplication still works. SMTP credentials are stored as GitHub repository secrets (`SMTP_USER`, `SMTP_PASSWORD`, `ALERT_TO`).

The branch was merged to main via PR #6. Alerts go to `alisha.schor@gmail.com`.

A `test_email.py` script and manual "Test Email Alert" workflow were also added so the SMTP pipeline could be verified without waiting for a real market drop. Email confirmed working.

**`stock-alerts/tests/test_check_once.py`** — 15 pytest tests covering:
- `is_market_open()`: weekday/weekend, before/after open, exact boundary times
- `fetch_intraday_change()`: normal drops and gains, empty data, single row, zero open price, network exceptions
- `send_alert()`: correct addresses used, graceful fallback when unconfigured, SMTP failure doesn't crash
- `main()`: -2% threshold fires, -5% threshold fires, both fire on a large drop, no re-alert same day, state resets on new day, skips fetch when market is closed

A CI workflow (`stock-alerts-ci.yml`) runs the tests automatically on any push touching `stock-alerts/`. Merged via PR #8.

*Done entirely on mobile. Not tested locally.*

### Follow-up: Test Fixes and Robustness Improvements

When the CI ran, almost all tests were failing. Investigated locally and found two categories of problems:

**Import / environment issue:** `yfinance` requires `curl_cffi` which can't build in some environments. Since `check_once.py` imports yfinance at the top level, the test module couldn't even load. Fixed with `tests/conftest.py` — it attempts to import yfinance and silently mocks it if the import fails. Unit tests already mock `yf.download` individually via `@patch`, so this has no effect on test behaviour.

**Wrong test assertion:** `test_alerts_when_two_percent_threshold_crossed` expected 1 alert, but the mock returns -3% for both `^GSPC` and `^DJI`, so 2 alerts correctly fire. Updated the assertion.

Two additional robustness issues were also identified and fixed in the application code itself:

- **NYSE holiday blindness:** `is_market_open()` only checked for weekends, so the monitor would still poll on Thanksgiving, Christmas, MLK Day, etc. Added `pandas-market-calendars` and a live NYSE calendar lookup to return `False` on exchange holidays. 5 new tests added (4 specific holidays + day-after-holiday sanity check).

- **yfinance MultiIndex columns:** Newer yfinance versions return a MultiIndex DataFrame from `yf.download()`. Accessing `data["Open"]` then returns a single-column DataFrame instead of a Series, silently breaking the price calculation. Added a one-line flatten before the `Open`/`Close` lookups. 2 new tests added.

Total: **30 tests, all passing locally.**

### Summary 4/11/26

| Time | Money | Pain<br>1:😊  5:🤕 |
| ---- | ----- | ------------------- |
| ~2 hrs | | 2/5 - Tests failing on CI was expected given the mobile-only build. Fixes were straightforward once the errors were visible. |

---

## 5 Apr 2026

### Notes Org: Consolidating Action Items into Meeting Notes

A quick follow-up to the 4/4 Notes Org session. The Captain decided to track action items in a separate system, so the standalone `Action Items.md` file was redundant. Rather than simply delete it, the content was merged into `Meeting Notes.md` to make that file more useful on its own.

The result is a single chronological log where actionable items appear as markdown checkboxes (`[ ]`) inline with the meeting notes they came from, and non-actionable context stays as plain bullets. Dates that only existed in `Action Items.md` — 1/23, 3/13, 3/25, and 4/1 — were added as new sections in `Meeting Notes.md`. The completed VDI item on 3/25 was preserved as `[x]`.

`Action Items.md` was deleted. One file instead of two.

### Summary 4/5/26

| Time | Money | Pain<br>1:😊  5:🤕 |
| ---- | ----- | ------------------- |
| ~5 min | | 1/5 - Straightforward merge, no ambiguity. |

---

## 12 Mar 2026

### Running Log: Repo Cleanup

The Captain had mentioned wanting to tidy things up, and that showed clearly in today's work. The `Running Log/` directory had accumulated a lot — all the original 2000s-era HTML source files, the Python scripts, and the generated dashboard were all sitting at the same level with no organization.

We separated things into a cleaner structure:

* All original HTML log files, images, and other assets → `Running Log/source/`
* Analysis and visualization scripts → `Running Log/src/`
* The generated dashboard was renamed from `running_log_dashboard.html` → `index.html` (cleaner URL for the Netlify deployment)
* Updated path references in both `parse_log.py` and `visualize_log.py` to account for the new layout

This was done as a branch and merged via PR #2. The commit message noted "forgot to commit screenshots" — some things are universal.

### Summary 3/12/26

| Time | Money | Pain<br>1:😊  5:🤕 |
| ---- | ----- | ------------------- |
| ~30 min | | 1/5 - Structural cleanup, no surprises. Paths updated cleanly. |

---

## 16 Mar 2026

### Strava API Interface

The natural next step for the running log project: what about *current* running data? The old HTML logs cover 2003–2007, but there's presumably a whole training history sitting in Strava. Today we built a tool to get it out.

The result is `strava-export/export.py`, a self-contained script that:

1. Handles OAuth2 authentication against the Strava API (opens a browser, spins up a local HTTP server on port 8000 to catch the callback, exchanges the code for tokens)
2. Stores and refreshes tokens automatically in `.strava_tokens.json` so you don't have to re-authorize every run
3. Pages through the full activity history via the Strava API
4. Exports to CSV with a rich set of fields: distance, moving time, elevation, heart rate, watts, cadence, suffer score, PRs, kudos, location, gear, and more

The `.env` / `.env.example` pattern was used to keep credentials out of the repo. Two CSV snapshots were generated today (`strava_activities_20260316_141409.csv` and `strava_activities_20260316_154519.csv`), suggesting a couple of runs of the export while refining the field list.

The Strava MCP tools also got wired in — the commit message references the "Strava API interface" broadly, which lines up with the MCP strava tools appearing in the available tool list.

### MATLAB/Simscape Revisited

Also committed today: `rc_model.m` and `setup_simscape_workspace.py`. These look like follow-up work from the 3/10 Simscape session — an RC (resistor-capacitor) circuit model, which is a cleaner, more self-contained thermal/hydraulic analog than the cruise control example. A companion `simscape_builder_review.html` was also generated, likely a report or review interface.

### Running Log Dashboard Updates

The `index.html` diff for today was large (928 lines touched, roughly half the file). Hard to tell without the Captain's notes what specifically changed, but the pattern here has been iterative dashboard polish — new chart features, layout fixes, or additional data.

### Summary 3/16/26

| Time | Money | Pain<br>1:😊  5:🤕 |
| ---- | ----- | ------------------- |
| ~2 hrs | | 2/5 - OAuth setup has its usual friction, but the export worked cleanly. The MATLAB/Simscape thread continues to be the rougher edge. |

To explore:
* [ ] Merge the Strava CSV data into the running log dashboard — the 2003–2007 data and modern Strava data in one view would be satisfying
* [ ] Decide what to do with the two snapshots (deduplicate? pick one as canonical?)
* [ ] Revisit block-resizing issue in Simulink MCP (noted 3/10)

---

## 18 Mar 2026

### Workout App: Explored, Abandoned

The Captain has a Google Sheet ("Chris Workouts") with several months of lift data, organized into ALifts, BLifts, and CLifts tabs. A "Make a Workout" sheet randomizes two exercises from each letter group using Apps Script. The idea: replicate that as an Android app.

We explored several approaches — native Android, React Native, a hosted web app via Netlify. A simple web app using the Google Sheets gviz/tq API seemed like the right call. We built it, deployed it to Netlify (`astonishing-bombolone-4558bf.netlify.app`), and hit a wall: the sheet isn't published to the web, only shared-with-link, so anonymous API calls came back empty. Tried browser automation to do a one-time data ingest from the authenticated session, but the Chrome tools were uncooperative (timeouts, download dialog interference). The Captain chose not to publish the sheet publicly, and manually exporting the data wasn't worth the friction. Project scrapped.

The JS logic was understood clearly: for each of A/B/C, pick 2 random unique rows from the corresponding `*Lifts` sheet. Simple enough to revisit later if the data access problem gets solved.

### Running Log: Netlify Deployment & Auto-Deploy Hook

Two things done here today:

First, the remote `ducktape.netlify.app` was out of date. Deployed the current local `Running Log/index.html` using the Netlify CLI — 127 files uploaded, live immediately.

Second, a quality-of-life hook so this never has to be done manually again. Two hooks added to `~/.claude/settings.json`:

* **PostToolUse** (`Write|Edit`): if the file path contains `Running Log/index.html`, sets a flag at `~/.claude/running-log-deploy-pending`
* **Stop**: if the flag exists, deploys to Netlify and clears the flag

Net effect: any session where `index.html` is changed will auto-deploy at the end of the turn, with a "Deploying Running Log to Netlify..." spinner.

### Summary 3/18/26

| Time | Money | Pain<br>1:😊  5:🤕 |
| ---- | ----- | ------------------- |
| ~1.5 hrs | | 2/5 - The workout app detour was frustrating but the Google auth wall is a real constraint. Netlify hook came together cleanly once jq was swapped for Python. |

To explore:
* [ ] Workout app: revisit if the sheet gets published or data gets exported manually
* [ ] Confirm auto-deploy hook fires correctly next session `index.html` is edited

---

## 4 Apr 2026

### Notes Org: Handwritten Notes → Markdown

The Captain had two months of handwritten work notes (Jan–Apr 2026) scanned as PDFs — one raw scan, one with OCR applied. The OCR quality turned out to be excellent; both files were identical in readable content, so no corrections were needed.

The notes covered a lot of ground: interview prep, content strategy meetings, Simscape Fluids needs analysis, and a running log of action items. Rather than dump everything into one file, the content was split into five themed markdown files in a new `Notes Org/` folder:

- **Interview Prep.md** — questions prepared for a hiring panel, including a scenario around writing a course on the MPC Toolbox
- **Course Strategy & Feedback.md** — reviewer fatigue analysis, the content prioritization framework, swimlane planning, and GenAI-in-training discussions
- **Simscape Fluids Analysis.md** — competitor landscape, needs analysis impressions, Val conversation on curriculum design, thermal management tutorial observations, and Erin M. modeling tips
- **Meeting Notes.md** — chronological log of all dated meetings from Jan–Mar 2026
- **Action Items.md** — all to-dos extracted and formatted as markdown checkboxes, organized by date

The `Notes Org/` folder was created on a feature branch and merged to main via the GitHub UI.

### Summary 4/4/26

| Time | Money | Pain<br>1:😊  5:🤕 |
| ---- | ----- | ------------------- |
| ~30 min | | 1/5 - OCR was clean, organization was straightforward. PDF upload via GitHub web UI was the only friction point. |

---

## 19 Mar 2026

### Simscape Fluids: Pipe (TL) + Tank (TL) Exploration

A focused Simscape Fluids session, working entirely in the Thermal Liquid domain.

**Skills and tooling housekeeping came first.** The Captain asked how to install community-created skills. We found that MathWorks publishes official skills and slash commands on GitHub under the `matlab` org — `matlab/skills` and `matlab/slash-commands`. Both were cloned and installed into `~/.claude/skills/` and `~/.claude/commands/`. Six auto-activating skills (filter design, Live Script, performance optimizer, test creator/runner, UI app builder) and nine slash commands are now available.

The `matlab-live-script` skill was inspected and found to already enforce `.m` plain-text format over `.mlx`. A rule was added to it: prefer `string` and its associated functions (including `compose()` for formatted output), avoid `char` and `sprintf`.

The `simscape-builder` skill (`skill_content.md`) got two additions:
- An **Output format** directive telling it to follow the `matlab-live-script` formatting rules when writing `.m` files, so both skills work together automatically.
- A **block parameterisation rule**: pass the variable name as a string literal (e.g. `'L'`) rather than the evaluated value (`num2str(L)` or `string(L)`), so blocks stay live-linked to workspace variables.
- A **block naming rule**: keep default block names unless multiple instances of the same type need to be distinguished.

**The Pipe (TL) demonstration model** (`pipe_tl_demo.m`) was built as a plain-text Live Script. The model drives water through a 1 m, 10 mm pipe between a 200 kPa upstream reservoir and an atmospheric downstream reservoir, with the pipe wall held at 60 °C. Key result: simulated steady-state flow was 0.568 kg/s at Re = 72,000 (turbulent), far below the Hagen-Poiseuille laminar estimate of 24.2 kg/s — which nicely illustrates why the block uses the Churchill friction correlation rather than assuming laminar flow. The Live Script explains both the friction and thermal effects inline alongside the build code.

During the session we also debugged a `pressure_spec` enum issue on the Reservoir (TL) block — it defaults to `foundation.enum.pressure_spec.atmospheric` regardless of the `reservoir_pressure` value set, and must be explicitly switched to `foundation.enum.pressure_spec.specified`.

### Summary 3/19/26

| Time | Money | Pain<br>1:😊  5:🤕 |
| ---- | ----- | ------------------- |
| ~2 hrs | | 2/5 - Productive. The Reservoir pressure_spec gotcha cost some back-and-forth but is now documented in the skill. Live Script output format working well. |

To explore:
* [ ] Tank (TL) demonstration model in Live Script format
* [ ] Pipe (TL) + Tank (TL) combined demo — revisit `build_pipe_to_tank_tl.m` and rewrite as Live Script with variable-name parameterisation
