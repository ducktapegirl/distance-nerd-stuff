# Future work: BYOD — making `strava-data/` forkable (bring your own data)

**Status:** proposed / design decisions resolved · **Created:** 2026-07-18 · **Owner:** unassigned
**Depends on:** [`adaptive-superlatives-future-work.md`](adaptive-superlatives-future-work.md) —
its Phase 3 owns two of the fork-blocking bugs below; land that first.

## Why

Today the README says it outright: *"you can't just clone this and get a working dashboard with
your own data."* This doc plans the work to reverse that for `strava-data/` — someone forks the
repo, plugs in their own Strava API credentials, and gets a working dashboard of **their** data —
while making the repo's structure legible enough that a forker clearly knows the entry point.

**Explicit scope boundary, stated up front: `Running Log/` is NOT part of this.** It's the
athlete's personal pre-Strava archive (2003–2007 hand-kept HTML logs), parsed into a page that is
inherently one person's history. A forker should ignore it entirely — and the docs this plan
produces must say so prominently, because the repo layout actively obscures this today: the Strava
dashboard's build output (`strava.html`) lands *inside* the `Running Log/` folder, since that
folder doubles as the GitHub Pages publish root (`deploy.yml` `upload-pages-artifact
path: "Running Log"`; `dashboard/config.py:16` `OUT_HTML`).

Honest framing: this is real work with a real maintenance cost, and the athlete is genuinely
unsure it's worth doing. The audience is general open-source polish — no specific person is
waiting on a fork. That ambivalence is why the effort bar below is deliberately conservative.

## What "forkable" should and shouldn't mean

- **In:** fix the outright bugs and leaks a fork would hit (crashes, false content, analytics
  leaking to the original athlete's account), remove personal data a fork shouldn't ship, and
  write the docs a stranger needs (entry point, what to change, credential setup from zero).
- **Out:** no config wizard, generator, or interactive onboarding tool. No repo restructuring, no
  file moves, no changing the live GitHub Pages URL. Forkers hand-edit a documented list of
  files; the docs make the list short and findable, not zero.

## Design decisions (resolved 2026-07-18)

Walked through explicitly (three question rounds + a full-repo audit for hardcoded personal
assumptions) — pinned here so the phases below aren't re-litigating settled ground.

- **One root-level `FORKING.md` is the entry point.** Not per-folder READMEs, not just expanding
  the README's "Poking at the code" section. One place that says: what's forkable
  (`strava-data/`), what to ignore (`Running Log/`), the change-checklist, and why `strava.html`
  publishes inside a folder named "Running Log" (intentional Pages-root plumbing, not a mistake).
- **Formally depends on the adaptive-superlatives plan.** That plan's Phase 3 already covers the
  home-box crash (`_SD_BOX`/`_BOS_BOX` at `charts_places.py:33-34`; `_centroid()` divide-by-zero
  at `:338`) and the Peaks false-claims bug (`_peaks_data()` appends rows unconditionally,
  `:1913-1948`). This plan references those as prerequisites — one source of truth, no re-doing.
- **`strava-export/` gets deprecated AND its checked-in personal CSVs removed.** The audit found
  it isn't just confusing legacy code sitting next to `strava-data/` — it contains **real
  checked-in Strava activity exports** (`strava_activities_2026*.csv`, ~56 KB each) that every
  fork would ship. `git rm` them from the current tree (recoverable from old commits; a full
  git-history purge is explicitly out of scope — see Non-goals). Also note `fetch.py:23-26,49-61`
  actively *prefers* `../strava-export/.env`/`.strava_tokens.json` over its own local copies —
  harmless fallback behavior, but its comments point a forker at the deprecated tool; fix the
  docstring when the deprecation lands.
- **Cosmetic personalization: emoji yes, prose no.** `RUN_EMOJI`/`MTB_EMOJI` (gendered woman
  running/biking emoji, `config.py:91-92`, consumed at `page.py:179,184` and
  `rollups_cards.py:151,187`) become an explicit, documented config toggle. But gendered
  **chart-title prose** ("She Pays Pace, Not Heart, for Heat" — `charts_exploratory.py:465`,
  rendered at `page.py:498,535`) is **editorial voice, not a mechanical bug** — same reasoning as
  the superlatives plan not auto-rewriting trip captions. Documented as hand-editable, not
  abstracted.
- **"San Diego"/"Boston" literal UI text is a documented limitation, not a fix.** Even once the
  home *boxes* are configurable (superlatives plan), the city names appear as literal strings:
  card titles (`charts_places.py:682-683`), the hero aria-label (`:1014`), View buttons
  (`:1027-1028`), footer copy (`:2170`). Generalizing to arbitrary home cities is a structural
  change beyond this plan's effort bar. `FORKING.md` lists the exact locations for hand-editing.
- **A new BYOD setup walkthrough doc, separate from `Handoffs/migration.md`.** migration.md is
  "notes to remind future-me" — it assumes an existing Strava API app, GH_PAT, and SMTP creds. A
  stranger needs the from-zero version: registering a Strava API application, first-time OAuth
  token bootstrap, the GitHub Actions secrets, MapTiler signup.
- **`strava-data/.env.example` is a new concrete deliverable.** None exists today — only
  `strava-export/.env.example` (for the deprecated tool). A forker currently has to
  reverse-engineer the env vars from `fetch.py:56-57`.

## Hardcoding checklist (ordered by how much each blocks/harms a fork)

1. **GoatCounter analytics leak — `page.py:338`.** The published HTML hardcodes
   `ducktapegirl.goatcounter.com`; a fork that misses this silently reports **its visitors'
   traffic to the original athlete's analytics account, forever**. Worse than a crash (a crash is
   visible; this never is). Fix: env-var it like `MAPTILER_KEY` (`config.py:36` pattern) with
   empty → omit the snippet entirely.
2. **Home-box build crash** — owned by the superlatives plan's Phase 3 (guard `_centroid()`, make
   the home boxes configurable). Referenced here as a prerequisite, not re-planned.
3. **Peaks false claims** — likewise owned by the superlatives plan (skip-on-no-match guard +
   editorial config extraction). Referenced, not re-planned.
   - **3b. Residual:** the "San Diego"/"Boston" literal UI text above survives box
     configurability — known limitation, hand-edit list in `FORKING.md`.
4. **MapTiler key domain restriction** — already env-var based (fork-friendly mechanically), but
   the forker needs their own MapTiler account with the key domain-restricted to **their** deploy
   domain (`config.py:32-36`, `deploy.yml:48-51`). Docs item, no code change.
5. **`MAP_CENTER_LAT`/`MAP_CENTER_LON` dead code — `config.py:86-88`.** Audited: zero references
   anywhere; the `chart_map()` they served was retired when Places landed. Delete, don't
   generalize.
6. **Gendered emoji → config toggle** (`config.py:91-92`); gendered chart prose → explicit
   non-goal (see decisions).
7. **`strava-export/` — deprecate + remove personal CSVs** (see decisions; includes the
   `fetch.py` credential-fallback docstring cleanup).
8. **Missing `strava-data/.env.example`** — new file, part of the setup-walkthrough deliverable.

Audited clean, for the record: `pyproject.toml`/`uv.lock`, `template.py`, `theme.py` are fully
generic; no segment-name string literals gate logic outside the superlatives `sig` matching; the
only remaining personal-name leakage is out-of-scope surfaces (`Claude's Log.md`, a personal
Python path in `.claude/agents/strava-qa.md:15` — optional low-priority cleanup).

## New setup walkthrough doc (outline)

Path TBD (likely `Docs/` doesn't exist — sensible home is next to `FORKING.md` or under
`Handoffs/`; decide at build time). Contents:

- Register a Strava API application from zero → `client_id`/`client_secret`.
- Local setup: copy `strava-data/.env.example`, first-time OAuth token bootstrap →
  `.strava_tokens.json` (both gitignored).
- GitHub Actions secrets checklist — all 8: `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`,
  `STRAVA_REFRESH_TOKEN`, `GH_PAT`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_TO`, `MAPTILER_KEY` —
  flagging that `GH_PAT` needs a **classic PAT with Secrets: write** (token rotation,
  `strava-fetch.yml:104-114`), a common stumbling block.
- MapTiler: create account, get key, domain-restrict to your Pages domain; absent key degrades
  gracefully to the Glow-only hero.
- SMTP alerting is optional — the workflow skips it cleanly when unset
  (`strava-fetch.yml:135-137`).

## `FORKING.md` (outline)

- **Lead with the split:** fork `strava-data/`; ignore `Running Log/` (personal archive).
- Why the Strava dashboard's HTML publishes into `Running Log/` (Pages-root plumbing — expected,
  don't "fix" it).
- The change-checklist (condensed from the table above): analytics, MapTiler key, home boxes +
  superlatives config (per the superlatives plan), emoji toggle, the hand-edit list for city
  names and chart prose.
- Known limitations: two-homes narrative is structural; basemap/hillshade assets are clipped to
  North America (lat ~24–55, lng ~-135–-60) — regeneration tooling exists and is documented in
  `tools/gen_basemap.py` / `tools/gen_hillshade.py` docstrings.
- Pointers: setup walkthrough, superlatives plan, this plan.

## Suggested phases

1. **Prerequisite:** confirm the adaptive-superlatives plan (at minimum its Phase 3 fork
   hardening + config extraction) has landed.
2. **Small fixes:** env-var the GoatCounter snippet; delete `MAP_CENTER_*`; emoji config toggle.
3. **Deprecate `strava-export/`:** deprecation note, `git rm` the personal CSVs, fix `fetch.py`'s
   credential-fallback docstring.
4. **`strava-data/.env.example`.**
5. **Write the BYOD setup walkthrough.**
6. **Write root `FORKING.md`.**
7. **Update `README.md`:** retire the "you can't just clone this" paragraph in "Poking at the
   code" (point at `FORKING.md` instead); this plan is already in the Future-work list.
8. **QA — synthetic fork smoke test** (mirrors the superlatives plan's QA): clone fresh, empty
   `data/`, no credentials → build either succeeds degraded or fails with a clear message, never
   crashes; published HTML contains no `goatcounter` reference when unset; walk the checklist
   as-written and note anything it missed.

## Non-goals (explicit)

- **Git-history purge** of `strava-export/`'s CSVs — history rewrite is its own decision, out of
  scope here; current-tree removal only.
- **Generalizing the two-homes narrative** (arbitrary home cities/names) — structural, exceeds
  the effort bar; documented hand-edit instead.
- **De-gendering chart prose via config** — editorial voice; hand-edit.
- **Non-North-America basemaps** — documented with existing regen tooling, not rebuilt.
- **Any wizard/onboarding tooling** — docs only.

## Related

- **Hard dependency:** [`adaptive-superlatives-future-work.md`](adaptive-superlatives-future-work.md)
  (owns the home-box and Peaks fork-safety fixes; its `superlatives.json` extraction is what makes
  the editorial content forkable at all).
- Sibling docs: [`places-plan.md`](places-plan.md), [`places-future-work.md`](places-future-work.md),
  [`wbgt-future-work.md`](wbgt-future-work.md).
