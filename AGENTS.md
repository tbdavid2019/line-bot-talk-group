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
- **Production Server**: `10.9.0.9` (`/home/david/linebot-gemini-summarize`)
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
- **CRITICAL RULE**: Always extract and provide the **`shareUrl`** (e.g. `https://wiki.david888.com/share/<id>`) to the user. Never return the internal edit `url`.
- **Formatting Standards**: 確保包含 H1 標題、`[TOC]` 目錄、清晰 H2/H3 章節、表格或 Mermaid 圖表，預設主題 `claude-canvas`。
- **Service Implementation**: Handled in `services/wiki_publisher.py` via `WikiPublisherService` (內建 `format_and_publish_if_long` 自動判斷與轉發布機制)。

