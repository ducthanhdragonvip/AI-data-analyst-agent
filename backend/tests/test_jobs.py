import pytest

from src.modules.api.controllers.jobs import JobStateMachine


def test_job_state_machine_allows_worker_lifecycle() -> None:
    machine = JobStateMachine("pending")

    machine.transition_to("running")
    machine.transition_to("succeeded")

    assert machine.status == "succeeded"


def test_job_state_machine_rejects_invalid_transition() -> None:
    machine = JobStateMachine("succeeded")

    with pytest.raises(ValueError):
        machine.transition_to("running")
