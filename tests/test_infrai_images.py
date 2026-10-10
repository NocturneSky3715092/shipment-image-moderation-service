import json

import httpx

from shipment_moderation.infrai_images import InfraiImageClient


def test_upload_uses_explicit_method_and_idempotency_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/image/upload"
        assert request.headers["Authorization"] == "Bearer " + "test-key"
        assert request.headers["Content-Type"] == "application/json"
        assert json.loads(request.content) == {
            "file": "aW1hZ2UtYnl0ZXM=",
            "filename": "doorstep.jpg",
            "idempotency_key": "event-42",
        }
        return httpx.Response(
            200,
            content=json.dumps({"ok": True, "data": {"id": "img_42"}, "error": None, "metadata": {}}),
            headers={"Content-Type": "application/json"},
        )

    client = InfraiImageClient(api_key="test-key", transport=httpx.MockTransport(handler))
    try:
        result = client.upload(b"image-bytes", "doorstep.jpg", "event-42")
    finally:
        client.close()

    assert result["id"] == "img_42"
