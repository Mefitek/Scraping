from scrape_momondo import *
import pandas as pd
from datetime import date, datetime
from itertools import product
from pathlib import Path
import matplotlib.pyplot as plt

MIN_TRIP_LENGTH = 21 # days
MAX_PRICE = 25_000

BASE_URL = "https://www.momondo.cz/flight-search"
URL_TAIL = f"4adults?fs=cabin%3De%3Bprice%3D-{int(MAX_PRICE)}%3Bstops%3D1&ucs=rpvfxn&sort=price_a"

#=====================================================
#=====================================================
#============        C H O I C E S        ============

CZ_LIST_ODLET = ["VIE", "BUD", "PRG"]
CZ_LIST_PRILET = ["VIE", "BUD", "PRG"]

JAP_IN_LIST = ["OSA"]
JAP_OUT_LIST = ["TYO"]

DATE_IN_LIST = [
    date(2027, 5, 6),
    date(2027, 5, 7),
    date(2027, 5, 8),
    date(2027, 5, 9),
    date(2027, 5, 10),
]

DATE_OUT_LIST = [
    date(2027, 5, 28),
    date(2027, 5, 29),
    date(2027, 5, 30),
    date(2027, 5, 31),
    date(2027, 6, 1),
    date(2027, 6, 2),
]

def get_combinations():
    combinations = product(
        CZ_LIST_ODLET,
        CZ_LIST_PRILET,
        DATE_IN_LIST,
        DATE_OUT_LIST,
        JAP_IN_LIST,
        JAP_OUT_LIST,
    )
    
    valid_combinations = (
        combination
        for combination in combinations
        if (combination[3] - combination[2]).days >= MIN_TRIP_LENGTH
    )

    return valid_combinations
    

#=====================================================
#===========            M A I N            ===========
#=====================================================


# =====================    MOMONDO    =====================
SCRAPES_DIR_MOMONDO = Path(__file__).parent / "scrapes_momondo"
SCRAPES_DIR_MOMONDO.mkdir(exist_ok=True)

FILE_NAME_MOMONDO = SCRAPES_DIR_MOMONDO / f"momondo_{datetime.now().strftime('%Y_%m_%d')}.csv"

SCRAPE_TIME_MOMONDO = 16_000 # [ms]
# =========================================================




columns = ["IN", "OUT", "IN-DATE", "OUT-DATE", "LENGTH", "PRICE", "PRICE_REAL", "CONFIRMED", "URL", "SCRAPED"]


def load_df(file_name):
    if file_name.exists():
        df = pd.read_csv(file_name)
        print(f"Loaded: {file_name}")
    else:
        df = pd.DataFrame(columns=columns)
        print(f"Not found: {file_name}")

    return df


def scrape_momondo(file_name=FILE_NAME_MOMONDO):
    df = load_df(file_name)

    for i, (cz_loc_1, cz_loc_2, date_in, date_out, jap_in, jap_out) in enumerate(get_combinations(), start=1):
        print(f"------   Scrape {i}")

        url = f"{BASE_URL}/{cz_loc_1}-{jap_in}/{date_in}/{jap_out}-{cz_loc_2}/{date_out}/{URL_TAIL}"
        print(url)

        if url in df["URL"].values:
            print("\t\t URL ALREADY IN DF, SKIPPING.")
            continue

        price, real_price, confirmed = momondo_scraper(url, wait_time=SCRAPE_TIME_MOMONDO)

        if price == ERROR_PRICE:
            print("\t\t NASTAL ERROR BĚHEM SCRAPINGU, KONČÍM")
            break

        new_row = {
            "IN": f"{cz_loc_1}-{jap_in}",
            "OUT": f"{jap_out}-{cz_loc_2}",
            "IN-DATE": date_in,
            "OUT-DATE": date_out,
            "LENGTH": (date_out - date_in).days,
            "PRICE": price,
            "PRICE_REAL": real_price,
            "CONFIRMED": confirmed,
            "URL": url,
            "SCRAPED": datetime.now()
        }

        print(f"\t Price: {price:_} | Real price: {real_price:_}")

        df.loc[len(df)] = new_row
        df = df.sort_values(by="PRICE_REAL", ascending=True)
        df.to_csv(file_name, index=False, encoding="utf-8-sig")

    df = df.sort_values(by="PRICE_REAL", ascending=True)
    df.to_csv(file_name, index=False, encoding="utf-8-sig")









from matplotlib.ticker import MultipleLocator

def graph_momondo(folder=SCRAPES_DIR_MOMONDO):
    folder = Path(folder)

    data = []

    for file in folder.glob("momondo_*.csv"):
        try:
            date_str = file.stem.replace("momondo_", "")
            scrape_date = datetime.strptime(date_str, "%Y_%m_%d").date()
        except ValueError:
            continue

        df = pd.read_csv(file)

        if "PRICE" not in df.columns or df.empty:
            continue
        if "PRICE_REAL" in df.columns:
            prices = pd.to_numeric(df["PRICE_REAL"], errors="coerce").dropna()
        else:
            prices = pd.to_numeric(df["PRICE"], errors="coerce").dropna()

        if prices.empty:
            continue

        data.append({
            "date": scrape_date,
            "min_price": prices.min(),
            "avg_price": prices.mean(),
        })

    if not data:
        print("Nenalezena žádná použitelná data.")
        return

    data = sorted(data, key=lambda x: x["date"])

    first_date = data[0]["date"]

    days = [(item["date"] - first_date).days for item in data]
    min_prices = [item["min_price"] for item in data]
    avg_prices = [item["avg_price"] for item in data]

    plt.figure(figsize=(12, 6))

    plt.plot(days, min_prices, marker="o", label="Nejnižší cena")
    plt.plot(days, avg_prices, marker="o", label="Průměrná cena")

    plt.xlabel("Den od začátku scrapování")
    plt.ylabel("Cena [Kč]")
    plt.title("Vývoj cen Momondo")
    plt.xticks(days)

    ax = plt.gca()

    # Hlavní čáry po 500 Kč, vedlejší po 100 Kč
    ax.yaxis.set_major_locator(MultipleLocator(500))
    ax.yaxis.set_minor_locator(MultipleLocator(100))

    # Hlavní i vedlejší mřížka
    ax.grid(which="major", alpha=0.4)
    ax.grid(which="minor", alpha=0.15)

    plt.legend()
    plt.tight_layout()
    plt.show()


scrape_momondo()
# graph_momondo()