import sys
import os
from PyQt6.QtCore import QCoreApplication, QTimer

# Khai thông đường dẫn để Python nhận diện được thư mục Code ở gốc dự án
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Code.Client.network_worker import NetworkClient

def on_connected():
    print("[TEST] ✅ Đã kết nối thành công tới Server!")

def on_received(data: dict):
    print(f"[TEST] 📥 Nhận được dữ liệu JSON từ Server: {data}")

def on_error(err: str):
    print(f"[TEST] ❌ Lỗi phát sinh: {err}")

if __name__ == "__main__":
    app = QCoreApplication(sys.argv)

    # Khởi tạo client (Đã chỉnh port về 5000 để khớp với server_core.py)
    client = NetworkClient(host='127.0.0.1', port=5000)

    # Đăng ký các tín hiệu (Signals)
    client.connected_signal.connect(on_connected)
    client.received_signal.connect(on_received)
    client.error_signal.connect(on_error)

    # Thực hiện kết nối tới Server
    print("[TEST] Đang kết nối tới Server...")
    if client.connect_to_server():
        # Gửi thử 1 gói tin JSON sau khi kết nối thành công
        QTimer.singleShot(500, lambda: client.send_data({"type": "ping", "message": "Hello Server"}))

    sys.exit(app.exec())