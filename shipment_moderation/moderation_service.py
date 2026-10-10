from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .infrai_images import InfraiError, InfraiImageClient
from .shipment_policy import ModerationLabel, ModerationSignal, decide_state


class ShipmentEvent(BaseModel):
    shipment_id: str = Field(min_length=1, max_length=80)
    event_id: UUID
    event_type: Literal["proof_of_delivery", "damage_report", "delivery_exception"]


class ProofOfDelivery(BaseModel):
    filename: str
    image_id: str


class ModerationResult(BaseModel):
    shipment: ShipmentEvent
    proof: ProofOfDelivery
    state: Literal["ready_to_publish", "needs_review"]
    exception_reason: str | None


app = FastAPI(title="Shipment image moderation")


@app.post("/shipment-images", response_model=ModerationResult)
def moderate_shipment_image(
    file: Annotated[UploadFile, File()],
    shipment_id: Annotated[str, Form(min_length=1, max_length=80)],
    event_id: Annotated[UUID, Form()],
    event_type: Annotated[
        Literal["proof_of_delivery", "damage_report", "delivery_exception"], Form()
    ],
    moderation_label: Annotated[ModerationLabel, Form()],
    moderation_confidence: Annotated[float, Form(ge=0, le=1)],
) -> ModerationResult:
    event = ShipmentEvent(shipment_id=shipment_id, event_id=event_id, event_type=event_type)
    content = file.file.read()
    client = InfraiImageClient()
    try:
        uploaded = client.upload(content, file.filename or "shipment-image", str(event_id))
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail={"code": exc.code, "error": exc.detail}) from exc
    finally:
        client.close()

    state, reason = decide_state(
        ModerationSignal(label=moderation_label, confidence=moderation_confidence)
    )
    return ModerationResult(
        shipment=event,
        proof=ProofOfDelivery(filename=file.filename or "shipment-image", image_id=str(uploaded["id"])),
        state=state.value,
        exception_reason=reason,
    )

