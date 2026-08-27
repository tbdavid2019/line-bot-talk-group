"""Unified LLM Service supporting Primary (nen.com.tw), Fallback (Groq), and Gemini."""

from __future__ import annotations

import os
import logging
import requests
from typing import Any, List, Dict, Optional

logger = logging.getLogger(__name__)


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
        timeout: int = 60
    ) -> None:
        # 1. Primary endpoint (Default: nen.com.tw / gpt-5.6-luna)
        self.primary_base_url = (
            primary_base_url or os.getenv("LLM_API_BASE") or "https://nen.com.tw/v1"
        ).rstrip('/')
        self.primary_model = primary_model or os.getenv("LLM_MODEL") or "gpt-5.6-luna"
        self.primary_api_key = (
            primary_api_key
            or os.getenv("LLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
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

    def _convert_to_openai_messages(self, contents: Any) -> List[Dict[str, str]]:
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

    def generate_content(self, contents: Any) -> LLMResponse:
        """
        Executes text generation with automatic failover:
        Primary (nen.com.tw / gpt-5.6-luna) -> Fallback (Groq / openai/gpt-oss-20b) -> Google Gemini.
        """
        messages = self._convert_to_openai_messages(contents)

        # 1. Try Primary LLM
        if self.primary_base_url and self.primary_api_key and self.primary_model:
            try:
                logger.info(f"Invoking Primary LLM ({self.primary_model} @ {self.primary_base_url})...")
                resp = requests.post(
                    f"{self.primary_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.primary_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.primary_model,
                        "messages": messages
                    },
                    timeout=self.timeout
                )
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        reply_text = choices[0].get("message", {}).get("content", "")
                        if reply_text:
                            return LLMResponse(reply_text)
                logger.warning(f"Primary LLM returned HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logger.warning(f"Primary LLM failed: {e}. Switching to Fallback LLM...")

        # 2. Try Fallback LLM
        if self.fallback_base_url and self.fallback_api_key and self.fallback_model:
            try:
                logger.info(f"Invoking Fallback LLM ({self.fallback_model} @ {self.fallback_base_url})...")
                resp = requests.post(
                    f"{self.fallback_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.fallback_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.fallback_model,
                        "messages": messages
                    },
                    timeout=self.timeout
                )
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        reply_text = choices[0].get("message", {}).get("content", "")
                        if reply_text:
                            return LLMResponse(reply_text)
                logger.error(f"Fallback LLM returned HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logger.error(f"Fallback LLM failed: {e}")

        # 3. Last Resort Fallback: Google Gemini
        gemini_key = (
            os.getenv("ASR_GEMINI_API_KEY")
            or os.getenv("GEMINI_LLM_API_KEY")
            or os.getenv("GEMINI_API_KEY")
        )
        if gemini_key:
            try:
                logger.info("Attempting final fallback to Google Gemini...")
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                model_name = os.getenv("GEMINI_LLM_MODEL", "gemini-flash-latest")
                model = genai.GenerativeModel(model_name)
                res = model.generate_content(contents)
                if res and res.text:
                    return LLMResponse(res.text)
            except Exception as e:
                logger.error(f"Google Gemini fallback failed: {e}")

        raise RuntimeError("All LLM providers (Primary, Fallback, Gemini) failed to generate response.")
