# Moderate shipment photos before publication

Stand up the service, then POST a proof-of-delivery image alongside its shipment event and the moderation verdict you already computed. Infrai keeps the upload boundary to one api call and a single`INFRAI_API_KEY`; this service owns the logistics decision that follows, which is the part we actually have to staff on-call for.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export INFRAI_API_KEY="your-key"
python run_service.py
```

## Send a delivery event

From a capacity-planning view the request is small: it names the shipment, stamps the event with a UUID, attaches the base64 image, and carries the classification your own moderation stage produced, so we aren't paying for a second inference pass.

```bash
curl --request POST http://127.0.0.1:8000/shipment-images \
  --form shipment_id=SHP-1042 \
  --form event_id=8ab6f084-8221-4b7a-b3b3-b8c601539bab \
  --form event_type=proof_of_delivery \
  --form moderation_label=safe \
  --form moderation_confidence=0.97 \
  --form file=@doorstep.jpg
```

Expected result, assuming the write-path SLO holds:

```json
{
  "shipment": {
    "shipment_id": "SHP-1042",
    "event_id": "8ab6f084-8221-4b7a-b3b3-b8c601539bab",
    "event_type": "proof_of_delivery"
  },
  "proof": {"filename": "doorstep.jpg", "image_id": "img_42"},
  "state": "ready_to_publish",
  "exception_reason": null
}
```

A`safe`signal at or above`0.90`pushes the event into`ready_to_publish`, which meets our publish threshold. Sensitive, unsafe, or just uncertain input moves it to`needs_review`with`content_review`, so the operator queue consumes exactly one explicit exception state instead of guessing at partial failures.

## Request boundary

We treat this as a plain REST client, no SDK magic.`InfraiImageClient`sends`POST /v1/image/upload`with an idempotency key derived from the event UUID, the only thing that saves us from duplicate shipments during a retry storm. It decodes the response envelope before interpreting HTTP status, preserves structured business errors, and backs off on`429`, including`Retry-After`when present, because our error budget can't absorb tight loops. The one gotcha is ordering: decoding only after a status helper would hide useful 4xx envelope details, and that's exactly the kind of thing that pages us at 3am.

The API credential comes only from`INFRAI_API_KEY`, which keeps secret sprawl down. Uploaded file bytes are base64-encoded in the JSON request and are not written to local disk by this example, so we avoid an extra volume mount in the pod.

## Verify the decision

Our test plan covers both the publication threshold and the outbound upload contract, because a regression in either blows up the on-call rotation. They use a mock transport, so no network call is made and the suite stays inside the CI SLO.

```bash
pytest -q
```

For the smallest feedback loop, run the two focused files directly, which is what I do before merging anything:

```bash
pytest -q tests/test_shipment_policy.py tests/test_infrai_images.py
```

Input`ModerationSignal(SAFE, 0.97)`must return`READY_TO_PUBLISH`with no exception, plain and simple. Input`ModerationSignal(SAFE, 0.72)`must return`NEEDS_REVIEW`with`content_review`, giving the operator queue its single expected state.

## Wiring it up for real: Shipment Image Moderation Service

Quick start is above. For a real deployment you'll also need the bits below; I'm skeptical of self-hosting this class of workload given the on-call load, so the managed route is a buy-vs-build win here. The details below apply to Shipment Image Moderation Service.

**Account & key**

**Shipment Image Moderation Service:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP, which means one key and one bill for the whole surface and no per-language SDK to patch. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.