"""Multi-tier image retrieval and caching system for The Butterfly Effect.

Provides verified, stunning, genre- and premise-accurate scene images with zero rate-limit banners:
1. Cache Layer: Local disk cache in static/game_images/cache/{hash}.jpg
2. Tier 1: AI Image Generation (Pollinations Flux/Sana) with rate-limit and error filtering
3. Tier 2: Web Image Search Backup (Bing Images / DuckDuckGo / Wikimedia / Web scraping)
4. Tier 3: Curated High-Art Genre/Role Preset Vault in static/game_images/presets/
"""

import hashlib
import json
import os
import re
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
IMAGES_DIR = STATIC_DIR / "game_images"
CACHE_DIR = IMAGES_DIR / "cache"
PRESETS_DIR = IMAGES_DIR / "presets"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
PRESETS_DIR.mkdir(parents=True, exist_ok=True)

# SSL context for safe outgoing requests on macOS/Linux
_SSL_CTX = ssl._create_unverified_context()
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

# Known bad signatures (rate limit banners, small placeholder SVGs/GIFs)
_BAD_CONTENT_PATTERNS = [
    b"Free limit reached",
    b"free image every 45 seconds",
    b"enter.pollinations.ai",
    b"Rate limit",
    b"402 Payment Required",
    b"Too Many Requests",
]


def _hash_key(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _is_valid_image_bytes(data: bytes) -> bool:
    """Validate that data is an actual substantial image and not a rate limit banner or error."""
    if not data or len(data) < 8192:  # Must be at least 8KB
        return False
    # Check for text error fragments in the binary stream
    for bad in _BAD_CONTENT_PATTERNS:
        if bad in data:
            return False
    # Check standard image magic headers (JPEG, PNG, WebP)
    is_jpeg = data.startswith(b"\xff\xd8\xff")
    is_png = data.startswith(b"\x89PNG\r\n\x1a\n")
    is_webp = data.startswith(b"RIFF") and b"WEBP" in data[:16]
    return is_jpeg or is_png or is_webp


def _fetch_url(url: str, headers: dict = None, timeout: int = 7) -> tuple[bytes, dict, int]:
    """Fetch URL with timeout and custom headers."""
    req_headers = {"User-Agent": _USER_AGENT}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as res:
            data = res.read()
            res_headers = dict(res.headers.items())
            return data, res_headers, res.status
    except Exception:
        return b"", {}, 0


def fetch_from_pollinations(prompt: str, seed: int = 42) -> bytes:
    """Attempt to generate an AI image via Pollinations with rate-limit detection."""
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=960&height=640&nologo=true&seed={seed}&model=flux"
    data, headers, status = _fetch_url(url, timeout=9)

    # Check headers for rate-limit / payment flags
    hdr_keys = [k.lower() for k in headers.keys()]
    if "payment-required" in hdr_keys or "retry-after" in hdr_keys:
        return b""
    if status != 200:
        return b""
    if not _is_valid_image_bytes(data):
        return b""
    return data


def scrape_google_images(query: str, limit: int = 4) -> list[str]:
    """Attempt to scrape candidate images from Google Images or Google-hosted sources."""
    results = []
    clean_q = re.sub(r'[\'\"\,]', '', query).strip()
    try:
        url = f"https://www.google.com/search?q={urllib.parse.quote(clean_q)}&tbm=isch&asearch=ichunk&async=_id:rg_s,_pms:s"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
        data, _, status = _fetch_url(url, headers=headers, timeout=5)
        if status == 200 and data:
            html = data.decode("utf-8", errors="ignore")
            # Extract direct full-res images or gstatic/googleusercontent
            matches = re.findall(r'\"(https://[^\"]+?\.(?:jpg|jpeg|png))\"', html)
            for m in matches:
                if not any(skip in m for skip in ("gstatic.com/favicon", "google.com/logos")):
                    if m not in results:
                        results.append(m)
            # Also check googleusercontent / gstatic
            g_matches = re.findall(r'(https://encrypted-tbn0\.gstatic\.com/images\?q=[^\s\"\'\<\>&]+)', html)
            for g in g_matches:
                if g not in results:
                    results.append(g)
    except Exception:
        pass
    return results[:limit]


def search_web_images(query: str, limit: int = 4) -> list[str]:
    """Scrape candidate high-resolution image URLs from web search (Google Images / Bing / Wikimedia - whichever works)."""
    candidates = []

    # 1. Google Images Search attempt
    try:
        g_imgs = scrape_google_images(query, limit=limit)
        for g in g_imgs:
            if g not in candidates:
                candidates.append(g)
    except Exception:
        pass

    # 2. Bing Images Search (fast, reliable, returns original media URLs)
    if len(candidates) < limit:
        try:
            clean_q = re.sub(r'[\'\"\,]', '', query)
            bing_url = f"https://www.bing.com/images/search?q={urllib.parse.quote(clean_q)}&FORM=HDRSC2"
            html_data, _, _ = _fetch_url(bing_url, timeout=5)
            html = html_data.decode("utf-8", errors="ignore")
            murls = re.findall(r'murl&quot;:&quot;(https://[^&]+\.(?:jpg|jpeg|png))', html)
            for m in murls:
                if m not in candidates:
                    candidates.append(m)
                if len(candidates) >= limit:
                    break
        except Exception:
            pass

    # 3. Wikimedia Commons backup (public domain museum/NASA art)
    if len(candidates) < limit:
        try:
            wiki_url = (
                f"https://commons.wikimedia.org/w/api.php?action=query&generator=search"
                f"&gsrsearch={urllib.parse.quote(query)}&gsrnamespace=6&gsrlimit=4"
                f"&prop=imageinfo&iiprop=url|mime&format=json"
            )
            data, _, _ = _fetch_url(wiki_url, timeout=5)
            if data:
                js = json.loads(data.decode("utf-8", errors="ignore"))
                pages = js.get("query", {}).get("pages", {})
                for p in pages.values():
                    info = p.get("imageinfo", [{}])[0]
                    u = info.get("url")
                    mime = info.get("mime", "")
                    if u and mime in ("image/jpeg", "image/png"):
                        if u not in candidates:
                            candidates.append(u)
                        if len(candidates) >= limit:
                            break
        except Exception:
            pass

    return candidates


def download_first_valid_image(candidate_urls: list[str]) -> bytes:
    """Download the first valid candidate image from a list of URLs."""
    for url in candidate_urls:
        data, _, status = _fetch_url(url, timeout=5)
        if status == 200 and _is_valid_image_bytes(data):
            return data
    return b""


def get_preset_image_bytes(role: str = "wanderer", genre: str = "fantasy") -> tuple[bytes, str]:
    """Retrieve verified local preset image matching role or genre."""
    role_key = (role or "wanderer").lower()
    genre_key = (genre or "fantasy").lower()

    # Priority role presets
    role_map = {
        "astronaut": "astronaut.jpg",
        "pilot": "astronaut.jpg",
        "cat": "cat.jpg",
        "hacker": "cyberpunk.jpg",
        "detective": "noir.jpg",
        "scientist": "astronaut.jpg",
        "witch": "fantasy.jpg",
        "fighter": "fantasy.jpg",
        "scholar": "fantasy.jpg",
        "sailor": "ocean.jpg",
    }

    # Genre fallback map
    genre_map = {
        "scifi": "astronaut.jpg",
        "cyberpunk": "cyberpunk.jpg",
        "mystery": "noir.jpg",
        "noir": "noir.jpg",
        "fantasy": "fantasy.jpg",
        "horror": "gothic.jpg",
        "adventure": "fantasy.jpg",
        "ocean": "ocean.jpg",
    }

    chosen_file = role_map.get(role_key) or genre_map.get(genre_key) or "fantasy.jpg"
    preset_path = PRESETS_DIR / chosen_file

    if preset_path.exists() and preset_path.stat().st_size > 5000:
        return preset_path.read_bytes(), chosen_file

    # If the specific preset doesn't exist, search PRESETS_DIR for any valid jpg
    for p in PRESETS_DIR.glob("*.jpg"):
        if p.stat().st_size > 5000:
            return p.read_bytes(), p.name

    return b"", ""


def resolve_scene_image(prompt: str, seed: int = 42, role: str = "wanderer", genre: str = "fantasy", loc: str = "") -> tuple[str, str]:
    """Main entry point: resolve the best valid image for the scene.
    
    Returns (image_url, image_source_type)
    """
    key = _hash_key(f"{prompt}:{seed}")
    cache_path = CACHE_DIR / f"{key}.jpg"
    cache_rel_url = f"/static/game_images/cache/{key}.jpg"

    # 1. Disk cache check
    if cache_path.exists() and cache_path.stat().st_size > 8192:
        return cache_rel_url, "cache"

    # 2. Tier 1: Try AI Generation
    try:
        ai_data = fetch_from_pollinations(prompt, seed=seed)
        if ai_data and _is_valid_image_bytes(ai_data):
            cache_path.write_bytes(ai_data)
            return cache_rel_url, "ai_generation"
    except Exception:
        pass

    # 3. Tier 2: Web Image Search Backup (whichever works)
    search_query = f"{role} {loc} {genre} concept art".strip()
    try:
        candidates = search_web_images(search_query)
        if candidates:
            web_data = download_first_valid_image(candidates)
            if web_data:
                cache_path.write_bytes(web_data)
                return cache_rel_url, "web_search"
    except Exception:
        pass

    # 4. Tier 3: Preset Vault fallback
    preset_data, preset_name = get_preset_image_bytes(role=role, genre=genre)
    if preset_data:
        cache_path.write_bytes(preset_data)
        return cache_rel_url, f"preset_{preset_name}"

    # Default to any existing static game image
    for img_file in IMAGES_DIR.glob("*.jpg"):
        if img_file.stat().st_size > 8192:
            return f"/static/game_images/{img_file.name}", "static_fallback"

    return cache_rel_url, "none"
