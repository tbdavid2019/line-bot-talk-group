# 群組摘要王 v3 

群組摘要王 v3 是一款使用 FastAPI、LINE Messaging API 和 Google Generative AI，來為 LINE 群組的訊息進行摘要的開源專案。

若你不想架設 LineBot , 可以免費使用我的服務 

Line @377mwhqu


## 🆕 版本更新

- ✅ **2MD Fast Reader & SERP Live Web Search 即時連網能力**：
  - **即時網路搜尋 (SERP)**：自動檢測即時問題（股價、最新新聞、財報、走勢、天氣），透過 2MD 搜尋引擎獲取實時事實（`https://2md.aiurl.tw` ➔ `https://2md.glsoft.ai` ➔ `https://create360.ai`）。
  - **網頁自動讀取與重點摘要**：直接傳送網址或使用 `!read <URL>` / `!網頁 <URL>`，自動透過 2MD Fast Reader 萃取乾淨 Markdown 內容並由 AI 生成結構化摘要。
  - **專屬搜尋指令**：支援 `!搜尋 <關鍵字>` / `!search <關鍵字>`。
- ✅ **原生 TextMessage 回應（支援任意選取複製與超連結點擊）**：
  - 全面採用原生 `TextMessage`，不再受限於 Flex Message 無法複製選取與連結不可點擊的問題。
- ✅ **全雙工智慧 LLM 推論升級 (Primary ➔ Fallback ➔ Gemini)**：
  - **主要 LLM**：`https://nen.com.tw/v1` (`gpt-5.6-luna`)
  - **備用 LLM**：`https://api.groq.com/openai/v1` (`openai/gpt-oss-20b`)
  - **第 3 備援**：Google Gemini Flash API (`gemini-flash-latest`)
- ✅ **AI 繪圖引擎全新升級 (Primary ➔ Fallback + 888box CDN)**：
  - **主要繪圖**：`https://nen.com.tw/v1` (`gemini-3.1-flash-image`)
  - **備用繪圖**：`https://generativelanguage.googleapis.com/v1beta` (`gemini-3.1-flash-image` / `gemini-3-pro-image-preview` / `gemini-2.5-flash-image`)
  - **儲存加速**：自動提取圖片並即時推送至 888box 多節點 CDN 儲存庫，生成專屬預覽連結
- ✅ **David888 Wiki 知識庫發布整合 (AI-First Canvas)**：
  - **LLM 自主長篇發布**：人類交代長篇分析、專題研究、系統架構或教學手冊時，LLM 自主編寫完整 Markdown（含 `[TOC]` 目錄、章節、表格與 Mermaid 圖表）並發布至 `wiki.david888.com`，在 LINE 中回傳精華摘要與線上閱讀連結 (`shareUrl`)。
  - **群組指令**：支援 `!wiki summary`（一鍵將對話轉存為 Wiki 專頁）與 `!wiki <標題> <內容>`。
- ✅ **888box Asset Storage 多節點整合**：
  - 支援將 AI 生成圖片、音訊、影片及匯出檔案自動存入 888box CDN
  - 自動多層級故障轉移：Primary (`box.david888.com`) ➔ Fallback 1 (`box.glsoft.ai`) ➔ Fallback 2 (`box.aiurl.tw`) ➔ GCS 備援
- ✅ **精確 @ Mention 檢測升級**：
  - 支援 LINE 原生 `is_self` 判定，徹底解決群組中提及 `@其他成員` 或 `@All` 時 Bot 誤插話的嚴重問題
  - 手打提及支援正則前後邊界匹配，安全過濾 `@..` 及一般內文符號
  - 新增 `extract_clean_question` 完整保留問題內部的 `@` 符號（如 `@decorator`）
- ✅ **GitHub Actions 自動化雙架構映像檔建置 (ARM64 + x86_64 ➔ Docker Hub)**：
  - **雙架構原生支援**：使用 QEMU + Docker Buildx 同時建置 `linux/amd64` (x64) 與 `linux/arm64` (Apple Silicon / ARM 伺服器) Multi-Arch 映像檔。
  - **自動化推送**：程式碼 Push 至 `master`/`main` 或發布 Tag 時，自動推播至 Docker Hub (`tbdavid2019/linebot-gemini-summarize`、`tbdavid2019/line-bot-talk-group`) 與 GHCR。
  - **Watchtower 無縫聯動**：伺服器端容器 `LINE-377mwhqu` 與 `LINE-113huwec` 自動偵測 Docker Hub 最新版並無感重啟升級。
- ✅ **Docker Compose & Watchtower 自動更新架構**：
  - 提供完整 `docker-compose.yml` 支援 `LINE-377mwhqu` 與 `LINE-113huwec`
  - 配置專屬 Scope 隔離的 `watchtower-linebot`，實現零停機安全自動化更新

### v3.3 (2026-01-05)
- ✅ **Flex Message 視覺升級**：所有 Bot 回應現在使用美觀的卡片樣式
- ✅ **語音轉文字 (ASR) 支援**：支援接收語音訊息並自動轉錄
  - 支援 Groq Whisper、OpenAI Whisper、Gemini 三種 ASR 服務
  - 具備智慧 Fallback 機制，確保服務可用性
  - 語音轉錄後可正常觸發所有功能（AI 對話、畫圖等）
- ⚠️ **重要**：需要更新 requirements.txt 並重新建置 Docker 容器

### v3.2 (2025-11-23)
- ✅ 修正圖片生成模型參數化問題
  - 移除硬編碼的模型名稱
  - 現在正確使用環境變數 `GEMINI_IMAGE_MODEL` 設定
  - 支援使用 `gemini-3-pro-image-preview` 等新模型
- ⚠️ **重要**：更新程式碼後需要重新建置並部署 Docker 容器才能生效

### v3.1 (2025-08-15)
- ✅ 新增 AI 問答模式（@ 機器人功能）
- ✅ 新增幫助系統 (!help)
- ✅ 改進多群組支援機制
- ✅ 模型參數化 (GEMINI_MODEL)
- ✅ 大小寫不敏感指令檢測
- ✅ 支援中英文指令符號



## 📚 目錄

- [功能](#功能)
- [🆕 最新功能](#-最新功能)
- [指令列表](#指令列表)
- [流程圖](#流程圖)
- [開始使用](#開始使用)
- [Docker 部署](#docker-部署)
- [多群組支援說明](./MULTI_GROUP_SUPPORT.md)

> 點子來自：「[如何開發一個「LINE Bot 群組聊天摘要生成器](https://engineering.linecorp.com/zh-hant/blog/linebot-chatgpt)」

> 最原始代碼 來自 https://github.com/louis70109/linebot-gemini-summarize.git  感謝原作者



## 功能

- 接收 LINE 群組中的訊息
- 透過命令清空對話歷史紀錄
- 透過命令產生訊息的摘要
- **AI 問答模式**：@ 機器人進行一次性問答
- **群組智慧回應**：在群組中只有被 @ 提及或使用特殊指令時才會回應
- **Flex Message 回應**：所有回應使用美觀的卡片樣式呈現
- **語音轉文字 (ASR)**：支援接收語音訊息並自動轉錄為文字

### 群組回應規則

- **私人訊息**：Bot 會回應所有訊息
- **群組訊息**：
  - **精確 @ 提及**：進入 AI 問答模式（一次性回答，不記錄到對話歷史）
    - `@377mwhqu 你好` - 使用官方 ID
    - `@Bot 什麼是 AI？` - 使用關鍵詞（需要真正的 mention）
    - `@機器人 幫我解釋` - 使用中文關鍵詞（需要真正的 mention）
  - **特殊指令**：
    - `!清空` 或 `！清空` `！clean` - 清空對話歷史紀錄
    - `!摘要` 或 `！摘要` `！總結` `！summary` - 產生訊息摘要
    - `!help` 或 `!幫助` - 顯示使用說明
  - 其他情況下不會回應，但會記錄訊息供摘要功能使用

### 功能特色

- **智慧記錄**：所有群組訊息都會被記錄，但不會產生回應打擾群組對話
- **AI 問答**：透過 @ 提及可以快速獲得 AI 回答，不會影響對話歷史
- **摘要功能**：基於記錄的訊息產生對話摘要
- **彈性配置**：支援中英文指令符號（`!` 和 `！`）

## 🆕 最新功能

### 1. 精確 AI 問答模式
在群組中精確 @ 機器人即可進行一次性問答：
```
@377mwhqu 什麼是梯度下降？     # 使用官方 ID（推薦）
@Bot Python 怎麼學？          # 使用關鍵詞 + mention
@機器人 請幫我解釋 AI          # 使用中文關鍵詞 + mention
```
- ✅ 精確檢測：避免誤觸發（如 `@john` 不會觸發 Bot）
- ✅ 一次性回答，問完就結束
- ✅ 不記錄到對話歷史（避免影響摘要）
- ✅ 自動使用繁體中文回答
- ✅ 支援官方 ID 和關鍵詞檢測

### 2. 幫助系統
使用以下指令獲得完整操作說明：
```
!help
!幫助
！help
！幫助
```

### 3. 多群組支援
- ✅ 支援同時在多個群組運作
- ✅ 每個群組的對話記錄完全分離
- ✅ 摘要和清空指令只影響當前群組
- ✅ 私人對話與群組對話分開儲存

👉 **詳細的多群組機制說明**：[MULTI_GROUP_SUPPORT.md](./MULTI_GROUP_SUPPORT.md)

### 4. 改進的指令系統
- ✅ 大小寫不敏感的指令檢測
- ✅ 支援中英文指令符號（`!` 和 `！`）
- ✅ 更清晰的使用說明

### 5. Flex Message 視覺升級
Bot 的所有文字回應現在都會自動包裝在美觀的 Flex Message 卡片中：
- ✅ 標題與作者資訊清楚呈現
- ✅ 裝飾性的頁首與頁尾
- ✅ 更好的可讀性與視覺效果

### 6. 語音轉文字 (ASR) 支援
Bot 現在支援接收語音訊息，並自動轉換為文字進行處理：
- ✅ 支援 **Groq Whisper**、**OpenAI Whisper**、**Gemini** 三種 ASR 服務
- ✅ 智慧 Fallback 機制：優先使用預設服務，失敗後自動切換
- ✅ 語音轉錄後可觸發所有功能（AI 對話、畫圖指令等）
- ✅ 在群組與私人對話中都可使用

## 指令列表

| 指令 | 功能 | 適用範圍 |
|------|------|---------|
| `@Bot [問題]` | AI 問答模式 | 群組 |
| `!摘要` / `！摘要` | 產生對話摘要 | 群組、私人 |
| `!清空` / `！清空` | 清空對話記錄 | 群組、私人 |
| `!help` / `!幫助` | 顯示使用說明 | 群組、私人 |
| `!畫圖 [描述]` | 生成圖片 | 群組、私人 |
| 語音訊息 | 語音轉文字處理 | 群組、私人 |
| 直接訊息 | 一般 AI 對話 | 私人 |

## 流程圖

```
   ┌─┐
   ║"│
   └┬┘
   ┌┼┐
    │            ┌─────┐          ┌──────────────┐               ┌────────┐          ┌──────┐
   ┌┴┐           │Group│          │Webhook_Server│               │Firebase│          │Gemini│
  User           └─────┘          └──────┬───────┘               └────────┘          └──────┘
   │    傳送文章訊息  │                    │                           │                  │
   │ ──────────────>│                    │                           │                  │
   │                │     傳送用戶指令     │                           │                  │
   │                │───────────────────>│                           │                  │
   │                │                    │   儲存聊天狀態在 Realtime DB│                  │
   │                │                    │ ────────────────────────> |                 │
   │                │                    │           儲存完畢         │                  │
   │                │                    │ <──────────────────────── |                  │
   │                │    回傳已完成文字    │                           │                  │
   │                │<───────────────────│                           │                  │
   │   輸入 "!摘要"  │                    │                           │                  │
   │ ──────────────>│                    │                           │                  │
   │                │     傳送用戶指令     │                           │                  │
   │                │───────────────────>│                           │                  │
   │                │                    │          抓取聊天記錄       │                  │
   │                │                    │ ────────────────────────> |                  │
   │                │                    │           回傳清單         │                  │
   │                │                    │ <─────────────────────────|                  │
   │                │                    │               下prompt 進行摘要運算            │
   │                │                    │ ────────────────────────────────────────────>|
   │                │                    │                   回傳摘要清單                 │
   │                │                    │ <────────────────────────────────────────────|
   │                │   回傳摘要資訊至群組  │                           │                  │
   │                │<───────────────────│                           │                  │
  User           ┌─────┐          ┌──────┴───────┐               ┌────────┐          ┌──────┐
   ┌─┐           │Group│          │Webhook_Server│               │Firebase│          │Gemini│
   ║"│           └─────┘          └──────────────┘               └────────┘          └──────┘
   └┬┘
   ┌┼┐
    │
   ┌┴┐
```

## 使用說明

### 基本指令

#### 私人對話
在與 Bot 的私人對話中，直接發送任何訊息即可獲得 Gemini AI 的回應。

#### 群組對話
在群組中，Bot 只會在以下情況回應：

1. **@ 提及 Bot**
   ```
   @BotName 請問今天天氣如何？
   ```

2. **使用特殊指令**
   - `!清空` 或 `！清空` - 清空當前對話的歷史紀錄
   - `!摘要` 或 `！摘要` - 對目前的對話內容生成摘要

### 使用範例

#### 群組對話範例：
```
用戶A: 今天要討論專案進度
用戶B: 我這邊已經完成了前端設計
用戶C: @BotName 請總結一下我們的討論
Bot: 根據您的討論，主要進度如下：...

用戶A: !摘要
Bot: 以下是對話摘要：
• 討論專案進度
• 前端設計已完成
• ...
```

#### 清空歷史紀錄：
```
任何用戶: !清空
Bot: ------對話歷史紀錄已經清空------
```

## 開始使用

### 環境變數

在開始之前，您需要設定以下環境變數：

- `LINE_CHANNEL_SECRET`: 您的 LINE Bot Channel 密鑰
- `LINE_CHANNEL_ACCESS_TOKEN`: 您的 LINE Bot Channel 令牌
- `LINE_BOT_ID`: 您的 LINE Bot 官方 ID（可選）
  - 預設值: `377mwhqu`
  - 用於精確檢測 @ 提及，避免誤觸發
- `FIREBASE_URL`: 您的 Firebase 資料庫 URL
  - Example: https://OOOXXX.firebaseio.com/
- `GEMINI_API_KEY`: 您的 Gemini API 金鑰
- `GEMINI_MODEL`: 使用的 Gemini 模型（可選）
  - 預設值: `gemini-2.5-flash`
  - 其他選項: `gemini-1.5-flash`, `gemini-1.5-pro` 等

#### 888box Asset Storage 相關環境變數（v3.4+）

- `BOX_STORAGE_ENDPOINTS`: 自訂 Box Storage API 端點列表（逗號分隔，可選）
  - 預設包含主要與備援節點：`https://box.david888.com,https://box.glsoft.ai,https://box.aiurl.tw`
  - 具備自動 Failover 機制，提供極速 CDN 圖片/檔案回傳網址
- `BOX_STORAGE_TOKEN`: 888box API 存取 Token（可選，如啟用登入權限控管時使用）

#### 圖片生成相關環境變數（v3.2+）

- `GEMINI_IMAGE_API_KEY`: 圖片生成專用的 Gemini API 金鑰（可選）
  - 如未設定，將使用 `GEMINI_API_KEY`
- `GEMINI_IMAGE_MODEL`: 圖片生成使用的模型（可選）
  - 預設值: `gemini-3-pro-image-preview`
  - 其他選項: `gemini-2.5-flash-image-preview`
  - **注意**：此環境變數會影響圖片生成的模型選擇
- `GCS_BUCKET_NAME`: Google Cloud Storage bucket 名稱（選填備援）
- `GOOGLE_APPLICATION_CREDENTIALS`: GCS 認證檔案路徑（選填備援）

#### Google Drive 轉存相關環境變數（群組檔案轉存）

- `GOOGLE_OAUTH_CLIENT_ID`: Google OAuth Client ID（Web）
- `GOOGLE_OAUTH_CLIENT_SECRET`: Google OAuth Client Secret（Web）
- `OAUTH_REDIRECT_BASE`: 服務對外 base URL，例如 `https://你的網域名稱`
  - callback endpoint 會使用：`{OAUTH_REDIRECT_BASE}/auth/google/callback`
- `TOKEN_ENCRYPTION_KEY`: 用於加密儲存 Google refresh token（Fernet key）
- `OAUTH_STATE_SIGNING_KEY`: 用於簽署 OAuth state（防止竄改/重放）

#### ASR (語音轉文字) 相關環境變數（v3.3+）

- `ASR_DEFAULT_PROVIDER`: 預設使用的 ASR 提供商（可選）
  - 預設值: `groq`
  - 其他選項: `openai`, `gemini`
- `ASR_GROQ_API_KEY`: Groq API 金鑰（可選）
- `ASR_OPENAI_API_KEY`: OpenAI API 金鑰（可選）
- `ASR_GEMINI_API_KEY`: Gemini ASR 專用金鑰（可選）
  - 如未設定，將使用 `GEMINI_API_KEY`

**注意**：ASR 功能至少需要設定一個 API Key。系統會優先使用 `ASR_DEFAULT_PROVIDER` 指定的服務，若失敗則自動切換至其他已設定的服務。

#### 其他環境變數

- `GEMINI_LLM_API_KEY`: 文字對話專用的 Gemini API 金鑰（可選）
  - 如未設定，將使用 `GEMINI_API_KEY`
- `GEMINI_LLM_MODEL`: 文字對話使用的模型（可選）
  - 預設值: `gemini-flash-latest`
  - 其他選項: `gemini-1.5-flash`, `gemini-1.5-pro` 等
  - 其他選項: `gemini-1.5-flash`, `gemini-1.5-pro` 等

如果您不在生產環境，請使用 `.env` 檔案來設定這些變數。

### LINE Webhook URL 設定

本專案的 LINE Bot callback URL 端點為：

**路由端點：** `/webhooks/line`  
**HTTP 方法：** POST

完整的 callback URL 格式：
```
https://你的域名/webhooks/line
```

#### 設定方法：

1. **本地開發環境：**
   ```
   http://localhost:8080/webhooks/line
   ```
   （需要使用 ngrok 等工具讓 LINE 能存取）

2. **部署環境：**
   ```
   https://你的網域名稱/webhooks/line
   ```

#### 如何設定：

**方法一：使用提供的腳本**
```bash
./change_bot_url.sh YOUR_CHANNEL_ACCESS_TOKEN https://你的域名/webhooks/line
```

**方法二：手動在 LINE Developers Console 設定**
1. 登入 [LINE Developers Console](https://developers.line.biz/)
2. 選擇你的 Bot
3. 進入 Messaging API 設定
4. 在 "Webhook URL" 欄位填入：`https://你的域名/webhooks/line`
5. 啟用 "Use webhook"

### Docker 部署

#### 🚀 GitHub Actions 自動建置與推播 (雙架構 arm64 / x86_64)

專案已內建完整的 GitHub Actions 工作流程（`.github/workflows/docker-build-push.yml`），只需設定一次 GitHub Secrets 即可全自動運作：

##### 1. 設定 GitHub Secrets
請至 GitHub 倉庫頁面：`Settings` ➔ `Secrets and variables` ➔ `Actions` ➔ `New repository secret` 加入以下兩組：

| Secret 名稱 | 說明 | 範例 |
|---|---|---|
| `DOCKERHUB_USERNAME` | 你的 Docker Hub 帳號 | `tbdavid2019` |
| `DOCKERHUB_TOKEN` | 你的 Docker Hub Access Token（或密碼） | `dckr_pat_xxx...` |

##### 2. 自動化觸發與多架構支援
- **雙架構原生映像**：每次 push 到 `master`/`main` 或發布 Tag 時，自動由 QEMU + Buildx 編譯 **`linux/amd64` (x64)** 與 **`linux/arm64` (ARM64)** 雙架構映像檔。
- **推播端點**：
  - `docker.io/<username>/linebot-gemini-summarize:latest`
  - `docker.io/<username>/line-bot-talk-group:latest`
  - `ghcr.io/<owner>/line-bot-talk-group:latest`
- **手動執行**：亦可在 GitHub 介面的 `Actions` 標籤頁點擊 `Run workflow` 手動觸發建置。

#### 本地建立 Docker Image


```bash
# 建立 Docker image
docker build -t linebot-gemini-summarize .
```

#### 執行 Docker Container

**方法一：直接設定環境變數**
```bash
# 執行容器（需要設定環境變數）
docker run -p 8080:8080 \
  -e LINE_CHANNEL_SECRET=你的_LINE_CHANNEL_SECRET \
  -e LINE_CHANNEL_ACCESS_TOKEN=你的_LINE_CHANNEL_ACCESS_TOKEN \
  -e FIREBASE_URL=你的_FIREBASE_URL \
  -e GEMINI_API_KEY=你的_GEMINI_API_KEY \
  -e PORT=8080 \
  linebot-gemini-summarize
```

**方法二：使用 .env 檔案（推薦）**
```bash
# 創建 .env 檔案
cat > .env << EOF
LINE_CHANNEL_SECRET=你的_LINE_CHANNEL_SECRET
LINE_CHANNEL_ACCESS_TOKEN=你的_LINE_CHANNEL_ACCESS_TOKEN
FIREBASE_URL=你的_FIREBASE_URL
GEMINI_API_KEY=你的_GEMINI_API_KEY
GEMINI_IMAGE_MODEL=gemini-3-pro-image-preview
GCS_BUCKET_NAME=你的_GCS_BUCKET_NAME
GOOGLE_APPLICATION_CREDENTIALS=/app/你的認證檔案.json
# ASR (語音轉文字) 設定
ASR_DEFAULT_PROVIDER=groq
ASR_GROQ_API_KEY=你的_GROQ_API_KEY
ASR_OPENAI_API_KEY=你的_OPENAI_API_KEY
PORT=8080
API_ENV=production
EOF
```
# 使用 .env 檔案執行容器
docker run -d -p 8080:8080 --env-file .env --restart unless-stopped linebot-gemini-summarize 

# 1. 停止並刪除舊容器
docker stop <container_name>
docker rm <container_name>

# 2. 重新建置映像檔
docker build -t linebot-gemini .



docker run -d \
  --env-file .env \
  -p 8080:8080 \
  --name LINE-377mwhqu \
  linebot-gemini


  docker run -d \
  --env-file .env2 \
  -p 8081:8080 \
  --name LINE-113huwec \
  linebot-gemini

```

**⚠️ 重要提醒：更新程式碼後的部署步驟**

如果您修改了程式碼（如更新模型設定），需要重新建置並部署：

```bash
# 1. 停止並移除舊容器
docker stop <container_name>
docker rm <container_name>

# 2. 重新建置 image
docker build -t linebot-gemini-summarize .

# 3. 使用新的 image 啟動容器
docker run -d -p 8080:8080 --env-file .env --restart unless-stopped linebot-gemini-summarize
```

#### 使用 Docker Compose（推薦）

建立 `docker-compose.yml` 檔案：
```yaml
version: '3.8'
services:
  linebot:
    build: .
    ports:
      - "8080:8080"
    environment:
      - LINE_CHANNEL_SECRET=你的_LINE_CHANNEL_SECRET
      - LINE_CHANNEL_ACCESS_TOKEN=你的_LINE_CHANNEL_ACCESS_TOKEN
      - FIREBASE_URL=你的_FIREBASE_URL
      - GEMINI_API_KEY=你的_GEMINI_API_KEY
      - GEMINI_MODEL=gemini-2.5-flash
      - GEMINI_IMAGE_MODEL=gemini-3-pro-image-preview
      - GCS_BUCKET_NAME=你的_GCS_BUCKET_NAME
      - GOOGLE_APPLICATION_CREDENTIALS=/app/你的認證檔案.json
      - ASR_DEFAULT_PROVIDER=groq
      - ASR_GROQ_API_KEY=你的_GROQ_API_KEY
      - ASR_OPENAI_API_KEY=你的_OPENAI_API_KEY
      - PORT=8080
      - API_ENV=production
```

然後執行：
```bash
# 首次部署或更新程式碼後
docker-compose up -d --build

# 僅重啟服務（未更改程式碼時）
docker-compose restart
```

## 📖 進階文件

### 多群組支援機制
詳細了解 Bot 如何在多個群組中運作，以及資料分離機制：

👉 **[多群組支援說明文件](./MULTI_GROUP_SUPPORT.md)**


## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

