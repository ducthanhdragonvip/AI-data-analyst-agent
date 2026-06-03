import pytest

from src.modules.data.vector_db.chroma_store import BusinessKnowledgeStore


def test_business_knowledge_store_accepts_only_business_document_types(tmp_path) -> None:
    store = BusinessKnowledgeStore(path=tmp_path)

    store.upsert_document(
        document_id="refund-sop",
        document_type="sop_business_process",
        title="Refund SOP",
        content="Refund requests over 500 need finance approval.",
    )

    hits = store.search("finance approval", document_types=["sop_business_process"])

    assert hits[0]["metadata"]["document_type"] == "sop_business_process"
    assert "finance approval" in hits[0]["document"]


@pytest.mark.parametrize("document_type", ["dataset", "database", "schema_profile", "postgres_table"])
def test_business_knowledge_store_rejects_dataset_and_database_documents(tmp_path, document_type: str) -> None:
    store = BusinessKnowledgeStore(path=tmp_path)

    with pytest.raises(ValueError):
        store.upsert_document(
            document_id="sales",
            document_type=document_type,
            title="Sales table",
            content="Dataset profile for sales table",
        )
