# Conduit backend (control arm) - report

Stack: Python 3 stdlib only (http.server.ThreadingHTTPServer, sqlite3, hmac/hashlib,
json, re) - no third-party packages, no network installs.

## Run it

    python3 run.py [port] [db_path]     # default: 8000, conduit.sqlite3

## Test it

    python3 -m unittest discover -s tests -t . -v

(equivalently `python3 tests/test_api.py`). Spins up the real HTTP server on an
OS-assigned free port with a throwaway temp sqlite file, fires real HTTP requests at it
with http.client, tears the server down after. 9 tests, exits 0.

## Layout

- conduit/db.py - sqlite schema + connection helper.
- conduit/auth.py - PBKDF2 password hashing + a signed (HMAC-SHA256) bearer token
  (Authorization: Token <token>), decodes back to a user id.
- conduit/slugs.py - kebab-case slug + de-dup (title, title-2, ...).
- conduit/errors.py - ValidationError(422) / Unauthorized(401) / Forbidden(403) /
  NotFound(404), all rendered as {"errors": {...}}.
- conduit/serializers.py - the exact JSON shapes from api-response-format.md
  (User/Profile/Article/Comment/Tags, including the "list endpoints omit body" rule).
- conduit/service/users.py, conduit/service/articles.py - business logic (pure
  functions over a sqlite connection), no HTTP concerns.
- conduit/http_app.py - routing table (regex per path) + BaseHTTPRequestHandler
  wiring: auth-header extraction, JSON in/out, error -> status-code mapping.
- run.py - standalone entry point.
- tests/test_api.py - end-to-end HTTP tests.

## Endpoint checklist vs specs/foreign-conduit/endpoints.md

| Endpoint | Status |
|---|---|
| POST /api/users/login | done |
| POST /api/users (register) | done |
| GET /api/user | done |
| PUT /api/user | done |
| GET /api/profiles/:username | done |
| POST /api/profiles/:username/follow | done |
| DELETE /api/profiles/:username/follow | done |
| GET /api/articles (tag/author/favorited/limit/offset) | done |
| GET /api/articles/feed (limit/offset) | done |
| GET /api/articles/:slug | done |
| POST /api/articles (tagList) | done |
| PUT /api/articles/:slug (slug regenerated on title change) | done |
| DELETE /api/articles/:slug | done |
| POST /api/articles/:slug/comments | done |
| GET /api/articles/:slug/comments | done |
| DELETE /api/articles/:slug/comments/:id | done |
| POST /api/articles/:slug/favorite | done |
| DELETE /api/articles/:slug/favorite | done |
| GET /api/tags | done |

All 19 endpoints in the spec are implemented and exercised by the tests. Response
formats match api-response-format.md (including the "no body in list views" rule
since 2024-08-16). Error format matches error-handling.md: 422 with
{"errors": {"field": ["msg"]}} for validation, 401 for missing/invalid auth, 403 for
valid-but-not-permitted (editing/deleting someone else's article or comment), 404 for
missing resources.

## Shortcuts / honest gaps

- Auth token is not a real JWT. It's HMAC-SHA256-signed base64url(json payload).hex(sig)
  - same contract (Authorization: Token <token>, opaque, server-verifiable, carries the
  user id), same threat model for this exercise, but not JWT-interoperable and has no
  expiry check (a decoded token is valid forever for the process lifetime). The server
  secret is generated once per process (os.urandom(32)) and not persisted, so restarting
  the server invalidates all previously-issued tokens - acceptable for a dev/test backend,
  not for production.
- Concurrency is coarse. ConduitHandler serializes every request through one global
  threading.Lock around DB access, to sidestep sqlite multi-connection/threading
  corner cases within the time budget. ThreadingHTTPServer still accepts connections
  concurrently, but request handling is effectively single-threaded. Fine for
  functional correctness and the test suite; would need a real connection-pool /
  WAL-mode strategy for throughput.
- No password/email format validation beyond "non-empty". No email regex, no
  password strength/length rule, no request-body-size limit. Only presence/uniqueness
  is checked, per the spec's "required fields" language.
- No pagination bounds-checking - limit/offset are parsed as ints with silent
  fallback to defaults on non-numeric input; no upper cap enforced.
- Tags are simple strings, no per-article tag ordering preserved - stored as
  a shared tags table + join table, returned alphabetically (GET /api/tags) or in
  alphabetical order per-article (tagList), not insertion order.
- No HTTPS, no CORS, no rate limiting, no logging middleware - a bare stdlib HTTP
  server is otherwise minimal by design (no dependency installs allowed).
- Not tested: malformed-JSON-body handling beyond a best-effort None fallback
  (falls through to a 422/"can't be blank" errors shape rather than a distinct
  400 Bad Request - the spec doesn't define a body-parse-error status, so 422 was reused).
- Everything else in the four spec files is implemented, not partial/missing.
