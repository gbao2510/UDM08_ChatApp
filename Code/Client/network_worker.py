import socket
import json
import datetime
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker

class NetworkClient(QThread):
    received_signal = pyqtSignal(dict)      # Nhận dl JSON từ server
    connected_signal = pyqtSignal()         # Báo kết nối thành công
    disconnected_signal = pyqtSignal()      # Báo ngắt kết nối
    error_signal = pyqtSignal(str)          # Báo lỗi

    def __init__(self, host='127.0.0.1', port=5000, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.client_socket = None
        self.is_running = False
        self._send_mutex = QMutex() # Thread-safe khi gửi dữ liệu
        self.username = None

    def connect_to_server(self, host=None, port=None) -> bool:
        """Khởi tạo kết nối TCP Socket tới Server"""
        if host:
            self.host = host
        if port:
            self.port = port

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
            self.is_running = True
            
            # Thông báo cho UI biết kết nối thành công
            self.connected_signal.emit()
            
            # Bắt đầu luồng run() chạy ngầm lắng nghe dữ liệu
            self.start()
            return True
        except Exception as e:
            self.error_signal.emit(f"Không thể kết nối Server: {str(e)}")
            return False

    def run(self):
        """Luồng chạy ngầm liên tục lắng nghe dữ liệu từ Server (sử dụng bytearray buffer chống lỗi UTF-8/emoji bị cắt đôi)"""
        buffer = bytearray()
        while self.is_running:
            try:
                data = self.client_socket.recv(4096)
                if not data:
                    break  # Server ngắt kết nối

                buffer.extend(data)
                
                while b"\n" in buffer:
                    newline_pos = buffer.find(b"\n")
                    line_bytes = bytes(buffer[:newline_pos])
                    del buffer[:newline_pos + 1]
                    line = line_bytes.decode('utf-8', errors='replace').strip()
                    if line:
                        try:
                            json_data = json.loads(line)
                            if isinstance(json_data, dict):
                                self.received_signal.emit(json_data)
                        except json.JSONDecodeError:
                            # Bỏ qua các chuỗi plain-text chào mừng từ server mà không báo lỗi hỏng UI
                            pass
                                        
            except Exception as e:
                if self.is_running:
                    self.error_signal.emit(f"Lỗi khi nhận dữ liệu: {str(e)}")
                break

        # Đóng socket khi kết thúc luồng
        self.is_running = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception:
                pass
        self.disconnected_signal.emit()

    def send_data(self, payload: dict) -> bool:
        """Hàm gửi dữ liệu dạng dict/JSON tới Server"""
        # Tự động lưu username nếu đây là gói đăng nhập
        if isinstance(payload, dict) and payload.get("type") == "login":
            if "username" in payload:
                self.username = payload["username"]

        if self.client_socket and self.is_running:
            # Khóa mutex để tránh xung đột khi gửi dữ liệu từ nhiều sự kiện UI
            locker = QMutexLocker(self._send_mutex)
            try:
                json_str = json.dumps(payload, ensure_ascii=False) + "\n"
                self.client_socket.sendall(json_str.encode('utf-8'))
                return True
            except Exception as e:
                self.error_signal.emit(f"Gửi dữ liệu thất bại: {str(e)}")
                return False
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
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            self.client_socket.close()
        self.wait()