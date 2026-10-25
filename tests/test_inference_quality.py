from aura.inference import _looks_like_usable_text

def test_rejects_short_gibberish_and_debug_output():
    messages = [{"role": "user", "content": "\uC548\uB155"}]
    assert not _looks_like_usable_text("\uACF4 \uACAC", messages)
    assert not _looks_like_usable_text("data[381]urcence: eale_espex", messages)
    assert not _looks_like_usable_text("\uFFFD\uFFFD\uFFFD\uFFFD", messages)

def test_accepts_korean_sentence():
    messages = [{"role": "user", "content": "\uC548\uB155"}]
    assert _looks_like_usable_text("\uC548\uB155\uD558\uC138\uC694. \uBB34\uC5C7\uC744 \uB3C4\uC640\uB4DC\uB9B4\uAE4C\uC694?", messages)
