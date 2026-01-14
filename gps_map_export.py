# gps_map_export.py
from __future__ import annotations
import json
from pathlib import Path

_HTML_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title}</title>

  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
        integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
          integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>

  <style>
    html, body, #map {{ height: 100%; margin: 0; }}
    .ctrl {{
      position: absolute; top: 10px; left: 10px; z-index: 9999;
      background: rgba(11,29,56,0.92); color: #fff;
      padding: 10px; border-radius: 10px; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      box-shadow: 0 4px 14px rgba(0,0,0,0.35); min-width: 260px;
    }}
    .ctrl label {{ display:block; font-size: 12px; opacity: 0.85; margin-top: 6px; }}
    .ctrl select, .ctrl input {{
      width: 100%; margin-top: 4px; padding: 6px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.18);
      background: rgba(255,255,255,0.06); color: #fff;
    }}
    .legend {{
      margin-top: 10px; font-size: 12px; opacity: 0.9;
    }}
    .legendbar {{
      height: 10px; border-radius: 6px; background: linear-gradient(90deg,
        #2c7bb6, #00a6ca, #00ccbc, #90eb9d, #ffff8c, #f9d057, #f29e2e, #e76818, #d7191c);
      margin-top: 6px;
    }}
    .small {{ font-size: 11px; opacity: 0.75; }}
    .popup table {{ border-collapse: collapse; font-size: 12px; }}
    .popup td {{ padding: 2px 6px; border-bottom: 1px solid rgba(0,0,0,0.08); }}
    .popup td:first-child {{ font-weight: 600; }}
  </style>
</head>
<body>
<div id="map"></div>

<div class="ctrl">
  <div style="font-weight:700;">{title}</div>
  <div class="small">Points: <span id="ptCount"></span></div>

  <label>Color by</label>
  <select id="fieldSelect"></select>

  <label>Min / Max (auto if blank)</label>
  <div style="display:flex; gap:8px;">
    <input id="minIn" placeholder="min" />
    <input id="maxIn" placeholder="max" />
  </div>

  <label>Marker size (px)</label>
  <input id="sizeIn" type="number" min="2" max="30" value="{default_size}"/>

  <div class="legend">
    <div>Legend</div>
    <div class="legendbar"></div>
    <div class="small"><span id="minLbl"></span> — <span id="maxLbl"></span></div>
  </div>
</div>

<script>
const points = {points_json};
const fields = {fields_json};

// --- Map ---
const map = L.map('map', {{ preferCanvas: true }});

// tiles (requires internet). If you want offline later, swap to local tiles.
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors'
}}).addTo(map);

// Fit bounds
const latlngs = points.map(p => [p.lat, p.lon]).filter(x => isFinite(x[0]) && isFinite(x[1]));
if (latlngs.length) {{
  map.fitBounds(latlngs, {{ padding: [30,30] }});
}} else {{
  map.setView([0,0], 2);
}}

document.getElementById("ptCount").textContent = String(points.length);

// --- Color scale (9-step) ---
function clamp01(x) {{ return Math.max(0, Math.min(1, x)); }}
function lerp(a,b,t) {{ return a + (b-a)*t; }}

// 9 anchor colors (blue->red)
const C = [
  [44,123,182],[0,166,202],[0,204,188],[144,235,157],
  [255,255,140],[249,208,87],[242,158,46],[231,104,24],[215,25,28]
];

function colorFor(t) {{
  t = clamp01(t);
  const n = C.length - 1;
  const x = t * n;
  const i = Math.floor(x);
  const f = x - i;
  const a = C[Math.max(0, Math.min(n, i))];
  const b = C[Math.max(0, Math.min(n, i+1))];
  const r = Math.round(lerp(a[0], b[0], f));
  const g = Math.round(lerp(a[1], b[1], f));
  const b2= Math.round(lerp(a[2], b[2], f));
  return `rgb(${{r}},${{g}},${{b2}})`;

}}

function toNumber(v) {{
  const x = Number(v);
  return isFinite(x) ? x : null;
}}

function autoMinMax(field) {{
  let mn = null, mx = null;
  for (const p of points) {{
    const v = toNumber(p[field]);
    if (v === null) continue;
    mn = (mn === null) ? v : Math.min(mn, v);
    mx = (mx === null) ? v : Math.max(mx, v);
  }}
  if (mn === null || mx === null) {{ mn = 0; mx = 1; }}
  if (mn === mx) {{ mx = mn + 1e-9; }}
  return [mn, mx];
}}

function popupHtml(p) {{
  let rows = "";
  for (const k of Object.keys(p)) {{
    const v = p[k];
    rows += `<tr><td>${{k}}</td><td>${{(v===null||v===undefined) ? "" : v}}</td></tr>`;
  }}
  return `<div class="popup"><table>${{rows}}</table></div>`;
}}

// --- Markers layer ---
const layer = L.layerGroup().addTo(map);

let markers = [];

function rebuild(field) {{
  // wipe
  layer.clearLayers();
  markers = [];

  const size = Math.max(2, Math.min(30, Number(document.getElementById("sizeIn").value || {default_size})));

  // min/max from inputs or auto
  let mn = toNumber(document.getElementById("minIn").value);
  let mx = toNumber(document.getElementById("maxIn").value);
  if (mn === null || mx === null) {{
    [mn, mx] = autoMinMax(field);
  }}
  document.getElementById("minLbl").textContent = mn.toFixed(3);
  document.getElementById("maxLbl").textContent = mx.toFixed(3);

  const denom = (mx - mn) || 1.0;

  for (const p of points) {{
    if (!isFinite(p.lat) || !isFinite(p.lon)) continue;

    const v = toNumber(p[field]);
    const t = (v === null) ? 0.0 : (v - mn) / denom;
    const col = colorFor(t);

    const m = L.circleMarker([p.lat, p.lon], {{
      radius: size * 0.5,
      color: col,
      fillColor: col,
      fillOpacity: 0.75,
      weight: 1
    }});
    m.bindPopup(popupHtml(p));
    m.addTo(layer);
    markers.push(m);
  }}
}}

function populateFields() {{
  const sel = document.getElementById("fieldSelect");
  sel.innerHTML = "";
  for (const f of fields) {{
    const opt = document.createElement("option");
    opt.value = f.key;
    opt.textContent = f.label;
    sel.appendChild(opt);
  }}
  sel.value = fields[0].key;
}}

populateFields();
rebuild(fields[0].key);

document.getElementById("fieldSelect").addEventListener("change", (e) => {{
  rebuild(e.target.value);
}});
document.getElementById("minIn").addEventListener("change", () => {{
  rebuild(document.getElementById("fieldSelect").value);
}});
document.getElementById("maxIn").addEventListener("change", () => {{
  rebuild(document.getElementById("fieldSelect").value);
}});
document.getElementById("sizeIn").addEventListener("change", () => {{
  rebuild(document.getElementById("fieldSelect").value);
}});
</script>
</body>
</html>
"""

def write_gps_map_html(
    out_path: Path,
    title: str,
    points: list[dict],
    fields: list[dict],
    default_size: int = 8,
) -> None:
    # points: list of dicts containing at least lat/lon plus any parameters
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    html = _HTML_TEMPLATE.format(
        title=title,
        points_json=json.dumps(points, separators=(",", ":")),
        fields_json=json.dumps(fields, separators=(",", ":")),
        default_size=int(default_size),
    )
    out_path.write_text(html, encoding="utf-8")
