# Human-in-the-Loop (HITL) Approval Pipeline

## Overview

This document describes the planned extension to add a human review and
approval step between content generation and publishing. Generated LinkedIn
posts are stored in DynamoDB and pushed to an Android app for review before
any publishing API is called.

---

## Decisions

| Decision | Choice | Reason |
|---|---|---|
| Notification channel | Firebase Cloud Messaging (FCM) | Free, reliable Android push |
| API layer | Lambda Function URLs | Free HTTPS — no API Gateway cost |
| Device token storage | SSM Parameter Store | Single user, no extra table needed |
| Approval scope (v1) | LinkedIn only | Start simple; model supports more platforms later |
| Orchestration | DynamoDB-based | No Step Functions — simpler and cheaper |
| Approval timeout | 24 hours (TTL) | DynamoDB auto-expires stale records |
| Editing | Yes — user can rewrite content in the app before confirming | |

---

## Architecture

```
EventBridge (daily cron)
    → Pipeline Lambda
        ├─ fetch + deduplicate + summarize + generate LinkedIn post  (unchanged)
        ├─ format_content(package) → store in approvals DynamoDB  (status: pending_approval)
        ├─ fetch FCM device token from SSM → send FCM push notification  (free)
        └─ mark_seen  (runs here — prevents re-fetch if pipeline re-runs before approval)

Android App  ←── FCM notification (topic + approval_id)
    └─ GET  {approval_api_function_url}/approvals/{id}   fetch post content
    └─ user reads post, optionally edits text
    └─ POST .../approve   (body: edited_content if changed)
    └─ POST .../reject    (no body needed)
                ↓  async Lambda invoke (InvocationType=Event)
        Publish Lambda
            └─ LinkedInPublisher.publish(edited_content or original_content)
            └─ PostTracker.mark_success / mark_error   (existing tool, unchanged)
            └─ ApprovalStore.mark_published / mark_failed
```

---

## New AWS Resources (~$0/month additional cost)

| Resource | Type | Notes |
|---|---|---|
| `tech-news-agent-approvals` | DynamoDB PAY_PER_REQUEST | TTL on `expires_at` (24 h) |
| Approval API Lambda | Python 3.12 | GET / approve / reject / device token update |
| Approval API Function URL | Lambda Function URL | Free HTTPS endpoint; auth via shared secret |
| Publish Lambda | Python 3.12 | Async-invoked on approve; posts to LinkedIn |
| `/tech-news-agent/fcm-server-key` | SSM SecureString | Firebase service account JSON |
| `/tech-news-agent/fcm-device-token` | SSM SecureString | Android device FCM token |
| `/tech-news-agent/hitl-secret` | SSM SecureString | Shared secret validated by Approval API |

**Removed / not needed:**
- ~~API Gateway~~ — replaced by free Lambda Function URLs
- ~~Devices DynamoDB table~~ — single user; token stored in SSM
- ~~EventBridge polling rule~~ — direct async Lambda invoke on approval

---

## Phase-by-Phase Implementation Plan

### Phase 1 — Data & Config

**`agent/models/__init__.py`**  
Add two new types:

```python
class ApprovalStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED         = "approved"
    REJECTED         = "rejected"
    PUBLISHED        = "published"
    FAILED           = "failed"

@dataclass
class ApprovalRecord:
    approval_id:      str           # UUID — DynamoDB PK
    run_id:           str           # pipeline run UUID
    platform:         str           # e.g. "linkedin"
    original_content: str           # generated post text
    topic:            str           # ContentPackage.topic
    status:           ApprovalStatus
    created_at:       datetime
    expires_at:       datetime      # TTL — 24 h after created_at
    edited_content:   str | None = None
    approved_at:      datetime | None = None
    published_at:     datetime | None = None
    error_message:    str | None = None
```

**`agent/config.py`**  
Add to `AgentConfig`:

```python
# HITL
hitl_enabled:         bool = os.environ.get("HITL_ENABLED", "false").lower() == "true"
approvals_table_name: str  = os.environ.get("APPROVALS_TABLE_NAME", "tech-news-agent-approvals")

# SSM paths (values never stored here)
FCM_SERVER_KEY_PARAM_PATH:  str = "/tech-news-agent/fcm-server-key"
FCM_DEVICE_TOKEN_PARAM_PATH: str = "/tech-news-agent/fcm-device-token"
HITL_SECRET_PARAM_PATH:     str = "/tech-news-agent/hitl-secret"
```

**`requirements.txt`**  
Add `google-auth>=2.29` (needed for FCM HTTP v1 OAuth token).

---

### Phase 2 — Backend Services (new files)

#### `agent/tools/approval_store.py`

DynamoDB CRUD for the approvals table. Constructor-injected `dynamodb_client`.

| Method | Description |
|---|---|
| `create_pending(run_id, platform, content, topic) → ApprovalRecord` | Write `pending_approval` record with 24-hour TTL |
| `get(approval_id) → ApprovalRecord \| None` | Fetch by primary key |
| `update_content(approval_id, edited_content)` | Save user-edited text |
| `approve(approval_id) → bool` | Conditional update (`pending_approval → approved`); returns `False` if already processed |
| `reject(approval_id) → bool` | Conditional update (`pending_approval → rejected`) |
| `mark_published(approval_id, platform_post_id, url)` | Set `published` + timestamps |
| `mark_failed(approval_id, error)` | Set `failed` + error message |

DynamoDB schema:

```
PK: approval_id  (String — UUID v4)

Attributes:
  run_id            String
  platform          String
  original_content  String
  edited_content    String   (optional)
  topic             String
  status            String
  created_at        String   (ISO-8601)
  expires_at        Number   (Unix epoch — TTL attribute)
  approved_at       String   (ISO-8601, optional)
  published_at      String   (ISO-8601, optional)
  platform_post_id  String   (optional)
  platform_url      String   (optional)
  error_message     String   (optional)
```

#### `agent/tools/push_notifier.py`

Sends a single FCM push notification when content is ready for review.

```python
class PushNotifier:
    def __init__(self, ssm_client, config=AgentConfig): ...

    def send_approval_notification(self, approval_id: str, topic: str, run_id: str) -> None:
        # 1. Fetch Firebase service account JSON from SSM (FCM_SERVER_KEY_PARAM_PATH)
        # 2. Fetch device FCM token from SSM (FCM_DEVICE_TOKEN_PARAM_PATH)
        # 3. Build OAuth2 access token via google.oauth2.service_account.Credentials
        # 4. POST to https://fcm.googleapis.com/v1/projects/{project_id}/messages:send
        #    Notification title: "Content ready: {topic}"
        #    Data payload:  {"approval_id": "...", "run_id": "..."}
```

---

### Phase 3 — Pipeline Changes

**`agent/workflows/news_pipeline.py`**  
Add optional constructor params `approval_store: ApprovalStore | None` and `push_notifier: PushNotifier | None`.

In `run()`, after Step 4 (generate), branch on `self._config.hitl_enabled`:

```
HITL_ENABLED=true  →  Step 5 becomes:
    run_id = str(uuid4())
    for each enabled publisher:
        content = publisher.format_content(package)
        record  = approval_store.create_pending(run_id, platform, content, topic)
        push_notifier.send_approval_notification(record.approval_id, topic, run_id)
    result.awaiting_approval = True
    # Step 6 (mark_seen) runs as normal

HITL_ENABLED=false →  pipeline runs exactly as today (no change)
```

`PipelineResult` gains a new field: `awaiting_approval: bool = False`.

---

### Phase 4 — Lambda Handlers (new files)

#### `agent/handlers/__init__.py`  
Empty package init.

#### `agent/handlers/approval_api.py`

Lambda Function URL handler. Parses `event["rawPath"]` + `event["requestContext"]["http"]["method"]`.

Auth: validates `x-hitl-secret` header on every request against the value fetched from SSM on Lambda cold start. Returns `401` on mismatch.

| Route | Method | Action |
|---|---|---|
| `/approvals/{id}` | GET | Return `ApprovalRecord` as JSON |
| `/approvals/{id}/approve` | POST | `update_content` (if body has `edited_content`) + `approve` + async-invoke Publish Lambda |
| `/approvals/{id}/reject` | POST | `reject` |
| `/devices/token` | POST | `ssm.put_parameter` to update `FCM_DEVICE_TOKEN_PARAM_PATH` |

Returns JSON with appropriate HTTP status codes and CORS headers.

#### `agent/handlers/publish_handler.py`

Async-invoked by `approval_api`. Event: `{"approval_id": "..."}`.

```
1. approval_store.get(approval_id)
2. effective_content = record.edited_content or record.original_content
3. publisher = get_active_publishers([record.platform])[0]
4. post_id = post_tracker.create_pending(platform, effective_content, topic)
5. result = publisher.publish(effective_content)
6. post_tracker.mark_success / mark_error(post_id, ...)
7. approval_store.mark_published / mark_failed(approval_id, ...)
```

---

### Phase 5 — Infrastructure

#### `infrastructure/stacks/storage_stack.py`  
Add `self.approvals_table` (PAY_PER_REQUEST, TTL on `expires_at`, AWS-managed encryption).

#### `infrastructure/stacks/approval_stack.py` (new)

```
ApprovalStack
  ├─ approval_api_lambda
  │     handler:  agent.handlers.approval_api.handler
  │     Function URL (auth=NONE; secret validated in code)
  │     env: APPROVALS_TABLE_NAME, PUBLISH_LAMBDA_ARN, HITL_SECRET_PARAM_PATH
  │     IAM: approvals_table r/w, SSM /tech-news-agent/*, lambda:InvokeFunction on publish_lambda
  │
  └─ publish_lambda
        handler:  agent.handlers.publish_handler.handler
        env: APPROVALS_TABLE_NAME, POSTS_TABLE_NAME
        IAM: approvals_table r/w, posts_table r/w, SSM /tech-news-agent/*
```

#### `infrastructure/stacks/agent_stack.py`  
Add env vars `HITL_ENABLED` and `APPROVALS_TABLE_NAME`.  
Add IAM: `approvals_table.grant_write_data(self.function)` + SSM read for FCM params.

#### `infrastructure/app.py`  
Instantiate `ApprovalStack` after `StorageStack`; pass `approvals_table` and `posts_table`.

---

### Phase 6 — Android App (`android/`)

Kotlin, min SDK 26 (Android 8.0), single-activity + Navigation Component.

**Dependencies (app/build.gradle.kts)**

```kotlin
// FCM
implementation("com.google.firebase:firebase-messaging-ktx:24.x")
// Network
implementation("com.squareup.retrofit2:retrofit:2.11.x")
implementation("com.squareup.retrofit2:converter-gson:2.11.x")
implementation("com.squareup.okhttp3:okhttp:4.12.x")
implementation("com.squareup.okhttp3:logging-interceptor:4.12.x")
// Jetpack
implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.8.x")
implementation("androidx.lifecycle:lifecycle-livedata-ktx:2.8.x")
implementation("androidx.navigation:navigation-fragment-ktx:2.8.x")
implementation("androidx.navigation:navigation-ui-ktx:2.8.x")
// UI
implementation("com.google.android.material:material:1.12.x")
// Coroutines
implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.x")
```

**`local.properties`** (excluded from git):

```properties
LAMBDA_BASE_URL=https://<your-function-url>.lambda-url.us-east-1.on.aws
HITL_SECRET=<value-from-ssm-hitl-secret-param>
```

**Project structure:**

```
android/
  app/
    google-services.json              ← add from Firebase Console (excluded from git)
    src/main/
      AndroidManifest.xml
      java/com/techcontent/agent/
        MainActivity.kt               ← NavHostFragment, toolbar
        data/
          api/
            ApprovalApiService.kt     ← Retrofit interface
            ApiClient.kt              ← OkHttp singleton; injects x-hitl-secret header
            ApprovalRepository.kt     ← suspend funs wrapping Retrofit calls
          model/
            ApprovalItem.kt           ← data class matching API JSON response
        fcm/
          TechAgentMessagingService.kt
            onNewToken()              ← POST /devices/token to update SSM
            onMessageReceived()       ← show notification; tap → ApprovalDetailFragment
        ui/
          ApprovalDetailFragment.kt   ← topic + post content; Edit / Confirm / Reject
          ApprovalDetailViewModel.kt  ← holds ApprovalItem LiveData; calls repository
      res/
        layout/
          activity_main.xml
          fragment_approval_detail.xml
        navigation/
          nav_graph.xml
  build.gradle.kts                    ← project-level (classpath plugins)
  settings.gradle.kts
  .gitignore                          ← google-services.json, local.properties, build/
```

**Key interaction flow in the app:**

1. FCM notification arrives → `TechAgentMessagingService.onMessageReceived`
   - Extract `approval_id` from data payload
   - Show system notification with title and body from notification payload
   - Notification tap intent: open `ApprovalDetailFragment` with `approval_id`

2. `ApprovalDetailFragment` opens
   - ViewModel calls `GET /approvals/{id}` → displays topic + post text
   - User taps **Edit** → `TextInputEditText` becomes editable
   - User taps **Confirm** → `POST /approvals/{id}/approve` with optional edited text
   - User taps **Reject** → `POST /approvals/{id}/reject`
   - UI shows loading spinner while request in flight; success/error snackbar after

3. `TechAgentMessagingService.onNewToken`
   - Called by FCM when token rotates
   - Calls `POST /devices/token` with new token so SSM stays current

---

### Phase 7 — Tests

| File | What it covers |
|---|---|
| `tests/tools/test_approval_store.py` | moto DynamoDB; all CRUD paths, conditional-update edge cases |
| `tests/tools/test_push_notifier.py` | mock SSM (moto) + `responses` library; FCM payload structure, missing token handling |
| `tests/handlers/test_approval_api.py` | mock `ApprovalStore` + Lambda client; all routes; wrong secret → 401; approve invokes publish Lambda |
| `tests/handlers/test_publish_handler.py` | mock `ApprovalStore` + publisher + `PostTracker`; publish success and error paths |
| `tests/test_news_pipeline.py` | extend existing tests: HITL=true → approvals created, no direct publish; HITL=false → existing behaviour unchanged |

---

## Setup Prerequisites (one-time)

Before deploying:

1. **Create a Firebase project** at [console.firebase.google.com](https://console.firebase.google.com)
2. Enable **Cloud Messaging** in the project settings
3. Download the **service account JSON** from *Project Settings → Service Accounts*
4. Store the JSON string in SSM:
   ```
   aws ssm put-parameter \
     --name /tech-news-agent/fcm-server-key \
     --value "$(cat serviceAccountKey.json)" \
     --type SecureString
   ```
5. Download `google-services.json` and place it in `android/app/` (excluded from git)
6. Generate a random shared secret and store it:
   ```
   aws ssm put-parameter \
     --name /tech-news-agent/hitl-secret \
     --value "<random-secret>" \
     --type SecureString
   ```
7. Add `HITL_SECRET=<same-value>` to `android/app/local.properties`
8. After first app install, launch the app — `onNewToken` will automatically register
   the device token in SSM

---

## Enabling HITL

```bash
# Deploy with HITL enabled
cdk deploy --all -c hitl_enabled=true

# Or set env var on the pipeline Lambda directly
HITL_ENABLED=true
```

When `HITL_ENABLED=false` (the default), the pipeline publishes directly with zero behaviour change.
