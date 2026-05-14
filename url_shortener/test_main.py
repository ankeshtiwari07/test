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

# ---------------------------------------------------------------------------
# TC-F-001  AC-1 — POST /shorten with valid https URL → 200 + short_code + short_url
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# TC-F-002  AC-1 — POST /shorten with valid http URL → 200
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# TC-F-003  AC-2 — GET /{short_code} for known code → 302 + correct Location
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# TC-F-004  AC-3 — GET /XXXXXX for unknown code → 404 + detail message
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# TC-F-005  AC-4 — POST /shorten with ftp:// URL → 422
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# TC-F-006  AC-5 — POST /shorten with bare non-URL string → 422
# ---------------------------------------------------------------------------
def test_TC_F_006_shorten_non_url_string_returns_422():
    """AC-5 / FR-6: a bare string with no scheme is rejected with 422."""
    response = client.post("/shorten", json={"url": "not-a-url-at-all"})

    assert response.status_code == 422, (
        f"Expected 422 for non-URL string, got {response.status_code}"
    )


# ---------------------------------------------------------------------------
# TC-F-007  AC-5 — POST /shorten with javascript: scheme → 422
# ---------------------------------------------------------------------------
def test_TC_F_007_shorten_javascript_scheme_returns_422():
    """AC-5 / FR-6: javascript: scheme is rejected with 422 (XSS vector)."""
    response = client.post("/shorten", json={"url": "javascript:alert(1)"})

    assert response.status_code == 422, (
        f"Expected 422 for javascript: URL, got {response.status_code}"
    )


# ---------------------------------------------------------------------------
# TC-F-008  AC-6 — GET /healthz → 200 + {status: ok}
# ---------------------------------------------------------------------------
def test_TC_F_008_healthz_returns_200_and_status_ok():
    """AC-6 / FR-7: GET /healthz returns 200 and exactly {status: ok}."""
    response = client.get("/healthz")

    assert response.status_code == 200, (
        f"Expected 200 from /healthz, got {response.status_code}"
    )
    assert response.json() == {"status": "ok"}, (
        f"Expected {{status: ok}}, got {response.json()}"
    )


# ---------------------------------------------------------------------------
# TC-F-009  AC-7 — Same URL twice → two distinct short codes (no dedup)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# TC-F-010  AC-1 — short_url contains the short_code as a path segment
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# TC-F-011  AC-2 — Multiple distinct URLs each redirect correctly
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# TC-R-001  /healthz must not be shadowed by /{short_code} wildcard route
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# TC-R-002  Counter increments monotonically — codes are always distinct
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# TC-R-003  Store isolation — code from a prior test is not present
# ---------------------------------------------------------------------------
def test_TC_R_003_store_is_empty_after_fixture_reset():
    """Regression: the autouse reset_store fixture must clear the store so
    a code created in a previous test cannot be resolved in this one."""
    response = client.get("/000001", follow_redirects=False)
    assert response.status_code == 404, (
        "Store was not properly reset between tests — "
        f"'000001' resolved when it should not have (got {response.status_code})"
    )


# ---------------------------------------------------------------------------
# TC-R-004  POST /shorten does NOT mutate store or counter on 422
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# TC-S-001  OWASP A03 — Injection: javascript: scheme blocked (XSS via redirect)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# TC-S-002  OWASP A03 — Injection: data: URI scheme blocked
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# TC-S-003  OWASP A05 — Security Misconfiguration: /healthz leaks no internals
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# TC-S-004  OWASP A01 — Broken Access Control: file:// scheme blocked (SSRF)
# ---------------------------------------------------------------------------
def test_TC_S_004_file_scheme_blocked_prevents_ssrf_local_file_read():
    """Security / OWASP A01 Broken Access Control / SSRF: file:// URLs must
    be rejected so the service cannot be used to probe local filesystem paths
    via a redirect to file:///etc/passwd."""
    response = client.post("/shorten", json={"url": "file:///etc/passwd"})

    assert response.status_code == 422, (
        f"file:// scheme must be blocked (422), got {response.status_code}"
    )


# ---------------------------------------------------------------------------
# TC-S-005  OWASP A01 — SSRF gap documented: internal metadata URL accepted
# ---------------------------------------------------------------------------
def test_TC_S_005_internal_metadata_url_accepted_documents_ssrf_gap():
    """Security / OWASP A01 SSRF (known gap): the service accepts
    http://169.254.169.254/latest/meta-data/ because scheme validation only
    checks http/https, not the destination host. This test documents the
    accepted risk (BRD §4 out-of-scope: no SSRF host-level protection)."""
    response = client.post(
        "/shorten",
        json={"url": "http://169.254.169.254/latest/meta-data/"},
    )
    # The service WILL return 200 — this is the documented behaviour.
    # The test asserts the current behaviour so a future change is visible.
    assert response.status_code == 200, (
        "Behaviour changed: internal metadata URL now rejected. "
        "Update SSRF gap documentation if intentional."
    )


# ===========================================================================
# EDGE / NEGATIVE CASES
# ===========================================================================

# ---------------------------------------------------------------------------
# TC-E-001  Empty string URL → 422
# ---------------------------------------------------------------------------
def test_TC_E_001_empty_string_url_returns_422():
    """Edge / empty: an empty string has no valid scheme and must be rejected."""
    response = client.post("/shorten", json={"url": ""})

    assert response.status_code == 422, (
        f"Expected 422 for empty URL string, got {response.status_code}"
    )


# ---------------------------------------------------------------------------
# TC-E-002  Null / missing url field → 422
# ---------------------------------------------------------------------------
def test_TC_E_002_missing_url_field_returns_422():
    """Edge / null: a request body with no 'url' key fails Pydantic validation → 422."""
    response = client.post("/shorten", json={})

    assert response.status_code == 422, (
        f"Expected 422 for missing 'url' field, got {response.status_code}"
    )


# ---------------------------------------------------------------------------
# TC-E-003  URL with max-length path (2 000 chars) → 200
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# TC-E-004  URL containing unicode characters → 200 + correct redirect
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# TC-E-005  Short code with special characters → 404 or 422, never 500
# ---------------------------------------------------------------------------
def test_TC_E_005_short_code_with_special_chars_returns_404_not_500():
    """Edge / negative: a GET request with special characters in the path
    must return 404 or 422 — the service must not crash on unusual input."""
    response = client.get("/!@#$%^", follow_redirects=False)

    assert response.status_code in (404, 422), (
        f"Expected 404 or 422 for special-char path, got {response.status_code}. "
        "A 500 would indicate an unhandled exception."
    )


# ---------------------------------------------------------------------------
# TC-E-006  Idempotency: 50 sequential calls → 50 unique codes
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# TC-E-007  POST /shorten with wrong Content-Type → 422
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# TC-E-008  GET /healthz is always 200 regardless of store state
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# TC-E-009  Partial-failure: invalid URL does not affect subsequent valid calls
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# TC-E-010  /healthz responds immediately with empty store (zero-dependency)
# ---------------------------------------------------------------------------
def test_TC_E_010_healthz_responds_with_empty_store():
    """Edge / timeout-resilience: /healthz must respond immediately with an
    empty store (zero storage dependency, FR-7)."""
    assert len(main._store) == 0, "Store should be empty at test start (fixture)"
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
