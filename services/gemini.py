"""Gemini text-generation boundary (delegates to unified LLMService)."""

from __future__ import annotations

from typing import Any, Callable, Optional
from services.llm import LLMService, LLMResponse


class GeminiService:
    def __init__(
        self,
        model_name: Optional[str] = None,
        model_factory: Optional[Callable[[str], Any]] = None
    ) -> None:
        self.model_name = model_name
        self.model_factory = model_factory
        self._llm_service = LLMService()

    def generate_content(self, contents: Any) -> Any:
        if self.model_factory is not None:
            # If a custom test mock or model factory was supplied
            try:
                model_instance = self.model_factory(self.model_name or "gemini-flash-latest")
                if hasattr(model_instance, "generate_content"):
                    return model_instance.generate_content(contents)
            except Exception:
                pass
        return self._llm_service.generate_content(contents)


class GeminiImageService:
    def __init__(self, api_key: str, model_name: str, client_factory: Callable[[str], Any] | None = None) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.client_factory = client_factory

    def generate_content_stream(self, contents: Any, config: Any) -> list[Any]:
        if self.client_factory:
            client = self.client_factory(self.api_key)
        else:
            from google import genai as genai_v2
            client = genai_v2.Client(api_key=self.api_key)
        response = client.models.generate_content_stream(
            model=self.model_name,
            contents=contents,
            config=config,
        )
        return list(response)
