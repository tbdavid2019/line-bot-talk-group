import os
import logging
import requests
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

DEFAULT_BOX_ENDPOINTS = [
    "https://box.david888.com",  # Primary
    "https://box.glsoft.ai",      # Fallback 1
    "https://box.aiurl.tw",       # Fallback 2
]

class BoxStorageService:
    """
    888box Asset Management Service
    支援主要的 box.david888.com 及 fallback (box.glsoft.ai, box.aiurl.tw)
    自動故障轉移 (Failover) 上傳圖片、影片、音訊與各類檔案。
    """
    def __init__(
        self,
        endpoints: Optional[List[str]] = None,
        token: Optional[str] = None,
        timeout: int = 15
    ):
        env_endpoints = os.getenv("BOX_STORAGE_ENDPOINTS")
        if env_endpoints:
            self.endpoints = [ep.strip().rstrip('/') for ep in env_endpoints.split(',') if ep.strip()]
        elif endpoints:
            self.endpoints = [ep.rstrip('/') for ep in endpoints]
        else:
            self.endpoints = DEFAULT_BOX_ENDPOINTS.copy()

        self.token = token or os.getenv("BOX_STORAGE_TOKEN", "")
        self.timeout = timeout

    def upload_file(
        self,
        file_data: bytes,
        filename: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        上傳檔案（二進位資料）至 Box Storage，若失敗則自動切換至 Fallback 節點。
        
        Returns:
            dict: { "id": "...", "url": "https://d36gp3xejpe77o.cloudfront.net/...", "share_url": "..." }
            None: 若所有節點皆上傳失敗
        """
        for endpoint in self.endpoints:
            api_url = f"{endpoint}/api.php?action=upload"
            try:
                files = {
                    'file': (filename, file_data, mime_type or 'application/octet-stream')
                }
                data = {}
                if title:
                    data['title'] = title
                if description:
                    data['description'] = description
                if self.token:
                    data['token'] = self.token

                logger.info(f"Uploading file '{filename}' to Box endpoint: {endpoint}")
                resp = requests.post(api_url, files=files, data=data, timeout=self.timeout)
                if resp.status_code == 200:
                    res_json = resp.json()
                    if res_json.get("result") == "success" and "data" in res_json:
                        logger.info(f"Successfully uploaded '{filename}' to {endpoint}. CDN URL: {res_json['data'].get('url')}")
                        return res_json["data"]
                    else:
                        logger.warning(f"Box upload to {endpoint} returned non-success: {res_json}")
                else:
                    logger.warning(f"Box upload to {endpoint} failed with HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logger.warning(f"Error uploading to Box endpoint {endpoint}: {e}")
                continue

        logger.error(f"All Box storage endpoints failed to upload file '{filename}'")
        return None

    def upload_url(
        self,
        url: str,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        透過遠端 URL 直接轉存至 Box Storage。
        """
        for endpoint in self.endpoints:
            api_url = f"{endpoint}/api.php?action=upload_url"
            try:
                data = {'url': url}
                if title:
                    data['title'] = title
                if description:
                    data['description'] = description
                if self.token:
                    data['token'] = self.token

                logger.info(f"Ingesting remote asset from '{url}' to Box endpoint: {endpoint}")
                resp = requests.post(api_url, data=data, timeout=self.timeout)
                if resp.status_code == 200:
                    res_json = resp.json()
                    if res_json.get("result") == "success" and "data" in res_json:
                        logger.info(f"Successfully ingested asset to {endpoint}. CDN URL: {res_json['data'].get('url')}")
                        return res_json["data"]
                    else:
                        logger.warning(f"Box upload_url to {endpoint} returned non-success: {res_json}")
                else:
                    logger.warning(f"Box upload_url to {endpoint} failed with HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logger.warning(f"Error calling upload_url on {endpoint}: {e}")
                continue

        logger.error(f"All Box storage endpoints failed to ingest asset from URL '{url}'")
        return None

    def get_stats(self) -> Optional[Dict[str, Any]]:
        """
        獲取 Box Storage 統計資訊
        """
        for endpoint in self.endpoints:
            api_url = f"{endpoint}/api.php?action=stats"
            try:
                resp = requests.get(api_url, timeout=self.timeout)
                if resp.status_code == 200:
                    res_json = resp.json()
                    if res_json.get("result") == "success":
                        return res_json.get("data")
            except Exception as e:
                logger.warning(f"Error fetching stats from {endpoint}: {e}")
                continue
        return None
