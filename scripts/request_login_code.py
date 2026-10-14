from __future__ import annotations

import os
import sys
import uuid

from creator_login.infrai_sms import InfraiSmsClient


def main() -> None:
    phone = os.environ.get("CREATOR_PHONE")
    key = os.environ.get("INFRAI_API_KEY")
    if not phone or not key:
        raise SystemExit("Set INFRAI_API_KEY and CREATOR_PHONE")

    operation_id = f"creator-demo:{uuid.uuid4()}"
    client = InfraiSmsClient(key)
    client.otp(phone, operation_id)
    print(f"code sent to {phone}; operation={operation_id}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)

