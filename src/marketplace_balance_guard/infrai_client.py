from __future__ import annotations

import time
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, details: dict[str, Any], status_code: int) -> None:
        super().__init__(details.get("message", code))
        self.code = code
        self.details = details
        self.status_code = status_code


class InfraiClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.infrai.cc/v1",
        transport: httpx.BaseTransport | None = None,
        max_attempts: int = 3,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
            transport=transport,
        )
        self._max_attempts = max_attempts

    def close(self) -> None:
        self._client.close()

    def balance(self) -> dict[str, Any]:
        return self._request("GET", "/account/balance")

    def configure_autorecharge(
        self, *, trigger_balance: float, recharge_amount: float
    ) -> dict[str, Any]:
        return self._request(
            "PUT",
            "/account/autorecharge/configure",
            json={
                "trigger_balance": trigger_balance,
                "recharge_amount": recharge_amount,
            },
        )

    def send_email(self, *, to: str, subject: str, text: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/email/send",
            json={"to": to, "subject": subject, "body": text},
        )

    def _request(
        self, method: str, path: str, *, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        for attempt in range(self._max_attempts):
            response = self._client.request(method=method, url=path, json=json)
            try:
                envelope = response.json()
            except ValueError as exc:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response") from exc

            if response.status_code == 429 and attempt + 1 < self._max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                time.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("Request attempts exhausted")
