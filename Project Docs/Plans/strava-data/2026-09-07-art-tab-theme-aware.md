# Make the Art tab theme-aware

## Context

The "Years in Motion" piece on the Strava dashboard's **Art** tab is hardcoded dark. When it
was built I made that a deliberate decision — the palette is tuned against near-black, and I
reasoned it would read as "a framed print on the card" in light mode. That decision is written
into `dashboard-spec.md:1988-1990` as a rule, and repeated as comments in `art_year.py:49-50`
and `ART_CSS:316-319`.

It was the wrong call: the rest of the dashboard follows the light/dark/system toggle, and a
panel that ignores it reads as a bug, not a choice. This plan reverses it.

**Decisions taken (fixed):**
- **Light = clean white.** The ground matches `--bg-elevated` (`#ffffff` in light) so the piece
  sits flush with the card, and the sport palette is darkened for legibility on white. It is a
  retuned palette, not an inversion — the dark hexes at 0.9px on white are near-invisible.
- **Dashboard tab only.** The static `year.svg` and the four proof SVGs keep their current dark
  appearance, unchanged — they are print-export starting points and must render in tools that do
  not implement `var()`.
- **`year.html` is retired** (Step 0). It was the standalone preview built before the Art tab
  existed; the tab supersedes it. Removing it leaves `art_fragment()` with a single consumer,
  which simplifies the rest of this plan.

## Approach

**CSS custom properties only. No JavaScript.** The Overview activity heatmap already solves this
exact problem — hand-built SVG emitting `fill="var(--accent)"` as a presentation attribute
(`strava-data/dashboard/charts_production.py:124,138`), themed purely by CSS, with
`running-log/qa.py:306-324` locking it in. The art SVG is inline in the document, so `:root`
custom properties cascade into it the same way.

`ART_JS` reads no colors, so it needs no change. `applyChartTheme()` stays uninvolved — that half
of the old spec claim remains true and is worth keeping.

### The load-bearing detail: gate on the existing `interactive` flag

`year_layer()` (`art_year.py:208`) already takes `interactive`, and both output paths go through
it — `art_fragment()` (ships `ART_CSS`) and `static_svg()` (`art_year.py:486`, ships nothing).

- `interactive=True` → emit `var(--art-run, #2dd4bf)`
- `interactive=False` → emit `#2dd4bf`, byte-identical to today

This is stronger than relying on `var()` fallbacks alone, because `year.svg` is a standalone file
a rasterizer may open (cairosvg, resvg, Inkscape, design tools) and **none of them implement
`var()` — they fail to black, not to the fallback.** Keep the static path literal and the question
never arises. Still write the `#literal` fallback into the interactive strings as cheap insurance
against the fragment ever being embedded without `ART_CSS`.

After the `year.html` removal below, `art_fragment()` has exactly one consumer — the dashboard —
so the gate's only remaining job is protecting `static_svg()`.

## Tokens

Declare at the top of `ART_CSS` (`art_year.py:315`) on `:root` / `:root.light`. A body `<style>`
may target `:root`, and `:root.light` (0,2,0) beats `:root` (0,1,0).

Use **independent `--art-*` tokens with literal hexes** — do not indirect through `--running` /
`--mtb`. Hairline art strokes want more contrast than a 3px Plotly line, so the values diverge
anyway, and retuning the chart palette should not silently retune a framed art piece.

| token | dark | light | notes |
|---|---|---|---|
| `--art-run` | `#2dd4bf` | `#0d9488` | matches `--running` light |
| `--art-mtb` | `#f59e0b` | `#b45309` | a step darker than `--mtb` light; hairlines |
| `--art-foot` | `#a3e635` | `#4d7c0f` | |
| `--art-snow` | `#60a5fa` | `#1d4ed8` | |
| `--art-other` | `#f472b6` | `#be185d` | |
| `--art-bg` | `#0b0f14` | `#ffffff` | ground, halo strokes, scrim stops; `= --bg-elevated` light |
| `--art-line` | `#243244` | `#cbd5e1` | month spokes + inner ring |
| `--art-month` | `#7c8ba1` | `#64748b` | month labels |
| `--art-num` | `#e2e8f0` | `#0f172a` | year numeral, readout name |
| `--art-stat` | `#94a3b8` | `#475569` | readout stat line |
| `--art-sub` | `#64748b` | `#64748b` | subtitle, readout date + sport |
| `--art-partial` | `#f59e0b` | `#c2710c` | picker dot |
| `--art-trace-op` | `.38` | `.30` | darker inks deposit more contrast |
| `--art-spoke-op` | `.9` | `1` | thin dark strokes on white are fragile |
| `--art-dim-spoke` | `.24` | `.18` | dimming toward white is weaker than toward black |
| `--art-dim-trace` | `.13` | `.09` | |
| `--art-off` | `.04` | `.05` | |
| `--art-glow` | `drop-shadow(0 0 5px currentColor)` | `none` | a glow on white reads as a print defect |

The five light family hexes are the Tailwind-700 relatives of the dark 400s: same hue family,
≥4.5:1 on white, still mutually distinguishable at 1px.

## Changes

### Step 0 — retire `year.html`

Do this first: it removes a consumer of `art_fragment()` and shrinks everything after it.

`year.html` was the standalone preview of the piece, built before the Art tab existed. Its own
README calls it "the piece standalone — same fragment the Art tab renders, in a bare page," which
the Art tab now is. It is ~0.7 MB of committed duplication, built by nothing automated, and not
published (Pages serves `running-log/`, not `Project Docs/`).

- **`strava-data/tools/proof_year_art.py:266-280`** — delete the block that builds the bare HTML
  shell and writes `year.html`.
- **`strava-data/tools/proof_year_art.py:20`** — drop `art_fragment` from the import list; it
  becomes unused. Keep `ART_BG`/`BG` (still used by the proof-sheet CSS) and `static_svg`.
- **`git rm "Project Docs/Plans/strava-data/year-art/year.html"`**
- **`Project Docs/Plans/strava-data/year-art/README.md:55`** — drop the Output table row.

**Must still work afterward:** `static_svg()` is *not* dead. `concept_year()`
(`proof_year_art.py:184-187`) calls it and is registered in `CONCEPTS` (line 190), which drives
both `year.svg` and the `proofs.html` contact sheet. Rerun the tool and confirm the four proof
SVGs plus `year.svg` are still produced and byte-identical.

### `strava-data/dashboard/art_year.py` — the whole implementation

1. **Token blocks** at the top of `ART_CSS`, plus these rules:
   - `#art-svg #art-scrim stop{stop-color:var(--art-bg)}` — belt-and-braces for the `<defs>` case
   - `#art-svg .art-trace{opacity:var(--art-trace-op)}` and `#art-svg .art-spoke{opacity:var(--art-spoke-op)}`,
     placed **above** the existing `.sel`/`.on` rules so those still out-specify
   - `background:ARTBG` → `background:var(--art-bg)` (line 322)
   - `.partial::after` color → `var(--art-partial)` (line 346)
   - `.art-spoke.on{filter:var(--art-glow)}` (line 326)
2. **Delete `.replace("ARTBG", ART_BG)`** at line 565.
3. **Two helpers** next to `COLOR`, so every call site reads alike and QA can grep one pattern:
   ```python
   def paint(key, interactive):
       return "var(--art-%s, %s)" % (key, COLOR[key]) if interactive else COLOR[key]
   def ink(token, literal, interactive):
       return "var(--%s, %s)" % (token, literal) if interactive else literal
   ```
4. **Convert `year_layer()` sites** (231 traces, 243 month spokes, 248-250 labels + halo,
   254 ring, 275-278 spokes, 282-285 numeral + halo, 287-289 subtitle + halo) through the helpers.
   Add `class="art-ring"` / `class="art-mon"` **on the interactive branch only** — classes, not
   structural selectors, so QA can assert them and group reordering can't break them.
5. **Fragment-only sites** (no gating needed): `halo` (537), `#art-rd-*` fills (539-547),
   scrim stops (568-571), ground rect (572).
6. **Leave `static_svg()` (486-498) completely untouched.**
7. **Legend swatch** (554): drop the inline `style="background:#hex"` — inline style beats every
   author rule — and emit `<i class="art-sw art-fam-%s"></i>`, colored from `ART_CSS`. Check first
   that `ART_JS` selects legend buttons by `[data-fam]` on the `<button>`, not via the `<i>`.

### `strava-data/qa.py` — a regression check

Add `check_art_theme_vars(rows, html)` and register it in `CHECKS` (line 234) as
`("Art -- Theme", check_art_theme_vars)`, matching the existing `(label, fn)` / `(rows, html)`
convention. Assert against the `<svg id="art-svg">` slice and the art `<style>`:

1. No `stroke="#`, `fill="#`, `stop-color="#` in the slice (allow `fill="none"`, `stroke="transparent"`)
2. The `--art-*` vars are actually present in the slice
3. **The `:root` and `:root.light` `--art-*` name sets are equal** — this is the check that earns
   its keep, catching a token added to dark and forgotten in light, which is invisible in a
   dark-mode screenshot
4. `"ARTBG" not in html`, and `background:var(--art-bg)` present — guards the likeliest silent miss
5. No `style="background:#` in `#art-legend`
6. **`year_layer(..., interactive=False)` output contains no `var(--`** — the guard on the
   print/standalone contract; without it a future refactor that hoists var-emission out of the
   branch passes every other check

> **Caveat worth knowing:** `strava-data/qa.py` is **not run by CI**. Both workflows run only
> `running-log/qa.py`, which reads `running-log/index.html` and cannot see the art at all
> (`.github/workflows/pr-checks.yml:78`, `running-log/qa.py:18`). So this check is manual /
> agent-invoked, like the rest of the Strava suite. Wiring `strava-data/qa.py` into `pr-checks.yml`
> is a separate, larger decision — flag it, don't bundle it.

### Docs

- **`Project Docs/Specs/strava-data/dashboard-spec.md:1988-1990`** — replace the "keeps its own
  dark ground in both themes" rule with the new one: themed by CSS custom properties alone,
  `applyChartTheme()` still uninvolved, `--art-bg` in light equals `--bg-elevated` so it sits flush
  with the card. Line ~2034's acceptance bullet must become the light-mode assertions below.
- **`art_year.py:49-50`** and **`ART_CSS:316-319`** — `ART_BG` survives as the dark literal and the
  static-path ground; say so, and say why the static path stays literal (rasterizers, no `var()`).
- **`Project Docs/Plans/strava-data/year-art/README.md`** Output table — the `year.html` row is
  removed in Step 0; add a Theme note to what remains: the Art tab follows the page toggle, while
  `year.svg` and the proof SVGs are emitted with literal colors and stay print-ready in any
  renderer.

## Traps

1. **The `ARTBG` replace at line 565** — leave it and a literal survives in `#art-svg{background:…}`,
   quietly defeating light mode. Most likely silent miss.
2. **Don't put `var()` in numeric attributes.** No precedent in this repo for `opacity="var(…)"`,
   and `stroke-width` is data-derived. Keep the literal attribute (static needs it) and override
   from CSS on the classes, which exist only when interactive.
3. **`stop-color` inside `<defs>`** is the case with least in-repo precedent — hence the explicit
   `#art-svg #art-scrim stop` rule alongside the attribute.
4. **The scrim's baked `stop-opacity` needs no change.** It is a relationship to the ground, not to
   a color: once `stop-color` follows `--art-bg`, white-at-0.93 knocks the bloom back in light
   exactly as black-at-0.93 does in dark. Don't add unused opacity knobs.
5. **Do the static byte-diff gate early** (step below), before touching docs or QA. If the proof
   SVGs differ, the `interactive` gating is wrong and everything after it is built on sand.

## Order

0. Retire `year.html` (Step 0 above); rerun the tool and confirm the proof SVGs are unchanged
1. Token blocks + new CSS rules in `ART_CSS`; delete the `ARTBG` replace
2. `paint()` / `ink()` helpers
3. Convert `year_layer()` sites, gated; add `art-ring` / `art-mon` classes
4. Convert fragment-only sites; leave `static_svg()` alone
5. Legend swatch → class
6. **Gate:** rerun `uv run python strava-data/tools/proof_year_art.py`, then
   `git status` on `Project Docs/Plans/strava-data/year-art/*.svg` → **zero diff**
7. Rebuild dashboard, browser verification
8. Docs, QA check

## Verification

Build (`uv run python strava-data/build_dashboard.py`), serve `running-log/` on **127.0.0.1**,
open `strava.html#art` at 1280px.

**Measure computed style, not screenshots** — a failed `var()` substitution renders as *black*,
which is nearly invisible on a dark ground but obvious to `getComputedStyle`.

```js
const cs = el => getComputedStyle(document.querySelector(el));
({ light: document.documentElement.classList.contains('light'),
   svgBg: cs('#art-svg').backgroundColor,
   run:   cs('#art-svg .art-fam-run.art-spoke').stroke,
   ring:  cs('#art-svg .art-ring').stroke,
   halo:  cs('#art-svg .art-mon').stroke,
   scrim: cs('#art-scrim stop').stopColor,
   traceOp: cs('#art-svg .art-trace').opacity,
   glow:  cs('#art-svg .art-spoke').filter,
   swatch: cs('#art-legend .art-fam-run').backgroundColor })
```

| | dark | light |
|---|---|---|
| `svgBg` | `rgb(11, 15, 20)` | `rgb(255, 255, 255)` |
| `run` | `rgb(45, 212, 191)` | `rgb(13, 148, 136)` |
| `ring` | `rgb(36, 50, 68)` | `rgb(203, 213, 225)` |
| `halo` | `rgb(11, 15, 20)` | `rgb(255, 255, 255)` |
| `scrim` | `rgb(11, 15, 20)` | `rgb(255, 255, 255)` |
| `traceOp` | `0.38` | `0.3` |
| `glow` | `drop-shadow(…)` | `none` |

**Any `rgb(0, 0, 0)` means `var()` did not substitute** — watch `scrim` (the `<defs>` case) and
`halo` (the `paint-order` case) especially.

Then:
- **Toggle without reload**, re-run the block, assert every value flipped; console clean.
- **System mode**: set the toggle to System and flip the OS scheme — the art must follow with no
  `applyChartTheme()` involvement.
- **Reload in light**: no dark flash. `THEME_INIT_JS` (`template.py:749-765`) sets `.light`
  pre-paint and the art has no JS colorization, so there should be none.
- **Flush check**: `#art-svg` and `#view-art .card` background both `rgb(255,255,255)`.
- **Interaction in light**: hover a spoke → readout fills, spoke + its trace light, others dim to
  `0.18`; `.on` spoke shows `filter: none`, `opacity: 1`. Toggle a family off, switch year, confirm
  the filter survives.
- **Contrast**: each light `--art-*` family vs `#ffffff` ≥ 3:1 (graphical-object threshold); all
  five proposed values clear 4.5:1.
- **Static path**: rerun `proof_year_art.py`; `git status` on
  `Project Docs/Plans/strava-data/year-art/*.svg` shows **zero diff**, and `proofs.html` still
  builds. Open `year.svg` directly (no stylesheet) — it must look exactly as today, with no
  `var(` anywhere in the file.
- `uv run python strava-data/qa.py` passes, including the new check.

## Critical files

- `strava-data/dashboard/art_year.py` — the entire implementation
- `strava-data/tools/proof_year_art.py` — Step 0: drop the `year.html` builder (266-280) and the
  now-unused `art_fragment` import (20)
- `strava-data/qa.py` — the regression check
- `Project Docs/Specs/strava-data/dashboard-spec.md` — the rule being reversed (~1988-1990, ~2034)
- `Project Docs/Plans/strava-data/year-art/README.md` — theme note
- `strava-data/dashboard/template.py` — reference only: tokens at 15-63, theme plumbing at
  749-765 / 1382-1387
- `strava-data/dashboard/charts_production.py:124,138` — the `var()`-in-SVG precedent to follow
