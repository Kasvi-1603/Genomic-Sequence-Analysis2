"""
Prepare Figma DNA Lottie for web playback.

The SVG→Lottie exports only encode staggered pop-in (2 keyframes per node on o/s/p).
There are NO rotation keyframes in those files — continuous motion requires
re-export with the LottieFiles for Figma plugin (see docs/DNA_LOTTIE_EXPORT.md).

This script can:
  1. Snap every node to its visible helix state from frame 0 (no timed arrival)
  2. Optionally add interim per-node orbital motion (until a proper export exists)

Run: python src/igda/vizNew/scripts/patch_dna_lottie_entrance.py
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOTTIE = ROOT / "static" / "animations" / "lottie"

FLATTEN_PROPS = ("o", "s", "p")
# Do not flatten r — preserve if present; exports currently have none.


def _end_value(keyframes: list):
    return copy.deepcopy(keyframes[-1].get("s"))


def _flatten_animated(prop: dict) -> dict:
    if prop.get("a") != 1:
        return prop
    keyframes = prop.get("k")
    if not isinstance(keyframes, list) or len(keyframes) < 2:
        return prop
    return {"a": 0, "k": _end_value(keyframes)}


def _patch_transform(tr: dict, *, add_orbit: bool, layer_index: int, layer_count: int, op: int) -> bool:
    changed = False
    for name in FLATTEN_PROPS:
        if name not in tr:
            continue
        flat = _flatten_animated(tr[name])
        if flat is not tr[name]:
            tr[name] = flat
            changed = True

    if add_orbit and tr.get("p", {}).get("a") == 0:
        pos = tr["p"]["k"]
        if isinstance(pos, list) and len(pos) >= 2:
            cx, cy = float(pos[0]), float(pos[1])
            phase = (layer_index / max(layer_count - 1, 1)) * math.tau
            radius = 6.0
            frames = [0, op * 0.25, op * 0.5, op * 0.75, op]
            keyframes = []
            for t in frames:
                angle = phase + math.tau * (t / op)
                keyframes.append(
                    {
                        "t": t,
                        "s": [cx + math.cos(angle) * radius, cy + math.sin(angle) * radius],
                        "i": {"x": 0.667, "y": 1},
                        "o": {"x": 0.333, "y": 0},
                    }
                )
            tr["p"] = {"a": 1, "k": keyframes}
            changed = True

    if add_orbit:
        phase_deg = (layer_index / max(layer_count - 1, 1)) * 360
        tr["r"] = {
            "a": 1,
            "k": [
                {"t": 0, "s": [phase_deg]},
                {"t": op * 0.5, "s": [phase_deg + 180]},
                {"t": op, "s": [phase_deg + 360]},
            ],
        }
        changed = True

    return changed


def _find_tr_in_layer(layer: dict) -> dict | None:
    for shape in layer.get("shapes", []):
        if shape.get("ty") != "gr":
            continue
        for item in shape.get("it", []):
            if item.get("ty") == "tr":
                return item
    return None


def _patch_layer_ks(layer: dict) -> bool:
    ks = layer.get("ks")
    if not isinstance(ks, dict):
        return False
    changed = False
    for name in FLATTEN_PROPS:
        if name not in ks:
            continue
        flat = _flatten_animated(ks[name])
        if flat is not ks[name]:
            ks[name] = flat
            changed = True
    return changed


def _walk(obj, layer_index: int, layer_count: int, op: int, add_orbit: bool) -> int:
    count = 0
    if isinstance(obj, dict):
        if obj.get("ty") == "tr":
            if _patch_transform(obj, add_orbit=add_orbit, layer_index=layer_index, layer_count=layer_count, op=op):
                count += 1
        for value in obj.values():
            count += _walk(value, layer_index, layer_count, op, add_orbit)
    elif isinstance(obj, list):
        for item in obj:
            count += _walk(item, layer_index, layer_count, op, add_orbit)
    return count


def patch_file(src: str, dest: str, *, add_orbit: bool = False) -> None:
    data = json.loads((LOTTIE / src).read_text(encoding="utf-8"))
    layers = data.get("layers", [])
    op = int(data.get("op", 115))
    n = len(layers)

    for i, layer in enumerate(layers):
        _patch_layer_ks(layer)
        tr = _find_tr_in_layer(layer)
        if tr:
            _patch_transform(tr, add_orbit=add_orbit, layer_index=i, layer_count=n, op=op)
        _walk(layer, i, n, op, add_orbit)

    (LOTTIE / dest).write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    print(f"{src} -> {dest} (orbit={add_orbit})")


def main() -> None:
    # Visible from frame 0; interim orbital until LottieFiles export
    patch_file("simple.json", "simple-ready.json", add_orbit=True)
    patch_file("animaed.json", "animaed-ready.json", add_orbit=False)
    patch_file("signal-lines.json", "signal-ready.json", add_orbit=False)


if __name__ == "__main__":
    main()
