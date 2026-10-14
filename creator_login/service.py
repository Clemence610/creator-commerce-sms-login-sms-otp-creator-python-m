from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field


class SmsGateway(Protocol):
    def otp(self, to: str, operation_id: str) -> None:
        """Send a code for one stable login operation."""

    def verify(self, to: str, code: str, operation_id: str) -> None:
        """Verify a submitted code for one stable login operation."""


class CodeRequest(BaseModel):
    login_id: str = Field(min_length=3, max_length=80)
    creator_id: str = Field(min_length=3, max_length=80)
    phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")


class CodeSubmission(BaseModel):
    login_id: str = Field(min_length=3, max_length=80)
    phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    code: str = Field(pattern=r"^\d{4,8}$")


class CodeSent(BaseModel):
    login_id: str
    state: str = "code_sent"


class AssetDelivery(BaseModel):
    asset_id: str
    title: str
    delivery: str


class SubscriberUpdate(BaseModel):
    subscriber_id: str
    update: str


class ContentJob(BaseModel):
    content_id: str
    processing: str


class CreatorWorkspace(BaseModel):
    login_id: str
    creator_id: str
    state: str
    assets: list[AssetDelivery]
    subscriber_updates: list[SubscriberUpdate]
    content_jobs: list[ContentJob]


@dataclass(frozen=True)
class PendingLogin:
    creator_id: str
    phone: str


class CreatorLoginService:
    def __init__(self, sms: SmsGateway) -> None:
        self.sms = sms
        self.pending: dict[str, PendingLogin] = {}

    def request_code(self, request: CodeRequest) -> CodeSent:
        self.sms.otp(request.phone, f"creator-login:{request.login_id}:send")
        self.pending[request.login_id] = PendingLogin(request.creator_id, request.phone)
        return CodeSent(login_id=request.login_id)

    def verify_code(self, request: CodeSubmission) -> CreatorWorkspace | None:
        pending = self.pending.get(request.login_id)
        if pending is None or pending.phone != request.phone:
            return None

        self.sms.verify(
            request.phone,
            request.code,
            f"creator-login:{request.login_id}:verify",
        )
        del self.pending[request.login_id]
        return CreatorWorkspace(
            login_id=request.login_id,
            creator_id=pending.creator_id,
            state="verified",
            assets=[
                AssetDelivery(
                    asset_id="course-editing-01",
                    title="Editing Workflow Pack",
                    delivery="ready",
                )
            ],
            subscriber_updates=[
                SubscriberUpdate(
                    subscriber_id="subscriber-1042",
                    update="welcome_pending",
                )
            ],
            content_jobs=[
                ContentJob(content_id="launch-reel-07", processing="queued")
            ],
        )
