ERROR_PRICE = 999_999_999

#=====================================================
#===========        S C R A P I N G        ===========

import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
cookies_handled = False

def open_momondo_detail(page, price):
    print(f"\tHledám Momondo detail pro cenu {price:_} Kč...")

    handle_cookies(page)

    for attempt in range(2):
        results = page.locator("div.Fxw9-result-item-container")
        count = results.count()

        print(f"\tPokus {attempt + 1}: nalezeno výsledků: {count}")

        for i in range(count):
            result = results.nth(i)

            try:
                text = result.inner_text()
                raw_prices = re.findall(r"\d[\d\s.\u00a0]*\s*Kč", text)
                result_prices = [int(re.sub(r"\D", "", value)) for value in raw_prices]
            except Exception:
                continue

            if price not in result_prices:
                continue

            print(f"\tNalezen správný výsledek #{i + 1}.")

            select_text = result.get_by_text("Zvolit", exact=True)

            if select_text.count() == 0:
                print("\tTlačítko Zvolit nenalezeno.")
                continue

            print("\tKlikám na Zvolit...")

            try:
                select_text.first.scroll_into_view_if_needed()
                select_text.first.click(timeout=10_000)
            except Exception as e:
                print(f"\tChyba při kliknutí na Zvolit: {e}")
                return None

            print("\tZvolit kliknuto.")
            return page

        if attempt == 0:
            print(f"\tCena {price:_} Kč mezi výsledky nenalezena.")
            print("\tČekám dalších 10 sekund na donačtení výsledků...")
            page.wait_for_timeout(10_000)

    # Přesná PRICE nebyla nalezena -> použijeme první výsledek
    print(f"\tVýsledek s cenou {price:_} Kč nenalezen ani na druhý pokus.")
    print("\tPoužívám první (nejvrchnější) výsledek.")

    results = page.locator("div.Fxw9-result-item-container")

    if results.count() == 0:
        print("\tNenalezen žádný výsledek.")
        return None

    first_result = results.first

    try:
        text = first_result.inner_text()
        raw_prices = re.findall(r"\d[\d\s.\u00a0]*\s*Kč", text)
        result_prices = [int(re.sub(r"\D", "", value)) for value in raw_prices]

        print(f"\tCeny prvního výsledku: {result_prices}")
    except Exception:
        pass

    select_text = first_result.get_by_text("Zvolit", exact=True)

    if select_text.count() == 0:
        print("\tU prvního výsledku nebylo nalezeno tlačítko Zvolit.")
        return None

    print("\tKlikám na Zvolit u prvního výsledku...")

    try:
        select_text.first.scroll_into_view_if_needed()
        select_text.first.click(timeout=10_000)
    except Exception as e:
        print(f"\tChyba při kliknutí na Zvolit: {e}")
        return None

    print("\tZvolit prvního výsledku kliknuto.")
    return page


def get_real_price(detail_page, wait_time):
    if detail_page is None:
        print("\tNepodařilo se otevřít Momondo detail.")
        return ERROR_PRICE

    print("\tHledám cenu s odbaveným zavazadlem...")

    try:
        baggage_text = detail_page.get_by_text("Odbavené zavazadlo", exact=True)
        baggage_text.first.wait_for(state="visible", timeout=10_000)

    except PlaywrightTimeoutError:
        print("\tText 'Odbavené zavazadlo' nenalezen.")
        return ERROR_PRICE

    print("\t'Odbavené zavazadlo' nalezeno.")

    element = baggage_text.first

    # Postupně procházet rodiče směrem nahoru
    for level in range(1, 10):
        try:
            parent = element.locator(f"xpath=ancestor::*[{level}]")
            text = parent.inner_text(timeout=2_000)

        except Exception:
            continue

        normalized_text = " ".join(text.split())

        print(f"\tParent {level}: {normalized_text[:200]}")

        # Rodič musí obsahovat jak název, tak cenu
        if "Odbavené zavazadlo" not in text:
            continue

        raw_prices = re.findall(
            r"\d[\d\s.\u00a0]*\s*Kč",
            text
        )

        if not raw_prices:
            continue

        prices = [
            int(re.sub(r"\D", "", price))
            for price in raw_prices
        ]

        real_price = min(prices)

        print(f"\tNalezena karta odbaveného zavazadla.")
        print(f"\tNalezené ceny v kartě: {prices}")
        print(f"\tPRICE_REAL: {real_price:_} Kč")

        return real_price

    print("\tNenalezena cena odbaveného zavazadla.")

    return ERROR_PRICE




def momondo_scraper(url: str, wait_time: int = 10000) -> tuple[int, int, bool]:
    global cookies_handled

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="chrome", args=["--start-minimized"])

        try:
            page = browser.new_page(locale="cs-CZ", viewport={"width": 1920, "height": 1080})

            page.goto(url, wait_until="domcontentloaded", timeout=60_000)

            handle_cookies(page)

            if "/help/bots.html" in page.url:
                return ERROR_PRICE, ERROR_PRICE, False

            try:
                page.wait_for_function(r"""() => /\d[\d\s.]*\s*Kč/.test(document.body.innerText)""", timeout=30_000)
            except PlaywrightTimeoutError:
                return ERROR_PRICE, ERROR_PRICE, False

            page.wait_for_timeout(wait_time)

            text = page.locator("body").inner_text()
            raw_prices = re.findall(r"\d[\d\s.\u00a0]*\s*Kč", text)
            prices = [int(re.sub(r"\D", "", price)) for price in raw_prices]

            if not prices:
                return ERROR_PRICE, ERROR_PRICE, False

            price = min(prices)

            detail_page = open_momondo_detail(page, price)

            if detail_page is None:
                print("\tNepodařilo se otevřít Momondo detail.")
                print("\tPoužívám PRICE také jako PRICE_REAL.")
                price_real = price
                confirmed = False
            else:
                price_real = get_real_price(detail_page, wait_time)
                confirmed = price_real != ERROR_PRICE

            print(f"\n\tPRICE:      {price:_} Kč")
            print(f"\tPRICE_REAL: {price_real:_} Kč")
            print(f"\tCONFIRMED:  {confirmed}")

            cookies_handled = False
            return price, price_real, confirmed

        finally:
            cookies_handled = False
            browser.close()






def handle_cookies(page):
    global cookies_handled
    if cookies_handled:
        print("\tCookies už byly vyřešeny, přeskakuji.")
        return True

    print("\tKontroluji cookies...")

    try:
        text = page.get_by_text("Zamítnout vše", exact=True)

        text.first.wait_for(
            state="visible",
            timeout=10_000
        )

        button = text.first.locator("xpath=ancestor::button[1]")

        print("\tCookie dialog nalezen - klikám na 'Zamítnout vše'.")

        button.click(timeout=5_000)

        text.first.wait_for(
            state="hidden",
            timeout=5_000
        )

        cookies_handled = True

        print("\tCookies zamítnuty.")
        return True

    except PlaywrightTimeoutError:
        print("\tCookie dialog nenalezen.")
        return False

    except Exception as e:
        print(f"\tChyba při zavírání cookies: {e}")
        return False    
    
    
    
    
    
    
    
