import json
import socket
import threading

HOST = "0.0.0.0"
PORT = 5000
BUFFER_SIZE = 4096
MAX_FRAME_SIZE = 1_000_000


def encode_message(data):
    """Chuyển dictionary thành JSON (giữ UTF-8 thật, không escape), kết
    thúc bằng newline. Nếu dữ liệu chứa surrogate lẻ không thể mã hóa
    UTF-8, tự động chuyển sang dạng thoát \\uXXXX (ASCII) để không crash.
    """
    if not isinstance(data, dict):
        raise ValueError("Message must be a JSON object.")

    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    try:
        return (text + "\n").encode("utf-8")
    except UnicodeEncodeError:
        # Dự phòng: surrogate lẻ (vd. "\ud83d") không mã hóa UTF-8 được,
        # chuyển sang dạng \\uXXXX thuần ASCII để vẫn gửi được dữ liệu.
        ascii_text = json.dumps(data, ensure_ascii=True, separators=(",", ":"))
        return (ascii_text + "\n").encode("ascii")


def make_error(code, message):
    """Tạo thông báo lỗi gửi về Client."""
    return {
        "type": "error",
        "error": {
            "code": code,
            "message": message
        }
    }


def _contains_lone_surrogate(value):
    """Đệ quy kiểm tra một giá trị JSON đã parse (dict/list/str) có chứa
    surrogate code point (U+D800-U+DFFF) hay không - dấu hiệu của chuỗi
    \\uXXXX bị lỗi, không được ghép cặp đúng cách."""
    if isinstance(value, str):
        return any(0xD800 <= ord(ch) <= 0xDFFF for ch in value)
    if isinstance(value, dict):
        return any(
            _contains_lone_surrogate(key) or _contains_lone_surrogate(val)
            for key, val in value.items()
        )
    if isinstance(value, list):
        return any(_contains_lone_surrogate(item) for item in value)
    return False


class MessageStore:
    """Lưu các thông điệp hợp lệ để tra cứu nội dung gốc khi có gói tin
    Reply (reply_to_id). Có thể dùng chung cho nhiều ServerRouter (vd. để
    các Client khác nhau trên cùng một Server có thể Reply chéo nhau)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.next_msg_id = 1
        self.messages = {}

    def add(self, message):
        """Gán msg_id tuần tự rồi lưu lại thông điệp để các Reply sau
        này có thể tham chiếu tới."""
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
    """Tách gói TCP, kiểm tra JSON/UTF-8, xử lý Reply (reply_to_id) và
    gán msg_id.

    Nếu không truyền `store`, mỗi ServerRouter tự tạo MessageStore riêng
    (phù hợp khi test độc lập hoặc không cần Reply chéo giữa các Client).
    Muốn nhiều Client Reply chéo nhau, truyền chung một MessageStore qua
    tham số `store` (xem ChatServer bên dưới).
    """

    def __init__(self, max_frame_size=MAX_FRAME_SIZE, store=None):
        self.buffer = bytearray()
        self.max_frame_size = max_frame_size
        self.store = store if store is not None else MessageStore()
        # Bật khi một khung tin vừa bị loại vì quá khổ: bỏ qua phần dữ
        # liệu còn sót lại của khung đó cho tới newline tiếp theo, tránh
        # hiểu nhầm phần đuôi là một gói JSON mới.
        self.skipping_oversized = False

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

        while True:
            if self.skipping_oversized:
                if b"\n" not in self.buffer:
                    break
                # Bỏ nốt phần còn lại của khung tin đã bị loại (tới hết dòng).
                _, _, remaining = self.buffer.partition(b"\n")
                self.buffer = bytearray(remaining)
                self.skipping_oversized = False
                continue

            if b"\n" not in self.buffer:
                break

            frame, _, remaining = self.buffer.partition(b"\n")
            self.buffer = bytearray(remaining)

            if not frame.strip():
                continue

            results.append(self.parse_frame(bytes(frame)))

        if len(self.buffer) > self.max_frame_size:
            self.buffer.clear()
            self.skipping_oversized = True
            results.append({
                "ok": False,
                "error": make_error(
                    "MESSAGE_TOO_LARGE",
                    "Thong diep vuot qua kich thuoc cho phep."
                )
            })

        return results

    def parse_frame(self, frame):
        """Kiểm tra UTF-8 (bỏ qua BOM nếu có), JSON object hợp lệ (không
        chứa surrogate lẻ), xử lý Reply (reply_to_id) rồi gán msg_id."""
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

        # Bo qua BOM (U+FEFF) neu Client vo tinh gui kem o dau goi tin.
        if text.startswith("\ufeff"):
            text = text[1:]

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

        if _contains_lone_surrogate(message):
            return {
                "ok": False,
                "error": make_error(
                    "INVALID_UNICODE",
                    "Chuoi JSON chua surrogate khong hop le (khong duoc "
                    "ghep cap)."
                )
            }

        # Neu la goi tin Reply, tim noi dung goc dua tren reply_to_id
        # TRUOC khi gan msg_id va luu thong diep hien tai.
        reply_result = None
        if "reply_to_id" in message:
            reply_result = self._resolve_reply(message["reply_to_id"])
            if not reply_result["ok"]:
                return reply_result

        # Gan msg_id tuan tu va luu lai de cac Reply trong tuong lai
        # co the tra cuu.
        self.store.add(message)

        if reply_result is not None:
            message["reply_to"] = reply_result["original"]

        return {
            "ok": True,
            "message": message
        }

    def _resolve_reply(self, reply_to_id):
        """Kiểm tra reply_to_id và tra cứu nội dung gốc tương ứng trong
        MessageStore."""
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
        # Dung chung cho moi Client de co the Reply cheo giua cac Client.
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
        # Moi Client co buffer rieng de tranh tron cac luong TCP, nhung
        # dung chung MessageStore de co the Reply cheo giua cac Client.
        parser = ServerRouter(store=self.store)

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