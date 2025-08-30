import logging
log = logging.getLogger(__name__)

from crawl4ai import LLMExtractionStrategy


class ChunkLimitedLLMExtractionStrategy(LLMExtractionStrategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        max_chunks = 5

        self.max_chunks = max_chunks

        # self.chunk_warning_threshold = chunk_warning_threshold
        # self.chunk_count = 0
        # self.warnings_issued = []

    def _merge(self, documents, chunk_token_threshold, overlap) -> list[str]:
        """Override merge method to implement hard chunk limiting"""
        merged = super()._merge(documents, chunk_token_threshold, overlap)
        chunk_count = len(merged)
        if chunk_count > self.max_chunks:
            log.warning(f"Content would generate {chunk_count} chunks, limiting to {self.max_chunks}")
            # Implement truncation or alternative processing
            merged = merged[:self.max_chunks]
            # self.warnings_issued.append(f"Content truncated to {self.max_chunks} chunks")
        return merged