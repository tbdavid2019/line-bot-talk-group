import logging
import os
import sys
import base64
import mimetypes
import uuid
import tempfile
import asyncio
from datetime import datetime
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
    PushMessageRequest,
    TextMessage,
    ImageMessage)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
)
import google.generativeai as genai
from google import genai as genai_v2
from google.genai import types
from google.cloud import storage
import uvicorn
from firebase import firebase

logging.basicConfig(
    level=os.getenv('LOG', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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

# Gemini LLM 設定（文字對話、摘要等）
gemini_llm_key = os.getenv('GEMINI_LLM_API_KEY')
gemini_llm_model = os.getenv('GEMINI_LLM_MODEL', 'gemini-1.5-pro')

# Gemini Image 設定（圖片生成）
gemini_image_key = os.getenv('GEMINI_IMAGE_API_KEY')
gemini_image_model = os.getenv('GEMINI_IMAGE_MODEL', 'gemini-2.5-flash-image-preview')

# 為了向後相容，如果沒有設定分離的 key，就使用舊的設定
if not gemini_llm_key:
    gemini_llm_key = os.getenv('GEMINI_API_KEY')
if not gemini_image_key:
    gemini_image_key = os.getenv('GEMINI_API_KEY')
if not gemini_llm_model and os.getenv('GEMINI_MODEL'):
    gemini_llm_model = os.getenv('GEMINI_MODEL')

bot_line_id = os.getenv('LINE_BOT_ID', '377mwhqu')  # Bot 的 LINE ID

# Google Cloud Storage 設定
gcs_bucket_name = os.getenv('GCS_BUCKET_NAME')  # 你的 Google Cloud Storage bucket 名稱
gcs_credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')  # Google Cloud 認證檔案路徑


# Initialize the Gemini LLM API
genai.configure(api_key=gemini_llm_key)

# Initialize Google Cloud Storage client
if gcs_credentials_path and gcs_bucket_name:
    try:
        logging.info(f"Initializing Google Cloud Storage...")
        logging.info(f"GCS bucket name: {gcs_bucket_name}")
        logging.info(f"GCS credentials path: {gcs_credentials_path}")
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(gcs_bucket_name)
        
        # 測試 bucket 是否存在
        if bucket.exists():
            logging.info(f"Successfully connected to GCS bucket: {gcs_bucket_name}")
        else:
            logging.error(f"GCS bucket does not exist: {gcs_bucket_name}")
            bucket = None
            
    except Exception as e:
        logging.error(f"Failed to initialize Google Cloud Storage: {e}")
        storage_client = None
        bucket = None
else:
    logging.warning("Google Cloud Storage not configured. Image generation will be disabled.")
    logging.warning(f"GCS_BUCKET_NAME: {gcs_bucket_name}")
    logging.warning(f"GOOGLE_APPLICATION_CREDENTIALS: {gcs_credentials_path}")
    storage_client = None
    bucket = None


async def upload_image_to_gcs(image_data, filename):
    """
    上傳圖片到 Google Cloud Storage 並返回公開 URL
    
    Args:
        image_data: 圖片的二進位資料
        filename: 檔案名稱
    
    Returns:
        str: 圖片的公開 URL，如果失敗則返回 None
    """
    logging.info(f"Starting upload_image_to_gcs - filename: {filename}")
    logging.info(f"Image data type: {type(image_data)}, size: {len(image_data) if image_data else 'None'}")
    
    if not bucket:
        logging.error("Google Cloud Storage not configured - bucket is None")
        logging.error(f"GCS bucket name: {gcs_bucket_name}")
        logging.error(f"GCS credentials path: {gcs_credentials_path}")
        return None
    
    try:
        # 建立唯一的檔案名稱
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"linebot_images/{timestamp}_{filename}"
        logging.info(f"Generated unique filename: {unique_filename}")
        
        # 上傳到 GCS
        logging.info(f"Creating blob in bucket: {bucket.name}")
        blob = bucket.blob(unique_filename)
        
        logging.info("Starting upload to GCS...")
        blob.upload_from_string(image_data)
        logging.info("Upload completed successfully")
        
        # 對於啟用了 uniform bucket-level access 的 bucket，
        # 我們不需要呼叫 make_public()，而是直接使用公開 URL
        logging.info("Generating public URL (uniform bucket-level access enabled)...")
        
        # 直接構建公開 URL
        public_url = f"https://storage.googleapis.com/{bucket.name}/{unique_filename}"
        logging.info(f"Image uploaded successfully: {public_url}")
        logging.info(f"Blob exists: {blob.exists()}")
        return public_url
        
    except Exception as e:
        logging.error(f"Failed to upload image to GCS: {e}")
        logging.error(f"Exception type: {type(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return None


async def generate_image_with_gemini(prompt, max_retries=1, retry_delay=15):
    """
    使用 Gemini 生成圖片
    
    Args:
        prompt: 圖片生成的提示詞
        max_retries: 最大重試次數
        retry_delay: 重試延遲（秒）
    
    Returns:
        tuple: (成功狀態, 結果訊息或圖片URL)
    """
    logging.info(f"Starting generate_image_with_gemini with prompt: {prompt}")
    
    # 檢查圖片生成 API 設定
    if not gemini_image_key:
        logging.error("Gemini Image API key not configured")
        return False, "圖片生成功能未設定 API Key"
    
    for attempt in range(max_retries + 1):
        if attempt > 0:
            logging.info(f"Retry attempt {attempt}/{max_retries} after {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
        
        try:
            logging.info(f"Creating Gemini Image client with API key: {gemini_image_key[:10]}...{gemini_image_key[-5:] if gemini_image_key else 'None'}")
            client = genai_v2.Client(api_key=gemini_image_key)
            
            # 使用測試中成功的模型
            model = "gemini-2.5-flash-image-preview"
            logging.info(f"Using image model: {model} (attempt {attempt + 1})")
            
            # 使用簡單直接的提示詞，測試證實有效
            prompts_to_try = [
                f"Create a photorealistic image of a {prompt}. Do not provide text description, only generate the actual image.",
                f"Generate image: {prompt}",
                f"Draw: {prompt}"
            ]
            
            current_prompt = prompts_to_try[min(attempt, len(prompts_to_try) - 1)]
            logging.info(f"Using prompt strategy {attempt + 1}: {current_prompt[:80]}...")
            
            # 使用簡單的內容結構，與測試中成功的相同
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=current_prompt),
                    ],
                ),
            ]
            
            generate_content_config = types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            )
            
            logging.info("Starting content generation stream...")
            
            # 生成內容
            image_url = None
            text_response = ""
            chunk_count = 0
            
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_content_config,
            ):
                chunk_count += 1
                logging.info(f"Processing chunk {chunk_count}")
                
                # 檢查 chunk 是否有有效的 candidates
                if (
                    not hasattr(chunk, 'candidates') or
                    chunk.candidates is None or
                    len(chunk.candidates) == 0 or
                    chunk.candidates[0].content is None or
                    chunk.candidates[0].content.parts is None or
                    len(chunk.candidates[0].content.parts) == 0
                ):
                    logging.warning(f"Chunk {chunk_count} has no valid content")
                    continue
                    
                part = chunk.candidates[0].content.parts[0]
                logging.info(f"Chunk {chunk_count} part type: {type(part)}")
                
                # 檢查是否有 inline_data
                if hasattr(part, 'inline_data') and part.inline_data:
                    logging.info(f"Found inline_data in chunk {chunk_count}: {type(part.inline_data)}")
                    if hasattr(part.inline_data, 'data') and part.inline_data.data:
                        logging.info(f"Found image data in chunk {chunk_count}")
                        inline_data = part.inline_data
                        image_data = inline_data.data
                        logging.info(f"Image data size: {len(image_data)} bytes")
                        logging.info(f"Image MIME type: {inline_data.mime_type}")
                        
                        file_extension = mimetypes.guess_extension(inline_data.mime_type) or '.png'
                        logging.info(f"File extension: {file_extension}")
                        
                        # 建立檔案名稱
                        safe_prompt = "".join(c for c in prompt if c.isalnum() or c in (' ', '-', '_')).rstrip()[:30]
                        filename = f"gemini_image_{safe_prompt}{file_extension}"
                        logging.info(f"Generated filename: {filename}")
                        
                        # 上傳到 Google Cloud Storage
                        logging.info("Starting upload to GCS...")
                        image_url = await upload_image_to_gcs(image_data, filename)
                        logging.info(f"Upload result: {image_url}")
                        
                        # 一旦找到圖片就跳出迴圈
                        if image_url:
                            logging.info("Image found and uploaded successfully, breaking loop")
                            break
                    else:
                        logging.info(f"inline_data exists but no data: {part.inline_data}")
                else:
                    logging.info(f"No inline_data in chunk {chunk_count}")
                
                # 處理文字回應
                if hasattr(part, 'text') and part.text:
                    text_response += part.text
                    logging.info(f"Received text in chunk {chunk_count}: {part.text[:100]}...")
                elif hasattr(chunk, 'text') and chunk.text:
                    text_response += chunk.text
                    logging.info(f"Received text from chunk object in chunk {chunk_count}: {chunk.text[:100]}...")
                else:
                    logging.info(f"Chunk {chunk_count} has no text data")
            
            logging.info(f"Finished processing {chunk_count} chunks")
            logging.info(f"Final image_url: {image_url}")
            logging.info(f"Final text_response: {text_response[:200]}...")
            
            if image_url:
                logging.info("Image generation successful")
                return True, image_url
            else:
                if text_response:
                    logging.warning(f"Model returned text only, no image generated. Text: {text_response[:200]}")
                    return False, f"❌ 模型只返回文字說明而未生成圖片。請嘗試更具體的描述，例如：'一位台灣婦女在傳統市場挑選新鮮蔬菜的真實照片'"
                else:
                    return False, "❌ 圖片生成失敗，請稍後再試。"
                
        except Exception as e:
            logging.error(f"Error generating image with Gemini (attempt {attempt + 1}): {e}")
            
            # 檢查是否為配額錯誤
            error_msg = str(e)
            is_quota_error = "429" in error_msg and "RESOURCE_EXHAUSTED" in error_msg
            is_rate_limit = "429" in error_msg
            
            if attempt < max_retries and is_rate_limit:
                logging.info(f"Rate limit hit, will retry in {retry_delay} seconds...")
                continue
            else:
                # 最後一次嘗試或非重試錯誤
                if is_quota_error:
                    return False, "❌ 圖片生成配額已用盡，請稍後再試或升級至付費方案。"
                elif "quota" in error_msg.lower():
                    return False, "❌ API 配額不足，請檢查您的 Google AI 使用額度。"
                else:
                    return False, f"❌ 生成圖片時發生錯誤，請稍後再試。"
    
    return False, "❌ 經過多次重試仍無法生成圖片，請稍後再試。"


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
            special_commands = ['!清空', '!clean',  '!摘要','!總結','!summary', '！清空', '！摘要', '!help', '!幫助', '！help', '！幫助', '!畫圖', '!生成圖片', '！畫圖', '！生成圖片', '!image', '!draw']
            
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
                                model = genai.GenerativeModel(gemini_llm_model)
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
• !畫圖 [描述] 或 ！畫圖 [描述]：生成圖片
  例：!畫圖 可愛的貓咪在花園裡玩耍
  提示：使用具體、詳細的描述效果更好
• !help 或 !幫助：顯示此說明

**私人功能：**
• 直接傳送訊息即可與 AI 對話
• 支援所有群組指令

**注意事項：**
• 群組中只有 @ 提及或特殊指令才會回應
• AI 問答為一次性回答，不會記錄到對話歷史
• 所有訊息都會被記錄以供摘要功能使用
• 圖片生成需要 Google Cloud Storage 設定"""
                        # 幫助訊息不記錄到對話歷史
                        
                    elif any(cmd in text.lower() for cmd in ['!畫圖', '！畫圖', '!生成圖片', '！生成圖片', '!image', '!draw']):
                        # 圖片生成功能
                        logging.info(f"Image generation command detected: {text}")
                        
                        if not bucket:
                            logging.error("Image generation requested but GCS not configured")
                            reply_msg = "抱歉，圖片生成功能目前無法使用，請聯繫管理員設定 Google Cloud Storage。"
                        else:
                            # 提取圖片描述
                            prompt = text
                            original_prompt = prompt
                            for cmd in ['!畫圖', '！畫圖', '!生成圖片', '！生成圖片', '!image', '!draw']:
                                if cmd in text.lower():
                                    prompt = text.lower().replace(cmd, '').strip()
                                    logging.info(f"Extracted prompt using command '{cmd}': '{prompt}'")
                                    break
                            
                            if not prompt:
                                logging.warning("No prompt provided for image generation")
                                reply_msg = "請提供圖片描述，例如：!畫圖 可愛的貓咪在花園裡玩耍"
                            else:
                                logging.info(f"Starting image generation process with prompt: '{prompt}'")
                                
                                # 先發送"生成中"的訊息
                                await line_bot_api.reply_message(
                                    ReplyMessageRequest(
                                        reply_token=event.reply_token,
                                        messages=[TextMessage(text=f"🎨 正在生成圖片：{prompt}\n請稍候...")]
                                    ))
                                logging.info("Sent 'generating' message to user")
                                
                                # 生成圖片
                                logging.info("Calling generate_image_with_gemini...")
                                success, result = await generate_image_with_gemini(prompt)
                                logging.info(f"Image generation result - success: {success}, result: {result}")
                                
                                if success:
                                    logging.info("Image generation successful, sending image message")
                                    # 發送圖片訊息
                                    image_message = ImageMessage(
                                        original_content_url=result,
                                        preview_image_url=result
                                    )
                                    # 使用 push message 發送圖片（因為已經用了 reply_token）
                                    if event.source.type == 'group':
                                        logging.info(f"Sending image to group: {event.source.group_id}")
                                        await line_bot_api.push_message(
                                            PushMessageRequest(
                                                to=event.source.group_id,
                                                messages=[image_message]
                                            )
                                        )
                                    else:
                                        logging.info(f"Sending image to user: {event.source.user_id}")
                                        await line_bot_api.push_message(
                                            PushMessageRequest(
                                                to=event.source.user_id,
                                                messages=[image_message]
                                            )
                                        )
                                    logging.info("Image message sent successfully")
                                    reply_msg = ""  # 不需要額外的文字回應
                                else:
                                    logging.error(f"Image generation failed: {result}")
                                    # 發送錯誤訊息
                                    error_message = TextMessage(text=f"❌ {result}")
                                    if event.source.type == 'group':
                                        logging.info(f"Sending error message to group: {event.source.group_id}")
                                        await line_bot_api.push_message(
                                            PushMessageRequest(
                                                to=event.source.group_id,
                                                messages=[error_message]
                                            )
                                        )
                                    else:
                                        logging.info(f"Sending error message to user: {event.source.user_id}")
                                        await line_bot_api.push_message(
                                            PushMessageRequest(
                                                to=event.source.user_id,
                                                messages=[error_message]
                                            )
                                        )
                                    reply_msg = ""  # 不需要額外的文字回應
                        
                        # 圖片生成指令不記錄到對話歷史
                        messages.pop()  # 移除剛才加入的用戶訊息
                        logging.info("Removed image generation command from conversation history")
                        
                    elif is_ai_question:
                        # AI 問答模式：一次性回答，不記錄到對話歷史（群組中的 @ 提及）
                        try:
                            model = genai.GenerativeModel(gemini_llm_model)
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
                            model = genai.GenerativeModel(gemini_llm_model)
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
                # AI 問答模式、幫助訊息和圖片生成指令不記錄到對話歷史
                should_save_to_firebase = not is_ai_question and not (
                    text.lower() in ['!help', '!幫助', '！help', '！幫助'] or
                    any(cmd in text.lower() for cmd in ['!畫圖', '！畫圖', '!生成圖片', '！生成圖片', '!image', '!draw'])
                )
                
                if should_save_to_firebase:
                    try:
                        fdb.put(user_chat_path, 'messages', messages)
                        logging.info(f"Saved message to Firebase: {user_chat_path}")
                    except Exception as e:
                        logging.error(f"Failed to save to Firebase: {e}")
                else:
                    logging.info(f"Skipped saving to Firebase (special command): {text[:50]}...")

                # 發送回應（只有在需要回應且有訊息內容時）
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
