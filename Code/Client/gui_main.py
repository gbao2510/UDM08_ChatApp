import os
import sys

# Đảm bảo nạp đúng các module cùng thư mục Client và thư mục gốc Project
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QFrame, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Liên kết module từ gui_actions.py, network_worker.py, gui_widgets.py
try:
    from gui_actions import EmojiPickerDialog, attach_context_menu_to_message
except Exception:
    EmojiPickerDialog = None
    attach_context_menu_to_message = None

try:
    from network_worker import NetworkClient
except Exception:
    NetworkClient = None

try:
    from gui_widgets import MessageItem, AutoResizingTextEdit, CircularAvatar
except Exception:
    MessageItem = None
    AutoResizingTextEdit = None
    CircularAvatar = None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chat Application - Team Client (Tuần 2: Quản lý Online & Ghép Widgets)")
        self.resize(920, 650)
        self.setMinimumSize(780, 520)

        # Trạng thái Reply hiện tại và danh sách user online để tái sử dụng cho menu hành động
        self.replying_to = None
        self.online_users_cache = []
        self.my_avatar = "avatar_user1.png"

        # Cài đặt giao diện
        self.setup_ui()
        # Bỏ nạp mock data lúc khởi động để kết nối dữ liệu thật từ Server
        self.lbl_online.setText("Online Users (0)")

        # Khởi tạo các module liên kết
        self.emoji_dialog = EmojiPickerDialog(parent_input_field=self.txt_message) if EmojiPickerDialog else None
        self.network_client = None

    def setup_ui(self):
        # Widget trung tâm - Dark Theme
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #18191a; color: #f2f3f5;")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # 1. KHU VỰC CẤU HÌNH MẠNG & USERNAME (TOP BAR)
        network_box = QFrame()
        network_box.setStyleSheet("""
            QFrame {
                background-color: #242526;
                border: 1px solid #393a3b;
                border-radius: 8px;
            }
        """)
        network_layout = QHBoxLayout(network_box)
        network_layout.setContentsMargins(14, 10, 14, 10)
        network_layout.setSpacing(10)

        # Ô nhập tên tài khoản
        lbl_user = QLabel("User:")
        lbl_user.setStyleSheet("border: none; font-weight: bold; color: #e4e6eb; font-size: 13px;")
        self.txt_username = QLineEdit("Gia Bảo")
        self.txt_username.setPlaceholderText("Tên bạn")
        self.txt_username.setFixedWidth(110)
        self.txt_username.setStyleSheet("""
            QLineEdit {
                background-color: #3a3b3c;
                color: #ffffff;
                border: 1px solid #4e4f50;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #0084ff;
            }
        """)

        # Ô nhập IP
        lbl_ip = QLabel("Server IP:")
        lbl_ip.setStyleSheet("border: none; font-weight: bold; color: #e4e6eb; font-size: 13px;")
        self.txt_ip = QLineEdit("127.0.0.1")
        self.txt_ip.setPlaceholderText("VD: 127.0.0.1")
        self.txt_ip.setFixedWidth(120)
        self.txt_ip.setStyleSheet("""
            QLineEdit {
                background-color: #3a3b3c;
                color: #ffffff;
                border: 1px solid #4e4f50;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #0084ff;
            }
        """)

        # Ô nhập Port
        lbl_port = QLabel("Port:")
        lbl_port.setStyleSheet("border: none; font-weight: bold; color: #e4e6eb; font-size: 13px;")
        self.txt_port = QLineEdit("5000")
        self.txt_port.setPlaceholderText("Port")
        self.txt_port.setFixedWidth(65)
        self.txt_port.setStyleSheet("""
            QLineEdit {
                background-color: #3a3b3c;
                color: #ffffff;
                border: 1px solid #4e4f50;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #0084ff;
            }
        """)

        # Nút Kết nối
        self.btn_connect = QPushButton("Kết nối")
        self.btn_connect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_connect.setStyleSheet("""
            QPushButton {
                background-color: #0084ff;
                color: white;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 6px;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0073e6;
            }
            QPushButton:disabled {
                background-color: #3a3b3c;
                color: #8a8d91;
            }
        """)
        self.btn_connect.clicked.connect(self.demo_connect_action)

        self.lbl_status = QLabel("Trạng thái: Chưa kết nối")
        self.lbl_status.setStyleSheet("border: none; color: #b0b3b8; font-style: italic; font-size: 13px;")

        network_layout.addWidget(lbl_user)
        network_layout.addWidget(self.txt_username)
        network_layout.addWidget(lbl_ip)
        network_layout.addWidget(self.txt_ip)
        network_layout.addWidget(lbl_port)
        network_layout.addWidget(self.txt_port)
        network_layout.addWidget(self.btn_connect)
        network_layout.addWidget(self.lbl_status)
        network_layout.addStretch()

        main_layout.addWidget(network_box)

        # 2. KHU VỰC THÂN CHÍNH (SIDEBAR + KHUNG CHAT)
        body_layout = QHBoxLayout()
        body_layout.setSpacing(12)

        # 2.1 Sidebar: Danh sách người online với ẢNH ĐẠI DIỆN (CircularAvatar từ gui_widgets.py)
        sidebar_outer = QVBoxLayout()
        sidebar_outer.setSpacing(4)
        self.lbl_online = QLabel("Online Users (0)")
        self.lbl_online.setStyleSheet("color: #e4e6eb; font-weight: bold; font-size: 13px; margin-bottom: 2px;")

        # Dùng QScrollArea + Widget tùy chỉnh để hiển thị Avatar + Tên (không dùng QListWidget)
        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setFixedWidth(240)
        self.sidebar_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #393a3b;
                border-radius: 8px;
                background-color: #242526;
            }
            QScrollBar:vertical {
                width: 4px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #4e4f50;
                border-radius: 2px;
            }
        """)
        self.sidebar_content = QWidget()
        self.sidebar_content.setStyleSheet("background-color: #242526;")
        self.sidebar_content_layout = QVBoxLayout(self.sidebar_content)
        self.sidebar_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.sidebar_content_layout.setContentsMargins(8, 8, 8, 8)
        self.sidebar_content_layout.setSpacing(4)
        self.sidebar_scroll.setWidget(self.sidebar_content)

        sidebar_outer.addWidget(self.lbl_online)
        sidebar_outer.addWidget(self.sidebar_scroll)
        body_layout.addLayout(sidebar_outer)

        # 2.2 Chat Area: TÍCH HỢP MESSAGEITEM VÀ SCROLLAREA TỪ GUI_WIDGETS.PY
        chat_layout = QVBoxLayout()
        lbl_chat = QLabel("Phòng Chat Chung")
        lbl_chat.setStyleSheet("color: #e4e6eb; font-weight: bold; font-size: 13px; margin-bottom: 2px;")

        self.scroll_chat = QScrollArea()
        self.scroll_chat.setWidgetResizable(True)
        self.scroll_chat.setStyleSheet("""
            QScrollArea {
                border: 1px solid #393a3b;
                border-radius: 8px;
                background-color: #242526;
            }
        """)
        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background-color: #242526;")
        self.chat_content_layout = QVBoxLayout(self.chat_container)
        self.chat_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_content_layout.setSpacing(6)
        self.scroll_chat.setWidget(self.chat_container)

        # Thanh trạng thái phụ trên khung chat: "Đang trả lời: [Tên]" kèm nút X hủy
        self.reply_bar = QFrame()
        self.reply_bar.setObjectName("replyStatusBar")
        self.reply_bar.setStyleSheet("""
            QFrame#replyStatusBar {
                background-color: #242526;
                border: 1px solid #393a3b;
                border-left: 3px solid #0084ff;
                border-radius: 6px;
            }
        """)
        reply_bar_layout = QHBoxLayout(self.reply_bar)
        reply_bar_layout.setContentsMargins(10, 6, 8, 6)
        reply_bar_layout.setSpacing(8)

        self.lbl_reply_status = QLabel("")
        self.lbl_reply_status.setStyleSheet(
            "border: none; color: #e4e6eb; font-size: 12px; font-weight: bold;"
        )

        self.lbl_reply_preview = QLabel("")
        self.lbl_reply_preview.setStyleSheet(
            "border: none; color: #b0b3b8; font-size: 12px; font-style: italic;"
        )

        self.btn_cancel_reply = QPushButton("X")
        self.btn_cancel_reply.setFixedSize(22, 22)
        self.btn_cancel_reply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel_reply.setToolTip("Hủy trả lời")
        self.btn_cancel_reply.setStyleSheet("""
            QPushButton {
                background-color: #3a3b3c;
                color: #e4e6eb;
                font-weight: bold;
                font-size: 11px;
                border: none;
                border-radius: 11px;
            }
            QPushButton:hover {
                background-color: #fa5252;
                color: #ffffff;
            }
        """)
        self.btn_cancel_reply.clicked.connect(self.cancel_reply)

        reply_bar_layout.addWidget(self.lbl_reply_status)
        reply_bar_layout.addWidget(self.lbl_reply_preview, stretch=1)
        reply_bar_layout.addWidget(self.btn_cancel_reply)
        self.reply_bar.hide()

        chat_layout.addWidget(lbl_chat)
        chat_layout.addWidget(self.scroll_chat)
        chat_layout.addWidget(self.reply_bar)
        body_layout.addLayout(chat_layout, stretch=1)

        main_layout.addLayout(body_layout, stretch=1)

        # 3. KHU VỰC NHẬP TIN NHẮN (TÍCH HỢP AUTORESIZINGTEXTEDIT TỪ GUI_WIDGETS.PY)
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)

        # Nút Emoji (liên kết với gui_actions.py)
        self.btn_emoji = QPushButton("😊")
        self.btn_emoji.setFixedSize(38, 38)
        self.btn_emoji.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_emoji.setToolTip("Chọn Emoji (gui_actions.py)")
        self.btn_emoji.setStyleSheet("""
            QPushButton {
                background-color: #3a3b3c;
                color: white;
                font-size: 18px;
                border: 1px solid #4e4f50;
                border-radius: 19px;
            }
            QPushButton:hover {
                background-color: #4e4f50;
            }
        """)
        self.btn_emoji.clicked.connect(self.demo_emoji_click)

        # Ô nhập tin nhắn tự co giãn (từ gui_widgets.py)
        if AutoResizingTextEdit:
            self.txt_message = AutoResizingTextEdit(min_height=38, max_height=100)
            # Khắc phục tính tương thích để gui_actions.py gọi .text() và .setText() không bị lỗi
            self.txt_message.text = self.txt_message.toPlainText
            self.txt_message.send_requested.connect(self.send_message)
        else:
            self.txt_message = QLineEdit()
            self.txt_message.setPlaceholderText("Nhập tin nhắn...")
            self.txt_message.setFixedHeight(38)
            self.txt_message.returnPressed.connect(self.send_message)

        # Nút Send phong cách Messenger (từ gui_widgets.py)
        self.btn_send = QPushButton("Send")
        self.btn_send.setFixedSize(65, 38)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #0084FF;
                color: white;
                font-weight: bold;
                border-radius: 19px;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0073E6;
            }
            QPushButton:pressed {
                background-color: #005BB5;
            }
        """)
        self.btn_send.clicked.connect(self.send_message)

        bottom_layout.addWidget(self.btn_emoji, alignment=Qt.AlignmentFlag.AlignBottom)
        bottom_layout.addWidget(self.txt_message, stretch=1)
        bottom_layout.addWidget(self.btn_send, alignment=Qt.AlignmentFlag.AlignBottom)

        main_layout.addLayout(bottom_layout)

    def load_initial_data(self):
        """Nạp dữ liệu mẫu ban đầu (Mock Data) gồm cả ảnh đại diện trong sidebar"""
        # 1. Danh sách thành viên với avatar mẫu
        mock_users = [
            {"name": "Trần Thuận Trí", "online": True,  "is_self": False},
            {"name": "Trương Gia Bân",  "online": True,  "is_self": False},
            {"name": "Lý Huỳnh Bích Trâm", "online": True,  "is_self": False},
            {"name": "Nguyễn Gia Bảo",  "online": True,  "is_self": True},
            {"name": "Trần Trung Trực", "online": True,  "is_self": False},
            {"name": "Ngô Gia Bảo",     "online": False, "is_self": False},
        ]
        self._clear_sidebar()
        self.online_users_cache = [u["name"] for u in mock_users]
        for u in mock_users:
            row = self._make_user_row(name=u["name"], is_online=u["online"])
            self.sidebar_content_layout.addWidget(row)
        self.lbl_online.setText(f"Online Users ({len(mock_users)})")

        # 2. Nạp bong bóng tin nhắn mẫu chuẩn từ gui_widgets.py
        mock_messages = [
            {"sender": "Ngô Gia Bảo",  "text": "Tiến độ hoàn thành như nào rồi.", "is_self": False},
            {"sender": "Nguyễn Gia Bảo", "text": "T đang hoàn thiện component MessageItem hiển thị độc lập.", "is_self": True},
            {"sender": "Lý Huỳnh Bích Trâm", "text": "Socket client tuần này gửi nhận chuỗi JSON cơ bản được rồi.", "is_self": False},
            {"sender": "Nguyễn Gia Bảo", "text": "Thử nghiệm tin nhắn dài tự động xuống dòng và co giãn chiều cao xem bong bóng chat có hoạt động chuẩn không.", "is_self": True},
        ]
        for data in mock_messages:
            self.add_message_to_chat(
                sender=data["sender"],
                message=data["text"],
                is_self=data["is_self"]
            )

    # =========================================================================
    # NHIỆM VỤ TUẦN 3 (NGUYỄN GIA BẢO): THÊM ẢNH ĐẠI DIỆN VÀO DANH SÁCH BẠN BÈ ONLINE
    # =========================================================================
    def _make_user_row(self, name: str, is_online: bool = True, avatar_path: str = None) -> QWidget:
        """
        Tạo 1 dòng hiển thị người dùng trong sidebar gồm:
        - Ảnh đại diện tròn (CircularAvatar từ gui_widgets.py)
        - Chấm trạng thái xanh/xám overlay lên góc avatar
        - Tên người dùng
        """
        # Đường dẫn ảnh đại diện: ghép với thư mục assets/ nếu là tên file tương đối
        default_avatar = os.path.join(current_dir, "assets", "default_avatar.png")
        used_path = default_avatar
        if avatar_path:
            if os.path.isabs(avatar_path) and os.path.exists(avatar_path):
                used_path = avatar_path
            else:
                assets_candidate = os.path.join(current_dir, "assets", os.path.basename(avatar_path))
                if os.path.exists(assets_candidate):
                    used_path = assets_candidate

        row = QWidget()
        row.setProperty("username", name)
        row.setFixedHeight(58)
        row.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border-radius: 8px;
            }
            QWidget:hover {
                background-color: #3a3b3c;
            }
        """)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(8, 6, 8, 6)
        row_layout.setSpacing(10)

        # Khung avatar + chấm trạng thái (dùng QLabel overlay)
        avatar_frame = QWidget()
        avatar_frame.setFixedSize(42, 42)
        avatar_frame_layout = QVBoxLayout(avatar_frame)
        avatar_frame_layout.setContentsMargins(0, 0, 0, 0)

        if CircularAvatar:
            avatar = CircularAvatar(size=38, image_path=used_path)
        else:
            avatar = QLabel("👤")
            avatar.setFixedSize(38, 38)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setStyleSheet("font-size: 22px;")

        avatar_frame_layout.addWidget(avatar)

        # Chấm trạng thái online/offline (QLabel nhỏ đè lên góc phải-dưới)
        dot = QLabel()
        dot.setFixedSize(12, 12)
        dot.setParent(avatar_frame)
        dot.move(28, 28)          # Góc dưới bên phải của avatar 38px
        dot.setStyleSheet(f"""
            QLabel {{
                background-color: {'#31a24c' if is_online else '#b0b3b8'};
                border-radius: 6px;
                border: 2px solid #242526;
            }}
        """)
        dot.raise_()

        row_layout.addWidget(avatar_frame)

        # Khối tên + trạng thái chữ
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)

        my_name = self.txt_username.text().strip() if hasattr(self, 'txt_username') else ""
        display_name = f"{name} (Bạn)" if name == my_name else name

        lbl_name = QLabel(display_name)
        lbl_name.setStyleSheet(f"""
            color: {'#e4e6eb' if is_online else '#8a8d91'};
            font-size: 13px;
            font-weight: {'bold' if name == my_name else 'normal'};
        """)

        lbl_status_txt = QLabel("Online" if is_online else "Offline")
        lbl_status_txt.setStyleSheet(f"""
            color: {'#31a24c' if is_online else '#8a8d91'};
            font-size: 11px;
        """)

        text_layout.addWidget(lbl_name)
        text_layout.addWidget(lbl_status_txt)
        row_layout.addLayout(text_layout, stretch=1)

        return row

    def _clear_sidebar(self):
        """Xóa toàn bộ các dòng user trong sidebar"""
        while self.sidebar_content_layout.count():
            child = self.sidebar_content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def update_online_users(self, user_list):
        """
        Cập nhật toàn bộ danh sách người dùng online lên sidebar với ảnh đại diện
        khi nhận được signal từ Server qua NetworkClient
        """
        self._clear_sidebar()
        self.online_users_cache = []

        for user in user_list:
            if isinstance(user, dict):
                name = user.get("username", "Unknown")
                avatar = user.get("avatar", None)
            else:
                name = str(user).strip()
                avatar = None

            if not name:
                continue

            self.online_users_cache.append(name)
            row = self._make_user_row(name=name, is_online=True, avatar_path=avatar)
            self.sidebar_content_layout.addWidget(row)

        count = self.sidebar_content_layout.count()
        self.lbl_online.setText(f"Online Users ({count})")

    def add_online_user(self, username, avatar_path=None):
        """Thêm 1 người dùng mới online vào sidebar"""
        if not username:
            return

        # Kiểm tra trùng tên an toàn qua property và QLabel con
        for i in range(self.sidebar_content_layout.count()):
            w = self.sidebar_content_layout.itemAt(i).widget()
            if w:
                if w.property("username") == username:
                    return
                for lbl in w.findChildren(QLabel):
                    lbl_text = lbl.text() or ""
                    if username in lbl_text:
                        return

        if username not in self.online_users_cache:
            self.online_users_cache.append(username)
        row = self._make_user_row(name=username, is_online=True, avatar_path=avatar_path)
        self.sidebar_content_layout.addWidget(row)
        count = self.sidebar_content_layout.count()
        self.lbl_online.setText(f"Online Users ({count})")

    def remove_online_user(self, username):
        """Xóa 1 người dùng vừa rời mạng khỏi sidebar"""
        if not username:
            return
        if username in self.online_users_cache:
            self.online_users_cache.remove(username)
        for i in range(self.sidebar_content_layout.count()):
            w = self.sidebar_content_layout.itemAt(i).widget()
            if w:
                matched = (w.property("username") == username)
                if not matched:
                    for lbl in w.findChildren(QLabel):
                        lbl_text = lbl.text() or ""
                        if username in lbl_text:
                            matched = True
                            break
                if matched:
                    item = self.sidebar_content_layout.takeAt(i)
                    if item.widget():
                        item.widget().deleteLater()
                    break
        count = self.sidebar_content_layout.count()
        self.lbl_online.setText(f"Online Users ({count})")

    def get_online_usernames(self):
        """Trả về danh sách tên người dùng online hiện tại cho ForwardDialog"""
        return list(self.online_users_cache)

    # =========================================================================
    # NHIỆM VỤ TUẦN 4 (NGUYỄN GIA BẢO): THANH TRẠNG THÁI PHỤ KHI TRẢ LỜI (REPLY)
    # =========================================================================
    def start_reply(self, message_dict: dict):
        """Hiển thị thanh trạng thái phụ 'Đang trả lời: [Tên]' kèm nút X hủy"""
        if not isinstance(message_dict, dict):
            return
        sender = message_dict.get("sender") or "Ẩn danh"
        content = message_dict.get("content") or message_dict.get("text") or ""

        self.replying_to = dict(message_dict)
        self.lbl_reply_status.setText(f"Đang trả lời: {sender}")

        if content:
            snippet = content if len(content) <= 60 else content[:57] + "..."
            self.lbl_reply_preview.setText(f'"{snippet}"')
            self.lbl_reply_preview.show()
        else:
            self.lbl_reply_preview.setText("")
            self.lbl_reply_preview.hide()

        self.reply_bar.show()
        if hasattr(self, "txt_message") and self.txt_message:
            self.txt_message.setFocus()

    def cancel_reply(self):
        """Hủy chế độ trả lời và ẩn thanh trạng thái phụ"""
        self.replying_to = None
        self.lbl_reply_status.setText("")
        self.lbl_reply_preview.setText("")
        self.reply_bar.hide()

    def handle_forward_confirmed(self, receiver: str, content: str):
        """Xử lý gửi gói tin chuyển tiếp (Forward) khi người dùng xác nhận trong ForwardDialog"""
        if not content:
            return
        my_name = self.txt_username.text().strip() or "Gia Bảo"
        if self.network_client and self.network_client.is_running:
            if hasattr(self.network_client, "send_forward"):
                self.network_client.send_forward(
                    original_msg_id=0,
                    content=content,
                    target_room_or_user=receiver,
                    original_sender=my_name,
                )
            else:
                self.network_client.send_data({
                    "type": "forward",
                    "sender": my_name,
                    "receiver": receiver,
                    "content": content,
                })
        self.add_system_message(f"Đã chuyển tiếp tin nhắn tới {receiver}.")

    # =========================================================================
    # CÁC HÀM XỬ LÝ TIN NHẮN (TÍCH HỢP MESSAGEITEM TỪ GUI_WIDGETS.PY)
    # =========================================================================
    def add_message_to_chat(self, sender: str, message: str, is_self: bool = False, msg_id=None, avatar_path=None, reply_to=None):
        """Thêm bong bóng tin nhắn Messenger (MessageItem) từ gui_widgets.py vào khung chat (hỗ trợ avatar và reply_to)"""
        resolved_avatar = None
        if avatar_path:
            if os.path.isabs(avatar_path) and os.path.exists(avatar_path):
                resolved_avatar = avatar_path
            else:
                candidate = os.path.join(current_dir, "assets", os.path.basename(avatar_path))
                if os.path.exists(candidate):
                    resolved_avatar = candidate

        if MessageItem:
            widget_item = MessageItem(
                sender_name=sender,
                message=message,
                is_self=is_self,
                avatar_path=resolved_avatar,
                reply_to=reply_to
            )
        else:
            widget_item = QLabel(f"<b>{sender}</b>: {message}")
            widget_item.setWordWrap(True)
            widget_item.setStyleSheet("""
                QLabel {
                    background-color: #3a3b3c;
                    color: #ffffff;
                    border-radius: 12px;
                    padding: 8px 12px;
                    font-size: 13px;
                }
            """)

        self.chat_content_layout.addWidget(widget_item)

        if attach_context_menu_to_message:
            msg_dict = {
                "msg_id": msg_id,
                "sender": sender,
                "content": message,
            }
            attach_context_menu_to_message(
                widget=widget_item,
                message_dict=msg_dict,
                get_online_users=self.get_online_usernames,
                on_reply=self.start_reply,
                on_forward_confirmed=self.handle_forward_confirmed,
            )

        # Cuộn thanh cuộn xuống tin nhắn mới nhất
        QApplication.processEvents()
        self.scroll_chat.verticalScrollBar().setValue(
            self.scroll_chat.verticalScrollBar().maximum()
        )

    def add_system_message(self, text: str):
        """Hiển thị thông báo hệ thống"""
        lbl = QLabel(f"📢 {text}")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #b0b3b8; font-style: italic; font-size: 12px; padding: 4px;")
        self.chat_content_layout.addWidget(lbl)
        QApplication.processEvents()
        self.scroll_chat.verticalScrollBar().setValue(
            self.scroll_chat.verticalScrollBar().maximum()
        )

    def send_message(self):
        """Gửi tin nhắn đi (hỗ trợ cả tin nhắn thường và Reply)"""
        if hasattr(self.txt_message, 'toPlainText'):
            text = self.txt_message.toPlainText().strip()
        else:
            text = self.txt_message.text().strip()

        if not text:
            return

        my_name = self.txt_username.text().strip() or "Gia Bảo"
        my_avatar = getattr(self, "my_avatar", "default_avatar.png")
        reply_info = self.replying_to

        # Hiển thị tin nhắn của chính mình lên khung chat (kèm ô trích dẫn reply nếu có)
        self.add_message_to_chat(
            sender=my_name,
            message=text,
            is_self=True,
            avatar_path=my_avatar,
            reply_to=reply_info
        )

        # Xóa ô nhập và reset chiều cao nếu là AutoResizingTextEdit
        self.txt_message.clear()
        if hasattr(self.txt_message, 'adjust_height'):
            self.txt_message.setFixedHeight(self.txt_message.min_height)

        # Hủy thanh trạng thái Reply sau khi gửi
        if reply_info:
            self.cancel_reply()

        # Gửi dữ liệu qua NetworkClient nếu đã kết nối Server
        if self.network_client and self.network_client.is_running:
            if reply_info:
                payload = {
                    "type": "reply",
                    "sender": my_name,
                    "receiver": "all",
                    "content": text,
                    "reply_to": reply_info,
                    "reply_to_id": reply_info.get("msg_id") or 0,
                    "reply_to_msg_id": reply_info.get("msg_id") or 0,
                }
            else:
                payload = {
                    "type": "msg",
                    "sender": my_name,
                    "receiver": "all",
                    "content": text,
                }
            self.network_client.send_data(payload)

    # =========================================================================
    # KẾT NỐI VÀ XỬ LÝ SIGNAL TỪ NETWORK_WORKER.PY
    # =========================================================================
    def demo_connect_action(self):
        """Kết nối tới Server qua NetworkClient từ network_worker.py"""
        ip = self.txt_ip.text().strip()
        port_text = self.txt_port.text().strip()
        username = self.txt_username.text().strip()

        if not username:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên người dùng (User)!")
            return

        if not ip or not port_text:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ IP và Port!")
            return

        try:
            port = int(port_text)
        except ValueError:
            QMessageBox.warning(self, "Lỗi", "Port phải là số nguyên!")
            return

        if not NetworkClient:
            QMessageBox.critical(self, "Lỗi", "Không tìm thấy class NetworkClient trong network_worker.py!")
            return

        # Dừng kết nối cũ nếu có
        if self.network_client and self.network_client.is_running:
            self.network_client.stop()

        # Khởi tạo NetworkClient và nối các signal
        self.network_client = NetworkClient(host=ip, port=port)
        self.network_client.connected_signal.connect(self.on_connected)
        self.network_client.disconnected_signal.connect(self.on_disconnected)
        self.network_client.received_signal.connect(self.on_message_received)
        self.network_client.error_signal.connect(self.on_network_error)

        self.lbl_status.setText(f"Đang kết nối tới {ip}:{port}...")
        self.lbl_status.setStyleSheet("border: none; color: #4dabf7; font-style: italic; font-size: 13px;")
        self.network_client.connect_to_server(ip, port)

    def on_connected(self):
        """Xử lý khi kết nối thành công: Gửi gói login báo tên và avatar của mình lên Server"""
        self.lbl_status.setText("Trạng thái: Đã kết nối Server")
        self.lbl_status.setStyleSheet("border: none; color: #40c057; font-weight: bold; font-size: 13px;")
        self.btn_connect.setEnabled(False)
        self.txt_username.setEnabled(False)
        self.txt_ip.setEnabled(False)
        self.txt_port.setEnabled(False)

        # Gửi thông điệp login kèm username và avatar để Server đồng bộ danh sách online (Tuần 2 & 3)
        my_name = self.txt_username.text().strip()
        my_avatar = getattr(self, "my_avatar", "default_avatar.png")
        login_packet = {
            "type": "login",
            "username": my_name,
            "avatar": my_avatar
        }
        self.network_client.send_data(login_packet)

    def on_disconnected(self):
        """Xử lý khi ngắt kết nối khỏi Server"""
        self.lbl_status.setText("Trạng thái: Đã ngắt kết nối")
        self.lbl_status.setStyleSheet("border: none; color: #b0b3b8; font-style: italic; font-size: 13px;")
        self.btn_connect.setEnabled(True)
        self.txt_username.setEnabled(True)
        self.txt_ip.setEnabled(True)
        self.txt_port.setEnabled(True)

        # Đổi tất cả người dùng sang trạng thái offline khi mất kết nối
        self.lbl_online.setText("Online Users (Đã ngắt kết nối)")
        for i in range(self.sidebar_content_layout.count()):
            w = self.sidebar_content_layout.itemAt(i).widget()
            if w:
                # Tìm chấm trạng thái (dot) và đổi sang màu xám
                for dot in w.findChildren(QLabel):
                    if dot.width() == 12 and dot.height() == 12:
                        dot.setStyleSheet("background-color: #b0b3b8; border-radius: 6px; border: 2px solid #242526;")

    def on_network_error(self, err_msg):
        """Xử lý khi gặp lỗi mạng"""
        self.lbl_status.setText("Trạng thái: Lỗi kết nối")
        self.lbl_status.setStyleSheet("border: none; color: #fa5252; font-style: italic; font-size: 13px;")
        self.btn_connect.setEnabled(True)
        self.txt_username.setEnabled(True)
        self.txt_ip.setEnabled(True)
        self.txt_port.setEnabled(True)
        QMessageBox.warning(self, "Lỗi mạng", err_msg)

    def on_message_received(self, data):
        """
        BẮT TẤT CẢ SIGNAL TỪ NETWORK_WORKER:
        - Đồng bộ danh sách online lên Sidebar (Nhiệm vụ chính Tuần 2)
        - Thêm/Xóa user khi có sự kiện join/leave
        - Lọc forward_ack và error để hiển thị thông báo hệ thống thay vì vẽ bong bóng Server
        - Hiển thị tin nhắn chat qua MessageItem (kèm trích dẫn reply và avatar)
        """
        if not isinstance(data, dict):
            return

        msg_type = data.get("type", "")

        # 1. Bắt signal cập nhật toàn bộ danh sách online từ Server (Tuần 2)
        if msg_type in ("online_list", "online_users", "user_list", "login_ack"):
            user_list = data.get("online_users") or data.get("users") or data.get("data") or []
            self.update_online_users(user_list)
            return

        # 2. Bắt signal khi có 1 user mới vừa vào mạng
        if msg_type in ("user_join", "user_online"):
            new_user = data.get("username", "")
            avatar = data.get("avatar", None)
            if new_user:
                self.add_online_user(new_user, avatar_path=avatar)
                self.add_system_message(f"{new_user} đã tham gia phòng chat.")
            return

        # 3. Bắt signal khi có 1 user vừa ngắt kết nối
        if msg_type in ("user_leave", "user_offline"):
            left_user = data.get("username", "")
            if left_user:
                self.remove_online_user(left_user)
                self.add_system_message(f"{left_user} đã rời phòng chat.")
            return

        # 4. Lọc gói tin xác nhận chuyển tiếp (forward_ack)
        if msg_type == "forward_ack":
            status = data.get("status")
            receiver = data.get("receiver", "phòng chung")
            if status == "success":
                self.add_system_message(f"Đã chuyển tiếp tin nhắn tới '{receiver}' thành công.")
            else:
                err_msg = data.get("message", "Chuyển tiếp thất bại.")
                self.add_system_message(f"Lỗi chuyển tiếp: {err_msg}")
            return

        # 5. Lọc gói tin báo lỗi (error) từ server
        if msg_type == "error":
            err_data = data.get("error", {})
            if isinstance(err_data, dict):
                err_msg = err_data.get("message") or err_data.get("code") or "Lỗi từ máy chủ."
            else:
                err_msg = str(data.get("message") or err_data or "Lỗi từ máy chủ.")
            self.add_system_message(f"Lỗi máy chủ: {err_msg}")
            return

        # 6. Bắt tin nhắn chat thông thường / reply / forward -> hiển thị qua bong bóng MessageItem
        sender = data.get("sender", "Server")
        content = data.get("content", str(data))
        msg_id = data.get("msg_id")
        avatar = data.get("avatar")
        reply_to = data.get("reply_to")

        if msg_type == "forward":
            orig_sender = data.get("original_sender", "")
            if orig_sender and orig_sender != sender:
                content = f"↗️ Chuyển tiếp từ {orig_sender}: {content}"

        my_name = self.txt_username.text().strip()
        is_self = (sender == my_name) or (sender == "Bạn")
        
        # Chỉ vẽ nếu tin nhắn không phải từ chính mình gửi lại (tránh bị lặp tin 2 lần)
        if not is_self:
            self.add_message_to_chat(
                sender=sender,
                message=content,
                is_self=False,
                msg_id=msg_id,
                avatar_path=avatar,
                reply_to=reply_to
            )

    def demo_emoji_click(self):
        """Mở Emoji Picker từ gui_actions.py"""
        if hasattr(self, 'emoji_dialog') and self.emoji_dialog:
            self.emoji_dialog.show()

    def closeEvent(self, event):
        """Dọn dẹp kết nối khi đóng ứng dụng"""
        if hasattr(self, 'network_client') and self.network_client and self.network_client.is_running:
            self.network_client.stop()
        if hasattr(self, 'emoji_dialog') and self.emoji_dialog:
            self.emoji_dialog.close()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
