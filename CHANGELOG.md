# Changelog

All notable changes to this project will be documented in this file.

## 2026-08-27

### Added
- **GitHub Actions Multi-Arch Docker Hub CI/CD (`.github/workflows/docker-build-push.yml`)**:
  - Configured automated GitHub Actions workflow utilizing QEMU and Docker Buildx to build and push dual-architecture Docker images (`linux/amd64`, `linux/arm64`) to Docker Hub (`tbdavid2019/linebot-gemini-summarize`, `tbdavid2019/line-bot-talk-group`) and GitHub Container Registry (GHCR).
  - Integrated GitHub Secrets (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`) with fallback repository naming.
  - Added triggers on push to `master`/`main`, release tags (`v*`), pull requests, and manual execution (`workflow_dispatch`).
  - Added `.dockerignore` to secure API keys, credentials, local virtual environments, and cache files from Docker contexts.
  - Optimized `Dockerfile` layer caching and added system dependencies (`git`, `curl`) for robust multi-arch compilation.
- **Autonomous Multi-Turn Tool Calling & Agent Loop (`services/llm.py`)**:
  - Empowered `LLMService` (`gpt-5.6-luna`) with autonomous tool calling:
    - `search_web(query)`: 2MD SERP live web search
    - `read_web_page(url)`: 2MD Fast Reader full Markdown extraction
    - `get_live_weather(location)`: Instant meteorological telemetry (temperature, feels-like, condition, humidity, wind speed, UV index, forecasts)
  - Implemented multi-turn tool execution loop resolving user inquiries with zero excuses and zero hallucinations.
- **2MD Fast Reader & SERP Live Web Search Engine (`services/web_search.py`)**:
  - Implemented `WebSearchService` integrating real-time web search (SERP), live meteorology telemetry, and URL to Markdown reader across multi-tier 2MD endpoints:
    - Primary: `https://2md.aiurl.tw`
    - Fallback 1: `https://2md.glsoft.ai`
    - Fallback 2: `https://create360.ai`
  - Integrated live search auto-enrichment into `LLMService` to ground AI responses on real-time facts, stock quotes, financial market quotes, weather, and breaking news.
  - Automatically fetches and summarizes web pages when URLs are sent or when commands `!read <URL>` / `!搜尋 <query>` are executed.
  - Added unit test suite `test/test_web_search.py`.
- **Unified LLM Service (`services/llm.py`)**:
  - Implemented `LLMService` with automatic multi-tier failover:
    - Primary: `https://nen.com.tw/v1` (`gpt-5.6-luna`)
    - Fallback: `https://api.groq.com/openai/v1` (`openai/gpt-oss-20b`)
    - 3rd Tier: Google Gemini (`gemini-flash-latest`)
  - Added unit test suite `test/test_llm_service.py`.
- **Image Generator Service (`services/image_generator.py`)**:
  - Implemented `ImageGeneratorService` with dual-tier failover:
    - Primary: `https://nen.com.tw/v1` (`gemini-3.1-flash-image`)
    - Fallback: `https://generativelanguage.googleapis.com/v1beta` (`gemini-3.1-flash-image` / `gemini-3-pro-image-preview` / `gemini-2.5-flash-image`)
    - Storage: Automatic multi-tier CDN storage via 888box (`services/box_storage.py`).
  - Added unit test suite `test/test_image_generator.py` covering primary success, fallback recovery, and storage upload.
- **David888 Wiki Publisher Service (`services/wiki_publisher.py`)**:
  - Implemented `WikiPublisherService` integrating REST publishing with `https://wiki.david888.com/api`.
  - **LLM Autonomous Wiki Publishing (AI-First Canvas)**: Whenever a user requests in-depth analysis, research reports, tutorials, or system designs, LLM autonomously drafts rich Markdown with `[TOC]`, section headings, and diagrams, publishes it directly to David888 Wiki, and replies in LINE with a clean executive summary plus public `shareUrl`.
  - Added commands `!wiki summary` (AI summary to Wiki) and `!wiki <title> <content>`.
  - Added unit test suite `test/test_wiki_publisher.py` covering auto-publishing logic, markdown formatting, and API integration.
- **888box Asset Storage Service (`services/box_storage.py`)**:
  - Implemented `BoxStorageService` supporting high-speed asset uploads and CDN delivery.
  - Multi-tier automatic failover across Primary (`https://box.david888.com`), Fallback 1 (`https://box.glsoft.ai`), and Fallback 2 (`https://box.aiurl.tw`).
  - Added unit test suite `test/test_box_storage.py` verifying failover and asset upload workflows.
  - Integrated `upload_asset_to_storage` into `main.py` for generated images, media downloads, and file exports.
- **Docker Compose & Scoped Watchtower Setup (`docker-compose.yml`)**:
  - Configured multi-container orchestration for `LINE-377mwhqu` (Port 8080) and `LINE-113huwec` (Port 8081).
  - Added HTTP healthchecks (`curl -f http://localhost:8080/`).
  - Added dedicated `watchtower-linebot` auto-updater locked specifically to LINE Bot containers with `WATCHTOWER_SCOPE=linebot`.
- **Engineering Guidelines (`AGENTS.md`)**:
  - Established permanent protocol requiring automated synchronization of `CHANGELOG.md`, `README.md`, and unit tests on every change.

### Fixed
- **Direct TextMessage Format & Clickable/Copyable LINE Output**:
  - Replaced non-selectable Flex Messages with native `TextMessage` for all AI responses, general conversations, summaries, and system messages, ensuring users can directly select/copy text and click URLs on both Mobile and Desktop LINE clients.
- **David888 Wiki Auto-Publish Boundary & Content Preservation**:
  - Fixed over-aggressive Wiki publishing where general questions (like "what can you do?") had their answers hidden behind a bare Wiki URL.
  - Restricted auto-publishing to explicit user intent (`!wiki`, `wiki`, `david888`, `維基`), and ensured that whenever a Wiki note is published, the full answer is ALWAYS delivered directly inside LINE alongside the clickable `shareUrl`.
- **GeminiService Direct LLM Delegation Fix**:
  - Resolved an issue where `GeminiService` passed deprecated `genai.GenerativeModel` directly to Google GenAI SDK which hung the event loop and caused LINE webhook timeouts.
  - Ensured all conversation and AI query routes in `main.py` and `services/gemini.py` directly route to `LLMService` (`https://nen.com.tw/v1` `gpt-5.6-luna` -> `groq` fallback).
- **Firebase Auth Decoupling & 401 Lock Resolution**:
  - Removed erroneous fallback from Firebase authentication to `GOOGLE_APPLICATION_CREDENTIALS` (which is exclusively for GCS storage under a different project), resolving 401 Unauthorized errors during event deduplication and message locking.
  - Aligned production `FIREBASE_URL` with active real-time database instance (`https://aicreate360-official-website-default-rtdb.asia-southeast1.firebasedatabase.app/`).
- **Gemini LLM API Key Fallback & Key Rotation**:
  - Rotated Gemini API key to active working credential (`ASR_GEMINI_API_KEY`), and added automatic fallback mechanism in `main.py` to prevent service interruption when primary LLM key expires.
- **Group `@` Mention False Trigger Resolution**:
  - Fixed issue where the bot falsely chimed in when users `@` mentioned other members (e.g. `@Alice`, `@Bob`) or `@All` in group chats when keywords like `bot` or `機器人` appeared in text.
  - Added native LINE `is_self: bool` check on all `mentionees` to verify if the bot itself was targeted.
  - Added strict regex boundary matching for manual `@<bot_id>` and `@Bot` calls.
  - Added `extract_clean_question()` to preserve intra-sentence `@` symbols in questions (e.g. `@decorator`).
  - Added 23 unit test cases in `test/test_mention_detection.py` covering all mention scenarios.

## 2026-07-23

### Added
- Added `services/firebase.py` to centralize Firebase RTDB reads, writes, append-only conversation records, transcript clearing, and conditional event claims.
- Added `services/gemini.py` to centralize Gemini text-generation access.
- Added offline `unittest` coverage for Firebase append-only persistence, legacy transcript compatibility, conditional deduplication conflicts, and Gemini service delegation.

### Changed
- LINE webhook processing now atomically claims each `message.id` in Firebase before any side effect, preventing duplicate replies and duplicate image/file work when LINE retries reach another container.
- Conversation updates now append records below `message_events` instead of overwriting the full `messages` list, while retaining reads of legacy history.
- Moved synchronous Firebase RTDB, Gemini text generation, ASR transcription, GCS uploads, and image-stream collection off FastAPI's event loop with `asyncio.to_thread`.

## [1.1.0] - 2026-07-23

### Added
- **Firebase Authentication Support**: Added `FirebaseServiceAccountAuth` class and `get_firebase_db()` helper function in `main.py` to support Google Cloud Service Account OAuth2 authentication for Firebase Realtime Database.
- **Automatic Key Discovery**: Automatically detects Service Account JSON credentials located in the `key/` directory or specified via `FIREBASE_CREDENTIALS` / `FIREBASE_KEY_PATH` / `GOOGLE_APPLICATION_CREDENTIALS` environment variables.
- **Security Protections**: Updated `.gitignore` to strictly exclude all `*.json` key files, `key/` folder, and private credentials to prevent key leaks to repository.

### Changed
- Refactored all `firebase.FirebaseApplication` instances in `main.py` to use `get_firebase_db()`.
- Updated `test/test_firebase.py` to support authenticated testing with Service Account key.
- Updated `.env.example` to document `FIREBASE_CREDENTIALS` option.
