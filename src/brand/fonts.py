"""Same-origin Söhne font proxy.

The Epiphan design-system stylesheet references the Söhne OTF files on
``chat.epiphan.com``, but those font files are served WITHOUT CORS headers.
A browser on any other origin (this app) therefore refuses to use them and
silently falls back to system fonts — which violates the brand rule that
Söhne must never be substituted.

This router serves the fonts same-origin instead:
  * ``GET /brand/fonts.css``        — @font-face rules pointing at our own
                                       ``/brand/font/<key>.otf`` endpoints.
  * ``GET /brand/font/<key>.otf``   — proxies the upstream OTF (a server-to-
                                       server fetch, so no browser CORS) and
                                       returns it with long cache headers.

Bytes are memoised in-process so a warm worker serves them instantly. If the
upstream is unreachable the font request fails and the browser falls back to
the neutral stack declared in ``demo.html`` — the page never breaks.
"""

from __future__ import annotations

import asyncio
import logging

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/brand", tags=["brand"])

_UPSTREAM = "https://chat.epiphan.com/api/brand/asset/{key}"

# Local key -> upstream asset key. Only the weights the demo actually uses:
# Buch (400) body, Kräftig (500) UI labels, Halbfett (600) headings, Mono (400).
_FONTS: dict[str, str] = {
    "sohne-buch": "font-sohne-buch",
    "sohne-kraftig": "font-sohne-kraftig",
    "sohne-halbfett": "font-sohne-halbfett",
    "sohne-mono-buch": "font-sohne-mono-buch",
}

# In-process cache of fetched OTF bytes, keyed by local key.
_cache: dict[str, bytes] = {}

# Per-key locks so a cold-start stampede collapses to one upstream fetch.
# dict.setdefault is atomic within the event loop (no await between check/set).
_locks: dict[str, asyncio.Lock] = {}

_FONT_CSS = "\n".join(
    [
        "@font-face{font-family:'Söhne';font-weight:400;font-style:normal;font-display:swap;"
        "src:url('/brand/font/sohne-buch.otf') format('opentype');}",
        "@font-face{font-family:'Söhne';font-weight:500;font-style:normal;font-display:swap;"
        "src:url('/brand/font/sohne-kraftig.otf') format('opentype');}",
        "@font-face{font-family:'Söhne';font-weight:600;font-style:normal;font-display:swap;"
        "src:url('/brand/font/sohne-halbfett.otf') format('opentype');}",
        "@font-face{font-family:'Söhne Mono';font-weight:400;font-style:normal;font-display:swap;"
        "src:url('/brand/font/sohne-mono-buch.otf') format('opentype');}",
    ]
)


@router.get("/fonts.css")
async def brand_fonts_css() -> Response:
    """Return the same-origin Söhne @font-face stylesheet."""
    return Response(
        content=_FONT_CSS,
        media_type="text/css",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/font/{key}.otf")
async def brand_font(key: str) -> Response:
    """Proxy a single Söhne OTF same-origin (sidesteps the upstream CORS gap)."""
    upstream_key = _FONTS.get(key)
    if upstream_key is None:
        raise HTTPException(status_code=404, detail=f"Unknown font key: {key}")

    if key not in _cache:
        async with _locks.setdefault(key, asyncio.Lock()):
            if key not in _cache:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        resp = await client.get(_UPSTREAM.format(key=upstream_key))
                        resp.raise_for_status()
                        _cache[key] = resp.content
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    logger.warning(
                        "Söhne font %r upstream returned HTTP %s", key, status
                    )
                    raise HTTPException(
                        status_code=502, detail=f"Font upstream error {status}"
                    ) from exc
                except httpx.HTTPError as exc:
                    logger.warning("Söhne font %r upstream unreachable: %s", key, exc)
                    raise HTTPException(
                        status_code=502, detail="Font upstream unavailable"
                    ) from exc

    return Response(
        content=_cache[key],
        media_type="font/otf",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
