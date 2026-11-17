import socket  # Thư viện socket mạng TCP chuẩn của Python
import threading  # Thư viện hỗ trợ lập trình đa luồng (multi-threading)
import json  # Thư viện làm việc và đóng/mở gói dữ liệu định dạng JSON
import logging  # Thư viện ghi nhật ký hoạt động (log) của hệ thống
import sys  # Thư viện hệ thống để tương tác với cấu hình môi trường chạy
import os  # Thư viện thao tác với tệp tin và đường dẫn thư mục hệ thống
import datetime  # Thư viện lấy ngày giờ hệ thống cho dấu thời gian (timestamp)

# Nạp ServerRouter và tiện ích từ server_router.py (hỗ trợ nhiều môi trường chạy khác nhau)
try:
    from Code.Server.server_router import ServerRouter, MessageIdGenerator, validate_username
except ImportError:
    try:
        from server_router import ServerRouter, MessageIdGenerator, validate_username
    except ImportError:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        try:
            from server_router import ServerRouter, MessageIdGenerator, validate_username
        except ImportError:
            # Fallback nếu chạy độc lập mà không có server_router.py
            class MessageIdGenerator:
                def __init__(self):
                    self._id = 0
                def next_id(self):
                    self._id += 1
                    return self._id
            def validate_username(name):
                if not name or not str(name).strip():
                    return False, ("EMPTY", "Tên không được để trống")
                return True, (None, None)

# Đảm bảo hiển thị tiếng Việt có dấu rõ ràng trên màn hình Console Windows mà không bị lỗi font
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # Thiết lập chuẩn đầu ra console là UTF-8
        sys.stderr.reconfigure(encoding='utf-8')  # Thiết lập chuẩn báo lỗi console là UTF-8
    except Exception:
        pass  # Nếu môi trường không hỗ trợ thì bỏ qua để không gây gián đoạn chương trình


class ServerCore:
    def __init__(self, host="0.0.0.0", port=5000):
        # Địa chỉ IP của Server (0.0.0.0 cho phép nhận kết nối từ mọi card mạng)
        self.host = host
        # Cổng mạng Port để Server lắng nghe các Client kết nối tới
        self.port = port
        # Biến lưu trữ đối tượng socket chính của Server
        self.server_socket = None
        # Biến cờ (flag) boolean để kiểm soát trạng thái Server đang bật hay tắt
        self.is_running = False

        # --- YÊU CẦU TUẦN 3: LƯU THÔNG TIN USERNAME VÀ AVATAR CỦA TỪNG CLIENT ---
        # Dictionary quản lý client: { client_socket: {"username": tên_user, "avatar": tên_file_avatar, "address": địa_chỉ} }
        self.clients = {}
        # Khóa Lock để đảm bảo an toàn đa luồng (thread-safe), tránh xung đột khi nhiều luồng cùng đọc/ghi self.clients
        self.lock = threading.Lock()

        # --- NỐI SERVERROUTER: BỘ ĐẾM ID TIN NHẮN VÀ TRA CỨU REPLY TOÀN HỆ THỐNG ---
        self.id_generator = MessageIdGenerator()
        self.msg_counter = 0

        # Gọi hàm cài đặt cấu hình ghi log ngay khi ServerCore được khởi tạo
        self.setup_logger()

    def setup_logger(self):
        """Thiết lập cấu hình ghi log hiển thị trên màn hình Console và lưu vào file server.log"""
        # Định dạng chuẩn của từng dòng log: Thời gian - Mức độ log - Tên luồng thực thi - Nội dung thông báo
        log_format = "%(asctime)s - [%(levelname)s] - (%(threadName)s) - %(message)s"
        # Áp dụng cấu hình cơ bản cho thư viện logging
        logging.basicConfig(
            level=logging.INFO,  # Ghi nhận các thông điệp từ mức INFO trở lên (INFO, WARNING, ERROR)
            format=log_format,  # Áp dụng định dạng dòng log đã định nghĩa ở trên
            handlers=[
                logging.FileHandler("server.log", encoding="utf-8"),  # Ghi log ra tệp server.log bằng bảng mã UTF-8
                logging.StreamHandler(sys.stdout)  # Đồng thời xuất trực tiếp dòng log ra màn hình Console
            ]
        )
        # Khởi tạo đối tượng logger riêng cho class ServerCore
        self.logger = logging.getLogger("ServerCore")

    def get_online_users(self):
        """
        Nhiệm vụ Tuần 3: Lấy danh sách toàn bộ người dùng online kèm thông tin avatar của từng người.
        Trả về danh sách dạng: [ {"username": "A", "avatar": "avatar_A.png"}, ... ]
        """
        # Sử dụng khóa lock để đảm bảo không bị lỗi dữ liệu nếu luồng khác đang thêm hoặc xóa client
        with self.lock:
            # Duyệt qua các client đang kết nối và tạo danh sách thông tin người dùng gồm cả username và avatar
            online_list = []
            for client_info in self.clients.values():
                # Tạo bản ghi thông tin gồm tên và avatar của client
                user_record = {
                    "username": client_info.get("username", "Người dùng ẩn danh"),  # Tên người dùng
                    "avatar": client_info.get("avatar", "default_avatar.png")  # Tên ảnh avatar
                }
                # Thêm bản ghi thông tin vào danh sách kết quả
                online_list.append(user_record)
            # Trả về danh sách chứa đầy đủ username và avatar của tất cả user đang online
            return online_list

    def find_client_socket_by_username(self, username):
        """
        Nhiệm vụ Tuần 4: Tìm socket của một client dựa vào username để phục vụ điều hướng tin nhắn 1-1.
        Trả về client_socket nếu tìm thấy, ngược lại trả về None.
        """
        # Chuẩn hóa tên tìm kiếm: xóa khoảng trắng thừa và so sánh chữ thường
        target_name = str(username).strip().casefold()
        # Sử dụng khóa lock để duyệt danh sách an toàn trong môi trường đa luồng
        with self.lock:
            # Duyệt qua từng cặp (socket, thông tin) trong dictionary self.clients
            for sock, info in self.clients.items():
                # So sánh tên người dùng không phân biệt hoa thường
                if info.get("username", "").strip().casefold() == target_name:
                    return sock  # Trả về socket của người nhận tìm thấy
        # Trả về None nếu người dùng này hiện không online hoặc không tồn tại
        return None

    def cleanup_client(self, client_socket, username=None, address=None, reason="Mất kết nối"):
        """
        =============================================================================
        NHIỆM VỤ TUẦN 5: GIẢI PHÓNG TRIỆT ĐỂ SOCKET VÀ TÀI NGUYÊN RÁC KHI MẤT KẾT NỐI
        =============================================================================
        Hàm dọn dẹp tài nguyên trung tâm, thực hiện 4 thao tác quan trọng:
        1. Xóa an toàn socket khỏi dictionary self.clients (Thread-safe)
        2. Đóng kết nối socket triệt để cả 2 chiều (shutdown SHUT_RDWR + close)
        3. Thu hồi và giải phóng tài nguyên bộ nhớ rác
        4. Thông báo user_leave và cập nhật danh sách online tới các client khác
        """
        # Biến cờ ghi nhận xem client này có thực sự nằm trong danh sách quản lý không
        removed_user = username

        # 1. Khóa lock và gỡ bỏ client_socket khỏi dictionary self.clients
        with self.lock:
            if client_socket in self.clients:
                client_info = self.clients.pop(client_socket)
                # Nếu chưa có username truyền vào thì lấy username đã lưu
                if not removed_user:
                    removed_user = client_info.get("username")
                # Nếu chưa có địa chỉ thì lấy địa chỉ đã lưu
                if not address:
                    address = client_info.get("address")

        # 2. Giải phóng triệt để socket vật lý: ngắt truyền/nhận và đóng kết nối
        try:
            # Dừng cả 2 chiều đọc và ghi của socket (tránh tình trạng socket rác ở trạng thái treo)
            client_socket.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass  # Socket có thể đã bị ngắt từ trước, bỏ qua lỗi nếu shutdown không được

        try:
            # Đóng hoàn toàn socket và giải phóng file descriptor của hệ điều hành
            client_socket.close()
        except Exception:
            pass  # Bỏ qua nếu socket đã đóng

        # 3. Ghi log nhật ký dọn dẹp tài nguyên rõ ràng để theo dõi hệ thống
        user_display = removed_user if removed_user else "Client chưa đăng nhập"
        addr_display = f"({address})" if address else ""
        self.logger.info(f"[GIẢI PHÓNG TÀI NGUYÊN] Đã thu hồi socket của [{user_display}] {addr_display}. Lý do: {reason}")

        # 4. Nếu người dùng đã từng đăng nhập, phát thông báo cho các client còn lại
        if removed_user:
            # Gói tin thông báo thành viên đã rời phòng chat
            leave_packet = {
                "type": "user_leave",
                "username": removed_user,
                "reason": reason  # Gửi kèm lý do ngắt kết nối (tắt đột ngột, timeout, ...)
            }
            # Gửi thông báo người rời phòng tới tất cả client còn lại
            self.broadcast_packet(leave_packet)
            # Gửi lại danh sách online mới nhất đã cập nhật cho các client còn lại
            self.broadcast_online_list()

    def send_packet(self, client_socket, packet_dict):
        """
        Hàm gửi 1 gói tin định dạng JSON (kèm ký tự '\\n' ở cuối) tới 1 socket client cụ thể.
        Tuần 5: Bắt lỗi kết nối socket chết và tự động gọi dọn dẹp tài nguyên rác ngay lập tức.
        """
        try:
            # Chuyển đổi dữ liệu Dictionary sang chuỗi JSON (giữ nguyên tiếng Việt nhờ ensure_ascii=False)
            json_str = json.dumps(packet_dict, ensure_ascii=False)
            # Thêm ký tự '\\n' ở cuối chuỗi để phân tách gói tin TCP (chống dính gói tin)
            data_to_send = (json_str + "\n").encode('utf-8')
            # Gửi toàn bộ dữ liệu byte qua kết nối socket
            client_socket.sendall(data_to_send)
            # Trả về True báo hiệu gửi thành công
            return True
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as e:
            # Bắt lỗi khi cố gắng gửi vào socket đã bị hỏng / client đã tắt đột ngột
            self.logger.warning(f"Phát hiện socket đã chết khi đang gửi dữ liệu ({e}). Bắt đầu dọn dẹp...")
            # Tự động giải phóng triệt để socket chết này để tránh rác hệ thống
            self.cleanup_client(client_socket, reason=f"Lỗi gửi dữ liệu: {e}")
            return False
        except Exception as e:
            # Ghi lại thông báo lỗi nếu việc gửi gói tin thất bại vì lý do khác
            self.logger.error(f"Lỗi khi gửi dữ liệu qua socket: {e}")
            return False

    def broadcast_packet(self, packet_dict, exclude_socket=None):
        """
        Hàm gửi 1 gói tin tới toàn bộ các client đang online (có thể bỏ qua socket của client gửi).
        Tuần 5: Tự động gom và dọn dẹp triệt để bất kỳ socket nào bị đứt kết nối trong quá trình broadcast.
        """
        # Dùng khóa lock để sao chép danh sách các socket đang kết nối nhằm tránh xung đột đa luồng
        with self.lock:
            target_sockets = list(self.clients.keys())

        # Danh sách tạm lưu các socket bị chết để dọn dẹp sau khi quét xong
        dead_sockets = []

        # Duyệt qua từng socket của các client trong danh sách
        for sock in target_sockets:
            # Nếu socket hiện tại trùng với exclude_socket thì bỏ qua không gửi lại cho người đó
            if sock == exclude_socket:
                continue
            # Thực hiện gửi gói tin tới socket của client này
            success = self.send_packet(sock, packet_dict)
            # Nếu gửi thất bại vì socket hỏng, đưa vào danh sách cần dọn dẹp
            if not success:
                dead_sockets.append(sock)

        # Giải phóng triệt để toàn bộ các socket chết phát hiện được
        for dead_sock in dead_sockets:
            self.cleanup_client(dead_sock, reason="Socket không phản hồi khi broadcast")

    def broadcast_online_list(self, exclude_socket=None):
        """
        Nhiệm vụ Tuần 3: Gửi broadcast danh sách online mới nhất (chứa cả username và avatar) tới các client khác.
        exclude_socket: socket của client vừa đăng nhập (được bỏ qua vì client này đã nhận gói login_ack riêng).
        """
        # Lấy danh sách online mới nhất gồm cả tên và avatar của tất cả người dùng
        online_users = self.get_online_users()

        # Đóng gói thông tin danh sách người dùng online vào dictionary JSON
        packet = {
            "type": "user_list",  # Loại gói tin là danh sách người dùng (khớp với xử lý ở client)
            "action": "update",  # Hành động: cập nhật lại toàn bộ danh sách
            "online_users": online_users  # Mảng danh sách các object {"username": ..., "avatar": ...}
        }

        # Ghi thông tin log về việc phát broadcast danh sách online kèm avatar
        self.logger.info(f"[BROADCAST] Gửi danh sách online ({len(online_users)} người, kèm avatar) tới các client.")

        # Gọi hàm phát broadcast gói tin này tới các client
        self.broadcast_packet(packet, exclude_socket=exclude_socket)

    def handle_forward_message(self, client_socket, current_username, current_avatar, message_dict):
        """
        =============================================================================
        NHIỆM VỤ TUẦN 4: XỬ LÝ ĐIỀU HƯỚNG TIN NHẮN FORWARD (CHUYỂN TIẾP 1-1 HOẶC PHÒNG CHUNG)
        =============================================================================
        Tham số:
        - client_socket: socket của người thực hiện chuyển tiếp tin nhắn
        - current_username: tên của người gửi chuyển tiếp
        - current_avatar: ảnh đại diện của người chuyển tiếp
        - message_dict: gói tin forward nhận được từ client
        """
        # 1. Đảm bảo gán msg_id tự tăng duy nhất cho tin nhắn forward
        with self.lock:
            self.msg_counter += 1  # Tăng bộ đếm tin nhắn lên 1
            msg_id = self.msg_counter  # Lấy mã định danh tin nhắn mới
        message_dict["msg_id"] = msg_id  # Gán msg_id vào gói tin

        # 2. Bổ sung thông tin người gửi (sender) và ảnh đại diện (avatar) nếu chưa có
        message_dict["sender"] = current_username
        if "avatar" not in message_dict or not message_dict.get("avatar"):
            message_dict["avatar"] = current_avatar

        # 3. Bổ sung dấu thời gian (timestamp) hiện tại nếu chưa có
        if "timestamp" not in message_dict or not message_dict.get("timestamp"):
            message_dict["timestamp"] = str(datetime.datetime.now().strftime("%H:%M:%S"))

        # 4. Trích xuất thông tin người nhận (receiver)
        receiver = message_dict.get("receiver", "all")

        # -------------------------------------------------------------------------
        # TRƯỜNG HỢP A: CHUYỂN TIẾP VÀO PHÒNG CHUNG (receiver == 'all' hoặc để trống)
        # -------------------------------------------------------------------------
        if not receiver or str(receiver).strip().lower() == "all":
            # Đảm bảo trường receiver được chuẩn hóa thành 'all'
            message_dict["receiver"] = "all"

            # Ghi log thông báo điều hướng chuyển tiếp tin nhắn vào phòng chung
            self.logger.info(
                f"[FORWARD PHÒNG CHUNG] (ID:{msg_id}) Từ [{current_username}] "
                f"tới phòng chung. Nội dung: '{message_dict.get('content', '')}'"
            )

            # Gửi broadcast gói tin forward tới tất cả các client khác (bỏ qua người gửi)
            self.broadcast_packet(message_dict, exclude_socket=client_socket)

            # Gửi gói phản hồi xác nhận (forward_ack) về cho chính người gửi
            forward_ack = {
                "type": "forward_ack",  # Loại gói tin xác nhận chuyển tiếp
                "status": "success",  # Trạng thái thành công
                "msg_id": msg_id,  # Mã định danh tin nhắn
                "receiver": "all",  # Nơi nhận là phòng chung
                "message": "Chuyển tiếp tin nhắn vào phòng chung thành công!"  # Thông báo chi tiết
            }
            self.send_packet(client_socket, forward_ack)

        # -------------------------------------------------------------------------
        # TRƯỜNG HỢP B: CHUYỂN TIẾP 1-1 (receiver là tên của 1 người dùng cụ thể)
        # -------------------------------------------------------------------------
        else:
            target_username = str(receiver).strip()  # Tên người nhận cụ thể
            # Tìm socket của người nhận trong danh sách đang online
            target_socket = self.find_client_socket_by_username(target_username)

            # Nếu tìm thấy người nhận đang online trên hệ thống
            if target_socket:
                # Ghi log thông báo điều hướng chuyển tiếp tin nhắn 1-1 thành công
                self.logger.info(
                    f"[FORWARD 1-1] (ID:{msg_id}) Từ [{current_username}] -> "
                    f"Riêng [{target_username}]. Nội dung: '{message_dict.get('content', '')}'"
                )

                # Gửi gói tin forward trực tiếp tới socket của người nhận đó
                self.send_packet(target_socket, message_dict)

                # Gửi gói phản hồi xác nhận (forward_ack) về cho người gửi biết đã chuyển tiếp 1-1 thành công
                forward_ack = {
                    "type": "forward_ack",  # Loại gói tin xác nhận chuyển tiếp
                    "status": "success",  # Trạng thái thành công
                    "msg_id": msg_id,  # Mã định danh tin nhắn
                    "receiver": target_username,  # Người nhận cụ thể
                    "message": f"Chuyển tiếp tin nhắn tới '{target_username}' thành công!"  # Thông báo thành công
                }
                self.send_packet(client_socket, forward_ack)

            # Nếu không tìm thấy người nhận (người nhận đang offline hoặc sai tên)
            else:
                # Ghi log cảnh báo người nhận không online
                self.logger.warning(
                    f"[FORWARD 1-1 THẤT BẠI] Từ [{current_username}] -> [{target_username}]: "
                    f"Người nhận không online hoặc không tồn tại."
                )

                # Gửi gói phản hồi thông báo lỗi về cho người gửi
                error_ack = {
                    "type": "forward_ack",  # Loại gói tin xác nhận chuyển tiếp
                    "status": "error",  # Trạng thái thất bại
                    "msg_id": msg_id,  # Mã định danh tin nhắn
                    "receiver": target_username,  # Người nhận không liên lạc được
                    "message": f"Không thể chuyển tiếp: Người dùng '{target_username}' hiện không online."
                }
                self.send_packet(client_socket, error_ack)

    def start(self):
        """Khởi động TCP Socket Server và đưa Server vào trạng thái lắng nghe kết nối từ Client"""
        try:
            # Tạo Socket với IPv4 (AF_INET) và giao thức TCP truyền tin cậy (SOCK_STREAM)
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Cho phép sử dụng lại địa chỉ IP/Port ngay lập tức khi chạy lại server (tránh lỗi Address already in use)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Gán IP và Port vào Socket của Server
            self.server_socket.bind((self.host, self.port))
            # Chuyển socket sang chế độ lắng nghe (hàng đợi chờ tối đa 10 kết nối cùng lúc)
            self.server_socket.listen(10)

            # Cập nhật trạng thái Server đang chạy
            self.is_running = True
            # Ghi log thông báo Server đã mở cổng thành công
            self.logger.info(f"Server đã khởi động thành công trên cổng {self.port} (IP: {self.host})")

            # Bắt đầu vòng lặp tiếp nhận các Client kết nối tới
            self.accept_clients()

        except Exception as e:
            # Ghi nhận log nếu xảy ra lỗi trong quá trình khởi động Server
            self.logger.error(f"Lỗi khởi động Server: {e}")
        finally:
            # Đảm bảo dọn dẹp tài nguyên và tắt Server an toàn khi kết thúc
            self.stop()

    def accept_clients(self):
        """Vòng lặp đón nhận từng kết nối mới từ Client tới Server"""
        # Ghi log thông báo Server đang trong trạng thái chờ Client
        self.logger.info("Đang chờ Client kết nối tới...")

        # Tiếp tục vòng lặp khi Server vẫn đang ở trạng thái hoạt động
        while self.is_running:
            try:
                # Hàm accept() sẽ tạm dừng luồng chính cho đến khi có 1 Client kết nối tới
                client_socket, client_address = self.server_socket.accept()

                # Tuần 5: Bật cơ chế TCP Keepalive để hệ thống tự phát hiện client mất kết nối ngầm
                try:
                    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                except Exception:
                    pass

                # Ghi log thông tin địa chỉ IP và Port của Client vừa kết nối thành công
                self.logger.info(f"Client mới kết nối thành công từ địa chỉ: {client_address}")

                # Khởi tạo một luồng (Thread) riêng biệt để phục vụ xử lý tin nhắn cho Client này
                client_thread = threading.Thread(
                    target=self.handle_client,  # Hàm mục tiêu mà luồng sẽ chạy
                    args=(client_socket, client_address),  # Tham số truyền vào hàm là socket và địa chỉ của client
                    name=f"Thread-{client_address[1]}"  # Đặt tên cho luồng theo số Port để dễ quan sát log
                )
                # Đặt chế độ luồng nền (daemon) để luồng này tự tắt khi Server tắt
                client_thread.daemon = True
                # Bắt đầu chạy luồng riêng cho Client này
                client_thread.start()

            except Exception as e:
                # Nếu Server đang chạy mà gặp sự cố khi nhận kết nối thì ghi lại thông báo lỗi
                if self.is_running:
                    self.logger.error(f"Lỗi khi tiếp nhận kết nối Client: {e}")
                # Thoát khỏi vòng lặp đón nhận kết nối nếu gặp sự cố
                break

    def handle_client(self, client_socket, client_address):
        """
        Hàm chạy trên luồng riêng để lắng nghe và xử lý toàn bộ dữ liệu trao đổi với 1 Client cụ thể.
        Tuần 5: Bắt trọn vẹn các lỗi kết nối (tắt đột ngột, timeout, đứt cáp), giải phóng tài nguyên triệt để
        và hỗ trợ cơ chế Reconnect tự động mượt mà.
        """
        # Biến lưu trữ tên người dùng của Client này (khởi tạo mặc định ban đầu là None)
        current_username = None
        # Biến lưu trữ tên ảnh avatar của Client này (khởi tạo mặc định là default_avatar.png)
        current_avatar = "default_avatar.png"
        # Bộ đệm bytearray để xử lý phân tách gói tin theo dấu '\n' (tránh lỗi cắt ngang ký tự tiếng Việt / emoji)
        buffer = bytearray()

        try:
            # Vòng lặp nhận dữ liệu từ Client liên tục trong suốt thời gian kết nối
            while self.is_running:
                # Đọc tối đa 4096 bytes dữ liệu từ kết nối socket của client
                data = client_socket.recv(4096)

                # Nếu dữ liệu nhận về là rỗng (b''), nghĩa là Client đã chủ động đóng socket
                if not data:
                    self.logger.info(f"Client {client_address} ({current_username or 'Chưa đăng nhập'}) đã chủ động ngắt kết nối.")
                    break  # Thoát khỏi vòng lặp nhận dữ liệu

                # Nối dữ liệu byte nhận được vào bộ đệm buffer
                buffer.extend(data)

                # Tiếp tục cắt và xử lý từng gói tin chừng nào trong bộ đệm còn chứa ký tự ngắt dòng '\n'
                while b"\n" in buffer:
                    # Tìm vị trí dấu xuống dòng đầu tiên trong buffer
                    newline_pos = buffer.find(b"\n")
                    # Tách lấy mẩu byte tương ứng với 1 gói tin
                    line_bytes = bytes(buffer[:newline_pos])
                    # Xóa phần dữ liệu đã lấy ra khỏi buffer
                    del buffer[:newline_pos + 1]

                    # Giải mã chuỗi UTF-8, thay thế ký tự lỗi nếu có và xóa khoảng trắng thừa
                    packet_str = line_bytes.decode('utf-8', errors='replace').strip()

                    # Nếu gói tin rỗng thì bỏ qua không xử lý
                    if not packet_str:
                        continue

                    # Thử phân tích chuỗi ký tự vừa nhận thành Dictionary theo định dạng JSON
                    try:
                        message_dict = json.loads(packet_str)
                    except json.JSONDecodeError:
                        # Ghi log cảnh báo nếu gói tin nhận được không đúng định dạng JSON
                        self.logger.warning(f"Gói tin không phải JSON từ {client_address}: {packet_str}")
                        # Gửi gói báo lỗi về client
                        self.send_packet(client_socket, {
                            "type": "error",
                            "error": {"code": "INVALID_JSON", "message": "Gói tin gửi lên không đúng định dạng JSON chuẩn."}
                        })
                        continue

                    # Kiểm tra dữ liệu JSON bắt buộc phải là một đối tượng dictionary
                    if not isinstance(message_dict, dict):
                        self.send_packet(client_socket, {
                            "type": "error",
                            "error": {"code": "INVALID_FORMAT", "message": "Gói tin JSON bắt buộc phải là một JSON Object (Dictionary)."}
                        })
                        continue

                    # Lấy loại gói tin (type) từ dictionary nhận được
                    msg_type = message_dict.get("type")

                    # =========================================================================
                    # XỬ LÝ ĐĂNG NHẬP (LOGIN) & CƠ CHẾ RECONNECT TỰ ĐỘNG (TUẦN 5)
                    # =========================================================================
                    if msg_type in ("login", "reconnect"):
                        raw_username = message_dict.get("username", "")

                        # 1. Kiểm tra tính hợp lệ của username (độ dài, ký tự cấm)
                        is_valid, err = validate_username(raw_username)
                        if not is_valid:
                            self.logger.warning(f"Từ chối đăng nhập từ {client_address}: {err[1]}")
                            self.send_packet(client_socket, {
                                "type": "login_ack",
                                "status": "error",
                                "error": {"code": err[0], "message": err[1]}
                            })
                            continue

                        valid_name = str(raw_username).strip()

                        # 2. XỬ LÝ TRÙNG TÊN HOẶC RECONNECT TỰ ĐỘNG (TUẦN 5)
                        old_socket = None
                        with self.lock:
                            # Tìm xem tên này đã có trong danh sách kết nối trước đó chưa
                            for sock, info in list(self.clients.items()):
                                if info.get("username", "").casefold() == valid_name.casefold():
                                    old_socket = sock
                                    break

                        # Nếu phát hiện user này đã từng kết nối trước đó:
                        if old_socket is not None and old_socket != client_socket:
                            # Ghi log phát hiện kết nối lại tự động
                            self.logger.info(
                                f"[RECONNECT TỰ ĐỘNG] Phát hiện user [{valid_name}] kết nối lại từ {client_address}. "
                                f"Tiến hành thu hồi và giải phóng socket cũ..."
                            )
                            # Giải phóng triệt để socket cũ bị đứt/treo mà không làm gián đoạn user
                            self.cleanup_client(old_socket, username=valid_name, reason="Client Reconnect tự động phiên mới")

                        # Gán tên người dùng hiện tại
                        current_username = valid_name

                        # 3. Trích xuất thông tin ảnh avatar từ gói login (mặc định default_avatar.png nếu rỗng)
                        extracted_avatar = message_dict.get("avatar")
                        if extracted_avatar and str(extracted_avatar).strip():
                            current_avatar = str(extracted_avatar).strip()
                        else:
                            current_avatar = "default_avatar.png"

                        # 4. Lưu thông tin đầy đủ vào self.clients an toàn đa luồng
                        with self.lock:
                            self.clients[client_socket] = {
                                "username": current_username,
                                "avatar": current_avatar,
                                "address": client_address
                            }

                        self.logger.info(f"==> Client [{current_username}] đã đăng nhập thành công với avatar: '{current_avatar}'.")

                        # 5. Gửi login_ack xác nhận về cho chính client vừa đăng nhập
                        login_ack_packet = {
                            "type": "login_ack",
                            "status": "success",
                            "username": current_username,
                            "avatar": current_avatar,
                            "online_users": self.get_online_users()  # Danh sách online kèm avatar
                        }
                        self.send_packet(client_socket, login_ack_packet)
                        self.logger.info(f"Đã gửi gói 'login_ack' xác nhận kèm avatar về cho [{current_username}].")

                        # 6. Gửi broadcast thông báo thành viên mới vào phòng tới các client khác
                        user_join_packet = {
                            "type": "user_join",
                            "username": current_username,
                            "avatar": current_avatar
                        }
                        self.broadcast_packet(user_join_packet, exclude_socket=client_socket)
                        # Đồng thời cập nhật lại danh sách online cho tất cả client khác
                        self.broadcast_online_list(exclude_socket=client_socket)
                        continue

                    # =========================================================================
                    # BẮT BUỘC ĐĂNG NHẬP TRƯỚC KHI GỬI CÁC LOẠI TIN NHẮN KHÁC
                    # =========================================================================
                    if current_username is None:
                        self.logger.warning(f"Client {client_address} gửi '{msg_type}' khi chưa đăng nhập.")
                        self.send_packet(client_socket, {
                            "type": "error",
                            "error": {"code": "NOT_LOGGED_IN", "message": "Bạn phải đăng nhập (type=login) trước khi gửi tin nhắn."}
                        })
                        continue

                    # =========================================================================
                    # XỬ LÝ GÓI TIN FORWARD (TUẦN 4)
                    # =========================================================================
                    if msg_type == "forward":
                        self.handle_forward_message(client_socket, current_username, current_avatar, message_dict)

                    # =========================================================================
                    # XỬ LÝ GÓI TIN TIN NHẮN THƯỜNG (MSG) VÀ TRẢ LỜI (REPLY)
                    # =========================================================================
                    elif msg_type in ("msg", "message", "reply"):
                        # Tự động gán msg_id duy nhất tăng dần cho tin nhắn
                        with self.lock:
                            self.msg_counter += 1
                            message_dict["msg_id"] = self.msg_counter

                        # Đảm bảo có thông tin người gửi và avatar
                        message_dict["sender"] = current_username
                        if "avatar" not in message_dict or not message_dict.get("avatar"):
                            message_dict["avatar"] = current_avatar
                        if "timestamp" not in message_dict or not message_dict.get("timestamp"):
                            message_dict["timestamp"] = str(datetime.datetime.now().strftime("%H:%M:%S"))

                        # Điều hướng theo người nhận (receiver)
                        msg_receiver = message_dict.get("receiver", "all")
                        if not msg_receiver or str(msg_receiver).strip().lower() == "all":
                            message_dict["receiver"] = "all"
                            self.logger.info(f"Tin nhắn [{msg_type}] từ [{current_username}] -> Phòng chung: {message_dict.get('content', '')}")
                            self.broadcast_packet(message_dict, exclude_socket=client_socket)
                        else:
                            target_user = str(msg_receiver).strip()
                            target_sock = self.find_client_socket_by_username(target_user)
                            if target_sock:
                                self.logger.info(f"Tin nhắn [{msg_type}] từ [{current_username}] -> Riêng [{target_user}]: {message_dict.get('content', '')}")
                                self.send_packet(target_sock, message_dict)
                            else:
                                self.logger.warning(f"Người nhận [{target_user}] không online.")
                                self.send_packet(client_socket, {
                                    "type": "error",
                                    "error": {"code": "USER_OFFLINE", "message": f"Người dùng '{target_user}' hiện không online."}
                                })

                    # Xử lý các loại thông điệp khác (ví dụ: ping, heartbeat...)
                    else:
                        self.logger.info(f"Nhận gói tin loại '{msg_type}' từ [{current_username}]: {message_dict}")

        # BẮT CÁC LỖI KẾT NỐI: CLIENT TẮT ĐỘT NGỘT, ĐỨT CÁP MẠNG, TIMEOUT (TUẦN 5)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, TimeoutError, OSError) as e:
            self.logger.warning(f"Client {client_address} ({current_username or 'Chưa đăng nhập'}) bị mất kết nối đột ngột: {e}")
        except Exception as e:
            self.logger.error(f"Lỗi phát sinh ngoài dự kiến từ Client {client_address} ({current_username or 'Chưa đăng nhập'}): {e}")
        finally:
            # KHỐI DỌN DẸP TRIỆT ĐỂ SOCKET VÀ TÀI NGUYÊN KHI CLIENT RỜI ĐI HOẶC GẶP LỖI (TUẦN 5)
            self.cleanup_client(
                client_socket,
                username=current_username,
                address=client_address,
                reason="Client ngắt kết nối hoặc gặp lỗi mạng"
            )

    def stop(self):
        """
        Hàm tắt Server an toàn:
        1. Gửi thông báo server_shutdown tới tất cả client đang online để client biết tự động reconnect
        2. Đóng và giải phóng toàn bộ socket client con
        3. Đóng socket Server chính
        """
        # Đặt cờ trạng thái Server sang False để dừng các vòng lặp lắng nghe
        self.is_running = False

        # 1. Gửi thông báo trước cho các client biết Server đang tắt
        shutdown_packet = {
            "type": "server_shutdown",
            "message": "Máy chủ đang tiến hành tắt hoặc bảo trì hệ thống. Vui lòng thử kết nối lại sau."
        }
        try:
            self.broadcast_packet(shutdown_packet)
        except Exception:
            pass

        # 2. Khóa lock và giải phóng triệt để tất cả kết nối socket con
        with self.lock:
            active_sockets = list(self.clients.keys())
            for sock in active_sockets:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    sock.close()
                except Exception:
                    pass
            # Xóa rỗng toàn bộ danh sách quản lý
            self.clients.clear()

        # 3. Đóng socket chính của Server
        if self.server_socket:
            try:
                self.server_socket.close()
                self.logger.info("Đã đóng Socket Server chính an toàn.")
            except Exception as e:
                self.logger.error(f"Lỗi khi đóng Socket Server chính: {e}")


# Điểm bắt đầu thực thi chương trình khi chạy trực tiếp tệp server_core.py
if __name__ == "__main__":
    # Đọc HOST và PORT linh hoạt từ tham số dòng lệnh hoặc biến môi trường hoặc dùng mặc định
    # Cú pháp chạy tùy biến: python server_core.py [HOST] [PORT]
    default_host = "0.0.0.0"
    default_port = 5000

    host = sys.argv[1] if len(sys.argv) > 1 else default_host
    try:
        port = int(sys.argv[2]) if len(sys.argv) > 2 else default_port
    except ValueError:
        print(f"[CẢNH BÁO] Port '{sys.argv[2]}' không hợp lệ, dùng port mặc định {default_port}")
        port = default_port

    # Khởi tạo đối tượng ServerCore
    server = ServerCore(host=host, port=port)

    print("=== UDM_08 TCP SERVER CORE (TUẦN 5 - BẮT LỖI MẤT KẾT NỐI & DỌN DẸP RÁC TRIỆT ĐỂ) ===")
    print(f"Server đang lắng nghe trên {host}:{port}. Nhấn Ctrl + C để dừng Server.\n")

    try:
        # Khởi chạy vòng lặp hoạt động của Server
        server.start()
    except KeyboardInterrupt:
        # Bắt sự kiện người dùng nhấn tổ hợp phím Ctrl + C để tắt Server an toàn
        print("\nĐang tiến hành tắt Server an toàn...")
        server.stop()
