# US English conversion — follow-up work

**Dated 2026-09-07.** Cross-cutting, so it sits at the `Specs/` root rather than
under a per-dashboard folder.

Commit `7a9a7ad` converted the repo's **docs and agent files** to US English:
111 replacements across 18 tracked `.md` and `.claude/` files. This file records
what that pass deliberately left behind, and what it turned up along the way.

Nothing here is urgent. None of it breaks anything today.

---

## 1. Python comments and docstrings — mechanical, safe

**135 occurrences across 27 tracked `.py` files.** Of the ones matching the
common stems, roughly **41 are in strings/docstrings and 23 in comments** — pure
prose that can be converted the same way the docs were, with no functional risk.

| File | Hits |
|---|---:|
| `strava-data/feed/svg.py` | 39 |
| `strava-data/tools/poster_40for40.py` | 16 |
| `strava-data/feed/cards.py` | 14 |
| `strava-data/tools/proof_year_art.py` | 9 |
| `strava-data/tools/gen_poster_glyphs.py` | 8 |
| `strava-data/feed/page.py` | 7 |
| `strava-data/feed/metrics.py` | 6 |
| *21 more files* | 1–5 each |

Note that `proof_year_art.py` and its `year-art/README.md` were written during
the same session as the conversion, so the README is US English while the script
beside it is not. That inconsistency is the most visible instance.

**Care needed:** the same guard the docs pass used — never rewrite inside code —
does not translate to a `.py` file, where the whole file is code. A converter
here has to work the other way round: only touch `tokenize.COMMENT` and
`tokenize.STRING` tokens, never `NAME`.

## 2. Python identifiers — a functional rename, not a docs edit

**45 occurrences are identifiers**, and renaming them changes the API surface of
the `feed` package. This is why it was split out rather than bundled in.

Two actual definitions:

- **`normalise(pts)`** — `strava-data/feed/places.py:160`. Imported and called
  from `strava-data/feed/metrics.py:542,557`, called within `places.py:156`, and
  named in a docstring in `geo.py:52`. `Project Docs/Specs/strava-data/route-mosaic.md`
  documents it by name, which is why the docs pass left that one backtick alone.
- **`centre(ring)`** — `strava-data/tools/gen_poster_glyphs.py:79`.

Plus a parameter name used widely:

- **`colour=`** is a keyword parameter on at least nine functions in
  `strava-data/feed/svg.py` (`_g`, `glyph_runner`, `glyph_bike`, `glyph_shoe`,
  `glyph_mountain`, `_fill`, `_ell`, `_stroke`, `_eye`, and the inner `glyph`),
  and **`fill_colour=` is passed as a keyword argument** from
  `strava-data/feed/cards.py:382`. So this is a cross-module rename, not a
  local one.

**If this is done:** rename definitions and every call site in one change, then
rebuild the feed and run `uv run python tools/epaper_check.py` — the 63 cards
exercise the glyph functions, and a missed keyword argument fails at render
time, not at import time.

**Or don't.** The identifiers are internal and self-consistent, and the docs now
describe them accurately (`route-mosaic.md` reads "normalizes via `normalise()`",
which is correct on both halves). Leaving them is a defensible choice.

## 3. Seven broken relative links in docs — pre-existing

Found while verifying the conversion, and **confirmed present at `HEAD` before
it** — the conversion introduced none of them.

| File | Broken target |
|---|---|
| `Project Docs/Plans/running-log/performance-section-redesign.md` | `../Handoffs/running-log/session-handoff.md` |
| " | `../Specs/running-log/design_handoff_running_log/readme.md` |
| " | `../../CLAUDE.md` |
| `Project Docs/Plans/strava-data/wbgt-future-work.md` | `../../strava-data/weather.py` |
| " | `../../strava-data/dashboard/charts_exploratory.py` |
| " | `../../strava-data/dashboard/template.py` |
| " | `../../strava-data/dashboard/page.py` |

The first three look like relative-depth mistakes that would resolve with the
right number of `../`. The `wbgt-future-work.md` ones point at
`strava-data/weather.py`, which does not exist — that doc may predate a
refactor, so check whether the file was renamed or the work was never done
before "fixing" the paths.

## Explicitly out of scope — do not convert

- **`running-log/running_log.csv` (14), `strava-data/data/*.csv` (13).** These
  are activity records — your own workout titles and segment names. They are
  data, not prose, and `data/` is owned by the fetch workflow, which would
  overwrite edits anyway.
- **`running-log/source/**`.** The 2003–2007 HTML logs are the *input* to
  `parse_log.py`. They are historical documents; editing them rewrites the past
  and risks changing what the parser sees.
- **Binary files.** `Hadd.doc` (21 apparent hits) and several `.jpg` files match
  only because a byte scan finds letter sequences inside them. Any tool doing
  this pass must filter to text files by extension, not by whether a regex
  matches.

## The converter

Written as a one-off in the session scratchpad and **not committed** — it was a
migration tool, not something the repo needs to keep. If this is picked up
again, the three things it had to get right:

1. **Skip fenced code blocks and inline backticks** (for docs), or restrict to
   comment and string tokens (for Python). `normalise()` in a doc names a real
   function; "correcting" it breaks the reference.
2. **Handle stems that drop a trailing `ue`/`re` explicitly.** Naive
   stem-plus-suffix produces `catalogd` and `centerd`. Both were caught in a dry
   run before applying.
3. **Split on `\n` only and write with `newline=""`.** The working copy is CRLF;
   `splitlines()` plus a rejoin rewrites every line ending and buries the real
   change in a whole-file diff. The committed pass is `+108/−108`.

Always dry-run and read the tally before applying.

## Related, tracked elsewhere

The year-art piece has its own open questions — bloom color by month vs. sport,
file size, keyboard access, metric morph — in
[`../Plans/strava-data/year-art/README.md`](../Plans/strava-data/year-art/README.md).
They are not repeated here.
