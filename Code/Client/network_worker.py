import socket
import json
import datetime
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker

# Hằng số cấu hình timeout mạng (giây)
CONNECT_TIMEOUT = 10    # Thời gian chờ tối đa khi kết nối tới Server
RECV_TIMEOUT    = 30    # Thời gian chờ tối đa giữa 2 lần nhận dữ liệu
MAX_RETRY_ERRORS = 3    # Số lần lỗi recv liên tiếp tối đa trước khi ngắt kết nối

class NetworkClient(QThread):
    received_signal     = pyqtSignal(dict)  # Nhận dl JSON từ server
    connected_signal    = pyqtSignal()      # Báo kết nối thành công
    disconnected_signal = pyqtSignal()      # Báo ngắt kết nối
    error_signal        = pyqtSignal(str)   # Báo lỗi kết nối / gửi dữ liệu
    timeout_signal      = pyqtSignal(str)   # Báo lỗi TIMEOUT / mất mạng lên GUI

    def __init__(self, host='127.0.0.1', port=5000, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.client_socket = None
        self.is_running = False
        self._send_mutex = QMutex() # Thread-safe khi gửi dữ liệu
        self.username = None

    def connect_to_server(self, host=None, port=None) -> bool:
        """Khởi tạo kết nối TCP Socket tới Server, có kiểm soát timeout khi connect"""
        if host:
            self.host = host
        if port:
            self.port = port

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Giới hạn thời gian chờ kết nối, nếu Server không phản hồi sau CONNECT_TIMEOUT giây  thì socket.connect() ném ra socket.timeout, bắt được ngay dưới đây
            self.client_socket.settimeout(CONNECT_TIMEOUT)
            self.client_socket.connect((self.host, self.port))

            # Sau khi kết nối thành công, chuyển sang timeout cho vòng lặp recv
            self.client_socket.settimeout(RECV_TIMEOUT)

            self.is_running = True
            self.connected_signal.emit()
            self.start()
            return True

        except socket.timeout:
            msg = f"Kết nối tới {self.host}:{self.port} hết thời gian chờ ({CONNECT_TIMEOUT}s). Kiểm tra lại mạng!"
            self.timeout_signal.emit(msg)
            self.error_signal.emit(msg)
            self._close_socket()
            return False

        except ConnectionRefusedError:
            msg = f"Server {self.host}:{self.port} từ chối kết nối. Server có đang chạy không?"
            self.error_signal.emit(msg)
            self._close_socket()
            return False

        except OSError as e:
            msg = f"Không thể kết nối Server: {str(e)}"
            self.error_signal.emit(msg)
            self._close_socket()
            return False

    def run(self):
        """Luồng chạy ngầm liên tục lắng nghe dữ liệu từ Server"""
        buffer = ""
        consecutive_errors = 0  # Đếm số lần lỗi recv liên tiếp để phát hiện mất mạng

        while self.is_running:
            try:
                data = self.client_socket.recv(4096).decode('utf-8')

                if not data:
                    # Server đóng kết nối bình thường
                    if self.is_running:
                        self.error_signal.emit("Server đã đóng kết nối.")
                    break

                # Nhận được dữ liệu, reset bộ đếm lỗi
                consecutive_errors = 0
                buffer += data

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        try:
                            json_data = json.loads(line)
                            if isinstance(json_data, dict):
                                self.received_signal.emit(json_data)
                        except json.JSONDecodeError:
                            # Bỏ qua plain-text không phải JSON
                            pass

            except socket.timeout:
                # Không nhận được dữ liệu trong RECV_TIMEOUT giây, khả năng cao là mất mạng
                consecutive_errors += 1
                msg = (
                    f"Mất kết nối với Server ({RECV_TIMEOUT}s không nhận được dữ liệu). "
                    f"Lần {consecutive_errors}/{MAX_RETRY_ERRORS}."
                )
                self.timeout_signal.emit(msg)

                if consecutive_errors >= MAX_RETRY_ERRORS:
                    self.error_signal.emit(
                        f"Mất mạng: Không nhận được phản hồi từ Server sau {MAX_RETRY_ERRORS} lần thử. "
                        "Vui lòng kiểm tra kết nối mạng và thử lại."
                    )
                    break
                # Chưa đủ số lần, tiếp tục chờ không ngắt ngay
                continue

            except ConnectionResetError:
                if self.is_running:
                    self.error_signal.emit(
                        "Kết nối bị Server ngắt đột ngột (Connection Reset). "
                        "Server có thể đã tắt hoặc mạng bị gián đoạn."
                    )
                break

            except OSError as e:
                # Bắt tất cả lỗi hệ thống mạng còn lại
                if self.is_running:
                    self.error_signal.emit(f"Lỗi mạng nghiêm trọng: {str(e)}")
                break

        # Dọn dẹp sau khi vòng lặp kết thúc 
        self.is_running = False
        self._close_socket()
        self.disconnected_signal.emit()

    def _close_socket(self):
        """Đóng socket an toàn"""
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self.client_socket.close()
            except Exception:
                pass
            self.client_socket = None

    def send_data(self, payload: dict) -> bool:
        """Hàm gửi dữ liệu dạng dict/JSON tới Server, có xử lý timeout và lỗi mạng"""
        # Tự động lưu username nếu đây là gói đăng nhập
        if isinstance(payload, dict) and payload.get("type") == "login":
            if "username" in payload:
                self.username = payload["username"]

        if not (self.client_socket and self.is_running):
            return False

        # Khóa mutex để tránh xung đột khi gửi dữ liệu từ nhiều sự kiện UI
        locker = QMutexLocker(self._send_mutex)
        try:
            json_str = json.dumps(payload, ensure_ascii=False) + "\n"
            self.client_socket.sendall(json_str.encode('utf-8'))
            return True

        except socket.timeout:
            msg = "Gửi dữ liệu thất bại: Hết thời gian chờ phản hồi từ Server (timeout)."
            self.timeout_signal.emit(msg)
            self.error_signal.emit(msg)
            return False

        except BrokenPipeError:
            msg = "Gửi dữ liệu thất bại: Kết nối đã bị đứt (Broken Pipe)."
            self.error_signal.emit(msg)
            return False

        except OSError as e:
            msg = f"Gửi dữ liệu thất bại: Lỗi mạng — {str(e)}"
            self.error_signal.emit(msg)
            return False

    def send_message(self, content: str, receiver: str = "all", sender: str = None) -> bool:
        """Hàm gửi tin nhắn văn bản thông thường tới Server"""
        if not content:
            return False

        sender_name = sender or self.username or ""
        payload = {
            "type": "msg",
            "sender": sender_name,
            "receiver": receiver,
            "content": str(content),
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
        }
        return self.send_data(payload)

    def send_emoji(self, emoji: str, receiver: str = "all", sender: str = None) -> bool:
        """Hàm gửi biểu tượng cảm xúc (Emoji) tới Server"""
        if not emoji:
            return False

        sender_name = sender or self.username or ""
        emoji_str = str(emoji)
        payload = {
            "type": "emoji",
            "sender": sender_name,
            "receiver": receiver,
            "emoji": emoji_str,
            "content": emoji_str,
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
        }
        return self.send_data(payload)

    def send_reply(self, reply_to_id: int, content: str, receiver: str = "all"):
        """Hàm gửi tin nhắn trả lời (Reply) một tin nhắn cụ thể theo reply_to_id."""
        sender_name = self.username or ""
        payload = {
            "type": "reply",
            "reply_to_id": reply_to_id,
            "reply_to_msg_id": reply_to_id,
            "content": content,
            "sender": sender_name,
            "receiver": receiver,
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
        }
        self.send_data(payload)

    def send_forward(self, original_msg_id: int, content: str, receiver: str = "all", original_sender: str = "",):
        """Hàm chuyển tiếp (Forward) một tin nhắn sang phòng/người dùng khác"""
        sender_name = self.username or ""
        payload = {
            "type": "forward",
            "original_msg_id": original_msg_id,
            "content": content,
            "sender": sender_name,
            "original_sender": original_sender,
            "receiver": receiver,
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
        }
        self.send_data(payload)

    def stop(self):
        """Dừng luồng an toàn khi tắt ứng dụng"""
        self.is_running = False
        self._close_socket()
        self.wait()