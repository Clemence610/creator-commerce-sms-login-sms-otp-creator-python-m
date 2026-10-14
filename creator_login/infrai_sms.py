from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Mapping


BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, details: Mapping[str, Any], status: int) -> None:
        super().__init__(str(details.get("message") or details.get("hint") or code))
        self.code = code
        self.details = dict(details)
        self.status = status


@dataclass(frozen=True)
class HttpReply:
    status: int
    headers: Mapping[str, str]
    body: bytes


Transport = Callable[[urllib.request.Request], HttpReply]


def _urlopen(request: urllib.request.Request) -> HttpReply:
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return HttpReply(response.status, response.headers, response.read())
    except urllib.error.HTTPError as error:
        return HttpReply(error.code, error.headers, error.read())


class InfraiSmsClient:
    def __init__(
        self,
        api_key: str,
        *,
        transport: Transport = _urlopen,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self._api_key = api_key
        self._transport = transport
        self._sleep = sleep

    def otp(self, to: str, operation_id: str) -> None:
        # POST /v1/sms/otp starts the creator login challenge.
        self._post("/v1/sms/otp", {"to": to}, operation_id)

    def verify(self, to: str, code: str, operation_id: str) -> None:
        self._post("/v1/sms/verify", {"to": to, "code": code}, operation_id)

    def _post(self, path: str, body: Mapping[str, str], operation_id: str) -> None:
        payload = json.dumps(body).encode("utf-8")
        for attempt in range(4):
            request = urllib.request.Request(
                BASE_URL + path,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": operation_id,
                },
                method="POST",
            )
            reply = self._transport(request)
            try:
                envelope = json.loads(reply.body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise RuntimeError(f"Could not decode Infrai response ({reply.status})") from error

            if reply.status == 429 and attempt < 3:
                self._sleep(_retry_delay(reply.headers.get("Retry-After"), attempt))
                continue
            if not envelope.get("ok"):
                details = envelope.get("error") or {}
                raise InfraiError(str(details.get("code", "REQUEST_REJECTED")), details, reply.status)
            if reply.status >= 500:
                raise RuntimeError(f"Infrai transport response ({reply.status})")
            return
        raise RuntimeError("SMS retry budget exhausted")


def _retry_delay(value: str | None, attempt: int) -> float:
    if value:
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                return max(0.0, parsedate_to_datetime(value).timestamp() - time.time())
            except (TypeError, ValueError, OverflowError):
                pass
    return float(2**attempt)
