"""Flask wizard UI for IGDA benchmarks (vizNew)."""

from __future__ import annotations

import json
import os
import tempfile
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import uuid4

from datetime import datetime, timedelta, timezone

from flask import Flask, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename

import igda
from igda.vizNew import session_workspace as bench_ws
from igda import RunConfig
from igda.compression.huffman import _build_tree
from igda.compression.rle import _encode_runs

_VIZNEW_ROOT = Path(__file__).resolve().parent
_UPLOAD_ROOT = Path(tempfile.gettempdir()) / "igda_viznew_uploads"
_SESSION_TEXT_DIR = Path(tempfile.gettempdir()) / "igda_viznew_session_text"
_SESSION_REPORT_DIR = Path(tempfile.gettempdir()) / "igda_viznew_session_reports"
# Render's free tier runs on a heavily shared/throttled CPU — cap the workload
# there so a single request doesn't run past gunicorn's worker timeout.
_LITE_MODE = bool(os.environ.get("RENDER") or os.environ.get("IGDA_LITE_MODE"))
_TRIALS = 1 if _LITE_MODE else 3
_MULTI_N_TRIALS = 1 if _LITE_MODE else 2
# Keep web benchmarks responsive on large FASTA files
_MAX_SEQUENCE_LEN = 12_000 if _LITE_MODE else 50_000
_MULTI_N_SIZES = (1_000, 4_000, 8_000) if _LITE_MODE else (2_000, 10_000, 25_000)
_MATCHERS_SCALING = ["naive", "kmp", "horspool", "ahocorasick"]
_EXACT_MATCHER_IDS = ("naive", "kmp", "horspool", "ahocorasick")
_TEXT_PREVIEW_LEN = 100_000
MIN_PATTERN_LEN_FOR_MUTATION = 6
MUTATION_PROXIMITY = 2
MUTATION_SITE_CAP = 200
HEATMAP_MAX_BINS = 48
HEATMAP_MIN_BINS = 12


def _summary_public(summary) -> dict[str, Any]:
    """Serialise BenchmarkSummary (rows use slots, not __dict__)."""
    return {
        "config": asdict(summary.config),
        "matcher_rows": [asdict(row) for row in summary.matcher_rows],
        "compression_rows": [asdict(row) for row in summary.compression_rows],
        "notes": list(summary.notes),
    }


def _parse_patterns(raw: str) -> list[str]:
    merged = raw.replace("\n", ",")
    tokens = [p.strip() for p in merged.split(",")]
    return igda.normalize_patterns(tokens, dedupe=True)


def _read_fasta_capped(path: Path, max_len: int) -> str:
    """Stream FASTA lines without loading unbounded sequence into memory."""
    chunks: list[str] = []
    total = 0
    with path.open(encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            s = line.strip()
            if not s or s.startswith(">"):
                continue
            if total >= max_len:
                break
            take = s[: max_len - total]
            chunks.append(take)
            total += len(take)
    return "".join(chunks)


def _load_uploaded_text(upload, *, max_len: int = _MAX_SEQUENCE_LEN) -> tuple[str, str]:
    """Read an uploaded file into sequence/text; returns (text, filename)."""
    filename = secure_filename(upload.filename or "upload.txt")
    suffix = Path(filename).suffix.lower()
    dest = _UPLOAD_ROOT / f"{uuid4().hex}_{filename}"
    _UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    upload.save(dest)
    try:
        if suffix in {".fa", ".fasta", ".fna", ".faa", ".ffn", ".frn"}:
            return _read_fasta_capped(dest, max_len), filename
        if suffix in {".txt", ".seq", ""}:
            raw = dest.read_text(encoding="utf-8", errors="ignore")
            if raw.lstrip().startswith(">"):
                return _read_fasta_capped(dest, max_len), filename
            return raw[:max_len], filename
        return dest.read_text(encoding="utf-8", errors="ignore")[:max_len], filename
    finally:
        try:
            dest.unlink(missing_ok=True)
        except OSError:
            pass


def _apply_length_limit(text: str, prefix_raw: str) -> tuple[str, str | None]:
    """Cap sequence length for interactive benchmarks."""
    if prefix_raw.isdigit():
        n = int(prefix_raw)
        if n > 0:
            return text[:n], None
    if len(text) > _MAX_SEQUENCE_LEN:
        return (
            text[:_MAX_SEQUENCE_LEN],
            f"Sequence truncated to first {_MAX_SEQUENCE_LEN:,} characters for faster benchmarks.",
        )
    return text, None


def _save_session_text(text: str) -> str:
    """Persist sequence on disk — cookie sessions cannot hold large FASTA strings."""
    _SESSION_TEXT_DIR.mkdir(parents=True, exist_ok=True)
    path = _SESSION_TEXT_DIR / f"{uuid4().hex}.txt"
    path.write_text(text[:_TEXT_PREVIEW_LEN], encoding="utf-8")
    return str(path)


def _load_session_text(path_str: str | None) -> str:
    if not path_str:
        return ""
    path = Path(path_str)
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="ignore")
    return ""


def _clear_session_text(path_str: str | None) -> None:
    if not path_str:
        return
    try:
        Path(path_str).unlink(missing_ok=True)
    except OSError:
        pass


def _session_sequence_text() -> str:
    """Load benchmark sequence from workspace (falls back to legacy paths)."""
    text = bench_ws.load_session_text()
    if text:
        return text
    text = _load_session_text(session.get("text_path"))
    if text:
        return text
    legacy = session.get("text_preview")
    return legacy if isinstance(legacy, str) else ""


def _has_benchmark() -> bool:
    if bench_ws.load_benchmark():
        return True
    return bool(session.get("benchmark"))


def _get_benchmark() -> dict[str, Any] | None:
    data = bench_ws.load_benchmark()
    if data:
        return data
    legacy = session.get("benchmark")
    if isinstance(legacy, dict):
        bench_ws.save_benchmark(legacy)
        return legacy
    return None


def _get_multi_n() -> list[dict[str, Any]]:
    data = bench_ws.load_multi_n()
    if data:
        return data
    legacy = session.get("multi_n")
    if isinstance(legacy, list) and legacy:
        bench_ws.save_multi_n(legacy)
        return legacy
    return []


def _get_mutation_report() -> dict[str, Any] | None:
    report = bench_ws.load_mutation_report()
    if report:
        return report
    return _load_mutation_report(session.get("mutation_report_path"))


def _upload_form_defaults() -> dict[str, Any]:
    cfg = bench_ws.load_upload_config()
    if cfg:
        return cfg
    return {
        "input_mode": "fasta",
        "patterns": "ATG,TATAAA,GCATCG,AATAAA",
        "max_edits": 1,
        "prefix_chars": "50000",
        "manual_text": "",
        "uploaded_files": [],
    }


def _save_mutation_report(report: dict[str, Any]) -> str:
    _SESSION_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = _SESSION_REPORT_DIR / f"{uuid4().hex}.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return str(path)


def _load_mutation_report(path_str: str | None) -> dict[str, Any] | None:
    if not path_str:
        return None
    path = Path(path_str)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _clear_mutation_report(path_str: str | None) -> None:
    if not path_str:
        return
    try:
        Path(path_str).unlink(missing_ok=True)
    except OSError:
        pass


def _exact_total_from_benchmark(benchmark_data: dict[str, Any]) -> int:
    return sum(
        int(row.get("match_count", 0))
        for row in benchmark_data.get("matcher_rows", [])
        if row.get("match_kind") == "exact"
    )


def _kmp_hits(text: str, patterns: list[str]) -> list[tuple[int, str]]:
    """KMP matches as (start, pattern) pairs."""
    hits: list[tuple[int, str]] = []
    result = igda.run_match("kmp", text, patterns)
    for m in result.matches:
        start = m.get("start")
        pat = m.get("pattern", "")
        if isinstance(start, int) and isinstance(pat, str) and pat:
            hits.append((start, pat))
    return hits


def _exact_positions_kmp(text: str, patterns: list[str]) -> set[int]:
    """Single KMP pass — sufficient for exact-position proximity checks."""
    return {pos for pos, _ in _kmp_hits(text, patterns)}


def _heatmap_bin_count(length: int) -> int:
    if length <= 0:
        return 1
    target = max(HEATMAP_MIN_BINS, length // 2000)
    return min(HEATMAP_MAX_BINS, target)


def _build_motif_heatmap(
    exact_hits: list[tuple[int, str]],
    mutation_hits: list[tuple[int, str]],
    exact_patterns: list[str],
    mutation_patterns: list[str],
    length: int,
) -> dict[str, Any]:
    """Pattern × genomic-bin density matrices for exact vs mutation-only hits."""
    num_bins = _heatmap_bin_count(length)
    bin_width = max(1, (length + num_bins - 1) // num_bins)
    bin_labels: list[str] = []
    for i in range(num_bins):
        start = i * bin_width
        bin_labels.append(f"{start:,}")

    def _layer(patterns: list[str], hits: list[tuple[int, str]]) -> dict[str, Any]:
        counts = {p: [0] * num_bins for p in patterns}
        max_val = 0
        for pos, pat in hits:
            row = counts.get(pat)
            if row is None:
                continue
            b = min(pos // bin_width, num_bins - 1)
            row[b] += 1
            if row[b] > max_val:
                max_val = row[b]
        return {"patterns": patterns, "counts": counts, "max": max_val}

    return {
        "num_bins": num_bins,
        "bin_width": bin_width,
        "sequence_length": length,
        "bin_labels": bin_labels,
        "exact": _layer(exact_patterns, exact_hits),
        "mutation": _layer(mutation_patterns, mutation_hits),
    }


def _huffman_tree_dict(text: str) -> dict[str, Any] | None:
    root = _build_tree(text)
    if root is None:
        return None

    def node_dict(node) -> dict[str, Any]:
        if node.ch is not None:
            return {"name": node.ch, "char": node.ch, "freq": node.freq}
        children: list[dict[str, Any]] = []
        if node.left is not None:
            children.append(node_dict(node.left))
        if node.right is not None:
            children.append(node_dict(node.right))
        return {"name": str(node.freq), "freq": node.freq, "children": children}

    return node_dict(root)


def _match_positions(text: str, patterns: list[str]) -> dict[str, list[int]]:
    if not text or not patterns or len(text) > 30_000:
        return {}
    result = igda.run_match("kmp", text, patterns)
    out: dict[str, list[int]] = {p: [] for p in patterns}
    for m in result.matches:
        pat = m.get("pattern")
        start = m.get("start")
        if isinstance(pat, str) and isinstance(start, int):
            out.setdefault(pat, []).append(start)
    for pat in out:
        out[pat] = sorted(set(out[pat]))
    return out


def _enrich_benchmark(public: dict[str, Any], text: str, patterns: list[str]) -> dict[str, Any]:
    """Adapt harness output to template-friendly field names."""
    matcher_rows = list(public.get("matcher_rows", []))
    compression_rows = list(public.get("compression_rows", []))

    exact = [r for r in matcher_rows if r.get("match_kind") == "exact"]
    approx = [r for r in matcher_rows if r.get("match_kind") == "approximate"]
    best_exact = min(exact, key=lambda r: r["time_ms_median"], default=None)
    best_approx = min(approx, key=lambda r: r["time_ms_median"], default=None)

    enriched_matchers: list[dict[str, Any]] = []
    for row in matcher_rows:
        algo_id = row.get("algorithm_id", "")
        enriched_matchers.append(
            {
                **row,
                "algorithm": algo_id,
                "is_best_exact": bool(best_exact and algo_id == best_exact.get("algorithm_id")),
                "is_best_approx": bool(best_approx and algo_id == best_approx.get("algorithm_id")),
            }
        )

    best_compression = max(compression_rows, key=lambda r: r.get("percent_saved", 0), default=None)
    huffman_codes: dict[str, str] = {}
    huffman_freq: dict[str, int] = {}
    tree_data: dict[str, Any] | None = None
    rle_run_summary: dict[str, int] = {}

    if text:
        huff_out = igda.run_compression("huffman", text)
        payload = huff_out.payload if isinstance(huff_out.payload, dict) else {}
        huffman_codes = dict(payload.get("codes", {}))
        huffman_freq = dict(Counter(text))
        tree_data = _huffman_tree_dict(text)
        runs = _encode_runs(text)
        rle_run_summary = dict(Counter(sym for sym, _ in runs))

    enriched_compression: list[dict[str, Any]] = []
    for row in compression_rows:
        cid = row.get("compression_id", "")
        item: dict[str, Any] = {
            **row,
            "algorithm": cid,
            "is_best": bool(best_compression and cid == best_compression.get("compression_id")),
        }
        if cid == "huffman":
            item["codebook"] = huffman_codes
            item["frequencies"] = huffman_freq
            item["tree_data"] = tree_data
        if cid == "rle":
            item["run_summary"] = rle_run_summary
        enriched_compression.append(item)

    def matcher_summary(row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return None
        return {
            "algorithm": row.get("algorithm_id"),
            "algorithm_name": row.get("algorithm_name"),
            "time_ms_median": row.get("time_ms_median"),
            "match_count": row.get("match_count"),
        }

    return {
        **public,
        "matcher_rows": enriched_matchers,
        "compression_rows": enriched_compression,
        "best_exact_matcher": matcher_summary(best_exact),
        "best_approx_matcher": matcher_summary(best_approx),
        "best_compression": (
            {
                "algorithm": best_compression.get("compression_id"),
                "compression_name": best_compression.get("compression_name"),
                "percent_saved": best_compression.get("percent_saved"),
                "time_ms_median": best_compression.get("time_ms_median"),
            }
            if best_compression
            else None
        ),
        "match_positions": _match_positions(text, patterns),
    }


def _multi_n_benchmark(text: str, patterns: list[str], max_edits: int) -> list[dict[str, Any]]:
    """Lightweight scaling series for the analysis chart (matchers only)."""
    sizes = sorted({n for n in _MULTI_N_SIZES if 0 < n <= len(text)})
    if not sizes and len(text) > 0:
        sizes = [len(text)]
    multi_n: list[dict[str, Any]] = []
    for n in sizes:
        algo_ids = list(_MATCHERS_SCALING)
        if n <= 8_000:
            algo_ids.append("edit_distance")
        cfg = RunConfig(
            warmup=0,
            trials=_MULTI_N_TRIALS,
            selected_algorithm_ids=algo_ids,
            selected_compression_ids=[],
            max_edits=max_edits,
        )
        summary = igda.run_benchmark(text[:n], patterns, cfg)
        public = _summary_public(summary)
        matcher_rows = [
            {**row, "algorithm": row.get("algorithm_id")}
            for row in public.get("matcher_rows", [])
        ]
        multi_n.append({"n": n, "results": {"matcher_rows": matcher_rows}})
    return multi_n


def compute_mutation_report(
    benchmark_data: dict[str, Any],
    text: str,
    patterns: list[str],
    max_edits: int,
) -> dict[str, Any] | None:
    """
    Robust mutation detection:
    - Only patterns >= 6 bases (short k-mers produce noise with edit distance)
    - Mutation site = EditDistance hit with no exact match within ±2 positions
    - Display capped at 200 sites; dist >= 1 only (excludes exact windows)
    """
    if max_edits < 1:
        return None

    cfg_max = benchmark_data.get("config", {}).get("max_edits", max_edits)
    all_patterns = list(patterns or [])
    skipped_short = [p for p in all_patterns if len(p) < MIN_PATTERN_LEN_FOR_MUTATION]
    qualifying_patterns = [p for p in all_patterns if len(p) >= MIN_PATTERN_LEN_FOR_MUTATION]

    empty_report: dict[str, Any] = {
        "total": 0,
        "snp_count": 0,
        "del_count": 0,
        "exact_total": 0,
        "sites": [],
        "pattern_counts": {},
        "max_edits": cfg_max,
        "skipped_short_patterns": skipped_short,
        "no_qualifying_patterns": not qualifying_patterns,
        "qualifying_patterns": qualifying_patterns,
    }

    if not text:
        return None

    seq_len = len(text)
    kmp_hits = _kmp_hits(text, all_patterns)

    if not qualifying_patterns:
        empty_report["heatmap"] = _build_motif_heatmap(
            kmp_hits,
            [],
            all_patterns,
            [],
            seq_len,
        )
        return empty_report

    exact_positions = {pos for pos, _ in kmp_hits}
    exact_total = _exact_total_from_benchmark(benchmark_data)

    edit_hits: list[dict[str, Any]] = []
    edit_result = igda.run_match(
        "edit_distance", text, qualifying_patterns, max_edits=max_edits
    )
    for m in edit_result.matches:
        start = m.get("start")
        pat = str(m.get("pattern", ""))
        dist = m.get("edit_distance", 1)
        if not isinstance(start, int):
            continue
        dist = int(dist) if not isinstance(dist, int) else dist
        if dist < 1:
            continue
        if len(pat) < MIN_PATTERN_LEN_FOR_MUTATION:
            continue
        edit_hits.append({"pos": start, "dist": dist, "pattern": pat})

    mutation_sites: list[dict[str, Any]] = []
    for hit in edit_hits:
        pos = hit["pos"]
        nearby_exact = any(
            abs(pos - ep) <= MUTATION_PROXIMITY for ep in exact_positions
        )
        if nearby_exact:
            continue

        pat_len = len(hit["pattern"])
        win_start = max(0, pos - 2)
        win_end = min(len(text), pos + pat_len + 2)
        mutation_sites.append(
            {
                "pos": pos,
                "pattern": hit["pattern"],
                "edit_dist": hit["dist"],
                "seq_window": text[win_start:win_end],
                "window_start": win_start,
                "mutation_type": "SNP",
            }
        )

    mutation_sites.sort(key=lambda x: x["pos"])
    capped = mutation_sites[:MUTATION_SITE_CAP]

    pattern_counts: dict[str, int] = {}
    for site in mutation_sites:
        p = site["pattern"]
        pattern_counts[p] = pattern_counts.get(p, 0) + 1

    snp_count = sum(1 for s in capped if s["mutation_type"] == "SNP")
    del_count = sum(1 for s in capped if s["mutation_type"] == "DELETION")

    mutation_hit_pairs = [(s["pos"], s["pattern"]) for s in mutation_sites]
    heatmap = _build_motif_heatmap(
        kmp_hits,
        mutation_hit_pairs,
        all_patterns,
        qualifying_patterns,
        seq_len,
    )

    return {
        "total": len(mutation_sites),
        "snp_count": snp_count,
        "del_count": del_count,
        "exact_total": exact_total,
        "sites": capped,
        "pattern_counts": pattern_counts,
        "max_edits": cfg_max,
        "skipped_short_patterns": skipped_short,
        "no_qualifying_patterns": False,
        "qualifying_patterns": qualifying_patterns,
        "heatmap": heatmap,
    }


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(_VIZNEW_ROOT / "templates"),
        static_folder=str(_VIZNEW_ROOT / "static"),
    )
    app.secret_key = "igda-viznew-dev-secret"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

    @app.before_request
    def _permanent_session_for_workspace():
        if request.endpoint not in (None, "static", "home"):
            session.permanent = True

    @app.context_processor
    def _inject_session_flags():
        return {
            "has_active_benchmark": _has_benchmark(),
            "benchmark_workspace_id": bench_ws.workspace_id() or "",
        }

    def _restore_input_meta_from_workspace() -> None:
        if session.get("input_meta") or not _has_benchmark():
            return
        cfg = bench_ws.load_upload_config() or {}
        seq = bench_ws.load_session_text()
        session["input_meta"] = {
            "source": cfg.get("input_mode", "fasta"),
            "filename": cfg.get("filename", "session input"),
            "length": len(seq),
            "patterns": cfg.get("patterns_list", []),
            "max_edits": cfg.get("max_edits", 1),
        }
        session.modified = True
        print("[BenchmarkSession] Restored input_meta from workspace")

    @app.before_request
    def _hydrate_workspace_on_nav():
        if request.endpoint in (None, "static", "home"):
            return
        _restore_input_meta_from_workspace()
        wid = bench_ws.workspace_id()
        if wid:
            print(f"[BenchmarkSession] Route {request.path} workspace={wid}")

    @app.route("/api/session/attach", methods=["POST"])
    def attach_workspace():
        payload = request.get_json(silent=True) or {}
        wid = payload.get("workspace_id")
        if not isinstance(wid, str) or not wid:
            return {"ok": False, "error": "missing workspace_id"}, 400
        if not bench_ws.workspace_exists(wid):
            return {"ok": False, "error": "unknown workspace"}, 404
        session["workspace_id"] = wid
        session.modified = True
        _restore_input_meta_from_workspace()
        print(f"[BenchmarkSession] Attached workspace {wid}")
        return {"ok": True, "workspace_id": wid}

    @app.route("/")
    def home():
        return render_template("home.html", current_step="home")

    @app.route("/api/session/upload-draft", methods=["POST"])
    def save_upload_draft():
        """Persist form edits without re-running the benchmark."""
        payload = request.get_json(silent=True) or {}
        if not bench_ws.workspace_id() and not _has_benchmark():
            return jsonify({"ok": False, "error": "no workspace"}), 400
        bench_ws.ensure_workspace()
        existing = bench_ws.load_upload_config() or {}
        patterns_raw = payload.get("patterns", existing.get("patterns", ""))
        patterns_list = (
            _parse_patterns(patterns_raw) if patterns_raw else existing.get("patterns_list", [])
        )
        merged = {
            **existing,
            "input_mode": payload.get("input_mode", existing.get("input_mode", "fasta")),
            "patterns": patterns_raw,
            "patterns_list": patterns_list,
            "max_edits": int(payload.get("max_edits", existing.get("max_edits", 1))),
            "prefix_chars": str(
                payload.get("prefix_chars", existing.get("prefix_chars", ""))
            ),
            "manual_text": payload.get(
                "manual_text", existing.get("manual_text", "")
            )[:8000],
        }
        bench_ws.save_upload_config(merged)
        if session.get("input_meta"):
            session["input_meta"] = {
                **session["input_meta"],
                "patterns": patterns_list,
                "max_edits": merged["max_edits"],
            }
            session.modified = True
        print("[BenchmarkSession] Saved upload draft")
        return jsonify({"ok": True})

    @app.route("/upload")
    def upload():
        upload_state = _upload_form_defaults()
        status = bench_ws.load_benchmark_status()
        has_bench = _has_benchmark()
        if has_bench and not status.get("completed"):
            status = {**status, "hasRun": True, "completed": True}
        artifacts = upload_state.get("compression_artifacts") or bench_ws.load_compression_artifacts()
        benchmark = _get_benchmark() if has_bench else None
        return render_template(
            "upload.html",
            current_step="upload",
            upload_state=upload_state,
            benchmark_status=status,
            has_benchmark=has_bench,
            session_restored=bool(has_bench and status.get("completed")),
            compression_artifacts=artifacts,
            benchmark_summary=benchmark,
        )

    @app.route("/run", methods=["POST"])
    def run():
        bench_ws.ensure_workspace()
        bench_ws.save_benchmark_status(
            {"hasRun": False, "running": True, "completed": False}
        )
        mode = request.form.get("input_mode", "manual")
        text = ""
        filename = "manual input"
        uploaded_files: list[dict[str, Any]] = []

        if mode == "fasta":
            upload = request.files.get("fasta_file")
            if upload and upload.filename:
                try:
                    dest, file_meta = bench_ws.persist_uploaded_file(
                        upload, max_len=_MAX_SEQUENCE_LEN
                    )
                    suffix = Path(file_meta["name"]).suffix.lower()
                    if suffix in {".fa", ".fasta", ".fna", ".faa", ".ffn", ".frn"}:
                        text = _read_fasta_capped(dest, _MAX_SEQUENCE_LEN)
                    else:
                        raw = dest.read_text(encoding="utf-8", errors="ignore")
                        if raw.lstrip().startswith(">"):
                            text = _read_fasta_capped(dest, _MAX_SEQUENCE_LEN)
                        else:
                            text = raw[:_MAX_SEQUENCE_LEN]
                    filename = file_meta["name"]
                    uploaded_files = [file_meta]
                except Exception as exc:
                    flash(f"Could not read file: {exc}", "error")
                    return redirect(url_for("upload"))
            else:
                text, filename = bench_ws.read_source_text(max_len=_MAX_SEQUENCE_LEN)
                cfg = bench_ws.load_upload_config() or {}
                uploaded_files = list(cfg.get("uploaded_files") or [])
                if not text:
                    flash("Choose a FASTA or text file to upload.", "error")
                    return redirect(url_for("upload"))
        else:
            text = request.form.get("manual_text", "").strip()
            if not text:
                flash("Enter sequence text or switch to file upload.", "error")
                return redirect(url_for("upload"))
            filename = "manual input"

        prefix = request.form.get("prefix_chars", "").strip()
        text, limit_note = _apply_length_limit(text, prefix)
        if limit_note:
            flash(limit_note, "info")

        if not text:
            flash("Input is empty after loading or truncation.", "error")
            return redirect(url_for("upload"))

        raw_patterns = request.form.get("patterns", "")
        patterns = _parse_patterns(raw_patterns)
        if not patterns:
            flash("Enter at least one search pattern.", "error")
            return redirect(url_for("upload"))

        max_edits = int(request.form.get("max_edits", 1))
        config = RunConfig(
            warmup=0,
            trials=_TRIALS,
            selected_algorithm_ids=[],
            selected_compression_ids=[],
            max_edits=max_edits,
        )
        summary = igda.run_benchmark(text, patterns, config)
        benchmark = _enrich_benchmark(_summary_public(summary), text, patterns)
        multi_n = _multi_n_benchmark(text, patterns, max_edits)
        mutation_report = compute_mutation_report(benchmark, text, patterns, max_edits)

        bench_ws.save_session_text(text)
        bench_ws.save_benchmark(benchmark)
        bench_ws.save_multi_n(multi_n)
        artifacts = bench_ws.build_compression_artifacts(
            text, filename, benchmark.get("compression_rows", [])
        )
        if mutation_report is not None:
            bench_ws.save_mutation_report(mutation_report)

        manual_preview = text[:8000] if mode == "manual" else ""
        bench_ws.save_upload_config(
            {
                "input_mode": mode,
                "patterns": raw_patterns,
                "patterns_list": patterns,
                "max_edits": max_edits,
                "prefix_chars": prefix,
                "manual_text": manual_preview,
                "filename": filename,
                "uploaded_files": uploaded_files,
                "compression_artifacts": artifacts,
                "benchmark_input_config": {
                    "max_sequence_len": _MAX_SEQUENCE_LEN,
                    "trials": _TRIALS,
                    "max_edits": max_edits,
                },
            }
        )
        now = datetime.now(timezone.utc).isoformat()
        bench_ws.save_benchmark_status(
            {
                "hasRun": True,
                "running": False,
                "completed": True,
                "lastRunAt": now,
            }
        )

        session["input_meta"] = {
            "source": mode,
            "filename": filename,
            "length": len(text),
            "patterns": patterns,
            "max_edits": max_edits,
        }
        session.pop("benchmark", None)
        session.pop("multi_n", None)
        _clear_session_text(session.get("text_path"))
        session.pop("text_path", None)
        _clear_mutation_report(session.get("mutation_report_path"))
        session.pop("mutation_report_path", None)
        session.pop("text_preview", None)
        session.modified = True
        print("[BenchmarkSession] Run complete - session saved to workspace")
        return redirect(url_for("pattern"))

    @app.route("/download/compression/<algorithm_id>")
    def download_compression(algorithm_id: str):
        path = bench_ws.compression_artifact_path(algorithm_id)
        if not path:
            flash("No compressed file for that algorithm in this session.", "error")
            return redirect(url_for("compression"))
        name = path.name
        for entry in bench_ws.load_compression_artifacts():
            if entry.get("algorithm") == algorithm_id:
                name = entry.get("compressed_file_name", name)
                break
        print(f"[BenchmarkSession] Download {algorithm_id} -> {name}")
        return send_file(
            path,
            as_attachment=True,
            download_name=name,
            mimetype="text/plain",
        )

    @app.route("/pattern")
    def pattern():
        return render_template(
            "pattern.html",
            current_step="pattern",
            meta=session.get("input_meta"),
            benchmark=_get_benchmark(),
            has_benchmark=_has_benchmark(),
        )

    @app.route("/compression")
    def compression():
        return render_template(
            "compression.html",
            current_step="compression",
            meta=session.get("input_meta"),
            benchmark=_get_benchmark(),
            compression_artifacts=bench_ws.load_compression_artifacts(),
            has_benchmark=_has_benchmark(),
        )

    @app.route("/analysis")
    def analysis():
        benchmark = _get_benchmark()
        meta = session.get("input_meta")
        has_benchmark = _has_benchmark()
        mutation_report = _get_mutation_report()

        needs_recompute = (
            has_benchmark
            and benchmark
            and meta
            and meta.get("max_edits", 0) >= 1
            and (mutation_report is None or "heatmap" not in (mutation_report or {}))
        )
        if needs_recompute:
            text = _session_sequence_text()
            if text:
                mutation_report = compute_mutation_report(
                    benchmark, text, meta.get("patterns", []), meta.get("max_edits", 0)
                )
                if mutation_report is not None:
                    bench_ws.save_mutation_report(mutation_report)

        return render_template(
            "analysis.html",
            current_step="analysis",
            meta=meta,
            benchmark=benchmark,
            multi_n=_get_multi_n(),
            compression_artifacts=bench_ws.load_compression_artifacts(),
            has_benchmark=has_benchmark,
            mutation_report=mutation_report,
            mutation_unavailable=bool(
                has_benchmark
                and meta
                and meta.get("max_edits", 0) >= 1
                and mutation_report is None
            ),
        )

    @app.route("/reset")
    def reset():
        print("[BenchmarkSession] Reset triggered by user")
        _clear_session_text(session.get("text_path"))
        _clear_mutation_report(session.get("mutation_report_path"))
        bench_ws.clear_workspace()
        session.clear()
        return redirect(url_for("home"))

    return app
