import asyncio
import csv
import json
import os
import re
import time
from typing import TypedDict

import dotenv
from googleapiclient.discovery import build
from prefect import flow, tags, task
from prefect.cache_policies import INPUTS, TASK_SOURCE
from prefect.logging import get_run_logger
from prefect.runtime import task_run

from tasks.scraper import scrape_url


class UniversityDict(TypedDict):
    website: str
    name: str


@task
def read_universities(filename: str) -> list[UniversityDict]:
    log = get_run_logger()

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

            website = row["website"].strip()
            if not website:
                log.warning(f"Skipping row with empty website: {row}")
                continue
            # remove http(s):// and www.
            website = re.sub(r"^https?://(www\.)?", "", website)
            # remove trailing slash
            website = website.rstrip("/")
            # add to list
            unis.append({'website': website, 'name': row["Hochschulname"]})

    # Make unique by name
    unis = list({uni["name"]: uni for uni in unis}.values())
    return unis


@task
def get_done_combos(output_file: str, keys: tuple) -> set[tuple]:
    combos_done = set()
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            objs = [json.loads(line) for line in f]
            for obj in objs:
                values = tuple(obj.get(k, "") for k in keys)
                if all(values):
                    combos_done.add(values)
    return combos_done


@task
def to_upper_slow(name: str) -> str:
    # time.sleep(0.01)
    time.sleep(1)
    return name.upper()


@task(cache_policy=TASK_SOURCE+INPUTS, log_prints=True, tags=['google-search'])
def google_search(query: str) -> list[str]:
    log = get_run_logger()
    log.info(f"Searching for {query}...")
    api_key = dotenv.get_key(".env", "GOOGLE_API_KEY")
    cse_id = dotenv.get_key(".env", "GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        log.error("Missing GOOGLE_API_KEY or GOOGLE_CSE_ID in .env file")
        return []
    service = build("customsearch", "v1", developerKey=api_key)
    # with concurrency("google-search", occupy=1):
    res = service.cse().list(q=query, cx=cse_id, num=10).execute()

    if len(res.get('items', [])) == 0:
        log.warning("No results found for query: %s", query)
        log.warning("response: %s", res)

    return [item['link'] for item in res.get('items', [])]


@flow(log_prints=True)
async def baseline():
    log = get_run_logger()

    input_file = '../einrichtungen/data/hochschulen.csv'
    output_file = "results_new.jsonlines"
    prompt_template = """Finde heraus ob aus dem Text hervorgeht, dass {software} oder eine auf
    {software} basierende Software in der Einrichtung {einrichtung} genutzt wird. Antworte im
    JSON-Format. Gebe eine kurze Begründung im Feld `reasoning` an, sowie das Ergebnis
    `true` oder `false` im Feld `result`."""

    try:
        unis = read_universities(input_file)
    except FileNotFoundError as e:
        log.error(e)
        return

    combos_done = get_done_combos(
        output_file, keys=("einrichtung", "software"))
    log.info("Found %d completed combos.", len(combos_done))

    # Zähle alle Unis
    total_unis = len(unis)
    log.info("Total universities to process: %d", total_unis)

    # unique universities
    unique_unis = {item["name"] for item in unis}
    log.info("Total unique universities: %d", len(unique_unis))

    # Zähle alle Unis die in combos_done sind
    unis_done = []
    unis_todo = []
    for item in unis:
        if (item["name"], "Moodle") in combos_done and (item["name"], "Ilias") in combos_done and (item["name"], "OpenOLAT") in combos_done:
            unis_done.append(item)
        else:
            unis_todo.append(item)
    total_unis_done = len(unis_done)
    print(f"Total universities already processed: {total_unis_done}")

    unis = unis_todo
    # unis = unis[0:20]

    tasks = []
    for index, item in enumerate(unis):
        site = item["website"]
        einrichtung = item["name"]

        for software in ["Moodle", "Ilias", "OpenOLAT"]:
            query = f"site:{site} {software}"
            arguments = {"einrichtung": einrichtung, "software": software}
            print(
                f"Processing {index + 1}/{len(unis)}: {item['name']}, {software}")

            # Erstelle async task statt submit
            task = handle_uni(query, prompt_template=prompt_template,
                            arguments=arguments, output_file=output_file)
            tasks.append(task)
    
    # Führe alle Tasks parallel aus
    await asyncio.gather(*tasks)


def _handle_uni_task_name():
    task_name = task_run.task_name
    parameters = task_run.parameters
    arguments = parameters.get("arguments", {})
    new_name = f"{task_name}-{arguments.get('einrichtung','unknown')}-{arguments.get('software','unknown')}"
    new_name = new_name.replace(" ", "-").lower()
    return new_name


@task(log_prints=True, task_run_name=_handle_uni_task_name, tags=['handle-uni'], cache_policy=TASK_SOURCE+INPUTS)
async def handle_uni(query, prompt_template, arguments, output_file):
    # Google search
    urls = google_search(query)

    combined_verdict = False
    scraping_results = []
    urls = urls[:5]
    
    for url in urls:
        result = await scrape_url(url=url,
                                 prompt_template=prompt_template,
                                 arguments=arguments)

        scraping_results.append(result)
        if result.result:
            combined_verdict = True
            # exit early
            break

    combined_inputs = [
        {"url": url, "result": result.result, "reasoning": result.reasoning}
        for url, result in zip(urls, scraping_results)
    ]

    if not combined_verdict:
        summary = "No evidence found"
    else:
        summary = "Evidence found"

    combined_reasoning = {
        'summary': summary,
        'inputs': combined_inputs,
    }

    res_item = {
        "result": combined_verdict,
    }
    res_item.update(arguments)
    res_item['reasoning'] = combined_reasoning

    with open(output_file, "a") as f:
        f.write(json.dumps(res_item, ensure_ascii=False) + "\n")

    return res_item


if __name__ == "__main__":
    with tags("baseline"):
        asyncio.run(baseline())
