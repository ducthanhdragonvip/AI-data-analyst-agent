import pytest

from app.services.jobs import JobStateMachine


def test_job_state_machine_allows_valid_transitions() -> None:
    machine = JobStateMachine("pending")

    machine.transition_to("running")
    machine.transition_to("succeeded")

    assert machine.status == "succeeded"


def test_job_state_machine_rejects_invalid_transitions() -> None:
    machine = JobStateMachine("pending")

    with pytest.raises(ValueError):
        machine.transition_to("succeeded")
