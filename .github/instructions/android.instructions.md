---
applyTo: "android/**"
---

# Android App Instructions

When working on any file under `android/`, always read `docs/hitl-plan.md`
first. It is the single source of truth for the architecture, API contracts,
data models, and setup steps for this app.

## Key reference points in docs/hitl-plan.md

| Section | What it covers |
|---|---|
| **Architecture** | End-to-end flow: pipeline → DynamoDB → FCM → app → Lambda Function URL → publish |
| **API routes** | All `GET`/`POST` endpoints the app calls on the Approval API Lambda |
| **`ApprovalItem` schema** | JSON fields returned by `GET /approvals/{id}` — must match `data/model/ApprovalItem.kt` |
| **Auth** | `x-hitl-secret` header; value comes from `local.properties` → `BuildConfig.HITL_SECRET` |
| **`local.properties`** | Required keys: `LAMBDA_BASE_URL`, `HITL_SECRET` — never commit these values |
| **Firebase setup** | One-time steps to create project, download `google-services.json`, store FCM key in SSM |
| **Phase 6** | Full Android project structure and dependency list |

## Conventions

- `BuildConfig.LAMBDA_BASE_URL` and `BuildConfig.HITL_SECRET` are the only
  way to read the Lambda URL and secret — never hard-code them.
- `google-services.json` and `local.properties` are excluded from git (see `android/.gitignore`).
- All API calls go through `ApprovalRepository` — the Fragment/ViewModel never
  calls Retrofit directly.
- Network calls must be `suspend` functions running inside `viewModelScope`.
- Use `Result<T>` (Kotlin stdlib) for error handling in the repository layer —
  never throw from a repository method.
- Min SDK is 26 (Android 8.0) — do not use APIs below that level without a
  compat check.
