"""2MD Fast Reader, SERP Live Web Search, and Live Meteorology Service for LLM Grounding."""

from __future__ import annotations

import os
import re
import logging
from typing import List, Optional, Dict
from urllib.parse import quote
import requests

logger = logging.getLogger(__name__)

LOCATION_MAP: Dict[str, str] = {
    "蘭嶼": "Lanyu",
    "綠島": "Green_Island",
    "台北": "Taipei",
    "臺北": "Taipei",
    "新北": "New_Taipei",
    "基隆": "Keelung",
    "桃園": "Taoyuan",
    "新竹": "Hsinchu",
    "苗栗": "Miaoli",
    "台中": "Taichung",
    "臺中": "Taichung",
    "彰化": "Changhua",
    "南投": "Nantou",
    "雲林": "Yunlin",
    "嘉義": "Chiayi",
    "台南": "Tainan",
    "臺南": "Tainan",
    "高雄": "Kaohsiung",
    "屏東": "Pingtung",
    "恆春": "Hengchun",
    "墾丁": "Hengchun",
    "宜蘭": "Yilan",
    "花蓮": "Hualien",
    "台東": "Taitung",
    "臺東": "Taitung",
    "澎湖": "Penghu",
    "金門": "Kinmen",
    "連江": "Matsu",
    "馬祖": "Matsu",
    "東京": "Tokyo",
    "大阪": "Osaka",
    "京都": "Kyoto",
    "沖繩": "Okinawa",
    "福岡": "Fukuoka",
    "首爾": "Seoul",
    "香港": "Hong_Kong",
    "新加坡": "Singapore",
    "紐約": "New_York",
    "倫敦": "London",
}

WEATHER_KEYWORDS = ["天氣", "氣溫", "降雨", "下雨", "風浪", "氣象", "預報", "溫度", "weather"]

REALTIME_KEYWORDS = [
    "股價", "即時", "今日", "今天", "最新", "新聞", "走勢", "匯率",
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
    """Provides high-speed SERP live search, URL to Markdown reading, and instant meteorological telemetry."""

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

    def extract_location(self, text: str) -> Optional[str]:
        """Extract matched location name or English code from text."""
        if not text:
            return None
        for name, loc_code in LOCATION_MAP.items():
            if name in text:
                return loc_code
        return None

    def should_search_weather(self, text: str) -> bool:
        """Determines if the query is asking about weather."""
        if not text:
            return False
        lower_text = text.lower()
        has_weather_kw = any(kw in lower_text for kw in WEATHER_KEYWORDS)
        has_location = any(loc in text for loc in LOCATION_MAP)
        return has_weather_kw and (has_location or "天氣" in text or "氣象" in text)

    def should_search(self, text: str) -> bool:
        """Determines if the text requires live web search or telemetry."""
        if not text:
            return False

        lower_text = text.lower().strip()

        # Weather query check
        if self.should_search_weather(text):
            return True

        # Explicit search action commands or prefixes
        for prefix in SEARCH_ACTION_PREFIXES:
            if lower_text.startswith(prefix.lower()):
                return True

        # Check for real-time keywords
        for kw in REALTIME_KEYWORDS:
            if kw in lower_text:
                return True

        return False

    def get_weather(self, location: str) -> Optional[str]:
        """
        Fetches live meteorological telemetry for a given location or Chinese place name.
        """
        if not location:
            return None

        # Resolve location code
        loc_code = self.extract_location(location) or location.strip().replace(" ", "_")

        try:
            url = f"https://wttr.in/{loc_code}?lang=zh-tw&format=j1"
            logger.info(f"Fetching meteorological telemetry for {location} ({loc_code})...")
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                current = data.get("current_condition", [{}])[0]
                weather_desc = current.get("lang_zh-tw", [{}])[0].get(
                    "value", current.get("weatherDesc", [{}])[0].get("value", "晴朗")
                )
                temp = current.get("temp_C", "--")
                feels_like = current.get("FeelsLikeC", "--")
                humidity = current.get("humidity", "--")
                wind_speed = current.get("windspeedKmph", "--")
                wind_dir = current.get("winddir16Point", "--")
                uv_index = current.get("uvIndex", "--")

                # Today forecast
                today_forecast = data.get("weather", [{}])[0]
                max_temp = today_forecast.get("maxtempC", "--")
                min_temp = today_forecast.get("mintempC", "--")

                return (
                    f"【即時氣象觀測資料 - {location}】\n"
                    f"- 即時天氣狀況：{weather_desc}\n"
                    f"- 當前氣溫：{temp}°C (體感溫度：{feels_like}°C)\n"
                    f"- 今日最高 / 最低溫：{max_temp}°C / {min_temp}°C\n"
                    f"- 相對濕度：{humidity}%\n"
                    f"- 風速與風向：{wind_speed} km/h (風向 {wind_dir})\n"
                    f"- 紫外線指數：{uv_index}\n"
                )
        except Exception as e:
            logger.warning(f"Failed to fetch weather for {location}: {e}")

        return None

    def search(self, query: str) -> Optional[str]:
        """
        Executes live web search across multi-tier 2MD endpoints.
        Returns Markdown formatted search results or None.
        """
        if not query:
            return None

        # Clean query if it started with command prefix
        clean_query = query
        for prefix in ['!search', '!搜尋', '！搜尋', '!s', '！s', '搜尋', '幫我查', '查一下', '找一下', '請查', '請搜尋', '查詢']:
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
        Automatically detects URLs, weather queries, or live search queries in prompt, fetches data,
        and enriches prompt with structured web context.
        """
        urls = self.extract_urls(prompt)
        web_context_chunks: List[str] = []

        # 1. Read any URLs present in prompt
        for u in urls[:2]:
            content = self.read_url(u)
            if content:
                truncated = content[:3500] + ("\n...(truncated)" if len(content) > 3500 else "")
                web_context_chunks.append(f"### [網頁內容 URL: {u}]\n{truncated}")

        # 2. If asking about weather, fetch live telemetry
        if self.should_search_weather(prompt):
            weather_data = self.get_weather(prompt)
            if weather_data:
                web_context_chunks.append(f"### [即時氣象觀測數據 (Live Weather Data)]:\n{weather_data}")

        # 3. Search web via 2MD for real-time grounding
        if not urls and (self.should_search(prompt) or not web_context_chunks):
            search_results = self.search(prompt)
            if search_results:
                truncated_search = search_results[:3500]
                web_context_chunks.append(f"### [即時網路檢索結果 (Live Web Search)]:\n{truncated_search}")

        if not web_context_chunks:
            return prompt

        combined_context = "\n\n".join(web_context_chunks)
        enriched = (
            f"{prompt}\n\n"
            f"--- 🌐 即時網路檢索與即時資料參考 ---\n"
            f"{combined_context}\n"
            f"--- 請直接依據上述即時資訊親切且準確地回答使用者問題，提供具體數值與出行/生活建議，嚴禁向使用者說「沒有即時資料」 ---"
        )
        return enriched
