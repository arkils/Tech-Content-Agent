package com.techcontent.agent.data.model

/**
 * Mirrors the JSON response from `GET /approvals/{id}` on the Approval API Lambda.
 *
 * All fields match the [ApprovalRecord][agent.models.ApprovalRecord] DynamoDB schema.
 * Gson deserialises the Lambda JSON response directly into this class.
 */
data class ApprovalItem(
    val approval_id: String,
    val run_id: String,
    val platform: String,
    val original_content: String,
    val topic: String,
    val status: String,
    val created_at: String,
    val expires_at: Long,
    val edited_content: String? = null,
    val approved_at: String? = null,
    val published_at: String? = null,
    val error_message: String? = null,
)

/** Request body for `POST /approvals/{id}/approve`. */
data class ApproveRequest(
    val edited_content: String? = null,
)

/** Request body for `POST /devices/token`. */
data class DeviceTokenRequest(
    val fcm_token: String,
)
