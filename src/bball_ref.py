from bs4 import BeautifulSoup
from typing import List, Tuple

import pandas as pd
import random
import requests
import string
import time


def get_all_players(save_results: bool = True) -> pd.DataFrame:
    """
    Scrape basic data for all past and present players.

    Args:
        save_results: Flag to save results to a csv.

    Returns:
        pd.DataFrame: data frame containing player name, stats, url, active status, and HOF status.
    """
    alphabet = string.ascii_lowercase
    df_list = []

    for letter in alphabet:
        url = f"https://www.basketball-reference.com/players/{letter}/"
        # add delay to avoid triggering anti-scraping protections
        time.sleep(random.uniform(2, 5))
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Request failed for letter '{letter}': {e}")
            return [], []
        soup = BeautifulSoup(response.content, "html.parser")

        # the first row is column names
        tr = soup.find_all("tr")
        if not tr:
            print(f"No data found for letter '{letter}'")
            return pd.DataFrame()

        headers = tr[0].get_text().strip().split("\n")
        tr = tr[1:]

        raw_data = []
        for row in tr:
            # scraped columns
            th = row.find_all("th")[0]
            name = th.get_text()
            stats = [td.get_text() for td in row.find_all("td")]

            # additional columns
            link = th.find_all("a")[0]["href"] if (len(th.find_all("a")) == 1) else ""
            is_active = len(th.find_all("strong"))
            is_hof = name[-1] == "*"
            raw_data.append([name.rstrip("*")] + stats + [link, is_active, is_hof])

        print(
            f"{str(len(raw_data)).rjust(4)} rows scraped for last names ending in '{letter}'"
        )
        df_list += raw_data

    print(f"{len(df_list)} rows scraped in total")
    df = pd.DataFrame(
        df_list, columns=[h.lower() for h in headers] + ["url", "is_active", "is_hof"]
    )
    if save_results:
        df.to_csv("data/all_players.csv", index=False)
        print("saved output to data/all_players.csv")

    return df


def get_table(soup: BeautifulSoup, div_id: str) -> pd.DataFrame:
    """
    Extracts stats table from player page based on `div_id`.

    Args:
        soup: Parsed HTML soup of the player page.
        div_id: ID of the div containing the table to be scraped.

    Returns:
        pd.DataFrame: DataFrame of the scraped table.
    """

    # the id should only appear once, so .find is used for conciseness
    table_div = soup.find("div", id=div_id)

    # table may be hidden in comments
    if not table_div:
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            if div_id in comment:
                comment_soup = BeautifulSoup(comment, "html.parser")
                table_div = comment_soup.find("div", id=div_id)
                if table_div:
                    break

    if not table_div or not table_div.thead or not table_div.tbody:
        return None

    headers = table_div.thead.find_all("th")
    rows = table_div.tbody.find_all("tr")

    stats_table = {}

    # first column uses <th>
    stats_table[headers[0].get_text()] = []
    for row in rows:
        stats_table[headers[0].get_text()].append(
            row.find("th", {"data-stat": headers[0].get("data-stat")}).get_text()
        )

    # other columns use <td>
    for th in headers[1:]:
        stats_table[th.get_text()] = []
        for row in rows:
            stats_table[th.get_text()].append(
                row.find("td", {"data-stat": th.get("data-stat")}).get_text()
            )

    return pd.DataFrame(stats_table)
