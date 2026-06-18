"""
Website proxy for iframe demo.

teg.ie blocks iframe embedding (X-Frame-Options: SAMEORIGIN) and uses ASP.NET
forms (POST). This proxy fetches pages server-side, rewrites navigation to stay
on /api/proxy/, and forwards GET/POST to the real site.
"""

import re
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import HTTPException
from fastapi.responses import HTMLResponse, Response

from app.config import Settings

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

PROXY_PREFIX = "/api/proxy"

# Rewrite navigation attributes — not stylesheet <link> hrefs
ANCHOR_HREF_RE = re.compile(
    r"(<a\s[^>]*?\bhref=)([\"'])([^\"']*)(\2)",
    re.IGNORECASE,
)
FORM_ACTION_RE = re.compile(
    r"(<form\s[^>]*?\baction=)([\"'])([^\"']*)(\2)",
    re.IGNORECASE,
)
EXISTING_BASE_RE = re.compile(r"<base[^>]*>", re.IGNORECASE)

# Client script: catch JS-driven navigation to teg.ie
NAV_GUARD_SCRIPT = """
<script id="teg-proxy-guard">
(function () {
  var PROXY = "/api/proxy";
  var HOSTS = {hosts};

  function hostAllowed(hostname) {
    return HOSTS.indexOf(hostname) !== -1;
  }

  function toProxy(url) {
    try {
      var u = new URL(url, window.location.href);
      if (hostAllowed(u.hostname)) {
        return PROXY + u.pathname + u.search + u.hash;
      }
    } catch (e) {}
    return null;
  }

  document.addEventListener("click", function (e) {
    var a = e.target.closest("a[href]");
    if (!a || a.target === "_blank") return;
    var next = toProxy(a.href);
    if (next) { e.preventDefault(); window.location.href = next; }
  }, true);

  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (!form || form.tagName !== "FORM") return;
    var next = toProxy(form.action || window.location.href);
    if (next && form.action !== next) form.action = next;
  }, true);
})();
</script>
"""


def _allowed_hosts(settings: Settings) -> set[str]:
    return {host.strip().lower() for host in settings.proxy_allowed_hosts.split(",") if host.strip()}


def _validate_target(url: str, settings: Settings) -> None:
    host = urlparse(url).hostname
    if not host or host.lower() not in _allowed_hosts(settings):
        raise HTTPException(status_code=403, detail="Proxy target not allowed")


def _build_target_url(settings: Settings, path: str, query: str) -> str:
    base = settings.proxy_target_base.rstrip("/") + "/"
    target = urljoin(base, path.lstrip("/"))
    if query:
        target = f"{target}?{query}"
    _validate_target(target, settings)
    return target


def _to_proxy_path(url: str, site_base: str) -> str | None:
    """Convert an internal teg.ie URL to a proxy path, or None to leave unchanged."""
    if not url or url.startswith("#"):
        return None
    if url.startswith(("mailto:", "tel:", "javascript:", "data:")):
        return None
    if url.startswith(PROXY_PREFIX):
        return None

    if url.startswith(site_base):
        path = url[len(site_base):]
        return f"{PROXY_PREFIX}/{path.lstrip('/')}" if path else f"{PROXY_PREFIX}/"

    if url.startswith("/") and not url.startswith("//"):
        return f"{PROXY_PREFIX}{url}"

    return None


def _rewrite_attr(match: re.Match, site_base: str) -> str:
    prefix, quote, url, end_quote = match.groups()
    proxy_path = _to_proxy_path(url, site_base)
    if proxy_path is None:
        return match.group(0)
    return f"{prefix}{quote}{proxy_path}{end_quote}"


def _rewrite_html(html: str, settings: Settings) -> str:
    """
    Keep all navigation inside the proxy:
    - <base href="/api/proxy/"> so relative URLs resolve locally
    - Rewrite <a href> and <form action> to proxy paths
    - Inject a small script to catch JS navigation to teg.ie
    """
    site_base = settings.proxy_target_base.rstrip("/")

    html = EXISTING_BASE_RE.sub("", html)
    html = ANCHOR_HREF_RE.sub(lambda m: _rewrite_attr(m, site_base), html)
    html = FORM_ACTION_RE.sub(lambda m: _rewrite_attr(m, site_base), html)

    # Relative URLs (forms, scripts, links) resolve through the proxy
    base_tag = f'<base href="{PROXY_PREFIX}/">'
    head_match = re.search(r"<head[^>]*>", html, flags=re.IGNORECASE)
    if head_match:
        html = html[: head_match.end()] + base_tag + html[head_match.end():]
    else:
        html = base_tag + html

    hosts_json = ", ".join(f'"{h}"' for h in _allowed_hosts(settings))
    script = NAV_GUARD_SCRIPT.replace("{hosts}", f"[{hosts_json}]")

    if re.search(r"</body>", html, re.IGNORECASE):
        html = re.sub(r"</body>", script + "</body>", html, count=1, flags=re.IGNORECASE)
    else:
        html += script

    return html


async def fetch_proxied(
    settings: Settings,
    path: str = "",
    query: str = "",
    method: str = "GET",
    body: bytes | None = None,
    content_type: str | None = None,
    cookie: str | None = None,
) -> Response:
    """Fetch from the target site and return without frame-blocking headers."""
    target_url = _build_target_url(settings, path, query)

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
    }
    if cookie:
        headers["Cookie"] = cookie
    if content_type and method == "POST":
        headers["Content-Type"] = content_type

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            if method == "POST":
                upstream = await client.post(target_url, headers=headers, content=body or b"")
            else:
                upstream = await client.get(target_url, headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to reach site: {exc}") from exc

    upstream_type = upstream.headers.get("content-type", "application/octet-stream")

    if "text/html" in upstream_type.lower():
        body_text = _rewrite_html(upstream.text, settings)
        return HTMLResponse(
            content=body_text,
            status_code=upstream.status_code,
            headers={"Cache-Control": "no-cache"},
        )

    media_type = upstream_type.split(";")[0].strip()
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )
