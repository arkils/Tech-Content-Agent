package com.techcontent.agent.fcm

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.util.Log
import androidx.core.app.NotificationCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.techcontent.agent.MainActivity
import com.techcontent.agent.R
import com.techcontent.agent.data.api.ApprovalRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * Handles incoming FCM messages and device token refresh events.
 *
 * When a new approval notification arrives, this service:
 *  1. Extracts the `approval_id` from the message data payload.
 *  2. Posts a system notification with the topic as the title.
 *  3. Attaches a tap intent that opens [MainActivity] → [ui.ApprovalDetailFragment].
 *
 * When the FCM token rotates ([onNewToken]), the new token is sent to the
 * Approval API Lambda (`POST /devices/token`) so SSM stays current.
 */
class TechAgentMessagingService : FirebaseMessagingService() {

    private val repository = ApprovalRepository()
    private val serviceScope = CoroutineScope(Dispatchers.IO)

    // ------------------------------------------------------------------
    // FCM callbacks
    // ------------------------------------------------------------------

    override fun onMessageReceived(message: RemoteMessage) {
        val approvalId = message.data["approval_id"] ?: run {
            Log.w(TAG, "Received FCM message without approval_id — ignoring")
            return
        }
        val topic = message.notification?.title
            ?: message.data["topic"]
            ?: "Content ready for review"
        val body = message.notification?.body
            ?: "Tap to review and approve your LinkedIn post."

        showNotification(approvalId, topic, body)
    }

    override fun onNewToken(token: String) {
        Log.d(TAG, "FCM token refreshed — registering with Approval API")
        serviceScope.launch {
            repository.updateDeviceToken(token).onFailure { err ->
                Log.e(TAG, "Failed to update device token: ${err.message}")
            }
        }
    }

    // ------------------------------------------------------------------
    // Private helpers
    // ------------------------------------------------------------------

    private fun showNotification(approvalId: String, title: String, body: String) {
        val manager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        ensureChannel(manager)

        val tapIntent = Intent(this, MainActivity::class.java).apply {
            action = "com.techcontent.agent.OPEN_APPROVAL"
            putExtra("approval_id", approvalId)
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            this,
            approvalId.hashCode(),
            tapIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()

        manager.notify(approvalId.hashCode(), notification)
    }

    private fun ensureChannel(manager: NotificationManager) {
        if (manager.getNotificationChannel(CHANNEL_ID) != null) return
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Content Approvals",
            NotificationManager.IMPORTANCE_HIGH,
        ).apply {
            description = "Notifications for LinkedIn posts awaiting your approval"
        }
        manager.createNotificationChannel(channel)
    }

    companion object {
        private const val TAG = "TechAgentFCM"
        private const val CHANNEL_ID = "content_approvals"
    }
}
