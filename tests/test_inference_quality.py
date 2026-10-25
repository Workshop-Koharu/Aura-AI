from aura.inference import _looks_like_usable_text


def test_rejects_short_gibberish_and_debug_output():
    messages = [{"role": "user", "content": "\uc548\ub155"}]
    assert not _looks_like_usable_text("\uacf4 \uacac", messages)
    assert not _looks_like_usable_text("data[381]urcence: eale_espex", messages)
    assert not _looks_like_usable_text("\ufffd\ufffd\ufffd\ufffd", messages)


def test_accepts_korean_sentence():
    messages = [{"role": "user", "content": "\uc548\ub155"}]
    assert _looks_like_usable_text(
        "\uc548\ub155\ud558\uc138\uc694. \ubb34\uc5c7\uc744 \ub3c4\uc640\ub4dc\ub9b4\uae4c\uc694?",
        messages,
    )


def test_greetings_are_reliable_without_loading_the_experimental_model():
    from aura.inference import generate_reply

    assert (
        generate_reply([{"role": "user", "content": "\uc548\ub155!"}])
        == "\uc548\ub155! \ub098\ub294 Aura AI\uc57c. \ubb34\uc5c7\uc744 \ub3c4\uc640\uc904\uae4c?"
    )
    assert (
        generate_reply([{"role": "user", "content": "Hello"}])
        == "Hello! I'm Aura AI. What can I help you with?"
    )
