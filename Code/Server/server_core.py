import socket  # Thư viện socket mạng TCP chuẩn của Python
import threading  # Thư viện hỗ trợ lập trình đa luồng (multi-threading)
import json  # Thư viện làm việc và đóng/mở gói dữ liệu định dạng JSON
import logging  # Thư viện ghi nhật ký hoạt động (log) của hệ thống
import sys  # Thư viện hệ thống để tương tác với cấu hình môi trường chạy
import os  # Thư viện thao tác với tệp tin và đường dẫn thư mục hệ thống
import datetime  # Thư viện lấy ngày giờ hệ thống cho dấu thời gian (timestamp)

# Nạp ServerRouter và tiện ích từ server_router.py
try:
    from Code.Server.server_router import ServerRouter, MessageIdGenerator, validate_username
except ImportError:
    try:
        from server_router import ServerRouter, MessageIdGenerator, validate_username
    except ImportError:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        from server_router import ServerRouter, MessageIdGenerator, validate_username

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
        # Dictionary quản lý client: { client_socket: {"username": tên_user, "avatar": tên_file_avatar} }
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
        # Sử dụng khóa lock để duyệt danh sách an toàn trong môi trường đa luồng
        with self.lock:
            # Duyệt qua từng cặp (socket, thông tin) trong dictionary self.clients
            for sock, info in self.clients.items():
                # So sánh tên người dùng không phân biệt khoảng trắng thừa
                if info.get("username", "").strip() == str(username).strip():
                    return sock  # Trả về socket của người nhận tìm thấy
        # Trả về None nếu người dùng này hiện không online hoặc không tồn tại
        return None

    def send_packet(self, client_socket, packet_dict):
        """Hàm hỗ trợ gửi 1 gói tin định dạng JSON (có kèm ký tự '\\n' ở cuối) tới 1 socket client cụ thể"""
        try:
            # Chuyển đổi dữ liệu Dictionary sang chuỗi JSON (giữ nguyên tiếng Việt nhờ ensure_ascii=False)
            json_str = json.dumps(packet_dict, ensure_ascii=False)
            # Thêm ký tự '\\n' ở cuối chuỗi để phân tách gói tin TCP (chống dính gói tin)
            data_to_send = (json_str + "\n").encode('utf-8')
            # Gửi toàn bộ dữ liệu byte qua kết nối socket
            client_socket.sendall(data_to_send)
            # Trả về True báo hiệu gửi thành công
            return True
        except Exception as e:
            # Ghi lại thông báo lỗi nếu việc gửi gói tin thất bại
            self.logger.error(f"Lỗi khi gửi dữ liệu qua socket: {e}")
            # Trả về False báo hiệu gửi thất bại
            return False

    def broadcast_packet(self, packet_dict, exclude_socket=None):
        """Hàm gửi 1 gói tin tới toàn bộ các client đang online (có thể bỏ qua socket của client gửi)"""
        # Dùng khóa lock để sao chép danh sách các socket đang kết nối nhằm tránh xung đột đa luồng
        with self.lock:
            target_sockets = list(self.clients.keys())

        # Duyệt qua từng socket của các client trong danh sách
        for sock in target_sockets:
            # Nếu socket hiện tại trùng với exclude_socket thì bỏ qua không gửi lại cho người đó
            if sock == exclude_socket:
                continue
            # Thực hiện gửi gói tin tới socket của client này
            self.send_packet(sock, packet_dict)

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
            # Cho phép sử dụng lại địa chỉ IP/Port ngay lập tức khi chạy lại server (tránh lỗi Port in use)
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
        """Hàm chạy trên luồng riêng để lắng nghe và xử lý toàn bộ dữ liệu trao đổi với 1 Client cụ thể (tích hợp ServerRouter)"""
        # Biến lưu trữ tên người dùng của Client này (khởi tạo mặc định ban đầu là None)
        current_username = None
        # Biến lưu trữ tên ảnh avatar của Client này (khởi tạo mặc định là default_avatar.png)
        current_avatar = "default_avatar.png"
        
        # Mỗi Client có 1 đối tượng ServerRouter riêng (dùng chung MessageIdGenerator của Server)
        # để tách gói TCP bằng bytearray, kiểm tra UTF-8/JSON nghiêm ngặt và tra cứu reply_to_id
        router = ServerRouter(id_generator=self.id_generator)

        try:
            # Vòng lặp nhận dữ liệu từ Client liên tục trong suốt thời gian kết nối
            while self.is_running:
                # Đọc tối đa 4096 bytes dữ liệu từ kết nối socket của client
                data = client_socket.recv(4096)

                # Nếu dữ liệu nhận về là rỗng (b''), nghĩa là Client đã chủ động ngắt kết nối
                if not data:
                    self.logger.info(f"Client {client_address} ({current_username}) đã đóng kết nối.")
                    break  # Thoát khỏi vòng lặp nhận dữ liệu

                # Nạp dữ liệu vào ServerRouter để tách gói bằng bytearray và kiểm tra tính hợp lệ
                for result in router.feed_data(data):
                    if not result["ok"]:
                        error_packet = result["error"]
                        self.logger.warning(f"Gói tin lỗi từ {client_address}: {error_packet}")
                        self.send_packet(client_socket, error_packet)
                        continue

                    message_dict = result["message"]
                    msg_type = message_dict.get("type")

                    # =========================================================================
                    # XỬ LÝ ĐĂNG NHẬP (LOGIN): KIỂM TRA TÊN HỢP LỆ & CHẶN TRÙNG USERNAME
                    # =========================================================================
                    if msg_type == "login":
                        if current_username is not None:
                            self.send_packet(client_socket, {
                                "type": "login_ack",
                                "status": "error",
                                "error": {"code": "ALREADY_LOGGED_IN", "message": "Bạn đã đăng nhập rồi."}
                            })
                            continue

                        # 1. Trích xuất và kiểm tra tính hợp lệ của username qua validate_username
                        raw_username = message_dict.get("username", f"User_{client_address[1]}")
                        valid_name, err = validate_username(raw_username)
                        if err:
                            self.send_packet(client_socket, {
                                "type": "login_ack",
                                "status": "error",
                                "error": {"code": err[0], "message": err[1]}
                            })
                            continue

                        # 2. Chặn trùng username (không phân biệt hoa thường)
                        with self.lock:
                            is_taken = any(
                                info.get("username", "").casefold() == valid_name.casefold()
                                for info in self.clients.values()
                            )
                        if is_taken:
                            self.logger.warning(f"Từ chối đăng nhập từ {client_address}: Username '{valid_name}' đã tồn tại.")
                            self.send_packet(client_socket, {
                                "type": "login_ack",
                                "status": "error",
                                "error": {"code": "USERNAME_TAKEN", "message": f"Username '{valid_name}' đã có người sử dụng."}
                            })
                            continue

                        current_username = valid_name

                        # 3. Trích xuất thông tin ảnh avatar từ gói login
                        extracted_avatar = message_dict.get("avatar")
                        if extracted_avatar and str(extracted_avatar).strip():
                            current_avatar = str(extracted_avatar).strip()
                        else:
                            current_avatar = "default_avatar.png"

                        # 4. Lưu thông tin vào self.clients an toàn đa luồng
                        with self.lock:
                            self.clients[client_socket] = {
                                "username": current_username,
                                "avatar": current_avatar
                            }

                        self.logger.info(f"==> Client [{current_username}] đã đăng nhập với avatar: '{current_avatar}'.")

                        # 5. Gửi login_ack về cho chính client vừa đăng nhập
                        login_ack_packet = {
                            "type": "login_ack",
                            "status": "success",
                            "username": current_username,
                            "avatar": current_avatar,
                            "online_users": self.get_online_users()
                        }
                        self.send_packet(client_socket, login_ack_packet)

                        # 6. Broadcast user_join và danh sách online mới nhất cho các client khác
                        user_join_packet = {
                            "type": "user_join",
                            "username": current_username,
                            "avatar": current_avatar
                        }
                        self.broadcast_packet(user_join_packet, exclude_socket=client_socket)
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
                    # XỬ LÝ ĐIỀU HƯỚNG TIN NHẮN FORWARD (TUẦN 4)
                    # =========================================================================
                    if msg_type == "forward":
                        self.handle_forward_message(client_socket, current_username, current_avatar, message_dict)

                    # =========================================================================
                    # XỬ LÝ TIN NHẮN THƯỜNG (MSG) VÀ TIN NHẮN TRẢ LỜI (REPLY)
                    # =========================================================================
                    elif msg_type in ("msg", "message", "reply"):
                        # Bổ sung thông tin người gửi, avatar và timestamp
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

        except ConnectionResetError:
            self.logger.warning(f"Client {client_address} ({current_username}) bị ngắt kết nối đột ngột (Connection Reset)!")
        except Exception as e:
            self.logger.error(f"Lỗi phát sinh khi xử lý Client {client_address} ({current_username}): {e}")
        finally:
            # KHỐI DỌN DẸP TÀI NGUYÊN KHI CLIENT RỜI KHỎI SERVER:
            with self.lock:
                if client_socket in self.clients:
                    del self.clients[client_socket]

            try:
                client_socket.close()
            except Exception:
                pass

            self.logger.info(f"Đã giải phóng tài nguyên của [{current_username}] ({client_address}).")

            if current_username:
                leave_packet = {
                    "type": "user_leave",
                    "username": current_username
                }
                self.broadcast_packet(leave_packet)
                self.broadcast_online_list()

    def stop(self):
        """Hàm tắt Server an toàn và đóng toàn bộ các kết nối socket đang hoạt động"""
        self.is_running = False

        with self.lock:
            for sock in list(self.clients.keys()):
                try:
                    sock.close()
                except Exception:
                    pass
            self.clients.clear()

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

    server = ServerCore(host=host, port=port)

    print("=== UDM_08 TCP SERVER CORE ===")
    print(f"Server đang lắng nghe trên {host}:{port}. Nhấn Ctrl + C để dừng Server.\n")

    try:
        server.start()
    except KeyboardInterrupt:
        print("\nĐang tiến hành tắt Server an toàn...")
        server.stop()
