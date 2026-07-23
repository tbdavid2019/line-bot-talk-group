# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2026-07-23

### Added
- **Firebase Authentication Support**: Added `FirebaseServiceAccountAuth` class and `get_firebase_db()` helper function in `main.py` to support Google Cloud Service Account OAuth2 authentication for Firebase Realtime Database.
- **Automatic Key Discovery**: Automatically detects Service Account JSON credentials located in the `key/` directory or specified via `FIREBASE_CREDENTIALS` / `FIREBASE_KEY_PATH` / `GOOGLE_APPLICATION_CREDENTIALS` environment variables.
- **Security Protections**: Updated `.gitignore` to strictly exclude all `*.json` key files, `key/` folder, and private credentials to prevent key leaks to repository.

### Changed
- Refactored all `firebase.FirebaseApplication` instances in `main.py` to use `get_firebase_db()`.
- Updated `test/test_firebase.py` to support authenticated testing with Service Account key.
- Updated `.env.example` to document `FIREBASE_CREDENTIALS` option.
