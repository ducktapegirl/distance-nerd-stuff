# Future work: Places hero — narrow-phone (<=360px) chrome crowding

**Status:** known issue / not started · **Created:** 2026-07-14 · **Owner:** unassigned

## Why

Found during the zoom-controls QA pass (commit `e7094cd`), not something that pass
introduced — confirmed via a canvas pixel-scan against the pre-change baseline that this
already existed. Documenting here rather than leaving it only in a commit message /
`dashboard-spec.md` verify-note, per the athlete's request for a standing to-do file.

## The problem

On mobile the hero's `.places-controls` (View + Map segmented-control rows) sits at the
bottom, and `.places-foot` (sport legend + activity/region/state stat line) is anchored
to the very bottom edge. Both are sized by their content, which wraps to 2 lines each at
narrow widths — so the available vertical gap between the on-canvas home labels (drawn on
`<canvas>`, not the DOM, so their position is data-driven and can't be measured/avoided
with CSS alone) and the footer is **genuinely too small to fit the controls block without
touching one side or the other** on the narrowest common phone widths.

Verified by canvas pixel-scanning (the labels are canvas pixels, not DOM — a real check,
not a guess) across four widths, both BEFORE (baseline, 96px controls offset) and AFTER
(commit `e7094cd`, 116px offset + shrunk footer) the zoom-controls fix:

| Width | Before: footer/legend collision | Before: on-canvas label collision | After: footer/legend | After: label |
|---|---|---|---|---|
| 430px (large) | yes | no | **fixed** | no |
| 390px (iPhone-class) | yes | no | **fixed** | no |
| 360px | yes | yes (~10px) | **fixed** | worse (~30px) |
| 320px (legacy/SE-class) | yes | yes (~18px) | **fixed** | worse (~38px) |

The footer/legend collision (the originally-reported bug) is fixed on every width tested.
The deeper on-canvas-label collision on <=360px widths is improved in absolute terms
(footer no longer eats into the available gap) but the controls block itself (146px tall:
fullscreen button + View row + Map row, each with gaps) is **taller than the available
gap** on these widths, so some overlap with the label band remains.

## Root cause

`.places-controls` bundles three stacked rows (fullscreen toggle, View filter, Map
filter) into one 146px-tall block, positioned as a single absolutely-positioned unit.
There is no viewport width at which a 146px-tall block reliably fits between the
data-driven label band and the footer on a <=360px-wide phone — the two constraints
were never really compatible at that block height in this layout.

## Fix options (pick one)

**A — Move the fullscreen toggle out of `.places-controls` (recommended).** It's really
its own "map utility" affordance, same category as the new zoom cluster, not a filter.
Making it an independent absolutely-positioned element (sitting just above the `.places-
zoom` cluster on mobile, matching desktop's current visual position via CSS math) shrinks
`.places-controls` to 2 rows (~96px), which *should* fit the available gap even at 320px
— re-verify empirically with the same pixel-scan technique before shipping.

**B — Hide the sport legend on mobile.** The route colors are already visible on the map
itself; the legend is somewhat redundant on a screen this small. Removing it would shrink
`.places-foot` by roughly half, likely enough on its own. Loses an accessibility aid
(color-name mapping) for mobile users, so pair with an alternative (e.g. a tap-to-reveal
legend, or fold it into the fullscreen view where there's more room).

**C — Broader mobile chrome rework.** Reconsider the whole bottom-stacked-controls
pattern for narrow phones (e.g. move View/Map into a bottom sheet, collapsible drawer, or
the fullscreen-only surface) rather than patching the existing absolute-position stack
further. Highest effort, most durable.

## Verification method (reuse this — don't eyeball it)

The on-canvas labels are `<canvas>` pixels, not DOM elements, so `getBoundingClientRect()`
can't see them. Use a pixel-scan: read the canvas `ImageData`, count bright (`r,g,b>140`)
pixels per row within the expected label x-range, and take the min/max y of rows with a
meaningful bright-pixel count as the label band. Compare against DOM rects
(`.places-controls`, `.places-foot`) via Playwright. See the QA harness pattern used for
commit `e7094cd` (canvas pixel-scan + `getBoundingClientRect` diff) — regenerate a script
like it rather than trusting a screenshot alone; the collision is a few pixels wide on the
edge cases and easy to eyeball as "fine" when it isn't.

Test at minimum: 320, 360, 390, 430 CSS px widths, both themes, both Glow/Terrain basemap
modes (label positions are basemap-mode-independent, but re-verify after any change).
