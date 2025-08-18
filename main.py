import logging
import os
import sys
if os.getenv('API_ENV') != 'production':
    from dotenv import load_dotenv

    load_dotenv()


from fastapi import FastAPI, HTTPException, Request
from linebot.v3.webhook import WebhookParser
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    ReplyMessageRequest,
    TextMessage)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
)
import google.generativeai as genai
import uvicorn
from firebase import firebase

logging.basicConfig(level=os.getenv('LOG', 'WARNING'))
logger = logging.getLogger(__file__)

app = FastAPI()

channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

configuration = Configuration(
    access_token=channel_access_token
)

parser = WebhookParser(channel_secret)


firebase_url = os.getenv('FIREBASE_URL')
gemini_key = os.getenv('GEMINI_API_KEY')
gemini_model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
bot_line_id = os.getenv('LINE_BOT_ID', '377mwhqu')  # Bot 的 LINE ID


# Initialize the Gemini Pro API
genai.configure(api_key=gemini_key)


def is_bot_mentioned(event, bot_id=None):
    """
    檢查是否 Bot 被提及
    
    Args:
        event: LINE webhook event
        bot_id: Bot 的 LINE ID（可選）
    
    Returns:
        bool: True 如果 Bot 被提及，False 否則
    """
    if not isinstance(event.message, TextMessageContent):
        return False
    
    text = event.message.text
    mention = getattr(event.message, 'mention', None)
    
    # 方法1: 檢查 mention 物件中是否包含特定的用戶ID
    if mention and hasattr(mention, 'mentionees'):
        # 注意：這需要知道 Bot 的實際 user_id，通常格式為 U開頭
        # 但我們可能無法直接獲取到 Bot 自己的 user_id
        pass
    
    # 方法2: 檢查文字中是否包含 Bot 的官方 ID
    if bot_id:
        # 檢查是否包含 @bot_id 格式（確保 @ 前面沒有其他字符）
        import re
        bot_patterns = [
            rf'(?<![a-zA-Z0-9])@{re.escape(bot_id)}(?![a-zA-Z0-9])',
            rf'(?<![a-zA-Z0-9])＠{re.escape(bot_id)}(?![a-zA-Z0-9])',
            rf'(?<![a-zA-Z0-9])@{re.escape(bot_id.lower())}(?![a-zA-Z0-9])',
            rf'(?<![a-zA-Z0-9])＠{re.escape(bot_id.lower())}(?![a-zA-Z0-9])'
        ]
        
        for pattern in bot_patterns:
            if re.search(pattern, text):
                logging.info(f"Bot mentioned with pattern: {pattern}")
                return True
    
    # 方法3: 檢查是否有 mention 且文字包含關鍵詞
    if mention:
        # 檢查常見的 Bot 呼叫方式
        bot_keywords = ['bot', 'Bot', 'BOT', '機器人', '摘要王']
        if any(keyword in text for keyword in bot_keywords):
            logging.info(f"Bot mentioned with keyword in text: {text}")
            return True
    
    return False


@app.get("/health")
async def health():
    return 'ok'

@app.get("/")
async def root():
    return {"message": "LINE Bot is running", "status": "ok"}


@app.post("/webhooks/line")
async def handle_callback(request: Request):
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = await request.body()
    body = body.decode()

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 創建 async client 在 async 函數內
    async_api_client = AsyncApiClient(configuration)
    line_bot_api = AsyncMessagingApi(async_api_client)
    
    try:
        for event in events:
            logging.info(event)
            if not isinstance(event, MessageEvent):
                continue
            if not isinstance(event.message, TextMessageContent):
                continue
            text = event.message.text
            user_id = event.source.user_id

            msg_type = event.message.type
            fdb = firebase.FirebaseApplication(firebase_url, None)
            
            # 設定 Firebase 路徑
            if event.source.type == 'group':
                user_chat_path = f'groups/{event.source.group_id}'
            else:
                user_chat_path = f'users/{user_id}'
            
            # 決定是否要回應
            should_reply = False
            is_ai_question = False  # 是否為 AI 問答模式
            special_commands = ['!清空', '!clean',  '!摘要','!總結','!summary', '！清空', '！摘要', '!help', '!幫助', '！help', '！幫助']
            
            if event.source.type == 'group':
                # 檢查是否真的提及了 Bot
                bot_mentioned = is_bot_mentioned(event, bot_line_id)
                
                # 檢查是否包含特殊指令
                has_special_command = any(cmd in text.lower() for cmd in special_commands)
                
                if bot_mentioned and not has_special_command:
                    # Bot 被提及但不是特殊指令 = AI 問答模式
                    should_reply = True
                    is_ai_question = True
                    logging.info(f"Bot mentioned - AI question mode: '{text}'")
                elif has_special_command:
                    # 特殊指令
                    should_reply = True
                    logging.info(f"Group message with special command: '{text}'")
                else:
                    logging.info(f"Recording group message (no reply): '{text}'")
            else:
                # 私人對話：所有訊息都回應
                should_reply = True
                # 檢查是否為特殊指令
                has_special_command = any(cmd in text.lower() for cmd in special_commands)
                if not has_special_command:
                    # 一般對話模式
                    logging.info(f"Private conversation mode: '{text}'")
                else:
                    logging.info(f"Private message with special command: '{text}'")
            
            # 獲取現有對話記錄
            try:
                chatgpt = fdb.get(user_chat_path, 'messages')
                if chatgpt is None:
                    messages = []
                else:
                    messages = chatgpt if isinstance(chatgpt, list) else []
            except Exception as e:
                logging.warning(f"Failed to get messages from Firebase: {e}")
                messages = []

            if msg_type == 'text':
                # 所有訊息都記錄到 Firebase
                messages.append({'role': 'user', 'parts': [text], 'timestamp': str(event.timestamp)})
                
                reply_msg = ""
                
                # 只有在需要回應時才處理
                if should_reply:
                    if text.lower() in ['!清空', '！清空', '!clean']:
                        try:
                            fdb.delete(user_chat_path, 'messages')
                            reply_msg = '------對話歷史紀錄已經清空------'
                            # 清空後重置 messages
                            messages = []
                        except Exception as e:
                            logging.error(f"Failed to clear Firebase data: {e}")
                            reply_msg = '清空對話記錄時發生錯誤，請稍後再試'

                    elif text.lower() in ['!摘要', '！摘要', '!總結', '！總結', '！summary']:
                        if len(messages) > 1:  # 確保有對話內容可以摘要
                            try:
                                model = genai.GenerativeModel(gemini_model)
                                # 準備給 Gemini 的訊息格式（移除 timestamp 欄位）
                                gemini_messages = []
                                for msg in messages:
                                    gemini_msg = {
                                        'role': msg['role'],
                                        'parts': msg['parts']
                                    }
                                    gemini_messages.append(gemini_msg)
                                
                                response = model.generate_content(
                                    f'Summary the following message in Traditional Chinese by less 5 list points. \n{gemini_messages}')
                                reply_msg = response.text
                                # 記錄摘要回應
                                messages.append({'role': 'model', 'parts': [reply_msg], 'timestamp': str(event.timestamp)})
                            except Exception as e:
                                logging.error(f"Error generating summary: {e}")
                                reply_msg = "抱歉，產生摘要時發生錯誤，請稍後再試。"
                        else:
                            reply_msg = '目前沒有足夠的對話紀錄可以摘要'
                            messages.append({'role': 'model', 'parts': [reply_msg], 'timestamp': str(event.timestamp)})
                    
                    elif text.lower() in ['!help', '!幫助', '！help', '！幫助']:
                        reply_msg = """🤖 群組摘要王 使用說明

**群組功能：**
• @ 機器人 + 問題：進入 AI 問答模式
  例：@Bot 什麼是梯度下降？

• !摘要 或 ！摘要：產生對話摘要
• !清空 或 ！清空：清空對話記錄
• !help 或 !幫助：顯示此說明

**私人功能：**
• 直接傳送訊息即可與 AI 對話
• 支援所有群組指令

**注意事項：**
• 群組中只有 @ 提及或特殊指令才會回應
• AI 問答為一次性回答，不會記錄到對話歷史
• 所有訊息都會被記錄以供摘要功能使用"""
                        # 幫助訊息不記錄到對話歷史
                        
                    elif is_ai_question:
                        # AI 問答模式：一次性回答，不記錄到對話歷史（群組中的 @ 提及）
                        try:
                            model = genai.GenerativeModel(gemini_model)
                            # 移除 @ 提及部分，只保留問題
                            clean_question = text
                            if hasattr(event.message, 'mention') and event.message.mention:
                                # 如果有 mention 資訊，移除被提及的部分
                                mention = event.message.mention
                                for mentioned_user in mention.mentionees:
                                    if mentioned_user.user_id:
                                        # 簡單的文字清理，移除可能的 @ 符號
                                        clean_question = text.replace('@', '').strip()
                            
                            response = model.generate_content(f"請用繁體中文回答以下問題：{clean_question}")
                            reply_msg = response.text
                            # AI 問答不記錄到對話歷史，所以移除剛加入的訊息
                            messages.pop()  # 移除剛才加入的用戶訊息
                        except Exception as e:
                            logging.error(f"Error in AI question mode: {e}")
                            reply_msg = "抱歉，處理您的問題時發生錯誤，請稍後再試。"
                            messages.pop()  # 移除剛才加入的用戶訊息
                            
                    else:
                        # 一般對話（私人對話或群組中的其他情況）
                        try:
                            model = genai.GenerativeModel(gemini_model)
                            # 準備給 Gemini 的訊息格式（移除 timestamp 欄位）
                            gemini_messages = []
                            for msg in messages:
                                gemini_msg = {
                                    'role': msg['role'],
                                    'parts': msg['parts']
                                }
                                gemini_messages.append(gemini_msg)
                            
                            response = model.generate_content(gemini_messages)
                            reply_msg = response.text
                            messages.append({'role': 'model', 'parts': [reply_msg], 'timestamp': str(event.timestamp)})
                            logging.info(f"Generated AI response for general conversation: {reply_msg[:50]}...")
                        except Exception as e:
                            logging.error(f"Error in general conversation: {e}")
                            reply_msg = "抱歉，處理您的訊息時發生錯誤，請稍後再試。"
                
                # 更新 Firebase 中的對話紀錄
                # AI 問答模式和幫助訊息不記錄到對話歷史
                if not is_ai_question and not (text.lower() in ['!help', '!幫助', '！help', '！幫助']):
                    try:
                        fdb.put(user_chat_path, 'messages', messages)
                        logging.info(f"Saved message to Firebase: {user_chat_path}")
                    except Exception as e:
                        logging.error(f"Failed to save to Firebase: {e}")
                else:
                    logging.info(f"Skipped saving to Firebase (AI question or help): {text[:50]}...")

                # 發送回應（只有在需要回應時）
                if should_reply and reply_msg:
                    await line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text=reply_msg)]
                        ))
    
    finally:
        # 關閉 async client
        await async_api_client.close()

    return 'OK'

if __name__ == "__main__":
    port = int(os.environ.get('PORT', default=8080))
    debug = True if os.environ.get(
        'API_ENV', default='develop') == 'develop' else False
    logging.info('Application will start...')
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=debug)
