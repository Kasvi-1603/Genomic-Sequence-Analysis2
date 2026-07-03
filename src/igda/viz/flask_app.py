"""Flask visualization app wired to igda benchmark backend."""

from __future__ import annotations

from dataclasses import asdict
from statistics import mean
from typing import Any

from flask import Flask, redirect, render_template, request, url_for

import igda


def _parse_patterns(raw: str) -> list[str]:
    return igda.normalize_patterns([p.strip() for p in raw.split(",")], dedupe=True)


def _parse_manual_strings(raw: str) -> list[str]:
    rows = [line.strip() for line in raw.splitlines() if line.strip()]
    return rows


def _build_segments(text: str, prefix_chars: int, segment_length: int, segment_count: int) -> list[str]:
    prefix = text[:prefix_chars]
    if segment_count <= 1:
        return [prefix]
    out: list[str] = []
    start = 0
    for _ in range(segment_count):
        end = min(start + segment_length, len(prefix))
        if end <= start:
            break
        out.append(prefix[start:end])
        start = end
    return out if out else [prefix]


def _best_row(rows: list[dict[str, Any]], *, kind: str) -> dict[str, Any] | None:
    subset = [r for r in rows if r.get("match_kind") == kind]
    if not subset:
        return None
    return min(subset, key=lambda r: r["time_ms_median"])


def _group_best_algorithms(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Average median time per algorithm across all cases."""
    bucket: dict[str, list[float]] = {}
    for row in rows:
        bucket.setdefault(row["algorithm_id"], []).append(float(row["time_ms_median"]))
    return {algo: mean(vals) for algo, vals in bucket.items()}


def _default_form(algo_ids: list[str], comp_ids: list[str]) -> dict[str, Any]:
    return {
        "input_mode": "fasta_only",
        "fasta_path": "data/raw/sequence.fasta",
        "manual_strings": "ATGCGTATGCGT\nGCGCGTTAACGT\nATTAACCGGTTA",
        "patterns": "ATG,TAA,GCG",
        "selected_algorithms": list(algo_ids),
        "selected_compressions": list(comp_ids),
        "warmup": 1,
        "trials": 3,
        "max_edits": 1,
        "prefix_chars": 50000,
        "run_mode": "single",
        "segment_count": 3,
        "segment_length": 16000,
    }


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates")

    @app.route("/", methods=["GET", "POST"])
    def home():
        selected_mode = request.args.get("input_mode", "fasta_only")
        if request.method == "POST":
            selected_mode = request.form.get("input_mode", "fasta_only")
            return redirect(url_for("analytics", input_mode=selected_mode))
        return render_template("home.html", selected_mode=selected_mode)

    @app.route("/analytics", methods=["GET", "POST"])
    def analytics():
        algo_ids = igda.list_algorithm_ids()
        comp_ids = igda.list_compression_ids()

        form = _default_form(algo_ids, comp_ids)
        form["input_mode"] = request.args.get("input_mode", form["input_mode"])

        case_summary: list[dict[str, Any]] = []
        matcher_rows: list[dict[str, Any]] = []
        compression_rows: list[dict[str, Any]] = []
        notes: list[str] = []
        best_exact_overall = None
        best_approx_overall = None
        best_compression = None
        error = None

        if request.method == "POST":
            try:
                form["fasta_path"] = request.form.get("fasta_path", form["fasta_path"])
                form["input_mode"] = request.form.get("input_mode", form["input_mode"])
                form["manual_strings"] = request.form.get("manual_strings", form["manual_strings"])
                form["patterns"] = request.form.get("patterns", form["patterns"])
                form["selected_algorithms"] = request.form.getlist("selected_algorithms") or []
                form["selected_compressions"] = request.form.getlist("selected_compressions") or []
                form["warmup"] = int(request.form.get("warmup", form["warmup"]))
                form["trials"] = int(request.form.get("trials", form["trials"]))
                form["max_edits"] = int(request.form.get("max_edits", form["max_edits"]))
                form["prefix_chars"] = int(request.form.get("prefix_chars", form["prefix_chars"]))
                form["run_mode"] = request.form.get("run_mode", form["run_mode"])
                form["segment_count"] = int(request.form.get("segment_count", form["segment_count"]))
                form["segment_length"] = int(request.form.get("segment_length", form["segment_length"]))

                patterns = _parse_patterns(str(form["patterns"]))
                if not patterns:
                    raise ValueError("Please provide at least one valid pattern.")

                segments: list[str] = []
                segment_labels: list[str] = []
                mode = str(form["input_mode"])

                if mode in ("fasta_only", "mixed"):
                    text = igda.load_fasta_sequence(str(form["fasta_path"]))
                    segment_count = 1 if form["run_mode"] == "single" else int(form["segment_count"])
                    fasta_segments = _build_segments(
                        text=text,
                        prefix_chars=int(form["prefix_chars"]),
                        segment_length=int(form["segment_length"]),
                        segment_count=segment_count,
                    )
                    segments.extend(fasta_segments)
                    segment_labels.extend([f"fasta_{i+1}" for i in range(len(fasta_segments))])

                if mode in ("manual_only", "mixed"):
                    manual_segments = _parse_manual_strings(str(form["manual_strings"]))
                    if mode == "manual_only" and not manual_segments:
                        raise ValueError("Manual mode selected, but no strings were provided.")
                    if mode == "mixed" and not manual_segments:
                        raise ValueError("Mixed mode selected. Please provide at least one manual string.")
                    segments.extend(manual_segments)
                    segment_labels.extend([f"manual_{i+1}" for i in range(len(manual_segments))])

                if not segments:
                    raise ValueError("No input strings were prepared. Check selected mode and fields.")

                cfg = igda.RunConfig(
                    warmup=int(form["warmup"]),
                    trials=int(form["trials"]),
                    selected_algorithm_ids=list(form["selected_algorithms"]),
                    selected_compression_ids=list(form["selected_compressions"]),
                    max_edits=int(form["max_edits"]),
                )

                for i, seg in enumerate(segments, start=1):
                    summary = igda.run_benchmark(seg, patterns, cfg)
                    case = segment_labels[i - 1] if i - 1 < len(segment_labels) else f"case_{i}"

                    case_matchers = [asdict(row) | {"case": case, "text_length": len(seg)} for row in summary.matcher_rows]
                    case_compressions = [
                        asdict(row) | {"case": case, "text_length": len(seg)} for row in summary.compression_rows
                    ]
                    matcher_rows.extend(case_matchers)
                    compression_rows.extend(case_compressions)
                    notes.extend([f"{case}: {n}" for n in summary.notes])

                    exact_best = _best_row(case_matchers, kind="exact")
                    approx_best = _best_row(case_matchers, kind="approximate")
                    case_summary.append(
                        {
                            "case": case,
                            "text_length": len(seg),
                            "best_exact": (
                                f"{exact_best['algorithm_id']} ({exact_best['time_ms_median']:.3f} ms)"
                                if exact_best
                                else "N/A"
                            ),
                            "best_approx": (
                                f"{approx_best['algorithm_id']} ({approx_best['time_ms_median']:.3f} ms)"
                                if approx_best
                                else "N/A"
                            ),
                        }
                    )

                # Overall "best for this specific run"
                exact_overall = _group_best_algorithms([r for r in matcher_rows if r["match_kind"] == "exact"])
                approx_overall = _group_best_algorithms([r for r in matcher_rows if r["match_kind"] == "approximate"])
                if exact_overall:
                    best_exact_overall = min(exact_overall.items(), key=lambda x: x[1])
                if approx_overall:
                    best_approx_overall = min(approx_overall.items(), key=lambda x: x[1])
                if compression_rows:
                    best_compression = max(compression_rows, key=lambda r: r["percent_saved"])

            except Exception as exc:  # pragma: no cover - runtime path
                error = str(exc)

        return render_template(
            "index.html",
            algo_ids=algo_ids,
            comp_ids=comp_ids,
            form=form,
            case_summary=case_summary,
            matcher_rows=matcher_rows,
            compression_rows=compression_rows,
            notes=notes,
            best_exact_overall=best_exact_overall,
            best_approx_overall=best_approx_overall,
            best_compression=best_compression,
            error=error,
        )

    return app


if __name__ == "__main__":
    create_app().run(debug=True)

