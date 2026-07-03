"""vizNew persistent benchmark workspace."""

from __future__ import annotations

from pathlib import Path

import pytest

from igda.vizNew import session_workspace as ws
from igda.vizNew.flask_app import create_app


@pytest.fixture
def workspace_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "workspaces"
    monkeypatch.setattr(ws, "_root", lambda: root)
    return root


def test_workspace_save_and_load(workspace_root: Path) -> None:
  app = create_app()
  app.testing = True
  client = app.test_client()

  with client.session_transaction() as sess:
    sess.clear()

  resp = client.post(
    "/run",
    data={
      "input_mode": "manual",
      "manual_text": "ATGATGATGTATAAA" * 80,
      "patterns": "ATG,TATAAA",
      "max_edits": "1",
      "prefix_chars": "",
    },
    follow_redirects=False,
  )
  assert resp.status_code == 302

  with client.session_transaction() as sess:
    wid = sess.get("workspace_id")
  assert wid
  assert (workspace_root / wid / "benchmark.json").is_file()
  assert (workspace_root / wid / "compression" / "manifest.json").is_file()

  upload = client.get("/upload")
  body = upload.get_data(as_text=True)
  assert "Session restored" in body
  assert "Loaded benchmark" in body
  assert "TATAAA" in body

  dl = client.get("/download/compression/huffman")
  assert dl.status_code == 200
  assert len(dl.data) > 0


def test_upload_draft_api(workspace_root: Path) -> None:
  app = create_app()
  client = app.test_client()

  client.post(
    "/run",
    data={
      "input_mode": "manual",
      "manual_text": "GCGCGCGC" * 50,
      "patterns": "GCGC",
      "max_edits": "0",
      "prefix_chars": "",
    },
  )

  draft = client.post(
    "/api/session/upload-draft",
    json={"patterns": "GCGC,AAAA", "max_edits": 2},
  )
  assert draft.status_code == 200
  assert draft.get_json()["ok"] is True

  upload = client.get("/upload")
  assert "AAAA" in upload.get_data(as_text=True)


def test_reset_clears_workspace(workspace_root: Path) -> None:
  app = create_app()
  client = app.test_client()

  client.post(
    "/run",
    data={
      "input_mode": "manual",
      "manual_text": "ACGT" * 100,
      "patterns": "ACGT",
      "max_edits": "0",
      "prefix_chars": "",
    },
  )

  with client.session_transaction() as sess:
    wid = sess["workspace_id"]

  client.get("/reset")

  assert not (workspace_root / wid).exists()

  upload = client.get("/upload")
  assert "Loaded benchmark" not in upload.get_data(as_text=True)
