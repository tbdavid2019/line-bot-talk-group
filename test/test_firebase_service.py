import unittest


class FakeDatabase:
    def __init__(self):
        self.values = {}
        self.posts = []
        self.writes = []
        self.deletes = []

    def get(self, path, name):
        return self.values.get((path, name))

    def post(self, path, value):
        self.posts.append((path, value))
        return {"name": f"push-{len(self.posts)}"}

    def delete(self, path, name):
        self.deletes.append((path, name))
        self.values.pop((path, name), None)

    def put(self, path, name, value):
        self.writes.append((path, name, value))


class FirebaseServiceTests(unittest.TestCase):
    def test_append_message_uses_append_only_event_collection(self):
        from services.firebase import FirebaseService

        db = FakeDatabase()
        service = FirebaseService(db)

        service.append_message(
            "groups/group-1",
            {"role": "user", "parts": ["hello"], "timestamp": "2"},
            message_id="line-message-1",
        )

        self.assertEqual(
            db.posts,
            [
                (
                    "groups/group-1/message_events",
                    {
                        "role": "user",
                        "parts": ["hello"],
                        "timestamp": "2",
                        "message_id": "line-message-1",
                    },
                )
            ],
        )

    def test_get_messages_orders_legacy_and_append_only_records(self):
        from services.firebase import FirebaseService

        db = FakeDatabase()
        db.values[("groups/group-1", "messages")] = [
            {"role": "user", "parts": ["old"], "timestamp": "10"},
        ]
        db.values[("groups/group-1/message_events", None)] = {
            "newer": {"role": "model", "parts": ["new"], "timestamp": "20"},
            "earlier": {"role": "user", "parts": ["earlier"], "timestamp": "15"},
        }

        messages = FirebaseService(db).get_messages("groups/group-1")

        self.assertEqual([message["parts"][0] for message in messages], ["old", "earlier", "new"])

    def test_acquire_message_lock_returns_false_when_conditional_write_conflicts(self):
        from services.firebase import FirebaseService

        calls = []

        def conditional_put(url, **kwargs):
            calls.append((url, kwargs))
            return type("Response", (), {"status_code": 412, "text": "already exists"})()

        service = FirebaseService(
            FakeDatabase(),
            firebase_url="https://example.firebaseio.com",
            conditional_put=conditional_put,
            now=lambda: 100,
        )

        self.assertFalse(service.acquire_message_lock("message-1", ttl_seconds=300))
        self.assertEqual(calls[0][0], "https://example.firebaseio.com/processed_events/message-1.json")
        self.assertEqual(calls[0][1]["headers"]["if-match"], "null_etag")

    def test_clear_messages_removes_legacy_and_append_only_records(self):
        from services.firebase import FirebaseService

        db = FakeDatabase()
        db.values[("groups/group-1", "messages")] = ["legacy"]
        db.values[("groups/group-1/message_events", None)] = {"event": "new"}

        FirebaseService(db).clear_messages("groups/group-1")

        self.assertNotIn(("groups/group-1", "messages"), db.values)
        self.assertNotIn(("groups/group-1/message_events", None), db.values)

    def test_read_write_and_delete_delegate_to_database(self):
        from services.firebase import FirebaseService

        db = FakeDatabase()
        service = FirebaseService(db)
        db.values[("groups/group-1/info", "drive_export")] = {"enabled": True}

        self.assertEqual(
            service.read("groups/group-1/info", "drive_export"), {"enabled": True}
        )
        service.write("groups/group-1/info", "drive_export", {"enabled": False})
        service.delete("groups/group-1/info", "drive_export")

        self.assertEqual(db.writes, [("groups/group-1/info", "drive_export", {"enabled": False})])
        self.assertEqual(db.deletes, [("groups/group-1/info", "drive_export")])
