import unittest
from unittest.mock import patch, MagicMock
from services.llm import LLMService, LLMResponse

class TestLLMService(unittest.TestCase):
    def test_message_conversion(self):
        service = LLMService()
        
        # String prompt
        res1 = service._convert_to_openai_messages("Hello")
        self.assertEqual(res1, [{"role": "user", "content": "Hello"}])

        # Gemini-style messages
        res2 = service._convert_to_openai_messages([
            {"role": "user", "parts": ["Hi"]},
            {"role": "model", "parts": ["Hello there!"]},
            {"role": "user", "parts": ["How are you?"]}
        ])
        self.assertEqual(res2, [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello there!"},
            {"role": "user", "content": "How are you?"}
        ])

    @patch('requests.post')
    def test_primary_llm_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {"message": {"content": "Primary response from gpt-5.6-luna", "role": "assistant"}}
            ]
        }
        mock_post.return_value = mock_resp

        service = LLMService(primary_api_key="mock-key", fallback_api_key="mock-key")
        res = service.generate_content("Testing Primary")
        self.assertEqual(res.text, "Primary response from gpt-5.6-luna")
        self.assertEqual(str(res), "Primary response from gpt-5.6-luna")

    @patch('requests.post')
    def test_primary_fail_fallback_success(self, mock_post):
        # 1st call (Primary) fails, 2nd call (Fallback) succeeds
        mock_resp_fail = MagicMock()
        mock_resp_fail.status_code = 500
        mock_resp_fail.text = "Internal Server Error"

        mock_resp_ok = MagicMock()
        mock_resp_ok.status_code = 200
        mock_resp_ok.json.return_value = {
            "choices": [
                {"message": {"content": "Fallback response from Groq", "role": "assistant"}}
            ]
        }
        mock_post.side_effect = [mock_resp_fail, mock_resp_ok]

        service = LLMService(primary_api_key="mock-key", fallback_api_key="mock-key")
        res = service.generate_content("Testing Fallback")
        self.assertEqual(res.text, "Fallback response from Groq")

if __name__ == '__main__':
    unittest.main()
