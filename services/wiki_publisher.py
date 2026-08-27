import os
import re
import time
import logging
import requests
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

DEFAULT_WIKI_API_BASE = "https://wiki.david888.com/api"

class WikiPublisherService:
    """
    David888 Wiki Publisher Service
    支援將 Markdown 內容、對話摘要發布至 wiki.david888.com 並取得公開唯讀分享網址 (shareUrl)。
    """
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 15
    ):
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
        width: str = "1200px"
    ) -> Optional[Dict[str, Any]]:
        """
        發布或附加 Markdown 筆記至 David888 Wiki。

        Returns:
            dict: { "url": "...", "shareUrl": "https://wiki.david888.com/share/...", "path": "..." }
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
            logger.info(f"Publishing note to David888 Wiki: path='{path}', theme='{theme}'")
            resp = requests.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json; charset=UTF-8"},
                timeout=self.timeout
            )
            if resp.status_code == 200:
                res_json = resp.json()
                if res_json.get("err") == 0 and "data" in res_json:
                    data = res_json["data"]
                    share_url = data.get("shareUrl")
                    logger.info(f"Wiki note published successfully. shareUrl: {share_url}")
                    return {
                        "path": path,
                        "url": data.get("url"),
                        "shareUrl": share_url,
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
        讀取 Wiki 頁面內容
        """
        api_url = f"{self.base_url}/{path}"
        headers = {}
        if as_markdown:
            headers["Accept"] = "text/markdown"
        if pw:
            headers["Authorization"] = f"Bearer {pw}"

        try:
            resp = requests.get(api_url, headers=headers, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            logger.error(f"Error fetching note from Wiki path '{path}': {e}")
        return None

    def render_markdown(self, markdown: str, theme: str = "claude-canvas", full_html: bool = False) -> Optional[Dict[str, Any]]:
        """
        呼叫 Wiki 渲染 API 將 Markdown 轉為 HTML
        """
        api_url = f"{self.base_url}/markdown/render"
        try:
            resp = requests.post(
                api_url,
                json={"markdown": markdown, "theme": theme, "fullHtml": full_html},
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            if resp.status_code == 200:
                res_json = resp.json()
                if res_json.get("err") == 0:
                    return res_json.get("data")
        except Exception as e:
            logger.error(f"Error rendering markdown via Wiki: {e}")
        return None
