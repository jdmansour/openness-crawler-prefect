import asyncio
import json
import os
import textwrap
import time

import dotenv
from googleapiclient.discovery import build
from prefect import flow, tags, task
from prefect.artifacts import create_markdown_artifact
from prefect.cache_policies import INPUTS, TASK_SOURCE
from prefect.logging import get_run_logger
from prefect.runtime import task_run

from read_universities import read_universities
from tasks.scraper import scrape_url


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
async def baseline() -> None:
    log = get_run_logger()

    # import definitions.openaccess as mod
    # import definitions.open_lms as mod
    from definitions.openaccess import OpenAccess as mod
    # from definitions.open_lms import OpenLMS as mod

    # mod = definitions.openaccess

    output_file = mod.output_file
    combo_keys = mod.combo_keys
    query_template = mod.query_template
    prompt_template = mod.prompt_template
    load_institutions = mod.load_institutions
    make_combos = mod.make_combos

    try:
        unis = load_institutions()
        unis_dict = {uni["name"]: uni for uni in unis}
    except FileNotFoundError as e:
        log.error(e)
        return

    # Filter: only universities with "Humboldt" in name
    # unis = [uni for uni in unis if "Humboldt" in uni["name"]]

    uni_names = [uni['name'] for uni in unis]
    all_combos = make_combos(uni_names)

    combos_done = get_done_combos(output_file, keys=combo_keys)
    combos_todo = all_combos - combos_done

    print("Total of %d inputs", len(all_combos))
    print("Already done: %d", len(combos_done))
    print("Remaining: %d", len(combos_todo))

    # # Limit to 10 combos
    # combos_todo = list(combos_todo)[:10]

    tasks = []
    for i, combo in enumerate(combos_todo):
        arguments = dict(zip(combo_keys, combo))
        einrichtung = arguments["einrichtung"]
        item = unis_dict[einrichtung]

        values: dict = arguments.copy()
        values.update(item)

        # query = f"site:{website} {arguments['software']}"
        query = query_template.format(**values)
        print(f"Processing {i + 1}/{len(combos_todo)}: {combo}")

        task = handle_uni(query, prompt_template=prompt_template,
                          arguments=arguments, output_file=output_file)
        tasks.append(task)
    
    # Führe alle Tasks parallel aus
    await asyncio.gather(*tasks)


def _handle_uni_task_name():
    task_name = task_run.task_name
    parameters = task_run.parameters
    arguments = parameters.get("arguments", {})

    new_name = task_name
    for v in arguments.values():
        new_name += '-' + str(v)
    new_name = new_name.replace(" ", "-").lower()
    return new_name


@task(log_prints=True, task_run_name=_handle_uni_task_name, tags=['handle-uni'])
async def handle_uni(query: str, prompt_template: str, arguments: dict[str, str], output_file: str) -> dict:
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

    # Create prefect artifact (markdown report)
    prompt = prompt_template.format(**arguments)
    args_markdown = "\n".join(f"    - {k}: {v}" for k, v in arguments.items())
    markdown = textwrap.dedent(f"""\
        # handle_uni results
        - **Query:** {query}
        - **Prompt:** {prompt}
        - **Arguments:**
        {args_markdown}
        - **Result:** {combined_verdict}
        - **Reasoning:**

        ## Inputs:
        Analyzed the following URLs:
        """)
    
    for url, result in zip(urls, scraping_results):
        markdown += textwrap.dedent(f"""\
            - **URL:** {url}
              **Result:** {result.result}
              **Reasoning:** {result.reasoning}
            """)

    description = f"Results for {arguments['einrichtung']}"

    await create_markdown_artifact(
        markdown=markdown,
        key="handle-uni-results",
        description=description
    )  # type: ignore

    # Return result as JSON
    combined_inputs = [
        {"url": url, "result": result.result, "reasoning": result.reasoning}
        for url, result in zip(urls, scraping_results)
    ]

    if not combined_verdict:
        summary = "No evidence found"
    else:
        summary = "Evidence found"

    res_item: dict = {
        "result": combined_verdict,
    }
    res_item.update(arguments)
    res_item['reasoning'] = {
        'summary': summary,
        'inputs': combined_inputs,
    }

    with open(output_file, "a", encoding='utf-8') as f:
        f.write(json.dumps(res_item, ensure_ascii=False) + "\n")

    return res_item


if __name__ == "__main__":
    with tags("baseline"):
        asyncio.run(baseline())
