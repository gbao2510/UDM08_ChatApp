import sys
from PyQt6.QtCore import QCoreApplication
from Code.Client.network_worker import NetworkClient
from PyQt6.QtCore import QTimer

def on_connected():
    print("[TEST] ✅ Đã kết nối thành công tới Server!")


def on_received(data: dict):
    print(f"[TEST] 📥 Nhận được dữ liệu JSON từ Server: {data}")


def on_error(err: str):
    print(f"[TEST] ❌ Lỗi phát sinh: {err}")


if __name__ == "__main__":
    app = QCoreApplication(sys.argv)

    # Khởi tạo client
    client = NetworkClient(host='127.0.0.1', port=8080)

    # Đăng ký các tín hiệu (Signals)
    client.connected_signal.connect(on_connected)
    client.received_signal.connect(on_received)
    client.error_signal.connect(on_error)

    # Thực hiện kết nối tới Server
    print("[TEST] Đang kết nối tới Server...")
    if client.connect_to_server():
        # Gửi thử 1 gói tin JSON sau khi kết nối
        QTimer.singleShot(500, lambda: client.send_data({"type": "ping", "message": "Hello Server"}))

    sys.exit(app.exec())