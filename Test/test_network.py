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
        # 1.Gửi thử 1 gói tin JSON sau khi kết nối thành công
        QTimer.singleShot(500, lambda: client.send_data({"type": "ping", "message": "Hello Server"}))
        # 2.Gửi thử 1 Emoji qua hàm send_emoji
        QTimer.singleShot(1000, lambda: client.send_emoji("🎉"))
        # 3. Gửi thử tin nhắn Reply (trả lời cho msg_id = 1) (1.5s)
        QTimer.singleShot(1500, lambda: client.send_reply(reply_to_msg_id=1, content="Trả lời cho tin nhắn số 1", target_room_or_user="general",),)
        # 4. Gửi thử tin nhắn Forward (chuyển tiếp msg_id = 1 sang room2) (2.0s)
        QTimer.singleShot(2000, lambda: client.send_forward( original_msg_id=1, content="Nội dung được chuyển tiếp", target_room_or_user="room2", original_sender="UserA",),)
    sys.exit(app.exec())