

from typing import TypedDict
from prefect import task
from prefect.logging import get_run_logger


import csv
import os
import re


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