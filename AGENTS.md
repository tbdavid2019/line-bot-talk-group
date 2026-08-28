# AGENTS Directives & Engineering Guidelines

This file serves as the mandatory ruleset and operational protocol for all AI agents working in this repository (`line-bot-talk-group`).

---

## 🚨 1. Mandatory Documentation Synchronization (變更即時紀錄鐵律)
**Whenever any feature, bug fix, configuration, or API integration is made, you MUST proactively update documentation without needing user reminders:**

1. **`CHANGELOG.md`**:
   - Record the changes under the current date section (`## YYYY-MM-DD`).
   - Group entries into `Added`, `Changed`, `Fixed`, or `Removed`.
   - Explicitly detail what was resolved or implemented.

2. **`README.md`**:
   - Keep commands, table of environment variables, architecture diagrams, and usage examples 100% up-to-date with reality.

3. **`test/` Suite**:
   - Always add or update offline unit tests to cover new features and prevent regressions.

---

## 📦 2. 888box Asset Storage System Reference
When generating or downloading images, videos, audio, or files, integrate with the multi-tier 888box Storage API:

- **Primary Endpoint**: `https://box.david888.com/api.php`
- **Fallback 1**: `https://box.glsoft.ai/api.php`
- **Fallback 2**: `https://box.aiurl.tw/api.php`
- **API Spec**: `https://box.david888.com/skill.php`
- **Failover Logic**: Handled automatically in `services/box_storage.py` via `BoxStorageService`.

---

## 🚢 3. Deployment & Watchtower Infrastructure
- **Production Server**: `10.9.0.9` (`/home/david/line-bot-talk-group`)
- **Containers**:
  - `LINE-377mwhqu` (Port 8080)
  - `LINE-113huwec` (Port 8081)
- **Watchtower Auto-updater**:
  - Must run with `WATCHTOWER_SCOPE=linebot` and target `LINE-377mwhqu LINE-113huwec`.
  - Target containers must carry label `com.centurylinklabs.watchtower.scope-label=linebot` to prevent scope collision with other services (e.g. `watchtower-url2md`).

---

## 📖 4. David888 Wiki Publishing Integration (AI-First Autonomous Canvas)
**Wiki 的核心定位是 LLM 的長篇知識庫畫布（AI-First Publishing Canvas）**：
- **設計哲學**：主要不是給人類手動輸入繁瑣指令，而是當人類交代 LLM 處理長篇分析、專題研究、系統架構設計或教學指南時，**LLM 自主編寫高結構化 Markdown 並主動發布至 Wiki，回傳 `shareUrl` 給人類在瀏覽器閱讀**。
- **API Base URL**: `https://wiki.david888.com/api`
- **Skill Spec**: `https://wiki.david888.com/.well-known/agent-skills/david888-wiki-publisher/SKILL.md`
- **Publish Endpoint**: `POST https://wiki.david888.com/api/<path>`
- **CRITICAL RULE 1**: Always extract and provide the **`shareUrl`** (e.g. `https://wiki.david888.com/share/<id>`) to the user. Never return the internal edit `url`.
- **CRITICAL RULE 2 (Document Structure)**: 文章第一行**必須強制為 Level-1 `# 文件標題`**（不得有任何對話寒暄開場廢話），緊接著引言摘要 `> ...` 與 `[TOC]` 目錄。
- **Multi-Modal Views**: 支援 2D 簡報模式 (`shareUrl + '/present'`) 與雙欄電子書模式 (`shareUrl + '/book'`)。
- **Markdown Utilities**: 提供無狀態 API：`POST /api/markdown/render`, `POST /api/markdown/parse`, `POST /api/markdown/extract`, `POST /api/markdown/lint`。
- **Service Implementation**: Handled in `services/wiki_publisher.py` via `WikiPublisherService` (內建 `format_and_publish_if_long` 與 Agentic Tool `publish_wiki_note`)。

---

## 🤖 5. LLM & Image Generation Infrastructure
- **LLM Text Generation**:
  - **Primary**: `https://nen.com.tw/v1` (Model: `gpt-5.6-luna`, Env: `LLM_API_KEY`)
  - **Fallback**: `https://api.groq.com/openai/v1` (Model: `openai/gpt-oss-20b`, Env: `LLM_FALLBACK_API_KEY`)
  - **3rd Tier**: Google Gemini Flash API (`gemini-flash-latest`)
  - **Implementation**: Handled in `services/llm.py` via `LLMService`.
- **Image Generation**:
  - **Primary**: `https://nen.com.tw/v1` (Model: `gemini-3.1-flash-image`, Env: `IMAGE_API_KEY` / `LLM_API_KEY`)
  - **Fallback**: `https://generativelanguage.googleapis.com/v1beta` (Model: `gemini-3.1-flash-image`, Env: `IMAGE_FALLBACK_API_KEY`)
  - **Storage**: Automatically uploaded and served via `888box` multi-tier CDN (`services/box_storage.py`).
  - **Implementation**: Handled in `services/image_generator.py` via `ImageGeneratorService`.

---

## 🌐 6. 2MD Fast Reader & SERP Live Web Search Engine
- **Primary Endpoint**: `https://2md.aiurl.tw/`
- **Fallback 1**: `https://2md.glsoft.ai/`
- **Fallback 2**: `https://create360.ai/`
- **Capabilities**:
  - **Live SERP Web Search**: `GET /s/<query>` or `GET /search?q=<query>` (powered by DuckDuckGo + multi-engine failover).
  - **URL to Markdown Web Reader**: `GET /<url>` (high-speed article & document extraction).
- **Implementation**: Handled in `services/web_search.py` via `WebSearchService` and seamlessly integrated into `LLMService` for real-time live retrieval (stock quotes, breaking news, market status, URL parsing).


