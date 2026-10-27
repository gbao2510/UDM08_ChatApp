import socket
import json
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker

class NetworkClient(QThread):
    received_signal = pyqtSignal(dict)      # Nhận dl JSON từ server
    connected_signal = pyqtSignal()         # Báo kết nối thành công
    disconnected_signal = pyqtSignal()      # Báo ngắt kết nối
    error_signal = pyqtSignal(str)          # Báo lỗi

    def __init__(self, host='127.0.0.1', port=8888, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.client_socket = None
        self.is_running = False
        self._send_mutex = QMutex() # Thread-safe khi gửi dữ liệu

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
        """Luồng chạy ngầm liên tục lắng nghe dữ liệu từ Server"""
        buffer = ""
        while self.is_running:
            try:
                data = self.client_socket.recv(4096).decode('utf-8')
                if not data:
                    break  # Server ngắt kết nối

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

    def send_data(self, payload: dict):
        """Hàm gửi dữ liệu dạng dict/JSON tới Server"""
        if self.client_socket and self.is_running:
            # Khóa mutex để tránh xung đột khi gửi dữ liệu từ nhiều sự kiện UI
            locker = QMutexLocker(self._send_mutex)
            try:
                json_str = json.dumps(payload) + "\n"
                self.client_socket.sendall(json_str.encode('utf-8'))
            except Exception as e:
                self.error_signal.emit(f"Gửi dữ liệu thất bại: {str(e)}")

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
