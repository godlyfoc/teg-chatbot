"""Headless browser fetching for JavaScript-rendered pages."""

import logging

logger = logging.getLogger(__name__)

CONTENT_SELECTORS = (
    ".faqContainer",
    "section#middle",
    "#content",
)

COOKIE_ACCEPT_SELECTORS = (
    "#onetrust-accept-btn-handler",
    "button:has-text('Accept All Cookies')",
    "button:has-text('Accept')",
    "button:has-text('Glac')",
)


async def _accept_cookies(page) -> None:
    for selector in COOKIE_ACCEPT_SELECTORS:
        try:
            button = page.locator(selector).first
            if await button.count() > 0 and await button.is_visible():
                await button.click(timeout=3000)
                await page.wait_for_timeout(500)
                return
        except Exception:
            continue


async def _wait_for_content(page, *, wait_ms: int) -> None:
    for selector in CONTENT_SELECTORS:
        try:
            await page.wait_for_selector(selector, timeout=wait_ms, state="attached")
            text = await page.locator(selector).first.inner_text()
            if len(text.strip()) >= 50:
                return
        except Exception:
            continue
    await page.wait_for_timeout(wait_ms)


class BrowserFetcher:
    """Reusable headless Chromium session for JS-rendered pages."""

    def __init__(
        self,
        *,
        wait_ms: int = 2500,
        timeout_ms: int = 60000,
    ) -> None:
        self.wait_ms = wait_ms
        self.timeout_ms = timeout_ms
        self._playwright = None
        self._browser = None

    async def __aenter__(self) -> "BrowserFetcher":
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("Playwright not installed — browser fallback disabled")
            return self

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def fetch_html(self, url: str) -> str | None:
        if not self._browser:
            return None

        page = await self._browser.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=self.timeout_ms)
            await _accept_cookies(page)
            await _wait_for_content(page, wait_ms=self.wait_ms)
            return await page.content()
        except Exception as exc:
            logger.warning("Browser fetch failed for %s: %s", url, exc)
            return None
        finally:
            await page.close()


async def fetch_rendered_html(
    url: str,
    *,
    wait_ms: int = 2500,
    timeout_ms: int = 60000,
    fetcher: BrowserFetcher | None = None,
) -> str | None:
    """Load a page in headless Chromium and return the rendered HTML."""
    if fetcher is not None:
        return await fetcher.fetch_html(url)

    async with BrowserFetcher(wait_ms=wait_ms, timeout_ms=timeout_ms) as session:
        return await session.fetch_html(url)
