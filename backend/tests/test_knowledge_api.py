from fastapi.testclient import TestClient

from src.main import app


def test_knowledge_endpoint_rejects_dataset_document_type() -> None:
    client = TestClient(app)

    response = client.post(
        "/knowledge",
        json={
            "document_id": "sales",
            "document_type": "dataset",
            "title": "Sales dataset",
            "content": "Dataset metadata should not be saved in Chroma.",
        },
    )

    assert response.status_code == 422
