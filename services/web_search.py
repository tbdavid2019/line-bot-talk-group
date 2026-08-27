"""2MD Fast Reader & SERP Live Web Search Service for LLM Grounding."""

from __future__ import annotations

import os
import re
import logging
from typing import List, Optional
from urllib.parse import quote
import requests

logger = logging.getLogger(__name__)

# Keywords indicating intent for real-time/live information retrieval
REALTIME_KEYWORDS = [
    "股價", "即時", "今日", "今天", "最新", "新聞", "走勢", "天氣", "匯率",
    "上市", "ipo", "股票", "報價", "市值", "財報", "營收", "盤後", "美股", "台股",
    "現價", "漲跌", "news", "price", "stock", "who is", "what happened", "current", "latest", "today"
]

SEARCH_ACTION_PREFIXES = [
    "!search", "!搜尋", "！搜尋", "!s ", "！s ", "搜尋", "幫我查", "查一下", "找一下", "請查", "請搜尋", "查詢"
]

URL_REGEX = re.compile(
    r'https?://(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b[-a-zA-Z0-9()@:%_+.~#?&/=]*',
    re.IGNORECASE
)


class WebSearchService:
    """Provides high-speed SERP live search and URL to Markdown reading via 2MD API."""

    def __init__(
        self,
        base_urls: Optional[List[str]] = None,
        timeout: int = 10
    ) -> None:
        if base_urls:
            self.base_urls = [u.rstrip('/') for u in base_urls]
        else:
            env_bases = os.getenv("WEB_SEARCH_BASE_URLS")
            if env_bases:
                self.base_urls = [u.strip().rstrip('/') for u in env_bases.split(',') if u.strip()]
            else:
                self.base_urls = [
                    "https://2md.aiurl.tw",
                    "https://2md.glsoft.ai",
                    "https://create360.ai"
                ]
        self.timeout = timeout

    def extract_urls(self, text: str) -> List[str]:
        """Extract all HTTP/HTTPS URLs from text."""
        if not text:
            return []
        return URL_REGEX.findall(text)

    def should_search(self, text: str) -> bool:
        """Determines if the text requires live web search."""
        if not text:
            return False

        lower_text = text.lower().strip()

        # Explicit search action commands or prefixes
        for prefix in SEARCH_ACTION_PREFIXES:
            if lower_text.startswith(prefix.lower()):
                return True

        # Check for real-time keywords
        for kw in REALTIME_KEYWORDS:
            if kw in lower_text:
                return True

        return False

    def search(self, query: str) -> Optional[str]:
        """
        Executes live web search across multi-tier 2MD endpoints.
        Returns Markdown formatted search results or None.
        """
        if not query:
            return None

        # Clean query if it started with command prefix
        clean_query = query
        for prefix in ['!search', '!搜尋', '！搜尋', '!s', '！s', '搜尋', '查一下', '幫我查', '查']:
            if clean_query.lower().startswith(prefix.lower()):
                clean_query = clean_query[len(prefix):].strip()
                break

        if not clean_query:
            clean_query = query.strip()

        encoded_query = quote(clean_query)

        for base_url in self.base_urls:
            try:
                # Try query path /search?q=... and /s/...
                url = f"{base_url}/search?q={encoded_query}"
                logger.info(f"Searching web via {base_url} for '{clean_query[:50]}'...")
                resp = requests.get(
                    url,
                    headers={"Accept": "text/plain"},
                    timeout=self.timeout
                )
                if resp.status_code == 200 and resp.text and not resp.text.startswith("No search results available"):
                    logger.info(f"Search successful from {base_url} (length: {len(resp.text)})")
                    return resp.text
                
                # Fallback to /s/ path
                s_url = f"{base_url}/s/{encoded_query}"
                resp2 = requests.get(
                    s_url,
                    headers={"Accept": "text/plain"},
                    timeout=self.timeout
                )
                if resp2.status_code == 200 and resp2.text and not resp2.text.startswith("No search results available"):
                    logger.info(f"Search successful from {base_url}/s/ (length: {len(resp2.text)})")
                    return resp2.text

                logger.warning(f"Search returned HTTP {resp.status_code} or no results from {base_url}")
            except Exception as e:
                logger.warning(f"Search endpoint {base_url} failed: {e}. Trying next...")

        return None

    def read_url(self, target_url: str) -> Optional[str]:
        """
        Reads and extracts clean Markdown from a single URL via 2MD API.
        """
        if not target_url or not target_url.startswith("http"):
            return None

        for base_url in self.base_urls:
            try:
                url = f"{base_url}/{target_url}"
                logger.info(f"Reading URL content via {base_url} for '{target_url}'...")
                resp = requests.get(
                    url,
                    headers={"Accept": "text/plain"},
                    timeout=self.timeout
                )
                if resp.status_code == 200 and resp.text:
                    logger.info(f"Read URL successful from {base_url} (length: {len(resp.text)})")
                    return resp.text
            except Exception as e:
                logger.warning(f"Read URL via {base_url} failed: {e}. Trying next...")

        return None

    def enrich_prompt_with_web(self, prompt: str) -> str:
        """
        Automatically detects URLs or live search queries in prompt, fetches data,
        and enriches prompt with structured web context.
        """
        urls = self.extract_urls(prompt)
        web_context_chunks: List[str] = []

        # 1. Read any URLs present in prompt
        for u in urls[:2]:  # Limit to first 2 URLs to conserve context
            content = self.read_url(u)
            if content:
                # Truncate content to 3500 chars to avoid exceeding LLM context limits
                truncated = content[:3500] + ("\n...(truncated)" if len(content) > 3500 else "")
                web_context_chunks.append(f"### [網頁內容 URL: {u}]\n{truncated}")

        # 2. If no URLs but query requires live search
        if not urls and self.should_search(prompt):
            search_results = self.search(prompt)
            if search_results:
                truncated_search = search_results[:3500]
                web_context_chunks.append(f"### [即時網路檢索結果 (Live Web Search)]:\n{truncated_search}")

        if not web_context_chunks:
            return prompt

        combined_context = "\n\n".join(web_context_chunks)
        enriched = (
            f"{prompt}\n\n"
            f"--- 🌐 即時網路檢索與網頁內容參考 ---\n"
            f"{combined_context}\n"
            f"--- 請基於上述即時網路資訊回答使用者問題，並保持客觀準確與最新資訊 ---"
        )
        return enriched
