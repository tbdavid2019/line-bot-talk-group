# Plan: LINE Bot auto-save group files to Google Drive (per-group single destination)

## Goal (MVP = option 3)

- Bot is in multiple LINE groups.
- Each LINE group can enable **one** Google Drive destination (one Google account + one folder).
- A group “owner/admin” binds the group and authorizes Google Drive via OAuth.
- When the group receives a file, the bot uploads it into that group’s configured Drive folder.

Non-goals for MVP:

- Per-user per-group destinations (matrix model) (defer).
- Fancy folder picker UI (defer; start with “create default folder” or “paste folder link/ID”).
- Multi-admin approvals / complex ACL.

## Constraints from current repo

- Backend: FastAPI.
- Persistence: Firebase Realtime Database with paths like `groups/{group_id}/messages` and `groups/{group_id}/info`.
- LINE SDK: `line-bot-sdk`.

## User flows

## Ownership model (decided)

- One owner per group (no global superadmin).
- First-come-first-served: the first user who completes `!drive bind` + DM OAuth becomes `owner_line_user_id`.
- Once a group has an owner, only the owner can disable (`!drive off`) or change Drive settings.
- To hand over ownership (future): owner disables export, then a new user can bind.

### 1) Bind group → user

Purpose: prevent random users from configuring Drive for groups they don’t control.

1. In the group, a user types: `!drive bind`
2. Bot replies in the group with a one-time binding code (e.g. `GDRIVE-83K2P`) and instructions:
   - “Please DM me: `!drive link GDRIVE-83K2P` within 10 minutes.”
3. User opens 1:1 chat with bot and sends: `!drive link GDRIVE-83K2P`
4. Bot validates:
   - code exists, not expired
   - code is for that group_id
   - (optional) the requester’s LINE user_id matches the one who issued bind in group
5. Bot responds with an OAuth login URL.

Edge case: if `drive_export` is already enabled/owned for that group, `!drive bind` should be rejected with guidance to use `!drive status` and ask the current owner to `!drive off`.

### 2) Google OAuth (Drive)

1. User opens OAuth login URL.
2. Google consent screen → callback to our FastAPI endpoint.
3. Callback exchanges code for tokens.
4. Persist refresh token (encrypted) + chosen destination folder.
5. Bot confirms in LINE DM: “Group X Drive export enabled.”

### 3) Configure destination folder

Two viable MVP options (pick one):

Option A (simplest UX/ops):
- After OAuth, bot creates a folder:
  - `LINE Bot Exports/{group_id}` (or group name if available)
- Store that folder_id as destination.

Option B (user chooses parent folder without UI):
- After OAuth, ask user to paste a Google Drive folder link/ID.
- Bot calls Drive API to validate folder access, then saves folder_id.

Recommendation for fastest shipping: Option A first, then add Option B.

### 4) Upload on file message

1. Group receives a file message event.
2. Bot downloads the binary from LINE using message_id.
3. Bot checks `groups/{group_id}/info/drive_export`:
   - enabled?
   - has owner + refresh token + folder_id?
4. If configured, bot uploads to Drive folder.
5. Bot optionally replies (or not) in group:
   - MVP: stay quiet to avoid noise; only reply on failure if explicitly asked (`!drive status`).

## Command surface

Group commands:

- `!drive bind` → generates binding code.
- `!drive status` → shows enabled/disabled + owner + destination folder.
- `!drive off` → disables export (owner only).

DM commands:

- `!drive link <CODE>` → begins OAuth for that group.
- `!drive folder <FOLDER_LINK_OR_ID>` → (if using Option B) set destination folder.
- `!drive unlink <GROUP_ID>` → revoke group export (owner only).

## Data model (Firebase)

Store minimal, explicit state. Suggested paths:

### Group config

`groups/{group_id}/info/drive_export`

- `enabled`: bool
- `owner_line_user_id`: string
- `owner_claimed_at`: unix
- `group_name`: string (optional; can be from LINE group summary)
- `google`
  - `refresh_token_enc`: string
  - `token_created_at`: unix
  - `scopes`: string[]
  - `subject_email`: string (optional; if available)
- `drive`
  - `folder_id`: string
  - `folder_name`: string (optional)
- `bind`
  - `active_code`: string
  - `expires_at`: unix
  - `requested_by_line_user_id`: string

### Upload dedupe (idempotency)

`groups/{group_id}/info/drive_export/uploads/{line_message_id}`

- `status`: `pending|success|failed`
- `drive_file_id`: string (on success)
- `error`: string (on failed)
- `created_at`: unix

This prevents double uploads if LINE retries webhooks or we retry internally.

## Google Drive integration

### Google Cloud setup

- Create GCP project.
- Enable Google Drive API.
- Configure OAuth consent screen.
- Create OAuth Client ID (Web application).
- Set redirect URI(s): `https://<your-domain>/auth/google/callback`

### Scopes

Prefer least privilege:

- Start with `https://www.googleapis.com/auth/drive.file`
  - Allows the app to create and manage files it creates.
  - Works well with “Option A: app creates folder and uploads inside”.

If later you want arbitrary-folder selection and broader access, you may need `drive` scope, which is much heavier.

### Token storage

- Store refresh tokens encrypted at rest (app-level encryption).
- Rotation: support “relink” if refresh token revoked.

## Security & privacy

- Encryption key for tokens via env var (e.g. `TOKEN_ENCRYPTION_KEY`).
- Never log refresh tokens or OAuth codes.
- Validate OAuth `state` parameter strictly (contains group_id + line_user_id + nonce + expiry).
- Prevent “link hijack”: `!drive link CODE` must bind to the correct LINE user_id.

## Reliability (must-have)

- Webhook retries: assume LINE may retry; implement dedupe by message_id.
- Upload retries: exponential backoff; mark failed with reason.
- Streaming upload: avoid loading big files fully into memory.
- File size limits: decide a max size; report if exceeded.

## Observability

- Structured logs: group_id, message_id, drive_file_id, latency.
- Minimal metrics (even just logs): success/fail counts.

## Implementation milestones

### Milestone 0: design decisions (30–60 min)

- Choose folder strategy: Option A vs B.
- Decide whether to be silent on upload or post a confirmation.
- Decide maximum file size.

### Milestone 1: data model + commands

- Add `!drive bind`, `!drive status`, `!drive off` (group).
- Add `!drive link <CODE>` (DM).
- Persist bind code + expiry in Firebase.

### Milestone 2: OAuth endpoints

- `/auth/google/start` (build state, redirect to Google).
- `/auth/google/callback` (exchange code, store refresh token encrypted).
- DM confirmation to user.

### Milestone 3: Drive folder + upload pipeline

- Create destination folder (Option A) OR validate provided folder (Option B).
- Handle LINE file message event → download → upload → store idempotency record.

### Milestone 4: hardening

- Retry logic + dedupe.
- Better error messages in `!drive status`.
- Add docs: required env vars + Google setup steps.

## Acceptance criteria (MVP)

- In a group: `!drive bind` generates code.
- In DM: `!drive link CODE` completes OAuth and enables export.
- When any member posts a file in that group, a copy appears in the configured Drive folder.
- `!drive status` shows correct enabled state.

## Open questions (need your decision)

1) Folder strategy for MVP: Option A (auto-create) or Option B (paste folder link)?

2) Upload confirmation behavior:
- Silent (recommended) vs reply per file vs daily summary.

3) Ownership is decided:
- Only the group owner can disable/replace settings (first-come-first-served).
