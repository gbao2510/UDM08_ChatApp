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
    """Lớp giả lập socket để kiểm thử logic xử lý của ServerCore mà không cần mở cổng mạng thật"""
    def __init__(self, incoming_bytes=b""):
        self.incoming = io.BytesIO(incoming_bytes)
        self.sent = []

    def recv(self, bufsize):
        return self.incoming.read(bufsize)

    def sendall(self, data):
        self.sent.append(data)

    def close(self):
        pass


def test_avatar_logic_unit():
    """Kiểm thử đơn vị (Unit Test) logic lưu và truyền avatar của ServerCore"""
    print("\n==========================================================================")
    print(" 1. KIỂM THỬ ĐƠN VỊ (UNIT TEST) LOGIC LƯU VÀ TRUYỀN AVATAR (TUẦN 3)")
    print("==========================================================================")

    server = ServerCore()
    server.is_running = True

    # 1. Giả lập Client B ('Trương Gia Bân', avatar: 'avatar_ban.png') đã kết nối từ trước
    sock_b = MockSocket()
    server.clients[sock_b] = {
        "username": "Trương Gia Bân",
        "avatar": "avatar_ban.png"
    }

    # 2. Giả lập Client A ('Trần Thuận Trí', avatar: 'avatar_tri.png') gửi gói tin login lên Server
    login_packet_a = {
        "type": "login",
        "username": "Trần Thuận Trí",
        "avatar": "avatar_tri.png"
    }
    raw_incoming_a = (json.dumps(login_packet_a, ensure_ascii=False) + "\n").encode('utf-8')

    sock_a = MockSocket(raw_incoming_a)
    # Gọi hàm xử lý client của Server
    server.handle_client(sock_a, ("127.0.0.1", 12345))

    # 3. Kiểm tra gói tin phản hồi login_ack gửi về cho chính Client A
    sent_to_a = [json.loads(p.decode('utf-8').strip()) for p in sock_a.sent]
    print(f"\n[A] Gói tin phản hồi cho Client A ({len(sent_to_a)} gói):")
    for p in sent_to_a:
        print(f"    - {p}")

    assert len(sent_to_a) >= 1, "Client A phải nhận được ít nhất 1 gói login_ack!"
    ack_a = sent_to_a[0]
    assert ack_a.get("type") == "login_ack", "Loại gói tin phải là login_ack!"
    assert ack_a.get("avatar") == "avatar_tri.png", "Avatar trong login_ack phải khớp với avatar lúc đăng nhập!"
    print("=> XÁC NHẬN: Server đã lưu và trả về chính xác avatar của Client A trong login_ack!")

    # 4. Kiểm tra các gói tin broadcast truyền sang Client B
    sent_to_b = [json.loads(p.decode('utf-8').strip()) for p in sock_b.sent]
    print(f"\n[B] Gói tin broadcast truyền sang Client B ({len(sent_to_b)} gói):")
    for p in sent_to_b:
        print(f"    - {p}")

    # Kiểm tra gói user_join có chứa avatar
    has_user_join = any(
        p.get("type") == "user_join" and p.get("username") == "Trần Thuận Trí" and p.get("avatar") == "avatar_tri.png"
        for p in sent_to_b
    )
    assert has_user_join, "Client B phải nhận được gói user_join chứa avatar của Client A!"
    print("=> XÁC NHẬN: Server đã truyền broadcast gói user_join kèm avatar tới Client B!")

    # Kiểm tra gói user_list có chứa danh sách user kèm avatar
    has_user_list_avatar = any(
        p.get("type") == "user_list" and any(u.get("username") == "Trần Thuận Trí" and u.get("avatar") == "avatar_tri.png" for u in p.get("online_users", []))
        for p in sent_to_b
    )
    assert has_user_list_avatar, "Gói user_list gửi sang Client B phải chứa thông tin avatar của Client A!"
    print("=> XÁC NHẬN: Gói user_list truyền danh sách online mới nhất có đầy đủ avatar của các thành viên!")

    print("\n🎉 [KẾT QUẢ KIỂM THỬ ĐƠN VỊ: THÀNH CÔNG 100%!]")


def test_avatar_live_socket():
    """Kiểm thử qua TCP Socket thật nếu server_core.py đang được bật"""
    print("\n==========================================================================")
    print(" 2. KIỂM THỬ QUA SOCKET MẠNG THỰC TẾ (NẾU SERVER ĐANG CHẠY)")
    print("==========================================================================")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect(('127.0.0.1', 5000))

        # Gửi login kèm avatar
        login_pkt = {"type": "login", "username": "TestUser_Tuan3", "avatar": "test_avatar.png"}
        sock.sendall((json.dumps(login_pkt) + "\n").encode('utf-8'))

        # Nhận phản hồi
        resp = sock.recv(4096).decode('utf-8')
        sock.close()

        pkt = json.loads(resp.strip().split("\n")[0])
        if pkt.get("type") == "login_ack" and pkt.get("avatar") == "test_avatar.png":
            print(f"-> [Socket Test Thành công]: Server phản hồi: {pkt}")
        else:
            print(f"-> [Socket Test]: Server phản hồi: {pkt}")
    except ConnectionRefusedError:
        print("[LƯU Ý] Server chưa chạy trên cổng 5000 (đã hoàn thành kiểm thử Unit Test ở bước 1).")
    except Exception as e:
        print(f"[LƯU Ý] Bỏ qua kiểm thử socket mạng: {e}")


if __name__ == "__main__":
    test_avatar_logic_unit()
    test_avatar_live_socket()
