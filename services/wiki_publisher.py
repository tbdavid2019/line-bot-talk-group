"""
David888 Wiki Publisher Service
Conforms strictly to https://wiki.david888.com/.well-known/agent-skills/david888-wiki-publisher/SKILL.md
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime
import logging
import requests
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

DEFAULT_WIKI_API_BASE = "https://wiki.david888.com/api"


class WikiPublisherService:
    """
    David888 Wiki Publisher Service
    支援將 Markdown 內容、對話摘要發布至 wiki.david888.com 並取得公開唯讀分享網址 (shareUrl)、
    2D 簡報模式網址 (/present)、雙欄電子書模式網址 (/book) 以及無狀態 Markdown 處理工具。
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 15
    ) -> None:
        self.base_url = (base_url or os.getenv("WIKI_API_BASE_URL") or DEFAULT_WIKI_API_BASE).rstrip('/')
        self.timeout = timeout

    @staticmethod
    def slugify(title: str, fallback_prefix: str = "note") -> str:
        """
        將標題轉為乾淨的 Wiki path slug
        """
        if not title:
            return f"{fallback_prefix}-{int(time.time())}"

        # 移除特殊符號，保留英文、數字、中文與連字號
        slug = re.sub(r'[^\w\-\u4e00-\u9fff]+', '-', title.strip()).strip('-')
        if not slug:
            slug = f"{fallback_prefix}-{int(time.time())}"
        return slug[:50]

    def publish_note(
        self,
        text: str,
        path: Optional[str] = None,
        title: Optional[str] = None,
        theme: str = "claude-canvas",
        public: bool = True,
        append: bool = False,
        pw: Optional[str] = None,
        vpw: Optional[str] = None,
        width: str = "100%"
    ) -> Optional[Dict[str, Any]]:
        """
        發布或附加 Markdown 筆記至 David888 Wiki。

        Returns:
            dict: {
                "path": "...",
                "url": "...",
                "shareUrl": "https://wiki.david888.com/share/...",
                "presentUrl": "https://wiki.david888.com/share/.../present",
                "bookUrl": "https://wiki.david888.com/share/.../book",
                "msg": "ok"
            }
            None: 若發布失敗
        """
        if not path:
            path = self.slugify(title or f"summary-{int(time.time())}")

        api_url = f"{self.base_url}/{path}"

        payload: Dict[str, Any] = {
            "text": text,
            "public": public,
            "theme": theme,
            "width": width
        }
        if append:
            payload["append"] = True
        if pw:
            payload["pw"] = pw
        if vpw:
            payload["vpw"] = vpw

        try:
            logger.info(f"Publishing note to David888 Wiki: path='{path}', theme='{theme}', width='{width}'")
            resp = requests.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json; charset=UTF-8"},
                timeout=self.timeout
            )
            if resp.status_code == 200:
                resp.encoding = "utf-8"
                res_json = resp.json()
                if res_json.get("err") == 0 and "data" in res_json:
                    data = res_json["data"]
                    share_url = data.get("shareUrl")
                    logger.info(f"Wiki note published successfully. shareUrl: {share_url}")

                    # Determine present / book modes
                    is_slide = bool(re.search(r'(?:^|\n)(?:---|--)(?:\n|$)', text) or "transition:" in text)
                    is_book = bool(re.search(r'(?:^|\n)\s*(?:-|\d+\.)\s+\[.+\]\((?:/share/|/|https://)', text))

                    present_url = f"{share_url}/present" if (share_url and is_slide) else None
                    book_url = f"{share_url}/book" if (share_url and is_book) else None

                    return {
                        "path": path,
                        "url": data.get("url"),
                        "shareUrl": share_url,
                        "presentUrl": present_url,
                        "bookUrl": book_url,
                        "msg": data.get("msg", "ok")
                    }
                else:
                    logger.warning(f"Wiki publish returned error response: {res_json}")
            else:
                logger.warning(f"Wiki publish failed with HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"Error publishing note to Wiki: {e}")

        return None

    def get_note(self, path: str, pw: Optional[str] = None, as_markdown: bool = True) -> Optional[str]:
        """
        讀取 Wiki 頁面內容 (支援 Accept: text/markdown 優先模式)
        """
        api_url = f"{self.base_url}/{path}"
        headers = {}
        if as_markdown:
            headers["Accept"] = "text/markdown"
        if pw:
            headers["Authorization"] = f"Bearer {pw}"

        try:
            resp = requests.get(api_url, headers=headers, timeout=self.timeout)
            resp.encoding = "utf-8"
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            logger.error(f"Error fetching note from Wiki path '{path}': {e}")
        return None

    def render_markdown(
        self,
        markdown: str,
        theme: str = "claude-canvas",
        full_html: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        呼叫 Wiki 渲染 API (POST /api/markdown/render) 將 Markdown 轉為 HTML
        """
        api_url = f"{self.base_url}/markdown/render"
        try:
            resp = requests.post(
                api_url,
                json={"markdown": markdown, "theme": theme, "fullHtml": full_html},
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            resp.encoding = "utf-8"
            if resp.status_code == 200:
                res_json = resp.json()
                if res_json.get("err") == 0:
                    return res_json.get("data")
        except Exception as e:
            logger.error(f"Error rendering markdown via Wiki: {e}")
        return None

    def parse_html_to_markdown(
        self,
        html: Optional[str] = None,
        url: Optional[str] = None
    ) -> Optional[str]:
        """
        呼叫 Wiki 解析 API (POST /api/markdown/parse) 將 HTML 或網頁轉換為結構化 Markdown
        """
        api_url = f"{self.base_url}/markdown/parse"
        payload: Dict[str, Any] = {}
        if html:
            payload["html"] = html
        elif url:
            payload["url"] = url
        else:
            return None

        try:
            resp = requests.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            resp.encoding = "utf-8"
            if resp.status_code == 200:
                res_json = resp.json()
                if res_json.get("err") == 0 and "data" in res_json:
                    return res_json["data"].get("markdown")
        except Exception as e:
            logger.error(f"Error parsing HTML to markdown via Wiki: {e}")
        return None

    def extract_structure(self, markdown: str) -> Optional[Dict[str, Any]]:
        """
        呼叫 Wiki 結構萃取 API (POST /api/markdown/extract) 提取標題、連結、結構與統計
        """
        api_url = f"{self.base_url}/markdown/extract"
        try:
            resp = requests.post(
                api_url,
                json={"markdown": markdown},
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            resp.encoding = "utf-8"
            if resp.status_code == 200:
                res_json = resp.json()
                if res_json.get("err") == 0 and "data" in res_json:
                    return res_json["data"]
        except Exception as e:
            logger.error(f"Error extracting markdown structure: {e}")
        return None

    def lint_markdown(self, markdown: str) -> Optional[Dict[str, Any]]:
        """
        呼叫 Wiki 自動修正與檢查 API (POST /api/markdown/lint)
        """
        api_url = f"{self.base_url}/markdown/lint"
        try:
            resp = requests.post(
                api_url,
                json={"markdown": markdown},
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            resp.encoding = "utf-8"
            if resp.status_code == 200:
                res_json = resp.json()
                if res_json.get("err") == 0 and "data" in res_json:
                    return res_json["data"]
        except Exception as e:
            logger.error(f"Error linting markdown: {e}")
        return None

    def should_auto_publish(self, prompt: str, content: str) -> bool:
        """
        判斷是否應自動轉存並發布為 David888 Wiki 專頁：
        僅在提問中明確提及 wiki / david888 / 維基 / 共筆 或特意要求發布時觸發。
        """
        if not content or not prompt:
            return False

        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ['wiki', 'david888', '維基', '共筆', '!wiki', '！wiki']):
            return True

        return False

    def prepare_wiki_markdown(self, prompt: str, content: str) -> str:
        """
        將內容格式化為嚴格符合 David888 Wiki 規範的 Markdown：
        1. 第一行強制為 Level-1 `# Document Title`（無任何對話前綴寒暄）。
        2. 若有對話廢話（如「好的，這是為您整理的...」）予以移除並提取真正 H1。
        3. `[TOC]` 目錄與引言摘要 `> ...` 強制排在 `# Document Title` 之後。
        4. 保留結構化章節（`##`、`###`）、表格與 Mermaid 圖表。
        """
        cleaned_content = re.sub(r'\[CALL:[^\]]+\]', '', content).strip()
        if not cleaned_content:
            cleaned_content = content.strip()

        # Check if there is a level-1 heading inside content
        h1_match = re.search(r'^(#\s+[^\n]+)', cleaned_content, re.MULTILINE)

        if h1_match:
            h1_header = h1_match.group(1).strip()
            # Remove any preamble text before the first # Title
            post_h1_text = cleaned_content[h1_match.end():].strip()
            result = f"{h1_header}\n\n{post_h1_text}"
        else:
            clean_title = prompt.strip()
            for prefix in [
                '@bot', '@機器人', '你透過', '請透過', '透過', 'david888', 'wiki',
                '寫一個', '幫我寫', '幫我', '請幫我', '請', '分析', '發布', '撰寫'
            ]:
                clean_title = re.sub(re.escape(prefix), '', clean_title, flags=re.IGNORECASE).strip()
            clean_title = clean_title.split('。')[0].split('\n')[0].strip()[:40]
            if not clean_title:
                clean_title = f"AI 專題筆記 ({datetime.now().strftime('%Y-%m-%d')})"
            result = f"# 📑 {clean_title}\n\n{cleaned_content}"

        # Ensure [TOC] is inserted after H1 (and after any top blockquote)
        heading_count = len(re.findall(r'^##\s+', result, re.MULTILINE))
        if heading_count >= 2 and '[TOC]' not in result and '[toc]' not in result:
            # Find insertion point after H1 and optional blockquote
            lines = result.split('\n')
            insert_idx = 1
            for i, line in enumerate(lines[1:], start=1):
                if line.startswith('>') or not line.strip():
                    insert_idx = i + 1
                else:
                    break

            top_section = "\n".join(lines[:insert_idx]).strip()
            bottom_section = "\n".join(lines[insert_idx:]).strip()
            result = f"{top_section}\n\n[TOC]\n\n{bottom_section}"

        return result

    def format_and_publish_if_long(self, prompt: str, content: str) -> str:
        """
        發布至 David888 Wiki 並保留完整的回答內容在 LINE 中，附上可點擊的 shareUrl。
        """
        if not self.should_auto_publish(prompt, content):
            return content

        try:
            wiki_md = self.prepare_wiki_markdown(prompt, content)
            title_slug = self.slugify(prompt[:30], fallback_prefix="ai-note")
            wiki_res = self.publish_note(
                text=wiki_md,
                title=title_slug,
                theme="claude-canvas",
                public=True,
                width="100%"
            )
            if wiki_res and wiki_res.get("shareUrl"):
                share_url = wiki_res["shareUrl"]
                extra_links = []
                if wiki_res.get("presentUrl"):
                    extra_links.append(f"🖥️ 簡報投影模式：{wiki_res['presentUrl']}")
                if wiki_res.get("bookUrl"):
                    extra_links.append(f"📖 雙欄電子書模式：{wiki_res['bookUrl']}")

                extra_str = ("\n" + "\n".join(extra_links)) if extra_links else ""
                return f"{content}\n\n---\n📑 本篇已同步發布至 David888 Wiki：\n{share_url}{extra_str}"
        except Exception as e:
            logger.error(f"Failed to publish response to wiki: {e}")

        return content
