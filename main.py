import logging
import os
import sys
import mimetypes
import uuid
import tempfile
import asyncio
import time
from datetime import datetime
if os.getenv('API_ENV') != 'production':
    from dotenv import load_dotenv

    load_dotenv()


from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from linebot.v3.webhook import WebhookParser
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    AsyncMessagingApiBlob,
    Configuration,
    ReplyMessageRequest,
    PushMessageRequest,
    ImageMessage)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    AudioMessageContent,
    FileMessageContent
)
import google.generativeai as genai
from google import genai as genai_v2
from google.genai import types
from google.cloud import storage
import uvicorn
from firebase import firebase
from flex_msg import create_flex_message
from asr import ASRHandler
import drive_export
from services.firebase import FirebaseService
from services.gemini import GeminiService
from services.llm import LLMService
from services.image_generator import ImageGeneratorService
from services.box_storage import BoxStorageService
from services.wiki_publisher import WikiPublisherService

logging.basicConfig(
    level=os.getenv('LOG', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__file__)

app = FastAPI()

# Initialize ASR Handler
asr_handler = ASRHandler()

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

class FirebaseServiceAccountAuth:
    """Authentication handler for python-firebase using Google Cloud Service Account JSON."""
    def __init__(self, key_path):
        self.key_path = key_path
        self._credentials = None
        self._init_credentials()

    def _init_credentials(self):
        from google.oauth2 import service_account
        self._credentials = service_account.Credentials.from_service_account_file(
            self.key_path,
            scopes=[
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/firebase.database'
            ]
        )

    def get_access_token(self):
        import google.auth.transport.requests
        if not self._credentials.valid:
            request = google.auth.transport.requests.Request()
            self._credentials.refresh(request)
        return self._credentials.token

_firebase_auth_obj = None

def get_firebase_db():
    global _firebase_auth_obj
    if not firebase_url:
        logging.error("FIREBASE_URL is not set")
        return firebase.FirebaseApplication(None, None)

    if _firebase_auth_obj is None:
        # 1. 優先檢查 FIREBASE_CREDENTIALS / FIREBASE_KEY_PATH
        cred_path = os.getenv('FIREBASE_CREDENTIALS') or os.getenv('FIREBASE_KEY_PATH')
        
        # 2. 檢查 key/ 資料夾
        if not cred_path or not os.path.exists(cred_path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            key_dir = os.path.join(base_dir, 'key')
            if os.path.exists(key_dir):
                json_files = [
                    os.path.join(key_dir, f) for f in os.listdir(key_dir)
                    if f.endswith('.json')
                ]
                if json_files:
                    cred_path = json_files[0]

        # 3. 檢查 FIREBASE_SECRET (舊版 Realtime Database 密鑰)
        firebase_secret = os.getenv('FIREBASE_SECRET')

        if cred_path and os.path.exists(cred_path):
            try:
                _firebase_auth_obj = FirebaseServiceAccountAuth(cred_path)
                logging.info(f"Firebase auth initialized with service account key: {cred_path}")
            except Exception as e:
                logging.error(f"Failed to initialize Firebase service account auth from {cred_path}: {e}")
        elif firebase_secret:
            _firebase_auth_obj = firebase_secret
            logging.info("Firebase auth initialized with FIREBASE_SECRET")
        else:
            _firebase_auth_obj = None
            logging.info("Firebase initialized with direct database access")

    return firebase.FirebaseApplication(firebase_url, _firebase_auth_obj)


# Gemini LLM 設定（文字對話、摘要等）
gemini_llm_key = os.getenv('GEMINI_LLM_API_KEY')
gemini_llm_model = os.getenv('GEMINI_LLM_MODEL', 'gemini-flash-latest')

# Gemini Image 設定（圖片生成）
gemini_image_key = os.getenv('GEMINI_IMAGE_API_KEY')
gemini_image_model = os.getenv('GEMINI_IMAGE_MODEL', 'gemini-3-pro-image-preview')

# 為了向後相容，如果沒有設定分離的 key，就使用舊的設定或 ASR 金鑰
if not gemini_llm_key:
    gemini_llm_key = os.getenv('GEMINI_API_KEY') or os.getenv('ASR_GEMINI_API_KEY')
if not gemini_image_key:
    gemini_image_key = os.getenv('GEMINI_API_KEY') or os.getenv('ASR_GEMINI_API_KEY')
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
        logging.info("Initializing Google Cloud Storage...")
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

# Initialize LLM Service (Primary: nen.com.tw / gpt-5.6-luna, Fallback: Groq / openai/gpt-oss-20b, Gemini)
llm_service = LLMService()

# Initialize Image Generator Service (Primary: nen.com.tw / gemini-3.1-flash-image, Fallback: Google GenAI)
image_generator_service = ImageGeneratorService()

# Initialize Box Storage Service (Primary: box.david888.com, Fallback: box.glsoft.ai, box.aiurl.tw)
box_storage_service = BoxStorageService()

# Initialize David888 Wiki Publisher Service (Base URL: https://wiki.david888.com/api)
wiki_publisher_service = WikiPublisherService()


async def upload_asset_to_storage(image_data, filename, mime_type="image/png", title=None, description=None):
    """
    上傳圖片、影片、音訊或各類檔案至儲存空間並返回公開 CDN URL。
    優先使用 888box (box.david888.com / box.glsoft.ai / box.aiurl.tw)，
    若未設定或上傳失敗則自動容錯使用 Google Cloud Storage。
    """
    logging.info(f"Uploading asset '{filename}' (MIME: {mime_type}) to storage...")
    
    # 1. 優先嘗試 888box Asset Management
    try:
        box_res = await asyncio.to_thread(
            box_storage_service.upload_file,
            image_data,
            filename,
            title=title or filename,
            description=description,
            mime_type=mime_type
        )
        if box_res and box_res.get("url"):
            cdn_url = box_res["url"]
            logging.info(f"Asset uploaded successfully to Box Storage CDN: {cdn_url}")
            return cdn_url
    except Exception as e:
        logging.warning(f"Failed to upload to Box Storage, trying GCS fallback: {e}")

    # 2. 備用：Google Cloud Storage
    if bucket:
        logging.info("Falling back to Google Cloud Storage upload...")
        return await upload_image_to_gcs(image_data, filename, mime_type)

    logging.error("All storage options failed (Box Storage and GCS)")
    return None


async def upload_image_to_gcs(image_data, filename, mime_type="image/png"):
    """
    上傳圖片到 Google Cloud Storage 並返回公開 URL
    
    Args:
        image_data: 圖片的二進位資料
        filename: 檔案名稱
        mime_type: 圖片的 MIME 類型，預設為 image/png
    
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
        # 建立唯一的檔案名稱 (確保沒有空格和特殊字符)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 進一步清理檔案名稱，確保只包含安全字符
        safe_filename = "".join(c if c.isalnum() or c in ('-', '_', '.') else '_' for c in filename)
        unique_filename = f"linebot_images/{timestamp}_{safe_filename}"
        logging.info(f"Generated unique filename: {unique_filename}")
        
        # 上傳到 GCS
        logging.info(f"Creating blob in bucket: {bucket.name}")
        blob = bucket.blob(unique_filename)
        
        logging.info("Starting upload to GCS...")
        # 設定正確的 content_type 以確保圖片能正確顯示
        await asyncio.to_thread(blob.upload_from_string, image_data, content_type=mime_type)
        logging.info(f"Upload completed successfully with content_type: {mime_type}")
        
        # 對於啟用了 uniform bucket-level access 的 bucket，
        # 我們不需要呼叫 make_public()，而是直接使用公開 URL
        logging.info("Generating public URL (uniform bucket-level access enabled)...")
        
        # 直接構建公開 URL，確保正確編碼
        from urllib.parse import quote
        encoded_filename = quote(unique_filename, safe='/')
        public_url = f"https://storage.googleapis.com/{bucket.name}/{encoded_filename}"
        logging.info(f"Image uploaded successfully: {public_url}")
        logging.info(f"Blob exists: {await asyncio.to_thread(blob.exists)}")
        return public_url
        
    except Exception as e:
        logging.error(f"Failed to upload image to GCS: {e}")
        logging.error(f"Exception type: {type(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return None


async def generate_image_with_gemini(prompt, max_retries=1, retry_delay=10):
    """
    使用 AI (Primary: nen.com.tw gemini-3.1-flash-image, Fallback: Google GenAI) 生成圖片並自動存入 888box CDN
    
    Args:
        prompt: 圖片生成的提示詞
        max_retries: 最大重試次數
        retry_delay: 重試延遲（秒）
    
    Returns:
        tuple: (成功狀態, 結果訊息或圖片URL)
    """
    logging.info(f"Starting image generation with prompt: {prompt}")
    
    for attempt in range(max_retries + 1):
        if attempt > 0:
            logging.info(f"Retry attempt {attempt}/{max_retries} after {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
            
        try:
            success, img_bytes, mime_type = await asyncio.to_thread(
                image_generator_service.generate_image_bytes,
                prompt
            )
            if success and img_bytes:
                file_extension = mimetypes.guess_extension(mime_type) or '.png'
                safe_prompt = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in prompt).rstrip()[:30]
                filename = f"ai_image_{safe_prompt}_{int(datetime.now().timestamp())}{file_extension}"
                
                logging.info(f"Uploading generated image ({len(img_bytes)} bytes) to storage...")
                image_url = await upload_asset_to_storage(
                    img_bytes,
                    filename,
                    mime_type=mime_type,
                    title=prompt
                )
                if image_url:
                    logging.info(f"Image generation and storage upload successful: {image_url}")
                    return True, image_url
            else:
                logging.warning(f"Image generation failed on attempt {attempt + 1}")
        except Exception as e:
            logging.error(f"Error during image generation (attempt {attempt + 1}): {e}")

    return False, "❌ 生成圖片失敗，請稍後再試。"


def is_bot_mentioned(event, bot_id=None, text=None):
    """
    檢查是否 Bot 被提及
    
    Args:
        event: LINE webhook event
        bot_id: Bot 的 LINE ID（可選）
        text: 訊息文字（可選，若為 None 則嘗試從 event.message 獲取）
    
    Returns:
        bool: True 如果 Bot 被提及，False 否則
    """
    if text is None:
        if not isinstance(getattr(event, 'message', None), TextMessageContent):
            return False
        text = event.message.text
    
    if not text:
        return False
    
    mention = getattr(getattr(event, 'message', None), 'mention', None)
    
    # 1. 檢查 LINE 官方提供的 Mention 物件
    if mention and hasattr(mention, 'mentionees') and mention.mentionees:
        # 遍歷所有 mentionee
        for mentionee in mention.mentionees:
            # 官方支援 is_self 屬性（當被 @ 的對象是當前 Bot 時為 True）
            if getattr(mentionee, 'is_self', False) is True:
                logging.info("Bot mentioned via native LINE mention (is_self=True)")
                return True
            if isinstance(mentionee, dict) and (mentionee.get('isSelf') is True or mentionee.get('is_self') is True):
                logging.info("Bot mentioned via native LINE mention dict (isSelf=True)")
                return True
        
        # 若有 mention 物件但所有 mentionee 都不是本 Bot (is_self != True)
        # 代表用戶明確是在 @ 其他人 或 @All，不應誤判為呼叫 Bot
        logging.info("Mention event found, but bot was not the target (other users/@all mentioned)")
        return False
    
    # 2. 若無 LINE 原生 mention 物件（用戶純文字手動輸入），檢查是否明確 @ Bot ID
    import re
    if bot_id:
        # 檢查是否包含 @bot_id 或 ＠bot_id（前後非字母數字底線，避免 email 如 test@377mwhqu.com 誤觸發）
        bot_id_pattern = rf'(?<![\w])[@＠]{re.escape(bot_id)}(?![\w])'
        if re.search(bot_id_pattern, text, re.IGNORECASE):
            logging.info(f"Bot mentioned with bot_id pattern: {bot_id}")
            return True
    
    # 3. 純文字手動輸入呼叫通用關鍵詞（例如「@Bot 請問...」、「@機器人 幫我...」）
    # 必須以 @ 或 ＠ 開頭接關鍵詞，避免內文中無意出現的單詞誤觸發
    text_stripped = text.strip()
    generic_patterns = [
        r'^[@＠](bot|機器人|摘要王)\b',
        r'^[@＠](bot|機器人|摘要王)\s+',
        r'^[@＠](bot|機器人|摘要王)[:：,，]'
    ]
    for pattern in generic_patterns:
        if re.search(pattern, text_stripped, re.IGNORECASE):
            logging.info(f"Bot mentioned with generic pattern: {pattern}")
            return True
    
    return False


def extract_clean_question(text: str, event=None, bot_id: str = None) -> str:
    """
    從被 @ 提及的訊息中提取乾淨的問題文字，移除 @Bot 或 @提及 部分
    """
    if not text:
        return ""
    
    clean_text = text
    mention = getattr(getattr(event, 'message', None), 'mention', None) if event else None
    
    # 1. 若有 LINE 原生 mention，利用 index 與 length 移除對應的 mention 字串
    if mention and hasattr(mention, 'mentionees') and mention.mentionees:
        mentionees = sorted(
            [m for m in mention.mentionees if getattr(m, 'index', None) is not None and getattr(m, 'length', None) is not None],
            key=lambda x: getattr(x, 'index'),
            reverse=True
        )
        for m in mentionees:
            idx = getattr(m, 'index')
            length = getattr(m, 'length')
            if getattr(m, 'is_self', False) is True or (isinstance(m, dict) and m.get('isSelf') is True):
                clean_text = clean_text[:idx] + clean_text[idx+length:]
    
    # 2. 若還有殘留的 @bot_id 或 @Bot / @機器人 / @摘要王 前綴，進行正則移除
    import re
    if bot_id:
        clean_text = re.sub(rf'(?<![\w])[@＠]{re.escape(bot_id)}(?![\w])', '', clean_text, flags=re.IGNORECASE)
        
    clean_text = re.sub(r'^[@＠](bot|機器人|摘要王)\s*[:：,，]?\s*', '', clean_text.strip(), flags=re.IGNORECASE)
    
    return clean_text.strip()


@app.get("/health")
async def health():
    return 'ok'

@app.get("/")
async def root():
    return {"message": "LINE Bot is running", "status": "ok"}


@app.get("/auth/google/callback")
async def google_oauth_callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        return PlainTextResponse(f"OAuth failed: {error}", status_code=400)
    if not code or not state:
        return PlainTextResponse("Missing code/state", status_code=400)

    try:
        payload = drive_export.verify_state(state)
    except Exception as e:
        logging.error(f"OAuth state verification failed: {e}")
        return PlainTextResponse("Invalid state", status_code=400)

    group_id = payload.get("group_id")
    line_user_id = payload.get("line_user_id")
    bind_code = payload.get("bind_code")
    nonce = payload.get("nonce")

    if not group_id or not line_user_id or not bind_code or not nonce:
        return PlainTextResponse("Invalid state payload", status_code=400)

    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    redirect_base = os.getenv("OAUTH_REDIRECT_BASE")
    if not client_id or not client_secret or not redirect_base:
        logging.error("Google OAuth env vars missing")
        return PlainTextResponse("Server not configured for Google OAuth", status_code=500)

    redirect_uri = redirect_base.rstrip("/") + "/auth/google/callback"

    fdb = get_firebase_db()
    firebase_service = FirebaseService(fdb, firebase_url, _firebase_auth_obj)

    code_record = await asyncio.to_thread(firebase_service.read, 'drive_bind_codes', bind_code)
    if not isinstance(code_record, dict):
        return PlainTextResponse("Bind code not found", status_code=400)

    expires_at = code_record.get("expires_at")
    if not isinstance(expires_at, int) or int(time.time()) > expires_at:
        return PlainTextResponse("Bind code expired", status_code=400)

    if code_record.get("used_at"):
        return PlainTextResponse("Bind code already used", status_code=400)

    if code_record.get("group_id") != group_id:
        return PlainTextResponse("Bind code group mismatch", status_code=400)

    if code_record.get("requested_by_line_user_id") != line_user_id:
        return PlainTextResponse("Bind code user mismatch", status_code=400)

    if code_record.get("oauth_nonce") != nonce:
        return PlainTextResponse("Bind code nonce mismatch", status_code=400)

    try:
        tokens = drive_export.exchange_code_for_tokens(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            code=code,
        )
    except Exception as e:
        logging.error(f"OAuth token exchange failed: {e}")
        return PlainTextResponse("Token exchange failed", status_code=500)

    if not tokens.refresh_token:
        # Do not mark used. User needs to re-consent to obtain refresh token.
        logging.error("No refresh_token returned by Google")
        return PlainTextResponse(
            "No refresh token returned. Please revoke app access in your Google account and relink.",
            status_code=400,
        )

    try:
        refresh_token_enc = drive_export.encrypt_refresh_token(tokens.refresh_token)
    except Exception as e:
        logging.error(f"Failed to encrypt refresh token: {e}")
        return PlainTextResponse("Server encryption error", status_code=500)

    try:
        folder_name = f"LINE Bot Export - {group_id}"
        folder_id, folder_name = drive_export.drive_ensure_folder(
            access_token=tokens.access_token,
            name=folder_name,
            parent_id=None,
        )
    except Exception as e:
        logging.error(f"Drive folder creation failed: {e}")
        return PlainTextResponse("Drive folder creation failed", status_code=500)

    drive_export_cfg = {
        "enabled": True,
        "owner_line_user_id": line_user_id,
        "owner_claimed_at": int(time.time()),
        "google": {
            "refresh_token_enc": refresh_token_enc,
            "token_created_at": int(time.time()),
            "scopes": (tokens.scope or "").split(),
        },
        "drive": {
            "folder_id": folder_id,
            "folder_name": folder_name,
        },
    }

    try:
        await asyncio.to_thread(
            firebase_service.write,
            f'groups/{group_id}/info',
            'drive_export',
            drive_export_cfg,
        )
        code_record["used_at"] = int(time.time())
        await asyncio.to_thread(firebase_service.write, 'drive_bind_codes', bind_code, code_record)
    except Exception as e:
        logging.error(f"Failed to persist drive export config: {e}")
        return PlainTextResponse("Failed to save configuration", status_code=500)

    async_api_client = AsyncApiClient(configuration)
    line_bot_api = AsyncMessagingApi(async_api_client)
    try:
        await line_bot_api.push_message(
            PushMessageRequest(
                to=line_user_id,
                messages=[create_flex_message("✅ 已啟用 Google Drive 轉存（此群組）", title="Drive 轉存")],
            )
        )
    except Exception as e:
        logging.error(f"Failed to push confirmation message: {e}")
    finally:
        await async_api_client.close()

    return PlainTextResponse("Drive export enabled. You can close this page.")


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
    line_bot_api_blob = AsyncMessagingApiBlob(async_api_client)
    
    try:
        for event in events:
            logging.info(event)
            if not isinstance(event, MessageEvent):
                continue

            # Claim before any external side effect. Firebase conditional writes
            # make this safe when LINE retries reach another container.
            fdb = get_firebase_db()
            firebase_service = FirebaseService(fdb, firebase_url, _firebase_auth_obj)
            event_message_id = getattr(event.message, 'id', None)
            if event_message_id:
                try:
                    claimed = await asyncio.to_thread(
                        firebase_service.acquire_message_lock, event_message_id
                    )
                except Exception as e:
                    logging.error(f"Failed to acquire message lock {event_message_id}: {e}")
                    continue
                if not claimed:
                    logging.info(f"Ignoring duplicate LINE event: {event_message_id}")
                    continue
            
            user_id = event.source.user_id
            text = ""
            
            if isinstance(event.message, TextMessageContent):
                text = event.message.text
            elif isinstance(event.message, AudioMessageContent):
                # Handle Audio
                try:
                    message_id = event.message.id
                    # Get message content using AsyncMessagingApiBlob
                    message_content_response = await line_bot_api_blob.get_message_content(message_id)
                    
                    # Save to temp file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.m4a') as tf:
                        # The response is a stream, read the content
                        tf.write(message_content_response)
                        temp_file_path = tf.name
                    
                    logging.info(f"Transcribing audio: {temp_file_path}")
                    text = await asyncio.to_thread(asr_handler.transcribe, temp_file_path)
                    logging.info(f"Transcribed text: {text}")
                    
                    # Clean up
                    os.unlink(temp_file_path)
                    
                    if not text:
                        continue
                        
                except Exception as e:
                    logging.error(f"Error handling audio message: {e}")
                    continue
            else:
                if isinstance(event.message, FileMessageContent):
                    if event.source.type != 'group':
                        continue

                    group_id = event.source.group_id
                    message_id = event.message.id
                    file_name = drive_export.safe_filename(
                        getattr(event.message, 'file_name', '') or getattr(event.message, 'fileName', ''),
                        fallback=f"line_file_{message_id}",
                    )
                    file_size = getattr(event.message, 'file_size', None)

                    # Simple size guard (avoid extremely large uploads).
                    if isinstance(file_size, int) and file_size > 50 * 1024 * 1024:
                        logging.warning(f"File too large for Drive export: {file_size} bytes")
                        continue

                    fdb = get_firebase_db()
                    try:
                        cfg = await asyncio.to_thread(
                            firebase_service.read, f'groups/{group_id}/info', 'drive_export'
                        )
                    except Exception as e:
                        logging.error(f"Failed to read drive_export config: {e}")
                        continue

                    if not isinstance(cfg, dict) or not cfg.get('enabled'):
                        continue

                    uploads_path = f'groups/{group_id}/info/drive_export/uploads'
                    try:
                        existing = await asyncio.to_thread(firebase_service.read, uploads_path, message_id)
                    except Exception:
                        existing = None

                    if isinstance(existing, dict) and existing.get('status') in ('pending', 'success'):
                        continue

                    try:
                        await asyncio.to_thread(firebase_service.write, uploads_path, message_id, {
                            'status': 'pending',
                            'created_at': int(time.time()),
                        })
                    except Exception as e:
                        logging.error(f"Failed to create upload record: {e}")
                        continue

                    try:
                        message_content = await line_bot_api_blob.get_message_content(message_id)
                    except Exception as e:
                        logging.error(f"Failed to download LINE file content: {e}")
                        try:
                            await asyncio.to_thread(firebase_service.write, uploads_path, message_id, {
                                'status': 'failed',
                                'error': 'line_download_failed',
                                'created_at': int(time.time()),
                            })
                        except Exception:
                            pass
                        continue

                    with tempfile.NamedTemporaryFile(delete=False) as tf:
                        tf.write(message_content)
                        temp_file_path = tf.name

                    try:
                        google_cfg = cfg.get('google', {}) if isinstance(cfg.get('google'), dict) else {}
                        drive_cfg = cfg.get('drive', {}) if isinstance(cfg.get('drive'), dict) else {}
                        refresh_token_enc = google_cfg.get('refresh_token_enc')
                        folder_id = drive_cfg.get('folder_id')

                        if not refresh_token_enc or not folder_id:
                            raise RuntimeError('drive_export_not_configured')

                        client_id = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
                        client_secret = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
                        if not client_id or not client_secret:
                            raise RuntimeError('google_oauth_env_missing')

                        def do_upload() -> str:
                            refresh_token = drive_export.decrypt_refresh_token(refresh_token_enc)
                            access_token = drive_export.refresh_access_token(
                                client_id=client_id,
                                client_secret=client_secret,
                                refresh_token=refresh_token,
                            )
                            return drive_export.drive_resumable_upload(
                                access_token=access_token,
                                file_path=temp_file_path,
                                filename=file_name,
                                folder_id=folder_id,
                            )

                        drive_file_id = await asyncio.to_thread(do_upload)

                        await asyncio.to_thread(firebase_service.write, uploads_path, message_id, {
                            'status': 'success',
                            'drive_file_id': drive_file_id,
                            'created_at': int(time.time()),
                        })
                    except Exception as e:
                        logging.error(f"Drive upload failed: {e}")
                        try:
                            await asyncio.to_thread(firebase_service.write, uploads_path, message_id, {
                                'status': 'failed',
                                'error': str(e)[:200],
                                'created_at': int(time.time()),
                            })
                        except Exception:
                            pass
                    finally:
                        try:
                            os.unlink(temp_file_path)
                        except Exception:
                            pass

                    continue

                continue

            # 設定 Firebase 路徑
            if event.source.type == 'group':
                user_chat_path = f'groups/{event.source.group_id}'
            else:
                user_chat_path = f'users/{user_id}'
            
            # 決定是否要回應
            should_reply = False
            is_ai_question = False  # 是否為 AI 問答模式
            is_drive_command = False
            is_wiki_command = False
            special_commands = ['!清空', '!clean',  '!摘要','!總結','!summary', '！清空', '！摘要', '!help', '!幫助', '！help', '！幫助', '!畫圖', '!生成圖片', '！畫圖', '！生成圖片', '!image', '!draw', '!drive', '！drive', '!wiki', '！wiki']
            
            if event.source.type == 'group':
                # 檢查是否真的提及了 Bot
                bot_mentioned = is_bot_mentioned(event, bot_line_id, text=text)
                
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
                messages = await asyncio.to_thread(
                    firebase_service.get_messages, user_chat_path
                )
                existing_message_count = len(messages)
            except Exception as e:
                logging.warning(f"Failed to get messages from Firebase: {e}")
                messages = []
                existing_message_count = 0

            if text:
                # 所有訊息都記錄到 Firebase
                messages.append({'role': 'user', 'parts': [text], 'timestamp': str(event.timestamp)})
                
                reply_msg = ""
                
                # 只有在需要回應時才處理
                if should_reply:
                    normalized = text.strip().replace('！', '!')
                    lowered = normalized.lower()

                    if lowered.startswith('!drive'):
                        is_drive_command = True
                        tokens = normalized.split()

                        # Ensure drive commands do not pollute conversation history
                        messages.pop()

                        if event.source.type == 'group':
                            group_id = event.source.group_id

                            if len(tokens) < 2:
                                reply_msg = "用法：!drive bind | !drive status | !drive off"
                            else:
                                subcmd = tokens[1].lower()
                                if subcmd == 'bind':
                                    try:
                                        existing = await asyncio.to_thread(
                                            firebase_service.read,
                                            f'groups/{group_id}/info',
                                            'drive_export',
                                        )
                                    except Exception:
                                        existing = None

                                    if isinstance(existing, dict) and existing.get('owner_line_user_id'):
                                        reply_msg = "此群組已有人綁定 Drive。請用 !drive status 查看，或請 owner 執行 !drive off 後再重新綁定。"
                                    else:
                                        bind_code = drive_export.generate_bind_code()
                                        expires_at = int(time.time()) + 10 * 60
                                        record = {
                                            'group_id': group_id,
                                            'requested_by_line_user_id': user_id,
                                            'expires_at': expires_at,
                                        }
                                        try:
                                            await asyncio.to_thread(
                                                firebase_service.write, 'drive_bind_codes', bind_code, record
                                            )
                                            await asyncio.to_thread(firebase_service.write, f'groups/{group_id}/info/drive_export', 'bind', {
                                                'active_code': bind_code,
                                                'expires_at': expires_at,
                                                'requested_by_line_user_id': user_id,
                                            })
                                            reply_msg = (
                                                "請私訊我以下指令完成綁定（10 分鐘內有效）：\n"
                                                f"!drive link {bind_code}"
                                            )
                                        except Exception as e:
                                            logging.error(f"Failed to create bind code: {e}")
                                            reply_msg = "建立綁定碼失敗，請稍後再試。"

                                elif subcmd == 'status':
                                    try:
                                        cfg = await asyncio.to_thread(
                                            firebase_service.read,
                                            f'groups/{group_id}/info',
                                            'drive_export',
                                        )
                                    except Exception:
                                        cfg = None

                                    if not isinstance(cfg, dict) or not cfg.get('enabled'):
                                        owner = cfg.get('owner_line_user_id') if isinstance(cfg, dict) else None
                                        bind = cfg.get('bind') if isinstance(cfg, dict) else None
                                        msg = "Drive 轉存：未啟用"
                                        if owner:
                                            msg += f"\nOwner: {owner}"
                                        if isinstance(bind, dict) and bind.get('active_code'):
                                            msg += f"\n綁定碼：{bind.get('active_code')}（到期：{bind.get('expires_at')}）"
                                        reply_msg = msg
                                    else:
                                        drive_cfg = cfg.get('drive', {}) if isinstance(cfg.get('drive'), dict) else {}
                                        reply_msg = (
                                            "Drive 轉存：已啟用\n"
                                            f"Owner: {cfg.get('owner_line_user_id')}\n"
                                            f"Folder ID: {drive_cfg.get('folder_id')}"
                                        )

                                elif subcmd == 'off':
                                    try:
                                        cfg = await asyncio.to_thread(
                                            firebase_service.read,
                                            f'groups/{group_id}/info',
                                            'drive_export',
                                        )
                                    except Exception:
                                        cfg = None

                                    if not isinstance(cfg, dict) or not cfg.get('owner_line_user_id'):
                                        reply_msg = "此群組尚未啟用 Drive 轉存。"
                                    elif cfg.get('owner_line_user_id') != user_id:
                                        reply_msg = "只有 owner 可以關閉 Drive 轉存。"
                                    else:
                                        try:
                                            await asyncio.to_thread(
                                                firebase_service.delete,
                                                f'groups/{group_id}/info',
                                                'drive_export',
                                            )
                                            reply_msg = "已關閉 Drive 轉存，群組已可重新綁定。"
                                        except Exception as e:
                                            logging.error(f"Failed to disable drive export: {e}")
                                            reply_msg = "關閉失敗，請稍後再試。"

                                else:
                                    reply_msg = "用法：!drive bind | !drive status | !drive off"

                        else:
                            # Private chat
                            if len(tokens) < 3:
                                reply_msg = "用法：!drive link <BIND_CODE>"
                            else:
                                subcmd = tokens[1].lower()
                                if subcmd != 'link':
                                    reply_msg = "用法：!drive link <BIND_CODE>"
                                else:
                                    bind_code = tokens[2].strip()
                                    code_record = await asyncio.to_thread(
                                        firebase_service.read, 'drive_bind_codes', bind_code
                                    )
                                    if not isinstance(code_record, dict):
                                        reply_msg = "綁定碼不存在。"
                                    else:
                                        expires_at = code_record.get('expires_at')
                                        if not isinstance(expires_at, int) or int(time.time()) > expires_at:
                                            reply_msg = "綁定碼已過期，請回群組重新執行 !drive bind。"
                                        elif code_record.get('used_at'):
                                            reply_msg = "綁定碼已使用，請回群組重新執行 !drive bind。"
                                        elif code_record.get('requested_by_line_user_id') != user_id:
                                            reply_msg = "此綁定碼不是由你建立。請由建立者完成綁定或重新產生綁定碼。"
                                        else:
                                            client_id = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
                                            redirect_base = os.getenv('OAUTH_REDIRECT_BASE')
                                            if not client_id or not redirect_base or not os.getenv('OAUTH_STATE_SIGNING_KEY'):
                                                reply_msg = "伺服器尚未設定 Google OAuth（缺少環境變數）。"
                                            else:
                                                redirect_uri = redirect_base.rstrip('/') + '/auth/google/callback'
                                                nonce = uuid.uuid4().hex
                                                exp = int(time.time()) + 10 * 60
                                                payload = {
                                                    'group_id': code_record.get('group_id'),
                                                    'line_user_id': user_id,
                                                    'bind_code': bind_code,
                                                    'nonce': nonce,
                                                    'exp': exp,
                                                }
                                                state = drive_export.sign_state(payload)

                                                code_record['oauth_nonce'] = nonce
                                                await asyncio.to_thread(
                                                    firebase_service.write,
                                                    'drive_bind_codes',
                                                    bind_code,
                                                    code_record,
                                                )

                                                oauth_url = drive_export.build_google_oauth_url(
                                                    client_id=client_id,
                                                    redirect_uri=redirect_uri,
                                                    state=state,
                                                )
                                                reply_msg = f"請點選以下連結授權 Google Drive：\n{oauth_url}"

                    elif text.lower() in ['!清空', '！清空', '!clean']:
                        try:
                            await asyncio.to_thread(firebase_service.clear_messages, user_chat_path)
                            reply_msg = '------對話歷史紀錄已經清空------'
                            # 清空後重置 messages
                            messages = []
                        except Exception as e:
                            logging.error(f"Failed to clear Firebase data: {e}")
                            reply_msg = '清空對話記錄時發生錯誤，請稍後再試'

                    elif text.lower() in ['!摘要', '！摘要', '!總結', '！總結', '！summary']:
                        if len(messages) > 1:  # 確保有對話內容可以摘要
                            try:
                                gemini_service = GeminiService(
                                    gemini_llm_model, genai.GenerativeModel
                                )
                                # 準備給 Gemini 的訊息格式（移除 timestamp 欄位）
                                gemini_messages = []
                                for msg in messages:
                                    gemini_msg = {
                                        'role': msg['role'],
                                        'parts': msg['parts']
                                    }
                                    gemini_messages.append(gemini_msg)
                                
                                response = await asyncio.to_thread(
                                    gemini_service.generate_content,
                                    f'Summary the following message in Traditional Chinese by less 5 list points. \n{gemini_messages}',
                                )
                                reply_msg = response.text
                                # 記錄摘要回應
                                messages.append({'role': 'model', 'parts': [reply_msg], 'timestamp': str(event.timestamp)})
                            except Exception as e:
                                logging.error(f"Error generating summary: {e}")
                                reply_msg = "抱歉，產生摘要時發生錯誤，請稍後再試。"
                        else:
                            reply_msg = '目前沒有足夠的對話紀錄可以摘要'
                            messages.append({'role': 'model', 'parts': [reply_msg], 'timestamp': str(event.timestamp)})
                    
                    elif text.lower().startswith('!wiki') or text.lower().startswith('！wiki'):
                        is_wiki_command = True
                        cleaned_cmd = text[5:].strip() if text.lower().startswith('!wiki') else text[5:].strip()
                        tokens = cleaned_cmd.split(maxsplit=1)
                        subcmd = tokens[0].lower() if tokens else ""

                        if not tokens or subcmd in ['help', '幫助', '說明', 'h', '?']:
                            reply_msg = """📖 David888 Wiki 發布指令說明

• `!wiki summary` 或 `!wiki 摘要`：將群組目前對話進行 AI 結構化總結，並直接發布為 David888 Wiki 網頁筆記（附公開閱讀網址與目錄）。
• `!wiki <標題> <Markdown內容>`：直接發布一篇 Markdown 文章到 David888 Wiki。
  例：`!wiki 今日會議記錄 # 會議決策\n1. 啟用新架構\n2. 部署 Watchtower`

🔗 Wiki 官網：https://wiki.david888.com"""

                        elif subcmd in ['summary', '摘要', '總結']:
                            if len(messages) > 1:
                                try:
                                    gemini_service = GeminiService(
                                        gemini_llm_model, genai.GenerativeModel
                                    )
                                    gemini_messages = [{'role': m['role'], 'parts': m['parts']} for m in messages if m.get('role') in ('user', 'model')]
                                    
                                    prompt_summary = f"""請將以下群組對話記錄整理成一份專業、結構清晰的 Markdown 知識庫筆記，請使用繁體中文。
格式要求：
1. 第一行必須是 H1 主標題：# 📑 群組對話精華摘要 ({datetime.now().strftime('%Y-%m-%d %H:%M')})
2. 請加入 [TOC]
3. 包含以下章節：
   - ## 🎯 核心主題與討論重點
   - ## 💡 關鍵決策與重要結論
   - ## 📌 待辦事項與行動清單 (Action Items)
   - ## 💬 重點討論脈絡記錄
對話記錄如下：
{gemini_messages}"""
                                    response = await asyncio.to_thread(
                                        gemini_service.generate_content,
                                        prompt_summary
                                    )
                                    summary_content = response.text
                                    
                                    # 發布到 David888 Wiki
                                    note_title = f"summary-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                                    wiki_res = await asyncio.to_thread(
                                        wiki_publisher_service.publish_note,
                                        text=summary_content,
                                        title=note_title,
                                        theme="claude-canvas",
                                        public=True
                                    )
                                    
                                    if wiki_res and wiki_res.get("shareUrl"):
                                        share_url = wiki_res["shareUrl"]
                                        reply_msg = f"📑 群組對話精華摘要已發布至 David888 Wiki！\n\n🔗 線上公開閱讀：\n{share_url}"
                                    else:
                                        reply_msg = f"📑 對話摘要：\n\n{summary_content}"
                                except Exception as e:
                                    logging.error(f"Error generating wiki summary: {e}")
                                    reply_msg = "抱歉，產生或發布 Wiki 摘要時發生錯誤，請稍後再試。"
                            else:
                                reply_msg = "目前沒有足夠的對話紀錄可以產生 Wiki 摘要"

                        else:
                            # 格式：!wiki <標題> <內容>
                            # tokens: [標題, 內容]
                            if len(tokens) >= 2:
                                note_title = tokens[0]
                                note_content = tokens[1]
                            else:
                                note_title = f"note-{int(time.time())}"
                                note_content = tokens[0]

                            try:
                                wiki_res = await asyncio.to_thread(
                                    wiki_publisher_service.publish_note,
                                    text=note_content,
                                    title=note_title,
                                    theme="claude-canvas",
                                    public=True
                                )
                                if wiki_res and wiki_res.get("shareUrl"):
                                    share_url = wiki_res["shareUrl"]
                                    reply_msg = f"✅ 文章已成功發布至 David888 Wiki！\n\n🔗 公開閱讀連結：\n{share_url}"
                                else:
                                    reply_msg = "❌ 發布至 David888 Wiki 失敗，請稍後再試。"
                            except Exception as e:
                                logging.error(f"Error publishing to wiki: {e}")
                                reply_msg = f"❌ 發布失敗：{e}"

                    elif text.lower() in ['!help', '!幫助', '！help', '！幫助']:
                        reply_msg = """🤖 群組摘要王 使用說明

**群組功能：**
• @ 機器人 + 問題：進入 AI 問答模式
  例：@Bot 什麼是梯度下降？

• !摘要 或 ！摘要：產生對話摘要
• !wiki summary：將對話整理為結構化筆記並發布至 David888 Wiki (含公開分享連結)
• !wiki <標題> <內容>：直接發布 Markdown 筆記至 David888 Wiki
• !清空 或 ！清空：清空對話記錄
• !drive bind：啟用此群組 Google Drive 轉存（owner 制）
  其他：!drive status / !drive off
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
• 圖片與檔案會自動存入 888box CDN 高速儲存"""
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
                                
                                # 不先發送"生成中"訊息，直接生成圖片後一次回覆
                                logging.info("Calling generate_image_with_gemini...")
                                success, result = await generate_image_with_gemini(prompt)
                                logging.info(f"Image generation result - success: {success}, result: {result}")
                                
                                if success:
                                    logging.info("Image generation successful, sending reply with image")
                                    # 使用 reply_message 一次發送文字和圖片（避免 push_message 額度問題）
                                    image_message = ImageMessage(
                                        original_content_url=result,
                                        preview_image_url=result
                                    )
                                    success_text = create_flex_message(f"🎨 圖片生成完成：{prompt}", title="圖片生成", header_text="AI 畫家")
                                    
                                    await line_bot_api.reply_message(
                                        ReplyMessageRequest(
                                            reply_token=event.reply_token,
                                            messages=[success_text, image_message]
                                        )
                                    )
                                    logging.info("Image and text sent successfully via reply_message")
                                    reply_msg = ""  # 已經回覆了
                                else:
                                    logging.error(f"Image generation failed: {result}")
                                    # 使用 reply_message 發送錯誤訊息
                                    reply_msg = f"❌ 圖片生成失敗：{result}"
                        
                        # 圖片生成指令不記錄到對話歷史
                        messages.pop()  # 移除剛才加入的用戶訊息
                        logging.info("Removed image generation command from conversation history")
                        
                    elif is_ai_question:
                        # AI 問答模式：一次性回答，不記錄到對話歷史（群組中的 @ 提及）
                        try:
                            gemini_service = GeminiService(
                                gemini_llm_model, genai.GenerativeModel
                            )
                            # 移除 @ 提及部分，只保留問題
                            clean_question = extract_clean_question(text, event, bot_line_id)
                            logging.info(f"Cleaned AI question: '{clean_question}'")
                            
                            response = await asyncio.to_thread(
                                gemini_service.generate_content,
                                f"請用繁體中文回答以下問題。若為長篇深入分析、架構規劃或教學，請使用具備清晰章節標題、[TOC]、重點清單或表格的完整 Markdown 格式：\n{clean_question}",
                            )
                            raw_reply = response.text
                            # 若產出為長篇分析/報告，LLM 自動發布至 David888 Wiki 並附上 shareUrl
                            reply_msg = await asyncio.to_thread(
                                wiki_publisher_service.format_and_publish_if_long,
                                clean_question,
                                raw_reply
                            )
                            # AI 問答不記錄到對話歷史，所以移除剛加入的訊息
                            messages.pop()  # 移除剛才加入的用戶訊息
                        except Exception as e:
                            logging.error(f"Error in AI question mode: {e}")
                            reply_msg = "抱歉，處理您的問題時發生錯誤，請稍後再試。"
                            messages.pop()  # 移除剛才加入的用戶訊息
                            
                    else:
                        # 一般對話（私人對話或群組中的其他情況）
                        try:
                            gemini_service = GeminiService(
                                gemini_llm_model, genai.GenerativeModel
                            )
                            # 準備給 Gemini 的訊息格式（移除 timestamp 欄位）
                            gemini_messages = []
                            for msg in messages:
                                gemini_msg = {
                                    'role': msg['role'],
                                    'parts': msg['parts']
                                }
                                gemini_messages.append(gemini_msg)
                            
                            response = await asyncio.to_thread(
                                gemini_service.generate_content, gemini_messages
                            )
                            raw_reply = response.text
                            # 若產出為長篇分析/報告，LLM 自動發布至 David888 Wiki 並附上 shareUrl
                            reply_msg = await asyncio.to_thread(
                                wiki_publisher_service.format_and_publish_if_long,
                                text,
                                raw_reply
                            )
                            messages.append({'role': 'model', 'parts': [reply_msg], 'timestamp': str(event.timestamp)})
                            logging.info(f"Generated AI response for general conversation: {reply_msg[:50]}...")
                        except Exception as e:
                            logging.error(f"Error in general conversation: {e}")
                            reply_msg = "抱歉，處理您的訊息時發生錯誤，請稍後再試。"
                
                # 更新 Firebase 中的對話紀錄
                # AI 問答模式、幫助訊息和圖片生成指令不記錄到對話歷史
                should_save_to_firebase = not is_ai_question and not (
                    text.lower() in ['!help', '!幫助', '！help', '！幫助'] or
                    any(cmd in text.lower() for cmd in ['!畫圖', '！畫圖', '!生成圖片', '！生成圖片', '!image', '!draw']) or
                    is_drive_command or
                    is_wiki_command
                )
                
                if should_save_to_firebase:
                    try:
                        for message in messages[existing_message_count:]:
                            await asyncio.to_thread(
                                firebase_service.append_message,
                                user_chat_path,
                                message,
                                event_message_id if message.get('role') == 'user' else None,
                            )
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
                            messages=[create_flex_message(reply_msg)]
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
