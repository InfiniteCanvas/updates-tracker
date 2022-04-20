import argparse
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timedelta
from time import sleep

import pandas as pd
import numpy as np
from toolz import functoolz
import requests_html
from bs4 import BeautifulSoup
from alive_progress import alive_bar, alive_it

# Regex
LAST_UPDATE = re.compile(r"([Tt]hread [Uu]pdated*:)\s*([0-9\-]+)")

# Date Formats
DATE_FORMAT_THREAD = "%Y-%m-%d"

# Default args
DEFAULT_OUTPUT_FILENAME = "output.html"
DEFAULT_INPUT_FILENAME = "tracked.csv"
DEFAULT_COOKIES_FILENAME = "cookies"
DEFAULT_THREADS = 5
DEFAULT_AGE = 21
DEFAULT_RETRIES = 5
DEFAULT_DELAY = 5

# stuff to initiate later
SESSION = requests_html.HTMLSession()
COOKIES = DEFAULT_COOKIES_FILENAME
INPUT = DEFAULT_INPUT_FILENAME
OUTPUT = DEFAULT_OUTPUT_FILENAME
THREADS = DEFAULT_THREADS
AGE = DEFAULT_AGE
RETRIES = DEFAULT_RETRIES
DELAY = DEFAULT_DELAY


# helper functions
def coalesce(*arg):
    return next((item for item in arg if item is not None), None)


def GetHtml(url: str):
    response = SESSION.get(url, cookies=COOKIES)
    while response.status_code != 200:
        print(f"Getting {response.status_code}. Retrying {url}")
        response = SESSION.get(url, cookies=COOKIES)
    return response.content


def GetSoup(content: bytes, parser: str = 'html.parser'):
    return BeautifulSoup(content, parser)


def GetRawThreadUpdatedDate(soup: BeautifulSoup):
    return LAST_UPDATE.search(soup.get_text()).group(2)


def GetThreadUpdated(date_raw: str):
    if date_raw is None:
        return datetime.now() - timedelta(days=700)
    return datetime.strptime(date_raw, DATE_FORMAT_THREAD)


def BatchProcess(func, datas, threads=THREADS):
    results = []
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(func, data) for data in datas]
        for future in alive_it(as_completed(futures)):
            result = future.result()
            if result is not None:
                results.append(result)
    return results


def ProcessDfRow(row):
    (index, data) = row
    title, url, last_update = data
    actual = urlToDate(url)
    return {
        'Title': title,
        'Url': url,
        'Updated': actual,
        'Has Updated': last_update < actual
    }


def save_to_file(filepath: str, content: str, mode: str = "w+"):
    with open(filepath, mode) as file:
        file.writelines(content)


mapl = functoolz.compose_left(map, list)
urlToDate = functoolz.compose_left(GetHtml, GetSoup, GetRawThreadUpdatedDate, GetThreadUpdated)


def parse_arguments(raw_args) -> dict:
    """
    :param raw_args: Arguments to parse
    :return: Parsed arguments dictionary
    """
    parser = argparse.ArgumentParser(prog="Simple Updates Tracker for f95zone",
                                     description="Uses a simple 'tracked.csv' file to track updates.")
    parser.add_argument('-i', '--input', nargs='?', default=os.path.join(sys.path[0], DEFAULT_INPUT_FILENAME), type=str,
                        help="Set the input file for tracked games. Default is the 'tracked.csv' in the script starting directory.")
    parser.add_argument('-o', '--output', nargs='?', default=os.path.join(sys.path[0], DEFAULT_OUTPUT_FILENAME),
                        type=str,
                        help="Path to output file. Default is 'output.html' in the script starting directory.")
    parser.add_argument('-c', '--cookies', nargs='?', default=os.path.join(sys.path[0], DEFAULT_COOKIES_FILENAME),
                        type=str,
                        help="Set the cookies file for the html session. Default is the 'cookies' in the script starting directory. If no file exists, no cookie is set.")
    parser.add_argument('-t', '--threads', nargs='?', type=int, default=DEFAULT_THREADS,
                        help='Number of threads to use for fetching data. Default is 5.')
    parser.add_argument('--age', nargs='?', type=int, default=DEFAULT_AGE,
                        help='Minimum age (in days) to qualify for a check. The default checks all entries older than 7 days.')
    parser.add_argument('--retries', nargs='?', type=int, default=DEFAULT_RETRIES,
                        help='Max retries. Defaults to 5.')
    parser.add_argument('--delay', nargs='?', type=int, default=DEFAULT_DELAY,
                        help='Delay between retries in seconds. Defaults to 5 seconds.')
    parameters = vars(parser.parse_args(raw_args))

    return parameters


def InitVariables(args):
    args = parse_arguments(sys.argv[1:])
    global COOKIES, THREADS, AGE, INPUT, OUTPUT, RETRIES, DELAY
    cp = Path(args['cookies'])
    if cp.exists():
        COOKIES = coalesce(Path(args['cookies']).read_text(), None)
    else:
        COOKIES = None
    THREADS = coalesce(args['threads'], DEFAULT_THREADS)
    AGE = (datetime.now() - timedelta(days=coalesce(args['age'], DEFAULT_AGE))).strftime(DATE_FORMAT_THREAD)
    INPUT = coalesce(args['input'], DEFAULT_INPUT_FILENAME)
    OUTPUT = coalesce(args['output'], DEFAULT_OUTPUT_FILENAME)
    RETRIES = coalesce(args['retries'], DEFAULT_RETRIES)
    DELAY = coalesce(args['delay'], DEFAULT_DELAY)


if __name__ == '__main__':
    InitVariables(parse_arguments(sys.argv[1:]))
    old_df = pd.read_csv(Path(INPUT))
    # drop dupes by url and fill empty dates
    old_df.drop_duplicates(subset="Url", inplace=True)
    old_df['Updated'] = pd.to_datetime(old_df['Updated'], format=DATE_FORMAT_THREAD)
    old_df['Updated'] = old_df['Updated'].transform(
        lambda x: datetime.strptime(AGE, DATE_FORMAT_THREAD) if pd.isna(x) else x)

    # only get old entries
    new_df = old_df.copy()
    difference_df = new_df[~(new_df.Updated.dt.strftime(DATE_FORMAT_THREAD) < AGE)]
    new_df = new_df[new_df.Updated.dt.strftime(DATE_FORMAT_THREAD) < AGE]

    # get actual thread updates
    r = BatchProcess(ProcessDfRow, list(new_df.iterrows()), THREADS)
    checked = pd.DataFrame(r)
    updated = checked.copy()[checked['Has Updated']].drop(['Has Updated'], axis=1)
    df = pd.concat([checked, difference_df])

    # save results
    save_to_file(OUTPUT, f"\n<b>{datetime.utcnow()}</b>\n", 'a+')
    if len(updated) > 0:
        print("\nThese need an update:")
        print(updated.head(len(updated)))
        # make thread urls links
        updated["Url"] = updated["Url"].transform(lambda x: f'<a href="{x}" target="_blank" rel="noopener noreferrer">{x}</a>')
        save_to_file(OUTPUT, updated.to_html(index=False, escape=False), 'a+')
    else:
        print("Everything up to date!")
        save_to_file(OUTPUT, "Everything up to date!", 'a+')
    save_to_file(OUTPUT, "<br>", 'a+')

    # update tracked
    save_to_file(INPUT, df.drop(['Has Updated'], axis=1).to_csv(index=False))

