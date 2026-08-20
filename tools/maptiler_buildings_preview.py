"""Generate a local side-by-side "3D buildings on/off" preview over Stanley Park.

Both panes run the *production* Places 3D Terrain setup -- the same custom MapTiler
terrain styles, the same terrain-rgb-v2 DEM at exaggeration 1.5, and the same
MapLibre GL JS build the hero loads from unpkg -- so this is a true before/after
rather than a prettier parallel universe. The only difference between the panes is
the fill-extrusion buildings layer on the right.

The route drawn in both panes is the real "Stanley Park Bike Cruise" (activity
18070704136), read from strava-data/data/streams/ at generate time. Its seawall loop
runs east into Coal Harbour, right where Vancouver's West End towers begin -- the
best-case shot for this feature across the whole Passport.

One-off dev tool -- not part of either dashboard's build pipeline. Output is
gitignored (tools/preview-output/); only this generator is committed, so the
baked-in MAPTILER_KEY never lands in git.

Usage:
    uv run python tools/maptiler_buildings_preview.py
    uv run python -m http.server 8766 --directory tools/preview-output
    # then open http://127.0.0.1:8766/maptiler_buildings_preview_vancouver.html
    # (must be 127.0.0.1, not localhost -- see CLAUDE.md)
    # NB: port 8765 is normally held by .claude/launch.json's "dashboards"
    # server, hence 8766 here.
"""

import csv
import json
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

# "Stanley Park Bike Cruise", 2026-04-11 -- the seawall loop. Chosen over the
# same-day run because it's the one that reaches Coal Harbour.
ACTIVITY_ID = "18070704136"
STREAM_CSV = os.path.join(_REPO_ROOT, "strava-data", "data", "streams", ACTIVITY_ID + ".csv")

# The two custom MapTiler styles 3D Terrain actually drapes onto, lifted verbatim
# from strava-data/dashboard/charts_places.py (TERRAIN_STYLE_ID / _DARK).
TERRAIN_STYLE_ID = "019fe2f9-32eb-7c1c-856d-ed5499e401cd"
TERRAIN_STYLE_ID_DARK = "019fe30f-cd64-7835-afd2-56ffea88cc0f"

# MTB amber -- the sport color this activity would get in the real hero.
ROUTE_COLOR = "#f59e0b"

# Camera: sits over Coal Harbour looking SSE. Bearing ~152 is the heading from
# this centre to the downtown tower core (~[-123.118, 49.283]), so the core lands
# dead ahead with the seawall's Coal Harbour arm in the near foreground.
#
# Zoom 15.2 is deliberate, not cosmetic. Measured against the tile API, the
# buildings tileset only ships `height`/`height_min` at z15 -- z12-13 tiles carry
# footprints with nothing but `group_id`, and z14 adds class/facade_color but
# STILL no height. Below z15 every extrusion resolves to height 0 and the layer
# is invisible. See BUILDINGS_ZOOM_NOTE below, which the page states outright.
CAMERA = {"center": [-123.1270, 49.2965], "zoom": 15.2, "pitch": 72, "bearing": 152}
BUILDINGS_MIN_ZOOM = 15

OUT_DIR = os.path.join(_HERE, "preview-output")
OUT_HTML = os.path.join(OUT_DIR, "maptiler_buildings_preview_vancouver.html")

# Same pinned MapLibre build the dashboard loads (see strava-data/dashboard/config.py).
MAPLIBRE_CDN = (
    '<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">'
    '<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>'
)


def load_route(path):
    """Read a fetch.py stream CSV -> [[lng, lat], ...], skipping gapped rows."""
    pts = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                lat, lng = float(row["lat"]), float(row["lng"])
            except (TypeError, ValueError):
                continue  # indoor/paused samples carry blank lat/lng
            pts.append([round(lng, 5), round(lat, 5)])
    return pts


# Placeholder substitution rather than str.format(): the JS below is dense with
# braces, and doubling every one of them is how subtle bugs get in. Same
# __TOKEN__ convention charts_places.py uses for its own key injection.
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>3D buildings preview - Stanley Park, Vancouver</title>
__MAPLIBRE_CDN__
<style>
  html, body { margin:0; padding:0; height:100%; background:#f4f4f2;
               font-family: system-ui, sans-serif; }
  header { display:flex; align-items:center; gap:1rem; flex-wrap:wrap;
           padding:0.5rem 1rem; background:#1c1c1c; color:#f4f4f2; font-size:0.9rem; }
  header .spacer { flex:1 1 auto; }
  header label { display:flex; align-items:center; gap:0.35rem; font-size:0.8rem; opacity:0.9; }
  header select { font:inherit; font-size:0.8rem; padding:0.15rem 0.3rem;
                  background:#2b2b2b; color:#f4f4f2; border:1px solid #444; border-radius:4px; }
  header button { font:inherit; font-size:0.8rem; padding:0.2rem 0.6rem; cursor:pointer;
                  background:#2b2b2b; color:#f4f4f2; border:1px solid #444; border-radius:4px; }
  header .stats { font-family: ui-monospace, monospace; font-size:0.72rem; opacity:0.75; }
  #panes { display:flex; width:100%; height:calc(100% - 3rem); }
  .pane { position:relative; flex:1 1 50%; height:100%; }
  .pane + .pane { border-left:2px solid #1c1c1c; }
  .pane-label { position:absolute; top:0.5rem; left:0.5rem; z-index:1;
                background:rgba(28,28,28,0.75); color:#f4f4f2;
                padding:0.25rem 0.6rem; border-radius:4px; font-size:0.8rem;
                pointer-events:none; }
  .map { width:100%; height:100%; }
</style>
</head>
<body>
<header>
  <strong>3D buildings on the Places 3D Terrain view</strong>
  <span>Stanley Park &rarr; downtown Vancouver &middot; synced camera</span>
  <span class="spacer"></span>
  <label>Buildings
    <select id="tint">
      <option value="flat">Flat tint</option>
      <option value="facade">Facade colors</option>
    </select>
  </label>
  <span id="stats" class="stats">measuring&hellip;</span>
  <label>Theme
    <select id="theme">
      <option value="light">Light</option>
      <option value="dark">Dark</option>
    </select>
  </label>
  <button id="reset">Reset camera</button>
</header>
<div id="panes">
  <div class="pane">
    <div class="pane-label">Today &mdash; 3D Terrain, no buildings</div>
    <div id="map-left" class="map"></div>
  </div>
  <div class="pane">
    <div class="pane-label">Proposed &mdash; + 3D buildings</div>
    <div id="map-right" class="map"></div>
  </div>
</div>
<script>
  var MT_KEY = "__MAPTILER_KEY__";
  var STYLE_LIGHT = "__TERRAIN_STYLE_ID__";
  var STYLE_DARK  = "__TERRAIN_STYLE_ID_DARK__";
  var CAMERA      = __CAMERA__;
  var BUILDINGS_MIN_ZOOM = __BUILDINGS_MIN_ZOOM__;
  var ROUTE       = __ROUTE__;
  var ROUTE_COLOR = "__ROUTE_COLOR__";

  var TERRAIN_SRC = "places-terrain-dem";
  var ROUTE_SRC   = "places-activity-route";
  var ROUTE_LAYER = "places-activity-route-line";
  var BLDG_SRC    = "places-buildings";
  var BLDG_LAYER  = "places-buildings-3d";

  var theme = "light";
  // Flat is the default because facade_color turns out to be sparse: a downtown
  // Vancouver probe found it on 28 of 4857 buildings (~0.6%), so "Facade colors"
  // is the flat fallback almost everywhere anyway. The live readout in the header
  // reports the real coverage for whatever is on screen.
  var tint  = "flat";

  function mtStyle(slug){ return "https://api.maptiler.com/maps/" + slug + "/style.json?key=" + MT_KEY; }
  function styleUrl(){ return mtStyle(theme === "dark" ? STYLE_DARK : STYLE_LIGHT); }

  // Flat-tint fallbacks: a warm neutral on the light relief, a cool slate on the
  // dark one -- picked to sit under the amber route rather than compete with it.
  function flatColor(){ return theme === "dark" ? "#39414f" : "#cfc7b9"; }
  function buildingColor(){
    // The specialized buildings tileset carries a per-feature facade_color; the
    // coalesce keeps unpainted features from dropping out entirely.
    if(tint === "facade") return ["coalesce", ["get", "facade_color"], flatColor()];
    return flatColor();
  }

  function makeMap(containerId){
    return new maplibregl.Map({
      container: containerId,
      style: styleUrl(),
      center: CAMERA.center, zoom: CAMERA.zoom,
      pitch: CAMERA.pitch, bearing: CAMERA.bearing,
      maxPitch: 85,            // MapLibre defaults to 60; the framing wants 68
      antialias: true,
    });
  }

  function addTerrain(map){
    if(!map.getSource(TERRAIN_SRC)){
      map.addSource(TERRAIN_SRC, {
        type: "raster-dem",
        url: "https://api.maptiler.com/tiles/terrain-rgb-v2/tiles.json?key=" + MT_KEY,
        tileSize: 512,
      });
    }
    map.setTerrain({source: TERRAIN_SRC, exaggeration: 1.5});
  }

  var ROUTE_GEOJSON = {type:"Feature", properties:{},
                       geometry:{type:"LineString", coordinates: ROUTE}};

  // A GeoJSON line added while terrain is already active gets tiled at
  // elevation 0, so it renders UNDER the terrain surface and is invisible from a
  // pitched camera -- which is what swallowed the route after a theme swap while
  // queryRenderedFeatures still happily reported it as drawn. Re-setting the data
  // once terrain is live forces a re-tile at the right elevation.
  function nudgeRoute(map){
    var src = map.getSource(ROUTE_SRC);
    if(src && map.getTerrain()) src.setData(ROUTE_GEOJSON);
  }

  // Source and layer are checked independently: a style swap can leave one
  // behind without the other, and an early return keyed on the source alone
  // would then never re-add the layer.
  function addRoute(map){
    if(!map.getSource(ROUTE_SRC)){
      map.addSource(ROUTE_SRC, {type: "geojson", data: ROUTE_GEOJSON});
    }
    if(map.getLayer(ROUTE_LAYER)) return;
    map.addLayer({
      id: ROUTE_LAYER, type: "line", source: ROUTE_SRC,
      layout: {"line-cap":"round", "line-join":"round"},
      paint: {"line-color": ROUTE_COLOR, "line-width": 4, "line-opacity": 0.95},
    });
  }

  function addBuildings(map){
    if(!map.getSource(BLDG_SRC)){
      // Raw MapLibre, not @maptiler/sdk -- the ?key= has to be appended by hand.
      map.addSource(BLDG_SRC, {
        type: "vector",
        url: "https://api.maptiler.com/tiles/buildings/tiles.json?key=" + MT_KEY,
      });
    }
    if(map.getLayer(BLDG_LAYER)) return;
    // Slip the extrusions beneath the first text layer so labels stay readable.
    var beforeId;
    var layers = map.getStyle().layers || [];
    for(var i=0; i<layers.length; i++){
      if(layers[i].type === "symbol" && layers[i].layout && layers[i].layout["text-field"]){
        beforeId = layers[i].id; break;
      }
    }
    map.addLayer({
      id: BLDG_LAYER, source: BLDG_SRC, "source-layer": "building",
      type: "fill-extrusion", minzoom: 13,
      paint: {
        "fill-extrusion-color": buildingColor(),
        // height / height_min are the SPECIALIZED buildings-tileset fields. The
        // standard planet tileset calls them render_height / render_min_height;
        // mixing the two renders nothing at all, with no error.
        "fill-extrusion-height": ["coalesce", ["get", "height"], 0],
        "fill-extrusion-base":   ["coalesce", ["get", "height_min"], 0],
        "fill-extrusion-opacity": 0.9,
      },
    }, beforeId);
  }

  // Poll-and-retry rather than gate on a 'load'/'idle' event: those events are
  // tied to the render loop, which some headless/off-screen browser contexts
  // never advance (style + tile network fetches still complete fine). Retrying
  // until the calls stop throwing works everywhere. Same approach as
  // maptiler_style_preview.py, and the same reason charts_places.py leans on
  // 'idle' + a timeout instead of 'style.load'.
  //
  // isStyleLoaded() is deliberately NOT used as the gate: under software WebGL it
  // stays false indefinitely even once the style is usable, so gating on it would
  // block forever. The budget is 100s rather than a couple of seconds because a
  // mid-session setStyle() (the theme toggle) has to refetch the whole style on a
  // starved render loop -- a 10s budget expired first and left the re-styled map
  // with no terrain, no route and no buildings at all.
  var RETRY_MS = 250, RETRY_MAX = 400;   // ~100s
  function applyOverlays(map, withBuildings, attempt){
    attempt = attempt || 0;
    try {
      addTerrain(map);
      addRoute(map);
      if(withBuildings) addBuildings(map);
    } catch (e) {
      if(attempt < RETRY_MAX){
        setTimeout(function(){ applyOverlays(map, withBuildings, attempt + 1); }, RETRY_MS);
      }
    }
  }

  var mapLeft  = makeMap("map-left");
  var mapRight = makeMap("map-right");
  var PANES = [[mapLeft, false], [mapRight, true]];
  applyOverlays(mapLeft, false);
  applyOverlays(mapRight, true);

  // Self-healing reconciler. A one-shot re-add after setStyle() is not enough:
  // for a moment after setStyle() the map still reports the OLD style, so
  // getSource()/getTerrain() answer about a style that is about to be discarded.
  // The adds then "succeed" against it, throw nothing, and get wiped when the new
  // style lands -- leaving the map bare with no error and nothing to retry on.
  // (That is exactly what silently emptied both panes on the theme toggle.)
  // Re-asserting on a cheap interval is idempotent and heals any swap, which is
  // the same reason charts_places.py re-runs applyTerrainState() on every 'idle'.
  function reconcile(){
    PANES.forEach(function(pair){
      var map = pair[0], withBuildings = pair[1];
      try {
        var freshTerrain = false;
        if(!map.getSource(TERRAIN_SRC) || !map.getTerrain()){ addTerrain(map); freshTerrain = true; }
        var freshRoute = false;
        if(!map.getLayer(ROUTE_LAYER)){ addRoute(map); freshRoute = true; }
        // Either ordering leaves the line flat-tiled, so re-tile whenever one of
        // the pair has just (re)appeared.
        if(freshTerrain || freshRoute) nudgeRoute(map);
        if(withBuildings && !map.getLayer(BLDG_LAYER)) addBuildings(map);
      } catch (e) { /* style mid-load; the next tick retries */ }
    });
  }
  setInterval(reconcile, 700);

  // Sync camera both ways, guarded against feedback loops.
  var syncing = false;
  function sync(source, target){
    source.on("move", function(){
      if(syncing) return;
      syncing = true;
      target.jumpTo({
        center: source.getCenter(), zoom: source.getZoom(),
        bearing: source.getBearing(), pitch: source.getPitch(),
      });
      syncing = false;
    });
  }
  sync(mapLeft, mapRight);
  sync(mapRight, mapLeft);

  document.getElementById("tint").addEventListener("change", function(e){
    tint = e.target.value;
    if(mapRight.getLayer(BLDG_LAYER)){
      mapRight.setPaintProperty(BLDG_LAYER, "fill-extrusion-color", buildingColor());
    }
  });

  document.getElementById("theme").addEventListener("change", function(e){
    theme = e.target.value;
    PANES.forEach(function(pair){
      var map = pair[0];
      // MapLibre's style-diff throws when a raster-dem tied to setTerrain() is
      // missing from the incoming style, so drop terrain before swapping. The
      // reconciler above puts terrain, route and buildings back once the new
      // style has actually landed -- no event to wait on, nothing to miss.
      if(map.getTerrain()) map.setTerrain(null);
      map.setStyle(styleUrl());
    });
  });

  document.getElementById("reset").addEventListener("click", function(){
    mapLeft.jumpTo({center: CAMERA.center, zoom: CAMERA.zoom,
                    pitch: CAMERA.pitch, bearing: CAMERA.bearing});
  });

  // Live readout: how many buildings are actually on screen, how many carry a
  // real height, and how many carry a facade_color -- the numbers the
  // "is this worth building?" decision turns on, kept in view rather than
  // buried in a one-off probe.
  var statsEl = document.getElementById("stats");
  function updateStats(){
    if(!mapRight.getLayer(BLDG_LAYER)){ statsEl.textContent = ""; return; }
    var z = mapRight.getZoom();
    var src = mapRight.querySourceFeatures(BLDG_SRC, {sourceLayer: "building"});
    if(!src.length){ statsEl.textContent = "z" + z.toFixed(1) + " · buildings: loading…"; return; }
    var heights = [], facades = 0;
    src.forEach(function(f){
      if(typeof f.properties.height === "number") heights.push(f.properties.height);
      if(f.properties.facade_color) facades++;
    });
    var tallest = heights.length ? Math.max.apply(null, heights) : 0;
    var txt = "z" + z.toFixed(1) + " · " + src.length + " buildings · "
      + heights.length + " with height · tallest " + Math.round(tallest)
      + " m · facade_color on " + (100 * facades / src.length).toFixed(1) + "%";
    // The whole feature hinges on this: below z15 the tiles carry no height, so
    // every extrusion collapses to 0 and the layer silently disappears.
    if(z < BUILDINGS_MIN_ZOOM) txt += "  ⚠ below z15 — no heights, extrusions flat";
    statsEl.textContent = txt;
  }
  mapRight.on("idle", updateStats);
  setInterval(updateStats, 2000);   // 'idle' is unreliable in headless contexts

  // Handy for headless verification: lets an --eval probe read whether the
  // extrusion layer actually has features rather than trusting a screenshot.
  window.__preview = {
    left: mapLeft, right: mapRight,
    buildingFeatureCount: function(){
      return mapRight.queryRenderedFeatures({layers: [BLDG_LAYER]}).length;
    },
  };
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
    if not os.path.exists(STREAM_CSV):
        sys.exit(
            "Missing stream for activity %s (%s). Run strava-data/fetch.py first."
            % (ACTIVITY_ID, STREAM_CSV)
        )

    route = load_route(STREAM_CSV)
    if len(route) < 2:
        sys.exit("Stream for activity %s has no usable GPS points." % ACTIVITY_ID)

    os.makedirs(OUT_DIR, exist_ok=True)
    html = HTML_TEMPLATE
    for token, value in [
        ("__MAPLIBRE_CDN__", MAPLIBRE_CDN),
        ("__MAPTILER_KEY__", MAPTILER_KEY),
        ("__TERRAIN_STYLE_ID__", TERRAIN_STYLE_ID),
        ("__TERRAIN_STYLE_ID_DARK__", TERRAIN_STYLE_ID_DARK),
        ("__CAMERA__", json.dumps(CAMERA)),
        ("__BUILDINGS_MIN_ZOOM__", str(BUILDINGS_MIN_ZOOM)),
        ("__ROUTE__", json.dumps(route)),
        ("__ROUTE_COLOR__", ROUTE_COLOR),
    ]:
        html = html.replace(token, value)

    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print("Route: %d GPS points from activity %s" % (len(route), ACTIVITY_ID))
    print("Wrote", OUT_HTML)
    print("Serve with: uv run python -m http.server 8766 --directory tools/preview-output")
    print("Then open: http://127.0.0.1:8766/maptiler_buildings_preview_vancouver.html")


if __name__ == "__main__":
    main()
