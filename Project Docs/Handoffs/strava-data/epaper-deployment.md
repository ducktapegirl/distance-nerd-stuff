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

All four land in `running-log/` — already the GitHub Pages publish root — and all are **gitignored**
like the dashboards' HTML. They are built from data + Python by the deploy workflow, never committed.

| File | Who reads it |
|---|---|
| `epaper.html` | The panel, via SenseCraft's **Web** function. One card, exactly 800×480, no JS. |
| `feed.xml` | The panel, via SenseCraft's **RSS** function. One item per card, plain text. |
| `epaper-all.html` | You. The proof sheet — every card at real size, grouped by family. |
| `feed.json` | Escape hatch for HMI Canvas or anything else later. |

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
  This is the main event: the card of the day at exactly 800×480.
- **RSS function** → `https://ducktapegirl.github.io/distance-nerd-stuff/feed.xml`
  All 57 cards as one-line text items — useful as a second page or a fallback.

---

## Refresh: three clocks, and why they get confused

This is the part worth understanding, because a stale panel has three possible causes:

| Clock | Where | Cadence | What it controls |
|---|---|---|---|
| **Strava fetch** | `.github/workflows/strava-fetch.yml` | every 3 days (`0 6 */3 * *`) | how current the *numbers* are |
| **Site rebuild** | `.github/workflows/deploy.yml` | daily (`0 7 * * *`) + on any content push | **which card is showing** |
| **Device poll** | SenseCraft HMI settings | *unverified — see below* | when the panel picks up a change |

**The daily rebuild is not redundant.** `card_of_the_day` is evaluated at *build* time — the panel
runs no JavaScript, so `epaper.html` contains one fixed card until the site is rebuilt. Without the
daily cron the rotation would only advance when the data changed, i.e. every 3 days and not at all
on a quiet stretch. The scheduled rebuild costs nothing (it re-renders committed data, makes no
Strava API calls) and is what makes "card of the day" true.

Day-of-month stepping restarts each month, so `*/3` fires on the 1st, 4th, 7th … 31st and then again
on the 1st — a 1-day gap at some month boundaries rather than 3. Harmless, just surprising.

**The device-side interval is unverified.** `sensecraft-hmi-docs.seeed.cc` is unreachable from the
environment this was written in, and the Seeed wiki mirror documents pairing but not refresh
settings. Find it in the SenseCraft UI and **write the real number here** — without it, "the panel
is stale" is unfalsifiable.

Note also that `metrics.load()` treats **the last day with data** as "today", not the wall clock. So
"3 days since an activity" counts from the last fetch, not from now — deliberate, since a wall-clock
count would describe the cron schedule rather than the athlete.

---

## Troubleshooting

| Symptom | Look at |
|---|---|
| Panel blank or showing the setup QR | Wi-Fi dropped, or Full Flash cleared pairing. Redo steps 2–3. |
| Numbers are weeks old | Strava fetch. Check the last green run of `strava-fetch.yml` and that its secrets are still valid. |
| Same card every day | The daily rebuild. Check `deploy.yml`'s scheduled runs — GitHub disables schedules on repos with no activity for 60 days. |
| Card changed on the site but not the panel | Device poll interval, or the device is offline. |
| Text is tiny / layout is wrong | The panel is being served something other than `epaper.html` — check the Web function URL. `epaper-all.html` is the proof sheet and will look wrong on the device. |
| 404 at the Pages URL | The branch has not merged to `main`, or the Pages deploy failed. |

## Changing what shows

- **Which cards rotate:** `ROTATION` in `strava-data/feed/cards.py` — a list of card ids. Currently
  11, so the cycle is 11 days. Every other card still builds and still ships in `feed.xml` and on
  the proof sheet; promoting one is a one-line edit.
- **Where the Journey cards go:** `CORRIDORS` in `strava-data/tools/gen_journey.py`, then re-run
  that tool. Not `feed/journey.py` — that only reads the generated asset.
- **A new card:** a `@card(idea, family, recipe)` function in `cards.py` composed from
  `layouts.py`. See the panel rules in `CLAUDE.md`.
