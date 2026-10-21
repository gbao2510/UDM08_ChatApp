import socket  # Thư viện mạng chuẩn của Python để làm việc với TCP Socket
import threading  # Thư viện hỗ trợ đa luồng để phục vụ nhiều Client đồng thời
import logging  # Thư viện chuẩn dùng để ghi lại lịch sử sự kiện (log)
from datetime import datetime  # Thư viện lấy ngày giờ hiện tại hệ thống
import sys  # Thư viện hệ thống để cấu hình bảng mã console UTF-8

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
        self.clients = []  # Danh sách tạm lưu trữ các socket của Client đang kết nối

        self.setup_logger()  # Gọi hàm cấu hình hệ thống ghi log ngay khi khởi tạo

    def setup_logger(self):
        """Thiết lập ghi log ra cả màn hình Console và lưu vào file server.log"""
        # Định dạng dòng log: [Thời gian] [Cấp độ LOG] [Tên luồng] Nội dung thông điệp
        log_format = "%(asctime)s - [%(levelname)s] - (%(threadName)s) - %(message)s"

        # Cấu hình logging cơ bản
        logging.basicConfig(
            level=logging.INFO,  # Ghi nhận các log từ mức INFO trở lên (INFO, WARNING, ERROR)
            format=log_format,  # Áp dụng định dạng dòng log đã định nghĩa ở trên
            handlers=[
                logging.FileHandler("server.log", encoding="utf-8"),  # Ghi log ra file server.log (hỗ trợ tiếng Việt)
                logging.StreamHandler(sys.stdout)  # Đồng thời in trực tiếp dòng log ra màn hình Console (chuẩn UTF-8)
            ]
        )
        self.logger = logging.getLogger("ServerCore")  # Lấy đối tượng logger để sử dụng trong toàn class

    def start(self):
        """Khởi động TCP Socket Server và bắt đầu lắng nghe kết nối"""
        try:
            # Tạo TCP Socket: AF_INET (IPv4), SOCK_STREAM (giao thức TCP tin cậy)
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Cho phép tái sử dụng lại địa chỉ IP/Port ngay lập tức khi restart server (tránh lỗi Address already in use)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Gán Socket với địa chỉ IP và Port đã chỉ định
            self.server_socket.bind((self.host, self.port))

            # Đưa Socket vào trạng thái lắng nghe kết nối từ Client (cho phép hàng đợi tối đa 10 kết nối chờ)
            self.server_socket.listen(10)

            self.is_running = True  # Đánh dấu Server bắt đầu hoạt động
            self.logger.info(f"Server đã khởi động thành công trên cổng {self.port} (IP: {self.host})")

            # Bắt đầu vòng lặp đón nhận các Client kết nối tới
            self.accept_clients()

        except Exception as e:
            # Bắt và ghi lại lỗi nếu không thể mở cổng hoặc bị lỗi mạng nghiêm trọng
            self.logger.error(f"Lỗi khởi động Server: {e}")
        finally:
            # Đảm bảo đóng socket và dọn dẹp tài nguyên khi dừng server
            self.stop()

    def accept_clients(self):
        """Vòng lặp chấp nhận kết nối từ các Client mới"""
        self.logger.info("Đang chờ Client kết nối tới...")

        while self.is_running:
            try:
                # Hàm accept() sẽ tạm dừng chờ cho đến khi có một Client kết nối tới
                client_socket, client_address = self.server_socket.accept()

                # Ghi log khi có Client mới kết nối thành công kèm IP và Port của Client đó
                self.logger.info(f"Client mới kết nối thành công từ địa chỉ: {client_address}")

                # Thêm socket của Client vào danh sách quản lý
                self.clients.append(client_socket)

                # Tạo một luồng (Thread) riêng biệt để xử lý dữ liệu cho Client này
                # target: hàm sẽ chạy ngầm, args: tham số truyền vào hàm đó
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address),
                    name=f"Thread-{client_address[1]}"  # Đặt tên luồng theo số Port để dễ theo dõi log
                )

                # Đặt luồng ở chế độ daemon để khi tắt Server thì các luồng con tự tắt theo
                client_thread.daemon = True

                # Bắt đầu kích hoạt luồng xử lý riêng cho Client
                client_thread.start()

            except Exception as e:
                # Nếu Server đang chạy mà gặp lỗi accept thì ghi nhận log
                if self.is_running:
                    self.logger.error(f"Lỗi khi tiếp nhận kết nối Client: {e}")
                break

    def handle_client(self, client_socket, client_address):
        """Hàm chạy trên luồng riêng để lắng nghe dữ liệu từ 1 Client cụ thể (Tuần 1: Mock echo)"""
        try:
            # Gửi lời chào mừng ban đầu tới Client (dạng bytes UTF-8)
            welcome_msg = "Chao mung ban den voi UDM08 Chat Server!\n"
            client_socket.sendall(welcome_msg.encode('utf-8'))

            while self.is_running:
                # Nhận tối đa 1024 bytes dữ liệu từ Client
                data = client_socket.recv(1024)

                # Nếu data rỗng (b''), nghĩa là Client đã chủ động ngắt kết nối
                if not data:
                    self.logger.info(f"Client {client_address} đã chủ động đóng kết nối.")
                    break

                # Giải mã dữ liệu từ byte sang chuỗi ký tự UTF-8
                text_received = data.decode('utf-8').strip()
                self.logger.info(f"Nhận từ {client_address}: {text_received}")

                # Phản hồi lại tin nhắn cho Client (Echo mock data tuần 1)
                reply_msg = f"[Server Echo]: {text_received}\n"
                client_socket.sendall(reply_msg.encode('utf-8'))

        except ConnectionResetError:
            # Xử lý trường hợp Client bị tắt đột ngột (tắt máy, crash, rút dây mạng)
            self.logger.warning(f"Client {client_address} bị ngắt kết nối đột ngột (Connection Reset)!")
        except Exception as e:
            # Ghi nhận các lỗi ngoại lệ khác trong quá trình truyền dữ liệu
            self.logger.error(f"Lỗi xử lý Client {client_address}: {e}")
        finally:
            # Khối finally luôn luôn chạy để dọn dẹp tài nguyên mạng
            if client_socket in self.clients:
                self.clients.remove(client_socket)  # Xóa socket khỏi danh sách quản lý
            client_socket.close()  # Đóng kết nối socket của client này
            self.logger.info(f"Đã giải phóng tài nguyên socket của Client {client_address}.")

    def stop(self):
        """Dừng Server và giải phóng toàn bộ tài nguyên Socket"""
        self.is_running = False  # Tắt cờ trạng thái để các vòng lặp dừng lại

        # Đóng toàn bộ các socket client đang kết nối
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        self.clients.clear()  # Làm rỗng danh sách client

        # Đóng socket chính của Server
        if self.server_socket:
            try:
                self.server_socket.close()
                self.logger.info("Đã đóng Socket Server.")
            except Exception as e:
                self.logger.error(f"Lỗi khi đóng Socket Server: {e}")


# Điểm chạy chương trình khi file này được thực thi trực tiếp
if __name__ == "__main__":
    PORT = 5000  # Cổng mạng quy định
    HOST = "127.0.0.1"  # Chạy thử nghiệm trên máy local (localhost)

    # Khởi tạo đối tượng ServerCore
    server = ServerCore(host=HOST, port=PORT)

    print("=== UDM_08 TCP SERVER CORE (TUẦN 1) ===")
    print("Server đang chạy. Nhấn Ctrl + C để dừng Server.\n")

    try:
        server.start()  # Bắt đầu chạy server
    except KeyboardInterrupt:
        print("\nĐang tắt Server an toàn...")
        server.stop()
