import asyncio
import base64
import logging
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

from app.config import settings
from app.schemas import ScrapedPage
from app.services.ai_client import ai_client
from app.utils.url_rewriter import rewrite_paths

logger = logging.getLogger(__name__)


async def _scroll_to_bottom(page) -> None:
    """Scroll page to bottom to trigger lazy-loaded content."""
    try:
        await page.evaluate("""
            async () => {
                const delay = (ms) => new Promise(r => setTimeout(r, ms));
                const scrollHeight = () => document.body.scrollHeight;
                let lastHeight = 0;
                let currentHeight = scrollHeight();

                while (lastHeight !== currentHeight) {
                    lastHeight = currentHeight;
                    window.scrollTo(0, currentHeight);
                    await delay(500);
                    currentHeight = scrollHeight();
                }
                window.scrollTo(0, 0);
            }
        """)
    except Exception as scroll_err:
        logger.warning("Scroll to bottom failed (non-critical): %s", scroll_err)


async def _extract_css(page, base_url: str) -> str:
    """Extract all CSS: inline <style> tags and linked stylesheet contents."""
    css_parts = []

    # Inline styles
    inline_styles = await page.evaluate("""
        () => {
            const styles = document.querySelectorAll('style');
            return Array.from(styles).map(s => s.textContent || '');
        }
    """)
    css_parts.extend(inline_styles)

    # Linked stylesheets
    stylesheet_urls = await page.evaluate("""
        () => {
            const links = document.querySelectorAll('link[rel="stylesheet"]');
            return Array.from(links).map(l => l.href).filter(Boolean);
        }
    """)

    from app.utils.url_rewriter import rewrite_css_paths

    for url in stylesheet_urls:
        try:
            response = await page.context.request.get(url, timeout=5000)
            if response.ok:
                raw_css = await response.text()
                # Crucial: Rewrite CSS based on the stylesheet's absolute URL, not the page's base_url!
                rewritten_css = rewrite_css_paths(raw_css, url)
                css_parts.append(rewritten_css)
        except Exception as css_err:
            logger.warning("Failed to fetch stylesheet %s: %s", url, css_err)

    return "\n\n/* --- stylesheet boundary --- */\n\n".join(css_parts)


async def _extract_js(page) -> str:
    """Extract inline <script> tag contents (skip external scripts to avoid bloat)."""
    inline_scripts = await page.evaluate("""
        () => {
            const scripts = document.querySelectorAll('script:not([src])');
            return Array.from(scripts).map(s => s.textContent || '').filter(t => t.trim().length > 0);
        }
    """)
    return "\n\n// --- script boundary ---\n\n".join(inline_scripts)


async def _get_accessibility_tree(page) -> dict:
    """Capture the accessibility tree snapshot."""
    try:
        tree = await page.accessibility.snapshot()
        return tree if tree else {}
    except Exception as a11y_err:
        logger.warning("Accessibility tree capture failed: %s", a11y_err)
        return {}


async def _scrape_with_playwright_async(url: str) -> ScrapedPage:
    """
    Full Playwright-based scraping logic.
    """
    from app.utils.content_optimizer import optimize_scraped_content

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        try:
            # Wait for domcontentloaded (more reliable than networkidle for heavy SPAs)
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=settings.SCRAPE_TIMEOUT_MS,
            )
            
            # Soft wait for networkidle, but ignore if it times out
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass

            # Scroll to trigger lazy content
            await _scroll_to_bottom(page)
            await asyncio.sleep(1)

            # Determine base URL
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"

            # Capture raw HTML
            raw_html = await page.content()
            rewritten_html = rewrite_paths(raw_html, base_url)

            # Capture raw CSS
            raw_css = await _extract_css(page, base_url)

            # Capture raw inline JS
            raw_js = await _extract_js(page)

            # === OPTIMIZATION: Clean and minimize before storing ===
            cleaned_html, cleaned_css, cleaned_js = optimize_scraped_content(
                html=rewritten_html,
                css=raw_css,
                js=raw_js,
                base_url=base_url,
            )

            # Accessibility tree
            a11y_tree = await _get_accessibility_tree(page)

            # Full-page screenshot
            screenshot_bytes = await page.screenshot(full_page=True)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            return ScrapedPage(
                cleaned_html=cleaned_html,
                css_bundle=cleaned_css,
                js_bundle=cleaned_js,
                accessibility_tree=a11y_tree,
                screenshot_base64=screenshot_b64,
                base_url=base_url,
            )

        finally:
            await browser.close()


def _scrape_sync_thread(url: str) -> ScrapedPage:
    """
    Run the playwright async code synchronously in a completely new event loop.
    This bypasses Windows Uvicorn asyncio policy conflicts.
    """
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    try:
        return new_loop.run_until_complete(_scrape_with_playwright_async(url))
    finally:
        new_loop.close()



async def _fallback_from_screenshot(
    screenshot_b64: str, url: str
) -> ScrapedPage:
    """
    Fallback: Use a captured screenshot + Gemini Vision to understand
    the page layout and generate a structural HTML approximation.
    """
    logger.info("Using screenshot fallback to reconstruct page structure")

    screenshot_bytes = base64.b64decode(screenshot_b64)

    prompt = (
        "You are an expert front-end developer. I have a screenshot of a webpage. "
        "Analyze the screenshot and generate a faithful HTML reconstruction that captures:\n"
        "1. The overall layout structure (header, hero section, content sections, footer)\n"
        "2. Navigation elements and their approximate text\n"
        "3. All visible text content, headings, paragraphs, and buttons\n"
        "4. Image placeholders with descriptive alt text\n"
        "5. The visual styling (colors, fonts, spacing) as inline CSS or a <style> block\n\n"
        "Return a complete, valid HTML document. Do NOT wrap in markdown code fences.\n"
        "The HTML should be as close as possible to what this page actually looks like.\n"
        f"The original URL is: {url}"
    )

    html_result = await ai_client.generate_text(
        prompt=prompt,
        image_bytes=screenshot_bytes,
        mime_type="image/png",
    )

    from app.utils.sanitizer import strip_code_fences
    clean_html = strip_code_fences(html_result)

    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    return ScrapedPage(
        cleaned_html=clean_html,
        css_bundle="",
        js_bundle="",
        accessibility_tree={},
        screenshot_base64=screenshot_b64,
        base_url=base_url,
    )


async def scrape_page(url: str) -> ScrapedPage:
    """
    Step 3: Scrape the target webpage using Playwright.

    If scraping fails or returns garbage (<500 chars of meaningful content),
    falls back to screenshot-based reconstruction via Gemini Vision.
    """
    logger.info("Step 3: Scraping target webpage: %s", url)

    screenshot_b64 = ""

    try:
        # Run Playwright in an isolated thread to bypass Windows asyncio loop issues
        result = await asyncio.to_thread(_scrape_sync_thread, url)

        # Validate we got meaningful content
        meaningful_length = len(result.cleaned_html.strip())
        if meaningful_length < 500:
            logger.warning(
                "Scraped HTML too short (%d chars), using screenshot fallback",
                meaningful_length,
            )
            if result.screenshot_base64:
                return await _fallback_from_screenshot(
                    result.screenshot_base64, url
                )
            raise RuntimeError("Scraping produced insufficient content and no screenshot available")

        logger.info(
            "Step 3 complete: Scraped %d chars of HTML, %d chars of CSS",
            len(result.cleaned_html),
            len(result.css_bundle),
        )
        return result

    except PlaywrightTimeout:
        logger.error("Playwright timed out for URL: %s", url)
        if screenshot_b64:
            return await _fallback_from_screenshot(screenshot_b64, url)
        raise RuntimeError(f"Page scraping timed out for {url}")

    except Exception as scrape_err:
        err_msg = getattr(scrape_err, "message", repr(scrape_err))
        logger.error("Scraping failed for %s: %s", url, err_msg)
        if screenshot_b64:
            return await _fallback_from_screenshot(screenshot_b64, url)
        raise RuntimeError(f"Scraping failed: {err_msg}") from scrape_err
