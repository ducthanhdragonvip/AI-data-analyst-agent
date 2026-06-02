from datetime import UTC, datetime

from app.services.conversations import conversation_was_deleted, message_to_dict


def test_message_to_dict_preserves_artifact_ids() -> None:
    message = type(
        "MessageStub",
        (),
        {
            "id": 7,
            "role": "assistant",
            "content": "Here is a chart.",
            "artifact_ids": [2, 3],
            "created_at": datetime(2026, 6, 2, tzinfo=UTC),
        },
    )()

    result = message_to_dict(message)

    assert result["id"] == 7
    assert result["artifact_ids"] == [2, 3]
    assert result["role"] == "assistant"


def test_conversation_was_deleted_is_false_for_missing_conversation() -> None:
    assert conversation_was_deleted(False) is False
