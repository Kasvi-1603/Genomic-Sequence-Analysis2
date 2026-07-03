"""Build composite DNA Lottie (single timeline, correct layer stack). Run from project root."""

from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOTTIE_DIR = ROOT / "static" / "animations" / "lottie"
OUT = LOTTIE_DIR / "dna-composite.json"

ARTBOARD_W = 1920
ARTBOARD_H = 1080
FR = 60
OP = 115


def _load(name: str) -> dict:
    return json.loads((LOTTIE_DIR / name).read_text(encoding="utf-8"))


def _renumber_layers(layers: list, start_ind: int) -> int:
    """Reassign ind and remap parent references."""
    mapping: dict[int, int] = {}
    for i, layer in enumerate(layers):
        old_ind = layer.get("ind")
        new_ind = start_ind + i
        layer["ind"] = new_ind
        if old_ind is not None:
            mapping[old_ind] = new_ind
    for layer in layers:
        parent = layer.get("parent")
        if parent is not None:
            layer["parent"] = mapping.get(parent, parent)
    return start_ind + len(layers)


def _offset_position(layer: dict, dx: float, dy: float) -> None:
    ks = layer.get("ks") or {}
    p = ks.get("p") or {}
    if p.get("a") != 0:
        return
    k = p.get("k")
    if isinstance(k, list) and len(k) >= 2:
        p["k"] = [k[0] + dx, k[1] + dy] + k[2:]


def _make_precomp_asset(asset_id: str, source: dict) -> dict:
    return {
        "id": asset_id,
        "nm": source.get("nm", asset_id),
        "fr": source.get("fr", FR),
        "layers": copy.deepcopy(source["layers"]),
        "w": source["w"],
        "h": source["h"],
    }


def _make_precomp_layer(
    asset_id: str,
    ind: int,
    name: str,
    comp_w: int,
    comp_h: int,
    pos: list[float],
    scale_pct: float,
) -> dict:
    return {
        "ty": 0,
        "nm": name,
        "ind": ind,
        "sr": 1,
        "st": 0,
        "op": OP,
        "ip": 0,
        "hd": False,
        "ddd": 0,
        "bm": 0,
        "hasMask": False,
        "ao": 0,
        "w": comp_w,
        "h": comp_h,
        "refId": asset_id,
        "ks": {
            "a": {"a": 0, "k": [comp_w / 2, comp_h / 2]},
            "p": {"a": 0, "k": pos},
            "s": {"a": 0, "k": [scale_pct, scale_pct, 100]},
            "r": {"a": 0, "k": 0},
            "o": {"a": 0, "k": 100},
            "sk": {"a": 0, "k": 0},
            "sa": {"a": 0, "k": 0},
        },
    }


def build() -> dict:
    simple = _load("simple.json")
    animaed = _load("animaed.json")
    signal = _load("signal-lines.json")

    assets: list[dict] = []
    next_ind = 1

    # Lottie: layers[0] = top (foreground). Stack back → front.

    # --- Back: Simple helix (precomp, centered & scaled to artboard) ---
    simple_id = "simple_helix"
    assets.append(_make_precomp_asset(simple_id, simple))
    scale = min(ARTBOARD_W / simple["w"], ARTBOARD_H / simple["h"])
    pos = [ARTBOARD_W / 2, ARTBOARD_H / 2, 0]
    simple_layer = _make_precomp_layer(
        simple_id, next_ind, "Simple helix", simple["w"], simple["h"], pos, scale * 100
    )
    next_ind += 1

    # --- Middle: Animaed frame layers (export order preserved) ---
    animaed_layers = copy.deepcopy(animaed["layers"])
    _renumber_layers(animaed_layers, next_ind)
    next_ind += len(animaed_layers)

    # --- Front: Signal lines (offset to lower band of artboard) ---
    signal_layers = copy.deepcopy(signal["layers"])
    _renumber_layers(signal_layers, next_ind)
    sx = ARTBOARD_W * 0.12
    sy = ARTBOARD_H * 0.82
    for layer in signal_layers:
        if layer.get("parent") is None:
            _offset_position(layer, sx, sy)

    layers = signal_layers + animaed_layers + [simple_layer]

    return {
        "v": animaed.get("v", "5.7.0"),
        "fr": FR,
        "ip": 0,
        "op": OP,
        "w": ARTBOARD_W,
        "h": ARTBOARD_H,
        "nm": "DNA composite",
        "ddd": 0,
        "meta": {"g": "vizNew composite — Simple + Animaed + signal-lines"},
        "assets": assets,
        "layers": layers,
    }


def main() -> None:
    composite = build()
    OUT.write_text(json.dumps(composite, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes, {len(composite['layers'])} layers)")


if __name__ == "__main__":
    main()
