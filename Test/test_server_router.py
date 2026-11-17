
import json
import pytest
from Code.Server.server_router import ServerRouter


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


def test_reply_to_id_resolves_original_message():
    router = ServerRouter()

    # 1. Gửi tin nhắn gốc
    r1 = router.feed_data(b'{"type":"msg","content":"Tin goc"}\n')
    assert r1[0]["ok"] is True
    original_id = r1[0]["message"]["msg_id"]
    assert original_id == 1

    # 2. Gửi tin nhắn reply theo reply_to_id
    reply_payload = f'{{"type":"reply","reply_to_id":{original_id},"content":"Tin phan hoi"}}\n'.encode("utf-8")
    r2 = router.feed_data(reply_payload)
    assert r2[0]["ok"] is True
    reply_msg = r2[0]["message"]
    assert reply_msg["msg_id"] == 2
    assert "reply_to" in reply_msg
    assert reply_msg["reply_to"]["content"] == "Tin goc"
    assert reply_msg["reply_to"]["msg_id"] == 1


def test_reply_to_msg_id_supported():
    router = ServerRouter()

    # Gửi tin nhắn gốc
    r1 = router.feed_data(b'{"type":"msg","content":"Original"}\n')
    assert r1[0]["ok"] is True

    # Gửi tin nhắn reply dùng tên trường reply_to_msg_id
    r2 = router.feed_data(b'{"type":"reply","reply_to_msg_id":1,"content":"Response"}\n')
    assert r2[0]["ok"] is True
    assert r2[0]["message"]["reply_to"]["content"] == "Original"


def test_reply_to_id_not_found_returns_error():
    router = ServerRouter()

    # Gửi reply cho một msg_id không tồn tại
    r = router.feed_data(b'{"type":"reply","reply_to_id":999,"content":"Lost"}\n')
    assert r[0]["ok"] is False
    assert r[0]["error"]["error"]["code"] == "REPLY_NOT_FOUND"


def test_invalid_reply_to_id_type_rejected():
    router = ServerRouter()

    # reply_to_id không phải số nguyên
    r = router.feed_data(b'{"type":"reply","reply_to_id":"abc","content":"Bad ID"}\n')
    assert r[0]["ok"] is False
    assert r[0]["error"]["error"]["code"] == "INVALID_REPLY_TO_ID"

