import base64
import hashlib
import hmac
import json
import mimetypes
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import requests


GOOGLE_OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
GOOGLE_DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"

DRIVE_SCOPE_FILE = "https://www.googleapis.com/auth/drive.file"


def now_ts() -> int:
    return int(time.time())


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * ((4 - (len(s) % 4)) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("ascii"))


def generate_bind_code(prefix: str = "GDRIVE", length: int = 5) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    suffix = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}-{suffix}"


def get_encryption_key() -> str:
    key = os.getenv("TOKEN_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is required")
    return key


def get_state_signing_key() -> str:
    key = os.getenv("OAUTH_STATE_SIGNING_KEY")
    if not key:
        raise RuntimeError("OAUTH_STATE_SIGNING_KEY is required")
    return key


def encrypt_refresh_token(refresh_token: str) -> str:
    try:
        import importlib

        Fernet = importlib.import_module("cryptography.fernet").Fernet
    except Exception as e:
        raise RuntimeError("cryptography is required for token encryption") from e
    f = Fernet(get_encryption_key().encode("ascii"))
    return f.encrypt(refresh_token.encode("utf-8")).decode("ascii")


def decrypt_refresh_token(refresh_token_enc: str) -> str:
    try:
        import importlib

        Fernet = importlib.import_module("cryptography.fernet").Fernet
    except Exception as e:
        raise RuntimeError("cryptography is required for token decryption") from e
    f = Fernet(get_encryption_key().encode("ascii"))
    return f.decrypt(refresh_token_enc.encode("ascii")).decode("utf-8")


def _hmac_secret() -> bytes:
    return get_state_signing_key().encode("ascii")


def sign_state(payload: Dict[str, Any]) -> str:
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(_hmac_secret(), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64url_encode(sig)}"


def verify_state(state: str) -> Dict[str, Any]:
    try:
        body_b64, sig_b64 = state.split(".", 1)
    except ValueError as e:
        raise ValueError("Invalid state format") from e

    expected = hmac.new(_hmac_secret(), body_b64.encode("ascii"), hashlib.sha256).digest()
    got = _b64url_decode(sig_b64)
    if not hmac.compare_digest(expected, got):
        raise ValueError("Invalid state signature")

    payload = json.loads(_b64url_decode(body_b64).decode("utf-8"))
    exp = payload.get("exp")
    if not isinstance(exp, int) or now_ts() > exp:
        raise ValueError("State expired")

    return payload


def build_google_oauth_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    scope: str = DRIVE_SCOPE_FILE,
) -> str:
    # NOTE: prompt=consent is important to reliably get refresh_token.
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": state,
    }
    from urllib.parse import urlencode

    return f"{GOOGLE_OAUTH_AUTH_URL}?{urlencode(params)}"


def safe_filename(name: str, fallback: str = "file") -> str:
    name = (name or "").strip()
    if not name:
        name = fallback

    # Prevent path traversal and strip control chars.
    name = name.replace("/", "_").replace("\\", "_")
    cleaned = []
    for ch in name:
        if ch.isprintable() and ch not in "\r\n\t":
            cleaned.append(ch)
        else:
            cleaned.append("_")
    name = "".join(cleaned)

    # Keep it reasonable.
    if len(name) > 180:
        root, ext = os.path.splitext(name)
        root = root[:160]
        ext = ext[:20]
        name = root + ext
    return name


@dataclass(frozen=True)
class OAuthTokens:
    access_token: str
    expires_in: int
    refresh_token: Optional[str]
    scope: Optional[str]
    token_type: Optional[str]


def exchange_code_for_tokens(
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
    timeout_s: int = 20,
) -> OAuthTokens:
    resp = requests.post(
        GOOGLE_OAUTH_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=timeout_s,
    )
    resp.raise_for_status()
    data = resp.json()
    return OAuthTokens(
        access_token=data["access_token"],
        expires_in=int(data.get("expires_in", 0)),
        refresh_token=data.get("refresh_token"),
        scope=data.get("scope"),
        token_type=data.get("token_type"),
    )


def refresh_access_token(
    *,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    timeout_s: int = 20,
) -> str:
    resp = requests.post(
        GOOGLE_OAUTH_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=timeout_s,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["access_token"]


def _drive_headers(access_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def drive_find_folder(
    *,
    access_token: str,
    name: str,
    parent_id: Optional[str] = None,
    timeout_s: int = 20,
) -> Optional[Tuple[str, str]]:
    # Returns (file_id, name) if found.

    def esc(value: str) -> str:
        # Google Drive query escaping for single-quoted strings.
        return value.replace("'", "\\'")

    q = [
        "mimeType='application/vnd.google-apps.folder'",
        f"name='{esc(name)}'",
        "trashed=false",
    ]
    if parent_id:
        q.append(f"'{parent_id}' in parents")

    resp = requests.get(
        GOOGLE_DRIVE_FILES_URL,
        headers=_drive_headers(access_token),
        params={
            "q": " and ".join(q),
            "fields": "files(id,name)",
            "pageSize": 1,
        },
        timeout=timeout_s,
    )
    resp.raise_for_status()
    files = resp.json().get("files", [])
    if not files:
        return None
    return files[0]["id"], files[0].get("name", name)


def drive_create_folder(
    *,
    access_token: str,
    name: str,
    parent_id: Optional[str] = None,
    timeout_s: int = 20,
) -> Tuple[str, str]:
    body: Dict[str, Any] = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        body["parents"] = [parent_id]

    resp = requests.post(
        GOOGLE_DRIVE_FILES_URL,
        headers={**_drive_headers(access_token), "Content-Type": "application/json"},
        json=body,
        params={"fields": "id,name"},
        timeout=timeout_s,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["id"], data.get("name", name)


def drive_ensure_folder(
    *,
    access_token: str,
    name: str,
    parent_id: Optional[str] = None,
) -> Tuple[str, str]:
    found = drive_find_folder(access_token=access_token, name=name, parent_id=parent_id)
    if found:
        return found
    return drive_create_folder(access_token=access_token, name=name, parent_id=parent_id)


def drive_resumable_upload(
    *,
    access_token: str,
    file_path: str,
    filename: str,
    folder_id: str,
    mime_type: Optional[str] = None,
    timeout_s: int = 60,
) -> str:
    if not mime_type:
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    size = os.path.getsize(file_path)
    metadata = {"name": filename, "parents": [folder_id]}

    init_resp = requests.post(
        f"{GOOGLE_DRIVE_UPLOAD_URL}?uploadType=resumable",
        headers={
            **_drive_headers(access_token),
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": mime_type,
            "X-Upload-Content-Length": str(size),
        },
        json=metadata,
        timeout=timeout_s,
    )
    init_resp.raise_for_status()
    upload_url = init_resp.headers.get("Location")
    if not upload_url:
        raise RuntimeError("Drive resumable upload did not return Location header")

    with open(file_path, "rb") as f:
        put_resp = requests.put(
            upload_url,
            headers={
                "Content-Length": str(size),
                "Content-Type": mime_type,
            },
            data=f,
            timeout=timeout_s,
        )
    put_resp.raise_for_status()
    data = put_resp.json()
    return data["id"]
