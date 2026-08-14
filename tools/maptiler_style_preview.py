"""Generate a local side-by-side MapTiler 3D-terrain style comparison.

Compares MapTiler's built-in topo-v4 style against a custom style ID, both in
light mode with 3D terrain, over California. One-off dev tool -- not part of
either dashboard's build pipeline. Output is gitignored (tools/preview-output/);
only this generator is committed, so the baked-in MAPTILER_KEY never lands in git.

Usage:
    uv run python tools/maptiler_style_preview.py
    uv run python -m http.server 8766 --directory tools/preview-output
    # then open http://127.0.0.1:8766/maptiler_style_preview_ca.html
    # (must be 127.0.0.1, not localhost -- see CLAUDE.md)
    # NB: port 8765 is normally held by .claude/launch.json's "dashboards"
    # server, hence 8766 here.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_REPO_ROOT, "strava-data", ".env"))
except ImportError:
    pass

MAPTILER_KEY = os.environ.get("MAPTILER_KEY", "")

# Left pane: MapTiler's built-in general-purpose topographic style.
TOPO_STYLE_ID = "topo-v4"
# Right pane: the custom "Outdoor-NoMarkings" style -- same ID already used as
# TERRAIN_STYLE_ID (light) in strava-data/dashboard/charts_places.py.
OUTDOOR_NO_MARKINGS_STYLE_ID = "019fe2f9-32eb-7c1c-856d-ed5499e401cd"

OUT_DIR = os.path.join(_HERE, "preview-output")
OUT_HTML = os.path.join(OUT_DIR, "maptiler_style_preview_ca.html")

MAPLIBRE_CDN = (
    '<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">'
    '<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>'
)

# California bounding box: [[west, south], [east, north]].
CA_BOUNDS = [[-124.48, 32.53], [-114.13, 42.01]]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MapTiler 3D style preview - topo-v4 vs Outdoor-NoMarkings</title>
{maplibre_cdn}
<style>
  html, body {{ margin: 0; padding: 0; height: 100%; background: #f4f4f2; font-family: system-ui, sans-serif; }}
  header {{
    display: flex; align-items: center; gap: 1rem;
    padding: 0.5rem 1rem; background: #1c1c1c; color: #f4f4f2;
    font-size: 0.9rem;
  }}
  header code {{ opacity: 0.7; }}
  #panes {{ display: flex; width: 100%; height: calc(100% - 2.5rem); }}
  .pane {{ position: relative; flex: 1 1 50%; height: 100%; }}
  .pane + .pane {{ border-left: 2px solid #1c1c1c; }}
  .pane-label {{
    position: absolute; top: 0.5rem; left: 0.5rem; z-index: 1;
    background: rgba(28, 28, 28, 0.75); color: #f4f4f2;
    padding: 0.25rem 0.6rem; border-radius: 4px;
    font-size: 0.8rem; pointer-events: none;
  }}
  .map {{ width: 100%; height: 100%; }}
</style>
</head>
<body>
<header>
  <strong>MapTiler 3D terrain preview</strong>
  <span>California, light mode, synced camera</span>
</header>
<div id="panes">
  <div class="pane">
    <div class="pane-label">topo-v4</div>
    <div id="map-left" class="map"></div>
  </div>
  <div class="pane">
    <div class="pane-label">Outdoor-NoMarkings</div>
    <div id="map-right" class="map"></div>
  </div>
</div>
<script>
  var MT_KEY = "{maptiler_key}";
  var CA_BOUNDS = {ca_bounds};
  var TOPO_STYLE = "https://api.maptiler.com/maps/{topo_style_id}/style.json?key=" + MT_KEY;
  var OUTDOOR_STYLE = "https://api.maptiler.com/maps/{outdoor_style_id}/style.json?key=" + MT_KEY;
  var TERRAIN_SRC = "terrain-dem";
  var INITIAL_PITCH = 60;

  function makeMap(containerId, styleUrl) {{
    return new maplibregl.Map({{
      container: containerId,
      style: styleUrl,
      bounds: CA_BOUNDS,
      fitBoundsOptions: {{ padding: 20 }},
      pitch: INITIAL_PITCH,
      antialias: true,
    }});
  }}

  function applyTerrain(map) {{
    if (map.getSource(TERRAIN_SRC)) return;
    map.addSource(TERRAIN_SRC, {{
      type: "raster-dem",
      url: "https://api.maptiler.com/tiles/terrain-rgb-v2/tiles.json?key=" + MT_KEY,
      tileSize: 512,
    }});
    map.setTerrain({{ source: TERRAIN_SRC, exaggeration: 1.5 }});
  }}

  var mapLeft = makeMap("map-left", TOPO_STYLE);
  var mapRight = makeMap("map-right", OUTDOOR_STYLE);

  // Poll-and-retry rather than gate on a 'load'/'idle' event: those events are
  // tied to the render loop, which some headless/off-screen browser contexts
  // never advance (style + tile network fetches still complete fine). Retrying
  // addSource/setTerrain until they stop throwing works everywhere.
  function tryApplyTerrain(map, attempt) {{
    attempt = attempt || 0;
    try {{
      applyTerrain(map);
    }} catch (e) {{
      if (attempt < 50) setTimeout(function () {{ tryApplyTerrain(map, attempt + 1); }}, 200);
    }}
  }}
  tryApplyTerrain(mapLeft);
  tryApplyTerrain(mapRight);

  // Sync camera both ways, guarded against feedback loops.
  var syncing = false;
  function sync(source, target) {{
    source.on("move", function () {{
      if (syncing) return;
      syncing = true;
      target.jumpTo({{
        center: source.getCenter(),
        zoom: source.getZoom(),
        bearing: source.getBearing(),
        pitch: source.getPitch(),
      }});
      syncing = false;
    }});
  }}
  sync(mapLeft, mapRight);
  sync(mapRight, mapLeft);
</script>
</body>
</html>
"""


def main():
    if not MAPTILER_KEY:
        sys.exit(
            "MAPTILER_KEY is not set. Add it to strava-data/.env "
            "(see strava-data/.env.example) or export it before running this script."
        )

    os.makedirs(OUT_DIR, exist_ok=True)
    html = HTML_TEMPLATE.format(
        maplibre_cdn=MAPLIBRE_CDN,
        maptiler_key=MAPTILER_KEY,
        ca_bounds=CA_BOUNDS,
        topo_style_id=TOPO_STYLE_ID,
        outdoor_style_id=OUTDOOR_NO_MARKINGS_STYLE_ID,
    )
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print("Wrote", OUT_HTML)
    print("Serve with: uv run python -m http.server 8766 --directory tools/preview-output")
    print("Then open: http://127.0.0.1:8766/maptiler_style_preview_ca.html")


if __name__ == "__main__":
    main()
