<<<<<<< HEAD
import socket  # Thư viện socket mạng TCP chuẩn của Python
import threading  # Thư viện đa luồng để phục vụ nhiều Client đồng thời
import json  # Thư viện làm việc với định dạng dữ liệu JSON
import logging  # Thư viện ghi log lịch sử hoạt động của hệ thống
import sys  # Thư viện hệ thống để chỉnh bảng mã UTF-8 cho Console
import os  # Thư viện thao tác với đường dẫn thư mục hệ thống

# Đảm bảo hiển thị tiếng Việt có dấu rõ ràng trên Console Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # Cấu hình chuẩn đầu ra UTF-8
        sys.stderr.reconfigure(encoding='utf-8')  # Cấu hình chuẩn báo lỗi UTF-8
=======
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
>>>>>>> fdfc9ac0e26b68b54271e13a6de8810c8a6b4904
    except Exception:
        pass


class ServerCore:
    def __init__(self, host="0.0.0.0", port=5000):
<<<<<<< HEAD
        # Địa chỉ IP của Server (0.0.0.0 chấp nhận kết nối từ mọi card mạng)
        self.host = host
        # Cổng mạng Port mà Server lắng nghe kết nối
        self.port = port
        # Biến lưu trữ socket chính của Server
        self.server_socket = None
        # Cờ đánh dấu Server đang chạy hay đã dừng
        self.is_running = False

        # --- YÊU CẦU TUẦN 2: QUẢN LÝ DANH SÁCH CLIENT ONLINE ---
        # Dictionary lưu trữ các client đang kết nối: {client_socket: username}
        self.clients = {}
        # Khóa Lock để tránh xung đột dữ liệu khi nhiều luồng cùng thao tác trên dictionary clients
        self.lock = threading.Lock()

        # Thiết lập cấu hình hệ thống ghi log
        self.setup_logger()

    def setup_logger(self):
        """Cấu hình ghi log ra cả màn hình Console và lưu vào file server.log"""
        # Định dạng dòng log: Thời gian - Cấp độ log - Tên luồng - Nội dung log
        log_format = "%(asctime)s - [%(levelname)s] - (%(threadName)s) - %(message)s"
        # Cài đặt cấu hình logging
        logging.basicConfig(
            level=logging.INFO,  # Ghi nhận các log từ mức INFO trở lên
            format=log_format,  # Áp dụng mẫu định dạng đã tạo
            handlers=[
                logging.FileHandler("server.log", encoding="utf-8"),  # Lưu vào file server.log (chuẩn UTF-8)
                logging.StreamHandler(sys.stdout)  # Đồng thời in ra màn hình Console
            ]
        )
        # Lấy đối tượng logger để sử dụng trong toàn class
        self.logger = logging.getLogger("ServerCore")

    def get_online_users(self):
        """Lấy danh sách tên (username) của các Client đang online hiện tại"""
        # Sử dụng khóa lock để đảm bảo việc đọc danh sách an toàn trong môi trường đa luồng
        with self.lock:
            # Lấy tất cả giá trị (username) trong dictionary clients và chuyển thành dạng list
            return list(self.clients.values())

    def send_packet(self, client_socket, packet_dict):
        """Hàm gửi 1 gói tin JSON (kèm ký tự '\\n' ở cuối) tới 1 Client cụ thể"""
        try:
            # Chuyển Dictionary thành chuỗi JSON (giữ nguyên tiếng Việt có dấu)
            json_str = json.dumps(packet_dict, ensure_ascii=False)
            # Thêm ký tự '\\n' ở cuối gói tin để chống dính gói tin TCP
            data_to_send = (json_str + "\n").encode('utf-8')
            # Gửi dữ liệu qua socket
            client_socket.sendall(data_to_send)
            return True
        except Exception as e:
            # Ghi log nếu xảy ra lỗi khi gửi
            self.logger.error(f"Lỗi khi gửi dữ liệu tới Client: {e}")
            return False

    def broadcast_online_list(self, exclude_socket=None):
        """
        Gửi broadcast danh sách online mới nhất tới các Client khác.
        exclude_socket: socket của Client vừa vào (được bỏ qua để không gửi lặp cho người này).
        """
        # Lấy danh sách tên tất cả người dùng đang online tại thời điểm hiện tại
        online_users = self.get_online_users()

        # Đóng gói thông tin danh sách online theo định dạng chuẩn JSON
        packet = {
            "type": "user_list",  # Loại gói tin là danh sách người dùng
            "action": "update",  # Hành động: cập nhật danh sách
            "online_users": online_users  # Danh sách mảng các username đang online
        }

        # Ghi log server việc thực hiện broadcast danh sách online
        self.logger.info(f"[BROADCAST] Gửi danh sách online {online_users} tới các client khác...")

        # Dùng khóa lock để sao chép danh sách các socket cần gửi nhằm tránh lỗi luồng
        with self.lock:
            target_clients = list(self.clients.keys())

        # Duyệt qua từng client đang kết nối với Server
        for sock in target_clients:
            # Nếu socket này chính là client vừa vào (exclude_socket) thì bỏ qua
            if sock == exclude_socket:
                continue
            # Gửi gói tin cập nhật danh sách online cho các client khác
            self.send_packet(sock, packet)
=======
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
>>>>>>> fdfc9ac0e26b68b54271e13a6de8810c8a6b4904

    def start(self):
        """Khởi động TCP Socket Server và bắt đầu lắng nghe kết nối"""
        try:
<<<<<<< HEAD
            # Khởi tạo TCP socket với IPv4 (AF_INET) và giao thức TCP (SOCK_STREAM)
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Cho phép sử dụng lại địa chỉ IP/Port ngay lập tức khi restart server
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Gán IP và Port cho socket chính của Server
            self.server_socket.bind((self.host, self.port))
            # Đưa Server vào trạng thái lắng nghe (hàng đợi tối đa 10 kết nối chờ)
            self.server_socket.listen(10)

            # Đánh dấu cờ Server đang hoạt động
            self.is_running = True
            self.logger.info(f"Server đã khởi động thành công trên cổng {self.port} (IP: {self.host})")

            # Bắt đầu vòng lặp đón nhận kết nối từ các Client
            self.accept_clients()

        except Exception as e:
            # Ghi nhận log nếu Server khởi động thất bại
            self.logger.error(f"Lỗi khởi động Server: {e}")
        finally:
            # Đảm bảo giải phóng tài nguyên khi dừng Server
            self.stop()

    def accept_clients(self):
        """Vòng lặp đón nhận từng Client mới kết nối tới Server"""
        self.logger.info("Đang chờ Client kết nối tới...")

        # Vòng lặp liên tục chừng nào Server còn đang chạy
        while self.is_running:
            try:
                # Hàm accept() tạm dừng chờ cho đến khi có một Client kết nối tới
                client_socket, client_address = self.server_socket.accept()
                # Ghi log khi có Client mới kết nối thành công kèm IP và Port
                self.logger.info(f"Client mới kết nối thành công từ địa chỉ: {client_address}")

                # Tạo một luồng (Thread) riêng biệt để xử lý dữ liệu cho Client này
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address),
                    name=f"Thread-{client_address[1]}"  # Đặt tên luồng theo số Port để dễ theo dõi log
                )
                # Đặt luồng daemon để khi Server tắt thì các luồng con tự động tắt theo
                client_thread.daemon = True
                # Bắt đầu kích hoạt luồng xử lý riêng cho Client
                client_thread.start()

            except Exception as e:
                # Nếu Server đang chạy mà gặp lỗi accept thì ghi nhận log
=======
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
>>>>>>> fdfc9ac0e26b68b54271e13a6de8810c8a6b4904
                if self.is_running:
                    self.logger.error(f"Lỗi khi tiếp nhận kết nối Client: {e}")
                break

    def handle_client(self, client_socket, client_address):
<<<<<<< HEAD
        """Hàm chạy trên luồng riêng để xử lý giao tiếp với 1 Client cụ thể"""
        # Biến lưu tên người dùng của client này (mặc định ban đầu là None)
        current_username = None
        # Bộ đệm string để tích lũy dữ liệu nhận được và cắt theo dấu xuống dòng '\\n'
        buffer = ""

        try:
            # Vòng lặp liên tục lắng nghe dữ liệu từ Client khi Server đang chạy
            while self.is_running:
                # Nhận tối đa 1024 bytes dữ liệu từ socket
                data = client_socket.recv(1024)

                # Nếu dữ liệu rỗng (b''), Client đã chủ động ngắt kết nối
                if not data:
                    self.logger.info(f"Client {client_address} ({current_username}) đã ngắt kết nối.")
                    break

                # Giải mã dữ liệu byte nhận được thành chuỗi UTF-8 và nối vào bộ đệm
                buffer += data.decode('utf-8')

                # Tách và xử lý từng gói tin phân cách bởi ký tự '\\n' (chống dính gói tin TCP)
                while "\n" in buffer:
                    # Tách lấy 1 gói tin đầu tiên, phần còn lại giữ lại trong buffer
                    packet_str, buffer = buffer.split("\n", 1)
                    # Xóa khoảng trắng thừa ở 2 đầu chuỗi
                    packet_str = packet_str.strip()

                    # Nếu gói tin rỗng thì bỏ qua
                    if not packet_str:
                        continue

                    # Thử phân tích chuỗi vừa nhận thành Dictionary JSON
                    try:
                        message_dict = json.loads(packet_str)
                    except json.JSONDecodeError:
                        # Ghi cảnh báo nếu dữ liệu nhận được không đúng định dạng JSON
                        self.logger.warning(f"Nhận chuỗi không phải JSON từ {client_address}: {packet_str}")
                        continue

                    # Lấy loại gói tin (type)
                    msg_type = message_dict.get("type")

                    # --- YÊU CẦU TUẦN 2: XỬ LÝ KHI CLIENT A VÀO VÀ ĐỒNG BỘ DANH SÁCH ONLINE ---
                    if msg_type == "login":
                        # Lấy username do client gửi lên (nếu không có thì đặt tên tạm theo Port)
                        current_username = message_dict.get("username", f"User_{client_address[1]}")

                        # Khóa lock để lưu Client và username vào danh sách quản lý
                        with self.lock:
                            self.clients[client_socket] = current_username

                        # Ghi log sự kiện Client A đăng nhập thành công
                        self.logger.info(f"==> Client A [{current_username}] đã vào hệ thống.")

                        # 1. Gửi gói 'login_ack' xác nhận cho CHÍNH Client A (kèm danh sách online hiện tại)
                        login_ack_packet = {
                            "type": "login_ack",
                            "status": "success",
                            "username": current_username,
                            "online_users": self.get_online_users()
                        }
                        self.send_packet(client_socket, login_ack_packet)
                        self.logger.info(f"Đã gửi login_ack cho [{current_username}].")

                        # 2. Gửi broadcast danh sách online mới nhất cho CÁC CLIENT KHÁC
                        self.broadcast_online_list(exclude_socket=client_socket)

                    # Xử lý các loại gói tin khác (ví dụ tin nhắn thường, ping,...)
                    else:
                        self.logger.info(f"Nhận tin nhắn loại '{msg_type}' từ [{current_username}]: {message_dict}")

        except ConnectionResetError:
            # Xử lý khi Client bị tắt đột ngột (rút dây mạng, tắt cửa sổ ngang)
            self.logger.warning(f"Client {client_address} ({current_username}) bị ngắt kết nối đột ngột!")
        except Exception as e:
            # Ghi nhận các lỗi ngoại lệ khác
            self.logger.error(f"Lỗi xử lý Client {client_address} ({current_username}): {e}")
        finally:
            # KHỐI DỌN DẸP KHI CLIENT THOÁT:
            with self.lock:
                # Xóa client khỏi danh sách quản lý online
                if client_socket in self.clients:
                    del self.clients[client_socket]

            # Đóng kết nối socket của client này
=======
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
            
>>>>>>> fdfc9ac0e26b68b54271e13a6de8810c8a6b4904
            try:
                client_socket.close()
            except Exception:
                pass

<<<<<<< HEAD
            self.logger.info(f"Đã giải phóng tài nguyên của [{current_username}] ({client_address}).")

            # Nếu client đã đăng nhập rời đi, broadcast lại danh sách online mới cho các client còn lại
            if current_username:
                self.broadcast_online_list()

    def stop(self):
        """Dừng Server và giải phóng toàn bộ tài nguyên socket"""
        # Đánh dấu cờ dừng server
        self.is_running = False

        # Khóa lock để đóng toàn bộ socket của các client đang online
        with self.lock:
            for sock in self.clients.keys():
                try:
                    sock.close()
                except Exception:
                    pass
            # Xóa rỗng danh sách client
            self.clients.clear()

        # Đóng socket chính của Server
        if self.server_socket:
            try:
                self.server_socket.close()
                self.logger.info("Đã đóng Socket Server chính.")
            except Exception as e:
                self.logger.error(f"Lỗi khi đóng Socket Server chính: {e}")


# Điểm chạy chương trình khi file này được thực thi trực tiếp
if __name__ == "__main__":
    PORT = 5000  # Cổng mạng quy định cho Server
    HOST = "127.0.0.1"  # Chạy thử nghiệm trên máy local (localhost)

    # Khởi tạo đối tượng ServerCore
    server = ServerCore(host=HOST, port=PORT)

    print("=== UDM_08 TCP SERVER CORE (TUẦN 2 - ĐỒNG BỘ DANH SÁCH ONLINE) ===")
    print("Server đang chạy. Nhấn Ctrl + C để dừng Server.\n")

    try:
        # Bắt đầu chạy server
        server.start()
    except KeyboardInterrupt:
        # Xử lý khi người dùng nhấn tổ hợp Ctrl + C để dừng an toàn
=======
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
>>>>>>> fdfc9ac0e26b68b54271e13a6de8810c8a6b4904
        print("\nĐang tắt Server an toàn...")
        server.stop()
