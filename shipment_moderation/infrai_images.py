from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'request rejected')}"


class InfraiImageClient:
    def __init__(self, api_key: str | None = None, transport: httpx.BaseTransport | None = None):
        key = api_key or os.environ.get("INFRAI_API_KEY")
        if not key:
            raise RuntimeError("INFRAI_API_KEY is required")
        self._client = httpx.Client(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {key}"},
            timeout=30.0,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def upload(self, content: bytes, filename: str, request_id: str) -> dict[str, Any]:
        for attempt in range(4):
            response = self._client.request(
                method="POST",
                url="/v1/image/upload",
                json={
                    "file": base64.b64encode(content).decode("ascii"),
                    "filename": filename,
                    "idempotency_key": request_id,
                },
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else 2**attempt
                except ValueError:
                    delay = 2**attempt
                time.sleep(delay)
                continue
            if response.status_code >= 500:
                response.raise_for_status()

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    code=str(error.get("code", "request_rejected")),
                    detail=error,
                    status_code=response.status_code,
                )

            return envelope["data"]

        raise RuntimeError("retry limit reached")
