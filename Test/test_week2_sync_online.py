import socket  # Thư viện socket mạng TCP chuẩn của Python
import json  # Thư viện làm việc với định dạng dữ liệu JSON
import time  # Thư viện time để tạo độ trễ giữa các hành động
import sys  # Thư viện hệ thống để chỉnh bảng mã UTF-8 cho Console

# Đảm bảo hiển thị tiếng Việt có dấu rõ ràng trên Console Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


def send_packet(sock, data_dict):
    """Gửi một gói tin JSON có dấu '\\n' ở cuối qua socket"""
    msg = json.dumps(data_dict, ensure_ascii=False) + "\n"
    sock.sendall(msg.encode('utf-8'))


def recv_packet(sock):
    """Nhận và giải mã một gói tin JSON từ socket"""
    data = sock.recv(1024).decode('utf-8')
    if data:
        line = data.strip().split("\n")[0]
        return json.loads(line)
    return None


def run_week2_test():
    server_ip = "127.0.0.1"  # Địa chỉ IP của Server
    server_port = 5000       # Cổng của Server

    print("==========================================================")
    print(" KỊCH BẢN KIỂM THỬ ĐỒNG BỘ DANH SÁCH ONLINE (TUẦN 2)")
    print("==========================================================")

    try:
        # 1. Khởi tạo Client B (Gia Bân) kết nối vào trước
        print("\n[BƯỚC 1] Khởi tạo Client B (Tên: 'Gia Bân') kết nối tới Server...")
        client_b = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_b.connect((server_ip, server_port))

        # Client B gửi gói login
        send_packet(client_b, {"type": "login", "username": "Gia Bân"})
        ack_b = recv_packet(client_b)
        print(f"-> [Client B nhận ACK]: {ack_b}")
        print(f"   Danh sách online lúc này của Client B: {ack_b.get('online_users')}")

        time.sleep(1)

        # 2. Khởi tạo Client A (Thuận Trí) kết nối vào sau
        print("\n[BƯỚC 2] Khởi tạo Client A (Tên: 'Thuận Trí') kết nối tới Server...")
        client_a = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_a.connect((server_ip, server_port))

        # Client A gửi gói login
        send_packet(client_a, {"type": "login", "username": "Thuận Trí"})
        ack_a = recv_packet(client_a)
        print(f"-> [Client A nhận ACK]: {ack_a}")
        print(f"   Danh sách online lúc này của Client A: {ack_a.get('online_users')}")

        # 3. Kiểm tra xem Client B có nhận được broadcast danh sách mới không
        print("\n[BƯỚC 3] Kiểm tra Client B có nhận được gói broadcast không...")
        broadcast_to_b = recv_packet(client_b)
        print(f"-> [Client B nhận BROADCAST]: {broadcast_to_b}")

        # Đánh giá kết quả kiểm thử
        if broadcast_to_b and "online_users" in broadcast_to_b:
            users = broadcast_to_b["online_users"]
            if "Thuận Trí" in users and "Gia Bân" in users:
                print("\n🎉 [KẾT QUẢ: THÀNH CÔNG RỰC RỠ!]")
                print("   Cơ chế broadcast đồng bộ danh sách online của Tuần 2 hoạt động chính xác 100%!")
            else:
                print("\n⚠️ [KẾT QUẢ: CHƯA ĐẦY ĐỦ]")
        else:
            print("\n❌ [KẾT QUẢ: THẤT BẠI] Client B không nhận được broadcast.")

        # Đóng các kết nối client
        client_a.close()
        client_b.close()
        print("\nĐã đóng các kết nối test.")

    except ConnectionRefusedError:
        print("[-] Lỗi: Không thể kết nối tới Server! Bạn cần bật server_core.py trước.")
    except Exception as e:
        print(f"[-] Lỗi trong quá trình test: {e}")


if __name__ == "__main__":



    
    run_week2_test()
