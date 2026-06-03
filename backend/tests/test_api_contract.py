from fastapi.testclient import TestClient

from src.core.models import Artifact, Job
from src.main import app


class FakeSession:
    async def get(self, model, object_id):
        if model is Job and object_id == 1:
            return Job(id=1, job_type="analysis", status="pending", input={"message": "hi"})
        if model is Artifact and object_id == 1:
            return Artifact(id=1, kind="plotly", title="Chart", mime_type="application/json", payload={"data": []})
        return None


async def fake_get_session():
    yield FakeSession()


def test_healthz_and_metadata_endpoints_match_frontend_contract() -> None:
    from src.core.database import get_session

    app.dependency_overrides[get_session] = fake_get_session
    client = TestClient(app)

    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/jobs/1").json()["status"] == "pending"
    assert client.get("/api/jobs/1").json()["status"] == "pending"
    assert client.get("/artifacts/1/metadata").json()["title"] == "Chart"
    assert client.get("/api/artifacts/1/metadata").json()["title"] == "Chart"
    assert client.get("/jobs/404").status_code == 404

    app.dependency_overrides.clear()
