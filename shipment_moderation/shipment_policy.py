from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ShipmentState(StrEnum):
    RECEIVED = "received"
    READY_TO_PUBLISH = "ready_to_publish"
    NEEDS_REVIEW = "needs_review"


class ModerationLabel(StrEnum):
    SAFE = "safe"
    SENSITIVE = "sensitive"
    UNSAFE = "unsafe"


@dataclass(frozen=True)
class ModerationSignal:
    label: ModerationLabel
    confidence: float


def decide_state(signal: ModerationSignal) -> tuple[ShipmentState, str | None]:
    if signal.label is ModerationLabel.SAFE and signal.confidence >= 0.90:
        return ShipmentState.READY_TO_PUBLISH, None
    return ShipmentState.NEEDS_REVIEW, "content_review"

