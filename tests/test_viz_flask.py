from __future__ import annotations

from igda.viz import create_app


def test_flask_index_get() -> None:
    app = create_app()
    app.testing = True
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "HELIX AI" in body


def test_home_post_redirects_to_analytics() -> None:
    app = create_app()
    app.testing = True
    client = app.test_client()
    resp = client.post("/", data={"input_mode": "manual_only"}, follow_redirects=False)
    assert resp.status_code in (301, 302)
    assert "/analytics" in resp.headers.get("Location", "")


def test_flask_analytics_post_manual_strings() -> None:
    app = create_app()
    app.testing = True
    client = app.test_client()
    resp = client.post(
        "/analytics",
        data={
            "input_mode": "manual_only",
            "manual_strings": "ACGTACGT\nGGGGTTTT\nAAAACCCC",
            "patterns": "ACG,TTT",
            "selected_algorithms": ["naive", "kmp"],
            "selected_compressions": ["rle"],
            "warmup": "0",
            "trials": "1",
            "max_edits": "1",
            "prefix_chars": "1000",
            "run_mode": "multiple",
            "segment_count": "3",
            "segment_length": "100",
        },
    )
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Case Summary" in body

