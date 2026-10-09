/* Telegram Mini App kutubxonasini faqat Telegram ichida yuklaymiz.
   Android ilovada u havolalarni ushlab qolib, Telegram'ni ochishga xalaqit beradi. */
(function () {
  "use strict";
  function start() {
    var s = document.createElement("script");
    s.src = "/panel/static/app.js?v=5";
    document.body.appendChild(s);
  }
  var inTelegram = /tgWebApp/.test(location.hash + location.search) || !!window.TelegramWebviewProxy ||
    (window.parent && window.parent !== window);
  if (!inTelegram || /MMebelApp/.test(navigator.userAgent)) { start(); return; }
  var sdk = document.createElement("script");
  sdk.src = "https://telegram.org/js/telegram-web-app.js";
  sdk.onload = start;
  sdk.onerror = start;
  document.head.appendChild(sdk);
})();
