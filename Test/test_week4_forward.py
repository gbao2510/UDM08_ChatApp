import json  # Thư viện làm việc với định dạng dữ liệu JSON
import io  # Thư viện xử lý luồng byte trong bộ nhớ
import sys  # Thư viện hệ thống để chỉnh bảng mã UTF-8 cho Console
import socket  # Thư viện socket mạng chuẩn của Python

# Đảm bảo hiển thị tiếng Việt có dấu rõ ràng trên Console Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Thêm đường dẫn thư mục gốc để import ServerCore
sys.path.insert(0, '')
from Code.Server.server_core import ServerCore


class MockSocket:
    """Lớp giả lập socket mạng để kiểm thử logic xử lý của ServerCore một cách tin cậy và độc lập"""
    def __init__(self, incoming_bytes=b""):
        self.incoming = io.BytesIO(incoming_bytes)
        self.sent = []

    def recv(self, bufsize):
        return self.incoming.read(bufsize)

    def sendall(self, data):
        self.sent.append(data)

    def close(self):
        pass


def test_forward_message_routing():
    """Kiểm thử toàn diện chức năng điều hướng tin nhắn Forward (Tuần 4)"""
    print("\n==========================================================================")
    print(" KIỂM THỬ ĐIỀU HƯỚNG TIN NHẮN FORWARD: 1-1 & PHÒNG CHUNG (TUẦN 4)")
    print("==========================================================================")

    server = ServerCore()
    server.is_running = True

    # Giả lập 2 client khác đang online trong hệ thống:
    # 1. Client B: Trương Gia Bân
    sock_b = MockSocket()
    server.clients[sock_b] = {
        "username": "Trương Gia Bân",
        "avatar": "avatar_ban.png"
    }

    # 2. Client C: Lý Huỳnh Bích Trâm
    sock_c = MockSocket()
    server.clients[sock_c] = {
        "username": "Lý Huỳnh Bích Trâm",
        "avatar": "avatar_tram.png"
    }

    # 3. Client A: Trần Thuận Trí (người gửi các tin nhắn chuyển tiếp)
    sock_a = MockSocket()
    server.clients[sock_a] = {
        "username": "Trần Thuận Trí",
        "avatar": "avatar_tri.png"
    }

    # -------------------------------------------------------------------------
    # KỊCH BẢN 1: FORWARD VÀO PHÒNG CHUNG (receiver = "all")
    # -------------------------------------------------------------------------
    print("\n[KỊCH BẢN 1] Client A gửi Forward vào phòng chung (receiver: 'all')...")
    forward_all = {
        "type": "forward",
        "sender": "Trần Thuận Trí",
        "receiver": "all",
        "content": "Thông báo: Ngày mai nhóm họp lúc 9h sáng nhé!",
        "timestamp": "15:30:00"
    }
    server.handle_forward_message(sock_a, "Trần Thuận Trí", "avatar_tri.png", forward_all)

    # Kiểm tra phản hồi forward_ack cho Client A
    sent_a = [json.loads(p.decode('utf-8').strip()) for p in sock_a.sent]
    print(f"-> [Client A nhận ACK]: {sent_a[-1]}")
    assert sent_a[-1].get("type") == "forward_ack"
    assert sent_a[-1].get("status") == "success"
    assert sent_a[-1].get("receiver") == "all"

    # Kiểm tra Client B và Client C đều nhận được tin nhắn Forward phòng chung
    sent_b = [json.loads(p.decode('utf-8').strip()) for p in sock_b.sent]
    sent_c = [json.loads(p.decode('utf-8').strip()) for p in sock_c.sent]
    print(f"-> [Client B nhận được]: {sent_b[-1]}")
    print(f"-> [Client C nhận được]: {sent_c[-1]}")

    assert sent_b[-1].get("type") == "forward" and sent_b[-1].get("receiver") == "all"
    assert sent_c[-1].get("type") == "forward" and sent_c[-1].get("receiver") == "all"
    print("=> XÁC NHẬN: Điều hướng Forward phòng chung THÀNH CÔNG 100%!")

    # -------------------------------------------------------------------------
    # KỊCH BẢN 2: FORWARD 1-1 TỚI CLIENT B (receiver = "Trương Gia Bân")
    # -------------------------------------------------------------------------
    print("\n[KỊCH BẢN 2] Client A gửi Forward 1-1 riêng cho 'Trương Gia Bân'...")
    forward_private = {
        "type": "forward",
        "sender": "Trần Thuận Trí",
        "receiver": "Trương Gia Bân",
        "content": "Bân ơi, đây là tài liệu mật tuần 4 tôi chuyển tiếp riêng cho ông.",
        "timestamp": "15:31:00"
    }
    # Reset lịch sử nhận của các socket
    sock_a.sent.clear()
    sock_b.sent.clear()
    sock_c.sent.clear()

    server.handle_forward_message(sock_a, "Trần Thuận Trí", "avatar_tri.png", forward_private)

    # Client A nhận được xác nhận chuyển tiếp 1-1 thành công
    sent_a = [json.loads(p.decode('utf-8').strip()) for p in sock_a.sent]
    print(f"-> [Client A nhận ACK 1-1]: {sent_a[-1]}")
    assert sent_a[-1].get("type") == "forward_ack"
    assert sent_a[-1].get("status") == "success"
    assert sent_a[-1].get("receiver") == "Trương Gia Bân"

    # Client B nhận được tin nhắn forward riêng
    sent_b = [json.loads(p.decode('utf-8').strip()) for p in sock_b.sent]
    print(f"-> [Client B nhận tin Forward riêng]: {sent_b[-1]}")
    assert sent_b[-1].get("type") == "forward"
    assert sent_b[-1].get("receiver") == "Trương Gia Bân"
    assert "tài liệu mật" in sent_b[-1].get("content")

    # Client C hoàn toàn KHÔNG nhận được (đảm bảo tính riêng tư 1-1)
    print(f"-> [Client C nhận được]: {len(sock_c.sent)} gói tin (Không bị lộ tin 1-1)")
    assert len(sock_c.sent) == 0
    print("=> XÁC NHẬN: Điều hướng Forward 1-1 chuẩn xác, bảo mật tin nhắn riêng tư!")

    # -------------------------------------------------------------------------
    # KỊCH BẢN 3: FORWARD 1-1 TỚI USER KHÔNG ONLINE (receiver = "Người Không Tồn Tại")
    # -------------------------------------------------------------------------
    print("\n[KỊCH BẢN 3] Client A gửi Forward 1-1 tới người offline ('Ngô Gia Bảo')...")
    forward_offline = {
        "type": "forward",
        "sender": "Trần Thuận Trí",
        "receiver": "Ngô Gia Bảo",
        "content": "Gửi cho Bảo lúc Bảo đang offline.",
        "timestamp": "15:32:00"
    }
    sock_a.sent.clear()
    server.handle_forward_message(sock_a, "Trần Thuận Trí", "avatar_tri.png", forward_offline)

    # Client A nhận được thông báo lỗi người dùng không online
    sent_a = [json.loads(p.decode('utf-8').strip()) for p in sock_a.sent]
    print(f"-> [Client A nhận báo lỗi]: {sent_a[-1]}")
    assert sent_a[-1].get("type") == "forward_ack"
    assert sent_a[-1].get("status") == "error"
    print("=> XÁC NHẬN: Xử lý ngoại lệ người nhận offline an toàn và chính xác!")

    print("\n🎉 [KẾT QUẢ KIỂM THỬ: TẤT CẢ KỊCH BẢN ĐẠT 100% THÀNH CÔNG!]")


if __name__ == "__main__":
    test_forward_message_routing()
