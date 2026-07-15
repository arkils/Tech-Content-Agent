package com.techcontent.agent.data.api

import com.techcontent.agent.data.model.ApprovalItem
import com.techcontent.agent.data.model.ApproveRequest
import com.techcontent.agent.data.model.DeviceTokenRequest
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

/**
 * Retrofit interface for the Approval API Lambda Function URL.
 *
 * All methods are `suspend` functions for use with Kotlin Coroutines.
 * The base URL is configured in [ApiClient].
 */
interface ApprovalApiService {

    /** Fetch the full approval record for the given [approvalId]. */
    @GET("approvals/{approvalId}")
    suspend fun getApproval(@Path("approvalId") approvalId: String): Response<ApprovalItem>

    /**
     * Approve the post for publishing.
     *
     * Pass [ApproveRequest.edited_content] if the user edited the text;
     * omit it (or pass `null`) to publish the original generated content.
     */
    @POST("approvals/{approvalId}/approve")
    suspend fun approve(
        @Path("approvalId") approvalId: String,
        @Body body: ApproveRequest = ApproveRequest(),
    ): Response<Unit>

    /** Reject the post — it will not be published. */
    @POST("approvals/{approvalId}/reject")
    suspend fun reject(@Path("approvalId") approvalId: String): Response<Unit>

    /**
     * Register or refresh the device FCM token in SSM.
     *
     * Called automatically by [fcm.TechAgentMessagingService.onNewToken].
     */
    @POST("devices/token")
    suspend fun updateDeviceToken(@Body body: DeviceTokenRequest): Response<Unit>
}
