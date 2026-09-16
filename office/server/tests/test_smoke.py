import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


def test_health_ok():
    r = TestClient(app).get("/health")
    assert r.status_code == 200
    assert r.json()["status"] in {"ok", "degraded"}


def test_board_and_state_endpoints(tmp_path, monkeypatch):
    import config
    monkeypatch.setattr(
        type(config.settings), "data_dir",
        property(lambda self: tmp_path), raising=False,
    )
    client = TestClient(app)
    assert client.get("/office/state").status_code == 200
    assert client.get("/board/cards").json() == []
    r = client.post("/board/cards", json={"title": "샘플", "tag": "feature"})
    assert r.status_code == 200 and r.json()["assignee"] == "후니"
