# Verifying the QA visual suite when the plotly CDN is blocked

**Written:** 2026-07-25, during the QA-agent consolidation work (Phases 1 and 3).
**Why:** Phase 3 landed the environment-adaptive transport, but the container it was
built in blocks `cdn.plot.ly`, so **no check that needs a rendered Plotly chart was
exercised against a live chart**. This note says exactly what's unverified and how to
close it — either in an environment with normal network access, or offline.

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
| V1 render smoke | partially — page loads, charts don't |
| V2 overlap, V3 edge-clip, V4 width-fill, V5 contrast | **no** — need rendered charts |

V2–V5 are byte-identical to the code that shipped in both QA agents before Phase 1
(verified by diffing against `git show`), so this is a *re-verification* gap, not
new untested logic. Still worth closing before Phase 2 builds on it.

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

So Playwright can fulfil the CDN request from disk. The whole workaround is one
`page.route` call:

```python
import os, plotly
PLOTLY_JS = os.path.join(os.path.dirname(plotly.__file__), "package_data", "plotly.min.js")
page.route("**/cdn.plot.ly/**",
           lambda r: r.fulfill(path=PLOTLY_JS, content_type="application/javascript"))
```

Inserted immediately after `page = context.new_page()` in `tools/mobile_preview.py`
(before `page.goto`). Verified result in the blocked container — charts rendered and
`_fullLayout` was readable:

```json
{"plotlyVersion": "2.35.2", "visible": 1, "rendered": 1,
 "sample": {"id": "chart-cumulative",
            "xRange": ["2003-08-31", "2007-05-12"],
            "size": {"l": 62, "r": 20, "t": 20, "b": 40, "w": 215, "h": 220}}}
```

That `xRange` is exactly the dataset's extent (2003-08-31 → 2007-05-12) with no
autorange blowout — i.e. the measurement **V6** is being built to assert was
readable offline.

**Not yet wired into the CLI.** Adding an `--offline-plotly` flag to
`tools/mobile_preview.py` is the obvious next step (~6 lines, plus a `plotly_source`
field in the report so a run says which it used). It was left out because Phase 3's
scope was the transport ladder; ask for it if a CDN-blocked environment turns out to be
the normal case rather than the exception.

**Caveats.**
- Only substitutes plotly.js. The Strava **map** tab also needs `unpkg.com`
  (maplibre-gl) and would stay blank; maplibre is not vendored in any Python package
  here, so that tab needs Option A or a separately cached copy.
- Keep the local file and the pinned tag in sync. If `nerd_common/tokens.py` ever moves
  off 2.35.2 while `pyproject.toml` keeps plotly 5.24.1 (or vice versa), the offline
  substitute silently becomes a *different* build than production serves — which is a
  worse failure than a blank chart, because it looks like it worked. Re-check
  `get_plotlyjs_version()` against the tag whenever either is bumped.

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

## What to do with the result

If Options A/B show V2–V5 clean at both viewports and both themes, the Phase 1 + 3 work
is fully verified and Phase 2 can proceed on solid ground. If any check misbehaves,
fix it in `.claude/qa-visual-suite.md` — it is the single source of truth, and both QA
agents read it.

## Related

- `.claude/qa-visual-suite.md` §V0 — the transport contract, incl. the T2-degraded state
- `Project Docs/Plans/qa-agent-consolidation.md` — the plan; Phases 2 and 4 remain
- `CLAUDE.md` §Preview — the probe-first environment guidance
- `tools/mobile_preview.py` — transport T2; `--probe` reports usability
