#!/usr/bin/env python3
"""Generate a cyberpunk (radical-themed) X/Twitter profile card SVG using the FxTwitter API."""

import base64
import datetime
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

USERNAME = os.environ.get("X_USERNAME", "wakokara")
OUT_PATH = os.environ.get("X_CARD_OUT", "assets/x-profile-card.svg")
USER_AGENT = "waxsd100-profile-readme/1.0 (+https://github.com/waxsd100/waxsd100)"

INVISIBLE_RE = re.compile(r"[\u200b-\u200f\u2028\u2029\u2060\ufeff]+")


def clean_text(text: str) -> str:
    if not text:
        return ""
    cleaned = INVISIBLE_RE.sub("", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def fetch_bytes(url: str, retries: int = 3) -> bytes:
    last_err = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    return resp.read()
        except Exception as err:
            last_err = err
        if attempt + 1 < retries:
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def fetch_user(username: str) -> dict:
    url = f"https://api.fxtwitter.com/{username}"
    last_err = None
    for attempt in range(4):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") == 200 and data.get("user"):
                    return data["user"]
                last_err = f"Unexpected payload: {data}"
        except Exception as err:
            last_err = err
        if attempt + 1 < 4:
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"FxTwitter lookup failed for @{username}: {last_err}")


def to_data_uri(url: str, mime: str = "image/jpeg") -> str:
    if not url:
        return ""
    try:
        raw = fetch_bytes(url, retries=2)
        b64 = base64.b64encode(raw).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return ""


def format_joined(joined_str: str) -> str:
    if not joined_str:
        return ""
    try:
        dt = datetime.datetime.strptime(joined_str, "%a %b %d %H:%M:%S %z %Y")
        return dt.strftime("%b %Y")
    except Exception:
        return ""


def format_num(n) -> str:
    try:
        return f"{int(n):,}"
    except Exception:
        return "0"


def build_svg(user: dict) -> str:
    name = clean_text(user.get("name") or f"@{USERNAME}")
    screen_name = clean_text(user.get("screen_name") or USERNAME)
    bio = clean_text(user.get("description") or "")
    website_obj = user.get("website") or {}
    website_disp = clean_text(website_obj.get("display_url") or "")
    joined = format_joined(user.get("joined") or "")

    avatar_url = (user.get("avatar_url") or "").replace("_normal.", "_400x400.")
    banner_base = user.get("banner_url") or ""
    banner_url = f"{banner_base}/600x200" if banner_base else ""

    avatar_uri = to_data_uri(avatar_url)
    banner_uri = to_data_uri(banner_url)

    posts = format_num(user.get("tweets", 0))
    followers = format_num(user.get("followers", 0))
    following = format_num(user.get("following", 0))
    likes = format_num(user.get("likes", 0))

    jst = datetime.timezone(datetime.timedelta(hours=9))
    updated_str = datetime.datetime.now(jst).strftime("%Y-%m-%d JST")

    meta_parts = [f"@{screen_name}"]
    if website_disp:
        meta_parts.append(website_disp)
    if joined:
        meta_parts.append(f"Joined {joined}")
    meta_line = "  ·  ".join(meta_parts)

    bio_truncated = (bio[:62] + "…") if len(bio) > 63 else bio

    banner_block = ""
    if banner_uri:
        banner_block = f"""
    <image href="{banner_uri}" x="0" y="0" width="660" height="84" preserveAspectRatio="xMidYMid slice" clip-path="url(#cardClip)" opacity="0.34" />
    <rect x="0" y="0" width="660" height="84" fill="url(#bannerFade)" clip-path="url(#cardClip)" />"""

    avatar_block = ""
    if avatar_uri:
        avatar_block = f"""
    <circle cx="58" cy="64" r="35" fill="#141321" stroke="url(#neonRing)" stroke-width="3" />
    <image href="{avatar_uri}" x="26" y="32" width="64" height="64" clip-path="url(#avatarClip)" preserveAspectRatio="xMidYMid slice" />"""
    else:
        avatar_block = """
    <circle cx="58" cy="64" r="34" fill="#1e1c33" stroke="url(#neonRing)" stroke-width="3" />"""

    bio_svg = ""
    if bio_truncated:
        bio_svg = f'<text x="108" y="92" class="bio">{html.escape(bio_truncated)}</text>'

    stat_items = [
        ("POSTS", posts, "#FE428E"),
        ("FOLLOWERS", followers, "#A9FEF7"),
        ("FOLLOWING", following, "#F8D847"),
        ("LIKES", likes, "#BD93F9"),
    ]
    stats_svg = []
    box_w = 144
    gap = 12
    start_x = 24
    for i, (label, val, accent) in enumerate(stat_items):
        bx = start_x + i * (box_w + gap)
        stats_svg.append(f"""
    <g transform="translate({bx}, 112)">
      <rect width="{box_w}" height="52" rx="6" fill="#1c1a30" stroke="#2f2b4f" stroke-width="1" />
      <rect width="3" height="32" x="0" y="10" rx="1.5" fill="{accent}" />
      <text x="14" y="21" class="stat-label">{label}</text>
      <text x="14" y="42" class="stat-val" fill="{accent}">{val}</text>
    </g>""")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="660" height="190" viewBox="0 0 660 190" role="img" aria-label="X Profile: {html.escape(name)} (@{html.escape(screen_name)})">
  <defs>
    <clipPath id="cardClip">
      <rect x="1" y="1" width="658" height="188" rx="8" />
    </clipPath>
    <clipPath id="avatarClip">
      <circle cx="58" cy="64" r="32" />
    </clipPath>
    <linearGradient id="neonRing" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FE428E" />
      <stop offset="50%" stop-color="#9D4EDD" />
      <stop offset="100%" stop-color="#00D8FF" />
    </linearGradient>
    <linearGradient id="bannerFade" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#141321" stop-opacity="0.25" />
      <stop offset="100%" stop-color="#141321" stop-opacity="1" />
    </linearGradient>
    <style>
      .name {{ font: 700 20px 'Segoe UI', 'Hiragino Sans', 'Meiryo', Ubuntu, sans-serif; fill: #FE428E; }}
      .meta {{ font: 600 12.5px 'Segoe UI', Ubuntu, monospace; fill: #A9FEF7; }}
      .bio {{ font: 400 12px 'Segoe UI', 'Hiragino Sans', Ubuntu, sans-serif; fill: #d0cee8; }}
      .stat-label {{ font: 700 10px 'Segoe UI', Ubuntu, monospace; fill: #9b96bd; letter-spacing: 0.08em; }}
      .stat-val {{ font: 700 17px 'Segoe UI', Ubuntu, monospace; }}
      .footer {{ font: 400 10px 'Segoe UI', Ubuntu, monospace; fill: #6e6a92; }}
    </style>
  </defs>

  <rect x="0.75" y="0.75" width="658.5" height="188.5" rx="8" fill="#141321" stroke="url(#neonRing)" stroke-width="1.5" />
  {banner_block}
  {avatar_block}

  <!-- X Logo -->
  <g transform="translate(612, 20) scale(1.1)" fill="#FE428E" opacity="0.9">
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
  </g>

  <text x="108" y="54" class="name">{html.escape(name)}</text>
  <text x="108" y="75" class="meta">{html.escape(meta_line)}</text>
  {bio_svg}

  {''.join(stats_svg)}

  <text x="636" y="180" text-anchor="end" class="footer">Powered by FxTwitter · Updated {updated_str}</text>
</svg>
"""


def main() -> int:
    try:
        user = fetch_user(USERNAME)
    except Exception as err:
        print(f"Warning: {err}", file=sys.stderr)
        if os.path.exists(OUT_PATH):
            print(f"Keeping existing {OUT_PATH}.", file=sys.stderr)
            return 0
        return 1

    svg = build_svg(user)
    os.makedirs(os.path.dirname(OUT_PATH) or ".", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Generated {OUT_PATH} ({len(svg)} bytes) for @{user.get('screen_name', USERNAME)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
