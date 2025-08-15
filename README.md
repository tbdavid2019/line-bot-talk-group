# 群組摘要王 v3 

群組摘要王 v3 是一款使用 FastAPI、LINE Messaging API 和 Google Generative AI，來為 LINE 群組的訊息進行摘要的開源專案。

若你不想架設 LineBot , 可以免費使用我的服務 

Line @377mwhqu


## 🆕 版本更新

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

> 原始摘要王v3 來自 https://github.com/louis70109/linebot-gemini-summarize.git  感謝原作者


## 功能

- 接收 LINE 群組中的訊息
- 透過命令清空對話歷史紀錄
- 透過命令產生訊息的摘要
- **AI 問答模式**：@ 機器人進行一次性問答
- **群組智慧回應**：在群組中只有被 @ 提及或使用特殊指令時才會回應

### 群組回應規則

- **私人訊息**：Bot 會回應所有訊息
- **群組訊息**：
  - **@ 提及 + 問題**：進入 AI 問答模式（一次性回答，不記錄到對話歷史）
    - 例如：`@Bot 什麼是梯度下降？`
  - **特殊指令**：
    - `!清空` 或 `！清空` - 清空對話歷史紀錄
    - `!摘要` 或 `！摘要` - 產生訊息摘要
    - `!help` 或 `!幫助` - 顯示使用說明
  - 其他情況下不會回應，但會記錄訊息供摘要功能使用

### 功能特色

- **智慧記錄**：所有群組訊息都會被記錄，但不會產生回應打擾群組對話
- **AI 問答**：透過 @ 提及可以快速獲得 AI 回答，不會影響對話歷史
- **摘要功能**：基於記錄的訊息產生對話摘要
- **彈性配置**：支援中英文指令符號（`!` 和 `！`）

## 🆕 最新功能

### 1. AI 問答模式
在群組中 @ 機器人即可進行一次性問答：
```
@Bot 什麼是梯度下降？
@機器人 Python 怎麼學？
```
- ✅ 一次性回答，問完就結束
- ✅ 不記錄到對話歷史（避免影響摘要）
- ✅ 自動使用繁體中文回答

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

## 指令列表

| 指令 | 功能 | 適用範圍 |
|------|------|---------|
| `@Bot [問題]` | AI 問答模式 | 群組 |
| `!摘要` / `！摘要` | 產生對話摘要 | 群組、私人 |
| `!清空` / `！清空` | 清空對話記錄 | 群組、私人 |
| `!help` / `!幫助` | 顯示使用說明 | 群組、私人 |
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
- `FIREBASE_URL`: 您的 Firebase 資料庫 URL
  - Example: https://OOOXXX.firebaseio.com/
- `GEMINI_API_KEY`: 您的 Gemini API 金鑰
- `GEMINI_MODEL`: 使用的 Gemini 模型（可選）
  - 預設值: `gemini-2.5-flash`
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

#### 建立 Docker Image

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
PORT=8080
API_ENV=production
EOF

# 使用 .env 檔案執行容器
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
      - PORT=8080
      - API_ENV=production
```

然後執行：
```bash
docker-compose up -d
```

## 📖 進階文件

### 多群組支援機制
詳細了解 Bot 如何在多個群組中運作，以及資料分離機制：

👉 **[多群組支援說明文件](./MULTI_GROUP_SUPPORT.md)**


## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！


