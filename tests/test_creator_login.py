import json
import urllib.error

import pytest

from creator_login.infrai_sms import HttpReply, InfraiError, InfraiSmsClient
from creator_login.service import CodeRequest, CodeSubmission, CreatorLoginService


class AcceptingSms:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def otp(self, to: str, operation_id: str) -> None:
        self.calls.append(("otp", to, operation_id))

    def verify(self, to: str, code: str, operation_id: str) -> None:
        self.calls.append(("verify", to, code, operation_id))


def test_verified_creator_receives_workspace_updates() -> None:
    sms = AcceptingSms()
    login = CreatorLoginService(sms)

    sent = login.request_code(
        CodeRequest(login_id="login-42", creator_id="creator-7", phone="+14155550100")
    )
    workspace = login.verify_code(
        CodeSubmission(login_id="login-42", phone="+14155550100", code="482901")
    )

    assert sent.state == "code_sent"
    assert workspace is not None
    assert workspace.state == "verified"
    assert workspace.assets[0].delivery == "ready"
    assert workspace.subscriber_updates[0].update == "welcome_pending"
    assert workspace.content_jobs[0].processing == "queued"
    assert sms.calls[1] == (
        "verify",
        "+14155550100",
        "482901",
        "creator-login:login-42:verify",
    )


def test_different_phone_cannot_release_creator_workspace() -> None:
    sms = AcceptingSms()
    login = CreatorLoginService(sms)
    login.request_code(
        CodeRequest(login_id="login-42", creator_id="creator-7", phone="+14155550100")
    )

    workspace = login.verify_code(
        CodeSubmission(login_id="login-42", phone="+14155550199", code="482901")
    )

    assert workspace is None
    assert [call[0] for call in sms.calls] == ["otp"]


def test_client_decodes_rejection_envelope_before_status() -> None:
    def transport(request: object) -> HttpReply:
        return HttpReply(
            400,
            {},
            json.dumps(
                {"ok": False, "data": None, "error": {"code": "CODE_REJECTED"}, "metadata": {}}
            ).encode(),
        )

    client = InfraiSmsClient("test-key", transport=transport)
    with pytest.raises(InfraiError) as caught:
        client.verify("+14155550100", "000000", "login-42")

    assert caught.value.status == 400
    assert caught.value.code == "CODE_REJECTED"


def test_client_retries_429_with_same_idempotency_key() -> None:
    requests = []
    sleeps = []

    def transport(request: object) -> HttpReply:
        requests.append(request)
        if len(requests) == 1:
            return HttpReply(429, {"Retry-After": "0"}, b'{"ok":false,"error":{"code":"BUSY"}}')
        return HttpReply(200, {}, b'{"ok":true,"data":{},"error":null,"metadata":{}}')

    client = InfraiSmsClient("test-key", transport=transport, sleep=sleeps.append)
    client.otp("+14155550100", "login-42")

    assert len(requests) == 2
    assert sleeps == [0.0]
    assert all(request.method == "POST" for request in requests)
    assert all(request.headers["Idempotency-key"] == "login-42" for request in requests)
    assert json.loads(requests[0].data) == {"to": "+14155550100"}

