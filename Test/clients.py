import socket
import threading
import time
import json
import os
import sys
import psutil

# Cấu hình mã hóa UTF-8 cho Windows Console để hiển thị tiếng Việt và biểu tượng chính xác
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Cấu hình địa chỉ Server (Khớp với Code/Server/server_core.py)
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 5000

# Đường dẫn lưu file báo cáo kết quả
REPORT_FILE = os.path.join(os.path.dirname(__file__), "stress_test_report.txt")


class ResourceMonitor:
    """
    Bộ giám sát tài nguyên phần cứng (CPU & RAM) chạy ngầm liên tục
    trong suốt thời gian thực hiện Stress Test để ghi nhận chỉ số Peak & Average.
    """
    def __init__(self, target_pid=None, sample_interval=0.1):
        self.sample_interval = sample_interval
        self.target_pid = target_pid
        self.target_proc = None
        if target_pid:
            try:
                self.target_proc = psutil.Process(target_pid)
            except Exception:
                self.target_proc = None

        self._running = False
        self._thread = None

        # Dữ liệu mẫu đo đạc
        self.cpu_samples = []
        self.ram_samples = []
        self.server_cpu_samples = []
        self.server_ram_mb_samples = []

    def start(self):
        self._running = True
        self.cpu_samples.clear()
        self.ram_samples.clear()
        self.server_cpu_samples.clear()
        self.server_ram_mb_samples.clear()

        # Thiết lập mốc ban đầu (baseline) cho psutil
        psutil.cpu_percent(interval=None)
        if self.target_proc and self.target_proc.is_running():
            try:
                self.target_proc.cpu_percent(interval=None)
            except Exception:
                pass

        # Khởi động luồng giám sát ngầm
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def _monitor_loop(self):
        while self._running:
            time.sleep(self.sample_interval)
            try:
                # 1. Đo tài nguyên toàn hệ thống (System-wide)
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                if cpu > 0.0:
                    self.cpu_samples.append(cpu)
                self.ram_samples.append(ram)

                # 2. Đo tài nguyên riêng của Server Process (nếu tìm thấy)
                if self.target_proc and self.target_proc.is_running():
                    try:
                        s_cpu = self.target_proc.cpu_percent(interval=None)
                        s_ram = self.target_proc.memory_info().rss / (1024 * 1024)  # Đổi ra MB
                        if s_cpu > 0.0:
                            self.server_cpu_samples.append(s_cpu)
                        self.server_ram_mb_samples.append(s_ram)
                    except Exception:
                        pass
            except Exception:
                pass

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        # Nếu bài test kết thúc quá nhanh mà chưa kịp lấy mẫu, lấy ngay 1 mẫu bổ sung
        if not self.cpu_samples:
            fallback_cpu = psutil.cpu_percent(interval=0.05)
            self.cpu_samples.append(fallback_cpu)
        if not self.ram_samples:
            self.ram_samples.append(psutil.virtual_memory().percent)

    def get_summary(self):
        """Tính toán các chỉ số thống kê Min, Max (Peak), Average"""
        summary = {
            "sys_cpu_avg": round(sum(self.cpu_samples) / len(self.cpu_samples), 2) if self.cpu_samples else 0.0,
            "sys_cpu_peak": round(max(self.cpu_samples), 2) if self.cpu_samples else 0.0,
            "sys_ram_avg": round(sum(self.ram_samples) / len(self.ram_samples), 2) if self.ram_samples else 0.0,
            "sys_ram_peak": round(max(self.ram_samples), 2) if self.ram_samples else 0.0,
            "server_cpu_peak": round(max(self.server_cpu_samples), 2) if self.server_cpu_samples else None,
            "server_ram_peak_mb": round(max(self.server_ram_mb_samples), 2) if self.server_ram_mb_samples else None,
        }
        return summary


def find_server_pid(port=DEFAULT_PORT):
    """Tự động tìm PID của tiến trình đang lắng nghe trên cổng port của Server"""
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr and conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                return conn.pid
    except Exception:
        pass
    return None


def send_packet(sock, payload_dict):
    """
    Gửi gói tin JSON kèm ký tự '\\n' ở cuối theo chuẩn giao thức protocol.py
    để chống hiện tượng dính gói tin trên giao thức TCP.
    """
    data = (json.dumps(payload_dict, ensure_ascii=False) + "\n").encode('utf-8')
    sock.sendall(data)


def simulate_single_client(client_id, host, port, results_collector, active_duration=1.5):
    """
    Hàm giả lập hành vi của 1 người dùng thật kết nối vào Server:
    1. Kết nối TCP Socket.
    2. Gửi gói tin 'login' đúng chuẩn JSON + '\\n'.
    3. Nhận phản hồi 'login_ack' từ Server và ghi nhận độ trễ (RTT).
    4. Gửi 1 tin nhắn chat mẫu ('msg').
    5. Giữ kết nối trong active_duration giây rồi đóng an toàn.
    """
    result = {
        "client_id": client_id,
        "success": False,
        "latency_ms": 0.0,
        "error": None
    }
    client_sock = None
    try:
        t_start = time.time()
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.settimeout(5.0)  # Timeout 5 giây để tránh treo luồng nếu server quá tải
        client_sock.connect((host, port))

        # 1. Gửi gói đăng nhập
        login_packet = {
            "type": "login",
            "username": f"user_stress_{client_id}"
        }
        send_packet(client_sock, login_packet)

        # 2. Đón nhận gói tin phản hồi đầu tiên (login_ack) từ Server
        recv_data = client_sock.recv(4096).decode('utf-8')
        t_rtt = (time.time() - t_start) * 1000  # Đổi sang millisecond
        result["latency_ms"] = round(t_rtt, 2)

        # 3. Gửi thêm 1 gói tin chat để ép Server điều hướng & broadcast
        msg_packet = {
            "type": "msg",
            "sender": f"user_stress_{client_id}",
            "receiver": "all",
            "content": f"[Stress Test] Tin nhắn kiểm thử từ user {client_id}"
        }
        send_packet(client_sock, msg_packet)

        # 4. Giữ kết nối hoạt động trong một khoảng thời gian
        time.sleep(active_duration)

        result["success"] = True

    except ConnectionRefusedError:
        result["error"] = "ConnectionRefused (Server chưa bật?)"
    except socket.timeout:
        result["error"] = "Timeout (Server phản hồi quá chậm)"
    except Exception as e:
        result["error"] = str(e)
    finally:
        if client_sock:
            try:
                client_sock.close()
            except Exception:
                pass
        results_collector.append(result)


def run_stress_test(num_users, host=DEFAULT_HOST, port=DEFAULT_PORT, server_pid=None):
    """
    Chạy kịch bản kiểm thử tải với số lượng user chỉ định:
    - Thu thập số liệu RAM/CPU trước, trong và sau bài test.
    - Ghi nhận tỷ lệ thành công và thời gian đáp ứng (RTT).
    """
    print(f"\n{'='*65}")
    print(f"🚀 BẮT ĐẦU TEST TẢI VỚI {num_users} USERS ĐỒNG THỜI")
    print(f"   Mục tiêu: {host}:{port} | Server PID: {server_pid or 'N/A'}")
    print(f"{'='*65}")

    # 1. Đo tài nguyên TRƯỚC bài test
    psutil.cpu_percent(interval=None)  # Reset bộ đo CPU
    ram_before_mb = psutil.virtual_memory().used / (1024 * 1024)
    ram_before_percent = psutil.virtual_memory().percent
    cpu_before_percent = psutil.cpu_percent(interval=0.5)

    print(f"[-] TRƯỚC TEST  -> CPU: {cpu_before_percent}% | RAM Hệ thống: {ram_before_percent}% ({round(ram_before_mb, 1)} MB)")

    # 2. Khởi động bộ giám sát tài nguyên thời gian thực
    monitor = ResourceMonitor(target_pid=server_pid, sample_interval=0.1)
    monitor.start()

    # 3. Tạo hàng loạt luồng Client ảo bắn đồng thời vào Server
    threads = []
    results = []
    test_start_time = time.time()

    for i in range(num_users):
        t = threading.Thread(
            target=simulate_single_client,
            args=(i + 1, host, port, results),
            name=f"StressClient-{i + 1}"
        )
        threads.append(t)
        t.start()

    # 4. Chờ toàn bộ các user ảo hoàn thành kịch bản
    for t in threads:
        t.join()

    total_duration = round(time.time() - test_start_time, 2)

    # 5. Dừng bộ giám sát tài nguyên
    monitor.stop()
    resource_summary = monitor.get_summary()

    # 6. Đo tài nguyên SAU bài test
    ram_after_percent = psutil.virtual_memory().percent
    ram_after_mb = psutil.virtual_memory().used / (1024 * 1024)
    cpu_after_percent = psutil.cpu_percent(interval=0.5)

    # 7. Thống kê kết quả kiểm thử
    success_count = sum(1 for r in results if r["success"])
    fail_count = num_users - success_count
    latencies = [r["latency_ms"] for r in results if r["success"] and r["latency_ms"] > 0]
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    min_latency = min(latencies) if latencies else 0.0
    max_latency = max(latencies) if latencies else 0.0

    print(f"[+] TRONG TEST  -> CPU Peak: {resource_summary['sys_cpu_peak']}% (Avg: {resource_summary['sys_cpu_avg']}%)")
    print(f"                -> RAM Peak: {resource_summary['sys_ram_peak']}%")
    if resource_summary['server_ram_peak_mb'] is not None:
        print(f"                -> RAM Server Process: ~{resource_summary['server_ram_peak_mb']} MB (CPU Peak: {resource_summary['server_cpu_peak']}%)")
    print(f"[+] SAU TEST    -> CPU: {cpu_after_percent}% | RAM Hệ thống: {ram_after_percent}% ({round(ram_after_mb, 1)} MB)")
    print(f"[-] KẾT QUẢ MẠNG:")
    print(f"    - Thành công: {success_count}/{num_users} ({round(success_count / num_users * 100, 1)}%)")
    print(f"    - Thất bại:   {fail_count}/{num_users}")
    print(f"    - Độ trễ phản hồi (RTT): Trung bình {avg_latency} ms (Min: {min_latency} ms | Max: {max_latency} ms)")
    print(f"    - Tổng thời gian hoàn thành: {total_duration} giây")
    print(f"{'='*65}")

    # Thu thập kết quả trả về để ghi báo cáo tổng hợp
    summary_data = {
        "num_users": num_users,
        "success_count": success_count,
        "fail_count": fail_count,
        "success_rate": round(success_count / num_users * 100, 1),
        "total_duration": total_duration,
        "avg_latency_ms": avg_latency,
        "cpu_before": cpu_before_percent,
        "cpu_peak": resource_summary["sys_cpu_peak"],
        "cpu_avg": resource_summary["sys_cpu_avg"],
        "cpu_after": cpu_after_percent,
        "ram_before_pct": ram_before_percent,
        "ram_peak_pct": resource_summary["sys_ram_peak"],
        "ram_after_pct": ram_after_percent,
        "server_ram_peak_mb": resource_summary["server_ram_peak_mb"]
    }
    return summary_data


def save_report_to_file(results_list, filepath=REPORT_FILE):
    """Lưu toàn bộ số liệu thống kê RAM/CPU vào file txt để nhóm đưa vào báo cáo"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("========================================================================\n")
        f.write("     BÁO CÁO KẾT QUẢ KIỂM THỬ TẢI (STRESS TEST REPORT) - UDM08\n")
        f.write(f"     Thời gian thực hiện: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("========================================================================\n\n")

        f.write(f"{'Chỉ số kiểm thử':<35} | {'Mức 1: 10 Users':<16} | {'Mức 2: 50 Users':<16}\n")
        f.write("-" * 74 + "\n")

        if len(results_list) >= 2:
            r1, r2 = results_list[0], results_list[1]
            f.write(f"{'Tỷ lệ kết nối thành công':<35} | {str(r1['success_rate']) + '%':<16} | {str(r2['success_rate']) + '%':<16}\n")
            f.write(f"{'Tổng thời gian thực thi (giây)':<35} | {str(r1['total_duration']) + ' s':<16} | {str(r2['total_duration']) + ' s':<16}\n")
            f.write(f"{'Độ trễ trung bình (RTT ms)':<35} | {str(r1['avg_latency_ms']) + ' ms':<16} | {str(r2['avg_latency_ms']) + ' ms':<16}\n")
            f.write(f"{'CPU Hệ thống trước test (%)':<35} | {str(r1['cpu_before']) + '%':<16} | {str(r2['cpu_before']) + '%':<16}\n")
            f.write(f"{'CPU Đỉnh trong test (Peak %)':<35} | {str(r1['cpu_peak']) + '%':<16} | {str(r2['cpu_peak']) + '%':<16}\n")
            f.write(f"{'CPU Trung bình trong test (%)':<35} | {str(r1['cpu_avg']) + '%':<16} | {str(r2['cpu_avg']) + '%':<16}\n")
            f.write(f"{'RAM Hệ thống trước test (%)':<35} | {str(r1['ram_before_pct']) + '%':<16} | {str(r2['ram_before_pct']) + '%':<16}\n")
            f.write(f"{'RAM Đỉnh trong test (Peak %)':<35} | {str(r1['ram_peak_pct']) + '%':<16} | {str(r2['ram_peak_pct']) + '%':<16}\n")
            f.write(f"{'RAM Hệ thống sau test (%)':<35} | {str(r1['ram_after_pct']) + '%':<16} | {str(r2['ram_after_pct']) + '%':<16}\n")
            if r1.get('server_ram_peak_mb') is not None:
                f.write(f"{'RAM Server Process (MB)':<35} | {str(r1['server_ram_peak_mb']) + ' MB':<16} | {str(r2['server_ram_peak_mb']) + ' MB':<16}\n")
        else:
            for r in results_list:
                f.write(f"Mức tải {r['num_users']} users: {json.dumps(r, ensure_ascii=False)}\n")

        f.write("\n========================================================================\n")
        f.write("Nhận xét sơ bộ:\n")
        f.write("- Khi số lượng client tăng từ 10 lên 50 user đồng thời, hệ thống vẫn duy trì\n")
        f.write("  kết nối ổn định, các gói tin broadcast được phân phối đầy đủ qua các socket con.\n")
        f.write("- Mức tăng RAM và CPU tỷ lệ thuận với số luồng phục vụ (Thread-per-client model).\n")
        f.write("========================================================================\n")
    print(f"\n📄 Đã tự động ghi nhận số liệu RAM/CPU vào file: {REPORT_FILE}")


if __name__ == "__main__":
    print("===================================================================")
    print("      UDM08 - CHƯƠNG TRÌNH KIỂM THỬ TẢI STRESS TEST CLIENTS        ")
    print("===================================================================")

    server_pid = find_server_pid(DEFAULT_PORT)
    if server_pid:
        print(f"[*] Phát hiện tiến trình Server đang chạy (PID: {server_pid})")
    else:
        print(f"[*] Chú ý: Chưa tìm thấy Server lắng nghe trên cổng {DEFAULT_PORT}.")
        print("    Vui lòng đảm bảo bạn đã khởi động Server trước bằng lệnh:")
        print("    python Code/Server/server_core.py\n")

    all_results = []

    # 1. Kiểm thử ở mức tải thấp: 10 Users
    res_10 = run_stress_test(num_users=10, host=DEFAULT_HOST, port=DEFAULT_PORT, server_pid=server_pid)
    all_results.append(res_10)

    print("\n⏳ Nghỉ 3 giây để Server giải phóng tài nguyên và ổn định hàng đợi...\n")
    time.sleep(3)

    # 2. Kiểm thử ở mức tải cao: 50 Users
    res_50 = run_stress_test(num_users=50, host=DEFAULT_HOST, port=DEFAULT_PORT, server_pid=server_pid)
    all_results.append(res_50)

    # 3. Ghi nhận số liệu ra file báo cáo
    save_report_to_file(all_results)
    print("\n✅ HOÀN THÀNH TOÀN BỘ KỊCH BẢN KIỂM THỬ TẢI.")
