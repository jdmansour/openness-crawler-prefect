import json
import logging
from typing import TYPE_CHECKING, Literal

import dotenv
from crawl4ai import (AsyncWebCrawler, CacheMode, CrawlerRunConfig,
                      CrawlResult, LLMConfig)
from crawl4ai.processors.pdf import (PDFContentScrapingStrategy,
                                     PDFCrawlerStrategy)
from pydantic import BaseModel, TypeAdapter

from crawl4ai_helpers import ChunkLimitedLLMExtractionStrategy
from prefect import flow, tags, task
from prefect.utilities.asyncutils import sync_compatible
from prefect.cache_policies import TASK_SOURCE, INPUTS

log = logging.getLogger(__name__)


class LMSResult(BaseModel):
    reasoning: str
    software_usage_found: bool
    error: Literal[False] = False

class ErrorBlock(BaseModel):
    index: int
    error: Literal[True] = True
    tags: list[str]
    content: str

@sync_compatible
@task(cache_policy=TASK_SOURCE+INPUTS)
async def scrape_url(url: str, prompt_template: str, arguments: dict, skip_cache=False) -> LMSResult:

    log.info(f"Scraping URL: {url} for {arguments}")
    is_pdf = False
    if "dumpFile" in url or url.endswith(".pdf"):
        # hack hack hack
        is_pdf = True

    api_key = dotenv.get_key(".env", "LLM_API_KEY")
    #base_url = "https://chat-ai.academiccloud.de/v1"
    base_url = dotenv.get_key(".env", "LLM_BASE_URL")
    provider = dotenv.get_key(".env", "LLM_PROVIDER")

    prompt = prompt_template.format(**arguments)

    if provider == "openai/llama-3.3-70b-instruct":
        extra_args = {
            "temperature": 0.0,
            "max_tokens": 800
        }
    else:
        extra_args = {
            "temperature": 1,
            # "max_completion_tokens": 800,
        }
    llm_strategy = ChunkLimitedLLMExtractionStrategy(
        llm_config=LLMConfig(provider=provider, base_url=base_url, api_token=api_key),
        schema=LMSResult.model_json_schema(),
        verbose=True,
        extraction_type="schema",
        instruction=prompt,
        chunk_token_threshold=1000,
        overlap_rate=0.05,
        apply_chunking=True,
        input_format="markdown",   # or "html", "fit_markdown"
        extra_args=extra_args,
    )

    # 2. Build the crawler config
    scraping_strategy = PDFContentScrapingStrategy() if is_pdf else None
    crawl_config = CrawlerRunConfig(
        scraping_strategy=scraping_strategy,  # type: ignore
        extraction_strategy=llm_strategy,
        cache_mode=CacheMode.DISABLED if is_pdf else CacheMode.WRITE_ONLY,
        verbose=True,
        log_console=True,
    )

    # Create a browser config if needed
    # browser_cfg = BrowserConfig(headless=True)

    crawler_strategy = PDFCrawlerStrategy() if is_pdf else None
    
    async with AsyncWebCrawler(crawler_strategy=crawler_strategy) as crawler:  # type: ignore
        # cast(AsyncLogger, crawler.logger).console.file = sys.stderr
        log.info("Scraping URL: %s", url)
        result = await crawler.arun(
            url=url,
            config=crawl_config
        )
        log.info("URL scraped: %s", url)
        if TYPE_CHECKING:
            assert isinstance(result, CrawlResult)

        # log.info("LLM usage: %s", llm_strategy.usages)
        # log.info("LLM usage: %s", llm_strategy.total_usage)
        # llm_strategy.show_usage()

        if not result.extracted_content:
            log.warning("⚠️ No content extracted")
            return LMSResult(reasoning="(No content extracted)", software_usage_found=False)


        log.info("result.error_message: %s", result.error_message)
        log.info("result.extracted_content: %s", result.extracted_content[:1000])

        try:
            data = TypeAdapter(list[LMSResult|ErrorBlock]).validate_json(
                result.extracted_content)
        except json.JSONDecodeError as e:
            log.warning(f"⚠️ JSON decoding error: {e}")
            log.warning("The extracted content might not be valid JSON.")
            log.warning("Extracted content: %s", result.extracted_content)
            raise
            return LMSResult(reasoning="(JSON decoding error)", software_usage_found=False)
        except Exception as e:
            log.warning(f"⚠️ Error validating JSON: {e}")
            log.warning("Extracted content: %s", result.extracted_content)
            raise
            return LMSResult(reasoning="(Error validating JSON)", software_usage_found=False)

        # # combine chunks into a single reasoning
        # chunks = []
        # for item in data:
        #     if isinstance(item, ErrorBlock):
        #         raise RuntimeError(
        #             f"Error in block {item.index}: {item.content}")
            
        #     chunks.append({
        #         "software_usage_found": item.software_usage_found,
        #         "reasoning": item.reasoning
        #     })

        positive: list[str] = []
        for item in data:
            if isinstance(item, ErrorBlock):
                raise RuntimeError(
                    f"Error in block {item.index}: {item.content}")
            if item.software_usage_found:
                positive.append(item.reasoning)

        usage_found = len(positive) > 0
        if usage_found:
            # reasoning = f"URL: {url};"
            reasoning = "; ".join(positive)
        else:
            # reasoning = f"URL: {url};"
            reasoning = "No mention found."

        return LMSResult(reasoning=reasoning, software_usage_found=usage_found)
