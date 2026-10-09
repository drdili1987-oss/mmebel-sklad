# JavaScript ko'prigi metodlari (WebView) nomlari o'zgarmasligi kerak
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
