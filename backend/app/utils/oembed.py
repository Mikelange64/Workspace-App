from urllib.parse import urlparse

import httpx

# Each entry is a fixed, hardcoded endpoint on the provider's own domain -
# the outbound request always goes to a trusted destination we chose, never
# to a URL supplied by the caller. Only the query string is user-derived.
OEMBED_ENDPOINTS = {
    "youtube.com": "https://www.youtube.com/oembed",
    "youtu.be": "https://www.youtube.com/oembed",
    "vimeo.com": "https://vimeo.com/api/oembed.json",
    "soundcloud.com": "https://soundcloud.com/oembed",
    "open.spotify.com": "https://open.spotify.com/oembed",
}


def fetch_oembed_thumbnail(url: str) -> str | None:
    """Look up a real thumbnail for links from a small allowlist of providers
    with public, keyless oEmbed endpoints. Returns None for anything else,
    or if the provider is slow/unreachable/returns something unexpected -
    this must never block or fail link creation.
    """
    hostname = (urlparse(url).hostname or "").removeprefix("www.")
    endpoint = OEMBED_ENDPOINTS.get(hostname)
    if endpoint is None:
        return None

    try:
        response = httpx.get(
            endpoint,
            params={"url": url, "format": "json"},
            timeout=5.0,
            follow_redirects=False,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    thumbnail = data.get("thumbnail_url")
    if isinstance(thumbnail, str) and thumbnail.startswith("https://"):
        return thumbnail
    return None
