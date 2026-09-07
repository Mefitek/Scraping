import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


ERROR_PRICE = 999_999_999
PROFILE_DIR = Path(__file__).parent / "google_chrome_profile"


def add_google_params(url: str) -> str:
    parts = urlsplit(url)
    params = dict(parse_qsl(parts.query))

    params["hl"] = "cs"
    params["gl"] = "CZ"
    params["curr"] = "CZK"

    return urlunsplit((
        parts.scheme,
        parts.netloc,
        parts.path,
        urlencode(params),
        parts.fragment,
    ))


def scrape_google_flights(url: str, wait_time: int = 10000) -> int:
    url = add_google_params(url)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            channel="chrome",
            locale="cs-CZ",
            timezone_id="Europe/Prague",
            viewport={"width": 1920, "height": 1080},
        )

        try:
            page = context.pages[0]

            page.bring_to_front()

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60_000,
            )

            #=====================================================
            #===========        C O N S E N T          ===========
            
            if "consent.google.com" in page.url:
                try:
                    button = page.get_by_role(
                        "button",
                        name=re.compile(r"Odmítnout vše|Reject all", re.IGNORECASE)
                    )

                    button.click(timeout=10_000)

                    page.wait_for_load_state(
                        "domcontentloaded",
                        timeout=30_000
                    )

                except PlaywrightTimeoutError:
                    print("Nepodařilo se odkliknout Google consent.")
                    return ERROR_PRICE

            #=====================================================
            #===========          D E B U G            ===========

            print()
            print("Google Flights debug:")
            print("URL:", page.url)
            print("webdriver:", page.evaluate("navigator.webdriver"))
            print("language:", page.evaluate("navigator.language"))
            print(
                "timezone:",
                page.evaluate(
                    "Intl.DateTimeFormat().resolvedOptions().timeZone"
                )
            )
            print()

            # Necháme Google Flights pořádně načíst výsledky
            page.wait_for_timeout(15_000)

            #=====================================================
            #===========          P R I C E            ===========

            try:
                page.wait_for_function(
                    r"""() => /\d[\d\s.]*\s*Kč/.test(document.body.innerText)""",
                    timeout=30_000
                )

            except PlaywrightTimeoutError:
                print("Nenalezeny žádné ceny.")
                return ERROR_PRICE

            page.wait_for_timeout(wait_time)

            #=====================================================
            # Nejprve zkusíme pouze řádky s lety

            flights = page.locator("li.pIav2d")
            prices = []

            print(f"Flight elements: {flights.count()}")

            for i in range(flights.count()):
                text = flights.nth(i).inner_text()

                raw_prices = re.findall(
                    r"\d[\d\s.\u00a0\u202f]*\s*Kč",
                    text
                )

                for price in raw_prices:
                    value = int(re.sub(r"\D", "", price))
                    prices.append(value)

            #=====================================================
            # Fallback pokud Google změnil CSS class

            if not prices:
                print("CSS flight selector nic nenašel, používám body fallback.")

                text = page.locator("body").inner_text()

                raw_prices = re.findall(
                    r"\d[\d\s.\u00a0\u202f]*\s*Kč",
                    text
                )

                prices = [
                    int(re.sub(r"\D", "", price))
                    for price in raw_prices
                ]

            #=====================================================

            if not prices:
                return ERROR_PRICE

            print("Nalezené ceny:")
            print(sorted(set(prices)))
            print()

            return min(prices)

        finally:
            context.close()