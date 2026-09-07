ERROR_PRICE = 999_999_999

#=====================================================
#===========        S C R A P I N G        ===========
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def momondo_scraper(url: str, wait_time: int = 10000) -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="chrome", args=["--start-minimized"])

        try:
            page = browser.new_page(locale="cs-CZ", viewport={"width": 1920, "height": 1080})

            page.goto(url, wait_until="domcontentloaded", timeout=60_000)

            if "/help/bots.html" in page.url:
                return ERROR_PRICE

            try:
                page.wait_for_function(r"""() => /\d[\d\s.]*\s*Kč/.test(document.body.innerText)""", timeout=30_000)
            except PlaywrightTimeoutError:
                return ERROR_PRICE

            page.wait_for_timeout(wait_time)

            text = page.locator("body").inner_text()
            raw_prices = re.findall(r"\d[\d\s.\u00a0]*\s*Kč", text)
            prices = [int(re.sub(r"\D", "", price)) for price in raw_prices]

            if not prices:
                return ERROR_PRICE

            return min(prices)

        finally:
            browser.close()       
            
            
