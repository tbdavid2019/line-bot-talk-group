import unittest
import base64
from unittest.mock import patch, MagicMock
from services.image_generator import ImageGeneratorService

class TestImageGeneratorService(unittest.TestCase):
    @patch('requests.post')
    def test_generate_image_primary_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        dummy_png_bytes = b"FAKEPNGDATA12345"
        dummy_b64 = base64.b64encode(dummy_png_bytes).decode('utf-8')
        mock_resp.json.return_value = {
            "choices": [
                {"message": {"content": f"Here is your image:\n![image](data:image/png;base64,{dummy_b64})"}}
            ]
        }
        mock_post.return_value = mock_resp

        service = ImageGeneratorService(primary_api_key="mock-key")
        success, img_bytes, mime_type = service.generate_image_bytes("cute cat")
        self.assertTrue(success)
        self.assertEqual(img_bytes, dummy_png_bytes)
        self.assertEqual(mime_type, "image/png")

    @patch('requests.post')
    def test_generate_image_fallback_success(self, mock_post):
        # 1st call (Primary) fails, 2nd call (Fallback) succeeds
        mock_resp_fail = MagicMock()
        mock_resp_fail.status_code = 500
        mock_resp_fail.text = "Internal Error"

        dummy_jpeg_bytes = b"FAKEJPEGDATA99999"
        dummy_b64 = base64.b64encode(dummy_jpeg_bytes).decode('utf-8')
        mock_resp_ok = MagicMock()
        mock_resp_ok.status_code = 200
        mock_resp_ok.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "image/jpeg",
                                    "data": dummy_b64
                                }
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.side_effect = [mock_resp_fail, mock_resp_ok]

        service = ImageGeneratorService(primary_api_key="mock-primary", fallback_api_key="mock-fallback")
        success, img_bytes, mime_type = service.generate_image_bytes("cute dog")
        self.assertTrue(success)
        self.assertEqual(img_bytes, dummy_jpeg_bytes)
        self.assertEqual(mime_type, "image/jpeg")

    @patch('requests.post')
    def test_generate_image_all_fail(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Error"
        mock_post.return_value = mock_resp

        service = ImageGeneratorService(primary_api_key="mock-key", fallback_api_key="mock-fallback")
        success, img_bytes, mime_type = service.generate_image_bytes("fail prompt")
        self.assertFalse(success)
        self.assertIsNone(img_bytes)

if __name__ == '__main__':
    unittest.main()
