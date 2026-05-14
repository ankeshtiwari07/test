# Test Plan: url-shortener-demo — Minimal FastAPI URL Shortening Service

## Coverage matrix

| AC | Functional | Regression | Security | Edge / negative | UAT |
| --- | --- | --- | --- | --- | --- |
| AC-1 (POST valid URL → 200 + short_code + short_url) | TC-F-001, TC-F-002, TC-F-010 | TC-R-002 | — | TC-E-003, TC-E-004, TC-E-006 | UAT-1 |
| AC-2 (GET known code → 302 + Location) | TC-F-003, TC-F-011 | TC-R-001 | — | TC-E-004 | UAT-2 |
| AC-3 (GET unknown code → 404 + detail) | TC-F-004 | TC-R-003 | — | TC-E-005 | UAT-3 |
| AC-4 (ftp:// → 422) | TC-F-005 | TC-R-004 | TC-S-004 | TC-E-009 | UAT-4 |
| AC-5 (non-URL / bad scheme → 422) | TC-F-006, TC-F-007 | TC-R-004 | TC-S-001, TC-S-002 | TC-E-001, TC-E-002, TC-E-007 | UAT-4 |
| AC-6 (GET /healthz → 200 {status:ok}) | TC-F-008 | TC-R-001 | TC-S-003 | TC-E-008, TC-E-010 | UAT-5 |
| AC-7 (same URL twice → distinct codes) | TC-F-009 | TC-R-002 | — | TC-E-006 | UAT-1 |
| AC-8 (CI pipeline green) | — | TC-R-001 – TC-R-004 | — | — | UAT-5 |
| AC-9 (Docker /healthz within 5 s) | TC-F-008 | — | TC-S-003 | TC-E-010 | UAT-5 |

---

## Functional tests

### TC-F-001
- **Target file:** `url_shortener/test_main.py` → `url_shortener/main.py`
- **AC covered:** AC-1 (FR-1, FR-3)
- **Given** a running service with an empty store
- **When** a client sends `POST /shorten` with body `{"url": "https://www.example.com"}`
- **Then** the response status is **200**, the body contains `short_code` matching `[A-Za-z0-9]{6}`, and `short_url` ends with `/<short_code>`
- **Expected result:** 200 OK; `short_code` is exactly 6 alphanumeric characters; `short_url` is a string ending with `/<short_code>`

### TC-F-002
- **Target file:** `url_shortener/test_main.py` → `url_shortener/main.py`
- **AC covered:** AC-1 (FR-6 — http allowed)
- **Given** a running service
- **When** a client sends `POST /shorten` with body `{"url": "http://example.org/path?q=1"}`
- **Then** the response status is **200** and `short_code` is 6 alphanumeric characters
- **Expected result:** 200 OK; plain `http://` URLs are not rejected

### TC-F-003
- **Target file:** `url_shortener/test_main.py` → `url_shortener/main.py`
- **AC covered:** AC-2 (FR-4)
- **Given** a short code previously returned by `POST /shorten` for `https://www.example.com`
- **When** a client sends `GET /{short_code}` with redirect-following disabled
- **Then** the response status is **302** and the `Location` header equals `https://www.example.com`
- **Expected result:** 302 Found; `Location: https://www.example.com`

### TC-F-004
- **Target file:** `url_shortener/test_main.py` → `url_shortener/main.py`
- **AC covered:** AC-3 (FR-5)
- **Given** a running service with an empty store
- **When** a client sends `GET /XXXXXX`
- **Then** the response status is **404** and the JSON body is `{"detail": "Short code not found"}`
- **Expected result:** 404 Not Found; `detail` field equals `"Short code not found"`

### TC-F-005
- **Target file:** `url_shortener/test_main.py` → `url_shortener/main.py`
- **AC covered:** AC-4 (FR-6)
- **Given** a running service
- **When** a client sends `POST /shorten` with body `{"url": "ftp://files.example.com/data"}`
- **Then** the response status is **422** and the detail mentions scheme restriction
- **Expected result:** 422 Unprocessable Entity; detail contains "scheme" or "http"

### TC-F-006
- **Target file:** `url_shortener/test_main.py` → `url_shortener/main.py`
- **AC covered:** AC-5 (FR-6)
- **Given** a running service
- **When** a client sends `POST /shorten` with body `{"url": "not-a-url-at-all"}`
- **Then** the response status is **422**
- **Expected result:** 422 Unprocessable Entity

### TC-F-007
- **Target file:** `url_shortener/test_main.py` → `url_shortener/main.py`
- **AC covered:** AC-5 (FR-6)
- **Given** a running service
- **When** a client sends `POST /shorten` with body `{"url": "javascript:alert(1)"}`
- **Then** the response status is **422**
- **Expected result:** 422 Unprocessable Entity

### TC-F-008
- **Target file:** `url_shortener/test_main.py` → `url_shortener/main.py`
- **AC covered:** AC-6 (FR-7)
- **Given** a running service
- **When** a client sends `GET /healthz`
- **Then** the response status is **200** and the body is exactly `{"status": "ok"}`
- **Expected result:** 200 OK; body `{"status": "ok"}`

### TC-F-009
- **Target file:** `url_shortener/test_main.py` → `url_shortener/main.py`
- **AC covered:** AC-7 (FR-2, FR-8)
- **Given** a running service
- **When** `POST /shorten` is called twice with the same URL `https://www.example.com`
- **Then** the two responses contain **different** values for `short_code`
- **Expected result:** `resp1.short_code != resp2.short_code`

### TC-F-010
- **Target file:** `url_shortener/test_main.py` → `url_shortener/main.py`
- **AC covered:** AC-1 (FR-1)
- **Given** a running service
- **When** `POST /shorten` is called with a valid URL
- **Then** `short_url` ends with `/<short_code>` (BASE_URL prefix + path segment)
- **Expected result:** `short_url` ends with `/<short_code>`

### TC-F-011
- **Target file:** `url_shortener/test_main.py` → `url_shortener/main.py`
- **AC covered:** AC-2 (FR-4)
- **Given** three distinct URLs shortened in sequence
- **When** each resulting short code is used in `GET /{short_code}`
- **Then** each redirects to its own original URL with status 302
- **Expected result:** 302 for each; `Location` matches the original URL for that code

---

## Regression tests

### TC-R-001
- **Files possibly affected:** `url_shortener/main.py` (route registration order)
- **Scenario:** `GET /healthz` must not be captured by the `GET /{short_code}` wildcard route
- **Expected behaviour:** `/healthz` always returns 200 `{"status": "ok"}` regardless of how many other routes are registered; the wildcard must not shadow it

### TC-R-002
- **Files possibly affected:** `url_shortener/main.py` (`_counter`, `_to_base62`)
- **Scenario:** Ten sequential `POST /shorten` calls produce ten distinct short codes
- **Expected behaviour:** The monotonic counter increments on every successful call; no two codes are equal within a session

### TC-R-003
- **Files possibly affected:** `url_shortener/test_main.py` (fixture), `url_shortener/main.py` (`_store`)
- **Scenario:** The `reset_store` autouse fixture clears `_store` and resets `_counter` to 0 before each test
- **Expected behaviour:** A code that would have been `000001` in a prior test is not resolvable in the next test (404)

### TC-R-004
- **Files possibly affected:** `url_shortener/main.py` (`shorten_url` handler)
- **Scenario:** A `POST /shorten` that returns 422 (invalid scheme) must not mutate `_store` or `_counter`
- **Expected behaviour:** `len(_store)` and `_counter` are identical before and after the rejected call

---

## Security tests

### TC-S-001
- **OWASP category:** A03 — Injection
- **Scenario:** `POST /shorten` with `{"url": "javascript:alert(document.cookie)"}` — an attacker attempts to store a `javascript:` URL so that `GET /{short_code}` returns a `Location: javascript:…` header, executing JS in the victim's browser
- **Mitigation under test:** Scheme allowlist (`http`/`https` only) in `shorten_url`; must return 422 before the URL is stored

### TC-S-002
- **OWASP category:** A03 — Injection
- **Scenario:** `POST /shorten` with a `data:text/html,<script>…</script>` URI — attacker attempts to inject HTML/JS content via a data URI redirect
- **Mitigation under test:** Scheme allowlist rejects `data:` scheme; must return 422

### TC-S-003
- **OWASP category:** A05 — Security Misconfiguration
- **Scenario:** `GET /healthz` response body is inspected for internal state leakage (store size, counter value, stack traces, version strings)
- **Mitigation under test:** Health handler returns only `{"status": "ok"}`; response body keys must be exactly `{"status"}`

### TC-S-004
- **OWASP category:** A01 — Broken Access Control (SSRF)
- **Scenario:** `POST /shorten` with `{"url": "file:///etc/passwd"}` — attacker attempts to store a `file://` URL so that a redirect causes the client (or a server-side follower) to read local files
- **Mitigation under test:** Scheme allowlist rejects `file://`; must return 422

### TC-S-005
- **OWASP category:** A01 — Broken Access Control (SSRF — known gap)
- **Scenario:** `POST /shorten` with `{"url": "http://169.254.169.254/latest/meta-data/"}` — documents that the service does NOT block SSRF to internal HTTP hosts because scheme validation only checks the scheme, not the destination
- **Mitigation under test:** None (out of scope per BRD §4); test asserts current behaviour (200) so any future change is visible

---

## Edge / negative cases

### TC-E-001
- **Input class:** Empty string
- **Scenario:** `POST /shorten` with `{"url": ""}` — empty string has no scheme
- **Expected behaviour:** 422 Unprocessable Entity; store and counter unchanged

### TC-E-002
- **Input class:** Null / missing field
- **Scenario:** `POST /shorten` with `{}` — `url` field absent; Pydantic validation fails
- **Expected behaviour:** 422 Unprocessable Entity (Pydantic required-field error)

### TC-E-003
- **Input class:** Max-length
- **Scenario:** `POST /shorten` with a URL whose path is 1 980 characters long (total ~2 000 chars)
- **Expected behaviour:** 200 OK; no length cap is defined in the BRD; service stores and returns the full URL

### TC-E-004
- **Input class:** Unicode
- **Scenario:** `POST /shorten` with a URL containing Japanese characters in the path; then `GET /{short_code}`
- **Expected behaviour:** 200 on shorten; 302 on redirect with `Location` equal to the original unicode URL verbatim

### TC-E-005
- **Input class:** Special characters in path
- **Scenario:** `GET /!@#$%^` — path contains characters outside the base-62 alphabet
- **Expected behaviour:** 404 or 422; must not return 500 (no unhandled exception)

### TC-E-006
- **Input class:** Idempotency / volume
- **Scenario:** 50 sequential `POST /shorten` calls with distinct URLs
- **Expected behaviour:** All 50 return 200; all 50 short codes are distinct and match `[A-Za-z0-9]{6}`

### TC-E-007
- **Input class:** Wrong Content-Type
- **Scenario:** `POST /shorten` with `Content-Type: text/plain` and a non-JSON body
- **Expected behaviour:** 422 Unprocessable Entity (FastAPI cannot parse the body as JSON)

### TC-E-008
- **Input class:** Store state independence
- **Scenario:** `GET /healthz` after 20 URLs have been shortened (store is populated)
- **Expected behaviour:** 200 `{"status": "ok"}` — health check has no storage dependency (FR-7)

### TC-E-009
- **Input class:** Partial failure
- **Scenario:** A 422-rejected call is immediately followed by a valid `POST /shorten`
- **Expected behaviour:** The valid call returns 200 with a correct short code; the service is not left in a broken state

### TC-E-010
- **Input class:** Timeout resilience / zero-dependency
- **Scenario:** `GET /healthz` when the store is empty (process just started)
- **Expected behaviour:** 200 `{"status": "ok"}` immediately; no dependency on store contents

---

## UAT plan

### UAT-1
- **Stakeholder role:** End user (any HTTP client / demo operator)
- **Scenario:** The user submits a long URL to the shortener and receives a short link. They verify the short link looks correct and is different each time they submit the same URL.
- **Success criterion:** `POST /shorten` with a valid `https://` URL returns a 6-character code and a `short_url` that ends with that code. Submitting the same URL a second time produces a different code.
- **Sign-off needed:** No

### UAT-2
- **Stakeholder role:** End user (any HTTP client / demo operator)
- **Scenario:** The user copies the `short_url` from the shorten response, pastes it into a browser (or curl), and is redirected to the original long URL without any error.
- **Success criterion:** `GET /{short_code}` returns HTTP 302 and the browser (or curl with `-L`) lands on the original URL.
- **Sign-off needed:** No

### UAT-3
- **Stakeholder role:** End user (any HTTP client / demo operator)
- **Scenario:** The user tries to visit a short link that was never created (e.g. typed randomly). They receive a clear "not found" message rather than a server error.
- **Success criterion:** `GET /XXXXXX` returns HTTP 404 with a JSON body containing `"detail": "Short code not found"`.
- **Sign-off needed:** No

### UAT-4
- **Stakeholder role:** End user / product owner (ankeshtiwari07)
- **Scenario:** The user accidentally submits an invalid URL (e.g. `ftp://…` or a plain word with no `http://` prefix). The service rejects it with a clear error rather than creating a broken short link.
- **Success criterion:** `POST /shorten` with an invalid URL returns HTTP 422. No short code is created. The user can correct their input and resubmit.
- **Sign-off needed:** Yes

### UAT-5
- **Stakeholder role:** Product owner / developer / reviewer (ankeshtiwari07, repository maintainers)
- **Scenario:** The team pushes code to the `aisdlc-url-shortener-v2` branch. GitHub Actions automatically runs all tests. The workflow completes successfully in under 3 minutes, and the PR shows a green check mark. The Docker container starts and responds to `GET /healthz` within 5 seconds.
- **Success criterion:** GitHub Actions workflow `url-shortener-ci.yml` exits with status 0; all pytest functions pass; `GET /healthz` returns `{"status": "ok"}` within 5 seconds of `docker run`.
- **Sign-off needed:** Yes

---

## Generated test files

### `url_shortener/test_main.py`
**Framework:** pytest + FastAPI TestClient (httpx)

```python
"""
url_shortener/test_main.py
==========================
Comprehensive pytest test suite for the URL Shortener Demo service.

Covers:
  - AC-1  Successful shorten (FR-1, FR-3)
  - AC-2  Redirect hit 302 (FR-4)
  - AC-3  Redirect miss 404 (FR-5)
  - AC-4  Invalid scheme ftp → 422 (FR-6)
  - AC-5  Non-URL string → 422 (FR-6)
  - AC-6  Health check (FR-7)
  - AC-7  Short-code uniqueness / no dedup (FR-2, FR-8)
  Plus regression, security, and edge-case tests.

Framework : pytest + FastAPI TestClient (httpx)
Run       : PYTHONPATH=url_shortener pytest url_shortener/test_main.py -v --tb=short
"""

import re
import pytest
from fastapi.testclient import TestClient

import main  # resolved via PYTHONPATH=url_shortener

# ---------------------------------------------------------------------------
# Shared client + isolation fixture
# ---------------------------------------------------------------------------

client = TestClient(main.app, raise_server_exceptions=False)

BASE62_RE = re.compile(r"^[A-Za-z0-9]{6}$")


@pytest.fixture(autouse=True)
def reset_store():
    """Reset in-memory store and counter before AND after every test.

    This guarantees full test isolation without a conftest.py.
    Monkeypatching the module-level globals directly is intentional:
    we are resetting *state*, not patching the *implementation*.
    """
    main._store.clear()
    main._counter = 0
    yield
    main._store.clear()
    main._counter = 0


# ===========================================================================
# FUNCTIONAL TESTS
# ===========================================================================

def test_TC_F_001_shorten_valid_https_url_returns_200_with_short_code_and_short_url():
    """AC-1 / FR-1 / FR-3: POST /shorten with https URL returns 200,
    a 6-char alphanumeric short_code, and a short_url ending with that code."""
    response = client.post("/shorten", json={"url": "https://www.example.com"})

    assert response.status_code == 200, (
        f"Expected 200 for valid https URL, got {response.status_code}"
    )
    data = response.json()
    assert "short_code" in data, "Response body must contain 'short_code'"
    assert "short_url" in data, "Response body must contain 'short_url'"

    short_code = data["short_code"]
    assert BASE62_RE.fullmatch(short_code), (
        f"short_code '{short_code}' must match [A-Za-z0-9]{{6}}"
    )
    assert data["short_url"].endswith(f"/{short_code}"), (
        f"short_url must end with '/{short_code}', got: {data['short_url']}"
    )


def test_TC_F_002_shorten_valid_http_url_returns_200():
    """AC-1 / FR-6: plain http:// URLs are permitted and return 200."""
    response = client.post("/shorten", json={"url": "http://example.org/path?q=1"})

    assert response.status_code == 200, (
        f"Expected 200 for valid http URL, got {response.status_code}"
    )
    data = response.json()
    assert BASE62_RE.fullmatch(data["short_code"]), (
        "short_code must be 6 alphanumeric characters"
    )


def test_TC_F_003_redirect_known_code_returns_302_with_location_header():
    """AC-2 / FR-4: GET /{short_code} for a known code returns 302 and
    the Location header equals the original URL."""
    original_url = "https://www.example.com"
    shorten_resp = client.post("/shorten", json={"url": original_url})
    assert shorten_resp.status_code == 200
    short_code = shorten_resp.json()["short_code"]

    redirect_resp = client.get(f"/{short_code}", follow_redirects=False)

    assert redirect_resp.status_code == 302, (
        f"Expected 302 redirect, got {redirect_resp.status_code}"
    )
    assert redirect_resp.headers.get("location") == original_url, (
        f"Location header must equal original URL '{original_url}', "
        f"got '{redirect_resp.headers.get('location')}'"
    )


def test_TC_F_004_redirect_unknown_code_returns_404_with_detail():
    """AC-3 / FR-5: GET with a non-existent short code returns 404 and
    the JSON body contains detail='Short code not found'."""
    response = client.get("/XXXXXX", follow_redirects=False)

    assert response.status_code == 404, (
        f"Expected 404 for unknown short code, got {response.status_code}"
    )
    data = response.json()
    assert data.get("detail") == "Short code not found", (
        f"Expected detail='Short code not found', got: {data.get('detail')}"
    )


def test_TC_F_005_shorten_ftp_url_returns_422():
    """AC-4 / FR-6: ftp:// scheme is rejected with HTTP 422."""
    response = client.post(
        "/shorten", json={"url": "ftp://files.example.com/data"}
    )

    assert response.status_code == 422, (
        f"Expected 422 for ftp:// URL, got {response.status_code}"
    )
    detail = str(response.json().get("detail", "")).lower()
    assert "scheme" in detail or "http" in detail, (
        f"Error detail should mention scheme restriction, got: '{detail}'"
    )


def test_TC_F_006_shorten_non_url_string_returns_422():
    """AC-5 / FR-6: a bare string with no scheme is rejected with 422."""
    response = client.post("/shorten", json={"url": "not-a-url-at-all"})

    assert response.status_code == 422, (
        f"Expected 422 for non-URL string, got {response.status_code}"
    )


def test_TC_F_007_shorten_javascript_scheme_returns_422():
    """AC-5 / FR-6: javascript: scheme is rejected with 422 (XSS vector)."""
    response = client.post("/shorten", json={"url": "javascript:alert(1)"})

    assert response.status_code == 422, (
        f"Expected 422 for javascript: URL, got {response.status_code}"
    )


def test_TC_F_008_healthz_returns_200_and_status_ok():
    """AC-6 / FR-7: GET /healthz returns 200 and exactly {status: ok}."""
    response = client.get("/healthz")

    assert response.status_code == 200, (
        f"Expected 200 from /healthz, got {response.status_code}"
    )
    assert response.json() == {"status": "ok"}, (
        f"Expected {{status: ok}}, got {response.json()}"
    )


def test_TC_F_009_same_url_twice_produces_different_short_codes():
    """AC-7 / FR-2 / FR-8: submitting the same URL twice yields two distinct
    short codes — the service does NOT deduplicate."""
    url = "https://www.example.com"
    resp1 = client.post("/shorten", json={"url": url})
    resp2 = client.post("/shorten", json={"url": url})

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    code1 = resp1.json()["short_code"]
    code2 = resp2.json()["short_code"]
    assert code1 != code2, (
        f"Expected distinct short codes for duplicate submissions, "
        f"but both returned '{code1}'"
    )


def test_TC_F_010_short_url_contains_short_code_as_path_segment():
    """AC-1 / FR-1: short_url in the response must contain the short_code
    as its final path segment (BASE_URL/<short_code>)."""
    response = client.post("/shorten", json={"url": "https://example.com"})

    assert response.status_code == 200
    data = response.json()
    short_code = data["short_code"]
    short_url = data["short_url"]
    assert short_url.endswith(f"/{short_code}"), (
        f"short_url '{short_url}' must end with '/{short_code}'"
    )


def test_TC_F_011_multiple_urls_each_redirect_to_correct_location():
    """AC-2 / FR-4: multiple distinct URLs can be shortened and each
    GET /{short_code} redirects to its own original URL."""
    urls = [
        "https://alpha.example.com",
        "https://beta.example.com",
        "http://gamma.example.com/path?q=1&r=2",
    ]
    code_to_url = {}
    for url in urls:
        resp = client.post("/shorten", json={"url": url})
        assert resp.status_code == 200, f"Shorten failed for {url}"
        code_to_url[resp.json()["short_code"]] = url

    for code, expected_url in code_to_url.items():
        redir = client.get(f"/{code}", follow_redirects=False)
        assert redir.status_code == 302, (
            f"Expected 302 for code '{code}', got {redir.status_code}"
        )
        assert redir.headers["location"] == expected_url, (
            f"Location for code '{code}' should be '{expected_url}', "
            f"got '{redir.headers.get('location')}'"
        )


# ===========================================================================
# REGRESSION TESTS
# ===========================================================================

def test_TC_R_001_healthz_not_shadowed_by_short_code_wildcard():
    """Regression: /healthz must resolve to the health handler, not the
    redirect handler, regardless of route registration order in main.py."""
    response = client.get("/healthz")

    assert response.status_code == 200, (
        "GET /healthz was captured by the /{short_code} wildcard route "
        f"(returned {response.status_code} instead of 200)"
    )
    assert response.json() == {"status": "ok"}, (
        f"GET /healthz returned unexpected body: {response.json()}"
    )


def test_TC_R_002_counter_increments_monotonically_across_ten_calls():
    """Regression / FR-2: ten sequential POST /shorten calls must produce
    ten distinct short codes (counter must never repeat within a session)."""
    codes = set()
    for i in range(10):
        resp = client.post(
            "/shorten", json={"url": f"https://example.com/page{i}"}
        )
        assert resp.status_code == 200, f"Call {i} failed: {resp.status_code}"
        code = resp.json()["short_code"]
        assert code not in codes, (
            f"Duplicate short_code '{code}' produced on call {i}"
        )
        codes.add(code)
    assert len(codes) == 10


def test_TC_R_003_store_is_empty_after_fixture_reset():
    """Regression: the autouse reset_store fixture must clear the store so
    a code created in a previous test cannot be resolved in this one."""
    response = client.get("/000001", follow_redirects=False)
    assert response.status_code == 404, (
        "Store was not properly reset between tests — "
        f"'000001' resolved when it should not have (got {response.status_code})"
    )


def test_TC_R_004_invalid_url_does_not_mutate_store_or_counter():
    """Regression / FR-6: a rejected POST /shorten (422) must not increment
    the counter or add any entry to the store."""
    store_size_before = len(main._store)
    counter_before = main._counter

    client.post("/shorten", json={"url": "ftp://bad.example.com"})

    assert main._counter == counter_before, (
        "Counter was incremented despite a 422 rejection"
    )
    assert len(main._store) == store_size_before, (
        "Store was mutated despite a 422 rejection"
    )


# ===========================================================================
# SECURITY TESTS
# ===========================================================================

def test_TC_S_001_javascript_scheme_blocked_prevents_xss_via_redirect():
    """Security / OWASP A03 Injection: a javascript: URL must be rejected
    at POST /shorten so it can never be stored and served as a redirect
    Location header (which would execute JS in the browser)."""
    response = client.post(
        "/shorten", json={"url": "javascript:alert(document.cookie)"}
    )

    assert response.status_code == 422, (
        f"javascript: scheme must be blocked (422), got {response.status_code}. "
        "Storing this URL would allow XSS via the 302 Location header."
    )


def test_TC_S_002_data_uri_scheme_blocked():
    """Security / OWASP A03 Injection: data: URIs must be rejected at
    POST /shorten to prevent content injection via redirect."""
    response = client.post(
        "/shorten",
        json={"url": "data:text/html,<script>alert(1)</script>"},
    )

    assert response.status_code == 422, (
        f"data: URI scheme must be blocked (422), got {response.status_code}"
    )


def test_TC_S_003_healthz_response_contains_no_internal_details():
    """Security / OWASP A05 Security Misconfiguration: GET /healthz must
    return only {status: ok} and must not expose stack traces, store size,
    counter values, or any other internal state."""
    response = client.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"status"}, (
        f"GET /healthz must expose only 'status', got keys: {set(body.keys())}"
    )
    assert body["status"] == "ok"


def test_TC_S_004_file_scheme_blocked_prevents_ssrf_local_file_read():
    """Security / OWASP A01 Broken Access Control / SSRF: file:// URLs must
    be rejected so the service cannot be used to probe local filesystem paths
    via a redirect to file:///etc/passwd."""
    response = client.post("/shorten", json={"url": "file:///etc/passwd"})

    assert response.status_code == 422, (
        f"file:// scheme must be blocked (422), got {response.status_code}"
    )


def test_TC_S_005_internal_metadata_url_accepted_documents_ssrf_gap():
    """Security / OWASP A01 SSRF (known gap): the service accepts
    http://169.254.169.254/latest/meta-data/ because scheme validation only
    checks http/https, not the destination host. This test documents the
    accepted risk (BRD §4 out-of-scope: no SSRF host-level protection)."""
    response = client.post(
        "/shorten",
        json={"url": "http://169.254.169.254/latest/meta-data/"},
    )
    assert response.status_code == 200, (
        "Behaviour changed: internal metadata URL now rejected. "
        "Update SSRF gap documentation if intentional."
    )


# ===========================================================================
# EDGE / NEGATIVE CASES
# ===========================================================================

def test_TC_E_001_empty_string_url_returns_422():
    """Edge / empty: an empty string has no valid scheme and must be rejected."""
    response = client.post("/shorten", json={"url": ""})

    assert response.status_code == 422, (
        f"Expected 422 for empty URL string, got {response.status_code}"
    )


def test_TC_E_002_missing_url_field_returns_422():
    """Edge / null: a request body with no 'url' key fails Pydantic validation → 422."""
    response = client.post("/shorten", json={})

    assert response.status_code == 422, (
        f"Expected 422 for missing 'url' field, got {response.status_code}"
    )


def test_TC_E_003_max_length_url_is_accepted():
    """Edge / max-length: a URL with a very long path (2 000 chars) must be
    accepted — there is no length cap in the BRD."""
    long_path = "a" * 1980
    long_url = f"https://example.com/{long_path}"
    response = client.post("/shorten", json={"url": long_url})

    assert response.status_code == 200, (
        f"Expected 200 for max-length URL, got {response.status_code}"
    )
    assert BASE62_RE.fullmatch(response.json()["short_code"])


def test_TC_E_004_unicode_url_is_accepted_and_redirects_correctly():
    """Edge / unicode: URLs with unicode path segments must be accepted and
    the service stores and returns them verbatim on redirect."""
    unicode_url = "https://example.com/\u65e5\u672c\u8a9e/\u30d1\u30b9"
    response = client.post("/shorten", json={"url": unicode_url})

    assert response.status_code == 200, (
        f"Expected 200 for unicode URL, got {response.status_code}"
    )
    short_code = response.json()["short_code"]
    redir = client.get(f"/{short_code}", follow_redirects=False)
    assert redir.status_code == 302
    assert redir.headers["location"] == unicode_url, (
        f"Unicode URL not preserved in Location header: {redir.headers.get('location')}"
    )


def test_TC_E_005_short_code_with_special_chars_returns_404_not_500():
    """Edge / negative: a GET request with special characters in the path
    must return 404 or 422 — the service must not crash on unusual input."""
    response = client.get("/!@#$%^", follow_redirects=False)

    assert response.status_code in (404, 422), (
        f"Expected 404 or 422 for special-char path, got {response.status_code}. "
        "A 500 would indicate an unhandled exception."
    )


def test_TC_E_006_fifty_sequential_calls_produce_fifty_unique_codes():
    """Edge / idempotency: 50 sequential POST /shorten calls must each
    produce a unique, valid 6-char base-62 short code (FR-2, FR-3)."""
    codes = []
    for i in range(50):
        resp = client.post(
            "/shorten", json={"url": f"https://example.com/item/{i}"}
        )
        assert resp.status_code == 200, f"Call {i} returned {resp.status_code}"
        code = resp.json()["short_code"]
        assert BASE62_RE.fullmatch(code), (
            f"Code '{code}' on call {i} is not 6 alphanumeric chars"
        )
        codes.append(code)

    assert len(set(codes)) == 50, (
        f"Expected 50 unique codes, got {len(set(codes))} unique out of 50"
    )


def test_TC_E_007_non_json_body_returns_422():
    """Edge / negative: sending a plain-text body instead of JSON must
    return 422 (FastAPI/Pydantic rejects unparseable request bodies)."""
    response = client.post(
        "/shorten",
        content=b"url=https://example.com",
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 422, (
        f"Expected 422 for non-JSON body, got {response.status_code}"
    )


def test_TC_E_008_healthz_returns_200_when_store_is_populated():
    """Edge / FR-7: /healthz must return 200 even when the store contains
    many entries — it has no dependency on storage state."""
    for i in range(20):
        client.post("/shorten", json={"url": f"https://example.com/p{i}"})

    response = client.get("/healthz")

    assert response.status_code == 200, (
        f"GET /healthz returned {response.status_code} with a populated store"
    )
    assert response.json() == {"status": "ok"}


def test_TC_E_009_invalid_url_rejection_does_not_break_subsequent_valid_calls():
    """Edge / partial-failure: after a 422 rejection the service must continue
    to accept and process valid URLs correctly."""
    bad_resp = client.post("/shorten", json={"url": "ftp://bad.example.com"})
    assert bad_resp.status_code == 422

    good_resp = client.post("/shorten", json={"url": "https://good.example.com"})
    assert good_resp.status_code == 200, (
        f"Service failed after a prior 422 rejection: {good_resp.status_code}"
    )
    assert BASE62_RE.fullmatch(good_resp.json()["short_code"])


def test_TC_E_010_healthz_responds_with_empty_store():
    """Edge / timeout-resilience: /healthz must respond immediately with an
    empty store (zero storage dependency, FR-7)."""
    assert len(main._store) == 0, "Store should be empty at test start (fixture)"
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

---

## Open questions / can't test

1. **AC-8 — CI pipeline green (automated):** The GitHub Actions workflow execution itself cannot be verified by the pytest suite. The test plan covers all individual behaviours that the CI runs, but the end-to-end "workflow exits 0 in ≤ 3 minutes" criterion requires a live GitHub Actions run. Verified only by observing the PR check status on `aisdlc-url-shortener-v2`.

2. **AC-9 — Docker container health within 5 s:** Container start-up time and the Docker `HEALTHCHECK` cannot be exercised by pytest. This requires a live `docker build` + `docker run` + `curl` smoke test. Documented in the UAT plan (UAT-5) and in the build artifact's "Docker smoke test" section.

3. **NFR-1 — ≤ 100 ms p99 at 50 concurrent requests:** Load/performance testing is out of scope for this pytest suite. The in-memory dict design makes this a near-certainty, but formal p99 measurement requires a tool such as `locust` or `k6`. Flagged as a known gap; acceptable for demo scope.

4. **TC-S-005 — SSRF to internal HTTP hosts:** The service does not block `http://169.254.169.254/…` because the BRD explicitly places SSRF host-level protection out of scope. The test documents the gap rather than asserting a block. Any future host-allowlist feature would need a new test.

5. **Thread-safety of `_counter` and `_store`:** The BRD (§7) explicitly accepts single-worker mode only. Concurrent mutation of the globals under `--workers > 1` is untested and out of scope.

---

```json
{
  "title": "url-shortener-demo — Minimal FastAPI URL Shortening Service",
  "ac_coverage": [
    {"ac": "AC-1", "tests": ["TC-F-001", "TC-F-002", "TC-F-010", "TC-R-002", "TC-E-003", "TC-E-004", "TC-E-006", "UAT-1"]},
    {"ac": "AC-2", "tests": ["TC-F-003", "TC-F-011", "TC-R-001", "TC-E-004", "UAT-2"]},
    {"ac": "AC-3", "tests": ["TC-F-004", "TC-R-003", "TC-E-005", "UAT-3"]},
    {"ac": "AC-4", "tests": ["TC-F-005", "TC-R-004", "TC-S-004", "TC-E-009", "UAT-4"]},
    {"ac": "AC-5", "tests": ["TC-F-006", "TC-F-007", "TC-R-004", "TC-S-001", "TC-S-002", "TC-E-001", "TC-E-002", "TC-E-007", "UAT-4"]},
    {"ac": "AC-6", "tests": ["TC-F-008", "TC-R-001", "TC-S-003", "TC-E-008", "TC-E-010", "UAT-5"]},
    {"ac": "AC-7", "tests": ["TC-F-009", "TC-R-002", "TC-E-006", "UAT-1"]},
    {"ac": "AC-8", "tests": ["TC-R-001", "TC-R-002", "TC-R-003", "TC-R-004", "UAT-5"]},
    {"ac": "AC-9", "tests": ["TC-F-008", "TC-S-003", "TC-E-010", "UAT-5"]}
  ],
  "functional_count": 11,
  "regression_count": 4,
  "security_count": 5,
  "edge_count": 10,
  "uat_count": 5,
  "test_files": ["url_shortener/test_main.py"],
  "uat_signoff_required_for": ["product-owner", "developer-reviewer"]
}
```
