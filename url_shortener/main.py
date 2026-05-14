"""
url_shortener/main.py
Minimal FastAPI URL-shortening microservice.

BRD §4 constraint: all application logic in this single file.
HLD §2 Component model: FastAPI App + In-Memory Store.
ADR-001: in-memory dict; ADR-002: base-62 counter; ADR-003: single-file.
"""

import os
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Base-62 alphabet: 0-9 A-Z a-z  (BRD §7 assumption; HLD §3)
# ---------------------------------------------------------------------------
_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def _to_base62(n: int) -> str:
    """Encode a non-negative integer as a 6-character base-62 string.

    Left-pads with '0' to ensure exactly 6 characters (FR-3).
    Supports up to 62**6 approx 56.8 billion unique codes (BRD §9 risk 6).
    """
    if n == 0:
        return _ALPHABET[0] * 6
    digits: list[str] = []
    while n:
        digits.append(_ALPHABET[n % 62])
        n //= 62
    return "".join(reversed(digits)).zfill(6)


# ---------------------------------------------------------------------------
# In-memory store  (ADR-001)
# ---------------------------------------------------------------------------
_store: dict[str, str] = {}   # short_code -> original_url
_counter: int = 0              # monotonically incrementing (ADR-002)

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="URL Shortener Demo",
    description="Minimal in-memory URL shortening service (AI-SDLC demo).",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------
class ShortenRequest(BaseModel):
    url: str


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str


class HealthResponse(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/healthz", response_model=HealthResponse, status_code=200)
def health_check() -> HealthResponse:
    """GET /healthz - liveness probe with no storage dependency (FR-7)."""
    return HealthResponse(status="ok")


@app.post("/shorten", response_model=ShortenResponse, status_code=200)
def shorten_url(body: ShortenRequest) -> ShortenResponse:
    """POST /shorten - create a short code for the supplied URL.

    FR-1: accepts {url}, returns {short_code, short_url}.
    FR-2: each call produces a distinct short code.
    FR-3: short code is exactly 6 base-62 characters.
    FR-6: rejects URLs whose scheme is not http or https (HTTP 422).
    FR-8: no deduplication - same URL submitted twice yields two codes.
    """
    global _counter

    parsed = urlparse(body.url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(
            status_code=422,
            detail="URL scheme must be http or https",
        )

    _counter += 1
    short_code = _to_base62(_counter)
    _store[short_code] = body.url

    return ShortenResponse(
        short_code=short_code,
        short_url=f"{BASE_URL}/{short_code}",
    )


@app.get("/{short_code}")
def redirect(short_code: str) -> RedirectResponse:
    """GET /{short_code} - redirect to the original URL (FR-4) or 404 (FR-5).

    Returns HTTP 302 with Location header set to the original URL.
    Returns HTTP 404 with {detail: 'Short code not found'} if unknown.

    NOTE: /healthz is registered before this route so it takes precedence.
    """
    original_url = _store.get(short_code)
    if original_url is None:
        raise HTTPException(status_code=404, detail="Short code not found")
    return RedirectResponse(url=original_url, status_code=302)
