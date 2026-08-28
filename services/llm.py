"""Unified LLM Service supporting Primary (nen.com.tw), Fallback (Groq), and Gemini with Autonomous Web Tools."""

from __future__ import annotations

import os
import json
import logging
import requests
from typing import Any, List, Dict, Optional

from services.web_search import WebSearchService

logger = logging.getLogger(__name__)

AVAILABLE_TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'search_web',
            'description': 'Search live web using 2MD SERP search engine to get real-time information, stock prices, news, facts, and website URLs.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {'type': 'string', 'description': 'The search query to look up'}
                },
                'required': ['query']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'read_web_page',
            'description': 'Read and extract full Markdown content from a specific web URL via 2MD Fast Reader.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'url': {'type': 'string', 'description': 'The target web page URL to read'}
                },
                'required': ['url']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_live_weather',
            'description': 'Get live real-time weather, temperature, humidity, wind speed, UV index, and forecast for any city or location (e.g. 蘭嶼, 綠島, 台北, 高雄, 東京).',
            'parameters': {
                'type': 'object',
                'properties': {
                    'location': {'type': 'string', 'description': 'The city, town, island, or location name'}
                },
                'required': ['location']
            }
        }
    }
]

SYSTEM_GROUNDING_PROMPT = (
    "你是一個全知、專業、親切且具備 2MD 高速即時網路搜尋、網頁閱讀與即時氣象觀測能力的 AI 智慧助理。\n"
    "【重要守則】:\n"
    "1. 必須一律使用「繁體中文（台灣習慣用語）」回答，嚴禁使用簡體中文或擅自使用英文，除非使用者明確要求英文。\n"
    "2. 當使用者詢問最新科技產品、手機行情/價格/規格、股票即時報價、即時新聞、匯率或任何真實世界事實時，請務必主動調用 search_web 等工具獲取最新真實資料。\n"
    "3. 嚴禁推托「我沒有即時資料」或「我是 AI 無法獲取行情」。請根據搜尋結果直接給出清晰、明確且具體的價格、規格或客觀事實分析。"
)


class LLMResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def __str__(self) -> str:
        return self.text


class LLMService:
    def __init__(
        self,
        primary_base_url: Optional[str] = None,
        primary_model: Optional[str] = None,
        primary_api_key: Optional[str] = None,
        fallback_base_url: Optional[str] = None,
        fallback_model: Optional[str] = None,
        fallback_api_key: Optional[str] = None,
        timeout: int = 60,
        enable_web_search: bool = True
    ) -> None:
        # 1. Primary endpoint (Default: nen.com.tw / gpt-5.6-luna or OpenAI official if key provided)
        env_llm_key = os.getenv("LLM_API_KEY")
        env_openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("ASR_OPENAI_API_KEY")

        if primary_base_url:
            self.primary_base_url = primary_base_url.rstrip('/')
        elif os.getenv("LLM_API_BASE"):
            self.primary_base_url = os.getenv("LLM_API_BASE").rstrip('/')
        elif env_openai_key and not env_llm_key:
            self.primary_base_url = "https://api.openai.com/v1"
        else:
            self.primary_base_url = "https://nen.com.tw/v1"

        if primary_model:
            self.primary_model = primary_model
        elif os.getenv("LLM_MODEL"):
            self.primary_model = os.getenv("LLM_MODEL")
        elif "api.openai.com" in self.primary_base_url:
            self.primary_model = "gpt-4o-mini"
        else:
            self.primary_model = "gpt-5.6-luna"

        self.primary_api_key = (
            primary_api_key
            or env_llm_key
            or env_openai_key
            or ""
        )

        # 2. Fallback endpoint (Default: Groq / openai/gpt-oss-20b)
        self.fallback_base_url = (
            fallback_base_url
            or os.getenv("LLM_FALLBACK_API_BASE")
            or "https://api.groq.com/openai/v1"
        ).rstrip('/')
        self.fallback_model = (
            fallback_model or os.getenv("LLM_FALLBACK_MODEL") or "openai/gpt-oss-20b"
        )
        self.fallback_api_key = (
            fallback_api_key
            or os.getenv("LLM_FALLBACK_API_KEY")
            or os.getenv("ASR_GROQ_API_KEY")
            or ""
        )

        self.timeout = timeout
        self.enable_web_search = enable_web_search
        self.web_search_service = WebSearchService()

    def _convert_to_openai_messages(self, contents: Any) -> List[Dict[str, Any]]:
        """Converts string, list of strings, or Gemini-style messages into OpenAI chat format."""
        if isinstance(contents, str):
            return [{"role": "user", "content": contents}]

        if isinstance(contents, list):
            openai_msgs = []
            for item in contents:
                if isinstance(item, str):
                    openai_msgs.append({"role": "user", "content": item})
                elif isinstance(item, dict):
                    role = item.get("role", "user")
                    if role == "model":
                        role = "assistant"
                    elif role not in ("user", "assistant", "system"):
                        role = "user"

                    parts = item.get("parts", [])
                    if isinstance(parts, list):
                        content_str = "\n".join(str(p) for p in parts if p)
                    else:
                        content_str = str(item.get("content", parts))

                    if content_str:
                        openai_msgs.append({"role": role, "content": content_str})
            if openai_msgs:
                return openai_msgs
            return [{"role": "user", "content": str(contents)}]

        return [{"role": "user", "content": str(contents)}]

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Executes tool via WebSearchService and returns string output."""
        try:
            if tool_name == 'search_web':
                query = args.get('query', '')
                res = self.web_search_service.search(query)
                return res[:3000] if res else "未搜尋到相關結果。"
            elif tool_name == 'read_web_page':
                url = args.get('url', '')
                res = self.web_search_service.read_url(url)
                return res[:3000] if res else "無法讀取該網頁內容。"
            elif tool_name == 'get_live_weather':
                location = args.get('location', '')
                res = self.web_search_service.get_weather(location)
                if not res:
                    # fallback to search
                    res = self.web_search_service.search(f"{location} 天氣 氣溫")
                return res[:3000] if res else "暫無該地區即時氣象資料。"
            else:
                return f"未知的工具：{tool_name}"
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return f"執行工具發生錯誤：{e}"

    def generate_content(self, contents: Any) -> LLMResponse:
        """
        Executes text generation with automatic failover:
        Primary (nen.com.tw / gpt-5.6-luna) with autonomous tool calling -> Fallback (Groq) -> Google Gemini.
        """
        raw_messages = self._convert_to_openai_messages(contents)

        # 1. Try Primary LLM with Autonomous Tool Loop
        if self.primary_base_url and self.primary_api_key and self.primary_model:
            try:
                logger.info(f"Invoking Primary LLM ({self.primary_model} @ {self.primary_base_url}) with agentic tools...")
                
                # Copy messages and ensure system prompt
                agent_messages: List[Dict[str, Any]] = []
                has_system = any(m.get("role") == "system" for m in raw_messages)
                if not has_system:
                    agent_messages.append({"role": "system", "content": SYSTEM_GROUNDING_PROMPT})
                agent_messages.extend([dict(m) for m in raw_messages])

                # Autonomous multi-turn tool calling loop (up to 5 iterations)
                for step in range(5):
                    resp = requests.post(
                        f"{self.primary_base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.primary_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.primary_model,
                            "messages": agent_messages,
                            "tools": AVAILABLE_TOOLS if self.enable_web_search else None
                        },
                        timeout=self.timeout
                    )
                    if resp.status_code != 200:
                        logger.warning(f"Primary LLM step {step} returned HTTP {resp.status_code}: {resp.text[:200]}")
                        break

                    data = resp.json()
                    choices = data.get("choices", [])
                    if not choices:
                        break

                    msg = choices[0].get("message", {})
                    agent_messages.append(msg)

                    tool_calls = msg.get("tool_calls")
                    if not tool_calls:
                        # Final answer received
                        reply_text = msg.get("content", "")
                        if reply_text:
                            return LLMResponse(reply_text)
                        break

                    # Execute all requested tool calls
                    for tc in tool_calls:
                        func = tc.get("function", {})
                        func_name = func.get("name", "")
                        try:
                            func_args = json.loads(func.get("arguments", "{}"))
                        except Exception:
                            func_args = {}

                        logger.info(f"Agent executing tool: {func_name}({func_args})")
                        tool_output = self._execute_tool(func_name, func_args)

                        agent_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id"),
                            "content": tool_output
                        })

            except Exception as e:
                logger.warning(f"Primary LLM agent loop failed: {e}. Switching to Fallback LLM...")

        # 2. Try Fallback LLM (Groq / openai/gpt-oss-20b) with Autonomous Tool Loop
        if self.fallback_base_url and self.fallback_api_key and self.fallback_model:
            try:
                logger.info(f"Invoking Fallback LLM ({self.fallback_model} @ {self.fallback_base_url}) with agentic tools...")
                fallback_messages: List[Dict[str, Any]] = []
                has_system = any(m.get("role") == "system" for m in raw_messages)
                if not has_system:
                    fallback_messages.append({"role": "system", "content": SYSTEM_GROUNDING_PROMPT})
                fallback_messages.extend([dict(m) for m in raw_messages])

                for step in range(5):
                    resp = requests.post(
                        f"{self.fallback_base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.fallback_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.fallback_model,
                            "messages": fallback_messages,
                            "tools": AVAILABLE_TOOLS if self.enable_web_search else None
                        },
                        timeout=self.timeout
                    )
                    if resp.status_code != 200:
                        logger.warning(f"Fallback LLM step {step} returned HTTP {resp.status_code}: {resp.text[:200]}")
                        break

                    resp.encoding = "utf-8"
                    data = resp.json()
                    choices = data.get("choices", [])
                    if not choices:
                        break

                    msg = choices[0].get("message", {})
                    fallback_messages.append(msg)

                    tool_calls = msg.get("tool_calls")
                    if not tool_calls:
                        reply_text = msg.get("content", "")
                        if reply_text:
                            return LLMResponse(reply_text)
                        break

                    for tc in tool_calls:
                        func = tc.get("function", {})
                        func_name = func.get("name", "")
                        try:
                            func_args = json.loads(func.get("arguments", "{}"))
                        except Exception:
                            func_args = {}

                        logger.info(f"Fallback Agent executing tool: {func_name}({func_args})")
                        tool_output = self._execute_tool(func_name, func_args)

                        fallback_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id"),
                            "content": tool_output
                        })
            except Exception as e:
                logger.error(f"Fallback LLM failed: {e}")

        # 3. Last Resort Fallback: Google Gemini (Dual SDK v2 / v1 with Web Grounding)
        gemini_key = (
            os.getenv("ASR_GEMINI_API_KEY")
            or os.getenv("GEMINI_LLM_API_KEY")
            or os.getenv("GEMINI_API_KEY")
        )
        if gemini_key:
            prompt_text = ""
            if isinstance(contents, str):
                prompt_text = contents
            elif isinstance(contents, list) and contents:
                for c in reversed(contents):
                    if isinstance(c, str):
                        prompt_text = c
                        break
                    elif isinstance(c, dict) and c.get('role') in ('user', 'human'):
                        parts = c.get('parts', [])
                        if parts and isinstance(parts[0], str):
                            prompt_text = parts[0]
                            break
            if not prompt_text:
                prompt_text = str(contents)

            enriched_prompt = (
                self.web_search_service.enrich_prompt_with_web(prompt_text)
                if self.enable_web_search else prompt_text
            )
            final_gemini_prompt = (
                f"{SYSTEM_GROUNDING_PROMPT}\n\n"
                f"使用者詢問內容：\n{enriched_prompt}"
            )

            # Try google-genai v2 Client SDK
            try:
                logger.info("Attempting Google Gemini fallback via google-genai v2 Client...")
                from google import genai as genai_v2
                client = genai_v2.Client(api_key=gemini_key)
                model_name = os.getenv("GEMINI_LLM_MODEL", "gemini-2.5-flash")
                res = client.models.generate_content(
                    model=model_name,
                    contents=final_gemini_prompt
                )
                if res and res.text:
                    return LLMResponse(res.text)
            except Exception as e_v2:
                logger.warning(f"Google GenAI v2 fallback failed: {e_v2}. Trying legacy google-generativeai v1...")

            # Try legacy google-generativeai v1 SDK
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                model_name = os.getenv("GEMINI_LLM_MODEL", "gemini-flash-latest")
                model = genai.GenerativeModel(model_name)
                res = model.generate_content(final_gemini_prompt)
                if res and res.text:
                    return LLMResponse(res.text)
            except Exception as e_v1:
                logger.error(f"Google Gemini legacy v1 fallback failed: {e_v1}")

        raise RuntimeError("All LLM providers (Primary, Fallback, Gemini) failed to generate response.")
