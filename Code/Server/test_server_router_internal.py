import contextlib
import json
import socket
import struct
import threading
import time

import pytest
from Code.Server.server_router import (
    MessageIdGenerator,
    ReconnectingClient,
    ServerCore,
    ServerRouter,
    close_socket_quietly,
    compute_backoff,
    enable_tcp_keepalive,
    encode_message,
)


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


# ---------------------------------------------------------------
# REPLY (tìm nội dung gốc dựa trên reply_to_id)
# ---------------------------------------------------------------

def json_line(obj):
    return (
        json.dumps(obj, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def error_code(result):
    return result["error"]["error"]["code"]


def test_reply_finds_original_content():
    router = ServerRouter()

    router.feed_data(json_line({"type": "chat", "content": "Hello"}))
    result = router.feed_data(
        json_line({"type": "chat", "content": "Hi", "reply_to_id": 1})
    )

    assert len(result) == 1
    assert result[0]["ok"] is True
    message = result[0]["message"]
    assert message["msg_id"] == 2
    assert message["reply_to_id"] == 1
    assert message["reply_to"]["msg_id"] == 1
    assert message["reply_to"]["content"] == "Hello"


def test_reply_to_unknown_id_is_rejected():
    router = ServerRouter()

    result = router.feed_data(
        json_line({"content": "x", "reply_to_id": 99})
    )

    assert result[0]["ok"] is False
    assert error_code(result[0]) == "REPLY_NOT_FOUND"


def test_reply_to_unknown_id_does_not_consume_msg_id():
    router = ServerRouter()

    result = router.feed_data(
        json_line({"content": "First"})
        + json_line({"content": "x", "reply_to_id": 99})
        + json_line({"content": "Second"})
    )

    assert result[0]["message"]["msg_id"] == 1
    assert result[1]["ok"] is False
    assert result[2]["message"]["msg_id"] == 2


@pytest.mark.parametrize(
    "bad_id", ['"1"', "1.5", "true", "false", "null", "[1]", "{}"]
)
def test_reply_to_id_must_be_integer(bad_id):
    router = ServerRouter()
    router.feed_data(json_line({"content": "Hello"}))

    result = router.feed_data(
        ('{"content":"x","reply_to_id":%s}\n' % bad_id).encode("utf-8")
    )

    assert result[0]["ok"] is False
    assert error_code(result[0]) == "INVALID_REPLY_TO_ID"


def test_reply_in_same_packet_as_original():
    router = ServerRouter()

    result = router.feed_data(
        json_line({"content": "Goc"})
        + json_line({"content": "Tra loi", "reply_to_id": 1})
    )

    assert result[1]["ok"] is True
    assert result[1]["message"]["reply_to"]["content"] == "Goc"


def test_reply_to_emoji_original():
    router = ServerRouter()

    router.feed_data(utf8_line(EMOJI_TEXT))
    result = router.feed_data(
        json_line({"content": "ok", "reply_to_id": 1})
    )

    assert result[0]["ok"] is True
    assert result[0]["message"]["reply_to"]["content"] == EMOJI_TEXT


def test_reply_split_across_tcp_packets():
    router = ServerRouter()
    router.feed_data(json_line({"content": "Hello"}))
    raw = json_line({"content": "Hi", "reply_to_id": 1})

    first = router.feed_data(raw[:10])
    second = router.feed_data(raw[10:])

    assert first == []
    assert second[0]["message"]["reply_to"]["content"] == "Hello"


def test_reply_to_failed_message_is_not_found():
    router = ServerRouter()

    router.feed_data(b'{"content":}\n')  # lỗi nên không có msg_id 1
    result = router.feed_data(
        json_line({"content": "x", "reply_to_id": 1})
    )

    assert result[0]["ok"] is False
    assert error_code(result[0]) == "REPLY_NOT_FOUND"


def test_reply_with_lone_surrogate_is_rejected_by_unicode_check():
    router = ServerRouter()
    router.feed_data(json_line({"content": "Hello"}))

    result = router.feed_data(
        b'{"content":"\\ud83d","reply_to_id":1}\n'
    )

    assert result[0]["ok"] is False
    assert error_code(result[0]) == "INVALID_UNICODE"


def test_client_cannot_choose_msg_id_in_reply():
    router = ServerRouter()
    router.feed_data(json_line({"content": "Hello"}))

    result = router.feed_data(
        json_line({"content": "Hi", "reply_to_id": 1, "msg_id": 999})
    )

    assert result[0]["message"]["msg_id"] == 2


def test_reply_chain_resolves_each_level():
    router = ServerRouter()

    router.feed_data(json_line({"content": "A"}))
    router.feed_data(json_line({"content": "B", "reply_to_id": 1}))
    result = router.feed_data(
        json_line({"content": "C", "reply_to_id": 2})
    )

    assert result[0]["message"]["msg_id"] == 3
    assert result[0]["message"]["reply_to"]["msg_id"] == 2
    assert result[0]["message"]["reply_to"]["content"] == "B"


def test_reply_across_clients_with_shared_id_generator():
    shared = MessageIdGenerator()
    alice = ServerRouter(id_generator=shared)
    bob = ServerRouter(id_generator=shared)

    alice.feed_data(json_line({"content": "Tu Alice"}))
    result = bob.feed_data(
        json_line({"content": "Tu Bob", "reply_to_id": 1})
    )

    assert result[0]["ok"] is True
    assert result[0]["message"]["msg_id"] == 2
    assert result[0]["message"]["reply_to"]["content"] == "Tu Alice"


def test_reply_not_found_with_separate_id_generators():
    alice = ServerRouter()
    bob = ServerRouter()

    alice.feed_data(json_line({"content": "Tu Alice"}))
    result = bob.feed_data(
        json_line({"content": "Tu Bob", "reply_to_id": 1})
    )

    assert error_code(result[0]) == "REPLY_NOT_FOUND"


def test_reply_message_is_encodable():
    router = ServerRouter()
    router.feed_data(utf8_line(EMOJI_TEXT))
    message = router.feed_data(
        json_line({"content": "ok", "reply_to_id": 1})
    )[0]["message"]

    echoed = json.loads(encode_message(message).decode("utf-8"))

    assert echoed["reply_to"]["content"] == EMOJI_TEXT
    assert echoed["msg_id"] == 2


def test_message_id_generator_register_and_lookup():
    gen = MessageIdGenerator()
    message = {"content": "A"}

    msg_id = gen.register(message)

    assert msg_id == 1
    assert message["msg_id"] == 1
    assert gen.get_message(1)["content"] == "A"
    assert gen.get_message(2) is None



# ---------------------------------------------------------------
# MẤT KẾT NỐI: ROUTER, HEARTBEAT, BACKOFF, TIỆN ÍCH SOCKET
# ---------------------------------------------------------------

def test_router_reset_discards_partial_frame():
    router = ServerRouter()

    router.feed_data(b'{"content":"dang do')
    assert router.pending_bytes > 0

    router.reset()

    assert router.pending_bytes == 0
    # Kết nối mới không bị dính nửa gói cũ
    result = router.feed_data(json_line({"content": "Moi"}))
    assert len(result) == 1
    assert result[0]["message"]["content"] == "Moi"


def test_router_reset_clears_discarding_state():
    router = ServerRouter(max_frame_size=50)
    router.feed_data(b"a" * 80)  # quá lớn, vào trạng thái bỏ phần đuôi
    assert router.discarding is True

    router.reset()

    assert router.discarding is False
    result = router.feed_data(json_line({"content": "ok"}))
    assert result[0]["ok"] is True


def test_heartbeat_does_not_consume_msg_id():
    router = ServerRouter()

    result = router.feed_data(
        json_line({"content": "A"})
        + json_line({"type": "ping"})
        + json_line({"type": "pong"})
        + json_line({"content": "B"})
    )

    assert [r["ok"] for r in result] == [True, True, True, True]
    assert result[0]["message"]["msg_id"] == 1
    assert "msg_id" not in result[1]["message"]
    assert "msg_id" not in result[2]["message"]
    assert result[3]["message"]["msg_id"] == 2


def test_heartbeat_is_not_stored_in_history():
    router = ServerRouter()
    router.feed_data(json_line({"type": "ping"}))

    assert router.id_generator.get_message(1) is None


def test_compute_backoff_grows_exponentially_and_caps():
    delays = [
        compute_backoff(n, initial=1, factor=2, maximum=10, jitter=0)
        for n in range(1, 7)
    ]

    assert delays == [1, 2, 4, 8, 10, 10]


def test_compute_backoff_survives_huge_attempt_numbers():
    assert compute_backoff(10_000, initial=1, factor=2, maximum=30, jitter=0) == 30


def test_compute_backoff_jitter_stays_in_bounds():
    for _ in range(200):
        delay = compute_backoff(3, initial=1, factor=2, maximum=30, jitter=0.2)
        assert 4 * 0.8 <= delay <= 4 * 1.2


def test_close_socket_quietly_accepts_none_and_is_idempotent():
    close_socket_quietly(None)

    a, b = socket.socketpair()
    close_socket_quietly(a)
    close_socket_quietly(a)  # đóng lần 2 không ném lỗi
    close_socket_quietly(b)

    assert a.fileno() == -1
    assert b.fileno() == -1


def test_enable_tcp_keepalive_sets_keepalive_flag():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        assert enable_tcp_keepalive(sock) in (True, False)
        assert sock.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE) != 0
    finally:
        sock.close()


# ---------------------------------------------------------------
# HẠ TẦNG TEST VỚI SOCKET THẬT (loopback)
# ---------------------------------------------------------------

def wait_until(predicate, timeout=3.0, interval=0.02):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


@contextlib.contextmanager
def running_server(port=0, **kwargs):
    """Chạy ServerCore thật trên 127.0.0.1 (port=0: hệ điều hành tự chọn cổng trống)."""
    kwargs.setdefault("log_file", None)
    server = ServerCore(host="127.0.0.1", port=port, **kwargs)
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    assert server.ready.wait(3), "Server khong khoi dong duoc"
    try:
        yield server
    finally:
        server.stop()
        thread.join(5)
        assert not thread.is_alive(), "Luong server van con song sau stop()"


def free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class RawClient:
    """Client thô để test Server: tự gửi/đọc từng dòng JSON."""

    def __init__(self, server, username=None):
        self.sock = socket.create_connection(("127.0.0.1", server.port), timeout=3)
        self.buffer = b""
        self.eof = False
        if username is not None:
            self.send({"type": "login", "username": username})
            ack = self.read_type("login_ack")
            assert ack["status"] == "success", ack

    def send(self, obj):
        self.sock.sendall(json_line(obj))

    def read(self, timeout=3.0):
        deadline = time.monotonic() + timeout
        while True:
            if b"\n" in self.buffer:
                line, self.buffer = self.buffer.split(b"\n", 1)
                if line.strip():
                    return json.loads(line.decode("utf-8"))
                continue
            remaining = deadline - time.monotonic()
            if remaining <= 0 or self.eof:
                return None
            self.sock.settimeout(remaining)
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                return None
            except ConnectionError:
                self.eof = True
                return None
            if not chunk:
                self.eof = True
                return None
            self.buffer += chunk

    def read_type(self, packet_type, timeout=3.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            packet = self.read(max(deadline - time.monotonic(), 0.01))
            if packet is None:
                if self.eof:
                    return None
                continue
            if packet.get("type") == packet_type:
                return packet
        return None

    def read_to_eof(self, timeout=3.0):
        deadline = time.monotonic() + timeout
        packets = []
        while not self.eof and time.monotonic() < deadline:
            packet = self.read(max(deadline - time.monotonic(), 0.01))
            if packet is not None:
                packets.append(packet)
        return packets, self.eof

    def close(self, abrupt=False):
        if abrupt:
            # SO_LINGER (on, 0s): close() gửi RST thay vì FIN, giống app bị kill/rút mạng
            self.sock.setsockopt(
                socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0)
            )
        self.sock.close()


def server_is_clean(server):
    return (
        not server.clients
        and not server.send_locks
        and not any(t.is_alive() for t in list(server.client_threads))
    )


# ---------------------------------------------------------------
# SERVER: CLIENT TẮT ĐỘT NGỘT / MẤT KẾT NỐI
# ---------------------------------------------------------------

def test_server_cleans_up_after_normal_close():
    with running_server() as server:
        client = RawClient(server, "alice")
        assert server.get_online_users() == ["alice"]

        client.close()

        assert wait_until(lambda: server_is_clean(server))


def test_server_cleans_up_after_abrupt_close_rst():
    with running_server() as server:
        client = RawClient(server, "alice")

        client.close(abrupt=True)

        assert wait_until(lambda: server_is_clean(server))
        assert server.get_online_users() == []


def test_server_cleans_up_client_that_never_logged_in():
    with running_server() as server:
        client = RawClient(server)
        assert wait_until(lambda: len(server.send_locks) == 1)

        client.close(abrupt=True)

        assert wait_until(lambda: server_is_clean(server))


def test_abrupt_disconnect_notifies_remaining_clients():
    with running_server() as server:
        alice = RawClient(server, "alice")
        bob = RawClient(server, "bob")

        alice.close(abrupt=True)

        leave = bob.read_type("user_leave")
        assert leave is not None and leave["username"] == "alice"
        user_list = bob.read_type("user_list")
        assert user_list["online_users"] == ["bob"]
        assert wait_until(lambda: len(server.send_locks) == 1)
        bob.close()


def test_disconnect_client_is_idempotent_and_notifies_once():
    with running_server() as server:
        alice = RawClient(server, "alice")
        bob = RawClient(server, "bob")
        with server.lock:
            alice_socket = next(
                s for s, name in server.clients.items() if name == "alice"
            )

        first = server.disconnect_client(alice_socket, "test")
        second = server.disconnect_client(alice_socket, "test")

        assert first is True
        assert second is False
        assert bob.read_type("user_leave")["username"] == "alice"
        assert bob.read_type("user_leave", timeout=0.3) is None  # không gửi lặp
        assert wait_until(lambda: server.get_online_users() == ["bob"])
        alice.close()
        bob.close()


def test_disconnect_client_closes_untracked_socket():
    server = ServerCore(log_file=None)
    a, b = socket.socketpair()

    assert server.disconnect_client(a) is False

    assert a.fileno() == -1
    b.close()


def test_register_client_rejects_already_cleaned_socket():
    server = ServerCore(log_file=None)
    a, b = socket.socketpair()
    try:
        with pytest.raises(ConnectionError):
            server.register_client(a, "ghost")
        assert server.clients == {}
    finally:
        a.close()
        b.close()


def test_failed_send_cleans_up_dead_client():
    server = ServerCore(log_file=None)
    a, b = socket.socketpair()
    server.clients[a] = "alice"
    server.send_locks[a] = threading.Lock()
    b.close()  # đầu bên kia chết

    results = []
    for _ in range(10):  # Windows có thể cần vài lần gửi mới thấy lỗi
        results.append(server.send_packet(a, {"type": "ping"}))
        if not results[-1]:
            break
        time.sleep(0.05)

    assert results[-1] is False
    assert a not in server.clients
    assert a not in server.send_locks
    assert a.fileno() == -1


def test_encode_error_does_not_disconnect_client():
    server = ServerCore(log_file=None)
    a, b = socket.socketpair()
    server.clients[a] = "alice"
    server.send_locks[a] = threading.Lock()
    try:
        assert server.send_packet(a, {"bad": object()}) is False  # không JSON hóa được
        assert a in server.clients  # lỗi dữ liệu không được ngắt Client
        assert a.fileno() != -1
    finally:
        a.close()
        b.close()


def test_ping_is_answered_and_consumes_no_msg_id():
    with running_server() as server:
        alice = RawClient(server, "alice")
        bob = RawClient(server, "bob")

        alice.send({"type": "message", "content": "truoc ping"})
        before = bob.read_type("message")["msg_id"]

        alice.send({"type": "ping"})
        assert alice.read_type("pong") is not None

        alice.send({"type": "message", "content": "sau ping"})
        after = bob.read_type("message")["msg_id"]

        assert after == before + 1  # ping/pong không ăn msg_id
        alice.close()
        bob.close()


# ---------------------------------------------------------------
# SERVER: KẾT NỐI "NỬA CHẾT" (không có FIN/RST) -> HEARTBEAT
# ---------------------------------------------------------------

def test_silent_client_is_dropped_by_idle_timeout():
    with running_server(heartbeat_interval=0.1, idle_timeout=0.4) as server:
        ghost = RawClient(server, "ghost")  # đăng nhập xong rồi im lặng, không trả lời ping

        packets, eof = ghost.read_to_eof(timeout=3)

        assert eof is True
        assert any(p.get("type") == "ping" for p in packets)
        assert wait_until(lambda: server_is_clean(server))


def test_client_answering_pings_stays_connected():
    with running_server(heartbeat_interval=0.1, idle_timeout=0.4) as server:
        client = RawClient(server, "alive")
        pings = 0
        deadline = time.monotonic() + 1.2

        while time.monotonic() < deadline:
            packet = client.read(timeout=0.2)
            if packet and packet.get("type") == "ping":
                pings += 1
                client.send({"type": "pong"})

        assert pings >= 2
        assert server.get_online_users() == ["alive"]
        client.close()


# ---------------------------------------------------------------
# SERVER: GIẢI PHÓNG TÀI NGUYÊN, accept() BỀN BỈ
# ---------------------------------------------------------------

def test_stop_releases_all_sockets_and_threads():
    with running_server() as server:
        clients = [RawClient(server, f"user{i}") for i in range(3)]
        idle_client = RawClient(server)  # chưa đăng nhập
        # connect() xong chưa chắc Server đã accept(): chờ nó đăng ký đủ 4 luồng
        assert wait_until(lambda: len(server.client_threads) == 4)
        threads = list(server.client_threads)

        server.stop()

        assert server.clients == {}
        assert server.send_locks == {}
        assert server.server_socket is None
        assert all(not t.is_alive() for t in threads)
        for client in clients + [idle_client]:
            _, eof = client.read_to_eof(timeout=2)
            assert eof is True


def test_stop_is_idempotent():
    with running_server() as server:
        RawClient(server, "alice")

        server.stop()
        server.stop()

        assert server_is_clean(server)


def test_port_is_released_after_stop():
    with running_server() as first:
        port = first.port
        RawClient(first, "alice")
    # Khởi động lại đúng cổng cũ: chứng tỏ socket lắng nghe đã được trả lại
    with running_server(port=port) as second:
        client = RawClient(second, "alice")
        assert second.get_online_users() == ["alice"]
        client.close()


def test_accept_loop_survives_transient_accept_error():
    class FlakyListener:
        """Bọc socket lắng nghe thật: lần accept() đầu tiên ném lỗi tạm thời."""

        def __init__(self, real):
            self.real = real
            self.failures_left = 1
            self.failed = threading.Event()

        def accept(self):
            if self.failures_left:
                self.failures_left -= 1
                self.failed.set()
                raise ConnectionAbortedError("simulated")
            return self.real.accept()

        def __getattr__(self, name):
            return getattr(self.real, name)

    with running_server() as server:
        flaky = FlakyListener(server.server_socket)
        server.server_socket = flaky

        assert flaky.failed.wait(5)
        client = RawClient(server, "alice")  # Server vẫn phục vụ sau lỗi

        assert server.get_online_users() == ["alice"]
        client.close()


# ---------------------------------------------------------------
# CLIENT TỰ ĐỘNG KẾT NỐI LẠI (ReconnectingClient)
# ---------------------------------------------------------------

def make_client(port, **kwargs):
    defaults = dict(
        initial_delay=0.05, max_delay=0.2, jitter=0,
        heartbeat_interval=0.2, idle_timeout=1.0, connect_timeout=1.0,
    )
    defaults.update(kwargs)
    return ReconnectingClient("127.0.0.1", port, **defaults)


@contextlib.contextmanager
def fake_server(on_connect=None):
    """Server giả đơn giản: nhận kết nối rồi để mặc (hoặc chạy on_connect)."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(5)
    listener.settimeout(0.2)
    connections = []
    stop = threading.Event()

    def loop():
        while not stop.is_set():
            try:
                conn, _ = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            connections.append(conn)
            if on_connect:
                on_connect(conn)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    try:
        yield listener.getsockname()[1], connections
    finally:
        stop.set()
        thread.join(2)
        for conn in connections:
            close_socket_quietly(conn)
        listener.close()


def test_client_send_returns_false_when_not_connected():
    client = make_client(free_port())

    assert client.send({"type": "message", "content": "x"}) is False
    assert client.state == "disconnected"


def test_client_connects_and_logs_in():
    with running_server() as server:
        client = make_client(server.port, username="alice")
        client.start()
        try:
            assert client.wait_connected(3)
            assert wait_until(lambda: server.get_online_users() == ["alice"])
            assert client.state == "connected"
        finally:
            client.stop()


def test_client_reconnects_after_server_restart():
    states = []
    with running_server() as first:
        port = first.port
        client = make_client(
            port, username="alice", on_state_change=lambda s, d: states.append(s)
        )
        client.start()
        try:
            assert client.wait_connected(3)

            first.stop()  # Server sập
            assert wait_until(lambda: not client.is_connected)

            with running_server(port=port) as second:  # Server sống lại
                assert wait_until(lambda: client.is_connected, timeout=5)
                assert wait_until(lambda: second.get_online_users() == ["alice"])
                assert client.reconnect_count == 1
        finally:
            client.stop()

    assert "disconnected" in states
    assert "reconnecting" in states
    assert states.index("disconnected") < len(states) - 1


def test_client_keeps_retrying_until_server_appears():
    port = free_port()
    client = make_client(port, username="alice")
    client.start()
    try:
        time.sleep(0.4)  # vài lần thử thất bại
        assert client.is_connected is False
        assert client.state in ("connecting", "reconnecting")

        with running_server(port=port) as server:
            assert client.wait_connected(5)
            assert wait_until(lambda: server.get_online_users() == ["alice"])
    finally:
        client.stop()


def test_client_gives_up_after_max_attempts():
    client = make_client(free_port(), max_attempts=3, initial_delay=0.01, max_delay=0.02, connect_timeout=0.2)
    client.start()
    thread = client._thread

    thread.join(5)

    assert not thread.is_alive()
    assert client.state == "disconnected"
    assert client._sock is None


def test_client_does_not_reconnect_when_disabled():
    with running_server() as first:
        client = make_client(first.port, username="alice", auto_reconnect=False)
        client.start()
        thread = client._thread
        assert client.wait_connected(3)

        first.stop()
        thread.join(3)

        assert not thread.is_alive()
        assert client.state == "disconnected"
        assert client.reconnect_count == 0


def test_client_detects_silent_server_and_reconnects():
    states = []
    with fake_server() as (port, connections):  # nhận kết nối nhưng không bao giờ trả lời
        client = make_client(
            port, heartbeat_interval=0.1, idle_timeout=0.4,
            on_state_change=lambda s, d: states.append(s),
        )
        client.start()
        try:
            assert wait_until(lambda: len(connections) >= 2, timeout=5)
        finally:
            client.stop()

    assert "disconnected" in states


def test_client_replies_pong_to_server_ping():
    replies = []

    def on_connect(conn):
        conn.settimeout(2)
        conn.sendall(b'{"type":"ping"}\n')
        replies.append(conn.recv(100))

    with fake_server(on_connect) as (port, _connections):
        client = make_client(port)
        client.start()
        try:
            assert wait_until(lambda: len(replies) == 1)
        finally:
            client.stop()

    assert json.loads(replies[0].decode("utf-8")) == {"type": "pong"}


def test_client_stop_releases_socket_and_thread():
    with running_server() as server:
        client = make_client(server.port, username="alice")
        client.start()
        assert client.wait_connected(3)
        thread = client._thread

        client.stop()
        client.stop()  # gọi lần 2 vô hại

        assert client.state == "stopped"
        assert client._sock is None
        assert not thread.is_alive()
        assert wait_until(lambda: server_is_clean(server))


def test_client_survives_exception_in_callback():
    received = []

    def bad_callback(message):
        received.append(message)
        raise RuntimeError("boom")

    with running_server() as server:
        bob = make_client(server.port, username="bob", on_message=bad_callback)
        bob.start()
        try:
            assert bob.wait_connected(3)
            alice = RawClient(server, "alice")
            alice.send({"type": "message", "content": "1"})
            alice.send({"type": "message", "content": "2"})

            assert wait_until(
                lambda: len([m for m in received if m.get("type") == "message"]) == 2
            )
            assert bob.is_connected
            alice.close()
        finally:
            bob.stop()


def test_client_username_taken_is_fatal_on_first_login_but_retried_after_reconnect():
    login_taken = (
        b'{"type":"login_ack","status":"error","error":{"code":"USERNAME_TAKEN"}}'
    )

    first_time = ReconnectingClient("x", 1, username="alice")
    assert first_time._handle_frame(login_taken)  # có lý do kết thúc phiên
    assert first_time._fatal is True  # tên bị người khác dùng thật: không thử lại

    after_reconnect = ReconnectingClient("x", 1, username="alice")
    after_reconnect._logged_in_once = True
    assert after_reconnect._handle_frame(login_taken)  # phiên cũ chưa được Server dọn
    assert after_reconnect._fatal is False  # nên sẽ tự thử lại