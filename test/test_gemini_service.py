import unittest


class GeminiServiceTests(unittest.TestCase):
    def test_generate_content_uses_configured_model(self):
        from services.gemini import GeminiService

        calls = []

        class Model:
            def generate_content(self, prompt):
                calls.append(prompt)
                return "response"

        service = GeminiService("gemini-test", model_factory=lambda name: Model())

        self.assertEqual(service.generate_content("hello"), "response")
        self.assertEqual(calls, ["hello"])

    def test_image_service_collects_stream_from_configured_client_and_model(self):
        from services.gemini import GeminiImageService

        calls = []

        class Models:
            def generate_content_stream(self, **kwargs):
                calls.append(kwargs)
                return iter(["chunk-1", "chunk-2"])

        class Client:
            models = Models()

        service = GeminiImageService(
            "image-key", "image-model", client_factory=lambda api_key: Client()
        )

        self.assertEqual(service.generate_content_stream("contents", "config"), ["chunk-1", "chunk-2"])
        self.assertEqual(calls, [{"model": "image-model", "contents": "contents", "config": "config"}])
