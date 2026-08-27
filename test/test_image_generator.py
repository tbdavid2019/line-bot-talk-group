import unittest
import base64
from unittest.mock import patch, MagicMock
from services.image_generator import ImageGeneratorService

class TestImageGeneratorService(unittest.TestCase):
    @patch('requests.post')
    def test_generate_image_base64_success(self, mock_post):
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

        service = ImageGeneratorService(api_key="mock-key")
        success, img_bytes, mime_type = service.generate_image_bytes("cute cat")
        self.assertTrue(success)
        self.assertEqual(img_bytes, dummy_png_bytes)
        self.assertEqual(mime_type, "image/png")

    @patch('requests.post')
    def test_generate_image_failure(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Error"
        mock_post.return_value = mock_resp

        service = ImageGeneratorService(api_key="mock-key")
        success, img_bytes, mime_type = service.generate_image_bytes("fail prompt")
        self.assertFalse(success)
        self.assertIsNone(img_bytes)

if __name__ == '__main__':
    unittest.main()
