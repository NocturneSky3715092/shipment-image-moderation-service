from shipment_moderation.shipment_policy import (
    ModerationLabel,
    ModerationSignal,
    ShipmentState,
    decide_state,
)


def test_high_confidence_safe_proof_can_be_published() -> None:
    state, reason = decide_state(ModerationSignal(ModerationLabel.SAFE, 0.97))

    assert state is ShipmentState.READY_TO_PUBLISH
    assert reason is None


def test_uncertain_proof_creates_review_exception() -> None:
    state, reason = decide_state(ModerationSignal(ModerationLabel.SAFE, 0.72))

    assert state is ShipmentState.NEEDS_REVIEW
    assert reason == "content_review"

