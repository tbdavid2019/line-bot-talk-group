#!/usr/bin/env python3
import unittest
from unittest.mock import patch, MagicMock
from services.wiki_publisher import WikiPublisherService

class TestWikiPublisherService(unittest.TestCase):
    def test_slugify(self):
        slug = WikiPublisherService.slugify("測試 標題 123!@#")
        self.assertEqual(slug, "測試-標題-123")

    @patch('requests.post')
    def test_publish_note_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "err": 0,
            "msg": "ok",
            "data": {
                "msg": "Saved successfully",
                "url": "https://wiki.david888.com/test-slug",
                "shareUrl": "https://wiki.david888.com/share/abc1234"
            }
        }
        mock_post.return_value = mock_resp

        service = WikiPublisherService()
        result = service.publish_note(
            text="# Hello World\nTesting wiki note",
            path="test-slug",
            theme="claude-canvas"
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["shareUrl"], "https://wiki.david888.com/share/abc1234")
        self.assertEqual(result["path"], "test-slug")

    @patch('requests.get')
    def test_get_note_markdown(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "# Wiki Content\nSample markdown"
        mock_get.return_value = mock_resp

        service = WikiPublisherService()
        content = service.get_note("test-slug", as_markdown=True)
        self.assertEqual(content, "# Wiki Content\nSample markdown")

    @patch('requests.post')
    def test_render_markdown(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "err": 0,
            "data": {"html": "<p>Rendered HTML</p>"}
        }
        mock_post.return_value = mock_resp

        service = WikiPublisherService()
        res = service.render_markdown("# Title")
        self.assertIsNotNone(res)
        self.assertIn("html", res)

if __name__ == '__main__':
    unittest.main()
