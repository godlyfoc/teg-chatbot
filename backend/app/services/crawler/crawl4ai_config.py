"""Crawl4AI browser and run configuration for teg.ie."""

from crawl4ai import BrowserConfig, CacheMode, CrawlerRunConfig

TEG_CSS_SELECTOR = "section#middle, .BlogContent, .BlogArticle, #content"


def build_browser_config() -> BrowserConfig:
    return BrowserConfig(
        headless=True,
        user_agent="TEG-Chatbot-Crawler/1.0",
    )


def build_run_config(
    *,
    concurrency: int,
    browser_wait_ms: int,
    browser_fallback: bool,
) -> CrawlerRunConfig:
    delay_s = browser_wait_ms / 1000.0 if browser_fallback else 0.1
    return CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=10,
        css_selector=TEG_CSS_SELECTOR,
        excluded_tags=["nav", "footer", "header", "script", "style", "noscript"],
        page_timeout=60000,
        delay_before_return_html=delay_s,
        remove_overlay_elements=True,
        semaphore_count=concurrency,
        verbose=False,
    )
