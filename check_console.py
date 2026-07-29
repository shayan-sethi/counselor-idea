import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Listen for console events
        page.on("console", lambda msg: print(f"Browser Console: {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"Browser Error: {err}"))
        
        print("Navigating to index.html...")
        await page.goto("http://127.0.0.1:3000/static/index.html")
        await page.wait_for_timeout(2000)
        
        print("Clicking Recommendation Studio tab...")
        await page.click("#tab-recommendations")
        await page.wait_for_timeout(2000)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
