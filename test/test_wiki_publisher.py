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

    @patch('requests.post')
    def test_publish_note_with_present_and_book_urls(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "err": 0,
            "data": {
                "url": "https://wiki.david888.com/my-slides",
                "shareUrl": "https://wiki.david888.com/share/slide123"
            }
        }
        mock_post.return_value = mock_resp

        service = WikiPublisherService()
        slide_text = "# Slide Title\n\n---\n\n## Slide 2\n\n---\n- [Chapter 1](/share/ch1)"
        result = service.publish_note(text=slide_text, path="my-slides")
        self.assertEqual(result["presentUrl"], "https://wiki.david888.com/share/slide123/present")
        self.assertEqual(result["bookUrl"], "https://wiki.david888.com/share/slide123/book")

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

    @patch('requests.post')
    def test_parse_html_to_markdown(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "err": 0,
            "data": {"markdown": "# Converted Title\n\nConverted text"}
        }
        mock_post.return_value = mock_resp

        service = WikiPublisherService()
        res = service.parse_html_to_markdown(html="<h1>Converted Title</h1><p>Converted text</p>")
        self.assertEqual(res, "# Converted Title\n\nConverted text")

    @patch('requests.post')
    def test_extract_structure(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "err": 0,
            "data": {"title": "Test Title", "stats": {"words": 50}}
        }
        mock_post.return_value = mock_resp

        service = WikiPublisherService()
        res = service.extract_structure("# Test Title\nSome content")
        self.assertEqual(res["title"], "Test Title")

    @patch('requests.post')
    def test_lint_markdown(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "err": 0,
            "data": {"valid": True, "issues": []}
        }
        mock_post.return_value = mock_resp

        service = WikiPublisherService()
        res = service.lint_markdown("# Clean Title")
        self.assertTrue(res["valid"])

    def test_should_auto_publish(self):
        service = WikiPublisherService()
        # General question -> False (direct answer in LINE)
        self.assertFalse(service.should_auto_publish("你好", "你好！很高興為您服務。"))
        self.assertFalse(service.should_auto_publish("what can you do?", "I can help with coding, writing..."))

        # Explicit wiki request -> True
        self.assertTrue(service.should_auto_publish("請透過 wiki 發布這篇分析", "詳細分析內容..."))
        self.assertTrue(service.should_auto_publish("!wiki summary", "對話摘要內容..."))

    def test_prepare_wiki_markdown_removes_preamble(self):
        service = WikiPublisherService()
        raw_text = "好的，這是我為您撰寫的分析報告：\n\n# 📚 深度分散式儲存架構白皮書\n\n> 執行摘要：評估 Edge 儲存。\n\n## 1. 簡介\n內容A\n\n## 2. 架構\n內容B"
        prepared = service.prepare_wiki_markdown("請發布白皮書", raw_text)
        self.assertTrue(prepared.startswith("# 📚 深度分散式儲存架構白皮書"))
        self.assertNotIn("好的，這是我為您撰寫的分析報告", prepared)
        self.assertIn("[TOC]", prepared)

    @patch('requests.post')
    def test_format_and_publish_if_long(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "err": 0,
            "data": {
                "url": "https://wiki.david888.com/ai-analysis-123",
                "shareUrl": "https://wiki.david888.com/share/ai999"
            }
        }
        mock_post.return_value = mock_resp

        service = WikiPublisherService()
        long_content = "這是為您整理的英文商務對話教學內容。"
        formatted_line_reply = service.format_and_publish_if_long("請透過 wiki 發布英文商務對話教學", long_content)

        self.assertIn("https://wiki.david888.com/share/ai999", formatted_line_reply)
        self.assertIn("這是為您整理的英文商務對話教學內容。", formatted_line_reply)

    @patch('requests.post')
    def test_dialogue_wiki_request_from_screenshot(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "err": 0,
            "data": {
                "url": "https://wiki.david888.com/business-english-dialogue",
                "shareUrl": "https://wiki.david888.com/share/eng123"
            }
        }
        mock_post.return_value = mock_resp

        service = WikiPublisherService()
        prompt = "你透過 david888 wiki 寫一個 英語對話給我。我要練習口語 商務場景。講甲方的要求太超過了 之類的抱怨。下方要有繁體中文"
        llm_response = "### Scene 1: Client demands\nAlex: We need to talk about client requests.\nMia: Several new requests?\nAlex: Yes, they want a totally different direction."

        # Verify prompt triggers wiki publishing
        self.assertTrue(service.should_auto_publish(prompt, llm_response))

        # Format & publish
        reply = service.format_and_publish_if_long(prompt, llm_response)

        # Verify no raw [CALL: syntax and real shareUrl is returned
        self.assertNotIn("[CALL:", reply)
        self.assertIn("https://wiki.david888.com/share/eng123", reply)

if __name__ == '__main__':
    unittest.main()
