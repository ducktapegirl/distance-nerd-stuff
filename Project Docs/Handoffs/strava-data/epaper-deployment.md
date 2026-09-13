# Deploying the e-paper feed to the reTerminal Sticky

**Status:** runbook · **Created:** 2026-09-03 · **Owner:** unassigned

How the cards built by `strava-data/build_feed.py` get onto the panel via SenseCraft HMI. Written to
be executed in a fresh session or by hand.

---

## The device

**reTerminal Sticky** — 3.97", 800×480, 4-level grayscale ePaper, 235 PPI, capacitive touch,
ESP32-S3, magnetic mount, ~7-day standby. The whole screen is about 3.4" × 2.0", so 1 mm ≈ 9.3 px:
that density is why the cards enforce a 26 px text floor and a 3 px stroke floor.

## What gets published

All of it lands in `running-log/` — already the GitHub Pages publish root — and all of it is
**gitignored** like the dashboards' HTML. Built from data + Python by the deploy workflow, never
committed.

| File | Status | Who reads it |
|---|---|---|
| `epaper.html` | **in use** | The panel, via SenseCraft's HTML / Web widget. Every rotation card at 800×480 inside one page; a few lines of script show the card for the current hour, and the build's own pick is the no-JS fallback. |
| `epaper/<id>.html` | **in use** | The panel, if you want **one fixed card** instead of the rotation — see below. One card, no script. |
| `feed.xml` | proof of concept | SenseCraft's RSS widget. One item per card, plain text. Nothing points at it today — see "What the fallbacks would allow". |
| `feed.json` | proof of concept | SenseCraft's External Data Source widget, or anything else later. Records the build-time pick (`card_of_the_day`) and `"chosen_by": "page"`. |
| `epaper-all.html` | local only | You — the proof sheet, every card at real size, grouped by family, filterable to the rotation. `deploy.yml` builds with `--no-sheets`, so it is never published. |

63 cards build; 16 of them rotate.

**The second panel** (2.9″ four-color XIAO, 296×128) is built by the same run into the same root:

| File | Status | Who reads it |
|---|---|---|
| `epaper_xiao.html` | **in use** (HTML widget, 30-min interval) | The XIAO panel. Every rotation card at 296×128 inside one page, the hour's card chosen by the page's script, the build's pick as the no-JS fallback. |
| `epaper_xiao/<id>.html` | **in use** | Pin **one fixed card**. Same ids as the Sticky's. |
| `epaper_xiao.png`, `epaper_xiao/<id>.png` | proof of concept | An Image widget by URL, a Gallery, or any image-URL device. The build-time card as a 2-bit indexed PNG, already quantized to the four colors. |
| `feed_xiao.xml` | proof of concept | An RSS widget. Exactly one item: the build-time card as title + description, and the same PNG as an `<enclosure>`, as bare base64 (`<dns:png>`) and as a `data:` URI (`<dns:pngDataUri>`). |
| `epaper_xiao.bin`, `epaper_xiao/<id>.bin` | proof of concept | A XIAO on its **own firmware**: packed 2-bit framebuffer, 9,472 bytes, index order black / white / yellow / red. |
| `epaper_xiao-all.html` | local only | You — audit, every card at panel size, "as the panel sees it" and "shipped PNG" toggles, and the mockup pairs. Never published, like the Sticky's sheet. |

**The proof-of-concept files are built by every deploy but rotate only when the site rebuilds**
(daily, or on a data push) — they carry the build-time pick, not the hour's. They exist so that a
different transport is a URL change away, not a build away. What each would let you do that the
HTML page cannot:

| Fallback | What it enables |
|---|---|
| `feed.xml` / `feed_xiao.xml` (RSS widget) | The fact as **text in SenseCraft's own typography**, composable on a Canvas beside its other widgets — weather, a calendar, a to-do list — instead of our art filling the screen. The one source Seeed documents as re-fetched every interval. The XIAO feed also carries the card PNG as base64, so an Image widget bound to that field would get the picture through the same guaranteed path. |
| `epaper_xiao.png` (Image widget, Gallery, or an image-URL device such as a TRMNL running BYOS) | Our **exact four-color pixels as an element** on a composed canvas rather than the whole screen — a card in one corner, something else beside it. Also the format that survives a renderer with no JavaScript, and the only one the Gallery slideshow can take. |
| `epaper_xiao.bin` (own firmware) | A device that **fetches the framebuffer itself** with no cloud in the loop: sub-hour refresh, offline tolerance, battery behavior under your control. The starting point for a TRMNL-firmware port of the 2.9″ panel. |
| `feed.json` (External Data Source widget) | **The numbers without the art**: bind fields to SenseCraft text widgets and lay the card out in its Canvas Designer, or feed any other consumer. |

All 16 of the Sticky's rotation cards rotate there; verify with
`uv run python tools/epaper_check.py --panel xiao`, which also checks every shipped PNG is
296×128, 2-bit indexed on the four-color palette, and that `feed_xiao.xml` carries one item with
its base64. Design notes and the open decisions:
`Project Docs/Plans/strava-data/epaper-xiao.md`.

Base URL: `https://ducktapegirl.github.io/distance-nerd-stuff/`

---

## Step 0 — get the URL live

`deploy.yml` triggers on pushes to `main`, so **nothing exists at the Pages URL until the branch
lands**. Merge `claude/strava-rss-display-brainstorm-z26d8r` first, then confirm:

```bash
curl -sI https://ducktapegirl.github.io/distance-nerd-stuff/epaper.html | head -1   # expect 200
curl -s  https://ducktapegirl.github.io/distance-nerd-stuff/feed.xml | head -5
```

### Step 0b — previewing before you merge

SenseCraft is a cloud platform: **the device fetches the URL itself**, so a `127.0.0.1` address will
not work. The URL has to be publicly reachable. Two routes:

**A. `workflow_dispatch` from the branch.** `deploy.yml` already has the trigger, and Pages
publishes whatever ref you dispatch it from — no extra tooling. Actions → *Deploy dashboards* → Run
workflow → pick the branch. **Caveat: this replaces the live site until `main` next deploys.** Fine
for a personal site, worth knowing before you press it.

**B. A tunnel.** Isolated, but needs a tool installed:

```bash
uv run python strava-data/build_feed.py
uv run python -m http.server 8765 --directory running-log &
cloudflared tunnel --url http://127.0.0.1:8765     # or: ngrok http 8765
```

Point SenseCraft at the tunnel's public `…/epaper.html`. Kill the tunnel when done — the URL dies
with it, and the panel will show whatever it cached.

For checking the *design* rather than the device, no tunnel is needed — open
`http://127.0.0.1:8765/epaper-all.html` in a browser.

### Verify locally before merging

Before either route, run the automated pass. It is far better than squinting at the proof sheet at
the wrong scale, because it measures the two things that decide whether a card is readable on the
actual panel:

```bash
uv run python strava-data/build_feed.py
uv run python tools/epaper_check.py
```

It checks `feed.xml` (well-formed, at least 17 items, unique GUIDs, no metric units) and then every
page at exactly 800×480: nothing scrolls, one `<svg>`, no text under 26 px, no effective stroke
under 3 px, no two text boxes overlapping, nothing drawn off-panel, clean console. Exit 1 on any
failure, and a screenshot of each card under `tools/preview-output/epaper/`.

The overlap check is the one that earns its keep: the cards are hand-placed at absolute user units
with no reflow, so a longer activity name or an extra row prints one label straight through another
without changing any font size. It needs Playwright (`uv add --dev playwright && uv run playwright
install chromium`); `--probe` reports whether it can run here.

---

## Step 1 — firmware

The reTerminal E series ships with SenseCraft HMI firmware and needs nothing. Only reflash if it has
been replaced (Home Assistant, Arduino, TRMNL): SenseCraft HMI → **Tools** → pick the entry matching
this exact device and panel size → **Flash** over USB-C.

**Full Flash clears stored Wi-Fi and pairing** — use it only when you want that.

## Step 2 — Wi-Fi

Needs a **2.4 GHz** network.

1. Connect a phone or laptop to the device's temporary open access point, shown on the panel
   (`reTerminal …-xxxx`, where `xxxx` is the last four of the MAC). No password.
2. Scan the on-screen QR code, or browse to `192.168.4.1`.
3. Choose the network, enter the password, **Connect**.
4. Wait for the panel to show a **pair code**.

## Step 3 — pair it

1. Sign in to [SenseCraft HMI](https://sensecraft.seeed.cc/hmi) → **Device** → **Add Device**.
2. Enter a name and the pair code from the panel → **Create**.
3. Confirm the device appears in your Panel.

## Step 4 — point it at the feed

- **Web function** → `https://ducktapegirl.github.io/distance-nerd-stuff/epaper.html`
  This is the main event: the current card at exactly 800×480, changing hourly.
- **RSS function** → `https://ducktapegirl.github.io/distance-nerd-stuff/feed.xml`
  All 63 cards as one-line text items — useful as a second page or a fallback.
- **To pin one card instead**, point the Web function at
  `…/epaper/<id>.html` (e.g. `…/epaper/haiku.html`) rather than `…/epaper.html`.

---

## Refresh: three clocks, and which one moves the card

A stale panel has three possible causes, and since 2026-09-13 the card rotation belongs to the
last of them:

| Clock | Where | Cadence | What it controls |
|---|---|---|---|
| **Strava fetch** | `.github/workflows/strava-fetch.yml` | every 3 days (`0 6 */3 * *`) | how current the *numbers* are |
| **Site rebuild** | `.github/workflows/deploy.yml` | daily (`0 7 * * *`) + on any content push | the **date-keyed** cards (`anniversary`, route of the day, this week) and the proof-of-concept files |
| **Device poll** | SenseCraft device card → Refresh Interval | **30 min** on the XIAO (verified 2026-09-13); Sticky not yet written down | **which card is showing** |

**The device page chooses the card.** `epaper.html` and `epaper_xiao.html` carry every rotation
card as an inert `<template>`, and a few lines of script swap in the one for the current hour —
keyed on hours since the epoch in UTC, modulo the rotation, exactly the formula
`cards.card_of_the_day` uses. SenseCraft's HTML widget renders the page in a cloud headless browser
(its documented example is windy.com, which is blank without JavaScript), so the script runs and
each poll gets the hour's card. **The device poll is therefore the rotation's clock**: at 30
minutes a card lands at most 30 minutes into its hour; a shorter interval tightens that, with the
panel's ~25 s refresh flash as the practical floor.

**The build still bakes its own pick into the page** as the visible card before the script runs.
That is the no-JS fallback: if a renderer ever stops running the script, the panel shows the
build-time card — the behavior this repo had until 2026-09-13 — and never a blank screen. The
signature of that state is a panel that stays on `feed.json`'s `card_of_the_day` /
`xiao.card_of_the_hour` for hours; the remedy is `cron: "0 * * * *"` in `deploy.yml`, the one-line
revert to an hourly rebuild.

**Why the rebuild is daily and not never.** `anniversary` is keyed to the build date by design ("1
day ago" must not say so for three days), and the route-of-the-day / this-week cards move by day.
One run a day keeps them honest between the every-three-days data pushes, at a runner minute.
`concurrency: {group: pages, cancel-in-progress: true}` means an overlapping run cancels the older
one rather than racing it. Two things to know about scheduled workflows: GitHub may delay them
under load, and it disables them entirely after 60 days with no repo activity — the date-keyed
cards would then freeze; the rotation would not.

Day-of-month stepping restarts each month, so `*/3` fires on the 1st, 4th, 7th … 31st and then again
on the 1st — a 1-day gap at some month boundaries rather than 3. Harmless, just surprising.

**The device-side interval lives on the device card in SenseCraft (Refresh Interval).** Verified on
the XIAO 2.9″ on 2026-09-13: set to **30 minutes**, pointed at `epaper_xiao.html` through the HTML
widget, and the cloud re-renders the page on every interval without another Apply. The Sticky's
setting has not been written down; add it here when it is.

Note also that `metrics.load()` treats **the last day with data** as "today", not the wall clock. So
"3 days since an activity" counts from the last fetch, not from now — deliberate, since a wall-clock
count would describe the cron schedule rather than the athlete.

---

## Troubleshooting

| Symptom | Look at |
|---|---|
| Panel blank or showing the setup QR | Wi-Fi dropped, or Full Flash cleared pairing. Redo steps 2–3. |
| Numbers are weeks old | Strava fetch. Check the last green run of `strava-fetch.yml` and that its secrets are still valid. |
| Card has not changed for many hours | The device poll (Refresh Interval on the device card), or the device is offline. If it is polling and still stuck on the card `feed.json` names as the build-time pick, the renderer is not running the page's script — revert `deploy.yml` to an hourly cron. |
| "1 day ago" has said so for days / the route of the day never changes | The daily `deploy.yml` schedule. Check Actions: scheduled workflows are delayed under load and are auto-disabled after 60 days of repo inactivity. |
| Text is tiny / layout is wrong | The panel is being served something other than `epaper.html` — check the widget URL. `epaper-all.html` is the proof sheet and will look wrong on the device. |
| 404 at the Pages URL | The branch has not merged to `main`, or the Pages deploy failed. |

### The XIAO panel

SenseCraft (Seeedash) is a **cloud-render, push** model: you compose a canvas of widgets, click
Apply, and the cloud pushes a bitmap to the device on the schedule set by the device card's
**Refresh Interval**. The device fetches nothing itself. So "the panel points at a URL" really
means "a widget on the canvas has a URL the cloud resolves when it renders". Three widgets can
carry the card, and the docs only document the refresh behavior of one of them:

| Widget | Point it at | Refreshes every interval? |
|---|---|---|
| **HTML** | `…/epaper_xiao.html` | **Yes — verified 2026-09-13, and what is in use.** The cloud re-renders the page every Refresh Interval (30 min); the card changes without another Apply. |
| **RSS** | `…/feed_xiao.xml` | Documented to refresh. Bind `title` / `description` to text; `dns:png` / `dns:pngDataUri` / `enclosure.url` carry the PNG for an Image widget if its tree allows the binding. Untested — kept as the fallback. |
| **Image** | `…/epaper_xiao.png` | Undocumented, untested. |

The HTML widget is the live path, so the page is what matters: the cards are pure black / white /
red / yellow, which is why the cloud's quantizer has nothing to decide. The PNG, framebuffer and
one-item feed still ship with every rebuild as the proof-of-concept fallbacks they were built to be
(see "What the fallbacks would allow" above).

If neither image path refreshes, the fallback is the XIAO's **own firmware**: an ESP32-S3 sketch
that wakes hourly, fetches `epaper_xiao.bin` and writes it to the panel. The framebuffer's index
order (black 0, white 1, yellow 2, red 3) follows the GDEY029F51 convention — verify against the
driver before trusting it on glass.

A full refresh on this panel takes ~25 s and flashes, so a Refresh Interval much under 15 minutes
buys nothing but flicker. Pairing is the same as the Sticky's; the SenseCraft firmware is per
panel, so pick the 2.9″ four-color entry under Tools.

## Changing what shows

- **Which cards rotate:** `ROTATION` in `strava-data/feed/cards.py` — a list of card ids. Currently
  16, one per hour, so the cycle is 16 hours. Every other card still builds and still ships in
  `feed.xml`, on the proof sheet, and at its own `epaper/<id>.html`; promoting one is a one-line
  edit, and the device page picks it up on the next rebuild.
- **Pinning one card instead of the rotation:** point the widget at `…/epaper/<id>.html` — e.g.
  `…/epaper/journey-run.html` — instead of `…/epaper.html`. One card, no script, same 800×480, and
  it never changes. Card ids are the `id` field in `feed.json` and the filenames in
  `running-log/epaper/`.
- **Where the Journey cards go:** `CORRIDORS` in `strava-data/tools/gen_journey.py`, then re-run
  that tool. Not `feed/journey.py` — that only reads the generated asset.
- **A new card:** a `@card(idea, family, recipe)` function in `cards.py` composed from
  `layouts.py`. See the panel rules in `CLAUDE.md`.
