import asyncio
import sys
import logging
from unittest.mock import patch
from app.services.web_scraper import scrape_page

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_happy_path():
    print("\n--- Testing Happy Path (Playwright) ---")
    try:
        result = await scrape_page("https://example.com")
        print(f"Success! Scraped {len(result.cleaned_html)} chars of HTML.")
        assert len(result.cleaned_html) > 500
        assert result.screenshot_base64 != ""
    except Exception as e:
        print(f"FAILED: {e}")

async def test_fallback_path():
    print("\n--- Testing Fallback Path (HTTPX) ---")
    # Simulate a Playwright timeout by patching the sync thread to raise TimeoutError
    with patch("app.services.web_scraper._scrape_sync_thread") as mock_thread:
        from playwright.async_api import TimeoutError
        mock_thread.side_effect = TimeoutError("Simulated Timeout")
        
        try:
            result = await scrape_page("https://example.com")
            print(f"Fallback Success! Scraped {len(result.cleaned_html)} chars of HTML via HTTPX.")
            assert len(result.cleaned_html) > 500
            assert result.screenshot_base64 == ""  # BS4 fallback has no screenshot
            print("Fallback correctly triggered and produced content.")
        except Exception as e:
            print(f"FAILED: {e}")

async def main():
    await test_happy_path()
    await test_fallback_path()

if __name__ == "__main__":
    asyncio.run(main())
