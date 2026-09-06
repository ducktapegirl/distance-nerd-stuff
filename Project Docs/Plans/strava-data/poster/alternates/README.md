# 40 for 40 — the three layouts that were not chosen

A decision record, not a build step. Four layouts were rendered from the real 2025 tracks and
put side by side; **A won** and became
[`strava-data/tools/poster_40for40.py`](../../../../../strava-data/tools/poster_40for40.py).
The other three are kept here because otherwise they would exist nowhere.

Open the `.svg` files in a browser, or run the script for a contact sheet of all four:

```bash
uv run python "Project Docs/Plans/strava-data/poster/alternates/proofs.py"
```

| | Layout | What it is | Why it lost |
|-|--------|-----------|-------------|
| A | **The Grid** | 5×8 small multiples, uniform cells, aspect-fitted, date under each | **Chosen.** Calm and gallery-like, and every route gets equal billing |
| B | **The Mosaic** | Squarified treemap; tile area is proportional to miles, tinted by sport | The most literal reading of the e-paper mosaic card and the most honest about scale, but busy: Whitney dominates and the short routes shrink to chips |
| C | **Ridgelines** | Forty elevation profiles stacked by date, heights square-root scaled | The most unusual of the four — skis saw-tooth, hikes tower, runs ripple — but dense, and it reads as a chart rather than as art |
| D | **The Year Ring** | Routes on a clock face, January at 12, size proportional to the square root of miles, a typographic 40 at the centre | Strong focal point and the most birthday-like, but it gives each route far less room than the grid does |

## The script is frozen at the proof stage

`proofs.py` is the script **as it stood when the choice was made**, so it reproduces exactly what
was compared — the four `.svg` files here are byte-identical to a fresh run. Its selection rules
have since diverged from the shipped poster:

- quotas differ, and there is no `SUB_QUOTA` reserving slots for trail runs;
- road bikes and e-bikes are still their own family, rather than mountain-bike-only;
- trail running still has its own colour, rather than merging into running;
- snow is one family, not split into downhill and nordic;
- there is no region reservation and no route-similarity test, so it can pick two laps of the
  same loop;
- the legend is text, not the continuous-line figures.

So re-running it shows the alternates **as they were seen**, not as they would look under
today's rules. Rebuilding B, C or D on the current selection would mean refactoring `render()`
in the shipped tool into per-layout functions behind a `--layout` flag.

Canvas and palette are shared with the shipped poster: 1600×2000 user units for 16×20 in at 100
units per inch, ground `#F5F0E6`, ink `#2B2A28`.
