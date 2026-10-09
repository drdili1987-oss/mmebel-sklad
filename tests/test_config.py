from mmebel.config import webhook_secret


def test_webhook_secret_is_always_telegram_safe():
    import re
    ok = re.compile(r"[A-Za-z0-9_-]{1,256}")
    assert webhook_secret("abc_DEF-123", "t") == "abc_DEF-123"
    for raw in ("a+b/c==", "", "пароль", "x" * 300):
        s = webhook_secret(raw, "1:tok")
        assert ok.fullmatch(s)
    assert webhook_secret("a+b", "t") != webhook_secret("a+c", "t")
