import json
import pytest
import sys
sys.path.insert(0, '') 

from Code.Server.server_router import ServerRouter

def test_parse_normal_message():
    router = ServerRouter()
    raw = json.dumps({
        "sender": "Ban",
        "content": "Xin chao"
    })

    result = router.parse_message(raw)

    assert result["sender"] == "Ban"
    assert result["content"] == "Xin chao"
    assert result["msg_id"] == 1


def test_msg_id_increases_sequentially():
    router = ServerRouter()

    msg1 = router.parse_message(
        '{"sender": "A", "content": "Hello"}'
    )
    msg2 = router.parse_message(
        '{"sender": "B", "content": "Hi"}'
    )
    msg3 = router.parse_message(
        '{"sender": "C", "content": "Test"}'
    )

    assert msg1["msg_id"] < msg2["msg_id"]
    assert msg2["msg_id"] < msg3["msg_id"]
