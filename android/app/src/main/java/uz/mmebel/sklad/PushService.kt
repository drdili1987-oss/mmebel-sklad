package uz.mmebel.sklad

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

/**
 * Firebase push xabarlari. Ilova orqa fonda bo'lsa, tizim xabarni o'zi ko'rsatadi;
 * ilova ochiq bo'lsa, shu yerda ko'rsatamiz.
 */
class PushService : FirebaseMessagingService() {

    override fun onNewToken(token: String) {
        Push.saveToken(this, token)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val n = message.notification ?: return
        Push.show(this, n.title ?: getString(R.string.app_name), n.body ?: "")
    }
}

object Push {
    const val CHANNEL_ID = "orders"
    private const val PREFS = "push"
    private val TOKEN_RE = Regex("^[A-Za-z0-9:_\\-]{20,4096}$")

    fun ensureChannel(ctx: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(CHANNEL_ID, ctx.getString(R.string.channel_orders), NotificationManager.IMPORTANCE_HIGH)
            ch.description = ctx.getString(R.string.channel_orders_desc)
            ctx.getSystemService(NotificationManager::class.java).createNotificationChannel(ch)
        }
    }

    fun saveToken(ctx: Context, token: String) {
        if (TOKEN_RE.matches(token)) {
            ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString("token", token).apply()
        }
    }

    fun token(ctx: Context): String? =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString("token", null)?.takeIf { TOKEN_RE.matches(it) }

    fun show(ctx: Context, title: String, body: String) {
        ensureChannel(ctx)
        val open = PendingIntent.getActivity(
            ctx, 0,
            Intent(ctx, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val notif = NotificationCompat.Builder(ctx, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_stat_notify)
            .setColor(ctx.getColor(R.color.accent))
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(open)
            .build()
        try {
            NotificationManagerCompat.from(ctx).notify((System.currentTimeMillis() % Int.MAX_VALUE).toInt(), notif)
        } catch (e: SecurityException) {
            // Foydalanuvchi bildirishnomalarga ruxsat bermagan
        }
    }
}
