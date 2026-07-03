"""Second-generation Flask UI with wizard screens and benchmark visuals."""

from __future__ import annotations

import json
from math import ceil
from statistics import median
from time import perf_counter
from typing import Any
from uuid import uuid4

from flask import Flask, redirect, render_template, request, session, url_for

import igda

_STATE_STORE: dict[str, dict[str, Any]] = {}


def _p95(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    ordered = sorted(values)
    idx = ceil(0.95 * len(ordered)) - 1
    idx = max(0, min(idx, len(ordered) - 1))
    return ordered[idx]


def _stats(times_ms: list[float]) -> tuple[float, float, float, float | None]:
    return median(times_ms), min(times_ms), max(times_ms), _p95(times_ms)


def _parse_patterns(raw: str) -> list[str]:
    merged = raw.replace("\n", ",")
    tokens = [x.strip() for x in merged.split(",")]
    return igda.normalize_patterns(tokens, dedupe=True)


def _normalize_input(mode: str, raw: str) -> str:
    if mode == "fasta":
        lines = [line.strip() for line in raw.splitlines() if line.strip() and not line.startswith(">")]
        return "".join(lines)
    return raw.strip()


def _session_state() -> dict[str, Any]:
    sid = session.get("viz2_sid")
    if not sid:
        sid = uuid4().hex
        session["viz2_sid"] = sid
    if sid not in _STATE_STORE:
        _STATE_STORE[sid] = {
            "items": [],
            "pattern": {},
            "compression": {},
            "pattern_runs": {},
            "compression_runs": {},
        }
    state = _STATE_STORE[sid]
    state.setdefault("pattern_runs", {})
    state.setdefault("compression_runs", {})
    return state


def _benchmark_matchers(
    text: str,
    patterns: list[str],
    algorithm_ids: list[str],
    warmup: int,
    trials: int,
    max_edits: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for algorithm_id in algorithm_ids:
        info = igda.get_matcher(algorithm_id).info
        for _ in range(max(0, warmup)):
            igda.run_match(algorithm_id, text, patterns, max_edits=max_edits)

        times_ms: list[float] = []
        last_result = None
        for _ in range(max(1, trials)):
            t0 = perf_counter()
            out = igda.run_match(algorithm_id, text, patterns, max_edits=max_edits)
            times_ms.append((perf_counter() - t0) * 1000.0)
            last_result = out

        med, mn, mx, p95 = _stats(times_ms)
        sample_positions: list[int] = []
        if last_result is not None:
            for m in last_result.matches[:5]:
                start = m.get("start")
                if isinstance(start, int):
                    sample_positions.append(start)

        rows.append(
            {
                "algorithm_id": info.id,
                "algorithm_name": info.name,
                "match_kind": info.match_kind.value,
                "time_ms_median": med,
                "time_ms_min": mn,
                "time_ms_max": mx,
                "time_ms_p95": p95,
                "match_count": (last_result.match_count if last_result is not None else 0),
                "sample_positions": sample_positions,
                "notes": info.notes,
            }
        )
    return sorted(rows, key=lambda row: row["time_ms_median"])


def _benchmark_compressions(
    text: str,
    compression_ids: list[str],
    warmup: int,
    trials: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    infos = {c.id: c for c in igda.list_compressions()}
    for compression_id in compression_ids:
        for _ in range(max(0, warmup)):
            igda.run_compression(compression_id, text)

        times_ms: list[float] = []
        last_result = None
        for _ in range(max(1, trials)):
            t0 = perf_counter()
            out = igda.run_compression(compression_id, text)
            times_ms.append((perf_counter() - t0) * 1000.0)
            last_result = out

        med, mn, mx, p95 = _stats(times_ms)
        info = infos[compression_id]
        rows.append(
            {
                "compression_id": info.id,
                "compression_name": info.name,
                "time_ms_median": med,
                "time_ms_min": mn,
                "time_ms_max": mx,
                "time_ms_p95": p95,
                "original_bytes": (last_result.original_bytes if last_result is not None else 0),
                "compressed_bytes": (last_result.compressed_bytes if last_result is not None else 0),
                "ratio": (last_result.ratio if last_result is not None else 1.0),
                "percent_saved": (last_result.percent_saved if last_result is not None else 0.0),
                "notes": info.notes,
            }
        )
    return sorted(rows, key=lambda row: row["time_ms_median"])


def _step_status(state: dict[str, Any]) -> dict[str, bool]:
    pattern_runs = state.get("pattern_runs", {})
    compression_runs = state.get("compression_runs", {})
    shared_ids = set(pattern_runs.keys()) & set(compression_runs.keys())
    return {
        "home": True,
        "pattern": bool(state.get("items")),
        "compression": bool(pattern_runs),
        "analysis": bool(shared_ids),
    }


def create_app_viz2() -> Flask:
    app = Flask(__name__, template_folder="templates")
    app.secret_key = "viz2-dev-key"

    @app.route("/", methods=["GET", "POST"])
    def home():
        state = _session_state()
        error = None
        if request.method == "POST":
            action = request.form.get("action", "add_item")
            if action == "add_item":
                mode = request.form.get("mode", "text")
                label = request.form.get("label", "").strip()
                pasted = request.form.get("pasted_input", "")
                upload = request.files.get("input_file")
                file_text = ""
                filename = ""
                if upload and upload.filename:
                    filename = upload.filename
                    file_text = upload.read().decode("utf-8", errors="ignore")

                raw = file_text if file_text.strip() else pasted
                normalized = _normalize_input(mode, raw)
                if not normalized:
                    error = "Provide file input or paste text before adding."
                else:
                    state["items"].append(
                        {
                            "id": uuid4().hex[:8],
                            "label": label or f"Sample {len(state['items']) + 1}",
                            "mode": mode,
                            "filename": filename,
                            "chars": len(normalized),
                            "lines": len(normalized.splitlines()) or 1,
                            "preview": normalized[:140],
                            "text": normalized,
                        }
                    )
            elif action == "remove_item":
                remove_id = request.form.get("remove_id", "")
                state["items"] = [item for item in state["items"] if item["id"] != remove_id]
                state.get("pattern_runs", {}).pop(remove_id, None)
                state.get("compression_runs", {}).pop(remove_id, None)
            elif action == "clear_items":
                state["items"] = []
                state["pattern"] = {}
                state["compression"] = {}
                state["pattern_runs"] = {}
                state["compression_runs"] = {}
            elif action == "continue":
                if state["items"]:
                    return redirect(url_for("pattern"))
                error = "Add at least one dataset item first."

        return render_template("viz2_home.html", items=state["items"], step_status=_step_status(state), error=error)

    @app.route("/pattern", methods=["GET", "POST"])
    def pattern():
        state = _session_state()
        if not state["items"]:
            return redirect(url_for("home"))

        algo_infos = igda.list_algorithms()
        algo_ids = [info.id for info in algo_infos]
        saved = state.get("pattern", {})
        form = {
            "item_id": saved.get("item_id", state["items"][0]["id"]),
            "patterns_raw": saved.get("patterns_raw", "ATG,TAA,GCG"),
            "primary_matcher": saved.get("primary_matcher", algo_ids[0] if algo_ids else ""),
            "warmup": saved.get("warmup", 0),
            "trials": saved.get("trials", 1),
            "max_edits": saved.get("max_edits", 1),
            "sample_chars": saved.get("sample_chars", 20000),
            "include_approximate": saved.get("include_approximate", False),
        }
        rows = saved.get("rows", [])
        error = None

        if request.method == "POST":
            form["item_id"] = request.form.get("item_id", form["item_id"])
            form["patterns_raw"] = request.form.get("patterns_raw", form["patterns_raw"])
            form["primary_matcher"] = request.form.get("primary_matcher", form["primary_matcher"])
            form["warmup"] = int(request.form.get("warmup", form["warmup"]))
            form["trials"] = int(request.form.get("trials", form["trials"]))
            form["max_edits"] = int(request.form.get("max_edits", form["max_edits"]))
            form["sample_chars"] = int(request.form.get("sample_chars", form["sample_chars"]))
            form["include_approximate"] = request.form.get("include_approximate") == "on"
            action = request.form.get("action", "run")

            try:
                patterns = _parse_patterns(str(form["patterns_raw"]))
                if not patterns:
                    raise ValueError("Enter at least one valid pattern.")
                selected_item = next((item for item in state["items"] if item["id"] == form["item_id"]), None)
                if selected_item is None:
                    raise ValueError("Choose a valid dataset item.")

                run_algo_ids = list(algo_ids)
                if not form["include_approximate"]:
                    run_algo_ids = [
                        info.id for info in algo_infos if info.match_kind.value == "exact"
                    ]
                    if form["primary_matcher"] not in run_algo_ids and run_algo_ids:
                        form["primary_matcher"] = run_algo_ids[0]

                target_items = state["items"] if action == "run_all" else [selected_item]
                for item in target_items:
                    benchmark_text = item["text"]
                    if int(form["sample_chars"]) > 0:
                        benchmark_text = benchmark_text[: int(form["sample_chars"])]
                    rows = _benchmark_matchers(
                        text=benchmark_text,
                        patterns=patterns,
                        algorithm_ids=run_algo_ids,
                        warmup=int(form["warmup"]),
                        trials=int(form["trials"]),
                        max_edits=int(form["max_edits"]),
                    )
                    primary = next((row for row in rows if row["algorithm_id"] == form["primary_matcher"]), None)
                    run_record = {
                        **form,
                        "patterns": patterns,
                        "item_label": item["label"],
                        "input_chars_used": len(benchmark_text),
                        "original_chars": len(item["text"]),
                        "rows": rows,
                        "winner": (rows[0]["algorithm_id"] if rows else None),
                        "primary": primary,
                    }
                    state["pattern_runs"][item["id"]] = run_record
                    if item["id"] == form["item_id"]:
                        state["pattern"] = dict(run_record)
                if action == "continue":
                    return redirect(url_for("compression"))
            except Exception as exc:  # pragma: no cover
                error = str(exc)

        primary = state.get("pattern", {}).get("primary")
        return render_template(
            "viz2_pattern.html",
            items=state["items"],
            algo_infos=algo_infos,
            form=form,
            rows=rows,
            primary=primary,
            step_status=_step_status(state),
            bar_data=json.dumps(rows),
            error=error,
        )

    @app.route("/compression", methods=["GET", "POST"])
    def compression():
        state = _session_state()
        if not state["items"]:
            return redirect(url_for("home"))

        comp_infos = igda.list_compressions()
        comp_ids = [info.id for info in comp_infos]
        saved = state.get("compression", {})
        form = {
            "item_id": saved.get("item_id", state["items"][0]["id"]),
            "primary_compression": saved.get("primary_compression", comp_ids[0] if comp_ids else ""),
            "warmup": saved.get("warmup", 0),
            "trials": saved.get("trials", 1),
            "sample_chars": saved.get("sample_chars", 50000),
        }
        rows = saved.get("rows", [])
        error = None

        if request.method == "POST":
            form["item_id"] = request.form.get("item_id", form["item_id"])
            form["primary_compression"] = request.form.get("primary_compression", form["primary_compression"])
            form["warmup"] = int(request.form.get("warmup", form["warmup"]))
            form["trials"] = int(request.form.get("trials", form["trials"]))
            form["sample_chars"] = int(request.form.get("sample_chars", form["sample_chars"]))
            action = request.form.get("action", "run")

            try:
                selected_item = next((item for item in state["items"] if item["id"] == form["item_id"]), None)
                if selected_item is None:
                    raise ValueError("Choose a valid dataset item.")
                target_items = state["items"] if action == "run_all" else [selected_item]
                for item in target_items:
                    benchmark_text = item["text"]
                    if int(form["sample_chars"]) > 0:
                        benchmark_text = benchmark_text[: int(form["sample_chars"])]
                    rows = _benchmark_compressions(
                        text=benchmark_text,
                        compression_ids=comp_ids,
                        warmup=int(form["warmup"]),
                        trials=int(form["trials"]),
                    )
                    primary = next((row for row in rows if row["compression_id"] == form["primary_compression"]), None)
                    run_record = {
                        **form,
                        "item_label": item["label"],
                        "input_chars_used": len(benchmark_text),
                        "original_chars": len(item["text"]),
                        "rows": rows,
                        "winner": (rows[0]["compression_id"] if rows else None),
                        "primary": primary,
                    }
                    state["compression_runs"][item["id"]] = run_record
                    if item["id"] == form["item_id"]:
                        state["compression"] = dict(run_record)
                if action == "continue":
                    return redirect(url_for("analysis"))
            except Exception as exc:  # pragma: no cover
                error = str(exc)

        primary = state.get("compression", {}).get("primary")
        return render_template(
            "viz2_compression.html",
            items=state["items"],
            comp_infos=comp_infos,
            form=form,
            rows=rows,
            primary=primary,
            step_status=_step_status(state),
            bar_data=json.dumps(rows),
            error=error,
        )

    @app.route("/analysis")
    def analysis():
        state = _session_state()
        pattern_state = state.get("pattern", {})
        compression_state = state.get("compression", {})
        pattern_rows = pattern_state.get("rows", [])
        compression_rows = compression_state.get("rows", [])
        pattern_primary = pattern_state.get("primary")
        compression_primary = compression_state.get("primary")
        tree_payload = {
            "pattern": [
                {"name": row["algorithm_id"], "value": round(1000.0 / max(row["time_ms_median"], 0.001), 2)}
                for row in pattern_rows
            ],
            "compression": [
                {"name": row["compression_id"], "value": round(row["percent_saved"], 2)}
                for row in compression_rows
            ],
        }
        pattern_runs = state.get("pattern_runs", {})
        compression_runs = state.get("compression_runs", {})
        per_item_analysis: list[dict[str, Any]] = []
        missing_pattern: list[str] = []
        missing_compression: list[str] = []
        for item in state.get("items", []):
            item_id = item["id"]
            p_run = pattern_runs.get(item_id)
            c_run = compression_runs.get(item_id)
            if not p_run:
                missing_pattern.append(item["label"])
            if not c_run:
                missing_compression.append(item["label"])
            if not p_run or not c_run:
                continue
            p_rows = p_run.get("rows", [])
            c_rows = c_run.get("rows", [])
            if not p_rows or not c_rows:
                continue
            per_item_analysis.append(
                {
                    "item_label": item["label"],
                    "item_mode": item["mode"],
                    "chars": item["chars"],
                    "pattern_primary": p_run.get("primary"),
                    "pattern_fastest": p_rows[0],
                    "compression_primary": c_run.get("primary"),
                    "compression_fastest": c_rows[0],
                    "compression_best_saved": max(c_rows, key=lambda row: row["percent_saved"]),
                    "pattern_rows": p_rows,
                    "compression_rows": c_rows,
                }
            )
        return render_template(
            "viz2_analysis.html",
            step_status=_step_status(state),
            pattern_rows=pattern_rows,
            compression_rows=compression_rows,
            pattern_primary=pattern_primary,
            compression_primary=compression_primary,
            pattern_winner=(pattern_rows[0] if pattern_rows else None),
            compression_winner=(compression_rows[0] if compression_rows else None),
            compression_best_saved=(max(compression_rows, key=lambda row: row["percent_saved"]) if compression_rows else None),
            tree_data=json.dumps(tree_payload),
            per_item_analysis=per_item_analysis,
            missing_pattern=missing_pattern,
            missing_compression=missing_compression,
            algo_infos=igda.list_algorithms(),
            comp_infos=igda.list_compressions(),
        )

    return app

