# Changelog

All notable changes to this project will be documented in this file.

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
