#!/usr/bin/env python3
import unittest
from unittest.mock import patch, MagicMock
from services.box_storage import BoxStorageService

class TestBoxStorageService(unittest.TestCase):
    def test_default_endpoints(self):
        service = BoxStorageService()
        self.assertEqual(len(service.endpoints), 3)
        self.assertEqual(service.endpoints[0], "https://box.david888.com")
        self.assertEqual(service.endpoints[1], "https://box.glsoft.ai")
        self.assertEqual(service.endpoints[2], "https://box.aiurl.tw")

    @patch('requests.post')
    def test_upload_file_primary_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "result": "success",
            "data": {
                "id": "123",
                "url": "https://d36gp3xejpe77o.cloudfront.net/storage/image/2026/08/27/test.png",
                "share_url": "https://box.david888.com/v/abcd"
            }
        }
        mock_post.return_value = mock_resp

        service = BoxStorageService()
        result = service.upload_file(b"dummy image data", "test.png", title="Test Image", mime_type="image/png")
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "123")
        self.assertIn("cloudfront.net", result["url"])
        self.assertEqual(mock_post.call_count, 1)

    @patch('requests.post')
    def test_upload_file_failover_to_secondary(self, mock_post):
        # First call fails (500), second call succeeds (200)
        mock_fail = MagicMock()
        mock_fail.status_code = 500
        mock_fail.text = "Server Error"

        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {
            "result": "success",
            "data": {
                "id": "456",
                "url": "https://d36gp3xejpe77o.cloudfront.net/storage/image/2026/08/27/test.png",
                "share_url": "https://box.glsoft.ai/v/efgh"
            }
        }
        mock_post.side_effect = [mock_fail, mock_success]

        service = BoxStorageService()
        result = service.upload_file(b"dummy image data", "test.png")
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "456")
        self.assertEqual(mock_post.call_count, 2)

    @patch('requests.get')
    def test_get_stats(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "result": "success",
            "data": {"total": 42, "image": 10, "video": 5}
        }
        mock_get.return_value = mock_resp

        service = BoxStorageService()
        stats = service.get_stats()
        self.assertIsNotNone(stats)
        self.assertEqual(stats["total"], 42)

if __name__ == '__main__':
    unittest.main()
