from prefect import flow, tags, task
from prefect.futures import wait
from prefect.cache_policies import DEFAULT, TASK_SOURCE, INPUTS
from prefect.assets import materialize
from typing import TypedDict
import csv
import os
import re
import logging
import time
import logging
import dotenv
from googleapiclient.discovery import build
from tasks.scraper import scrape_url  # Importing the scrape_url task
import asyncio
import json
log = logging.getLogger("baseline")

class UniversityDict(TypedDict):
    website: str
    name: str


@task
def read_universities(filename: str) -> list[UniversityDict]:

    if not os.path.exists(filename):
        raise FileNotFoundError(f"File {filename} does not exist.")

    # parse csv
    # get columns website and Hochschulname
    # remove http(s):// and www. from website
    unis: list[UniversityDict] = []
    with open(filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=",")
        for row in reader:
            # Universität
            if row.get("Hochschultyp", "").strip() != "Universität":
                continue
            # if "Hannover" not in row.get("Hochschulname", ""):
            #     # if not "Göttingen" in row.get("Hochschulname", ""):
            #     continue

            website = row["website"].strip()
            if not website:
                log.warning(f"Skipping row with empty website: {row}")
                continue
            # remove http(s):// and www.
            website = re.sub(r"^https?://(www\.)?", "", website)
            # remove trailing slash
            website = website.rstrip("/")
            # add to list
            unis.append(dict(website=website, name=row["Hochschulname"]))
            # unis.append((website, row["Hochschulname"]))

    # Make unique by name
    unis = list({uni["name"]: uni for uni in unis}.values())
    return unis

@task
def to_upper_slow(name: str) -> str:
    # time.sleep(0.01)
    time.sleep(1)
    return name.upper()


@task(cache_policy=TASK_SOURCE+INPUTS, log_prints=True)
def google_search(query: str, skip_cache=False) -> list[str]:
    print(f"Searching for {query}...")
    api_key = dotenv.get_key(".env", "GOOGLE_API_KEY")
    cse_id = dotenv.get_key(".env", "GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        log.error("Missing GOOGLE_API_KEY or GOOGLE_CSE_ID in .env file")
        return []
    service = build("customsearch", "v1", developerKey=api_key)
    res = service.cse().list(q=query, cx=cse_id, num=10).execute()

    if len(res.get('items', [])) == 0:
        log.warning(f"No results found for query: {query}")
        log.warning("response: %s", res)

    return [item['link'] for item in res.get('items', [])]

@flow(log_prints=True)
def baseline():
    input_file = '../einrichtungen/data/hochschulen.csv'
    output_file = "results_new.jsonlines"

    log = logging.getLogger("baseline")
    # log.info(f"Reading universities from {filename}")
    
    try:
        unis = read_universities(input_file)
    except FileNotFoundError as e:
        log.error(e)
        return

    # results = []
    # # log.info(f"Found {len(universities)} universities.")
    # for uni in universities:
    #     name = uni['name']
    #     results.append(to_upper_slow.submit(name))
    #     # print(name)
    #     # print(uni['name'])
    #     # log.info(f"University: {uni['name']}, Website: {uni['website']}")
    # wait(results)

    jobs = []
    for index, item in enumerate(unis):
        print(f"Processing {index + 1}/{len(unis)}: {item['name']} ({item['website']})")
        site = item["website"]
        einrichtung = item["name"]
        if index > 5:
            break

        # , "OpenOLAT", "Canvas", "Stud.IP"]:
        for software in ["Moodle"]:
        # for software in ["Moodle", "Ilias", "OpenOLAT"]:
            # if (einrichtung, software) in combos_done:
            #     log.info(f"Skipping {einrichtung} - {software}, already done")
            #     continue
            query = f"site:{site} {software}"
            r = handle_uni.submit(query, "Fasse bitte diese Seite in 2-3 Sätzen zusammen.", {"software": software, "einrichtung": einrichtung}, output_file)
            jobs.append(r)
            # print(r)
    wait(jobs)

def store_result(result, filename: str):
    with open(filename, "a") as f:
        f.write(json.dumps(result) + "\n")


@task(log_prints=True)
def handle_uni(query, prompt_template, arguments, output_file):
    output_url = "file://" + os.path.abspath(output_file)

    # Step 1: Google search
    results = google_search(query, skip_cache=False)
    store_func = materialize(output_url)(store_result)
    for result in results:
        print(result)
        x = scrape_url(url=result,
                        prompt_template="Fasse bitte diese Seite in 2-3 Sätzen zusammen.",
                        arguments={})
        print("Storing result for", arguments["einrichtung"])
        print(x)
        store_func(x.model_dump_json(), output_file)
        return x
    


if __name__ == "__main__":
    with tags("baseline"):
        baseline()
