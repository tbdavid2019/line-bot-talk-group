"""Image Generator Service supporting nen.com.tw (gemini-3.1-flash-image) and Google GenAI fallback."""

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
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 45
    ) -> None:
        self.base_url = (
            base_url or os.getenv("IMAGE_API_BASE") or "https://nen.com.tw/v1"
        ).rstrip('/')
        self.model = model or os.getenv("IMAGE_MODEL") or "gemini-3.1-flash-image"
        self.api_key = (
            api_key
            or os.getenv("IMAGE_API_KEY")
            or os.getenv("LLM_API_KEY")
            or ""
        )
        self.timeout = timeout

    def generate_image_bytes(self, prompt: str) -> Tuple[bool, Optional[bytes], str]:
        """
        Generates an image via nen.com.tw gemini-3.1-flash-image.
        Returns: (success: bool, image_bytes: bytes, mime_type: str)
        """
        # 1. Primary Image Generation (nen.com.tw / gemini-3.1-flash-image)
        if self.base_url and self.api_key and self.model:
            try:
                logger.info(f"Generating image via Primary API ({self.model} @ {self.base_url}) for prompt: '{prompt}'")
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
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
                        
                        # Match data:image/png;base64,...
                        m = re.search(r'data:image\/([a-zA-Z]+);base64,([A-Za-z0-9+/=]+)', content)
                        if m:
                            fmt = m.group(1).lower()
                            mime_type = f"image/{fmt}"
                            b64_data = m.group(2)
                            img_bytes = base64.b64decode(b64_data)
                            logger.info(f"Successfully generated {fmt} image ({len(img_bytes)} bytes)")
                            return True, img_bytes, mime_type

                        # Match direct image URL in markdown ![...](https://...)
                        url_m = re.search(r'!\[.*?\]\((https?:\/\/[^\s\)]+)\)', content)
                        if url_m:
                            img_url = url_m.group(1)
                            img_resp = requests.get(img_url, timeout=15)
                            if img_resp.status_code == 200:
                                content_type = img_resp.headers.get("Content-Type", "image/png")
                                return True, img_resp.content, content_type

                        logger.warning(f"No image extracted from model response: {content[:200]}")
                else:
                    logger.error(f"Primary Image API returned HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logger.error(f"Primary Image API error: {e}")

        # 2. Fallback to Google GenAI Client if configured
        gemini_image_key = (
            os.getenv("GEMINI_IMAGE_API_KEY")
            or os.getenv("ASR_GEMINI_API_KEY")
            or os.getenv("GEMINI_API_KEY")
        )
        if gemini_image_key:
            try:
                logger.info("Attempting fallback image generation via Google GenAI...")
                from google import genai as genai_v2
                from google.genai import types as genai_types
                client = genai_v2.Client(api_key=gemini_image_key)
                response = client.models.generate_content_stream(
                    model=os.getenv("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview"),
                    contents=[
                        f"Create a photorealistic image of a {prompt}. Do not provide text description, only generate the actual image.",
                        f"Generate image: {prompt}",
                    ],
                    config=genai_types.GenerateContentConfig(response_modalities=["IMAGE"])
                )
                for chunk in response:
                    for part in chunk.candidates[0].content.parts:
                        inline_data = getattr(part, 'inline_data', None)
                        if inline_data and getattr(inline_data, 'data', None):
                            return True, inline_data.data, inline_data.mime_type or "image/png"
            except Exception as e:
                logger.error(f"Google GenAI fallback image generation failed: {e}")

        return False, None, ""
