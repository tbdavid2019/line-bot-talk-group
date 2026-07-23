# Webhook Resiliency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract Firebase and Gemini SDK access, prevent duplicate webhook processing across containers, and persist chat messages without overwriting concurrent writes.

**Architecture:** `FirebaseService` owns RTDB access, event claims, and append-only transcript records. `GeminiService` owns synchronous text generation. The FastAPI webhook calls these blocking services through `asyncio.to_thread`; it claims an event before doing any side effect and reads ordered records to supply Gemini context.

**Tech Stack:** Python 3.13, FastAPI, python-firebase RTDB client, Google Generative AI SDK, unittest.

---

### Task 1: Firebase service contract

**Files:**
- Create: `services/firebase.py`
- Test: `test/test_firebase_service.py`

- [ ] Write failing unit tests for append-only message records and an already-claimed event.
- [ ] Run `python -m unittest test.test_firebase_service` and confirm it fails because the service module is absent.
- [ ] Implement the smallest `FirebaseService` API: `get_messages`, `append_message`, and `acquire_message_lock`.
- [ ] Re-run the unit tests and confirm they pass.

### Task 2: Gemini service contract

**Files:**
- Create: `services/gemini.py`
- Test: `test/test_gemini_service.py`

- [ ] Write a failing test showing that text generation delegates to a configured model.
- [ ] Run `python -m unittest test.test_gemini_service` and confirm it fails because the service module is absent.
- [ ] Implement `GeminiService.generate_content`.
- [ ] Re-run the unit test and confirm it passes.

### Task 3: Webhook integration

**Files:**
- Modify: `main.py`
- Test: `test/test_firebase_service.py`

- [ ] Replace direct transcript list reads/writes with the Firebase service methods.
- [ ] Claim each LINE `message.id` before processing, and ignore duplicate events.
- [ ] Wrap all Firebase, Gemini, GCS, and ASR synchronous SDK calls touched by the webhook in `asyncio.to_thread`.
- [ ] Run the unit tests to ensure append-only ordering and duplicate behavior remain correct.

### Task 4: Release record

**Files:**
- Modify: `CHANGELOG.md`

- [ ] Add an unreleased entry covering service extraction, cross-container deduplication, append-only transcripts, and async offloading.
- [ ] Run `python -m compileall main.py services test` and `python -m unittest discover -s test`.
