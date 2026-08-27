#!/usr/bin/env python3
import unittest
from unittest.mock import patch, MagicMock
from services.web_search import WebSearchService


class TestWebSearchService(unittest.TestCase):
    def setUp(self):
        self.service = WebSearchService(base_urls=["https://2md.aiurl.tw", "https://2md.glsoft.ai"])

    def test_extract_urls(self):
        text = "Check this out: https://example.com/test and http://foo.bar/index.html"
        urls = self.service.extract_urls(text)
        self.assertEqual(urls, ["https://example.com/test", "http://foo.bar/index.html"])

    def test_should_search(self):
        # Real-time queries -> True
        self.assertTrue(self.service.should_search("台積電即時股價"))
        self.assertTrue(self.service.should_search("今日最新科技新聞"))
        self.assertTrue(self.service.should_search("!search OpenAI最新發表"))
        self.assertTrue(self.service.should_search("!搜尋 台北明天天氣"))

        # General queries without real-time keywords -> False
        self.assertFalse(self.service.should_search("什麼是二元搜尋樹？"))
        self.assertFalse(self.service.should_search("請幫我寫一首七言絕句"))

    @patch('requests.get')
    def test_search_success_primary(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "[1] Title: TSMC Stock\n[1] URL Source: https://tw.stock.yahoo.com\n[1] Content: 1000 TWD"
        mock_get.return_value = mock_resp

        result = self.service.search("!search 台積電")
        self.assertIsNotNone(result)
        self.assertIn("1000 TWD", result)

    @patch('requests.get')
    def test_search_failover(self, mock_get):
        # First call fails, second succeeds
        resp1 = MagicMock()
        resp1.status_code = 500
        resp1.text = "Server Error"

        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.text = "[1] Title: Fallback search result\n[1] Content: Live info"

        mock_get.side_effect = [resp1, resp1, resp2]

        result = self.service.search("NVIDIA earnings")
        self.assertIsNotNone(result)
        self.assertIn("Live info", result)

    @patch('requests.get')
    def test_read_url_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "# Article Title\n\nFull Markdown page content here."
        mock_get.return_value = mock_resp

        result = self.service.read_url("https://news.ycombinator.com")
        self.assertIsNotNone(result)
        self.assertIn("Article Title", result)

    @patch('requests.get')
    def test_enrich_prompt_with_url(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "# Hacker News Top Story\nAI models released today."
        mock_get.return_value = mock_resp

        prompt = "請幫我摘要這個網頁：https://news.ycombinator.com"
        enriched = self.service.enrich_prompt_with_web(prompt)

        self.assertIn("即時網路檢索與即時資料參考", enriched)
        self.assertIn("Hacker News Top Story", enriched)


if __name__ == '__main__':
    unittest.main()
