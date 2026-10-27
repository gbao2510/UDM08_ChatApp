import sys
sys.path.insert(0, '') 

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from Code.Client.network_worker import NetworkClient


def handle_connected():
    print("\n[TEST] -> Đã kết nối thành công tới Server!")

def handle_received(data):
    print(f"[TEST] -> NHẬN DỮ LIỆU TỪ SERVER: {data}\n")

def handle_error(err_msg):
    print(f"[TEST] -> Lỗi: {err_msg}")

def send_test_data(client: NetworkClient):
    print("[TEST] -> Đang gửi dữ liệu test sang Server...")
    client.send_data({
        "type": "login",
        "username": "bichtram"
    })


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Khởi tạo client
    client = NetworkClient(host='127.0.0.1', port=5000)

    # Lắp tín hiệu
    client.connected_signal.connect(handle_connected)
    client.received_signal.connect(handle_received)
    client.error_signal.connect(handle_error)

    print("Đang thử kết nối tới Server...")
    
    # Thực hiện kết nối
    if client.connect_to_server():
        QTimer.singleShot(500, lambda: send_test_data(client))

    sys.exit(app.exec())