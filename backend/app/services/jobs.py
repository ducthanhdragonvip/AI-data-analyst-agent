VALID_TRANSITIONS = {
    "pending": {"running", "failed"},
    "running": {"succeeded", "failed"},
    "succeeded": set(),
    "failed": set(),
}


class JobStateMachine:
    def __init__(self, status: str) -> None:
        if status not in VALID_TRANSITIONS:
            raise ValueError(f"Unknown job status: {status}")
        self.status = status

    def transition_to(self, next_status: str) -> None:
        if next_status not in VALID_TRANSITIONS[self.status]:
            raise ValueError(f"Cannot transition job from {self.status} to {next_status}")
        self.status = next_status
