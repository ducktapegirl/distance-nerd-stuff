# distance-nerd-stuff

*seriously, who cares?*

I do, apparently. This is a little personal corner of the internet for poking
at my own endurance sports data: a **Strava dashboard** for activities pulling using the Strava API
activities (2024+), and a **Running Log**: my college running log that predated Strava entirely (2003-2007).

**Live:**
- 🏠 Start here — https://ducktapegirl.github.io/distance-nerd-stuff/
- 🏃 Running Log — https://ducktapegirl.github.io/distance-nerd-stuff/college.html
- 🚴 Strava dashboard — https://ducktapegirl.github.io/distance-nerd-stuff/strava.html

## What's actually here

- **Strava dashboard** — charts and stats built from my Strava activity
  history: pace trends, segment performance, mountain bike speed, that kind
  of thing. Refreshed automatically a few times a week.
- **Running Log** — my running history going back well before Strava
  existed, parsed out of old hand-kept HTML logs into one browsable,
  searchable page.
- **An e-paper feed** — the same data cut into 63 single-fact "cards" for a
  little 800×480 gray-scale panel stuck to the fridge. Sixteen of them
  rotate, one an hour. No color, no JavaScript, nothing smaller than 26 px,
  because at 235 PPI the whole screen is about the size of a credit card.

All of it is static pages, rebuilt from data + a few Python scripts, and
published with GitHub Pages.

## Built by a team of robots (sort of)

The Strava dashboard isn't hand-coded — it's built and maintained by a
small crew of Claude agents, each with one job: one decides what's
interesting in the data, one designs how a new chart should look, one writes
the actual code, one checks the result before it ships. I (a human) approve
each stage along the way. It's equal parts "I wanted these specific charts"
and "I wanted to see how far an agentic build pipeline could go." Curious
how it works under the hood? See [`strava-data/AGENTS.md`](strava-data/AGENTS.md).

## Filing an issue

Want something fixed or added? [Open an issue](https://github.com/ducktapegirl/distance-nerd-stuff/issues/new/choose) — there are three forms, and each needs the right tag:

- **Bug report** — something's broken, wrong, or looks off. This form auto-tags itself **`bug`**.
- **New view / chart idea** — propose a question you want a dashboard to answer. This form
  auto-tags itself **`enhancement`**.
- **General enhancement** — anything else you'd like improved that isn't a new chart or view
  (navigation, layout, exports, workflow, etc.). This form auto-tags itself **`enhancement`**.

Filing an issue with the `bug` or `enhancement` tag doesn't trigger anything by itself — only I
can apply the `agent:ready` label, and nothing happens until I do. Once it's applied, the issue
may get picked up and routed automatically: `bug` reports go straight to a fix, and `enhancement`
requests go through the full design pipeline if rough or get built more directly if specific
(based on your own "how formed is this idea?" answer on the form). You'll see progress as label changes
(`agent:in-progress` → `agent:done`) and eventually a pull request that closes the issue.

## Can I use this?

Not as-is. The data here is mine — the Strava dashboard is built from CSVs
pulled through my personal Strava API credentials, so you can't just clone
this and get a working dashboard with your own data. But the build scripts
themselves are plain Python and free to read or borrow from. How it's all
built and run lives in [`CLAUDE.md`](CLAUDE.md).

## What's next

A handful of ideas are written up but not built yet — a real heat-stress
index for the heat-vs-pace charts, clickable links out to Strava, records
that update themselves when a bigger hike comes along, and an orphaned
summer-2003 log the parser has never read. They're collected in
[`Project Docs/Plans/README.md`](Project%20Docs/Plans/README.md).

