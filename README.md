# UDM08 — TCP Chat Application (Client–Server)

> **Mã đề tài:** UDM08 · **Môn học:** Lập trình mạng · **Học kỳ:** 1 / 2026-2027

---

## 1. Danh sách thành viên

| STT | Họ và Tên | MSSV | Vai trò | Module đảm nhiệm |
|-----|-----------|------|---------|-----------------|
| 1 | **Ngô Gia Bảo** | — | Nhóm trưởng | `gui_actions.py` – Emoji Picker, Context Menu, Forward Dialog, Assets helper |
| 2 | Trần Thuận Trí | — | Thành viên | `server_core.py` – Lõi TCP Server, quản lý kết nối |
| 3 | Trương Gia Bân | — | Thành viên | `server_router.py` – Bộ định tuyến JSON / UTF-8 |
| 4 | Lý Huỳnh Bích Trâm | — | Thành viên | `network_worker.py` – QThread Client, gửi/nhận socket |
| 5 | Nguyễn Gia Bảo | — | Thành viên | `gui_main.py` – Giao diện chính PyQt6 |
| 6 | Trần Trung Trực | — | Thành viên | `gui_widgets.py` – MessageItem, AutoResizingTextEdit |

---

## 2. Kiến trúc hệ thống

### 2.1 Mô hình tổng quan

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT (PyQt6)                            │
│                                                                  │
│  gui_main.py ──► gui_widgets.py ──► gui_actions.py              │
│       │                                                          │
│  network_worker.py (QThread)  ──► socket.connect(HOST, PORT)    │
└───────────────────────────┬──────────────────────────────────────┘
                            │  TCP / JSON+\n  (UTF-8)
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│                        SERVER (Python)                           │
│                                                                  │
│  server_core.py (ServerCore)  ──► server_router.py (ServerRouter)│
│       │                                                          │
│  threading.Thread (mỗi client 1 thread)                         │
│  Shared: protocol.py · Shared/protocol.py                       │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Sơ đồ luồng dữ liệu (Message Flow)

```
Client A                    Server                     Client B / All
   │                           │                              │
   │── login {"type":"login"} ─►│                              │
   │                           │── login_ack ────────────────►│
   │                           │── user_join broadcast ───────►│
   │                           │                              │
   │── msg {"type":"msg"} ─────►│                              │
   │                           │── broadcast msg ─────────────►│
   │                           │                              │
   │── reply {"reply_to_id":N}─►│── resolve original msg       │
   │                           │── broadcast reply ───────────►│
   │                           │                              │
   │── forward {"receiver":"B"}►│── direct to Client B ────────►│
   │                           │◄─ forward_ack ───────────────│
   │◄─ forward_ack ────────────│                              │
```

### 2.3 Sơ đồ kiến trúc module (phân tầng)

```
┌────────────────────────────────────────────────────────┐
│  TẦNG GIAO DIỆN (Presentation Layer)                   │
│  gui_main.py · gui_widgets.py · gui_actions.py         │
│  style.css · Code/Client/assets/                       │
├────────────────────────────────────────────────────────┤
│  TẦNG MẠNG CLIENT (Network Layer – Client Side)        │
│  network_worker.py  (QThread + TCP socket)             │
├────────────────────────────────────────────────────────┤
│  TẦNG GIAO THỨC CHUNG (Shared Protocol)                │
│  Code/Shared/protocol.py                               │
│  - encode_message / decode_messages                    │
│  - make_login_packet, make_msg_packet, ...             │
├────────────────────────────────────────────────────────┤
│  TẦNG ĐỊNH TUYẾN SERVER (Routing Layer)                │
│  server_router.py  (bytearray buffer, UTF-8/JSON)      │
│  - parse_frame / feed_data / _resolve_reply            │
├────────────────────────────────────────────────────────┤
│  TẦNG LÕI SERVER (Core Layer)                          │
│  server_core.py  (ServerCore, threading, logging)      │
│  - accept_connections / handle_client                  │
│  - broadcast / send_to_one / get_online_users          │
└────────────────────────────────────────────────────────┘
```

---

## 3. Cấu trúc thư mục

```
UDM08_ChatApp/
├── Code/
│   ├── Client/
│   │   ├── gui_main.py          # Cửa sổ chính PyQt6
│   │   ├── gui_widgets.py       # MessageItem, AutoResizingTextEdit
│   │   ├── gui_actions.py       # EmojiPicker, ForwardDialog, ContextMenu
│   │   ├── network_worker.py    # QThread gửi/nhận TCP
│   │   ├── style.css            # CSS toàn bộ giao diện Dark Theme
│   │   └── assets/              # Icon, avatar, hình ảnh
│   │       ├── app_icon.png
│   │       ├── emoji_icon.png
│   │       ├── send_icon.png
│   │       ├── default_avatar.png
│   │       └── avatar_user*.png
│   ├── Server/
│   │   ├── server_core.py       # Lõi TCP Server (threading, logging)
│   │   └── server_router.py     # Bộ định tuyến JSON / UTF-8
│   └── Shared/
│       └── protocol.py          # Giao thức chung (encode/decode JSON)
├── Test/
│   ├── test_server_router.py    # Unit test ServerRouter (reply_to_id, ...)
│   ├── test_week3_avatar.py     # Test Avatar tuần 3
│   ├── test_week4_forward.py    # Test Forward tuần 4
│   ├── test_week5_error_handling.py  # Test xử lý lỗi kết nối tuần 5
│   ├── test_ngo_gia_bao_checklist.py # Test tổng hợp module Ngô Gia Bảo
│   ├── test_network.py          # Test luồng mạng
│   └── clients.py               # Stress-test: giả lập nhiều client
├── DOCX/                        # Báo cáo Word (kiến trúc, protocol, test)
├── PPTX/                        # Slide thuyết trình
├── Extra/                       # Tài liệu bổ sung
├── server.log                   # Log server tự động (tạo khi chạy)
├── Code/requirements.txt        # Danh sách thư viện
└── README.md                    # Tài liệu này
```

---

## 4. Yêu cầu hệ thống

| Thành phần | Phiên bản tối thiểu |
|------------|-------------------|
| Python | 3.11+ |
| PyQt6 | 6.4+ |
| OS | Windows 10/11, macOS 12+, Ubuntu 20.04+ |

---

## 5. Hướng dẫn cài đặt

### Bước 1 — Clone repository

```bash
git clone https://github.com/gbao2510/UDM08_ChatApp.git
cd UDM08_ChatApp
```

### Bước 2 — Cài đặt thư viện

```bash
pip install -r Code/requirements.txt
```

> **Lưu ý:** Chỉ cần cài `PyQt6`. Toàn bộ module còn lại (`socket`, `threading`, `json`, `logging`, ...) là thư viện chuẩn của Python, **không cần** cài thêm.

---

## 6. Hướng dẫn chạy ứng dụng

### 6.1 Khởi động Server

Mở **Terminal 1** (CMD / PowerShell / bash), chạy từ thư mục gốc dự án:

```bash
# Chạy với IP và Port mặc định (0.0.0.0:5000)
python Code/Server/server_core.py

# Hoặc chỉ định IP và Port tuỳ ý
python Code/Server/server_core.py 127.0.0.1 5000
```

Kết quả mong đợi:

```
=== UDM_08 TCP SERVER CORE ===
Server đang lắng nghe trên 0.0.0.0:5000. Nhấn Ctrl + C để dừng Server.
```

Log hoạt động được ghi tự động ra file `server.log` trong thư mục gốc.

### 6.2 Khởi động Client

Mở **Terminal 2** (và Terminal 3, 4, ... để test nhiều người dùng):

```bash
python Code/Client/gui_main.py
```

Trên giao diện Client:
1. Nhập **Username** (ví dụ: `UserA`)
2. Nhập **IP Server** (mặc định `127.0.0.1`) và **Port** (`5000`)
3. Bấm **Kết nối**

### 6.3 Kiểm thử stress (nhiều client giả lập)

```bash
python Test/clients.py
```

---

## 7. Hướng dẫn chạy Unit Test

Chạy toàn bộ bộ kiểm thử từ thư mục gốc:

```bash
python -m pytest -v
```

Kết quả mong đợi: **115 passed** (không có FAILED / ERROR).

Chạy từng nhóm test riêng:

```bash
# Test ServerRouter (bytearray, UTF-8, reply_to_id, ...)
python -m pytest Test/test_server_router.py -v

# Test Avatar (Tuần 3)
python -m pytest Test/test_week3_avatar.py -v

# Test Forward (Tuần 4)
python -m pytest Test/test_week4_forward.py -v

# Test xử lý lỗi kết nối (Tuần 5)
python -m pytest Test/test_week5_error_handling.py -v

# Test checklist module Ngô Gia Bảo
python -m pytest Test/test_ngo_gia_bao_checklist.py -v
```

---

## 8. Giao thức truyền tin (Protocol)

Toàn bộ dữ liệu truyền qua TCP dưới dạng **JSON**, kết thúc bằng ký tự `\n` làm phân định gói tin.  
Mã hóa: **UTF-8** (hỗ trợ Emoji, tiếng Việt có dấu).

### 8.1 Các loại gói tin (Message Types)

| `type` | Hướng | Mô tả |
|--------|-------|-------|
| `login` | Client → Server | Đăng nhập, kèm `username` và `avatar` |
| `login_ack` | Server → Client | Xác nhận đăng nhập, trả về `online_users` |
| `msg` | Client → Server → All | Tin nhắn thông thường broadcast |
| `reply` | Client → Server → All | Trả lời tin nhắn, kèm `reply_to_id` |
| `forward` | Client → Server → Target | Chuyển tiếp 1-1 hoặc broadcast |
| `forward_ack` | Server → Client | Xác nhận forward thành công/thất bại |
| `user_join` | Server → All | Thông báo có người dùng mới vào phòng |
| `user_leave` | Server → All | Thông báo có người dùng rời phòng |
| `error` | Server → Client | Thông báo lỗi có mã lỗi rõ ràng |

### 8.2 Ví dụ gói tin

**Login (Client → Server):**
```json
{"type": "login", "username": "UserA", "avatar": "avatar_user1.png"}
```

**Login ACK (Server → Client):**
```json
{"type": "login_ack", "status": "success", "online_users": [{"username": "UserA", "avatar": "avatar_user1.png"}]}
```

**Tin nhắn thường (Client → Server):**
```json
{"type": "msg", "sender": "UserA", "receiver": "all", "content": "Xin chào mọi người! 👋"}
```

**Server broadcast (Server → All Clients):**
```json
{"type": "msg", "msg_id": 1, "sender": "UserA", "receiver": "all", "content": "Xin chào mọi người! 👋", "timestamp": "10:30:00"}
```

**Reply (Client → Server):**
```json
{"type": "reply", "sender": "UserB", "receiver": "all", "content": "Chào bạn! 😊", "reply_to_id": 1}
```

**Forward (Client → Server):**
```json
{"type": "forward", "sender": "UserA", "receiver": "UserB", "content": "Tin nhắn chuyển tiếp"}
```

**Error (Server → Client):**
```json
{"type": "error", "error": {"code": "USERNAME_TAKEN", "message": "Tên người dùng đã được sử dụng"}}
```

### 8.3 Mã lỗi (Error Codes)

| Mã lỗi | Ý nghĩa |
|--------|---------|
| `USERNAME_TAKEN` | Tên người dùng đã có người khác dùng |
| `ALREADY_LOGGED_IN` | Socket này đã đăng nhập rồi |
| `NOT_LOGGED_IN` | Chưa đăng nhập, không được gửi tin nhắn |
| `INVALID_JSON` | Gói tin không đúng định dạng JSON |
| `REPLY_NOT_FOUND` | `reply_to_id` trỏ tới tin nhắn không tồn tại |
| `INVALID_REPLY_TO_ID` | Giá trị `reply_to_id` không phải số nguyên |

---

## 9. Tính năng theo tuần

| Tuần | Mục tiêu | Trạng thái |
|------|----------|-----------|
| Tuần 1 | Dựng khung độc lập, mock data, Emoji Picker | ✅ Hoàn thành |
| Tuần 2 | Ghép nối Server-Client, chat cơ bản, quản lý online | ✅ Hoàn thành |
| Tuần 3 | Avatar, Emoji UTF-8, danh sách bạn bè online | ✅ Hoàn thành |
| Tuần 4 | Reply tin nhắn, Forward 1-1, Context Menu chuột phải | ✅ Hoàn thành |
| Tuần 5 | Xử lý lỗi kết nối, reconnect tự động, CSS polish, README | ✅ Hoàn thành |

---

## 10. Phân công chi tiết theo tuần

### Tuần 1 — Dựng khung & Mock Data

| Thành viên | Module | Nhiệm vụ |
|-----------|--------|---------|
| Trần Thuận Trí | `server_core.py` | Tạo TCP Server cơ bản, log sự kiện |
| Trương Gia Bân | `server_router.py` | Viết unit test JSON, msg_id tăng dần |
| Lý Huỳnh Bích Trâm | `network_worker.py` | QThread NetworkClient, `connect_to_server()`, `send_data()` |
| Nguyễn Gia Bảo | `gui_main.py` | Khung PyQt6, nhập IP/Port, mock data |
| Trần Trung Trực | `gui_widgets.py` | MessageItem, AutoResizingTextEdit |
| **Ngô Gia Bảo** | `gui_actions.py` | **Emoji Picker Dialog, Assets helper, chuẩn bị icon/avatar** |

### Tuần 2 — Ghép nối & Chat cơ bản

| Thành viên | Module | Nhiệm vụ |
|-----------|--------|---------|
| Trần Thuận Trí | `server_core.py` | Đồng bộ danh sách online, broadcast |
| Trương Gia Bân | `server_router.py` | Tách gói TCP, kiểm tra JSON, trả lỗi rõ ràng |
| Lý Huỳnh Bích Trâm | `network_worker.py` | Nhận signal, emit lên UI |
| Nguyễn Gia Bảo | `gui_main.py` | Cập nhật sidebar online, add MessageItem |
| Trần Trung Trực | `gui_widgets.py` | Add MessageItem vào QScrollArea |
| **Ngô Gia Bảo** | `gui_actions.py` | **Viết stress_test clients.py, báo cáo RAM/CPU** |

### Tuần 3 — Avatar & Emoji

| Thành viên | Module | Nhiệm vụ |
|-----------|--------|---------|
| Trần Thuận Trí | `server_core.py` | Lưu và truyền avatar khi login |
| Trương Gia Bân | `server_router.py` | UTF-8 chuẩn xác cho Emoji |
| Lý Huỳnh Bích Trâm | `network_worker.py` | `send_emoji()` tích hợp luồng gửi tin |
| Nguyễn Gia Bảo | `gui_main.py` | Hiển thị avatar tròn trong danh sách bạn bè |
| Trần Trung Trực | `gui_widgets.py` | MessageItem hiển thị avatar tròn cạnh bong bóng |
| **Ngô Gia Bảo** | `gui_actions.py` | **Emoji Picker nhúng vào khung soạn thảo** |

### Tuần 4 — Reply & Forward

| Thành viên | Module | Nhiệm vụ |
|-----------|--------|---------|
| Trần Thuận Trí | `server_core.py` | Điều hướng Forward 1-1 và phòng chung |
| Trương Gia Bân | `server_router.py` | `_resolve_reply()` tra cứu `reply_to_id` |
| Lý Huỳnh Bích Trâm | `network_worker.py` | `send_reply()`, `send_forward()` |
| Nguyễn Gia Bảo | `gui_main.py` | Thanh trạng thái Reply, trích dẫn tin nhắn |
| Trần Trung Trực | `gui_widgets.py` | MessageItem vẽ ô trích dẫn `reply_to` |
| **Ngô Gia Bảo** | `gui_actions.py` | **Context Menu chuột phải, ForwardDialog pop-up** |

### Tuần 5 — Xử lý lỗi & Hoàn thiện

| Thành viên | Module | Nhiệm vụ |
|-----------|--------|---------|
| Trần Thuận Trí | `server_core.py` | Bắt lỗi kết nối, reconnect tự động phía Server |
| Trương Gia Bân | `server_router.py` | Bắt lỗi kết nối, reconnect tự động phía Router |
| Lý Huỳnh Bích Trâm | `network_worker.py` | try-catch timeout, cảnh báo mất mạng lên UI |
| Nguyễn Gia Bảo | `gui_main.py` | CSS polish, cuộn xuống khi có tin mới |
| Trần Trung Trực | `gui_widgets.py` | CSS polish, hover, cuộn tự động |
| **Ngô Gia Bảo** | `gui_actions.py` | **Viết README, sơ đồ kiến trúc, báo cáo Word** |

---

## 11. Demo nhanh từng module

### Chạy demo Emoji Picker & Context Menu (gui_actions.py)
```bash
python Code/Client/gui_actions.py
```
Cửa sổ demo sẽ hiện ra với:
- Nút **Mở Emoji Picker** → chọn emoji tự động chèn vào ô nhập
- Nút **Pop-up Forward** → hiện dialog chọn người nhận
- **Click chuột phải** vào bong bóng chat → Context Menu (Reply / Forward / Copy)

### Chạy demo Client độc lập (không cần Server)
```bash
python Code/Client/gui_main.py
```
Giao diện đầy đủ sẽ hiện ra. Có thể dùng mà không kết nối Server để xem layout.

---

## 12. Video Demo & Thuyết trình

- **Link Video (Google Drive / YouTube):** 
- **Quy định video:** Thể hiện đầy đủ các chức năng bắt buộc, ít nhất 1 kịch bản lỗi/mất kết nối, mỗi thành viên trình bày phần việc của mình và bật webcam.

---

## 13. Hướng dẫn đóng gói nộp bài (Course Submission)

Trước khi nộp bài trên hệ thống môn học, nhóm thực hiện dọn dẹp các tệp tạm / cache và đóng gói theo định dạng quy định:

```bash
# 1. Xóa cache Python và các file sinh tự động
# Windows PowerShell:
Get-ChildItem -Path . -Include __pycache__,.pytest_cache -Recurse -Force | Remove-Item -Recurse -Force
Remove-Item -Path server.log -Force -ErrorAction SilentlyContinue

# 2. Nén toàn bộ thư mục thành file .7z đúng định dạng:
# CourseCode-GroupCode-ProjectCode.7z (Ví dụ: IT008-N08-UDM_08.7z)
```

---

## 14. Thông tin liên hệ & Repository

- **GitHub:** https://github.com/gbao2510/UDM08_ChatApp
- **Nhánh chính:** `main`
- **Nhánh phát triển:** `ngobao`, `thuantri`, `giaban`, `bichtram`, `nguyenbao`, `trungtruc`

---

*README được viết và cập nhật bởi **Ngô Gia Bảo** (Nhóm trưởng) — Tuần 5 (19/11/2026)*
