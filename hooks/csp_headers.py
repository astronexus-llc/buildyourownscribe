"""Write Cloudflare Pages `_headers` after each build.

The site is served with a strict Content-Security-Policy. The Material theme
puts a few small scripts inline in every page, and a strict policy only runs
inline scripts it has been given the hash of. Those hashes change when the
theme is updated, so they are computed from the built pages, not kept by hand.
"""
import base64
import hashlib
import re
from pathlib import Path

INLINE_SCRIPT = re.compile(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", re.S)
DATA_TYPES = ("application/json", "application/ld+json", "text/template")


def inline_script_hashes(site_dir: Path) -> list[str]:
    hashes = set()
    for page in site_dir.rglob("*.html"):
        for m in INLINE_SCRIPT.finditer(page.read_text(encoding="utf-8")):
            attrs, body = m.group("attrs"), m.group("body")
            if "src=" in attrs or any(t in attrs for t in DATA_TYPES) or not body.strip():
                continue
            digest = hashlib.sha256(body.encode("utf-8")).digest()
            hashes.add("'sha256-" + base64.b64encode(digest).decode() + "'")
    return sorted(hashes)


def on_post_build(config, **kwargs):
    site_dir = Path(config["site_dir"])
    scripts = " ".join(["'self'", *inline_script_hashes(site_dir), "https://static.cloudflareinsights.com"])
    csp = "; ".join([
        "default-src 'none'",
        f"script-src {scripts}",
        "style-src 'self' 'unsafe-inline'",
        "font-src 'self'",
        "img-src 'self' data:",
        "connect-src 'self' https://cloudflareinsights.com",
        "worker-src 'self'",
        "manifest-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'none'",
        "form-action 'none'",
    ])
    (site_dir / "_headers").write_text("\n".join([
        "/*",
        f"  Content-Security-Policy: {csp}",
        "  Strict-Transport-Security: max-age=31536000; includeSubDomains; preload",
        "  X-Frame-Options: DENY",
        "  X-Content-Type-Options: nosniff",
        "  Referrer-Policy: strict-origin-when-cross-origin",
        "  Permissions-Policy: geolocation=(), microphone=(), camera=(), payment=()",
        "",
        "/assets/*",
        "  Cache-Control: public, max-age=31536000, immutable",
        "",
    ]), encoding="utf-8")
