import socket
import threading
import time
import psutil

# Cấu hình địa chỉ Server (Khớp với file server_core.py)
HOST = '127.0.0.1'
PORT = 5000

def simulate_single_client(client_id):
    """Hàm giả lập 1 user kết nối và gửi tin nhắn"""
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((HOST, PORT))
        
        # Gửi 1 tin nhắn rác để ép Server phải xử lý
        msg = f'{{"type": "login", "username": "user_ao_{client_id}"}}'
        client.sendall(msg.encode('utf-8'))
        
        # Giữ kết nối trong 2 giây rồi ngắt
        time.sleep(2)
        client.close()
    except ConnectionRefusedError:
        print(f"[Lỗi] User {client_id} không thể kết nối (Server chưa bật?)")
    except Exception as e:
        pass

def run_stress_test(num_users):
    """Hàm chạy test với số lượng user chỉ định và đo RAM/CPU"""
    print(f"\n{'='*40}")
    print(f"🚀 BẮT ĐẦU TEST TẢI VỚI {num_users} USERS")
    
    # 1. Đo tài nguyên TRƯỚC khi test
    cpu_before = psutil.cpu_percent(interval=1)
    ram_before = psutil.virtual_memory().percent
    print(f"[-] TRƯỚC TEST -> CPU: {cpu_before}% | RAM: {ram_before}%")

    threads = []
    start_time = time.time()

    # 2. Bắn hàng loạt luồng (thread) ảo cùng lúc vào Server
    for i in range(num_users):
        t = threading.Thread(target=simulate_single_client, args=(i,))
        threads.append(t)
        t.start()

    # Đợi toàn bộ user ảo chạy xong
    for t in threads:
        t.join()

    # 3. Đo tài nguyên SAU khi test
    cpu_after = psutil.cpu_percent(interval=0.1)
    ram_after = psutil.virtual_memory().percent
    
    print(f"[+] SAU TEST   -> CPU: {cpu_after}% | RAM: {ram_after}%")
    print(f"⏱️ THỜI GIAN HOÀN THÀNH: {round(time.time() - start_time, 2)} giây")
    print(f"{'='*40}")

if __name__ == "__main__":
    print("Đang khởi động kịch bản Stress Test...")
    
    # Test ở mức tải thấp: 10 User
    run_stress_test(num_users=10)
    
    time.sleep(3) # Nghỉ 3 giây cho Server thở
    
    # Test ở mức tải cao: 50 User
    run_stress_test(num_users=50)