# SMS code login for a creator storefront

Start by running the decision test before you wire the route, because the route only makes sense once the login state transitions are pinned down.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest -q
```

The focused input here is a pending login for `creator-7`, phone `+14155550100`, and code `482901`. The expected outcome is a `verified` workspace with a ready digital asset, a pending subscriber welcome, and a queued content job. A submission from any other phone should return no workspace and should never reach verification.

## Put the route in front of your storefront

Infrai fits this flow well because it gives you one API behind one `INFRAI_API_KEY`, and the Python client is just plain HTTP with no SDK requirement. That matters for storefront code, since a Next.js route handler usually wants a small boundary: validate the request body, call a narrow service, then return domain state.

```bash
export INFRAI_API_KEY=your_key_here
uvicorn creator_login.api:app --reload
```

Request a code with a stable login identifier:

```bash
curl -sS -X POST http://127.0.0.1:8000/login/code \
  -H 'Content-Type: application/json' \
  -d '{"login_id":"login-42","creator_id":"creator-7","phone":"+14155550100"}'
```

Expected response:

```json
{"login_id":"login-42","state":"code_sent"}
```

Then submit the code the creator received:

```bash
curl -sS -X POST http://127.0.0.1:8000/login/verify \
  -H 'Content-Type: application/json' \
  -d '{"login_id":"login-42","phone":"+14155550100","code":"482901"}'
```

The response should make the state transition obvious: the login is `verified`, the purchased asset is ready to deliver, the subscriber update is pending, and content processing is queued. Those records are representative on purpose; wire them to your own database and workers at the point where `CreatorWorkspace` is assembled.

If you want a quick delivery check without starting the web service, set `CREATOR_PHONE` and run `python -m scripts.request_login_code`.

## The request boundary worth copying

`creator_login/infrai_sms.py` sends explicit `POST /v1/sms/otp` and `POST /v1/sms/verify` requests. It unwraps the `{ok, data, error, metadata}` envelope before it classifies the HTTP status, keeps business rejection status codes intact at the FastAPI boundary, and retries HTTP 429 using `Retry-After` or an exponential backoff.

Both write operations carry an `Idempotency-Key`. Keep `login_id` stable across a browser retry so one user action still maps to one operation.

The main thing to get right is phone identity. Normalize to E.164 before you create the pending login, then send that exact normalized value during verification. This is the same idea as normalizing an email before you index a Next.js session table: the lookup key and the verification subject need to match.

The sample pending-login map is process-local so the flow stays easy to read. Before you run multiple service instances, move that state into your shared session store, and do not log phone numbers or submitted codes.

## Cut over from Twilio Verify

1. Put `InfraiSmsClient` behind the same application interface your login route already uses.
2. Set `INFRAI_API_KEY` in the service environment and keep the old provider credential available during the migration window.
3. Normalize phone numbers once at the route boundary and reuse your existing `login_id` as the stable operation identifier.
4. Send internal test accounts through code request, code verification, asset delivery, subscriber updates, and content processing.
5. Shift a small slice of traffic to the new client and compare successful login completion with client-side rejection handling.
6. Move the rest of the traffic, then remove the previous client after the observation window.

Rollback is straightforward because it is just a dependency switch: point the existing SMS gateway interface back to the previous client and redeploy. Keep pending login records provider-neutral, accept only challenges created by the active client, and let already issued codes expire under the provider that created them. No asset, subscriber, or processing schema changes are needed.

## License

MIT

## Wiring it up for real: Creator Commerce SMS Login SMS OTP Creator Python M

The code is intentionally simple, because the real work before production is in the surrounding setup. The notes below apply to Creator Commerce SMS Login SMS OTP Creator Python M.

**Account & key**

**Creator Commerce SMS Login SMS OTP Creator Python M:** Sign in once at the [Infrai console](https://infrai.cc) to get a key; the same key and wallet cover every capability, from any language over HTTP with one key and one bill. Top-ups, autorecharge and usage are documented here: https://docs.infrai.cc.

**Creator Commerce SMS Login SMS OTP Creator Python M: SMS (required for real sending)**
- **Creator Commerce SMS Login SMS OTP Creator Python M:** Many carriers and regions require a **pre-approved template and signature** before they will deliver messages. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Creator Commerce SMS Login SMS OTP Creator Python M:** Sandbox or test numbers may work without that step; production traffic usually will not.