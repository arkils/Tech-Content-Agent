package com.techcontent.agent.data.api

import com.techcontent.agent.data.model.ApprovalItem
import com.techcontent.agent.data.model.ApproveRequest
import com.techcontent.agent.data.model.DeviceTokenRequest

/**
 * Data-layer wrapper around [ApprovalApiService].
 *
 * Converts Retrofit [retrofit2.Response] into a [Result] so the ViewModel
 * never deals with HTTP status codes directly.
 */
class ApprovalRepository(
    private val api: ApprovalApiService = ApiClient.approvalApiService,
) {

    suspend fun getApproval(approvalId: String): Result<ApprovalItem> = runCatching {
        val response = api.getApproval(approvalId)
        response.body() ?: error("Empty response body (HTTP ${response.code()})")
    }

    suspend fun approve(approvalId: String, editedContent: String?): Result<Unit> = runCatching {
        val response = api.approve(approvalId, ApproveRequest(edited_content = editedContent))
        if (!response.isSuccessful) error("Approve failed (HTTP ${response.code()})")
    }

    suspend fun reject(approvalId: String): Result<Unit> = runCatching {
        val response = api.reject(approvalId)
        if (!response.isSuccessful) error("Reject failed (HTTP ${response.code()})")
    }

    suspend fun updateDeviceToken(token: String): Result<Unit> = runCatching {
        val response = api.updateDeviceToken(DeviceTokenRequest(fcm_token = token))
        if (!response.isSuccessful) error("Token update failed (HTTP ${response.code()})")
    }
}
