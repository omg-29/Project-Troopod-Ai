import asyncio
from playwright.async_api import async_playwright

async def main():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            print("Chromium launched successfully.")
            await browser.close()
    except Exception as e:
        print(f"Error: {repr(e)}")

if __name__ == "__main__":
    asyncio.run(main())
