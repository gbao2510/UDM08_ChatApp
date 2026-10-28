
import json

from server_router import ServerRouter


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
