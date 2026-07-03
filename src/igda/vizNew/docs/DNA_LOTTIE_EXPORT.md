# DNA Lottie export (Figma → web)

## Why the current SVG export looks wrong

`Simple.json` and `Animaed.json` were exported with **SVG to Lottie v1.0.0**. That exporter only captured:

- Staggered **pop-in** (opacity 0→100, scale 0→100, position snap)
- **No** `r` (rotation) keyframes
- **No** continuous orbital motion after nodes appear

`signal lines.json` was exported with **LottieFiles Figma v112** and does contain real timeline animation.

The homepage cannot render rotation that is not present in the JSON. Patching only removes the arrival wave; it cannot invent Figma Smart Animate data.

## Correct export (recommended)

1. Open [Smooth Animated DNA](https://www.figma.com/design/NtrCAIRFAc4ztbgXygiCMq/) in Figma.
2. Select the **Animaed** frame (the full prototype, not a flattened group).
3. Use the **LottieFiles** plugin for Figma (same workflow as `signal lines`).
4. Export with **prototype / Smart Animate** enabled.
5. Save as `src/igda/vizNew/static/animations/lottie/animaed-lottiefiles.json`.
6. Update `home.html` `data-lottie-animaed` to that file and remove interim `simple-ready.json` if the new file is self-contained.

## Interim files (until re-export)

`python src/igda/vizNew/scripts/patch_dna_lottie_entrance.py` generates:

| File | Purpose |
|------|---------|
| `simple-ready.json` | All nodes visible at frame 0 + interim per-node orbit |
| `animaed-ready.json` | Visible overlay (masks/effects), no arrival |
| `signal-ready.json` | Signal line timing preserved |

These are a **placeholder** until a LottieFiles export of the helix exists.
