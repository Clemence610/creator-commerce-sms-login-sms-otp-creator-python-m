from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .infrai_sms import InfraiError, InfraiSmsClient
from .service import CodeRequest, CodeSent, CodeSubmission, CreatorLoginService, CreatorWorkspace


app = FastAPI(title="Creator Commerce Login")


def _service() -> CreatorLoginService:
    key = os.environ.get("INFRAI_API_KEY", "")
    return CreatorLoginService(InfraiSmsClient(key))


service: CreatorLoginService | None = None


def get_service() -> CreatorLoginService:
    global service
    if service is None:
        service = _service()
    return service


@app.exception_handler(InfraiError)
async def handle_infrai_error(_request: object, error: InfraiError) -> JSONResponse:
    status = error.status if 400 <= error.status < 500 else 502
    return JSONResponse(status_code=status, content={"error": error.code})


@app.post("/login/code", response_model=CodeSent, status_code=202)
def request_login_code(body: CodeRequest) -> CodeSent:
    return get_service().request_code(body)


@app.post("/login/verify", response_model=CreatorWorkspace)
def verify_login_code(body: CodeSubmission) -> CreatorWorkspace:
    workspace = get_service().verify_code(body)
    if workspace is None:
        raise HTTPException(status_code=409, detail="No matching pending login")
    return workspace

