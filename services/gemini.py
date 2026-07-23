"""Gemini text-generation boundary."""

from __future__ import annotations

from typing import Any, Callable


class GeminiService:
    def __init__(self, model_name: str, model_factory: Callable[[str], Any]) -> None:
        self.model_name = model_name
        self.model_factory = model_factory

    def generate_content(self, contents: Any) -> Any:
        return self.model_factory(self.model_name).generate_content(contents)


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

