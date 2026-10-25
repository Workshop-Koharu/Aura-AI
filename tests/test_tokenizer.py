from aura.tokenizer import ByteTokenizer


def test_korean_utf8_roundtrip():
    tokenizer = ByteTokenizer()
    text = "??, Aura AI! ?? ????."
    assert tokenizer.decode(tokenizer.encode(text)) == text


def test_special_tokens_are_outside_utf8_bytes():
    tokenizer = ByteTokenizer()
    ids = tokenizer.encode("??", add_bos=True, add_eos=True)
    assert ids[0] == tokenizer.BOS_ID
    assert ids[-1] == tokenizer.EOS_ID
    assert all(0 <= token < 256 for token in ids[1:-1])
