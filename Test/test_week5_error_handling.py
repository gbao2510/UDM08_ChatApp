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
import os
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
from Code.Server.server_core import ServerCore


class MockSocket:
    """Lớp giả lập socket mạng hỗ trợ kiểm thử các tình huống đứt mạng, lỗi kết nối và reconnect"""
    def __init__(self, incoming_bytes=b"", should_raise_on_send=False):
        self.incoming = io.BytesIO(incoming_bytes)
        self.sent = []
        self.is_closed = False
        self.is_shutdown = False
        self.should_raise_on_send = should_raise_on_send

    def recv(self, bufsize):
        if self.is_closed:
            raise OSError("Socket đã đóng")
        return self.incoming.read(bufsize)

    def sendall(self, data):
        if self.is_closed or self.should_raise_on_send:
            raise BrokenPipeError("[Errno 32] Broken pipe: Socket đích đã đứt kết nối!")
        self.sent.append(data)

    def shutdown(self, how):
        self.is_shutdown = True

    def close(self):
        self.is_closed = True


def test_week5_error_handling_and_cleanup():
    """Kiểm thử toàn diện các yêu cầu Tuần 5: Bắt lỗi kết nối, Reconnect tự động và Dọn dẹp rác triệt để"""
    print("\n==========================================================================")
    print(" KIỂM THỬ TUẦN 5: BẮT LỖI KẾT NỐI, RECONNECT TỰ ĐỘNG & GIẢI PHÓNG TÀI NGUYÊN")
    print("==========================================================================")

    server = ServerCore()
    server.is_running = True

    # -------------------------------------------------------------------------
    # KỊCH BẢN 1: CLIENT TẮT ĐỘT NGỘT & SERVER DỌN DẸP RÁC TRIỆT ĐỂ
    # -------------------------------------------------------------------------
    print("\n[KỊCH BẢN 1] Client B ('Trương Gia Bân') tắt đột ngột (Connection Reset)...")
    sock_a = MockSocket()
    server.clients[sock_a] = {"username": "Trần Thuận Trí", "avatar": "avatar_tri.png"}

    sock_b = MockSocket()
    server.clients[sock_b] = {"username": "Trương Gia Bân", "avatar": "avatar_ban.png"}

    assert len(server.clients) == 2, "Hệ thống phải có 2 client ban đầu"

    # Giả lập Client B bị sập kết nối đột ngột
    server.cleanup_client(sock_b, username="Trương Gia Bân", reason="Client bị tắt đột ngột (Connection Reset)")

    # Kiểm tra giải phóng tài nguyên
    assert sock_b not in server.clients, "Socket B phải được xóa sạch khỏi self.clients!"
    assert sock_b.is_closed is True, "Socket B phải được đóng (close) triệt để!"
    assert sock_b.is_shutdown is True, "Socket B phải được ngắt (shutdown) cả 2 chiều!"
    assert len(server.clients) == 1, "Chỉ còn 1 client A trong hệ thống!"

    # Kiểm tra Client A nhận được thông báo rời phòng và danh sách cập nhật
    sent_a = [json.loads(p.decode('utf-8').strip()) for p in sock_a.sent]
    has_leave_pkt = any(p.get("type") == "user_leave" and p.get("username") == "Trương Gia Bân" for p in sent_a)
    has_updated_list = any(p.get("type") == "user_list" and len(p.get("online_users", [])) == 1 for p in sent_a)

    assert has_leave_pkt, "Client A phải nhận được thông báo user_leave của B!"
    assert has_updated_list, "Client A phải nhận được danh sách online mới nhất sau khi B thoát!"
    print("=> XÁC NHẬN [Kịch bản 1]: Đã bắt lỗi tắt đột ngột và giải phóng triệt để socket rác!")

    # -------------------------------------------------------------------------
    # KỊCH BẢN 2: CLIENT RECONNECT TỰ ĐỘNG VỚI CÙNG USERNAME
    # -------------------------------------------------------------------------
    print("\n[KỊCH BẢN 2] Client A ('Trần Thuận Trí') tự động Reconnect sau khi rớt mạng...")
    # Client A hiện đang có socket cũ sock_a trong self.clients
    assert sock_a in server.clients

    # Giả lập Client A kết nối lại bằng socket mới (sock_a_reconnect) với cùng tên 'Trần Thuận Trí'
    login_reconnect_pkt = {
        "type": "login",
        "username": "Trần Thuận Trí",
        "avatar": "avatar_tri.png"
    }
    raw_incoming = (json.dumps(login_reconnect_pkt) + "\n").encode('utf-8')
    sock_a_reconnect = MockSocket(raw_incoming)

    # Server xử lý kết nối mới này
    server.handle_client(sock_a_reconnect, ("127.0.0.1", 33333))

    # Kiểm tra: Socket cũ phải được dọn dẹp và socket mới được cấp phép thành công
    sent_new = [json.loads(p.decode('utf-8').strip()) for p in sock_a_reconnect.sent]
    assert len(sent_new) >= 1, "Socket mới phải nhận được login_ack!"
    ack = sent_new[0]
    assert ack.get("type") == "login_ack", "Phải nhận được gói login_ack!"
    assert ack.get("status") == "success", "Đăng nhập reconnect phải thành công, không bị chặn USERNAME_TAKEN!"
    assert sock_a.is_closed is True, "Socket cũ bị treo phải được dọn dẹp và đóng triệt để!"
    print("=> XÁC NHẬN [Kịch bản 2]: Cơ chế Reconnect tự động hoạt động mượt mà, thu hồi socket cũ!")

    # -------------------------------------------------------------------------
    # KỊCH BẢN 3: PHÁT HIỆN VÀ THU HỒI SOCKET CHẾT KHI GỬI DỮ LIỆU
    # -------------------------------------------------------------------------
    print("\n[KỊCH BẢN 3] Phát hiện socket chết (Broken Pipe) khi đang broadcast dữ liệu...")
    # Tạo 1 socket bị lỗi khi sendall
    broken_socket = MockSocket(should_raise_on_send=True)
    server.clients[broken_socket] = {"username": "User_Hong_Mang", "avatar": "default.png"}

    # Server gửi tin nhắn broadcast
    server.broadcast_packet({"type": "msg", "sender": "HeThong", "content": "Tin nhắn thử nghiệm"})

    # Kiểm tra: Socket hỏng phải bị phát hiện và xóa ngay lập tức khỏi self.clients
    assert broken_socket not in server.clients, "Socket hỏng phải được tự động thu hồi ngay khi gửi thất bại!"
    assert broken_socket.is_closed is True, "Socket hỏng phải được đóng hoàn toàn!"
    print("=> XÁC NHẬN [Kịch bản 3]: Tự động quét và dọn sạch socket chết (zero zombie sockets)!")

    # -------------------------------------------------------------------------
    # KỊCH BẢN 4: SERVER TẮT AN TOÀN & THÔNG BÁO TỚI TOÀN BỘ CLIENT
    # -------------------------------------------------------------------------
    print("\n[KỊCH BẢN 4] Server tắt an toàn (Shutdown) và dọn dẹp toàn bộ tài nguyên...")
    client_live = MockSocket()
    server.clients[client_live] = {"username": "User_Dang_Online", "avatar": "default.png"}

    # Gọi hàm tắt Server
    server.stop()

    # Kiểm tra: Client phải nhận được gói server_shutdown trước khi socket bị đóng
    sent_live = [json.loads(p.decode('utf-8').strip()) for p in client_live.sent]
    has_shutdown_pkt = any(p.get("type") == "server_shutdown" for p in sent_live)
    assert has_shutdown_pkt, "Client phải nhận được thông báo server_shutdown để chủ động xử lý!"
    assert len(server.clients) == 0, "Toàn bộ clients phải được xóa sạch rác khi tắt server!"
    assert client_live.is_closed is True, "Tất cả socket con phải được đóng an toàn!"
    print("=> XÁC NHẬN [Kịch bản 4]: Server đóng an toàn, giải phóng 100% tài nguyên!")

    print("\n🎉 [KẾT QUẢ KIỂM THỬ TUẦN 5: TẤT CẢ 4 KỊCH BẢN ĐẠT 100% THÀNH CÔNG!]")


if __name__ == "__main__":
    test_week5_error_handling_and_cleanup()
