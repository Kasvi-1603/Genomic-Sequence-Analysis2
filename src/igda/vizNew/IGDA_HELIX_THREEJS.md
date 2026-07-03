# IGDA — Three.js DNA Helix (Option A: Bioluminescent)
**Cursor instruction file — build the animated DNA double helix for the vizNew home page.**

---

## What to build

A rotating 3D DNA double helix rendered in a `<canvas>` element using Three.js (CDN).

- Two helical strands: rose pink (`#FDA1A2`) and teal (`#1D9E75`)
- Connecting rungs between the strands (near-white, semi-transparent)
- Slow continuous auto-rotation on Y axis
- Rose point light above + teal fill below
- Background: blackcurrant (`#100D20`) matching the page
- **Full left hero panel** (responsive canvas, not a fixed 360×360 circle)
- Diagonal composition: **lower-left → upper-right**

**Implementation file:** `src/igda/vizNew/static/js/helix.js`  
Load on `home.html` only — not on other pages.

---

## CDN import (home.html only)

```html
<script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
<script src="{{ url_for('static', filename='js/helix.js') }}"></script>
```

Three.js r160 UMD build — `THREE` is a global. No import maps or ES modules on the Flask page.

---

## Canvas element (home.html hero section)

```html
<div class="home-anim-panel dna-helix-panel">
  <canvas id="dna-helix" aria-hidden="true"></canvas>
</div>
```

CSS: `static/css/dna-helix.css` — canvas fills the left panel (`position: absolute; inset: 0`).

---

## Architecture

| Piece | Location |
|--------|----------|
| Scene logic | `static/js/helix.js` |
| Layout/styles | `static/css/dna-helix.css`, `static/css/home.css` |
| Template | `templates/home.html` |

**Legacy (optional):** `frontend/` React Three Fiber bundle (`static/dna-helix/dna-helix.js`) is no longer used on the home page. Rebuild only if you switch back to R3F.

---

## Helix parameters (defaults in `helix.js`)

| Parameter | Default | Notes |
|-----------|---------|--------|
| `HELIX_RADIUS` | 0.95 | Strand distance from axis |
| `HELIX_HEIGHT` | 8.8 | Spine length (diagonal span) |
| `TURNS` | 4.2 | Full 360° coils |
| `POINTS_PER_TURN` | 24 | Curve smoothness |
| `STRAND_TUBE_RADIUS` | 0.068 | Strand thickness |
| `RUNG_TUBE_RADIUS` | 0.038 | Base-pair bar thickness |
| `SPHERE_RADIUS` | 0.11 | Node beads |
| `RUNG_EVERY` | 3 | Rungs per N points |
| `ROTATION_SPEED` | 0.004 | Radians per frame |

Composition (group transform):

- `rotation`: `[-0.22, 0.15, -0.68]` — diagonal rise lower-left → upper-right
- `position`: `[-2.4, -3.2, 0]`, `scale`: `1.35`

---

## Lighting

```
          pinkLight (#FDA1A2) — above, main key
    [camera]  →  [helix]
          tealLight (#1D9E75) — below, shadow fill
          backLight (rose, low) — separation from background
```

Ambient `#1D1842` keeps shadows readable. Intensities in `helix.js` use physically reasonable values for r160 (not the doc’s older “8 / 6” literals).

---

## Geometry

1. Parametric helix points → `CatmullRomCurve3` → `TubeGeometry` per strand  
2. `CylinderGeometry` rungs aligned with `quaternion.setFromUnitVectors`  
3. `MeshStandardMaterial` only (no `MeshBasicMaterial` on helix meshes)  
4. All helix meshes in one `Group` for rotation; lights stay on the scene

---

## How to run

```bash
python src/igda/vizNew/app.py
# http://127.0.0.1:5003
```

**DevTools checks:**

- `THREE is not defined` → CDN script missing or wrong order  
- Black canvas → camera / group position  
- WebGL unavailable → canvas stays empty (no overlay text in the hero panel)  

---

*End of helix build instructions.*
