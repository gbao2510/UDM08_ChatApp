import json
import pytest
from Code.Server.server_router import ServerRouter, encode_message


def test_parse_normal_message():
    router = ServerRouter()

    result = router.feed_data(
        b'{"type":"chat","content":"Hello"}\n'
    )

    assert len(result) == 1
    assert result[0]["ok"] is True
    assert result[0]["message"]["content"] == "Hello"
    assert result[0]["message"]["msg_id"] == 1


def test_tcp_packet_split():
    router = ServerRouter()

    first = router.feed_data(b'{"content":"Hel')
    second = router.feed_data(b'lo"}\n')

    assert first == []
    assert len(second) == 1
    assert second[0]["message"]["content"] == "Hello"


def test_multiple_messages_in_one_packet():
    router = ServerRouter()

    result = router.feed_data(
        b'{"content":"One"}\n{"content":"Two"}\n'
    )

    assert len(result) == 2
    assert result[0]["message"]["msg_id"] == 1
    assert result[1]["message"]["msg_id"] == 2


def test_invalid_json_returns_clear_error():
    router = ServerRouter()

    result = router.feed_data(b'{"content":}\n')

    assert result[0]["ok"] is False
    assert result[0]["error"]["error"]["code"] == "INVALID_JSON"


def test_invalid_json_does_not_consume_msg_id():
    router = ServerRouter()

    result = router.feed_data(
        b'{"content":"First"}\n'
        b'{"content":}\n'
        b'{"content":"Second"}\n'
    )

    assert result[0]["message"]["msg_id"] == 1
    assert result[1]["ok"] is False
    assert result[2]["message"]["msg_id"] == 2


def test_json_array_is_rejected():
    router = ServerRouter()

    result = router.feed_data(b'["Hello"]\n')

    assert result[0]["ok"] is False
    assert result[0]["error"]["error"]["code"] == (
        "JSON_OBJECT_REQUIRED"
    )


def test_invalid_utf8_is_rejected():
    router = ServerRouter()

    result = router.feed_data(b'\xff\n')

    assert result[0]["ok"] is False
    assert result[0]["error"]["error"]["code"] == (
        "INVALID_ENCODING"
    )


def test_error_response_is_valid_json():
    router = ServerRouter()
    result = router.feed_data(b'{"content":}\n')[0]

    response = result["error"]
    encoded = (
        json.dumps(response, ensure_ascii=False) + "\n"
    ).encode("utf-8")

    decoded = json.loads(encoded.decode("utf-8"))

    assert decoded["type"] == "error"
    assert decoded["error"]["code"] == "INVALID_JSON"
    assert encoded.endswith(b"\n")


# ---------------------------------------------------------------
# UTF-8 / EMOJI
# ---------------------------------------------------------------

EMOJI_TEXT = "Xin chào 😀🔥 👨‍👩‍👧 🇻🇳"


def utf8_line(content):
    """Tạo 1 gói tin JSON UTF-8 (giữ nguyên emoji, không escape) kết thúc bằng newline."""
    return (
        json.dumps({"content": content}, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def test_emoji_message_is_parsed():
    router = ServerRouter()

    result = router.feed_data(utf8_line(EMOJI_TEXT))

    assert len(result) == 1
    assert result[0]["ok"] is True
    assert result[0]["message"]["content"] == EMOJI_TEXT
    assert result[0]["message"]["msg_id"] == 1


def test_emoji_split_in_the_middle_of_utf8_bytes():
    router = ServerRouter()
    raw = utf8_line("Hi 😀")
    cut = raw.index("😀".encode("utf-8")) + 2  # cắt giữa 4 byte của emoji

    first = router.feed_data(raw[:cut])
    second = router.feed_data(raw[cut:])

    assert first == []
    assert len(second) == 1
    assert second[0]["message"]["content"] == "Hi 😀"


@pytest.mark.parametrize("cut", range(1, len(utf8_line(EMOJI_TEXT))))
def test_emoji_message_split_at_every_byte_position(cut):
    router = ServerRouter()
    raw = utf8_line(EMOJI_TEXT)

    results = router.feed_data(raw[:cut]) + router.feed_data(raw[cut:])

    assert len(results) == 1
    assert results[0]["ok"] is True
    assert results[0]["message"]["content"] == EMOJI_TEXT


def test_emoji_fed_one_byte_at_a_time():
    router = ServerRouter()
    results = []

    for byte in utf8_line(EMOJI_TEXT):
        results.extend(router.feed_data(bytes([byte])))

    assert len(results) == 1
    assert results[0]["message"]["content"] == EMOJI_TEXT


def test_emoji_in_json_key_is_supported():
    router = ServerRouter()

    result = router.feed_data("{\"😀\":1}\n".encode("utf-8"))

    assert result[0]["ok"] is True
    assert result[0]["message"]["😀"] == 1


def test_valid_surrogate_pair_escape_becomes_emoji():
    router = ServerRouter()

    result = router.feed_data(b'{"content":"\\ud83d\\ude00"}\n')

    assert result[0]["ok"] is True
    assert result[0]["message"]["content"] == "😀"


def test_lone_surrogate_is_rejected():
    router = ServerRouter()

    result = router.feed_data(b'{"content":"\\ud83d"}\n')

    assert result[0]["ok"] is False
    assert result[0]["error"]["error"]["code"] == "INVALID_UNICODE"


def test_lone_surrogate_in_key_is_rejected():
    router = ServerRouter()

    result = router.feed_data(b'{"\\ude00":1}\n')

    assert result[0]["ok"] is False
    assert result[0]["error"]["error"]["code"] == "INVALID_UNICODE"


def test_lone_surrogate_does_not_consume_msg_id():
    router = ServerRouter()

    result = router.feed_data(
        utf8_line("😀")
        + b'{"content":"\\ud83d"}\n'
        + utf8_line("🔥")
    )

    assert result[0]["message"]["msg_id"] == 1
    assert result[1]["ok"] is False
    assert result[2]["message"]["msg_id"] == 2


def test_truncated_emoji_bytes_are_rejected():
    router = ServerRouter()

    # 3 trong 4 byte của 😀 rồi gặp newline -> UTF-8 không hợp lệ
    result = router.feed_data(b'{"content":"\xf0\x9f\x98"}\n')

    assert result[0]["ok"] is False
    assert result[0]["error"]["error"]["code"] == "INVALID_ENCODING"


def test_cesu8_encoded_surrogates_are_rejected():
    router = ServerRouter()

    # 😀 mã hóa sai kiểu CESU-8 (2 surrogate, mỗi cái 3 byte)
    result = router.feed_data(
        b'{"content":"\xed\xa0\xbd\xed\xb8\x80"}\n'
    )

    assert result[0]["ok"] is False
    assert result[0]["error"]["error"]["code"] == "INVALID_ENCODING"


def test_utf8_bom_is_ignored():
    router = ServerRouter()

    result = router.feed_data(b"\xef\xbb\xbf" + utf8_line("😀"))

    assert result[0]["ok"] is True
    assert result[0]["message"]["content"] == "😀"


def test_encode_message_keeps_emoji_as_real_utf8():
    encoded = encode_message({"type": "chat", "content": EMOJI_TEXT})

    assert encoded.endswith(b"\n")
    assert "😀".encode("utf-8") in encoded
    assert b"\\ud83d" not in encoded
    assert json.loads(encoded.decode("utf-8"))["content"] == EMOJI_TEXT


def test_encode_message_does_not_crash_on_lone_surrogate():
    encoded = encode_message({"content": "\ud83d"})

    assert encoded.endswith(b"\n")
    encoded.decode("ascii")  # dự phòng phải là ASCII thuần
    assert json.loads(encoded.decode("ascii"))["content"] == "\ud83d"


def test_emoji_roundtrip_router_to_encode_message():
    router = ServerRouter()
    message = router.feed_data(utf8_line(EMOJI_TEXT))[0]["message"]

    echoed = json.loads(encode_message(message).decode("utf-8"))

    assert echoed["content"] == EMOJI_TEXT
    assert echoed["msg_id"] == 1


def test_oversized_frame_is_reported_once_then_recovers():
    router = ServerRouter(max_frame_size=100)

    first = router.feed_data(b'{"content":"' + b"a" * 150)  # chưa có newline
    middle = router.feed_data(b"b" * 50)                      # phần đuôi bị bỏ
    last = router.feed_data(b'"}\n' + utf8_line("😀"))

    assert len(first) == 1
    assert first[0]["error"]["error"]["code"] == "MESSAGE_TOO_LARGE"
    assert middle == []
    assert len(last) == 1  # phần đuôi không bị hiểu nhầm là gói JSON mới
    assert last[0]["message"]["content"] == "😀"