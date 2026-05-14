"""
url_shortener/test_main.py
pytest test suite for the URL shortener service.

Covers AC-1 through AC-7 (BRD §8) and satisfies NFR-6 (>= 5 test functions).
Uses FastAPI TestClient (synchronous httpx wrapper) - no live server needed.

Store and counter are reset before each test via the reset_store fixture
to guarantee test isolation (HLD §8 open question resolved here).
"""

import re
import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(autouse=True)
def reset_store():
    """Reset in-memory store and counter before every test for isolation."""
    main._store.clear()
    main._counter = 0
    yield
    main._store.clear()
    main._counter = 0


client = TestClient(main.app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# AC-1: Successful shorten (FR-1, FR-3)
# ---------------------------------------------------------------------------
def test_shorten_success_returns_200_with_valid_short_code():
    """AC-1: POST /shorten with a valid https URL returns 200, short_code,
    and short_url ending with the short_code."""
    response = client.post("/shorten", json={"url": "https://www.example.com"})
    assert response.status_code == 200
    data = response.json()
    assert "short_code" in data
    assert "short_url" in data
    short_code = data["short_code"]
    # FR-3: exactly 6 alphanumeric characters
    assert re.fullmatch(r"[A-Za-z0-9]{6}", short_code), (
        f"short_code '{short_code}' does not match [A-Za-z0-9]{{6}}"
    )
    # short_url must end with /<short_code>
    assert data["short_url"].endswith(f"/{short_code}")


def test_shorten_http_url_is_accepted():
    """AC-1 (http variant): plain http:// URLs are valid (FR-6 allows http)."""
    response = client.post("/shorten", json={"url": "http://example.org/path"})
    assert response.status_code == 200
    data = response.json()
    assert re.fullmatch(r"[A-Za-z0-9]{6}", data["short_code"])


# ---------------------------------------------------------------------------
# AC-2: Redirect hit (FR-4)
# ---------------------------------------------------------------------------
def test_redirect_returns_302_with_correct_location():
    """AC-2: GET /{short_code} for a known code returns 302 and correct Location."""
    shorten_resp = client.post(
        "/shorten", json={"url": "https://www.example.com"}
    )
    assert shorten_resp.status_code == 200
    short_code = shorten_resp.json()["short_code"]

    redirect_resp = client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_resp.status_code == 302
    assert redirect_resp.headers["location"] == "https://www.example.com"


# ---------------------------------------------------------------------------
# AC-3: Redirect miss / 404 (FR-5)
# ---------------------------------------------------------------------------
def test_redirect_unknown_code_returns_404():
    """AC-3: GET /XXXXXX for a non-existent code returns 404 with detail."""
    response = client.get("/XXXXXX", follow_redirects=False)
    assert response.status_code == 404
    data = response.json()
    assert data.get("detail") == "Short code not found"


# ---------------------------------------------------------------------------
# AC-4: Invalid scheme rejection - ftp (FR-6)
# ---------------------------------------------------------------------------
def test_shorten_ftp_url_returns_422():
    """AC-4: POST /shorten with ftp:// URL returns 422."""
    response = client.post(
        "/shorten", json={"url": "ftp://files.example.com/data"}
    )
    assert response.status_code == 422
    body = response.json()
    detail_text = str(body.get("detail", "")).lower()
    assert "scheme" in detail_text or "http" in detail_text


# ---------------------------------------------------------------------------
# AC-5: Non-URL string rejection (FR-6)
# ---------------------------------------------------------------------------
def test_shorten_non_url_string_returns_422():
    """AC-5: POST /shorten with a bare non-URL string returns 422."""
    response = client.post("/shorten", json={"url": "not-a-url-at-all"})
    assert response.status_code == 422


def test_shorten_javascript_scheme_returns_422():
    """AC-5 (variant): javascript: scheme is rejected with 422."""
    response = client.post(
        "/shorten", json={"url": "javascript:alert(1)"}
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# AC-6: Health check (FR-7)
# ---------------------------------------------------------------------------
def test_healthz_returns_200_with_ok_status():
    """AC-6: GET /healthz returns 200 and exactly {status: ok}."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# AC-7: Short-code uniqueness across calls (FR-2, FR-8)
# ---------------------------------------------------------------------------
def test_same_url_twice_produces_different_short_codes():
    """AC-7: Submitting the same URL twice yields two distinct short codes
    (no deduplication - FR-8)."""
    url = "https://www.example.com"
    resp1 = client.post("/shorten", json={"url": url})
    resp2 = client.post("/shorten", json={"url": url})
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["short_code"] != resp2.json()["short_code"]


# ---------------------------------------------------------------------------
# Additional edge-case tests
# ---------------------------------------------------------------------------
def test_shorten_missing_url_field_returns_422():
    """Pydantic validation: missing 'url' field in request body returns 422."""
    response = client.post("/shorten", json={})
    assert response.status_code == 422


def test_base62_encoding_produces_only_alphanumeric_characters():
    """FR-3: All short codes produced across multiple calls are alphanumeric."""
    pattern = re.compile(r"^[A-Za-z0-9]{6}$")
    for i in range(10):
        resp = client.post(
            "/shorten", json={"url": f"https://example.com/page{i}"}
        )
        assert resp.status_code == 200
        assert pattern.match(resp.json()["short_code"]), (
            f"Code {resp.json()['short_code']} failed alphanumeric check"
        )


def test_redirect_stores_and_retrieves_multiple_urls():
    """FR-4: Multiple distinct URLs can be shortened and each redirects correctly."""
    urls = [
        "https://alpha.example.com",
        "https://beta.example.com",
        "http://gamma.example.com/path?q=1",
    ]
    codes = []
    for url in urls:
        resp = client.post("/shorten", json={"url": url})
        assert resp.status_code == 200
        codes.append((resp.json()["short_code"], url))

    for code, expected_url in codes:
        redir = client.get(f"/{code}", follow_redirects=False)
        assert redir.status_code == 302
        assert redir.headers["location"] == expected_url
