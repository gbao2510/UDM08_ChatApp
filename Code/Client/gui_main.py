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
    QFrame, QMessageBox, QScrollArea, QFileDialog, QMenu, QDialog
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QKeySequence, QShortcut, QPixmap, QIcon, QPainter, QPainterPath

def load_stylesheet(filename: str = "style.css") -> str:
    """Đọc và nạp nội dung file CSS/QSS riêng biệt từ thư mục Client"""
    css_path = os.path.join(current_dir, filename)
    if os.path.exists(css_path):
        try:
            with open(css_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"[CSS Error] Không thể nạp file {filename}: {e}")
    return ""

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


class AvatarChooserDialog(QDialog):
    """Hộp thoại trực quan để người dùng chọn ảnh đại diện có sẵn hoặc tải từ máy tính"""
    def __init__(self, current_avatar: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chọn ảnh đại diện của bạn")
        self.setFixedSize(380, 260)
        self.selected_avatar = current_avatar
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        lbl_title = QLabel("Chọn một ảnh đại diện yêu thích:")
        lbl_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #1e293b;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        assets_dir = os.path.join(current_dir, "assets")
        preset_avatars = [
            ("avatar_user1.png", "Bé Shin 1"),
            ("avatar_user2.png", "Bé Shin 2"),
            ("avatar_user3.png", "Bé Shin 3"),
            ("avatar_user4.png", "Bé Shin 4"),
            ("default_avatar.png", "Mặc định"),
        ]

        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(10)
        grid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for file_name, label_text in preset_avatars:
            vbox = QVBoxLayout()
            vbox.setSpacing(4)
            vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)

            full_path = os.path.join(assets_dir, file_name)
            btn = QPushButton()
            btn.setFixedSize(48, 48)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            pix = QPixmap(full_path) if os.path.exists(full_path) else QPixmap()
            if not pix.isNull():
                rounded = QPixmap(48, 48)
                rounded.fill(Qt.GlobalColor.transparent)
                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                path = QPainterPath()
                path.addEllipse(0, 0, 48, 48)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, pix.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                painter.end()
                btn.setIcon(QIcon(rounded))
                btn.setIconSize(QSize(48, 48))

            is_current = (file_name == os.path.basename(self.selected_avatar))
            border_color = "#3b82f6" if is_current else "#cbd5e1"
            bg_color = "#eff6ff" if is_current else "#ffffff"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_color};
                    border: 2.5px solid {border_color};
                    border-radius: 24px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    border-color: #2563eb;
                    background-color: #dbeafe;
                }}
            """)
            btn.clicked.connect(lambda _, fn=file_name: self._on_avatar_selected(fn))

            lbl_name = QLabel(label_text)
            lbl_name.setStyleSheet("font-size: 11px; color: #64748b;")
            lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)

            vbox.addWidget(btn)
            vbox.addWidget(lbl_name)
            grid_layout.addLayout(vbox)

        layout.addLayout(grid_layout)

        # Nút tùy chọn tải ảnh từ máy tính
        btn_custom = QPushButton("📂 Tải ảnh từ máy tính...")
        btn_custom.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_custom.setStyleSheet("""
            QPushButton {
                background-color: #f8fafc;
                color: #334155;
                font-weight: 600;
                font-size: 12px;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
                color: #1e293b;
                border-color: #94a3b8;
            }
        """)
        btn_custom.clicked.connect(self._choose_custom_file)
        layout.addWidget(btn_custom)

        # Nút Đóng
        btn_close = QPushButton("Đóng")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #e2e8f0;
                color: #475569;
                font-weight: 600;
                font-size: 12px;
                border: none;
                border-radius: 8px;
                padding: 5px 14px;
            }
            QPushButton:hover {
                background-color: #cbd5e1;
            }
        """)
        btn_close.clicked.connect(self.reject)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

    def _on_avatar_selected(self, file_name: str):
        self.selected_avatar = file_name
        self.accept()

    def _choose_custom_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn ảnh đại diện của bạn",
            "",
            "Hình ảnh (*.png *.jpg *.jpeg *.bmp *.ico);;Tất cả tệp (*.*)"
        )
        if file_path:
            self.selected_avatar = file_path
            self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chat Application ")
        self.resize(920, 650)
        self.setMinimumSize(780, 520)

        # Trạng thái hội thoại (Phòng chung và Chat riêng 1-1)
        self.chat_target = "all"
        self.conversations = {"all": []}
        self.unread_counts = {}

        # Trạng thái Reply hiện tại và danh sách user online để tái sử dụng cho menu hành động
        self.replying_to = None
        self.online_users_cache = []
        self.my_avatar = "avatar_user1.png"

        # Cài đặt giao diện và nạp stylesheet từ file CSS riêng
        self.setup_ui()
        self.apply_stylesheet()
        self.setup_shortcuts()
        
        # Nạp dữ liệu mẫu ban đầu (Mock Data) để hiển thị đầy đủ danh sách bạn bè, avatar và tin nhắn chat
        self.load_initial_data()
        self.update_sidebar_active_state()

        # Khởi tạo các module liên kết
        self.emoji_dialog = EmojiPickerDialog(parent_input_field=self.txt_message) if EmojiPickerDialog else None
        self.network_client = None

    def apply_stylesheet(self):
        """Nạp và kích hoạt style.css riêng cho cửa sổ chính"""
        css = load_stylesheet("style.css")
        if css:
            self.setStyleSheet(css)

    def _on_chat_scroll_range_changed(self, min_val, max_val):
        """Tự động cuộn xuống đáy khi khung chat có thêm tin nhắn mới (mở rộng vùng cuộn)"""
        self.scroll_chat.verticalScrollBar().setValue(max_val)

    def scroll_to_bottom(self):
        """
        Nhiệm vụ: Tự cuộn xuống đáy khi có tin mới.
        Dùng multi-stage QTimer để đảm bảo ngay cả khi tin nhắn dài/ảnh chưa render xong layout,
        thanh cuộn vẫn đảm bảo 100% chạm đáy.
        """
        bar = self.scroll_chat.verticalScrollBar()
        bar.setValue(bar.maximum())
        QTimer.singleShot(10, lambda: bar.setValue(bar.maximum()))
        QTimer.singleShot(50, lambda: bar.setValue(bar.maximum()))
        QTimer.singleShot(120, lambda: bar.setValue(bar.maximum()))

    def set_online_count(self, count):
        """Hiển thị nhãn Online Users kèm huy hiệu số lượng màu xanh chuẩn theo Mockup"""
        self.lbl_online.setText(
            f'Online Users <span style="background-color: #3ca56c; color: #ffffff; border-radius: 9px; padding: 2px 7px; font-size: 11px; font-weight: bold;">{count}</span>'
        )

    def toggle_network_bar(self):
        """Ẩn hoặc hiện thanh thông tin User / IP / Port / Kết nối"""
        is_visible = self.network_box.isVisible()
        self.network_box.setVisible(not is_visible)
        self.btn_show_network.setVisible(is_visible)
        self.update_collapsed_network_text()

    def update_collapsed_network_text(self):
        """Cập nhật nội dung vắn tắt trên nút mở rộng khi thanh kết nối bị ẩn"""
        user = self.txt_username.text().strip() if hasattr(self, 'txt_username') else "Gia Bảo"
        ip = self.txt_ip.text().strip() if hasattr(self, 'txt_ip') else "127.0.0.1"
        port = self.txt_port.text().strip() if hasattr(self, 'txt_port') else "5000"
        
        is_connected = bool(self.network_client and self.network_client.is_running)
        if is_connected:
            self.btn_show_network.setText(f"🟢 Đã kết nối: {ip}:{port} • {user} ▼")
        else:
            self.btn_show_network.setText(f"⚙️ Cài đặt kết nối: {ip}:{port} • {user} ▼")

    def setup_shortcuts(self):
        """Cài đặt các phím tắt: Thoát/rời phòng chat bằng Ctrl+Q, Ctrl+W hoặc Ctrl+D"""
        self.shortcut_quit = QShortcut(QKeySequence("Ctrl+Q"), self)
        self.shortcut_quit.activated.connect(self.leave_room)

        self.shortcut_close = QShortcut(QKeySequence("Ctrl+W"), self)
        self.shortcut_close.activated.connect(self.leave_room)

        self.shortcut_disconnect = QShortcut(QKeySequence("Ctrl+D"), self)
        self.shortcut_disconnect.activated.connect(self.leave_room)

    def leave_room(self):
        """Xử lý rời khỏi phòng chat (Thoát phòng) qua phím tắt (Ctrl+Q / Ctrl+W / Ctrl+D) hoặc nút bấm"""
        is_connected = bool(self.network_client and self.network_client.is_running)

        reply = QMessageBox.question(
            self,
            "Xác nhận thoát phòng",
            "Bạn có chắc chắn muốn rời khỏi phòng chat không?\n(Phím tắt: Ctrl+Q hoặc Ctrl+W)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        my_name = self.txt_username.text().strip() or "Gia Bảo"

        if is_connected:
            try:
                self.network_client.send_data({
                    "type": "leave",
                    "sender": my_name
                })
            except Exception:
                pass
            self.network_client.stop()

        self.lbl_status.setText("Trạng thái: Đã rời phòng")
        self.lbl_status.setStyleSheet("border: none; color: #fa5252; font-style: italic; font-size: 13px;")
        self.btn_connect.setEnabled(True)
        if hasattr(self, 'btn_leave'):
            self.btn_leave.setEnabled(False)
        self.txt_username.setEnabled(True)
        self.txt_ip.setEnabled(True)
        self.txt_port.setEnabled(True)

        self.set_online_count(0)
        for i in range(self.sidebar_content_layout.count()):
            w = self.sidebar_content_layout.itemAt(i).widget()
            if w:
                for dot in w.findChildren(QLabel):
                    if dot.width() == 12 and dot.height() == 12:
                        dot.setStyleSheet("background-color: #94a3b8; border-radius: 6px; border: 2px solid #ffffff;")

        self.add_system_message("Bạn đã rời khỏi phòng chat (Ctrl+Q).")
        self.switch_to_chat_target("all")
        self.update_collapsed_network_text()

    def setup_ui(self):
        # Widget trung tâm - Quản lý qua file style.css
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # 1. KHU VỰC CẤU HÌNH MẠNG & USERNAME (TOP BAR - CÓ THỂ BẤM ẨN/HIỆN)
        # Nút mở lại thanh kết nối (hiển thị khi thanh kết nối đang bị ẩn)
        self.btn_show_network = QPushButton("⚙️ Cài đặt kết nối: 127.0.0.1:5000 • Gia Bảo ▼")
        self.btn_show_network.setObjectName("btnShowNetwork")
        self.btn_show_network.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_show_network.setToolTip("Bấm để hiển thị lại thanh cấu hình IP / Port / User")
        self.btn_show_network.clicked.connect(self.toggle_network_bar)
        self.btn_show_network.hide()

        self.network_box = QFrame()
        self.network_box.setObjectName("networkBox")
        network_layout = QHBoxLayout(self.network_box)
        network_layout.setContentsMargins(14, 10, 14, 10)
        network_layout.setSpacing(10)

        # Nút Avatar cá nhân (Click để đổi avatar)
        self.avatar_btn = QPushButton()
        self.avatar_btn.setObjectName("btnMyAvatar")
        self.avatar_btn.setFixedSize(36, 36)
        self.avatar_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.avatar_btn.setToolTip("Bấm để đổi ảnh đại diện của bạn")
        self.avatar_btn.clicked.connect(self.open_avatar_chooser)
        self.update_my_avatar_button()

        # Ô nhập tên tài khoản
        lbl_user = QLabel("User:")
        lbl_user.setObjectName("lblTopBar")
        self.txt_username = QLineEdit("Gia Bảo")
        self.txt_username.setObjectName("txtUsername")
        self.txt_username.setPlaceholderText("Tên bạn")
        self.txt_username.setFixedWidth(110)

        # Ô nhập IP
        lbl_ip = QLabel("Server IP:")
        lbl_ip.setObjectName("lblTopBar")
        self.txt_ip = QLineEdit("127.0.0.1")
        self.txt_ip.setObjectName("txtIp")
        self.txt_ip.setPlaceholderText("VD: 127.0.0.1")
        self.txt_ip.setFixedWidth(120)

        # Ô nhập Port
        lbl_port = QLabel("Port:")
        lbl_port.setObjectName("lblTopBar")
        self.txt_port = QLineEdit("5000")
        self.txt_port.setObjectName("txtPort")
        self.txt_port.setPlaceholderText("Port")
        self.txt_port.setFixedWidth(65)

        # Nút Kết nối
        self.btn_connect = QPushButton("Kết nối")
        self.btn_connect.setObjectName("btnConnect")
        self.btn_connect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_connect.clicked.connect(self.demo_connect_action)

        # Nút Rời phòng (Phím tắt: Ctrl+Q hoặc Ctrl+W)
        self.btn_leave = QPushButton("Rời phòng")
        self.btn_leave.setObjectName("btnLeave")
        self.btn_leave.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_leave.setToolTip("Rời khỏi phòng chat (Phím tắt: Ctrl+Q hoặc Ctrl+W)")
        self.btn_leave.clicked.connect(self.leave_room)
        self.btn_leave.setEnabled(False)
        self.btn_leave.setStyleSheet("""
            QPushButton#btnLeave {
                background-color: #fee2e2;
                color: #dc2626;
                font-weight: bold;
                padding: 6px 14px;
                border-radius: 8px;
                border: 1px solid #fca5a5;
                font-size: 13px;
            }
            QPushButton#btnLeave:hover {
                background-color: #fecaca;
                border-color: #f87171;
            }
            QPushButton#btnLeave:pressed {
                background-color: #fca5a5;
            }
            QPushButton#btnLeave:disabled {
                background-color: #f1f5f9;
                color: #94a3b8;
                border: 1px solid #e2e8f0;
            }
        """)

        self.lbl_status = QLabel("Trạng thái: Chưa kết nối")
        self.lbl_status.setObjectName("lblStatus")

        # Nút bấm để ẩn thanh kết nối
        self.btn_hide_network = QPushButton("▲ Ẩn")
        self.btn_hide_network.setObjectName("btnHideNetwork")
        self.btn_hide_network.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hide_network.setToolTip("Ẩn thanh thông tin kết nối để mở rộng khung chat")
        self.btn_hide_network.clicked.connect(self.toggle_network_bar)

        network_layout.addWidget(self.avatar_btn)
        network_layout.addWidget(lbl_user)
        network_layout.addWidget(self.txt_username)
        network_layout.addWidget(lbl_ip)
        network_layout.addWidget(self.txt_ip)
        network_layout.addWidget(lbl_port)
        network_layout.addWidget(self.txt_port)
        network_layout.addWidget(self.btn_connect)
        network_layout.addWidget(self.btn_leave)
        network_layout.addWidget(self.lbl_status)
        network_layout.addStretch()
        network_layout.addWidget(self.btn_hide_network)

        main_layout.addWidget(self.btn_show_network, alignment=Qt.AlignmentFlag.AlignHCenter)
        main_layout.addWidget(self.network_box)

        # 2. KHU VỰC THÂN CHÍNH (SIDEBAR + KHUNG CHAT)
        body_layout = QHBoxLayout()
        body_layout.setSpacing(12)

        # 2.1 Sidebar: Danh sách người online với ẢNH ĐẠI DIỆN (CircularAvatar từ gui_widgets.py)
        sidebar_outer = QVBoxLayout()
        sidebar_outer.setSpacing(6)

        # Thẻ chuyển nhanh về Phòng Chat Chung
        self.row_public_room = self._create_public_room_row()
        sidebar_outer.addWidget(self.row_public_room)

        self.lbl_online = QLabel()
        self.lbl_online.setObjectName("lblOnlineTitle")
        self.set_online_count(0)
        sidebar_outer.addWidget(self.lbl_online)

        # Dùng QScrollArea + Widget tùy chỉnh để hiển thị Avatar + Tên (không dùng QListWidget)
        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setObjectName("sidebarScroll")
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setFixedWidth(240)
        self.sidebar_content = QWidget()
        self.sidebar_content.setObjectName("sidebarContent")
        self.sidebar_content_layout = QVBoxLayout(self.sidebar_content)
        self.sidebar_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.sidebar_content_layout.setContentsMargins(8, 8, 8, 8)
        self.sidebar_content_layout.setSpacing(4)
        self.sidebar_scroll.setWidget(self.sidebar_content)

        sidebar_outer.addWidget(self.sidebar_scroll)
        body_layout.addLayout(sidebar_outer)

        # 2.2 Chat Area: TÍCH HỢP MESSAGEITEM VÀ SCROLLAREA TỪ GUI_WIDGETS.PY
        chat_layout = QVBoxLayout()

        # Thanh tiêu đề hội thoại (Chat Header) hỗ trợ chuyển đổi giữa Phòng Chung và Chat Riêng 1-1
        chat_header = QWidget()
        chat_header.setObjectName("chatHeader")
        chat_header_layout = QHBoxLayout(chat_header)
        chat_header_layout.setContentsMargins(4, 0, 4, 2)
        chat_header_layout.setSpacing(8)

        self.lbl_chat = QLabel("Phòng Chat Chung")
        self.lbl_chat.setObjectName("lblChatTitle")

        self.lbl_target_badge = QLabel("Công khai")
        self.lbl_target_badge.setObjectName("lblTargetBadge")
        self.lbl_target_badge.setStyleSheet(
            "background-color: #e2e8f0; color: #475569; border-radius: 8px; padding: 2px 8px; font-size: 11px; font-weight: 600;"
        )

        self.btn_back_to_public = QPushButton("🌐 Về phòng chung")
        self.btn_back_to_public.setObjectName("btnBackToPublic")
        self.btn_back_to_public.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back_to_public.setToolTip("Quay lại trò chuyện trong Phòng Chat Chung")
        self.btn_back_to_public.setStyleSheet("""
            QPushButton#btnBackToPublic {
                background-color: #eff6ff;
                color: #2563eb;
                border: 1px solid #bfdbfe;
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton#btnBackToPublic:hover {
                background-color: #dbeafe;
                border-color: #93c5fd;
            }
            QPushButton#btnBackToPublic:pressed {
                background-color: #bfdbfe;
            }
        """)
        self.btn_back_to_public.clicked.connect(lambda: self.switch_to_chat_target("all"))
        self.btn_back_to_public.hide()

        chat_header_layout.addWidget(self.lbl_chat)
        chat_header_layout.addWidget(self.lbl_target_badge)
        chat_header_layout.addStretch()
        chat_header_layout.addWidget(self.btn_back_to_public)

        self.scroll_chat = QScrollArea()
        self.scroll_chat.setObjectName("chatScrollArea")
        self.scroll_chat.setWidgetResizable(True)
        # Tự động cuộn xuống đáy khi có tin nhắn mới làm thay đổi chiều cao nội dung chat
        self.scroll_chat.verticalScrollBar().rangeChanged.connect(self._on_chat_scroll_range_changed)

        self.chat_container = QWidget()
        self.chat_container.setObjectName("chatContainer")
        self.chat_content_layout = QVBoxLayout(self.chat_container)
        self.chat_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_content_layout.setSpacing(6)
        self.scroll_chat.setWidget(self.chat_container)

        # Thanh trạng thái phụ trên khung chat: "Đang trả lời: [Tên]" kèm nút X hủy
        self.reply_bar = QFrame()
        self.reply_bar.setObjectName("replyStatusBar")
        reply_bar_layout = QHBoxLayout(self.reply_bar)
        reply_bar_layout.setContentsMargins(10, 6, 8, 6)
        reply_bar_layout.setSpacing(8)

        self.lbl_reply_status = QLabel("")
        self.lbl_reply_status.setObjectName("lblReplyStatus")

        self.lbl_reply_preview = QLabel("")
        self.lbl_reply_preview.setObjectName("lblReplyPreview")

        self.btn_cancel_reply = QPushButton("X")
        self.btn_cancel_reply.setObjectName("btnCancelReply")
        self.btn_cancel_reply.setFixedSize(22, 22)
        self.btn_cancel_reply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel_reply.setToolTip("Hủy trả lời")
        self.btn_cancel_reply.clicked.connect(self.cancel_reply)

        reply_bar_layout.addWidget(self.lbl_reply_status)
        reply_bar_layout.addWidget(self.lbl_reply_preview, stretch=1)
        reply_bar_layout.addWidget(self.btn_cancel_reply)
        self.reply_bar.hide()

        chat_layout.addWidget(chat_header)
        chat_layout.addWidget(self.scroll_chat)
        chat_layout.addWidget(self.reply_bar)
        body_layout.addLayout(chat_layout, stretch=1)

        main_layout.addLayout(body_layout, stretch=1)

        # 3. KHU VỰC NHẬP TIN NHẮN (THANH PILL BO TRÒN VÀ CÁC NÚT ICON THEO MOCKUP)
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        # Nút tròn dấu (+) bên trái
        self.btn_plus = QPushButton("+")
        self.btn_plus.setObjectName("btnPlus")
        self.btn_plus.setFixedSize(38, 38)
        self.btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_plus.setToolTip("Thêm tệp hoặc tính năng (Click để mở menu)")
        self.btn_plus.clicked.connect(self.show_plus_menu)

        # Khung Pill tròn màu trắng chứa ô nhập và các biểu tượng
        self.input_pill = QFrame()
        self.input_pill.setObjectName("inputPill")
        input_pill_layout = QHBoxLayout(self.input_pill)
        input_pill_layout.setContentsMargins(14, 2, 8, 2)
        input_pill_layout.setSpacing(6)

        # Ô nhập tin nhắn
        if AutoResizingTextEdit:
            self.txt_message = AutoResizingTextEdit(min_height=34, max_height=100)
            self.txt_message.setObjectName("inputMessage")
            self.txt_message.setStyleSheet("")  # Dùng style từ style.css
            self.txt_message.setPlaceholderText("Nhập tin nhắn...")
            self.txt_message.text = self.txt_message.toPlainText
            self.txt_message.send_requested.connect(self.send_message)
        else:
            self.txt_message = QLineEdit()
            self.txt_message.setObjectName("inputMessage")
            self.txt_message.setPlaceholderText("Nhập tin nhắn...")
            self.txt_message.setFixedHeight(34)
            self.txt_message.returnPressed.connect(self.send_message)

        # Các nút biểu tượng bên phải thanh pill (📎 Đính kèm, 😊 Emoji, 🎙️ Ghi âm)
        self.btn_attach = QPushButton("📎")
        self.btn_attach.setObjectName("btnAttach")
        self.btn_attach.setFixedSize(28, 28)
        self.btn_attach.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_attach.setToolTip("Đính kèm tệp hoặc hình ảnh")
        self.btn_attach.clicked.connect(lambda: self.choose_and_send_file(image_only=False))

        self.btn_emoji = QPushButton("😊")
        self.btn_emoji.setObjectName("btnEmoji")
        self.btn_emoji.setFixedSize(28, 28)
        self.btn_emoji.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_emoji.setToolTip("Chọn Emoji (gui_actions.py)")
        self.btn_emoji.clicked.connect(self.demo_emoji_click)

        self.btn_mic = QPushButton("🎙️")
        self.btn_mic.setObjectName("btnMic")
        self.btn_mic.setFixedSize(28, 28)
        self.btn_mic.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mic.setToolTip("Ghi âm giọng nói")
        self.btn_mic.clicked.connect(self.demo_mic_click)

        input_pill_layout.addWidget(self.txt_message, stretch=1)
        input_pill_layout.addWidget(self.btn_attach)
        input_pill_layout.addWidget(self.btn_emoji)
        input_pill_layout.addWidget(self.btn_mic)

        # Nút Send phong cách Gradient xanh biển theo Mockup
        self.btn_send = QPushButton("✈  Send")
        self.btn_send.setObjectName("btnSend")
        self.btn_send.setFixedHeight(38)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.clicked.connect(self.send_message)

        bottom_layout.addWidget(self.btn_plus, alignment=Qt.AlignmentFlag.AlignBottom)
        bottom_layout.addWidget(self.input_pill, stretch=1)
        bottom_layout.addWidget(self.btn_send, alignment=Qt.AlignmentFlag.AlignBottom)

        main_layout.addLayout(bottom_layout)

    def _create_public_room_row(self) -> QFrame:
        """Tạo thẻ bấm chuyển nhanh về Phòng Chat Chung trên đầu sidebar"""
        frame = QFrame()
        frame.setObjectName("rowPublicRoom")
        frame.setFixedHeight(52)
        frame.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        icon_lbl = QLabel("🌐")
        icon_lbl.setFixedSize(38, 38)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #dbeafe, stop:1 #bfdbfe); border-radius: 19px; font-size: 18px;")

        text_vbox = QVBoxLayout()
        text_vbox.setSpacing(1)
        lbl_title = QLabel("Phòng Chat Chung")
        lbl_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #1e293b; background: transparent;")
        lbl_sub = QLabel("Tất cả thành viên")
        lbl_sub.setStyleSheet("font-size: 11px; color: #64748b; background: transparent;")
        text_vbox.addWidget(lbl_title)
        text_vbox.addWidget(lbl_sub)

        self.badge_public = QLabel("")
        self.badge_public.setObjectName("badgePublic")
        self.badge_public.setFixedSize(18, 18)
        self.badge_public.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge_public.setStyleSheet("background-color: #3b82f6; color: #ffffff; border-radius: 9px; font-size: 10px; font-weight: bold;")
        self.badge_public.hide()

        layout.addWidget(icon_lbl)
        layout.addLayout(text_vbox, stretch=1)
        layout.addWidget(self.badge_public)

        # Chặn bắt chuột ở label con để click trúng frame
        icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        lbl_title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        lbl_sub.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.badge_public.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        frame.mousePressEvent = lambda e: self.switch_to_chat_target("all")
        return frame

    def load_initial_data(self):
        """Nạp dữ liệu mẫu ban đầu (Mock Data) gồm cả ảnh đại diện trong sidebar và phân chia hội thoại"""
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
        self.set_online_count(len(mock_users))

        # 2. Nạp bong bóng tin nhắn mẫu chuẩn từ gui_widgets.py vào Phòng Chat Chung
        mock_messages = [
            {"sender": "Ngô Gia Bảo",  "text": "Tiến độ hoàn thành như nào rồi.", "is_self": False},
            {"sender": "Nguyễn Gia Bảo", "text": "T đang hoàn thiện component MessageItem hiển thị độc lập.", "is_self": True},
            {"sender": "Lý Huỳnh Bích Trâm", "text": "Socket client tuần này gửi nhận chuỗi JSON cơ bản được rồi.", "is_self": False},
            {"sender": "Nguyễn Gia Bảo", "text": "Thử nghiệm tin nhắn dài tự động xuống dòng và co giãn chiều cao xem bong bóng chat có hoạt động chuẩn không.", "is_self": True},
        ]
        self.conversations["all"] = []
        for data in mock_messages:
            self.add_message_to_chat(
                sender=data["sender"],
                message=data["text"],
                is_self=data["is_self"],
                target="all"
            )

        # 3. Tạo sẵn dữ liệu mẫu cho cuộc trò chuyện riêng với Trần Thuận Trí
        self.conversations["Trần Thuận Trí"] = [
            {
                "sender": "Trần Thuận Trí",
                "message": "Chào Bảo, bạn đã xong phần giao diện tin nhắn riêng 1-1 chưa?",
                "is_self": False,
                "msg_id": 101,
                "avatar_path": None,
                "reply_to": None,
                "target": "Trần Thuận Trí",
            },
            {
                "sender": "Nguyễn Gia Bảo",
                "message": "Mình vừa hoàn thiện xong! Bạn chỉ cần click trực tiếp vào tên bất kỳ ai trên sidebar là có thể nhắn riêng rồi nhé.",
                "is_self": True,
                "msg_id": 102,
                "avatar_path": getattr(self, "my_avatar", "default_avatar.png"),
                "reply_to": None,
                "target": "Trần Thuận Trí",
            }
        ]

    # =========================================================================
    # NHIỆM VỤ TUẦN 3 & TIN NHẮN RIÊNG: HIỂN THỊ DANH SÁCH BẠN BÈ VÀ CHỌN CHAT 1-1
    # =========================================================================
    def _make_user_row(self, name: str, is_online: bool = True, avatar_path: str = None) -> QWidget:
        """
        Tạo 1 dòng hiển thị người dùng trong sidebar gồm:
        - Ảnh đại diện tròn (CircularAvatar từ gui_widgets.py)
        - Chấm trạng thái xanh/xám overlay lên góc avatar
        - Tên người dùng và trạng thái
        - Huy hiệu số tin nhắn chưa đọc (nếu có)
        - Sự kiện click chuột để chuyển sang chat riêng 1-1
        """
        # Đường dẫn ảnh đại diện: ghép với thư mục assets/ nếu là tên file tương đối
        my_name = self.txt_username.text().strip() if hasattr(self, 'txt_username') else ""
        if (name == my_name or name == "Nguyễn Gia Bảo") and not avatar_path:
            avatar_path = getattr(self, "my_avatar", "avatar_user1.png")
        used_path = self._resolve_avatar_path(avatar_path)

        row = QWidget()
        row.setObjectName("userRow")
        row.setProperty("username", name)
        row.setProperty("is_self", (name == my_name or name == "Nguyễn Gia Bảo"))
        row.setFixedHeight(58)
        row.setCursor(Qt.CursorShape.PointingHandCursor)
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

        avatar_frame_layout.addWidget(avatar)

        # Chấm trạng thái online/offline (QLabel nhỏ đè lên góc phải-dưới)
        dot = QLabel()
        dot.setObjectName("dotOnline" if is_online else "dotOffline")
        dot.setFixedSize(12, 12)
        dot.setParent(avatar_frame)
        dot.move(28, 28)          # Góc dưới bên phải của avatar 38px
        dot.setStyleSheet(
            f"background-color: {'#10b981' if is_online else '#94a3b8'}; border-radius: 6px; border: 2px solid #ffffff;"
        )
        dot.raise_()

        row_layout.addWidget(avatar_frame)

        # Khối tên + trạng thái chữ
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)

        my_name = self.txt_username.text().strip() if hasattr(self, 'txt_username') else ""
        display_name = f"{name} (Bạn)" if name == my_name else name

        lbl_name = QLabel(display_name)
        lbl_name.setObjectName("userNameSelf" if name == my_name else "userName")

        lbl_status_txt = QLabel("Online" if is_online else "Offline")
        lbl_status_txt.setObjectName("userStatus" if is_online else "userStatusOffline")

        text_layout.addWidget(lbl_name)
        text_layout.addWidget(lbl_status_txt)
        row_layout.addLayout(text_layout, stretch=1)

        # Huy hiệu tin nhắn riêng chưa đọc
        lbl_badge = QLabel()
        lbl_badge.setObjectName("lblUnreadBadge")
        lbl_badge.setFixedSize(18, 18)
        lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_badge.setStyleSheet(
            "background-color: #ef4444; color: #ffffff; border-radius: 9px; font-size: 10px; font-weight: bold;"
        )
        unread_count = self.unread_counts.get(name, 0) if hasattr(self, 'unread_counts') else 0
        if unread_count > 0 and (not hasattr(self, 'chat_target') or self.chat_target != name):
            lbl_badge.setText(str(unread_count) if unread_count <= 99 else "99+")
            lbl_badge.show()
        else:
            lbl_badge.hide()
        row_layout.addWidget(lbl_badge)

        # Để sự kiện click chuột luôn rơi vào `row`
        for child in (avatar_frame, lbl_name, lbl_status_txt, lbl_badge):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        row.mousePressEvent = lambda event, target_name=name: self.on_user_row_clicked(target_name)

        # Áp dụng màu active nếu đang chọn chat riêng với user này
        is_active = (hasattr(self, 'chat_target') and self.chat_target == name)
        if is_active:
            row.setStyleSheet("""
                QWidget#userRow {
                    background-color: #e0e7ff;
                    border-radius: 10px;
                    border: 1.5px solid #6366f1;
                }
                QWidget#userRow:hover {
                    background-color: #dbeafe;
                }
            """)
        else:
            row.setStyleSheet("""
                QWidget#userRow {
                    background-color: transparent;
                    border-radius: 10px;
                    border: 1.5px solid transparent;
                }
                QWidget#userRow:hover {
                    background-color: #f1f5f9;
                }
            """)

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
        self.set_online_count(count)

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
        self.set_online_count(count)

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
        self.set_online_count(count)

    def get_online_usernames(self):
        """Trả về danh sách tên người dùng online hiện tại cho ForwardDialog"""
        return list(self.online_users_cache)

    # =========================================================================
    # QUẢN LÝ CHUYỂN ĐỔI HỘI THOẠI & TIN NHẮN RIÊNG 1-1
    # =========================================================================
    def on_user_row_clicked(self, target_name: str):
        """Xử lý khi người dùng click vào một bạn bè trong danh sách online"""
        my_name = self.txt_username.text().strip() if hasattr(self, 'txt_username') else ""
        if target_name == my_name:
            self.add_system_message("Đây là tài khoản của chính bạn.")
            return
        self.switch_to_chat_target(target_name)

    def switch_to_chat_target(self, target: str):
        """Chuyển đổi khu vực chat giữa Phòng Chat Chung ('all') và Chat riêng với 1 người"""
        target = (target or "all").strip()
        if target == self.chat_target:
            return

        self.chat_target = target
        
        # Hủy trạng thái reply từ hội thoại trước để tránh gửi nhầm
        if self.replying_to:
            self.cancel_reply()

        # Xóa badge chưa đọc của hội thoại này khi đã mở xem
        self.unread_counts[target] = 0

        self.update_chat_header()
        self.update_sidebar_active_state()
        self.update_sidebar_badges()
        self.render_current_conversation()

    def update_chat_header(self):
        """Cập nhật tiêu đề, nhãn trạng thái và nút quay về trên thanh Chat Header"""
        if self.chat_target == "all":
            self.lbl_chat.setText("Phòng Chat Chung")
            self.lbl_target_badge.setText("Công khai")
            self.lbl_target_badge.setStyleSheet(
                "background-color: #e2e8f0; color: #475569; border-radius: 8px; padding: 2px 8px; font-size: 11px; font-weight: 600;"
            )
            self.btn_back_to_public.hide()
            if hasattr(self, "txt_message") and self.txt_message:
                self.txt_message.setPlaceholderText("Nhập tin nhắn...")
        else:
            self.lbl_chat.setText(f"🔒 Chat riêng: {self.chat_target}")
            self.lbl_target_badge.setText("Tin nhắn riêng 1-1")
            self.lbl_target_badge.setStyleSheet(
                "background-color: #dbeafe; color: #1d4ed8; border-radius: 8px; padding: 2px 8px; font-size: 11px; font-weight: 600;"
            )
            self.btn_back_to_public.show()
            if hasattr(self, "txt_message") and self.txt_message:
                self.txt_message.setPlaceholderText(f"Nhắn riêng cho {self.chat_target}...")

    def update_sidebar_active_state(self):
        """Cập nhật viền sáng và màu nền active cho thẻ phòng chung hoặc user đang chọn"""
        # Trạng thái nút phòng chat chung
        if hasattr(self, "row_public_room") and self.row_public_room:
            if self.chat_target == "all":
                self.row_public_room.setStyleSheet("""
                    QFrame#rowPublicRoom {
                        background-color: #e0e7ff;
                        border-radius: 12px;
                        border: 1.5px solid #6366f1;
                    }
                    QFrame#rowPublicRoom:hover {
                        background-color: #dbeafe;
                    }
                """)
            else:
                self.row_public_room.setStyleSheet("""
                    QFrame#rowPublicRoom {
                        background-color: #ffffff;
                        border-radius: 12px;
                        border: 1px solid #e2e8f0;
                    }
                    QFrame#rowPublicRoom:hover {
                        background-color: #f1f5f9;
                    }
                """)

        # Trạng thái từng user row
        if hasattr(self, "sidebar_content_layout"):
            for i in range(self.sidebar_content_layout.count()):
                w = self.sidebar_content_layout.itemAt(i).widget()
                if w:
                    username = w.property("username")
                    if username == self.chat_target:
                        w.setStyleSheet("""
                            QWidget#userRow {
                                background-color: #e0e7ff;
                                border-radius: 10px;
                                border: 1.5px solid #6366f1;
                            }
                            QWidget#userRow:hover {
                                background-color: #dbeafe;
                            }
                        """)
                    else:
                        w.setStyleSheet("""
                            QWidget#userRow {
                                background-color: transparent;
                                border-radius: 10px;
                                border: 1.5px solid transparent;
                            }
                            QWidget#userRow:hover {
                                background-color: #f1f5f9;
                            }
                        """)

    def update_sidebar_badges(self):
        """Cập nhật các huy hiệu số tin nhắn chưa đọc trên Sidebar"""
        # 1. Badge của Phòng Chat Chung
        pub_count = self.unread_counts.get("all", 0)
        if hasattr(self, "badge_public") and self.badge_public:
            if pub_count > 0 and self.chat_target != "all":
                self.badge_public.setText(str(pub_count) if pub_count <= 99 else "99+")
                self.badge_public.show()
            else:
                self.badge_public.hide()

        # 2. Badge của từng người dùng online
        if hasattr(self, "sidebar_content_layout"):
            for i in range(self.sidebar_content_layout.count()):
                w = self.sidebar_content_layout.itemAt(i).widget()
                if w:
                    username = w.property("username")
                    cnt = self.unread_counts.get(username, 0)
                    badge = w.findChild(QLabel, "lblUnreadBadge")
                    if badge:
                        if cnt > 0 and self.chat_target != username:
                            badge.setText(str(cnt) if cnt <= 99 else "99+")
                            badge.show()
                        else:
                            badge.hide()

    def render_current_conversation(self):
        """Vẽ lại toàn bộ tin nhắn thuộc hội thoại hiện tại (Phòng chung hoặc Chat 1-1)"""
        # Xóa các widget tin nhắn hiện tại khỏi layout
        while self.chat_content_layout.count():
            item = self.chat_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        messages = self.conversations.get(self.chat_target, [])
        if not messages:
            if self.chat_target != "all":
                # Hiển thị banner hướng dẫn khi cuộc trò chuyện 1-1 chưa có tin nhắn nào
                banner = QFrame()
                banner.setObjectName("emptyChatBanner")
                banner.setStyleSheet("""
                    QFrame#emptyChatBanner {
                        background-color: #f8fafc;
                        border: 1.5px dashed #cbd5e1;
                        border-radius: 14px;
                        padding: 16px;
                        margin: 20px 24px;
                    }
                """)
                b_layout = QVBoxLayout(banner)
                b_layout.setSpacing(6)
                b_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

                lbl_lock = QLabel("🔒")
                lbl_lock.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_lock.setStyleSheet("font-size: 26px; background: transparent;")

                lbl_t = QLabel(f"Trò chuyện riêng với {self.chat_target}")
                lbl_t.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_t.setStyleSheet("font-size: 14px; font-weight: bold; color: #1e293b; background: transparent;")

                lbl_s = QLabel("Tin nhắn gửi tại đây sẽ chỉ gửi riêng cho người này, không gửi vào phòng chung.")
                lbl_s.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_s.setStyleSheet("font-size: 12px; color: #64748b; background: transparent;")

                b_layout.addWidget(lbl_lock)
                b_layout.addWidget(lbl_t)
                b_layout.addWidget(lbl_s)
                self.chat_content_layout.addWidget(banner)
        else:
            for msg_item in messages:
                self._render_message_widget(msg_item)

        self.scroll_to_bottom()

    def _render_message_widget(self, msg_dict: dict):
        """Tạo đối tượng MessageItem và gắn vào chat_content_layout"""
        sender = msg_dict.get("sender", "")
        message = msg_dict.get("message", "")
        is_self = msg_dict.get("is_self", False)
        msg_id = msg_dict.get("msg_id")
        avatar_path = msg_dict.get("avatar_path")
        reply_to = msg_dict.get("reply_to")

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
            # Xóa stylesheet cục bộ để nhận màu từ style.css
            if hasattr(widget_item, "lbl_msg"):
                widget_item.lbl_msg.setStyleSheet("")
            if hasattr(widget_item, "btn_reply"):
                widget_item.btn_reply.setStyleSheet("")

            # Kết nối tín hiệu nút Trả lời (Reply button ❞) trên bong bóng chat
            if hasattr(widget_item, "reply_requested"):
                widget_item.reply_requested.connect(
                    lambda data, m_id=msg_id: self.start_reply({
                        "msg_id": m_id or data.get("msg_id") or 0,
                        "sender": data.get("sender") or sender,
                        "content": data.get("content") or message,
                    })
                )
        else:
            widget_item = QLabel(f"<b>{sender}</b>: {message}")
            widget_item.setObjectName("fallbackMessage")
            widget_item.setWordWrap(True)

        self.chat_content_layout.addWidget(widget_item)

        if attach_context_menu_to_message:
            ctx_msg_dict = {
                "msg_id": msg_id,
                "sender": sender,
                "content": message,
            }
            attach_context_menu_to_message(
                widget=widget_item,
                message_dict=ctx_msg_dict,
                get_online_users=self.get_online_usernames,
                on_reply=self.start_reply,
                on_forward_confirmed=self.handle_forward_confirmed,
            )
        return widget_item

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
    def add_message_to_chat(self, sender: str, message: str, is_self: bool = False, msg_id=None, avatar_path=None, reply_to=None, target: str = None):
        """Thêm bong bóng tin nhắn Messenger (MessageItem) từ gui_widgets.py vào khung chat (hỗ trợ avatar, reply_to và lưu trữ theo hội thoại)"""
        conv_target = target if target is not None else getattr(self, "chat_target", "all")

        msg_record = {
            "msg_id": msg_id,
            "sender": sender,
            "message": message,
            "is_self": is_self,
            "avatar_path": avatar_path,
            "reply_to": reply_to,
            "target": conv_target,
        }
        self.conversations.setdefault(conv_target, []).append(msg_record)

        # Chỉ vẽ trực tiếp ra giao diện nếu người dùng đang đứng ở đúng hội thoại này
        if conv_target == getattr(self, "chat_target", "all"):
            self._render_message_widget(msg_record)
            self.scroll_to_bottom()

    def add_system_message(self, text: str):
        """Hiển thị thông báo hệ thống"""
        lbl = QLabel(f"📢 {text}")
        lbl.setObjectName("lblSystemMessage")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chat_content_layout.addWidget(lbl)
        
        # Tự động cuộn xuống tin nhắn mới nhất
        self.scroll_to_bottom()

    def send_message(self):
        """Gửi tin nhắn đi (hỗ trợ tin nhắn thường, Reply và định tuyến theo Phòng Chung / Chat Riêng 1-1)"""
        if hasattr(self.txt_message, 'toPlainText'):
            text = self.txt_message.toPlainText().strip()
        else:
            text = self.txt_message.text().strip()

        if not text:
            return

        my_name = self.txt_username.text().strip() or "Gia Bảo"
        my_avatar = getattr(self, "my_avatar", "default_avatar.png")
        reply_info = self.replying_to
        target = getattr(self, "chat_target", "all")

        # Hiển thị tin nhắn của chính mình lên hội thoại hiện tại
        self.add_message_to_chat(
            sender=my_name,
            message=text,
            is_self=True,
            avatar_path=my_avatar,
            reply_to=reply_info,
            target=target
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
                    "receiver": target,
                    "content": text,
                    "reply_to": reply_info,
                    "reply_to_id": reply_info.get("msg_id") or 0,
                    "reply_to_msg_id": reply_info.get("msg_id") or 0,
                }
            else:
                payload = {
                    "type": "msg",
                    "sender": my_name,
                    "receiver": target,
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
        self._clear_sidebar()
        self.lbl_status.setText("Trạng thái: Đã kết nối Server")
        self.lbl_status.setStyleSheet("border: none; color: #40c057; font-weight: bold; font-size: 13px;")
        self.btn_connect.setEnabled(False)
        if hasattr(self, 'btn_leave'):
            self.btn_leave.setEnabled(True)
        self.txt_username.setEnabled(False)
        self.txt_ip.setEnabled(False)
        self.txt_port.setEnabled(False)
        self.update_collapsed_network_text()

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
        if hasattr(self, 'btn_leave'):
            self.btn_leave.setEnabled(False)
        self.txt_username.setEnabled(True)
        self.txt_ip.setEnabled(True)
        self.txt_port.setEnabled(True)
        self.update_collapsed_network_text()

        # Đổi tất cả người dùng sang trạng thái offline khi mất kết nối
        self.lbl_online.setText("Online Users (Đã ngắt kết nối)")
        for i in range(self.sidebar_content_layout.count()):
            w = self.sidebar_content_layout.itemAt(i).widget()
            if w:
                # Tìm chấm trạng thái (dot) và đổi sang màu xám
                for dot in w.findChildren(QLabel):
                    if dot.width() == 12 and dot.height() == 12:
                        dot.setStyleSheet("background-color: #94a3b8; border-radius: 6px; border: 2px solid #ffffff;")

    def on_network_error(self, err_msg):
        """Xử lý khi gặp lỗi mạng"""
        self.lbl_status.setText("Trạng thái: Lỗi kết nối")
        self.lbl_status.setStyleSheet("border: none; color: #fa5252; font-style: italic; font-size: 13px;")
        self.btn_connect.setEnabled(True)
        if hasattr(self, 'btn_leave'):
            self.btn_leave.setEnabled(False)
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
        receiver = data.get("receiver", "all")

        if msg_type == "forward":
            orig_sender = data.get("original_sender", "")
            if orig_sender and orig_sender != sender:
                content = f"↗️ Chuyển tiếp từ {orig_sender}: {content}"

        my_name = self.txt_username.text().strip()
        is_self = (sender == my_name) or (sender == "Bạn")
        
        # Chỉ vẽ nếu tin nhắn không phải từ chính mình gửi lại (tránh bị lặp tin 2 lần)
        if not is_self:
            # Phân loại: Tin nhắn phòng chung hay tin nhắn riêng 1-1
            is_private = bool(receiver and str(receiver).strip().lower() != "all")
            conv_target = sender if is_private else "all"

            self.add_message_to_chat(
                sender=sender,
                message=content,
                is_self=False,
                msg_id=msg_id,
                avatar_path=avatar,
                reply_to=reply_to,
                target=conv_target
            )

            # Nếu tin nhắn đến khi đang ở hội thoại khác -> thông báo và tăng badge chưa đọc
            if is_private and self.chat_target != conv_target:
                self.unread_counts[conv_target] = self.unread_counts.get(conv_target, 0) + 1
                self.update_sidebar_badges()
                self.add_system_message(f"🔒 Tin nhắn riêng mới từ {sender}: {content[:35]}...")
            elif not is_private and self.chat_target != "all":
                self.unread_counts["all"] = self.unread_counts.get("all", 0) + 1
                self.update_sidebar_badges()

    def demo_emoji_click(self):
        """Mở Emoji Picker từ gui_actions.py"""
        if hasattr(self, 'emoji_dialog') and self.emoji_dialog:
            self.emoji_dialog.show()

    # =========================================================================
    # QUẢN LÝ AVATAR CÁ NHÂN & GỬI TỆP TIN / HÌNH ẢNH
    # =========================================================================
    def _resolve_avatar_path(self, avatar_path: str) -> str:
        """Tìm đường dẫn tuyệt đối an toàn cho avatar"""
        default_avatar = os.path.join(current_dir, "assets", "default_avatar.png")
        if not avatar_path:
            return default_avatar
        if os.path.isabs(avatar_path) and os.path.exists(avatar_path):
            return avatar_path
        candidate = os.path.join(current_dir, "assets", os.path.basename(avatar_path))
        if os.path.exists(candidate):
            return candidate
        return default_avatar

    def update_my_avatar_button(self):
        """Cập nhật hình ảnh avatar hiển thị trên nút avatar ở thanh kết nối"""
        if not hasattr(self, 'avatar_btn') or not self.avatar_btn:
            return
        resolved = self._resolve_avatar_path(self.my_avatar)
        pix = QPixmap(resolved) if os.path.exists(resolved) else QPixmap()
        if not pix.isNull():
            rounded = QPixmap(36, 36)
            rounded.fill(Qt.GlobalColor.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addEllipse(0, 0, 36, 36)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, pix.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
            painter.end()
            self.avatar_btn.setIcon(QIcon(rounded))
            self.avatar_btn.setIconSize(QSize(36, 36))
            self.avatar_btn.setText("")
        else:
            self.avatar_btn.setIcon(QIcon())
            self.avatar_btn.setText("👤")

    def open_avatar_chooser(self):
        """Mở hộp thoại chọn hoặc đổi ảnh đại diện cá nhân"""
        dlg = AvatarChooserDialog(current_avatar=self.my_avatar, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.my_avatar = dlg.selected_avatar
            self.update_my_avatar_button()
            self._update_self_row_avatar()
            self.add_system_message(f"Đã cập nhật ảnh đại diện: {os.path.basename(self.my_avatar)}")

    def _update_self_row_avatar(self):
        """Cập nhật lại avatar của dòng chính mình trong sidebar nếu đang hiển thị"""
        my_name = self.txt_username.text().strip() if hasattr(self, 'txt_username') else ""
        if not hasattr(self, "sidebar_content_layout"):
            return
        resolved = self._resolve_avatar_path(self.my_avatar)
        for i in range(self.sidebar_content_layout.count()):
            w = self.sidebar_content_layout.itemAt(i).widget()
            if w:
                username = w.property("username") or ""
                is_self = bool(w.property("is_self")) or (username == my_name) or ("(Bạn)" in username)
                if not is_self:
                    for lbl in w.findChildren(QLabel):
                        if "(Bạn)" in (lbl.text() or ""):
                            is_self = True
                            break
                if is_self:
                    if CircularAvatar:
                        avatar_widget = w.findChild(CircularAvatar)
                        if avatar_widget:
                            avatar_widget.image_path = resolved
                            avatar_widget.update_avatar()

    def choose_and_send_file(self, image_only: bool = False):
        """Mở hộp thoại chọn tệp/hình ảnh từ máy tính và gửi vào cuộc trò chuyện hiện tại"""
        if image_only:
            caption = "Chọn hình ảnh để gửi"
            file_filter = "Hình ảnh (*.png *.jpg *.jpeg *.gif *.bmp);;Tất cả tệp (*.*)"
        else:
            caption = "Chọn tệp hoặc hình ảnh để gửi"
            file_filter = "Tất cả tệp (*.*);;Hình ảnh (*.png *.jpg *.jpeg *.gif *.bmp);;Tài liệu (*.pdf *.docx *.txt *.zip *.rar)"

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            caption,
            "",
            file_filter
        )
        if not file_path:
            return

        file_name = os.path.basename(file_path)
        try:
            size_bytes = os.path.getsize(file_path)
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        except Exception:
            size_str = "N/A"

        ext = os.path.splitext(file_name)[1].lower()
        if ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
            prefix = "🖼️ [Hình ảnh]"
        elif ext in (".pdf", ".doc", ".docx", ".txt", ".xlsx", ".pptx"):
            prefix = "📄 [Tài liệu]"
        elif ext in (".zip", ".rar", ".7z", ".tar", ".gz"):
            prefix = "📦 [Tệp nén]"
        else:
            prefix = "📎 [Tệp đính kèm]"

        file_msg = f"{prefix} {file_name} ({size_str})\n📂 Đường dẫn: {file_path}"

        my_name = self.txt_username.text().strip() or "Gia Bảo"
        my_avatar = getattr(self, "my_avatar", "avatar_user1.png")
        target = getattr(self, "chat_target", "all")
        reply_info = self.replying_to

        # Hiển thị lên giao diện chat của chính mình
        self.add_message_to_chat(
            sender=my_name,
            message=file_msg,
            is_self=True,
            avatar_path=my_avatar,
            reply_to=reply_info,
            target=target
        )

        if reply_info:
            self.cancel_reply()

        # Gửi dữ liệu qua NetworkClient nếu đã kết nối
        if self.network_client and self.network_client.is_running:
            payload = {
                "type": "msg",
                "sender": my_name,
                "receiver": target,
                "content": file_msg,
                "file_info": {
                    "file_name": file_name,
                    "file_size": size_str,
                    "file_path": file_path,
                }
            }
            self.network_client.send_data(payload)

        dest_name = "Phòng Chat Chung" if target == "all" else f"'{target}'"
        self.add_system_message(f"Đã gửi tệp '{file_name}' ({size_str}) tới {dest_name}.")

    def show_plus_menu(self):
        """Hiển thị menu tính năng mở rộng khi bấm nút tròn (+)"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                color: #1e293b;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 4px;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #e0e7ff;
                color: #1d4ed8;
            }
        """)

        act_file = menu.addAction("📎 Đính kèm tệp tin...")
        act_file.triggered.connect(lambda: self.choose_and_send_file(image_only=False))

        act_img = menu.addAction("🖼️ Gửi hình ảnh...")
        act_img.triggered.connect(lambda: self.choose_and_send_file(image_only=True))

        menu.addSeparator()

        act_avatar = menu.addAction("🎭 Đổi ảnh đại diện (Avatar)...")
        act_avatar.triggered.connect(self.open_avatar_chooser)

        act_clear = menu.addAction("🧹 Xóa trắng màn hình chat...")
        act_clear.triggered.connect(self.clear_current_chat)

        btn_pos = self.btn_plus.mapToGlobal(self.btn_plus.rect().topLeft())
        menu.exec(btn_pos)

    def clear_current_chat(self):
        """Xóa trắng màn hình chat hiện tại (làm sạch giao diện)"""
        target_title = "Phòng Chat Chung" if self.chat_target == "all" else self.chat_target
        reply = QMessageBox.question(
            self,
            "Xác nhận xóa màn hình chat",
            f"Bạn có chắc muốn làm sạch màn hình trò chuyện của '{target_title}' không?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.conversations[self.chat_target] = []
            self.render_current_conversation()
            self.add_system_message("Màn hình trò chuyện đã được làm sạch.")

    def demo_mic_click(self):
        """Thông báo tính năng ghi âm thoại"""
        self.add_system_message("🎙️ Tính năng gửi ghi âm thoại (Voice Message) đang được phát triển.")

    def closeEvent(self, event):
        """Dọn dẹp kết nối khi đóng ứng dụng"""
        if hasattr(self, 'network_client') and self.network_client and self.network_client.is_running:
            self.network_client.stop()
        if hasattr(self, 'emoji_dialog') and self.emoji_dialog:
            self.emoji_dialog.close()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Nạp toàn bộ giao diện từ file CSS riêng biệt
    css_content = load_stylesheet("style.css")
    if css_content:
        app.setStyleSheet(css_content)
        
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
