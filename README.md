# igda — Intelligent Genome & Data Anomaly Detection (DAA lab)

## Layout

| Path | Role |
|------|------|
| `data/raw/` | Place downloaded FASTA (e.g. NCBI exports). Not committed by default. |
| `data/processed/` | Optional cleaned or truncated sequences for experiments. |
| `src/igda/input/` | Load files, pattern lists, and run settings. |
| `src/igda/core/` | Shared types (e.g. corpus, config, result summaries). |
| `src/igda/matchers/` | String algorithms: naive, KMP, Horspool, Aho–Corasick, edit distance. |
| `src/igda/bench/` | Timings, trials, and fair comparison. |
| `src/igda/compression/` | Huffman, RLE, and compression metrics. |
| `src/igda/viz/` | Plots; reads only summary data. |
| `src/igda/report/` | Generated reports (Markdown/PDF) from summary data. |
| `tests/` | Unit tests. |

The code lives under `igda` so the name `input` is not a top-level import (`input` is a Python builtin when used carelessly at the root).

## Install (editable, for later)

```text
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

From the project root (`DAA_el`), always run commands after `cd` into that folder (Windows example):

```text
cd "c:\Users\sh\Documents\sem 4\DAA_el"
```

---

## How to run (what is “backend” vs UI)

This repo has **one Python package** (`igda` under `src/igda/`) that implements matchers, compression, benchmarking, and input helpers. That package **is** the backend logic — there is **no separate backend server** unless you add one later.

| What you want | What to run |
|---------------|-------------|
| **Web dashboard (Flask)** — home page + analytics, uses `igda` internally | **`src/igda/viz/app.py`** (see below) |
| **Scripts / terminal / notebooks** — `import igda` | Same install; no extra “server” file |
| **Tests** | `pytest` from project root |

### Start the web UI (recommended entry file)

**Run this file:**

```text
python src/igda/viz/app.py
```

Then open a browser:

- **Home (choose input mode):** [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
- **Analytics (full form + results):** [http://127.0.0.1:5000/analytics](http://127.0.0.1:5000/analytics)  
  (Home’s “Continue” button redirects here with the selected mode.)

### Start the new wizard frontend (viz2)

```text
python src/igda/viz/app_viz2.py
```

### Start vizNew (upload any FASTA — no hardcoded paths)

```text
python src/igda/vizNew/app.py
```

Open [http://127.0.0.1:5003/](http://127.0.0.1:5003/) for the cinematic home animation, then **Upload** in the sidebar (or `/upload`) to load FASTA/text and run benchmarks.

**DNA hero animation:** Vanilla Three.js helix on the home page (`static/js/helix.js`, spec: `src/igda/vizNew/IGDA_HELIX_THREEJS.md`). Optional R3F sources remain in `vizNew/frontend/` if you need that pipeline.

Alternative launcher:

```text
python DAA/viz2.py
```

Stop the server with **Ctrl+C** in the terminal.

**Alternative launcher** (same Flask app, useful if you keep a copy under `DAA/`):

```text
python DAA/new.py
```

Both load the Flask app from `igda.viz.flask_app` / `igda.viz.app`.

---

## Matchers (backend — front end picks one by `id`)

- `igda.list_algorithms()` → `AlgorithmInfo` for each: **time** and **space** fields for your DAA write-up, plus `match_kind` (exact vs approximate). Call `.as_public_dict()` for JSON in an API later.
- `igda.run_match(algorithm_id, text, patterns, **kwargs)` with `kwargs` e.g. `max_edits` for `edit_distance` only.

Algorithm ids: `naive`, `kmp`, `horspool`, `ahocorasick`, `edit_distance`.

## Compression (backend — user picks codec by `id`)

- `igda.list_compressions()` -> `CompressionInfo` entries with complexity/notes.
- `igda.run_compression(compression_id, text)` -> `CompressionResult` with:
  - `original_bytes`
  - `compressed_bytes`
  - `ratio` (`compressed/original`)
  - `percent_saved` (`(1-ratio)*100`)

Compression ids: `huffman`, `rle`.

## Benchmark (simple analysis layer)

- `igda.RunConfig(...)` sets warmup/trials + selected matcher/compression ids.
- `igda.run_benchmark(text, patterns, config)` runs all selected options on the **same input** and returns:
  - matcher timing rows (median/min/max/p95, match_count, extras)
  - compression rows (timing + original/compressed bytes + ratio + percent_saved)
  - notes (e.g. exact + approximate comparison caveat)

## Input helpers (simple ingestion)

- `igda.load_fasta_sequence(path)` -> one continuous sequence string (ignores FASTA headers and blank lines).
- `igda.load_patterns_file(path)` -> list of patterns (supports comments `#` and comma-separated lines).
- `igda.prepare_run_inputs(...)` -> returns `(text, patterns)` ready for matching/benchmarking.

## Flask UI (viz)

- **Start file:** [`src/igda/viz/app.py`](src/igda/viz/app.py) — run with `python src/igda/viz/app.py` from project root after `pip install -e ".[dev]"`.
- **Implementation:** [`src/igda/viz/flask_app.py`](src/igda/viz/flask_app.py) defines routes; templates live in [`src/igda/viz/templates/`](src/igda/viz/templates/).

Features included:
- **Home** (`/`): helix-style landing; pick input mode only.
- **Analytics** (`/analytics`): dropdowns for algorithms + compression; FASTA / manual / mixed; per-case tables; best matcher and compression hints.
- FASTA: first N chars, single slice or multiple segments.
- Manual: one string per line, each line is its own case.
- Mixed: FASTA-derived cases and manual cases in one run (separate rows).

## Run tests

```text
pytest
```
