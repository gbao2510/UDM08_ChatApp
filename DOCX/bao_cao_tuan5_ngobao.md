# BÁO CÁO ĐỒ ÁN — UDM08 TCP CHAT APPLICATION

**Môn học:** Lập trình mạng  
**Mã đề tài:** UDM08  
**Nhóm thực hiện:** 6 thành viên  
**Người tổng hợp báo cáo:** Ngô Gia Bảo (Nhóm trưởng)  
**Ngày cập nhật:** 19/11/2026 (Tuần 5 — Hoàn thiện)

---

## 1. Mô tả đề tài

Đề tài xây dựng ứng dụng **Chat TCP Client–Server thời gian thực** sử dụng:

- **TCP Socket** làm nền tảng truyền thông tin cậy giữa Server và nhiều Client đồng thời.
- **JSON + ký tự `\n`** làm định dạng giao thức chống dính gói tin (packet framing).
- **UTF-8** để hỗ trợ đầy đủ tiếng Việt có dấu và Emoji.
- **PyQt6** để xây dựng giao diện người dùng hiện đại (Dark Theme, Messenger-style).
- **threading** để Server xử lý nhiều client song song mà không bị blocking.

---

## 2. Kiến trúc hệ thống

### 2.1 Phân tầng kiến trúc

```
┌────────────────────────────────────────────────────────┐
│  TẦNG GIAO DIỆN (Presentation)                         │
│  gui_main.py · gui_widgets.py · gui_actions.py         │
├────────────────────────────────────────────────────────┤
│  TẦNG MẠNG CLIENT (Network – Client)                   │
│  network_worker.py  (QThread + TCP socket)             │
├────────────────────────────────────────────────────────┤
│  TẦNG GIAO THỨC CHUNG (Shared Protocol)                │
│  Code/Shared/protocol.py                               │
├────────────────────────────────────────────────────────┤
│  TẦNG ĐỊNH TUYẾN SERVER (Routing)                      │
│  server_router.py  (bytearray buffer, UTF-8/JSON)      │
├────────────────────────────────────────────────────────┤
│  TẦNG LÕI SERVER (Core)                                │
│  server_core.py  (ServerCore, threading, logging)      │
└────────────────────────────────────────────────────────┘
```

### 2.2 Luồng xử lý kết nối

1. **ServerCore.start()** → tạo socket TCP, bind `(host, port)`, gọi `socket.listen()`.
2. Với mỗi Client kết nối mới → tạo `threading.Thread(target=handle_client)`.
3. **handle_client()** → đọc dữ liệu vào `bytearray` buffer, cắt theo `\n`, đưa qua `ServerRouter.feed_data()`.
4. **ServerRouter.parse_frame()** → kiểm tra UTF-8 hợp lệ, parse JSON, kiểm tra cấu trúc, gắn `msg_id`.
5. **ServerCore** routing: `login` → xác thực username, gửi `login_ack`; `msg` → broadcast; `reply` → resolve + broadcast; `forward` → gửi 1-1.
6. Khi client ngắt kết nối → xóa khỏi `self.clients`, broadcast `user_leave`.

---

## 3. Giao thức truyền tin (Protocol)

### 3.1 Cơ chế đóng gói

Mỗi gói tin là một **JSON object** (không phải array) kết thúc bằng `\n`:

```
{"type":"msg","sender":"A","content":"Hello"}\n
```

**Lý do chọn `\n` làm phân định:**
- Đơn giản, dễ implement ở cả Server và Client.
- JSON object không bao giờ chứa ký tự `\n` thô bên trong (JSON đã escape thành `\\n`).
- Cho phép tách gói ngay cả khi TCP chia nhỏ hoặc gộp nhiều gói.

### 3.2 Xử lý TCP Packet Splitting

Client và Server đều dùng `bytearray` buffer:

```python
buf = bytearray()
while True:
    chunk = sock.recv(4096)
    buf += chunk
    while b"\n" in buf:
        line, buf = buf.split(b"\n", 1)
        msg = json.loads(line.decode("utf-8"))
        process(msg)
```

Giải quyết 2 vấn đề:
- **Packet Splitting:** TCP chia 1 gói JSON thành nhiều `recv()` → buffer ghép lại.
- **Packet Merging:** TCP gộp nhiều gói JSON vào 1 `recv()` → tách theo `\n`.

### 3.3 Danh sách loại gói tin

| `type` | Hướng | Trường bắt buộc | Mô tả |
|--------|-------|----------------|-------|
| `login` | C→S | `username`, `avatar` | Đăng nhập |
| `login_ack` | S→C | `status`, `online_users` | Kết quả đăng nhập |
| `msg` | C→S→All | `sender`, `receiver`, `content` | Chat thường |
| `reply` | C→S→All | `sender`, `content`, `reply_to_id` | Trả lời tin |
| `forward` | C→S→Target | `sender`, `receiver`, `content` | Chuyển tiếp |
| `forward_ack` | S→C | `status`, `receiver` | Xác nhận forward |
| `user_join` | S→All | `username`, `online_users` | Người mới vào |
| `user_leave` | S→All | `username`, `online_users` | Người rời phòng |
| `error` | S→C | `error.code`, `error.message` | Thông báo lỗi |

### 3.4 Mã lỗi chuẩn

| Code | HTTP tương đương | Mô tả |
|------|-----------------|-------|
| `USERNAME_TAKEN` | 409 Conflict | Tên đã có người dùng |
| `ALREADY_LOGGED_IN` | 400 Bad Request | Socket đã đăng nhập |
| `NOT_LOGGED_IN` | 401 Unauthorized | Chưa login, từ chối gói tin |
| `INVALID_JSON` | 400 Bad Request | JSON không hợp lệ |
| `REPLY_NOT_FOUND` | 404 Not Found | msg_id không tồn tại |
| `INVALID_REPLY_TO_ID` | 422 Unprocessable | reply_to_id không phải số nguyên |

---

## 4. Cấu trúc gói tin chi tiết

### 4.1 Login Flow

```
Client                              Server
  │                                   │
  │──► {"type":"login",               │
  │     "username":"Alice",           │
  │     "avatar":"avatar_user1.png"}  │
  │                                   │── Kiểm tra username hợp lệ
  │                                   │── Kiểm tra trùng lặp (case-insensitive)
  │◄── {"type":"login_ack",           │
  │     "status":"success",           │
  │     "online_users":[              │
  │       {"username":"Alice",        │
  │        "avatar":"avatar_user1.png"}
  │     ]}                            │
  │                                   │── Broadcast user_join tới tất cả
```

### 4.2 Reply Flow

```
Client A              Server               Client B
   │                    │                     │
   │── reply ──────────►│                     │
   │   reply_to_id: 5   │── _resolve_reply(5) │
   │                    │   (tra cứu msg_id=5)│
   │                    │── broadcast reply ──►│
   │                    │   kèm reply_to:{...} │
```

### 4.3 Forward Flow (1-1)

```
Client A              Server               Client B
   │                    │                     │
   │── forward ─────────►│                    │
   │   receiver:"Bob"    │── find socket(Bob)  │
   │                    │── send to Bob ──────►│
   │◄── forward_ack ────│                     │
   │    status:"success" │                    │
```

---

## 5. Mô tả chi tiết các module

### 5.1 server_core.py — Lõi TCP Server

**Tác giả:** Trần Thuận Trí  
**Lớp chính:** `ServerCore`

| Phương thức | Mô tả |
|------------|-------|
| `start()` | Tạo socket, bind, listen, vòng lặp accept |
| `stop()` | Đặt cờ `is_running=False`, đóng socket |
| `handle_client(sock, addr)` | Thread xử lý 1 client: đọc buffer, routing |
| `broadcast(data, exclude=None)` | Gửi tới tất cả client (trừ người gửi nếu cần) |
| `send_to_one(username, data)` | Gửi riêng tới 1 client theo tên |
| `get_online_users()` | Trả về list `[{username, avatar}, ...]` |
| `disconnect_client(sock)` | Dọn dẹp khi client ngắt kết nối |

**Cơ chế thread-safe:** `threading.Lock()` bảo vệ `self.clients` dictionary.  
**Logging:** Ghi ra `server.log` và Console đồng thời.

---

### 5.2 server_router.py — Bộ định tuyến JSON/UTF-8

**Tác giả:** Trương Gia Bân  
**Lớp chính:** `ServerRouter`, `MessageIdGenerator`

| Phương thức | Mô tả |
|------------|-------|
| `feed_data(raw_bytes)` | Nạp chunk bytes, trả về list kết quả parse |
| `parse_frame(line_bytes)` | Parse 1 dòng: kiểm tra UTF-8 → JSON → cấu trúc |
| `_resolve_reply(reply_id)` | Tra cứu tin nhắn gốc theo msg_id |
| `encode_message(data)` | Dict → JSON bytes + `\n` |

**Đặc điểm nổi bật:**
- Reject lone surrogate (ký tự UTF-16 bị cắt đôi).
- Reject JSON array (chỉ chấp nhận object).
- Frame size limit để tránh DoS.
- Hỗ trợ cả `reply_to_id` và `reply_to_msg_id` (tương thích ngược).

---

### 5.3 network_worker.py — Luồng mạng Client

**Tác giả:** Lý Huỳnh Bích Trâm  
**Lớp chính:** `NetworkClient(QThread)`

| Signal | Kiểu | Mô tả |
|--------|------|-------|
| `connected` | — | Kết nối thành công |
| `disconnected` | — | Mất kết nối |
| `message_received` | `dict` | Nhận được gói tin mới |
| `error_occurred` | `str` | Lỗi mạng |

| Phương thức | Mô tả |
|------------|-------|
| `run()` | Vòng lặp nhận: bytearray buffer + split `\n` + decode UTF-8 |
| `send_data(packet_dict)` | Encode JSON + `\n`, gửi qua socket |
| `send_reply(content, receiver, reply_to_id)` | Gửi gói reply |
| `send_forward(content, receiver)` | Gửi gói forward |
| `stop()` | Đặt cờ `is_running=False`, đóng socket |

---

### 5.4 gui_main.py — Giao diện chính

**Tác giả:** Nguyễn Gia Bảo  
**Lớp chính:** `MainWindow(QMainWindow)`

Chức năng chính:
- Khung kết nối (IP, Port, Username, Avatar)
- Sidebar danh sách người dùng online (cập nhật realtime)
- Khung chat với scroll tự động
- Thanh soạn thảo kèm Emoji Picker
- Thanh trạng thái Reply (trích dẫn tin nhắn đang reply)
- Xử lý tất cả signal từ `NetworkClient`

---

### 5.5 gui_widgets.py — Component đồ họa

**Tác giả:** Trần Trung Trực  
**Lớp chính:** `MessageItem`, `AutoResizingTextEdit`

**MessageItem:** Bong bóng chat kiểu Messenger
- Tin của mình: bên phải, màu xanh `#0084ff`
- Tin của bạn: bên trái, màu xám `#3a3b3c`
- Hiển thị avatar tròn, tên người gửi, nội dung, timestamp
- Vẽ ô trích dẫn `reply_to` phía trên nội dung chính

**AutoResizingTextEdit:** Ô nhập liệu tự động tăng chiều cao theo nội dung.

---

### 5.6 gui_actions.py — Các component hành động

**Tác giả:** Ngô Gia Bảo  
**Lớp chính:** `EmojiPickerDialog`, `ForwardDialog`  
**Hàm tiện ích:** `create_message_context_menu()`, `attach_context_menu_to_message()`, `get_asset_path()`, `get_asset_icon()`, `get_asset_pixmap()`

| Chức năng | Mô tả |
|----------|-------|
| `EmojiPickerDialog` | Grid 4×6 emoji, tự chèn vào con trỏ ô soạn thảo |
| `ForwardDialog` | Danh sách người online, ô tìm kiếm, xác nhận chuyển tiếp |
| `create_message_context_menu()` | Menu Reply / Forward / Copy khi click chuột phải |
| `attach_context_menu_to_message()` | Gắn menu vào MessageItem và các QLabel con |
| `get_asset_path()` | Trả về đường dẫn tuyệt đối an toàn tới file trong `assets/` |

---

## 6. Kết quả kiểm thử

### 6.1 Unit Test tự động

| File test | Số test | Kết quả |
|-----------|---------|---------|
| `Code/Server/test_server_router_internal.py` | 71 | ✅ 71 passed |
| `Test/test_server_router.py` | 12 | ✅ 12 passed |
| `Test/test_ngo_gia_bao_checklist.py` | 14 | ✅ 14 passed |
| `Test/test_week3_avatar.py` | 2 | ✅ 2 passed |
| `Test/test_week4_forward.py` | 1 | ✅ 1 passed |
| `Test/test_week5_error_handling.py` | 15 | ✅ 15 passed |
| **Tổng cộng** | **115** | ✅ **115 passed / 0 failed** |

### 6.2 Kiểm thử ServerRouter

| Kịch bản | Kết quả |
|---------|---------|
| Gói tin JSON bình thường | ✅ Parse thành công, gắn msg_id |
| TCP chia gói tin giữa chừng | ✅ Buffer ghép đúng |
| Nhiều gói tin trong 1 recv() | ✅ Tách đúng theo `\n` |
| JSON không hợp lệ | ✅ Trả `INVALID_JSON`, không dừng |
| JSON là array `[...]` | ✅ Từ chối, trả lỗi |
| Emoji 4-byte bị cắt đôi | ✅ Buffer chờ đủ byte mới decode |
| Lone surrogate UTF-16 | ✅ Từ chối ngay |
| `reply_to_id` tồn tại | ✅ Trả về nội dung tin gốc |
| `reply_to_id` không tồn tại | ✅ Trả `REPLY_NOT_FOUND` |
| `reply_to_id` không phải số nguyên | ✅ Trả `INVALID_REPLY_TO_ID` |

### 6.3 Stress Test (Test/clients.py)

| Số client giả lập | RAM sử dụng | CPU | Kết quả |
|-------------------|-------------|-----|---------|
| 10 clients | ~25 MB | <5% | ✅ Ổn định |
| 50 clients | ~80 MB | <15% | ✅ Ổn định |

---

## 7. Các vấn đề đã giải quyết

### 7.1 TCP Packet Splitting với Emoji/tiếng Việt

**Vấn đề:** Emoji 4 byte (ví dụ 😀 = `F0 9F 98 80`) có thể bị TCP chia thành 2 đoạn:  
- recv 1: `...F0 9F`  
- recv 2: `98 80\n`  

Khi decode UTF-8 ở recv 1 → lỗi `UnicodeDecodeError`.

**Giải pháp:** Dùng `bytearray` buffer, chỉ decode UTF-8 sau khi đã có đủ ký tự `\n`.

### 7.2 pytest Import Mismatch

**Vấn đề:** Hai file `test_server_router.py` tồn tại ở cả `Code/Server/` và `Test/` → pytest báo lỗi `import file mismatch`.

**Giải pháp:** Đổi tên `Code/Server/test_server_router.py` → `Code/Server/test_server_router_internal.py`.

### 7.3 GitHub Desktop Stash mất thay đổi

**Vấn đề:** Chuyển nhánh trong GitHub Desktop tự động stash toàn bộ thay đổi đang làm dở.

**Giải pháp:** Dùng `git stash apply` để khôi phục, sau đó commit ngay trước khi chuyển nhánh.

---

## 8. Hướng phát triển tiếp theo

- [ ] Mã hóa TLS/SSL cho kết nối TCP.
- [ ] Lưu lịch sử chat vào SQLite.
- [ ] Gửi file/ảnh qua socket.
- [ ] Thông báo đẩy (notification) khi có tin nhắn mới.
- [ ] Triển khai lên VPS thực tế.

---

*Báo cáo được tổng hợp bởi **Ngô Gia Bảo** — Nhóm trưởng UDM08*  
*Cập nhật lần cuối: 19/11/2026 (Tuần 5)*
