package uz.mmebel.sklad

import android.annotation.SuppressLint
import android.content.ActivityNotFoundException
import android.content.Intent
import android.graphics.Bitmap
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.webkit.CookieManager
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback

/**
 * MMebel paneli uchun Android qobiq.
 * Panel serverdan yuklanadi (har doim eng yangi versiya), kirish Telegram bot orqali tasdiqlanadi.
 * O'z serverimizdan tashqari barcha havolalar (t.me, tel:) tashqi ilovada ochiladi.
 */
class MainActivity : ComponentActivity() {

    private lateinit var web: WebView
    private lateinit var progress: ProgressBar
    private lateinit var offline: LinearLayout
    private val baseUri: Uri by lazy { Uri.parse(BuildConfig.BASE_URL) }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        web = findViewById(R.id.web)
        progress = findViewById(R.id.progress)
        offline = findViewById(R.id.offline)
        findViewById<Button>(R.id.retry).setOnClickListener { reload() }

        with(web.settings) {
            javaScriptEnabled = true
            domStorageEnabled = true            // sessiya tokeni localStorage'da
            allowFileAccess = false
            allowContentAccess = false
            setSupportMultipleWindows(false)
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            cacheMode = WebSettings.LOAD_DEFAULT
            userAgentString = "$userAgentString MMebelApp/${BuildConfig.VERSION_NAME}"
        }
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, false)
        web.addJavascriptInterface(AppBridge(), "MMebelApp")
        web.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView, newProgress: Int) {
                progress.visibility = if (newProgress < 100) View.VISIBLE else View.GONE
            }
        }
        web.webViewClient = PanelClient()

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                // Avval panelga beramiz: ochiq oyna bo'lsa yopadi yoki bosh sahifaga qaytadi
                web.evaluateJavascript("window.mmebelBack ? window.mmebelBack() : false") { handled ->
                    if (handled != "true") finish()
                }
            }
        })

        if (savedInstanceState != null) web.restoreState(savedInstanceState) else web.loadUrl(BuildConfig.BASE_URL)
    }

    private fun reload() {
        offline.visibility = View.GONE
        web.visibility = View.VISIBLE
        web.loadUrl(BuildConfig.BASE_URL)
    }

    private fun isOwn(uri: Uri) = uri.scheme == "https" && uri.host == baseUri.host

    private fun openExternal(url: String) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        } catch (e: ActivityNotFoundException) {
            Toast.makeText(this, R.string.no_app, Toast.LENGTH_LONG).show()
        }
    }

    private inner class PanelClient : WebViewClient() {
        override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
            val uri = request.url
            if (isOwn(uri)) return false
            openExternal(uri.toString())
            return true
        }

        override fun onPageStarted(view: WebView, url: String?, favicon: Bitmap?) {
            progress.visibility = View.VISIBLE
        }

        override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
            if (request.isForMainFrame) {
                web.visibility = View.INVISIBLE
                offline.visibility = View.VISIBLE
                progress.visibility = View.GONE
            }
        }
    }

    /** Panel JS kodi chaqiradigan ko'prik: window.MMebelApp.openExternal(url) */
    inner class AppBridge {
        @JavascriptInterface
        fun openExternal(url: String) {
            val uri = Uri.parse(url)
            // Faqat Telegram havolalariga ruxsat — boshqa sxemalar ochilmaydi
            if (uri.scheme == "https" && uri.host == "t.me") runOnUiThread { openExternal(url) }
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        web.saveState(outState)
    }

    override fun onResume() {
        super.onResume()
        web.onResume()
    }

    override fun onPause() {
        web.onPause()
        super.onPause()
    }

    override fun onDestroy() {
        web.destroy()
        super.onDestroy()
    }
}
