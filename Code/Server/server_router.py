import json
import socket
import threading

HOST = "0.0.0.0"
PORT = 5000
BUFFER_SIZE = 4096
MAX_FRAME_SIZE = 1_000_000


def encode_message(data):
    """Chuyển dictionary thành JSON, kết thúc bằng newline."""
    if not isinstance(data, dict):
        raise ValueError("Message must be a JSON object.")

    return (
        json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def make_error(code, message):
    """Tạo thông báo lỗi gửi về Client."""
    return {
        "type": "error",
        "error": {
            "code": code,
            "message": message
        }
    }


class MessageStore:
    """Lưu các thông điệp hợp lệ (dùng chung cho toàn Server) để tra cứu
    nội dung gốc khi có gói tin Reply (reply_to_id)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.next_msg_id = 1
        self.messages = {}

    def add(self, message):
        """Gán msg_id tuần tự dùng chung cho mọi Client, rồi lưu lại
        thông điệp để các Reply sau này có thể tham chiếu tới."""
        with self.lock:
            msg_id = self.next_msg_id
            self.next_msg_id += 1
            message["msg_id"] = msg_id
            self.messages[msg_id] = message
            return msg_id

    def get(self, msg_id):
        """Tra cứu nội dung gốc theo msg_id. Trả về None nếu không có."""
        with self.lock:
            return self.messages.get(msg_id)


class ServerRouter:
    """Tách gói TCP, kiểm tra JSON, xử lý Reply (reply_to_id) và gán msg_id."""

    def __init__(self, store, max_frame_size=MAX_FRAME_SIZE):
        self.buffer = bytearray()
        self.max_frame_size = max_frame_size
        self.store = store

    def feed_data(self, data):
        """
        Nhận một phần dữ liệu TCP.
        Trả về danh sách các thông điệp hoàn chỉnh hoặc lỗi.
        """
        if not isinstance(data, (bytes, bytearray)):
            return [{
                "ok": False,
                "error": make_error(
                    "INVALID_INPUT_TYPE",
                    "Du lieu dau vao phai la bytes."
                )
            }]

        self.buffer.extend(data)
        results = []

        while b"\n" in self.buffer:
            frame, _, remaining = self.buffer.partition(b"\n")
            self.buffer = bytearray(remaining)

            if not frame.strip():
                continue

            results.append(self.parse_frame(bytes(frame)))

        if len(self.buffer) > self.max_frame_size:
            self.buffer.clear()
            results.append({
                "ok": False,
                "error": make_error(
                    "MESSAGE_TOO_LARGE",
                    "Thong diep vuot qua kich thuoc cho phep."
                )
            })

        return results

    def parse_frame(self, frame):
        """Kiểm tra UTF-8, JSON object và gán msg_id."""
        try:
            text = frame.decode("utf-8")
        except UnicodeDecodeError:
            return {
                "ok": False,
                "error": make_error(
                    "INVALID_ENCODING",
                    "Du lieu phai duoc ma hoa bang UTF-8 hop le."
                )
            }

        try:
            message = json.loads(text)
        except json.JSONDecodeError as exc:
            return {
                "ok": False,
                "error": make_error(
                    "INVALID_JSON",
                    f"JSON khong hop le tai dong {exc.lineno}, "
                    f"cot {exc.colno}: {exc.msg}."
                )
            }

        if not isinstance(message, dict):
            return {
                "ok": False,
                "error": make_error(
                    "JSON_OBJECT_REQUIRED",
                    "Thong diep JSON phai la mot object."
                )
            }

        # Nếu là gói tin Reply, tìm nội dung gốc dựa trên reply_to_id
        # TRƯỚC khi gán msg_id và lưu thông điệp hiện tại.
        reply_result = None
        if "reply_to_id" in message:
            reply_result = self._resolve_reply(message["reply_to_id"])
            if not reply_result["ok"]:
                return reply_result

        # Gán msg_id tuần tự (dùng chung cho toàn Server) và lưu lại
        # để các Reply trong tương lai có thể tra cứu.
        self.store.add(message)

        if reply_result is not None:
            message["reply_to"] = reply_result["original"]

        return {
            "ok": True,
            "message": message
        }

    def _resolve_reply(self, reply_to_id):
        """Kiểm tra reply_to_id và tra cứu nội dung gốc tương ứng trong
        MessageStore dùng chung của toàn Server."""
        if not isinstance(reply_to_id, int) or isinstance(reply_to_id, bool):
            return {
                "ok": False,
                "error": make_error(
                    "INVALID_REPLY_TO_ID",
                    "reply_to_id phai la so nguyen (msg_id)."
                )
            }

        original = self.store.get(reply_to_id)

        if original is None:
            return {
                "ok": False,
                "error": make_error(
                    "REPLY_NOT_FOUND",
                    f"Khong tim thay thong diep goc voi msg_id={reply_to_id}."
                )
            }

        return {
            "ok": True,
            "original": original
        }


class ChatServer:
    """TCP Server minh họa tích hợp ServerRouter."""

    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.store = MessageStore()

    def start(self):
        with socket.socket(
            socket.AF_INET, socket.SOCK_STREAM
        ) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen()

            print(f"Server dang chay tai {self.host}:{self.port}")

            try:
                while True:
                    client, address = server.accept()
                    print(f"Client ket noi: {address}")

                    threading.Thread(
                        target=self.handle_client,
                        args=(client, address),
                        daemon=True
                    ).start()

            except KeyboardInterrupt:
                print("\nServer dang dung.")

    def handle_client(self, client, address):
        # Mỗi Client có buffer riêng để tránh trộn các luồng TCP,
        # nhưng dùng chung MessageStore để có thể Reply chéo giữa các Client.
        parser = ServerRouter(self.store)

        with client:
            try:
                while True:
                    data = client.recv(BUFFER_SIZE)

                    if not data:
                        print(f"Client da ngat ket noi: {address}")
                        break

                    for result in parser.feed_data(data):
                        if not result["ok"]:
                            response = result["error"]
                        else:
                            message = result["message"]
                            print(f"Nhan tu {address}: {message}")

                            response = {
                                "type": "ack",
                                "message": "Server da nhan tin nhan hop le.",
                                "received": message
                            }

                        client.sendall(encode_message(response))

            except (ConnectionError, OSError) as exc:
                print(f"Loi ket noi voi {address}: {exc}")


if __name__ == "__main__":
    ChatServer().start()