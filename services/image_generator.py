"""Image Generator Service supporting Primary (nen.com.tw) and Fallback (Google Generative Language)."""

from __future__ import annotations

import os
import re
import base64
import logging
import requests
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class ImageGeneratorService:
    def __init__(
        self,
        primary_base_url: Optional[str] = None,
        primary_model: Optional[str] = None,
        primary_api_key: Optional[str] = None,
        fallback_base_url: Optional[str] = None,
        fallback_model: Optional[str] = None,
        fallback_api_key: Optional[str] = None,
        timeout: int = 45
    ) -> None:
        # 1. Primary Endpoint (nen.com.tw / gemini-3.1-flash-image)
        self.primary_base_url = (
            primary_base_url or os.getenv("IMAGE_API_BASE") or "https://nen.com.tw/v1"
        ).rstrip('/')
        self.primary_model = primary_model or os.getenv("IMAGE_MODEL") or "gemini-3.1-flash-image"
        self.primary_api_key = (
            primary_api_key
            or os.getenv("IMAGE_API_KEY")
            or os.getenv("LLM_API_KEY")
            or ""
        )

        # 2. Fallback Endpoint (Google Generative Language API)
        self.fallback_base_url = (
            fallback_base_url
            or os.getenv("IMAGE_FALLBACK_BASE")
            or "https://generativelanguage.googleapis.com/v1beta"
        ).rstrip('/')
        self.fallback_model = (
            fallback_model
            or os.getenv("IMAGE_FALLBACK_MODEL")
            or os.getenv("GEMINI_IMAGE_MODEL")
            or "gemini-3.1-flash-image"
        )
        self.fallback_api_key = (
            fallback_api_key
            or os.getenv("IMAGE_FALLBACK_API_KEY")
            or os.getenv("GEMINI_IMAGE_API_KEY")
            or os.getenv("ASR_GEMINI_API_KEY")
            or os.getenv("GEMINI_LLM_API_KEY")
            or ""
        )

        self.timeout = timeout

    def generate_image_bytes(self, prompt: str) -> Tuple[bool, Optional[bytes], str]:
        """
        Generates an image with multi-tier failover:
        Primary (nen.com.tw / gemini-3.1-flash-image) -> Fallback (Google Generative Language API).
        Returns: (success: bool, image_bytes: bytes, mime_type: str)
        """
        # 1. Primary Image Generation (nen.com.tw / gemini-3.1-flash-image)
        if self.primary_base_url and self.primary_api_key and self.primary_model:
            try:
                logger.info(f"Generating image via Primary API ({self.primary_model} @ {self.primary_base_url}) for: '{prompt[:60]}'...")
                resp = requests.post(
                    f"{self.primary_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.primary_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.primary_model,
                        "messages": [
                            {"role": "user", "content": f"Generate image: {prompt}"}
                        ]
                    },
                    timeout=self.timeout
                )
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        
                        # Match data:image/png;base64,... or data:image/jpeg;base64,...
                        m = re.search(r'data:image\/([a-zA-Z]+);base64,([A-Za-z0-9+/=]+)', content)
                        if m:
                            fmt = m.group(1).lower()
                            mime_type = f"image/{fmt}"
                            b64_data = m.group(2)
                            img_bytes = base64.b64decode(b64_data)
                            logger.info(f"Primary API generated {fmt} image ({len(img_bytes)} bytes)")
                            return True, img_bytes, mime_type

                        # Match direct image URL in markdown ![...](https://...)
                        url_m = re.search(r'!\[.*?\]\((https?:\/\/[^\s\)]+)\)', content)
                        if url_m:
                            img_url = url_m.group(1)
                            img_resp = requests.get(img_url, timeout=15)
                            if img_resp.status_code == 200:
                                content_type = img_resp.headers.get("Content-Type", "image/png")
                                return True, img_resp.content, content_type

                        logger.warning(f"No image extracted from Primary response: {content[:200]}")
                else:
                    logger.warning(f"Primary Image API returned HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logger.warning(f"Primary Image API failed: {e}. Switching to Fallback...")

        # 2. Fallback Image Generation (Google Generative Language API)
        if self.fallback_api_key:
            models_to_try = [
                self.fallback_model,
                "gemini-3.1-flash-image",
                "gemini-3-pro-image-preview",
                "gemini-2.5-flash-image"
            ]
            # Deduplicate preserving order
            seen = set()
            unique_models = [m for m in models_to_try if m and not (m in seen or seen.add(m))]

            clean_base_url = re.sub(r'/openai/?$', '', self.fallback_base_url)
            for model_candidate in unique_models:
                clean_model = model_candidate.replace('models/', '')
                try:
                    logger.info(f"Attempting Fallback Image API ({clean_model} @ Google Generative Language API)...")
                    url = f"{clean_base_url}/models/{clean_model}:generateContent?key={self.fallback_api_key}"
                    resp = requests.post(
                        url,
                        headers={"Content-Type": "application/json"},
                        json={
                            "contents": [{"parts": [{"text": f"Create a photorealistic image: {prompt}"}]}],
                            "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}
                        },
                        timeout=self.timeout
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for part in parts:
                                inline_data = part.get("inlineData")
                                if inline_data and inline_data.get("data"):
                                    mime_type = inline_data.get("mimeType", "image/png")
                                    img_bytes = base64.b64decode(inline_data["data"])
                                    logger.info(f"Fallback Image API succeeded with {model_candidate} ({len(img_bytes)} bytes, {mime_type})")
                                    return True, img_bytes, mime_type
                    else:
                        logger.warning(f"Fallback model {model_candidate} returned HTTP {resp.status_code}: {resp.text[:200]}")
                except Exception as e:
                    logger.warning(f"Fallback model {model_candidate} error: {e}")

        # 3. Last Resort Fallback: Google GenAI Client SDK
        if self.fallback_api_key:
            try:
                logger.info("Attempting last resort fallback via google-genai Client SDK...")
                from google import genai as genai_v2
                from google.genai import types as genai_types
                client = genai_v2.Client(api_key=self.fallback_api_key)
                response = client.models.generate_content_stream(
                    model=self.fallback_model,
                    contents=[
                        f"Create a photorealistic image of {prompt}. Do not provide text description, only generate the actual image."
                    ],
                    config=genai_types.GenerateContentConfig(response_modalities=["IMAGE"])
                )
                for chunk in response:
                    for part in chunk.candidates[0].content.parts:
                        inline_data = getattr(part, 'inline_data', None)
                        if inline_data and getattr(inline_data, 'data', None):
                            return True, inline_data.data, inline_data.mime_type or "image/png"
            except Exception as e:
                logger.error(f"Google GenAI SDK fallback failed: {e}")

        return False, None, ""
