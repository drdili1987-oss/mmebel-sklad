package uz.mmebel.sklad

import android.Manifest
import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.net.Uri
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
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
        Push.show(this, n.title ?: getString(R.string.app_name), n.body ?: "", message.data["sound"])
    }
}

/** Ovozli kanal: server `sound` kaliti -> kanal ID, nom, res/raw dagi ovoz. Server bilan mos (mmebel/push.py SOUNDS). */
private data class SoundChannel(val id: String, val nameRes: Int, val rawRes: Int)

object Push {
    const val CHANNEL_ID = "orders"
    private const val PREFS = "push"
    private val TOKEN_RE = Regex("^[A-Za-z0-9:_\\-]{20,4096}$")
    private val SOUND_CHANNELS = mapOf(
        "new" to SoundChannel("order_new", R.string.channel_new, R.raw.yangi_buyurtma),
        "ready" to SoundChannel("order_ready", R.string.channel_ready, R.raw.buyurtma_tayyor),
        "cancel" to SoundChannel("order_cancel", R.string.channel_cancel, R.raw.buyurtma_bekor),
    )

    /** Barcha kanallarni yaratadi. Android 8+ da kanal ovozi keyin o'zgarmaydi — yangi ovoz = yangi kanal ID. */
    fun ensureChannel(ctx: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val nm = ctx.getSystemService(NotificationManager::class.java)
        val base = NotificationChannel(CHANNEL_ID, ctx.getString(R.string.channel_orders), NotificationManager.IMPORTANCE_HIGH)
        base.description = ctx.getString(R.string.channel_orders_desc)
        nm.createNotificationChannel(base)
        val attrs = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_NOTIFICATION)
            .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
            .build()
        for (sc in SOUND_CHANNELS.values) {
            val ch = NotificationChannel(sc.id, ctx.getString(sc.nameRes), NotificationManager.IMPORTANCE_HIGH)
            ch.setSound(rawUri(ctx, sc.rawRes), attrs)
            ch.enableVibration(true)
            nm.createNotificationChannel(ch)
        }
    }

    private fun rawUri(ctx: Context, res: Int): Uri =
        Uri.parse("android.resource://${ctx.packageName}/$res")

    fun saveToken(ctx: Context, token: String) {
        if (TOKEN_RE.matches(token)) {
            ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString("token", token).apply()
        }
    }

    fun token(ctx: Context): String? =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString("token", null)?.takeIf { TOKEN_RE.matches(it) }

    @SuppressLint("MissingPermission") // ruxsat quyida aniq tekshiriladi
    fun show(ctx: Context, title: String, body: String, sound: String? = null) {
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            return
        }
        ensureChannel(ctx)
        val open = PendingIntent.getActivity(
            ctx, 0,
            Intent(ctx, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val sc = SOUND_CHANNELS[sound]
        val builder = NotificationCompat.Builder(ctx, sc?.id ?: CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_stat_notify)
            .setColor(ctx.getColor(R.color.accent))
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(open)
        // Android 7 va pastida kanal yo'q — ovoz bildirishnomaning o'zida
        if (sc != null && Build.VERSION.SDK_INT < Build.VERSION_CODES.O) builder.setSound(rawUri(ctx, sc.rawRes))
        val notif = builder.build()
        try {
            NotificationManagerCompat.from(ctx).notify((System.currentTimeMillis() % Int.MAX_VALUE).toInt(), notif)
        } catch (e: SecurityException) {
            // Foydalanuvchi bildirishnomalarga ruxsat bermagan
        }
    }
}
