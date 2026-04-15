import asyncio
from app.services.web_scraper import scrape_page

async def main():
    try:
        await scrape_page("https://example.com")
        print("Success")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
