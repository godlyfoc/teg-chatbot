"""URL helpers for the crawler."""

from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

SKIP_SCHEMES = {"mailto", "tel", "javascript", "data"}
NON_HTML_EXTENSIONS = (
    ".mp3", ".wma", ".wav", ".doc", ".docx",
    ".zip", ".png", ".jpg", ".jpeg", ".gif", ".css", ".js",
)
JUNK_FRAGMENTS = ("/WebResource.axd", "/ScriptResource.axd")


def is_pdf_url(url: str) -> bool:
    return urlparse(url).path.lower().endswith(".pdf")


def is_html_page_url(url: str) -> bool:
    if is_pdf_url(url):
        return False
    path = urlparse(url).path.lower()
    if not path or path.endswith("/"):
        return True
    return not any(path.endswith(ext) for ext in NON_HTML_EXTENSIONS)


def is_allowed_domain(url: str, allowed_domains: list[str]) -> bool:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    for domain in allowed_domains:
        normalized = domain.lower().removeprefix("www.")
        if host == normalized or host.endswith(f".{normalized}"):
            return True
    return False


def _is_junk(url: str) -> bool:
    lower = url.lower()
    return any(fragment.lower() in lower for fragment in JUNK_FRAGMENTS)


def _normalize(url: str, base_url: str, allowed_domains: list[str]) -> str | None:
    if not url or not url.strip():
        return None

    parsed = urlparse(url.strip())
    if parsed.scheme and parsed.scheme.lower() in SKIP_SCHEMES:
        return None

    absolute = urljoin(base_url, url.strip())
    parsed = urlparse(absolute)
    if parsed.scheme not in ("http", "https"):
        return None

    normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", parsed.query, ""))
    if not is_allowed_domain(normalized, allowed_domains) or _is_junk(normalized):
        return None
    return normalized


def normalize_html_url(url: str, base_url: str, allowed_domains: list[str]) -> str | None:
    normalized = _normalize(url, base_url, allowed_domains)
    if normalized and is_html_page_url(normalized):
        return normalized
    return None


def normalize_pdf_url(url: str, base_url: str, allowed_domains: list[str]) -> str | None:
    normalized = _normalize(url, base_url, allowed_domains)
    if normalized and is_pdf_url(normalized):
        return normalized
    return None


def extract_links_from_html(
    html: str,
    page_url: str,
    base_url: str,
    allowed_domains: list[str],
) -> tuple[set[str], set[str]]:
    """Return internal HTML and PDF links found on a page."""
    html_urls: set[str] = set()
    pdf_urls: set[str] = set()

    soup = BeautifulSoup(html, "lxml")

    def _maybe_add_pdf(raw_url: str) -> None:
        pdf = normalize_pdf_url(raw_url, page_url, allowed_domains)
        if pdf:
            pdf_urls.add(pdf)

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if is_pdf_url(href) or href.lower().endswith(".pdf"):
            _maybe_add_pdf(href)
        else:
            page = normalize_html_url(href, page_url, allowed_domains)
            if page:
                html_urls.add(page)

    for tag in soup.find_all(["iframe", "embed", "object"]):
        for attr in ("src", "data", "href"):
            raw = tag.get(attr)
            if raw and (is_pdf_url(raw) or raw.lower().endswith(".pdf")):
                _maybe_add_pdf(raw)

    return html_urls, pdf_urls
