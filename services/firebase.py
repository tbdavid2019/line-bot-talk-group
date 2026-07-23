"""Firebase Realtime Database access used by webhook processing."""

from __future__ import annotations

import time
from typing import Any, Callable
from urllib.parse import quote

import requests


class FirebaseService:
    """Keep transcript persistence and idempotency outside HTTP handlers."""

    def __init__(
        self,
        database: Any,
        firebase_url: str | None = None,
        auth: Any = None,
        conditional_put: Callable[..., Any] = requests.put,
        now: Callable[[], float] = time.time,
    ) -> None:
        self.database = database
        self.firebase_url = firebase_url.rstrip("/") if firebase_url else None
        self.auth = auth
        self.conditional_put = conditional_put
        self.now = now

    def get_messages(self, conversation_path: str) -> list[dict[str, Any]]:
        """Read legacy list records and append-only records in timestamp order."""
        legacy = self.database.get(conversation_path, "messages") or []
        events = self.database.get(f"{conversation_path}/message_events", None) or {}

        records: list[dict[str, Any]] = []
        if isinstance(legacy, list):
            records.extend(record for record in legacy if isinstance(record, dict))
        if isinstance(events, dict):
            records.extend(record for record in events.values() if isinstance(record, dict))

        return sorted(records, key=self._message_sort_key)

    def read(self, path: str, name: str | None = None) -> Any:
        return self.database.get(path, name)

    def write(self, path: str, name: str, value: Any) -> Any:
        return self.database.put(path, name, value)

    def delete(self, path: str, name: str | None = None) -> Any:
        return self.database.delete(path, name)

    def append_message(
        self,
        conversation_path: str,
        message: dict[str, Any],
        message_id: str | None = None,
    ) -> Any:
        """Append one record without overwriting concurrent conversation updates."""
        record = dict(message)
        if message_id:
            record["message_id"] = message_id
        return self.database.post(f"{conversation_path}/message_events", record)

    def clear_messages(self, conversation_path: str) -> None:
        """Clear both the legacy transcript and the append-only replacement."""
        self.database.delete(conversation_path, "messages")
        self.database.delete(f"{conversation_path}/message_events", None)

    def acquire_message_lock(self, message_id: str, ttl_seconds: int = 300) -> bool:
        """Atomically claim a LINE message ID using RTDB conditional creation.

        A 412 response means another process already owns the event.  The expiry
        is retained for operational cleanup and future retry handling; a stale
        lock is intentionally not overwritten by this method.
        """
        if not self.firebase_url:
            raise RuntimeError("FIREBASE_URL is required for message deduplication")

        safe_message_id = quote(message_id, safe="")
        url = f"{self.firebase_url}/processed_events/{safe_message_id}.json"
        payload = {
            "status": "pending",
            "created_at": int(self.now()),
            "expires_at": int(self.now()) + ttl_seconds,
        }
        params = self._auth_params()
        response = self.conditional_put(
            url,
            params=params,
            headers={"if-match": "null_etag"},
            json=payload,
            timeout=10,
        )
        if response.status_code == 200:
            return True
        if response.status_code == 412:
            return False
        raise RuntimeError(
            f"Unable to claim message lock ({response.status_code}): {response.text[:200]}"
        )

    @staticmethod
    def _message_sort_key(message: dict[str, Any]) -> tuple[int, str]:
        timestamp = message.get("timestamp", 0)
        try:
            return int(timestamp), str(message.get("message_id", ""))
        except (TypeError, ValueError):
            return 0, str(message.get("message_id", ""))

    def _auth_params(self) -> dict[str, str]:
        if not self.auth:
            return {}
        if isinstance(self.auth, str):
            return {"auth": self.auth}
        return {"access_token": self.auth.get_access_token()}
