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

    def test_should_auto_publish(self):
        service = WikiPublisherService()
        # Short simple answer -> False
        self.assertFalse(service.should_auto_publish("你好", "你好！很高興為您服務。"))

        # Long answer (> 600 chars) -> True
        long_text = "這是一段長篇分析內容。" * 50
        self.assertTrue(service.should_auto_publish("分析架構", long_text))

        # Structured answer with 2+ headings -> True
        structured_text = "## 1. 架構說明\n內容很詳細\n\n## 2. 核心機制\n包含細部說明與實作細節\n\n" * 10
        self.assertTrue(service.should_auto_publish("請說明系統架構", structured_text))

    def test_prepare_wiki_markdown(self):
        service = WikiPublisherService()
        raw_text = "## 第一章\n內容A\n\n## 第二章\n內容B"
        prepared = service.prepare_wiki_markdown("請分析分散式系統", raw_text)
        self.assertTrue(prepared.startswith("# 📑"))
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
        long_content = ("## 1. 核心結論\nDeepSeek-V4 推論架構極大降低延遲。\n\n## 2. 邊緣節點實作\n" + "詳細實作步驟內容說明。" * 30)
        formatted_line_reply = service.format_and_publish_if_long("請深入分析 AI Agent 趨勢", long_content)

        self.assertIn("https://wiki.david888.com/share/ai999", formatted_line_reply)
        self.assertIn("📑 AI 深度長篇分析已發布至 David888 Wiki！", formatted_line_reply)

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
