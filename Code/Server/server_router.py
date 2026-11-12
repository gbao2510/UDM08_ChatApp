import json
import logging
import socket
import sys
import threading
 
HOST = "0.0.0.0"  # Đổi thành "127.0.0.1" nếu chỉ muốn chạy thử trên máy local
PORT = 5000
BUFFER_SIZE = 4096
MAX_FRAME_SIZE = 1_000_000
MAX_USERNAME_LENGTH = 32
 
 
# =====================================================================
# TIỆN ÍCH DÙNG CHUNG
# =====================================================================
 
def configure_utf8_console():
    """Ép stdout/stderr dùng UTF-8 để print/log không lỗi khi có emoji, tiếng Việt."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
 
 
def has_invalid_unicode(value):
    """
    Kiểm tra đệ quy (cả key lẫn value) xem có chuỗi nào không thể mã hóa UTF-8.
    Ví dụ: surrogate lẻ "\\ud83d" - json.loads chấp nhận nhưng .encode("utf-8") sẽ lỗi.
    """
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            try:
                item.encode("utf-8")
            except UnicodeEncodeError:
                return True
        elif isinstance(item, dict):
            stack.extend(item.keys())
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
    return False
 
 
def encode_message(data):
    """Chuyển dictionary thành JSON UTF-8, kết thúc bằng newline."""
    if not isinstance(data, dict):
        raise ValueError("Message must be a JSON object.")
 
    separators = (",", ":")
 
    try:
        # Giữ nguyên emoji/tiếng Việt dưới dạng UTF-8 thật.
        payload = json.dumps(data, ensure_ascii=False, separators=separators)
        return (payload + "\n").encode("utf-8")
    except UnicodeEncodeError:
        # Dự phòng: escape toàn bộ ký tự không phải ASCII, vẫn là JSON hợp lệ.
        payload = json.dumps(data, ensure_ascii=True, separators=separators)
        return (payload + "\n").encode("ascii")
 
 
def make_error(code, message):
    """Tạo thông báo lỗi gửi về Client."""
    return {
        "type": "error",
        "error": {
            "code": code,
            "message": message
        }
    }
 
 
class MessageIdGenerator:
    """Bộ sinh msg_id tuần tự, dùng chung cho mọi Client (an toàn đa luồng).
    Đồng thời lưu lại nội dung các thông điệp hợp lệ để tra cứu khi có gói
    tin Reply (reply_to_id)."""
 
    def __init__(self, start=1):
        self._next = start
        self._lock = threading.Lock()
        self._messages = {}
 
    def next_id(self):
        with self._lock:
            value = self._next
            self._next += 1
            return value
 
    def register(self, message):
        """Gán msg_id tuần tự cho message rồi lưu lại để các Reply sau
        này có thể tra cứu nội dung gốc. Trả về msg_id vừa gán."""
        with self._lock:
            msg_id = self._next
            self._next += 1
            message["msg_id"] = msg_id
            self._messages[msg_id] = message
            return msg_id
 
    def get_message(self, msg_id):
        """Tra cứu nội dung gốc theo msg_id. Trả về None nếu không có."""
        with self._lock:
            return self._messages.get(msg_id)
 
 
# =====================================================================
# SERVER ROUTER: TÁCH GÓI, KIỂM TRA UTF-8/JSON, GÁN msg_id
# =====================================================================
 
class ServerRouter:
    """
    Mỗi Client có 1 ServerRouter riêng (buffer riêng, không trộn luồng TCP),
    nhưng dùng chung 1 MessageIdGenerator nên msg_id là duy nhất toàn Server.
    """
 
    def __init__(self, max_frame_size=MAX_FRAME_SIZE, id_generator=None):
        self.buffer = bytearray()
        self.max_frame_size = max_frame_size
        self.id_generator = id_generator or MessageIdGenerator()
        # True khi đang bỏ qua phần còn lại của 1 gói quá lớn (đến khi gặp '\n').
        self.discarding = False
 
    @staticmethod
    def _too_large():
        return {
            "ok": False,
            "error": make_error(
                "MESSAGE_TOO_LARGE",
                "Thong diep vuot qua kich thuoc cho phep."
            )
        }
 
    def feed_data(self, data):
        """
        Nhận một phần dữ liệu TCP, trả về danh sách thông điệp hoàn chỉnh hoặc lỗi.
 
        Tách frame theo byte b"\\n" an toàn với UTF-8 (0x0A không bao giờ nằm trong
        chuỗi đa byte), và chỉ giải mã khi frame đã đủ, nên emoji bị cắt đôi giữa
        hai lần recv() vẫn được ghép đúng.
        """
        if not isinstance(data, (bytes, bytearray)):
            return [{
                "ok": False,
                "error": make_error(
                    "INVALID_INPUT_TYPE",
                    "Du lieu dau vao phai la bytes."
                )
            }]
 
        results = []
        data = bytes(data)
 
        # Đang bỏ qua phần đuôi của gói quá lớn: chờ đến '\n' rồi mới xử lý tiếp,
        # tránh phần đuôi bị hiểu nhầm thành 1 gói JSON mới.
        if self.discarding:
            newline_pos = data.find(b"\n")
            if newline_pos == -1:
                return results
            data = data[newline_pos + 1:]
            self.discarding = False
 
        self.buffer.extend(data)
 
        while True:
            newline_pos = self.buffer.find(b"\n")
            if newline_pos == -1:
                break
 
            frame = bytes(self.buffer[:newline_pos])
            del self.buffer[:newline_pos + 1]
 
            if not frame.strip():
                continue
 
            if len(frame) > self.max_frame_size:
                results.append(self._too_large())
                continue
 
            results.append(self.parse_frame(frame))
 
        # Chưa thấy '\n' mà buffer đã vượt giới hạn: báo lỗi, bỏ phần đã nhận
        # và tiếp tục bỏ phần còn lại của gói này.
        if len(self.buffer) > self.max_frame_size:
            self.buffer.clear()
            self.discarding = True
            results.append(self._too_large())
 
        return results
 
    def parse_frame(self, frame):
        """Kiểm tra UTF-8 nghiêm ngặt, JSON object, Unicode hợp lệ và gán msg_id."""
        try:
            # "utf-8-sig": tự bỏ BOM nếu có, còn lại vẫn là UTF-8 nghiêm ngặt.
            text = frame.decode("utf-8-sig")
        except UnicodeDecodeError:
            return {
                "ok": False,
                "error": make_error(
                    "INVALID_ENCODING",
                    "Du lieu phai duoc ma hoa bang UTF-8 hop le."
                )
            }
 
        try:
            message = json.loads(text)
        except json.JSONDecodeError as exc:
            return {
                "ok": False,
                "error": make_error(
                    "INVALID_JSON",
                    f"JSON khong hop le tai dong {exc.lineno}, "
                    f"cot {exc.colno}: {exc.msg}."
                )
            }
 
        if not isinstance(message, dict):
            return {
                "ok": False,
                "error": make_error(
                    "JSON_OBJECT_REQUIRED",
                    "Thong diep JSON phai la mot object."
                )
            }
 
        if has_invalid_unicode(message):
            return {
                "ok": False,
                "error": make_error(
                    "INVALID_UNICODE",
                    "Chuoi chua ky tu Unicode khong hop le "
                    "(surrogate le trong emoji)."
                )
            }
 
        # Neu la goi tin Reply, tim noi dung goc dua tren reply_to_id
        # TRUOC khi gan msg_id va luu thong diep hien tai.
        reply_result = None
        if "reply_to_id" in message:
            reply_result = self._resolve_reply(message["reply_to_id"])
            if not reply_result["ok"]:
                return reply_result
 
        # Server tự cấp msg_id (ghi đè nếu Client có gửi kèm) và lưu lại
        # để các Reply trong tương lai có thể tra cứu.
        self.id_generator.register(message)
 
        if reply_result is not None:
            message["reply_to"] = reply_result["original"]
 
        return {
            "ok": True,
            "message": message
        }
 
    def _resolve_reply(self, reply_to_id):
        """Kiểm tra reply_to_id và tra cứu nội dung gốc tương ứng."""
        if not isinstance(reply_to_id, int) or isinstance(reply_to_id, bool):
            return {
                "ok": False,
                "error": make_error(
                    "INVALID_REPLY_TO_ID",
                    "reply_to_id phai la so nguyen (msg_id)."
                )
            }
 
        original = self.id_generator.get_message(reply_to_id)
 
        if original is None:
            return {
                "ok": False,
                "error": make_error(
                    "REPLY_NOT_FOUND",
                    f"Khong tim thay thong diep goc voi msg_id={reply_to_id}."
                )
            }
 
        return {
            "ok": True,
            "original": original
        }
 
 
# =====================================================================
# SERVER CORE: KẾT NỐI, ĐĂNG NHẬP, DANH SÁCH ONLINE
# =====================================================================
 
def validate_username(raw_username):
    """Trả về (username_đã_chuẩn_hóa, None) nếu hợp lệ, ngược lại (None, (code, message))."""
    if not isinstance(raw_username, str):
        return None, ("INVALID_USERNAME", "Username phai la chuoi.")
 
    username = raw_username.strip()
 
    if not username:
        return None, ("INVALID_USERNAME", "Username khong duoc de trong.")
 
    if len(username) > MAX_USERNAME_LENGTH:
        return None, (
            "INVALID_USERNAME",
            f"Username toi da {MAX_USERNAME_LENGTH} ky tu."
        )
 
    # Chặn ký tự điều khiển (xuống dòng, tab...) để không làm hỏng log/giao thức.
    if not username.isprintable():
        return None, ("INVALID_USERNAME", "Username chua ky tu khong hop le.")
 
    return username, None
 
 
class ServerCore:
    def __init__(self, host=HOST, port=PORT):
        # Địa chỉ IP (0.0.0.0 chấp nhận kết nối từ mọi card mạng) và cổng lắng nghe
        self.host = host
        self.port = port
        # Socket chính của Server và cờ trạng thái chạy/dừng
        self.server_socket = None
        self.is_running = False
 
        # Danh sách Client đã đăng nhập: {client_socket: username}
        self.clients = {}
        # Khóa gửi riêng cho từng socket (kể cả Client chưa đăng nhập):
        # {client_socket: Lock}. Tránh 2 luồng cùng sendall() làm lẫn byte.
        self.send_locks = {}
        # Khóa bảo vệ self.clients và self.send_locks
        self.lock = threading.Lock()
 
        # msg_id dùng chung cho mọi Client
        self.id_generator = MessageIdGenerator()
 
        configure_utf8_console()
        self.setup_logger()
 
    def setup_logger(self):
        """Cấu hình ghi log ra Console và file server.log"""
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
 
    def get_online_users(self):
        """Lấy danh sách username của các Client đang online"""
        with self.lock:
            return list(self.clients.values())
 
    def send_packet(self, client_socket, packet_dict):
        """Gửi 1 gói tin JSON (UTF-8, kết thúc '\\n') tới 1 Client cụ thể"""
        with self.lock:
            send_lock = self.send_locks.get(client_socket)
 
        # Socket đã bị dọn dẹp (Client đã thoát) thì không gửi nữa.
        if send_lock is None:
            return False
 
        try:
            data_to_send = encode_message(packet_dict)
            with send_lock:
                client_socket.sendall(data_to_send)
            return True
        except Exception as e:
            self.logger.error(f"Lỗi khi gửi dữ liệu tới Client: {e}")
            return False
 
    def broadcast_online_list(self, exclude_socket=None):
        """
        Gửi danh sách online mới nhất tới các Client đã đăng nhập.
        exclude_socket: socket của Client vừa vào (đã nhận login_ack nên bỏ qua).
        """
        # Lấy danh sách tên và danh sách socket trong cùng 1 lần khóa để khớp nhau
        with self.lock:
            online_users = list(self.clients.values())
            target_clients = list(self.clients.keys())
 
        packet = {
            "type": "user_list",
            "action": "update",
            "online_users": online_users
        }
 
        self.logger.info(f"[BROADCAST] Gửi danh sách online {online_users} tới các client khác...")
 
        for sock in target_clients:
            if sock == exclude_socket:
                continue
            self.send_packet(sock, packet)
 
    def register_client(self, client_socket, username):
        """Thêm Client vào danh sách online. Trả về False nếu username đã có người dùng."""
        with self.lock:
            # Kiểm tra trùng tên và thêm vào trong cùng 1 lần khóa để tránh 2 Client
            # đăng nhập cùng tên cùng lúc (không phân biệt hoa/thường).
            for existing in self.clients.values():
                if existing.casefold() == username.casefold():
                    return False
            self.clients[client_socket] = username
            return True
 
    def start(self):
        """Khởi động TCP Socket Server và bắt đầu lắng nghe kết nối"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
 
            self.is_running = True
            self.logger.info(f"Server đã khởi động thành công trên cổng {self.port} (IP: {self.host})")
 
            self.accept_clients()
 
        except Exception as e:
            self.logger.error(f"Lỗi khởi động Server: {e}")
        finally:
            self.stop()
 
    def accept_clients(self):
        """Vòng lặp đón nhận từng Client mới kết nối tới Server"""
        self.logger.info("Đang chờ Client kết nối tới...")
 
        while self.is_running:
            try:
                client_socket, client_address = self.server_socket.accept()
                self.logger.info(f"Client mới kết nối thành công từ địa chỉ: {client_address}")
 
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address),
                    name=f"Thread-{client_address[1]}",
                    daemon=True
                )
                client_thread.start()
 
            except Exception as e:
                if self.is_running:
                    self.logger.error(f"Lỗi khi tiếp nhận kết nối Client: {e}")
                break
 
    def process_login(self, client_socket, client_address, message, current_username):
        """Xử lý gói login. Trả về username hiện tại của Client sau khi xử lý."""
 
        def reject(code, text):
            self.logger.warning(f"Từ chối đăng nhập từ {client_address}: [{code}] {text}")
            self.send_packet(client_socket, {
                "type": "login_ack",
                "status": "error",
                "error": {"code": code, "message": text}
            })
 
        # Mỗi kết nối chỉ đăng nhập 1 lần
        if current_username is not None:
            reject("ALREADY_LOGGED_IN", "Ban da dang nhap roi.")
            return current_username
 
        # Không gửi username thì đặt tên tạm theo Port
        raw_username = message.get("username", f"User_{client_address[1]}")
        username, error = validate_username(raw_username)
        if error:
            reject(*error)
            return None
 
        if not self.register_client(client_socket, username):
            reject("USERNAME_TAKEN", "Username da co nguoi su dung.")
            return None
 
        self.logger.info(f"==> Client A [{username}] đã vào hệ thống.")
 
        # 1. login_ack cho CHÍNH Client vừa vào (kèm danh sách online hiện tại)
        self.send_packet(client_socket, {
            "type": "login_ack",
            "status": "success",
            "username": username,
            "online_users": self.get_online_users()
        })
        self.logger.info(f"Đã gửi login_ack cho [{username}].")
 
        # 2. Broadcast danh sách mới cho CÁC CLIENT KHÁC
        self.broadcast_online_list(exclude_socket=client_socket)
 
        return username
 
    def process_message(self, client_socket, client_address, message, current_username):
        """Điều phối 1 thông điệp đã hợp lệ. Trả về username hiện tại của Client."""
        msg_type = message.get("type")
 
        if msg_type == "login":
            return self.process_login(client_socket, client_address, message, current_username)
 
        # Các loại gói khác bắt buộc phải đăng nhập trước
        if current_username is None:
            self.logger.warning(f"Client {client_address} gửi '{msg_type}' khi chưa đăng nhập.")
            self.send_packet(client_socket, make_error(
                "NOT_LOGGED_IN",
                "Ban phai dang nhap (type=login) truoc khi gui tin nhan."
            ))
            return current_username
 
        # Tin nhắn thường, broadcast sang các client khác
        if msg_type in ("msg", "message"):
            with self.lock:
                targets = [s for s in self.clients if s != client_socket]
            for sock in targets:
                self.send_packet(sock, message)
            self.logger.info(f"Broadcast msg từ [{current_username}] tới {len(targets)} client")
            return current_username

        # Tin nhắn thường khác, ping,... (xử lý chi tiết ở các tuần sau)
        self.logger.info(
            f"Nhận tin nhắn loại '{msg_type}' (msg_id={message['msg_id']}) "
            f"từ [{current_username}]: {message}"
        )
        return current_username
 
    def handle_client(self, client_socket, client_address):
        """Chạy trên luồng riêng để xử lý giao tiếp với 1 Client"""
        current_username = None
        # Mỗi Client có Router riêng (buffer riêng), dùng chung bộ sinh msg_id
        router = ServerRouter(id_generator=self.id_generator)
 
        with self.lock:
            self.send_locks[client_socket] = threading.Lock()
 
        try:
            while self.is_running:
                data = client_socket.recv(BUFFER_SIZE)
 
                if not data:
                    self.logger.info(f"Client {client_address} ({current_username}) đã ngắt kết nối.")
                    break
 
                for result in router.feed_data(data):
                    if not result["ok"]:
                        error_packet = result["error"]
                        detail = error_packet["error"]
                        self.logger.warning(
                            f"Gói tin lỗi từ {client_address}: "
                            f"[{detail['code']}] {detail['message']}"
                        )
                        self.send_packet(client_socket, error_packet)
                        continue
 
                    current_username = self.process_message(
                        client_socket, client_address, result["message"], current_username
                    )
 
        except ConnectionResetError:
            self.logger.warning(f"Client {client_address} ({current_username}) bị ngắt kết nối đột ngột!")
        except Exception as e:
            self.logger.error(f"Lỗi xử lý Client {client_address} ({current_username}): {e}")
        finally:
            # DỌN DẸP KHI CLIENT THOÁT
            with self.lock:
                self.clients.pop(client_socket, None)
                self.send_locks.pop(client_socket, None)
 
            try:
                client_socket.close()
            except Exception:
                pass
 
            self.logger.info(f"Đã giải phóng tài nguyên của [{current_username}] ({client_address}).")
 
            # Client đã đăng nhập rời đi: gửi user_leave và cập nhật lại danh sách online cho những người còn lại
            if current_username:
                leave_packet = {
                    "type": "user_leave",
                    "username": current_username
                }
                with self.lock:
                    remaining_sockets = list(self.clients.keys())
                for sock in remaining_sockets:
                    self.send_packet(sock, leave_packet)
                self.broadcast_online_list()
 
    def stop(self):
        """Dừng Server và giải phóng toàn bộ tài nguyên socket (gọi nhiều lần vẫn an toàn)"""
        self.is_running = False
 
        with self.lock:
            sockets = list(self.send_locks.keys())  # gồm cả Client chưa đăng nhập
            self.clients.clear()
            self.send_locks.clear()
 
        for sock in sockets:
            try:
                sock.shutdown(socket.SHUT_RDWR)  # đánh thức luồng đang chờ recv()
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
 
        if self.server_socket:
            try:
                self.server_socket.close()
                self.logger.info("Đã đóng Socket Server chính.")
            except Exception as e:
                self.logger.error(f"Lỗi khi đóng Socket Server chính: {e}")
            finally:
                self.server_socket = None
 
 
def main():
    server = ServerCore(host=HOST, port=PORT)
 
    print("=== UDM_08 TCP SERVER (TUẦN 2 - ĐỒNG BỘ DANH SÁCH ONLINE) ===")
    print("Server đang chạy. Nhấn Ctrl + C để dừng Server.\n")
 
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nĐang tắt Server an toàn...")
        server.stop()
 
 
if __name__ == "__main__":
    main()