from prepare_dialogues import extract_pairs, parse_data


def test_extracts_instruction_response_pair():
    item = {"instruction": "\uc548\ub155", "output": "\uc548\ub155\ud558\uc138\uc694!"}
    examples = list(extract_pairs(item))
    assert len(examples) == 1
    assert examples[0] == "User: \uc548\ub155\nAura: \uc548\ub155\ud558\uc138\uc694!\n"


def test_extracts_messages_format():
    item = {
        "messages": [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello"}]
    }
    assert list(extract_pairs(item)) == ["User: Hi\nAura: Hello\n"]


def test_jsonl_pair_extraction():
    raw = b'{"instruction":"hi","output":"hello"}\n'
    assert list(parse_data(raw, "sample.jsonl")) == ["User: hi\nAura: hello\n"]
