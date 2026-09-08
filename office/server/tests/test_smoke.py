import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


def test_health_ok():
    r = TestClient(app).get("/health")
    assert r.status_code == 200
    assert r.json()["status"] in {"ok", "degraded"}
