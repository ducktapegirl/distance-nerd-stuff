# Verifying the QA visual suite when the plotly CDN is blocked

**Written:** 2026-07-25, during the QA-agent consolidation work (Phases 1 and 3).
**Why:** Phase 3 landed the environment-adaptive transport, but the container it was
built in blocks `cdn.plot.ly`, so no check that needs a rendered Plotly chart could be
exercised against a live chart.

> **Update, same day — the gap was closed offline.** `--offline-plotly` is now wired
> into `tools/mobile_preview.py` (Option B below), and V2–V5 were run against real
> rendered charts in the blocked container: all clean on running-log's *performance*
> tab and Strava's *exploratory* tab at 375px. **This note is no longer a blocker.**
> It stays as the reference for verifying in an environment with normal network access
> (Option A), which is still worth doing — see "What's still worth checking elsewhere".

## The gap, precisely

Both dashboards load plotly.js from a single pinned CDN tag
(`nerd_common/tokens.py:35` → `https://cdn.plot.ly/plotly-2.35.2.min.js`). Where that
host is unreachable, the browser still loads the page and the DOM is complete, but
`window.Plotly` never appears and **no chart renders**. The suite calls this state
**T2-degraded** (`.claude/qa-visual-suite.md` §V0).

| Suite check | Verified in the build container? |
|---|---|
| V0 transport probe (all failure paths) | **yes** — each forced deliberately |
| `--desktop` / `--theme` / `--eval @file` / Chromium fallback | **yes** |
| V1 render smoke | **yes**, via `--offline-plotly` |
| V2 overlap, V3 edge-clip, V4 width-fill, V5 contrast | **yes**, via `--offline-plotly` |

V2–V5 are byte-identical to the code that shipped in both QA agents before Phase 1
(verified by diffing against `git show`), so this was a *re-verification* gap rather
than new untested logic — now closed offline.

Two other hosts are blocked in the same environment and are worth knowing about:
`unpkg.com` (maplibre-gl → the Strava **map** tab only) and `gc.zgo.at`
(goatcounter analytics → irrelevant to QA).

---

## Option A — verify in an environment with CDN access (preferred)

Nothing to install or change. From the repo root:

```bash
# 1. Is this transport usable here? exit 0 = yes, 2 = no (JSON says why).
uv run python tools/mobile_preview.py --probe --page /index.html

# 2. Build both dashboards.
uv run python strava-data/build_dashboard.py
uv run python "running-log/visualize_log.py"

# 3. Confirm charts actually render (this is the bit that was impossible).
uv run python tools/mobile_preview.py --page /index.html \
  --eval '() => { const v=[...document.querySelectorAll(".js-plotly-plot")].filter(e=>e.offsetParent!==null); return JSON.stringify({plotly: !!window.Plotly, visible: v.length, rendered: v.filter(e=>!!e._fullLayout).length}); }'
```

Expect `plotly: true`, `visible > 0`, and `rendered === visible`. **Check `visible > 0`
explicitly** — the `.js-plotly-plot` class is applied by Plotly itself, so in a blocked
environment the selector matches nothing and `rendered === visible` passes vacuously as
`0 === 0`. In the blocked container this command returns
`{"plotly":false,"visible":0,"rendered":0}`; that is the signature of the problem, not a
pass. Then run the suite's checks at both viewports and both themes — the V0 invocation
reference lists the flags.

**Run un-sandboxed.** Charts need real egress to `cdn.plot.ly`.

> Charts on non-active tabs render lazily on tab activation, so `visible` counts only
> the current tab's charts. Pass `--click '.tab[data-view="<name>"]'` to reach the rest.

## Option B — serve plotly.js offline (works with no network at all)

**This was tested in the blocked container and it works.** The `plotly` Python package
already vendors the exact build the pages pin — confirmed, not assumed:

```bash
uv run python -c "from plotly.offline import get_plotlyjs_version; print(get_plotlyjs_version())"
# -> 2.35.2, which is exactly what nerd_common/tokens.py pins
```

So Playwright can fulfil the CDN request from disk. **This is wired into the CLI** as
`--offline-plotly`:

```bash
# The transport reports usable even with the CDN blocked:
uv run python tools/mobile_preview.py --probe --offline-plotly --page /index.html
# -> {"ok": true, "plotly": true, "plotly_local_version": "2.35.2", ...}, exit 0

# Run any suite check against real rendered charts, no network needed:
uv run python tools/mobile_preview.py --page /index.html --offline-plotly \
  --click '.tab[data-view="performance"]' --eval @tools/qa-checks/width-fill.js
```

It reports `plotly_source` and `plotly_local_version` so a run always says which
bundle it used.

**The version-drift trap is guarded, not just documented.** The intercepted URL carries
the version the page pins, so the handler compares it against the installed package and
records a loud `plotly_version_mismatch` + `warning` when they differ. Verified by
pointing a copy of the page at `plotly-2.99.9.min.js`:

```json
{"plotly_version_mismatch": {"requested": "2.99.9", "served": "2.35.2"},
 "warning": "VERSION DRIFT: the page pins plotly 2.99.9 but the installed package
             vendors 2.35.2. Charts rendered against a DIFFERENT build than
             production serves - treat these measurements as unreliable ..."}
```

If you ever see that warning, the measurements from that run are not trustworthy —
re-sync `nerd_common/tokens.py`'s pin with `pyproject.toml`'s plotly version.

**Caveat — what `--offline-plotly` does NOT cover.** Only plotly.js is substituted. The
Strava **map** tab also needs `unpkg.com` (maplibre-gl), which is not vendored in any
Python package here, so that tab stays blank offline and needs Option A or C.

## Option C — allow the host in the environment's network policy

Claude Code web/remote environments have a configurable network policy. If
`cdn.plot.ly` (and `unpkg.com`, for the map tab) can be allowlisted for this repo's
environment, T2 works normally with no code change and no version-drift risk. See
https://code.claude.com/docs/en/claude-code-on-the-web. Diagnose with:

```bash
curl -sS "$HTTPS_PROXY/__agentproxy/status"   # recentRelayFailures names blocked hosts
```

A 403 on CONNECT is a policy denial, not a misconfiguration — don't try to route around
it.

---

## What's still worth checking elsewhere

Offline verification closed the blocking gap, but three things are only observable in an
environment with real network access — none blocks Phase 2:

1. **The Strava map tab** (`unpkg.com`/maplibre-gl) — never renders offline, so its
   charts and any map-specific layout issue are unverified.
2. **Real CDN delivery** — offline serves the bundle instantly from disk, so it can't
   surface a slow-CDN race where a chart is measured before it finishes laying out. If
   checks are ever flaky in normal use but clean offline, suspect settle timing and
   raise `--settle`.
3. **Transport T1 (Preview MCP)** — not provisioned in the build container, so the
   T1 branch of V0 and the `preview_snapshot` a11y path are untested end to end.

If any check misbehaves, fix it in `.claude/qa-visual-suite.md` — it is the single
source of truth, and both QA agents read it.

## Related

- `.claude/qa-visual-suite.md` §V0 — the transport contract, incl. the T2-degraded state
- `Project Docs/Plans/qa-agent-consolidation.md` — the plan; Phases 2 and 4 remain
- `CLAUDE.md` §Preview — the probe-first environment guidance
- `tools/mobile_preview.py` — transport T2; `--probe` reports usability
