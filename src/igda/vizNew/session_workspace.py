"""Persistent benchmark workspace on disk (survives navigation; small Flask session cookie)."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from flask import session
from werkzeug.utils import secure_filename

import igda

_MAX_MANUAL_PREVIEW = 8_000
_LOG_PREFIX = "[BenchmarkSession]"


def _root() -> Path:
    import tempfile

    return Path(tempfile.gettempdir()) / "igda_viznew_workspace"


def workspace_exists(wid: str) -> bool:
    return (_root() / wid).is_dir()


def workspace_id() -> str | None:
    wid = session.get("workspace_id")
    return wid if isinstance(wid, str) and wid else None


def ensure_workspace(*, create: bool = True) -> Path | None:
    wid = workspace_id()
    if not wid and create:
        wid = uuid4().hex
        session["workspace_id"] = wid
        session.modified = True
        print(f"{_LOG_PREFIX} Created workspace {wid}")
    if not wid:
        return None
    path = _root() / wid
    path.mkdir(parents=True, exist_ok=True)
    (path / "compression").mkdir(exist_ok=True)
    return path


def clear_workspace() -> None:
    wid = session.pop("workspace_id", None)
    session.pop("benchmark_status", None)
    if wid:
        shutil.rmtree(_root() / wid, ignore_errors=True)
        print(f"{_LOG_PREFIX} Cleared workspace {wid}")


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"{_LOG_PREFIX} Saved {path.name}")


def _read_json(path: Path) -> Any | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        print(f"{_LOG_PREFIX} Restored {path.name}")
        return data
    except (json.JSONDecodeError, OSError) as exc:
        print(f"{_LOG_PREFIX} Failed to read {path.name}: {exc}")
        return None


def save_upload_config(config: dict[str, Any]) -> None:
    ws = ensure_workspace()
    if ws:
        _write_json(ws / "upload_config.json", config)


def load_upload_config() -> dict[str, Any] | None:
    ws = ensure_workspace(create=False)
    if not ws:
        return None
    return _read_json(ws / "upload_config.json")


def save_benchmark_status(status: dict[str, Any]) -> None:
    ws = ensure_workspace()
    if ws:
        _write_json(ws / "benchmark_status.json", status)
    session["benchmark_status"] = status
    session.modified = True


def load_benchmark_status() -> dict[str, Any]:
    cached = session.get("benchmark_status")
    if isinstance(cached, dict):
        return cached
    ws = ensure_workspace(create=False)
    if not ws:
        return {"hasRun": False, "running": False, "completed": False}
    status = _read_json(ws / "benchmark_status.json") or {
        "hasRun": False,
        "running": False,
        "completed": False,
    }
    session["benchmark_status"] = status
    session.modified = True
    return status


def save_benchmark(benchmark: dict[str, Any]) -> None:
    ws = ensure_workspace()
    if ws:
        _write_json(ws / "benchmark.json", benchmark)


def load_benchmark() -> dict[str, Any] | None:
    ws = ensure_workspace(create=False)
    if not ws:
        return None
    return _read_json(ws / "benchmark.json")


def save_multi_n(multi_n: list[dict[str, Any]]) -> None:
    ws = ensure_workspace()
    if ws:
        _write_json(ws / "multi_n.json", multi_n)


def load_multi_n() -> list[dict[str, Any]]:
    ws = ensure_workspace(create=False)
    if not ws:
        return []
    return _read_json(ws / "multi_n.json") or []


def save_mutation_report(report: dict[str, Any]) -> str | None:
    ws = ensure_workspace()
    if not ws:
        return None
    path = ws / "mutation_report.json"
    _write_json(path, report)
    return str(path)


def load_mutation_report() -> dict[str, Any] | None:
    ws = ensure_workspace(create=False)
    if not ws:
        return None
    return _read_json(ws / "mutation_report.json")


def save_session_text(text: str, *, max_len: int = 100_000) -> str | None:
    ws = ensure_workspace()
    if not ws:
        return None
    path = ws / "sequence.txt"
    path.write_text(text[:max_len], encoding="utf-8")
    print(f"{_LOG_PREFIX} Saved sequence ({min(len(text), max_len):,} chars)")
    return str(path)


def load_session_text() -> str:
    ws = ensure_workspace(create=False)
    if ws:
        path = ws / "sequence.txt"
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="ignore")
    legacy = session.get("text_path")
    if legacy and Path(legacy).is_file():
        return Path(legacy).read_text(encoding="utf-8", errors="ignore")
    preview = session.get("text_preview")
    return preview if isinstance(preview, str) else ""


def source_file_path() -> Path | None:
    ws = ensure_workspace(create=False)
    if not ws:
        return None
    for pattern in ("source_*", "sequence.txt"):
        matches = list(ws.glob(pattern))
        if matches:
            return matches[0]
    return None


def persist_uploaded_file(upload, *, max_len: int) -> tuple[Path, dict[str, Any]]:
    """Save raw upload to workspace; returns (path, file_meta)."""
    ws = ensure_workspace()
    assert ws is not None
    filename = secure_filename(upload.filename or "upload.txt")
    dest = ws / f"source_{filename}"
    upload.save(dest)
    meta = {
        "id": uuid4().hex,
        "name": filename,
        "size": dest.stat().st_size,
        "type": Path(filename).suffix.lower() or ".txt",
        "uploadedAt": datetime.now(timezone.utc).isoformat(),
        "storedPath": dest.name,
    }
    print(f"{_LOG_PREFIX} Persisted upload {filename}")
    return dest, meta


def read_source_text(*, max_len: int) -> tuple[str, str]:
    """Load sequence from persisted source; returns (text, filename)."""
    cfg = load_upload_config() or {}
    filename = cfg.get("filename", "session input")
    ws = ensure_workspace(create=False)
    if not ws:
        return "", filename

    mode = cfg.get("input_mode", "fasta")
    if mode == "manual":
        manual = cfg.get("manual_text", "")
        if manual:
            return manual[:max_len], filename
        seq = ws / "sequence.txt"
        if seq.is_file():
            return seq.read_text(encoding="utf-8", errors="ignore")[:max_len], filename
        return "", filename

    src = source_file_path()
    if src and src.suffix.lower() in {".fa", ".fasta", ".fna", ".faa", ".ffn", ".frn"}:
        return _read_fasta_file(src, max_len), filename
    if src and src.is_file():
        raw = src.read_text(encoding="utf-8", errors="ignore")
        if raw.lstrip().startswith(">"):
            return _read_fasta_file(src, max_len), filename
        return raw[:max_len], filename
    seq = ws / "sequence.txt"
    if seq.is_file():
        return seq.read_text(encoding="utf-8", errors="ignore")[:max_len], filename
    return "", filename


def _read_fasta_file(path: Path, max_len: int) -> str:
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


def build_compression_artifacts(
    text: str,
    original_filename: str,
    benchmark_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run compressors, write downloadable files, return manifest entries."""
    ws = ensure_workspace()
    if not ws or not text:
        return []

    comp_dir = ws / "compression"
    comp_dir.mkdir(exist_ok=True)
    original_size = len(text.encode("utf-8"))
    artifacts: list[dict[str, Any]] = []

    for row in benchmark_rows:
        algo = row.get("compression_id") or row.get("algorithm", "")
        if not algo:
            continue
        try:
            result = igda.run_compression(algo, text)
        except Exception as exc:
            print(f"{_LOG_PREFIX} Compression artifact failed for {algo}: {exc}")
            continue

        ext = "_huffman.txt" if algo == "huffman" else "_rle.txt"
        out_name = f"{Path(original_filename).stem}{ext}"
        out_path = comp_dir / out_name

        if algo == "huffman":
            payload = result.payload if isinstance(result.payload, dict) else {}
            bundle = {
                "format": "igda-huffman-v1",
                "codes": payload.get("codes", {}),
                "bitstring": payload.get("bitstring", ""),
                "original_file_name": original_filename,
            }
            out_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
            download_bytes = out_path.stat().st_size
        elif algo == "rle":
            runs = result.payload if isinstance(result.payload, list) else []
            bundle = {
                "format": "igda-rle-v1",
                "runs": [[sym, cnt] for sym, cnt in runs],
                "original_file_name": original_filename,
            }
            out_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
            download_bytes = out_path.stat().st_size
        else:
            continue

        ob = int(result.original_bytes)
        cb = max(int(result.compressed_bytes), 1)
        ratio_display = round(ob / cb, 4) if ob else 1.0
        entry = {
            "algorithm": algo,
            "algorithm_name": row.get("compression_name", algo),
            "original_file_name": original_filename,
            "compressed_file_name": out_name,
            "original_size": original_size,
            "compressed_size": int(result.compressed_bytes),
            "file_size_on_disk": download_bytes,
            "compression_ratio": ratio_display,
            "space_saved_percent": round(result.percent_saved, 2),
            "compression_time_ms": round(float(row.get("time_ms_median", 0)), 3),
            "download_route": f"/download/compression/{algo}",
            "metadata": {
                "encoding": bundle["format"],
                "stored_in_workspace": True,
            },
        }
        artifacts.append(entry)
        print(f"{_LOG_PREFIX} Wrote compression artifact {out_name}")

    _write_json(comp_dir / "manifest.json", artifacts)
    return artifacts


def load_compression_artifacts() -> list[dict[str, Any]]:
    ws = ensure_workspace(create=False)
    if not ws:
        return []
    manifest = _read_json(ws / "compression" / "manifest.json")
    return manifest if isinstance(manifest, list) else []


def compression_artifact_path(algorithm_id: str) -> Path | None:
    ws = ensure_workspace(create=False)
    if not ws:
        return None
    comp_dir = ws / "compression"
    for entry in load_compression_artifacts():
        if entry.get("algorithm") == algorithm_id:
            name = entry.get("compressed_file_name")
            if name:
                path = comp_dir / name
                if path.is_file():
                    return path
    # Legacy .igda bundles from older sessions
    for pattern in (f"*_{algorithm_id}.txt", f"*_{algorithm_id}*.igda"):
        matches = sorted(comp_dir.glob(pattern))
        if matches:
            return matches[0]
    return None
