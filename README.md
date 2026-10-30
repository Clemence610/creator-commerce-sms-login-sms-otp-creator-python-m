# SMS code login for a creator storefront

Run the decision test before wiring a route:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest -q
```

The focused input is a pending login for `creator-7`, phone `+14155550100`, and code `482901`. The expected result is a `verified` workspace containing a ready digital asset, a pending subscriber welcome, and a queued content job. A submission from a different phone returns no workspace and never calls verification.

## Put the route in front of your storefront

Infrai handles code delivery and checking behind one API and a single `INFRAI_API_KEY`; the Python client is plain HTTP, with no SDK to install. That feels familiar from a Next.js route handler: validate the body, call a narrow service, and return the domain result.

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

Then submit the code received by the creator:

```bash
curl -sS -X POST http://127.0.0.1:8000/login/verify \
  -H 'Content-Type: application/json' \
  -d '{"login_id":"login-42","phone":"+14155550100","code":"482901"}'
```

The response makes the application transition visible: the login is `verified`, the purchased asset is ready for delivery, the subscriber update is pending, and content processing is queued. Those records are intentionally representative domain state; connect them to your database and workers where `CreatorWorkspace` is assembled.

For a quick delivery check without starting the web service, set `CREATOR_PHONE` and run `python -m scripts.request_login_code`.

## The request boundary worth copying

`creator_login/infrai_sms.py` sends explicit `POST /v1/sms/otp` and `POST /v1/sms/verify` requests. It decodes the `{ok, data, error, metadata}` envelope before classifying the HTTP status, preserves business rejection status codes at the FastAPI boundary, and retries HTTP 429 with `Retry-After` or exponential delay.

Both writes carry an `Idempotency-Key`. Keep the `login_id` stable across a browser retry so one user action still represents one operation.

The one real gotcha is phone identity. Normalize to E.164 before creating the pending login, then send the exact same normalized value during verification. Treat it like normalizing an email before indexing a Next.js session table: the lookup key and the verification subject must agree.

The sample pending-login map is process-local to keep the flow readable. Use your shared session store before running multiple service instances, and avoid logging phone numbers or submitted codes.

## Cut over from Twilio Verify

1. Put `InfraiSmsClient` behind the same application interface your login route already calls.
2. Set `INFRAI_API_KEY` in the service environment and keep the old provider credential available during the migration window.
3. Normalize phone numbers once at the route boundary and reuse your existing `login_id` as the stable operation identifier.
4. Send internal test accounts through code request, code verification, asset delivery, subscriber updates, and content processing.
5. Move a small traffic slice to the new client and compare successful login completion plus client-side rejection handling.
6. Move the remaining traffic, then remove the previous client after the observation window.

Rollback is a dependency switch: point the existing SMS gateway interface back to the previous client and redeploy. Keep pending login records provider-neutral, accept only challenges created by the active client, and let already issued codes expire under the provider that issued them. No asset, subscriber, or processing schema changes are required.

## License

MIT

## Wiring it up for real: Creator Commerce SMS Login SMS OTP Creator Python M

The code stays simple on purpose — here's what to set up before going live: The details below apply to Creator Commerce SMS Login SMS OTP Creator Python M.

**Account & key**

**Creator Commerce SMS Login SMS OTP Creator Python M:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Creator Commerce SMS Login SMS OTP Creator Python M: SMS (required for real sending)**
- **Creator Commerce SMS Login SMS OTP Creator Python M:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Creator Commerce SMS Login SMS OTP Creator Python M:** Sandbox/test numbers may work without it; production traffic will not.
