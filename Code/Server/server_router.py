import json
import logging
import random
import socket
import sys
import threading
import time
 
HOST = "0.0.0.0"  # Đổi thành "127.0.0.1" nếu chỉ muốn chạy thử trên máy local
PORT = 5000
BUFFER_SIZE = 4096
MAX_FRAME_SIZE = 1_000_000
MAX_USERNAME_LENGTH = 32

# --- Cấu hình phát hiện mất kết nối ---
HEARTBEAT_INTERVAL = 15      # giây không có dữ liệu -> gửi ping
IDLE_TIMEOUT = 60            # giây không nhận được gì từ đối phương -> coi là chết
ACCEPT_POLL_INTERVAL = 1.0   # accept() thức dậy định kỳ để kiểm tra cờ dừng
MAX_ACCEPT_ERRORS = 20       # số lỗi accept() liên tiếp tối đa trước khi bỏ cuộc
THREAD_JOIN_TIMEOUT = 2.0    # chờ tối đa mỗi luồng Client khi stop()
HEARTBEAT_TYPES = ("ping", "pong")  # gói kiểm tra sống: không cấp msg_id, không lưu lịch sử

# --- Cấu hình reconnect của Client ---
RECONNECT_INITIAL_DELAY = 1.0
RECONNECT_MAX_DELAY = 30.0
RECONNECT_FACTOR = 2.0
CONNECT_TIMEOUT = 5.0
 
 
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
 
 
def close_socket_quietly(sock):
    """Đóng socket triệt để và KHÔNG BAO GIỜ ném lỗi (gọi nhiều lần vẫn an toàn).
    shutdown() trước để đánh thức luồng khác đang bị kẹt trong recv()/accept()."""
    if sock is None:
        return
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except (OSError, ValueError):
        pass
    try:
        sock.close()
    except (OSError, ValueError):
        pass


def enable_tcp_keepalive(sock, idle=30, interval=10, count=3):
    """Bật TCP keepalive để hệ điều hành tự phát hiện kết nối "nửa chết"
    (rút dây mạng, tắt nguồn máy - không có FIN/RST). Trả về True nếu bật được."""
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if hasattr(socket, "SIO_KEEPALIVE_VALS"):  # Windows
            sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, idle * 1000, interval * 1000))
        else:
            if hasattr(socket, "TCP_KEEPIDLE"):  # Linux
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, idle)
            elif hasattr(socket, "TCP_KEEPALIVE"):  # macOS
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPALIVE, idle)
            if hasattr(socket, "TCP_KEEPINTVL"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval)
            if hasattr(socket, "TCP_KEEPCNT"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, count)
        return True
    except (OSError, AttributeError, ValueError):
        return False


def compute_backoff(attempt, initial=RECONNECT_INITIAL_DELAY, factor=RECONNECT_FACTOR,
                    maximum=RECONNECT_MAX_DELAY, jitter=0.2):
    """Thời gian chờ (giây) trước lần reconnect thứ `attempt` (bắt đầu từ 1).
    Tăng dần theo cấp số nhân, có chặn trên và nhiễu ngẫu nhiên (jitter) để
    nhiều Client không cùng dồn vào Server một lúc sau khi Server sống lại."""
    exponent = min(max(attempt - 1, 0), 30)  # tránh OverflowError khi mất mạng rất lâu
    delay = min(maximum, initial * (factor ** exponent))
    if jitter:
        delay *= random.uniform(1 - jitter, 1 + jitter)
    return min(maximum, delay)


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

    @property
    def pending_bytes(self):
        """Số byte dở dang (chưa đủ 1 gói) đang nằm trong buffer."""
        return len(self.buffer)

    def reset(self):
        """Giải phóng buffer khi Client mất kết nối: bỏ nửa gói dở dang để khỏi
        giữ bộ nhớ và không lẫn sang kết nối khác."""
        self.buffer = bytearray()
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
 
        # Gói kiểm tra sống (ping/pong) không phải tin nhắn: không cấp msg_id,
        # không lưu vào lịch sử (tránh "ăn" msg_id và làm phình bộ nhớ).
        if message.get("type") in HEARTBEAT_TYPES:
            return {
                "ok": True,
                "message": message
            }

        # Neu la goi tin Reply, tim noi dung goc dua tren reply_to_id hoac reply_to_msg_id
        # TRUOC khi gan msg_id va luu thong diep hien tai.
        reply_result = None
        reply_id = message.get("reply_to_id")
        if reply_id is None:
            reply_id = message.get("reply_to_msg_id")

        if "reply_to_id" in message or "reply_to_msg_id" in message:
            reply_result = self._resolve_reply(reply_id)
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
    def __init__(self, host=HOST, port=PORT, heartbeat_interval=HEARTBEAT_INTERVAL,
                 idle_timeout=IDLE_TIMEOUT, log_file="server.log"):
        # Địa chỉ IP (0.0.0.0 chấp nhận kết nối từ mọi card mạng) và cổng lắng nghe
        self.host = host
        self.port = port
        # Phát hiện mất kết nối: sau heartbeat_interval giây không nhận được gì thì
        # gửi ping; sau idle_timeout giây vẫn im lặng thì coi Client đã chết.
        self.heartbeat_interval = heartbeat_interval
        self.idle_timeout = idle_timeout
        # Socket chính của Server và cờ trạng thái chạy/dừng
        self.server_socket = None
        self.is_running = False
 
        # Được set khi Server đã bind + listen xong (tiện cho test / khởi động ở luồng khác)
        self.ready = threading.Event()

        # Danh sách Client đã đăng nhập: {client_socket: username}
        self.clients = {}
        # Khóa gửi riêng cho từng socket (kể cả Client chưa đăng nhập):
        # {client_socket: Lock}. Tránh 2 luồng cùng sendall() làm lẫn byte.
        # Cũng là "sổ đăng ký" mọi socket đang sống: có trong đây = chưa được dọn dẹp.
        self.send_locks = {}
        # Khóa bảo vệ self.clients và self.send_locks
        # Các luồng xử lý Client đang chạy, để stop() chờ chúng thoát hẳn
        self.client_threads = set()
        # Khóa bảo vệ self.clients, self.send_locks và self.client_threads
        self.lock = threading.Lock()
 

        # msg_id dùng chung cho mọi Client
        self.id_generator = MessageIdGenerator()
 

        configure_utf8_console()
        self.setup_logger(log_file=log_file)
 
    def setup_logger(self, log_file="server.log"):
        """Cấu hình ghi log ra Console và file server.log (log_file=None: chỉ ra Console)"""
        log_format = "%(asctime)s - [%(levelname)s] - (%(threadName)s) - %(message)s"
        handlers = [logging.StreamHandler(sys.stdout)]
        if log_file:
            handlers.insert(0, logging.FileHandler(log_file, encoding="utf-8"))
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=handlers
        )
        self.logger = logging.getLogger("ServerCore")
 

    def get_online_users(self):
        """Lấy danh sách username của các Client đang online"""
        with self.lock:
            return list(self.clients.values())
 
    def send_packet(self, client_socket, packet_dict):
        """Gửi 1 gói tin JSON (UTF-8, kết thúc '\\n') tới 1 Client cụ thể"""
        """Gửi 1 gói tin JSON (UTF-8, kết thúc '\\n') tới 1 Client cụ thể.
        Nếu gửi lỗi do mất kết nối thì dọn dẹp luôn Client đó (luồng gửi/broadcast
        phát hiện Client chết sớm hơn luồng recv, nhất là khi kết nối "nửa chết")."""
        with self.lock:
            send_lock = self.send_locks.get(client_socket)
 

        # Socket đã bị dọn dẹp (Client đã thoát) thì không gửi nữa.
        if send_lock is None:
            return False
 

        try:
            data_to_send = encode_message(packet_dict)
        except (ValueError, TypeError) as e:
            # Lỗi dữ liệu, KHÔNG phải lỗi kết nối: không được ngắt Client vì lỗi này.
            self.logger.error(f"Không mã hóa được gói tin để gửi: {e}")
            return False

        try:
            with send_lock:
                client_socket.sendall(data_to_send)
            return True
        except OSError as e:
            # Gồm BrokenPipe/ConnectionReset/Aborted và cả timeout khi Client không đọc.
            # Gửi dở dang làm hỏng luồng byte nên bắt buộc phải đóng hẳn socket.
            self.logger.warning(f"Lỗi khi gửi dữ liệu tới Client, ngắt kết nối: {e}")
            self.disconnect_client(client_socket)
            return False
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
            # Socket đã bị dọn dẹp (vừa mất kết nối) thì không đăng ký "người ma"
            # vào danh sách online, vì sẽ không còn ai dọn nó nữa.
            if client_socket not in self.send_locks:
                raise ConnectionError("Socket da bi don dep truoc khi dang nhap xong.")

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
 
            # accept() thức dậy định kỳ để kiểm tra cờ dừng (stop() từ luồng khác,
            # Ctrl+C trên Windows) thay vì bị kẹt vô hạn.
            self.server_socket.settimeout(ACCEPT_POLL_INTERVAL)
            self.port = self.server_socket.getsockname()[1]  # hỗ trợ port=0 (cổng tự chọn)

            self.is_running = True
            self.logger.info(f"Server đã khởi động thành công trên cổng {self.port} (IP: {self.host})")
 
            self.ready.set()

            self.accept_clients()
 

        except Exception as e:
            self.logger.error(f"Lỗi khởi động Server: {e}")
        finally:
            self.stop()
 

    def configure_client_socket(self, client_socket):
        """Thiết lập socket của Client vừa kết nối: timeout, TCP_NODELAY, keepalive."""
        # Timeout áp dụng cho cả recv() lẫn sendall(): recv() hết giờ -> gửi ping,
        # sendall() hết giờ -> Client không chịu đọc, bị ngắt.
        client_socket.settimeout(self.heartbeat_interval)
        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        enable_tcp_keepalive(client_socket)

    def accept_clients(self):
        """Vòng lặp đón nhận từng Client mới kết nối tới Server"""
        """Vòng lặp đón nhận từng Client mới kết nối tới Server.
        Lỗi tạm thời của 1 lần accept() không được làm sập cả Server."""
        self.logger.info("Đang chờ Client kết nối tới...")
 
        consecutive_errors = 0

        while self.is_running:
            server_socket = self.server_socket
            if server_socket is None:
                break

            try:
                client_socket, client_address = server_socket.accept()
            except socket.timeout:
                continue  # chỉ để kiểm tra lại is_running
            except OSError as e:
                # Server đang dừng (socket chính đã bị đóng): thoát bình thường.
                if not self.is_running or server_socket.fileno() == -1:
                    break
                # Lỗi tạm thời (Client hủy kết nối giữa chừng, hết file descriptor...):
                # ghi log, nghỉ một chút rồi accept tiếp.
                consecutive_errors += 1
                self.logger.error(
                    f"Lỗi khi tiếp nhận kết nối Client ({consecutive_errors}/{MAX_ACCEPT_ERRORS}): {e}"
                )
                if consecutive_errors >= MAX_ACCEPT_ERRORS:
                    self.logger.critical("Quá nhiều lỗi accept() liên tiếp, Server dừng nhận kết nối.")
                    break
                time.sleep(min(0.1 * consecutive_errors, 2.0))
                continue

            consecutive_errors = 0
            self.logger.info(f"Client mới kết nối thành công từ địa chỉ: {client_address}")

            client_thread = None
            try:
                self.configure_client_socket(client_socket)

                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address),
                    name=f"Thread-{client_address[1]}",
                    daemon=True
                )
                # Đăng ký socket + luồng TRƯỚC khi chạy luồng, để stop() không bỏ sót.
                with self.lock:
                    self.send_locks[client_socket] = threading.Lock()
                    self.client_threads.add(client_thread)
                client_thread.start()
 

            except Exception as e:
                if self.is_running:
                    self.logger.error(f"Lỗi khi tiếp nhận kết nối Client: {e}")
                break
 
                # Không dựng được luồng/socket cho Client này: dọn dẹp rồi tiếp tục phục vụ người khác.
                self.logger.error(f"Không thể phục vụ Client {client_address}: {e}")
                with self.lock:
                    self.client_threads.discard(client_thread)
                self.disconnect_client(client_socket)

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
 

        # Gói kiểm tra sống: không cần đăng nhập, không broadcast.
        if msg_type == "ping":
            self.send_packet(client_socket, {"type": "pong"})
            return current_username
        if msg_type == "pong":
            return current_username

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
 
        last_seen = time.monotonic()  # lần cuối nhận được bất kỳ dữ liệu nào từ Client
        reason = "Client đã ngắt kết nối."

        with self.lock:
            self.send_locks[client_socket] = threading.Lock()
 
            # Đã được đăng ký khi accept; setdefault chỉ để an toàn nếu gọi trực tiếp.
            self.send_locks.setdefault(client_socket, threading.Lock())

        try:
            while self.is_running:
                try:
                    data = client_socket.recv(BUFFER_SIZE)
                except socket.timeout:
                    # Im lặng quá lâu: Client đã chết (rút mạng, treo máy...) hay chỉ đang rảnh?
                    idle = time.monotonic() - last_seen
                    if idle >= self.idle_timeout:
                        reason = f"Client không phản hồi sau {idle:.0f}s, coi như mất kết nối."
                        self.logger.warning(f"Client {client_address} ({current_username}): {reason}")
                        break
                    # Còn trong hạn: gửi ping. Gửi lỗi -> send_packet đã dọn dẹp Client này.
                    if not self.send_packet(client_socket, {"type": "ping"}):
                        reason = "Không gửi được ping, Client đã mất kết nối."
                        break
                    continue

                if not data:
                    if router.pending_bytes:
                        self.logger.warning(
                            f"Client {client_address} đóng kết nối khi còn {router.pending_bytes} "
                            f"byte dở dang, bỏ phần dữ liệu này."
                        )
                    self.logger.info(f"Client {client_address} ({current_username}) đã ngắt kết nối.")
                    break
 

                last_seen = time.monotonic()

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
        except ConnectionError as e:
            # ConnectionReset / ConnectionAborted / BrokenPipe: Client tắt đột ngột (kill app, rút mạng...)
            reason = f"Client bị ngắt kết nối đột ngột: {e}"
            self.logger.warning(f"Client {client_address} ({current_username}) bị ngắt kết nối đột ngột! ({e})")
        except OSError as e:
            reason = f"Lỗi socket: {e}"
            if self.is_running:
                self.logger.warning(f"Lỗi socket với Client {client_address} ({current_username}): {e}")
            # Server đang dừng: socket bị stop() đóng, đây là chuyện bình thường.
        except Exception as e:
            reason = f"Lỗi không mong đợi: {e}"
            self.logger.error(f"Lỗi xử lý Client {client_address} ({current_username}): {e}")
        finally:
            # DỌN DẸP KHI CLIENT THOÁT - luôn chạy, dù thoát bằng cách nào
            router.reset()  # bỏ buffer dở dang
            with self.lock:
                self.client_threads.discard(threading.current_thread())
            self.disconnect_client(client_socket, reason)
 

    def disconnect_client(self, client_socket, reason=None):
        """
        Dọn dẹp TRIỆT ĐỂ 1 Client: gỡ khỏi mọi danh sách, đóng socket, báo cho những
        người còn lại. Gọi từ luồng nào, bao nhiêu lần cũng an toàn (idempotent) - luồng
        recv, luồng broadcast và stop() có thể cùng phát hiện 1 Client chết.
        Trả về True nếu lần gọi này là lần thực sự dọn dẹp.
        """
        with self.lock:
            was_tracked = client_socket in self.send_locks or client_socket in self.clients
            username = self.clients.pop(client_socket, None)
            self.send_locks.pop(client_socket, None)

        # Luôn đóng socket (đóng lại socket đã đóng là vô hại) để không bao giờ rò rỉ fd.
        close_socket_quietly(client_socket)

        if not was_tracked:
            return False

        if reason:
            self.logger.info(f"Ngắt kết nối [{username}]: {reason}")

        # Chỉ lần dọn dẹp đầu tiên mới thông báo, nên user_leave không bị gửi lặp.
        if username:
            leave_packet = {
                "type": "user_leave",
                "username": username
            }
            with self.lock:
                remaining_sockets = list(self.clients.keys())
            for sock in remaining_sockets:
                self.send_packet(sock, leave_packet)
            self.broadcast_online_list()

        return True

    def stop(self):
        """Dừng Server và giải phóng toàn bộ tài nguyên socket (gọi nhiều lần vẫn an toàn)"""
        """Dừng Server và giải phóng toàn bộ tài nguyên socket + luồng (gọi nhiều lần vẫn an toàn)"""
        self.is_running = False
 

        with self.lock:
            sockets = list(self.send_locks.keys()) + [s for s in self.clients if s not in self.send_locks]
            threads = list(self.client_threads)
            server_socket, self.server_socket = self.server_socket, None
            self.clients.clear()
            self.send_locks.clear()

        # Đóng socket Client: shutdown() đánh thức các luồng đang chờ recv()
        for sock in sockets:
            close_socket_quietly(sock)

        if server_socket:
            try:
                server_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                server_socket.close()
                self.logger.info("Đã đóng Socket Server chính.")
            except Exception as e:
                self.logger.error(f"Lỗi khi đóng Socket Server chính: {e}")
 
 

        # Chờ các luồng Client thoát hẳn để không để lại luồng rác.
        current = threading.current_thread()
        for thread in threads:
            if thread is not current:
                thread.join(timeout=THREAD_JOIN_TIMEOUT)

        with self.lock:
            self.client_threads.clear()
        self.ready.clear()


# =====================================================================
# CLIENT TỰ ĐỘNG KẾT NỐI LẠI
# =====================================================================

class ReconnectingClient:
    """
    Client TCP tự phát hiện mất kết nối (Server sập, rớt mạng, Server im lặng) và tự
    kết nối lại với thời gian chờ tăng dần (exponential backoff + jitter).

    - Chạy trên 1 luồng nền riêng; on_message / on_state_change được gọi từ luồng đó.
    - Có username: tự gửi login sau mỗi lần (kết nối lại), nên Server thấy Client "vào lại".
    - Tự trả lời ping của Server và chủ động ping khi rảnh để phát hiện Server chết.
    - Mỗi lần mất kết nối đều đóng socket, xóa buffer; stop() đóng socket và chờ luồng thoát.

    Trạng thái: "disconnected" | "connecting" | "connected" | "reconnecting" | "stopped"
    """

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    STOPPED = "stopped"

    def __init__(self, host, port, username=None, on_message=None, on_state_change=None,
                 auto_reconnect=True, max_attempts=None,
                 initial_delay=RECONNECT_INITIAL_DELAY, max_delay=RECONNECT_MAX_DELAY,
                 factor=RECONNECT_FACTOR, jitter=0.2, connect_timeout=CONNECT_TIMEOUT,
                 heartbeat_interval=HEARTBEAT_INTERVAL, idle_timeout=IDLE_TIMEOUT,
                 max_frame_size=MAX_FRAME_SIZE):
        self.host = host
        self.port = port
        self.username = username
        self.on_message = on_message
        self.on_state_change = on_state_change
        self.auto_reconnect = auto_reconnect
        self.max_attempts = max_attempts  # số lần kết nối thất bại liên tiếp tối đa; None = vô hạn
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.factor = factor
        self.jitter = jitter
        self.connect_timeout = connect_timeout
        self.heartbeat_interval = heartbeat_interval
        self.idle_timeout = idle_timeout
        self.max_frame_size = max_frame_size

        self.logger = logging.getLogger("ReconnectingClient")
        self.reconnect_count = 0  # số lần kết nối lại THÀNH CÔNG

        self._lock = threading.Lock()       # bảo vệ _sock, _state, _thread
        self._send_lock = threading.Lock()  # tránh 2 luồng cùng sendall() làm lẫn byte
        self._sock = None
        self._state = self.DISCONNECTED
        self._thread = None
        self._stop_event = threading.Event()
        self._connected_event = threading.Event()
        self._ever_connected = False
        self._logged_in_once = False
        self._fatal = False  # lỗi không thể tự khắc phục (vd. username không hợp lệ)

    # ------------------------------------------------------------ API công khai

    @property
    def state(self):
        with self._lock:
            return self._state

    @property
    def is_connected(self):
        return self.state == self.CONNECTED

    def start(self):
        """Bắt đầu kết nối (và tự kết nối lại) ở luồng nền."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._fatal = False
            self._state = self.DISCONNECTED
            self._thread = threading.Thread(
                target=self._run, name="ReconnectingClient", daemon=True
            )
            thread = self._thread
        thread.start()

    def wait_connected(self, timeout=None):
        """Chờ đến khi kết nối thành công. Trả về True nếu đã kết nối."""
        return self._connected_event.wait(timeout)

    def send(self, packet):
        """Gửi 1 gói tin dict. Trả về False nếu đang không kết nối hoặc gửi lỗi
        (gửi lỗi sẽ kích hoạt kết nối lại)."""
        with self._lock:
            sock = self._sock
        if sock is None:
            return False

        try:
            data = encode_message(packet)
        except (ValueError, TypeError) as e:
            self.logger.error(f"Không mã hóa được gói tin để gửi: {e}")
            return False

        try:
            with self._send_lock:
                sock.sendall(data)
            return True
        except OSError as e:
            self.logger.warning(f"Lỗi khi gửi dữ liệu tới Server: {e}")
            # Đóng socket để vòng recv thoát ra và bắt đầu kết nối lại.
            self._drop_socket(sock)
            return False

    def stop(self):
        """Dừng hẳn: không kết nối lại nữa, đóng socket, chờ luồng nền thoát. Gọi nhiều lần vẫn an toàn."""
        self._stop_event.set()
        self._drop_socket()

        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=self.connect_timeout + THREAD_JOIN_TIMEOUT)

        self._set_state(self.STOPPED)

    # ------------------------------------------------------------ nội bộ

    def _notify(self, callback, *args):
        if callback is None:
            return
        try:
            callback(*args)
        except Exception:
            self.logger.exception("Callback của Client ném lỗi (đã bỏ qua).")

    def _set_state(self, state, detail=None):
        with self._lock:
            if self._state == state or self._state == self.STOPPED:
                return
            self._state = state
        if state == self.CONNECTED:
            self._connected_event.set()
        else:
            self._connected_event.clear()
        self.logger.info(f"Trạng thái kết nối: {state}" + (f" ({detail})" if detail else ""))
        self._notify(self.on_state_change, state, detail)

    def _drop_socket(self, sock=None):
        """Giải phóng socket hiện tại (hoặc socket chỉ định). An toàn khi gọi nhiều lần."""
        with self._lock:
            target = sock if sock is not None else self._sock
            if target is self._sock:
                self._sock = None
        close_socket_quietly(target)

    def _run(self):
        attempt = 0  # số lần kết nối thất bại liên tiếp
        try:
            while not self._stop_event.is_set():
                self._set_state(self.RECONNECTING if self._ever_connected else self.CONNECTING)

                sock = self._open_connection()
                if sock is not None:
                    attempt = 0
                    self._run_session(sock)  # chặn đến khi mất kết nối; luôn tự dọn socket
                else:
                    attempt += 1

                if self._stop_event.is_set() or self._fatal or not self.auto_reconnect:
                    break
                if self.max_attempts is not None and attempt >= self.max_attempts:
                    self.logger.error(f"Đã thử kết nối {attempt} lần không được, từ bỏ.")
                    break

                delay = compute_backoff(
                    max(attempt, 1), self.initial_delay, self.factor, self.max_delay, self.jitter
                )
                self._set_state(self.RECONNECTING, f"thử lại sau {delay:.1f}s")
                if self._stop_event.wait(delay):  # ngủ nhưng thức dậy ngay khi stop()
                    break
        finally:
            self._drop_socket()
            self._set_state(self.STOPPED if self._stop_event.is_set() else self.DISCONNECTED)

    def _open_connection(self):
        """Mở kết nối TCP. Trả về socket đã cấu hình, hoặc None nếu thất bại."""
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.connect_timeout)
        except OSError as e:
            self.logger.warning(f"Không kết nối được tới {self.host}:{self.port}: {e}")
            return None

        try:
            sock.settimeout(self.heartbeat_interval)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            enable_tcp_keepalive(sock)
        except OSError as e:
            self.logger.warning(f"Không cấu hình được socket: {e}")
            close_socket_quietly(sock)
            return None
        return sock

    def _mark_connected(self):
        if self._ever_connected:
            self.reconnect_count += 1
        self._ever_connected = True
        self._set_state(self.CONNECTED)

    def _run_session(self, sock):
        """Chạy 1 phiên kết nối đến khi mất kết nối. Luôn giải phóng socket + buffer khi thoát."""
        buffer = bytearray()
        reason = "Mất kết nối."

        with self._lock:
            if self._stop_event.is_set():
                close_socket_quietly(sock)
                return
            self._sock = sock

        try:
            if self.username is not None:
                # Tự đăng nhập lại; CONNECTED khi nhận được login_ack thành công.
                if not self.send({"type": "login", "username": self.username}):
                    raise ConnectionError("Không gửi được gói login.")
            else:
                self._mark_connected()

            last_received = time.monotonic()

            while not self._stop_event.is_set():
                try:
                    data = sock.recv(BUFFER_SIZE)
                except socket.timeout:
                    silent = time.monotonic() - last_received
                    if silent >= self.idle_timeout:
                        reason = f"Server không phản hồi sau {silent:.0f}s."
                        break
                    # Chủ động ping để biết Server còn sống hay không.
                    if not self.send({"type": "ping"}):
                        reason = "Không gửi được ping."
                        break
                    continue

                if not data:
                    reason = "Server đã đóng kết nối."
                    break

                last_received = time.monotonic()
                buffer.extend(data)

                session_over = False
                for frame in self._extract_frames(buffer):
                    stop_reason = self._handle_frame(frame)
                    if stop_reason:
                        reason = stop_reason
                        session_over = True
                        break
                if session_over:
                    break

                if len(buffer) > self.max_frame_size:
                    reason = "Server gửi gói tin quá lớn."
                    break

        except OSError as e:  # gồm ConnectionError
            reason = f"Lỗi kết nối: {e}"
        except Exception as e:
            reason = f"Lỗi không mong đợi: {e}"
            self.logger.exception("Lỗi trong phiên kết nối của Client.")
        finally:
            buffer.clear()
            self._drop_socket(sock)
            self._set_state(self.DISCONNECTED, reason)

    @staticmethod
    def _extract_frames(buffer):
        """Tách các gói hoàn chỉnh (kết thúc bằng '\\n') ra khỏi buffer, phần dở dang ở lại."""
        frames = []
        while True:
            newline_pos = buffer.find(b"\n")
            if newline_pos == -1:
                return frames
            frame = bytes(buffer[:newline_pos])
            del buffer[:newline_pos + 1]
            if frame.strip():
                frames.append(frame)

    def _handle_frame(self, frame):
        """Xử lý 1 gói từ Server. Trả về None để tiếp tục, hoặc chuỗi lý do để kết thúc phiên."""
        try:
            message = json.loads(frame.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.logger.warning("Bỏ qua gói tin không hợp lệ từ Server.")
            return None
        if not isinstance(message, dict):
            return None

        msg_type = message.get("type")

        if msg_type == "ping":
            self.send({"type": "pong"})
            return None
        if msg_type == "pong":
            return None

        if msg_type == "login_ack":
            if message.get("status") == "success":
                self._logged_in_once = True
                self._mark_connected()
            else:
                error = message.get("error")
                code = error.get("code") if isinstance(error, dict) else None
                if code == "USERNAME_TAKEN" and self._logged_in_once:
                    # Server chưa kịp dọn phiên cũ của chính mình: thử lại sau, đừng bỏ cuộc.
                    return "Username còn bị giữ bởi phiên cũ, sẽ thử lại."
                self._fatal = True
                self._notify(self.on_message, message)
                return f"Đăng nhập bị từ chối: {code}"
            self._notify(self.on_message, message)
            return None

        self._notify(self.on_message, message)
        return None


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