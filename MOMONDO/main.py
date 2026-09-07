from scrape_momondo import *
import pandas as pd
from datetime import date, datetime
from itertools import product
from pathlib import Path


MIN_TRIP_LENGTH = 21 # days

BASE_URL = "https://www.momondo.cz/flight-search"
URL_TAIL = "4adults?fs=cabin%3De%3Bprice%3D-30000%3Bstops%3D1&ucs=rpvfxn&sort=price_a"


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

columns = ["IN", "OUT", "IN-DATE", "OUT-DATE", "LENGTH", "PRICE", "URL", "SCRAPED"]

SCRAPES_DIR = Path(__file__).parent / "scrapes"
SCRAPES_DIR.mkdir(exist_ok=True)

FILE_NAME = SCRAPES_DIR / f"momondo_{datetime.now().strftime('%Y_%m_%d')}.csv"

MAX_LOOPS = 999
SCRAPE_TIME = 12_000 # [ms]


def load_df(file_name=FILE_NAME):
    if file_name.exists():
        df = pd.read_csv(file_name)
        print(f"Loaded: {file_name}")
    else:
        df = pd.DataFrame(columns=columns)
        print(f"Not found: {file_name}")

    return df


def scrape(file_name=FILE_NAME):
    df = load_df(file_name)

    for i, (cz_loc_1, cz_loc_2, date_in, date_out, jap_in, jap_out) in enumerate(get_combinations(), start=1):
        print(f"------   Scrape {i}")

        url = f"{BASE_URL}/{cz_loc_1}-{jap_in}/{date_in}/{jap_out}-{cz_loc_2}/{date_out}/{URL_TAIL}"
        print(url)

        if url in df["URL"].values:
            print("\t\t URL ALREADY IN DF, SKIPPING.")
            continue

        price = momondo_scraper(url, wait_time=SCRAPE_TIME)

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
            "URL": url,
            "SCRAPED": datetime.now()
        }

        print(f"\t Price: {price:_}")
        df.loc[len(df)] = new_row

        df.to_csv(file_name, index=False, encoding="utf-8-sig")

        if i >= MAX_LOOPS:
            break

    df = df.sort_values(by="PRICE", ascending=True)
    df.to_csv(file_name, index=False, encoding="utf-8-sig")
    
    
scrape()