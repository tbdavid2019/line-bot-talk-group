import os
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock

# Mock external dependencies for test execution
for mod_name in [
    'linebot', 'linebot.v3', 'linebot.v3.webhook', 'linebot.v3.messaging',
    'linebot.v3.exceptions', 'linebot.v3.webhooks', 'fastapi',
    'fastapi.responses', 'firebase', 'google.generativeai',
    'google.genai', 'google.genai.types', 'google.cloud', 'google.cloud.storage'
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = types.ModuleType(mod_name)

class TextMessage:
    def __init__(self, text: str):
        self.text = text

class ReplyMessageRequest:
    def __init__(self, reply_token: str, messages: list):
        self.reply_token = reply_token
        self.messages = messages

class PushMessageRequest:
    def __init__(self, to: str, messages: list):
        self.to = to
        self.messages = messages

class FlexMessage:
    pass

class FlexContainer:
    pass

sys.modules['linebot.v3.messaging'].TextMessage = TextMessage
sys.modules['linebot.v3.messaging'].ReplyMessageRequest = ReplyMessageRequest
sys.modules['linebot.v3.messaging'].PushMessageRequest = PushMessageRequest
sys.modules['linebot.v3.messaging'].FlexMessage = FlexMessage
sys.modules['linebot.v3.messaging'].FlexContainer = FlexContainer
sys.modules['linebot.v3.messaging'].AsyncApiClient = MagicMock()
sys.modules['linebot.v3.messaging'].AsyncMessagingApi = MagicMock()
sys.modules['linebot.v3.messaging'].AsyncMessagingApiBlob = MagicMock()
sys.modules['linebot.v3.messaging'].Configuration = MagicMock()
sys.modules['linebot.v3.messaging'].ImageMessage = MagicMock()
sys.modules['linebot.v3.exceptions'].InvalidSignatureError = type('InvalidSignatureError', (Exception,), {})
sys.modules['linebot.v3.webhook'].WebhookParser = MagicMock()
sys.modules['linebot.v3.webhooks'].MessageEvent = type('MessageEvent', (), {})
sys.modules['linebot.v3.webhooks'].TextMessageContent = type('TextMessageContent', (), {})
sys.modules['linebot.v3.webhooks'].AudioMessageContent = type('AudioMessageContent', (), {})
sys.modules['linebot.v3.webhooks'].FileMessageContent = type('FileMessageContent', (), {})
sys.modules['fastapi'].FastAPI = MagicMock()
sys.modules['fastapi'].HTTPException = type('HTTPException', (Exception,), {})
sys.modules['fastapi'].Request = MagicMock()
sys.modules['fastapi.responses'].PlainTextResponse = MagicMock()
sys.modules['firebase'].firebase = MagicMock()
sys.modules['google.generativeai'].configure = MagicMock()
sys.modules['google.generativeai'].GenerativeModel = MagicMock()
sys.modules['google.genai'].Client = MagicMock()

os.environ['LINE_CHANNEL_SECRET'] = 'mock_secret'
os.environ['LINE_CHANNEL_ACCESS_TOKEN'] = 'mock_token'

from main import safe_reply_message


class TestSafeReply(unittest.IsolatedAsyncioTestCase):

    async def test_safe_reply_success_uses_reply_message(self):
        line_bot_api = MagicMock()
        line_bot_api.reply_message = AsyncMock()
        line_bot_api.push_message = AsyncMock()

        event = MagicMock()
        event.reply_token = "valid_reply_token_123"
        event.source.group_id = "group_abc"

        messages = [TextMessage(text="Hello world")]

        result = await safe_reply_message(line_bot_api, event, messages)

        self.assertTrue(result)
        line_bot_api.reply_message.assert_awaited_once()
        call_args = line_bot_api.reply_message.await_args[0][0]
        self.assertEqual(call_args.reply_token, "valid_reply_token_123")
        self.assertEqual(call_args.messages, messages)

        # push_message should NOT be called when reply_message succeeds
        line_bot_api.push_message.assert_not_awaited()

    async def test_safe_reply_fallback_to_push_for_group(self):
        line_bot_api = MagicMock()
        line_bot_api.reply_message = AsyncMock(side_effect=Exception("Invalid reply token (expired)"))
        line_bot_api.push_message = AsyncMock()

        event = MagicMock()
        event.reply_token = "expired_token_456"
        event.source.group_id = "group_xyz"
        event.source.user_id = "user_123"

        messages = [TextMessage(text="Push fallback message")]

        result = await safe_reply_message(line_bot_api, event, messages)

        self.assertTrue(result)
        line_bot_api.reply_message.assert_awaited_once()
        line_bot_api.push_message.assert_awaited_once()
        push_call_args = line_bot_api.push_message.await_args[0][0]
        self.assertEqual(push_call_args.to, "group_xyz")
        self.assertEqual(push_call_args.messages, messages)

    async def test_safe_reply_fallback_to_push_for_user(self):
        line_bot_api = MagicMock()
        line_bot_api.reply_message = AsyncMock(side_effect=Exception("Reply token expired after 35s"))
        line_bot_api.push_message = AsyncMock()

        event = MagicMock()
        event.reply_token = "expired_token_789"
        event.source.group_id = None
        event.source.room_id = None
        event.source.user_id = "user_single_direct"

        messages = [TextMessage(text="Direct user fallback")]

        result = await safe_reply_message(line_bot_api, event, messages)

        self.assertTrue(result)
        line_bot_api.reply_message.assert_awaited_once()
        line_bot_api.push_message.assert_awaited_once()
        push_call_args = line_bot_api.push_message.await_args[0][0]
        self.assertEqual(push_call_args.to, "user_single_direct")
        self.assertEqual(push_call_args.messages, messages)

    async def test_safe_reply_handles_push_failure_gracefully(self):
        line_bot_api = MagicMock()
        line_bot_api.reply_message = AsyncMock(side_effect=Exception("Reply timeout"))
        line_bot_api.push_message = AsyncMock(side_effect=Exception("Push network error"))

        event = MagicMock()
        event.reply_token = "token_err"
        event.source.group_id = "group_err"

        messages = [TextMessage(text="Fail gracefully")]

        result = await safe_reply_message(line_bot_api, event, messages)

        self.assertFalse(result)
        line_bot_api.reply_message.assert_awaited_once()
        line_bot_api.push_message.assert_awaited_once()

    async def test_safe_reply_handles_missing_target_id(self):
        line_bot_api = MagicMock()
        line_bot_api.reply_message = AsyncMock(side_effect=Exception("Reply timeout"))
        line_bot_api.push_message = AsyncMock()

        event = MagicMock()
        event.reply_token = "token_notarget"
        event.source.group_id = None
        event.source.room_id = None
        event.source.user_id = None

        messages = [TextMessage(text="No target ID")]

        result = await safe_reply_message(line_bot_api, event, messages)

        self.assertFalse(result)
        line_bot_api.reply_message.assert_awaited_once()
        line_bot_api.push_message.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
