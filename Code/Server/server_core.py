import socket  # Thư viện mạng chuẩn của Python để làm việc với TCP Socket
import threading  # Thư viện hỗ trợ đa luồng để phục vụ nhiều Client đồng thời
import logging  # Thư viện chuẩn dùng để ghi lại lịch sử sự kiện (log)
from datetime import datetime  # Thư viện lấy ngày giờ hiện tại hệ thống
import sys  # Thư viện hệ thống để cấu hình bảng mã console UTF-8
import os
import json

# Đảm bảo nạp đúng module server_router từ cùng thư mục
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Liên kết module server_router.py (Trương Gia Bân)
from server_router import ServerRouter

# Đảm bảo hiển thị tiếng Việt có dấu mượt mà trên console Windows mà không bị lỗi font/crash
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


class ServerCore:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host  # Địa chỉ IP mà Server lắng nghe (0.0.0.0 nghĩa là chấp nhận mọi card mạng)
        self.port = port  # Cổng mạng (Port) để Client kết nối tới
        self.server_socket = None  # Biến lưu trữ đối tượng Socket chính của Server
        self.is_running = False  # Cờ (Flag) kiểm soát trạng thái chạy/dừng của Server
        self.clients = {}  # Quản lý client {client_socket: username} để phục vụ Tuần 2
        self.lock = threading.Lock()  # Khóa bảo vệ danh sách client khi thao tác đa luồng

        # Liên kết router để parse và đánh số tin nhắn JSON
        self.router = ServerRouter()

        self.setup_logger()  # Gọi hàm cấu hình hệ thống ghi log ngay khi khởi tạo

    def setup_logger(self):
        """Thiết lập ghi log ra cả màn hình Console và lưu vào file server.log"""
        log_format = "%(asctime)s - [%(levelname)s] - (%(threadName)s) - %(message)s"
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler("server.log", encoding="utf-8"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger("ServerCore")

    def broadcast(self, packet_dict):
        """Gửi thông điệp tới tất cả Client đang kết nối"""
        payload = json.dumps(packet_dict, ensure_ascii=False) + "\n"
        data_bytes = payload.encode('utf-8')
        with self.lock:
            for sock in list(self.clients.keys()):
                try:
                    sock.sendall(data_bytes)
                except Exception:
                    pass

    def broadcast_online_list(self):
        """
        Cơ chế đồng bộ danh sách online (Tuần 2):
        Gửi broadcast danh sách user online mới nhất cho tất cả các Client
        """
        with self.lock:
            online_users = list(self.clients.values())
        packet = {
            "type": "online_list",
            "users": online_users
        }
        self.broadcast(packet)
        self.logger.info(f"Đã broadcast danh sách online ({len(online_users)} users): {online_users}")

    def start(self):
        """Khởi động TCP Socket Server và bắt đầu lắng nghe kết nối"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)

            self.is_running = True
            self.logger.info(f"Server đã khởi động thành công trên cổng {self.port} (IP: {self.host})")

            # Bắt đầu vòng lặp đón nhận Client
            self.accept_clients()

        except Exception as e:
            self.logger.error(f"Lỗi khởi động Server: {e}")
        finally:
            self.stop()

    def accept_clients(self):
        """Vòng lặp chấp nhận kết nối từ các Client mới"""
        self.logger.info("Đang chờ Client kết nối tới...")

        while self.is_running:
            try:
                client_socket, client_address = self.server_socket.accept()
                self.logger.info(f"Client mới kết nối thành công từ địa chỉ: {client_address}")

                # Gán tên tạm thời cho client
                default_name = f"User_{client_address[1]}"
                with self.lock:
                    self.clients[client_socket] = default_name

                # Tạo luồng xử lý riêng cho Client này
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address),
                    name=f"Thread-{client_address[1]}"
                )
                client_thread.daemon = True
                client_thread.start()

                # Gửi ngay danh sách online hiện tại cho mọi người
                self.broadcast_online_list()

            except Exception as e:
                if self.is_running:
                    self.logger.error(f"Lỗi khi tiếp nhận kết nối Client: {e}")
                break

    def handle_client(self, client_socket, client_address):
        """Hàm chạy trên luồng riêng để lắng nghe dữ liệu từ 1 Client cụ thể"""
        try:
            # Gửi lời chào mừng ban đầu tới Client dạng JSON
            welcome_data = json.dumps({"type": "msg", "sender": "Hệ thống", "content": "Chào mừng bạn đến với UDM08 Chat Server!"}, ensure_ascii=False) + "\n"
            client_socket.sendall(welcome_data.encode('utf-8'))

            buffer = ""
            while self.is_running:
                data = client_socket.recv(4096)
                if not data:
                    self.logger.info(f"Client {client_address} đã ngắt kết nối.")
                    break

                buffer += data.decode('utf-8')
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    self.logger.info(f"Nhận từ {client_address}: {line}")

                    try:
                        parsed_msg = self.router.parse_message(line)
                        msg_type = parsed_msg.get("type", "")

                        # Xử lý gói tin đăng ký tên (login) -> Cập nhật danh sách online
                        if msg_type == "login":
                            username = parsed_msg.get("username", "").strip()
                            if username:
                                with self.lock:
                                    self.clients[client_socket] = username
                                self.logger.info(f"Client {client_address} cập nhật username: {username}")
                                self.broadcast_online_list()

                        # Xử lý gói tin nhắn chat -> Broadcast cho tất cả Client cùng phòng
                        elif msg_type == "msg":
                            self.broadcast(parsed_msg)

                        else:
                            # Phản hồi lại gói tin cho client
                            reply = json.dumps(parsed_msg, ensure_ascii=False) + "\n"
                            client_socket.sendall(reply.encode('utf-8'))

                    except Exception as e:
                        # Fallback tin nhắn thường
                        echo_payload = {"type": "msg", "sender": "Server Echo", "content": line}
                        reply = json.dumps(echo_payload, ensure_ascii=False) + "\n"
                        client_socket.sendall(reply.encode('utf-8'))

        except ConnectionResetError:
            self.logger.warning(f"Client {client_address} bị ngắt kết nối đột ngột (Connection Reset)!")
        except Exception as e:
            self.logger.error(f"Lỗi xử lý Client {client_address}: {e}")
        finally:
            with self.lock:
                if client_socket in self.clients:
                    left_name = self.clients.pop(client_socket)
                    self.logger.info(f"Đã giải phóng tài nguyên của {left_name} ({client_address}).")
            
            try:
                client_socket.close()
            except Exception:
                pass

            # Đồng bộ lại danh sách online sau khi 1 Client rời đi
            self.broadcast_online_list()

    def stop(self):
        """Dừng Server và giải phóng toàn bộ tài nguyên Socket"""
        self.is_running = False
        with self.lock:
            for client in self.clients.keys():
                try:
                    client.close()
                except Exception:
                    pass
            self.clients.clear()

        if self.server_socket:
            try:
                self.server_socket.close()
                self.logger.info("Đã đóng Socket Server.")
            except Exception as e:
                self.logger.error(f"Lỗi khi đóng Socket Server: {e}")


if __name__ == "__main__":
    PORT = 5000
    HOST = "127.0.0.1"

    server = ServerCore(host=HOST, port=PORT)
    print("=== UDM_08 TCP SERVER CORE (TUẦN 2: ONLINE SYNC) ===")
    print("Server đang chạy. Nhấn Ctrl + C để dừng Server.\n")

    try:
        server.start()
    except KeyboardInterrupt:
        print("\nĐang tắt Server an toàn...")
        server.stop()
