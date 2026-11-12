import os
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QDialog, QGridLayout, QPushButton,
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QAction, QGuiApplication

# Đảm bảo hiển thị chuẩn tiếng Việt và Emoji trên Console Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# =========================================================================
# 1. QUẢN LÝ THƯ MỤC TÀI NGUYÊN (ASSETS HELPER) - NGÔ GIA BẢO (TV6)
# =========================================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(CURRENT_DIR, "assets")

def get_asset_path(filename: str) -> str:
    """
    Trả về đường dẫn tuyệt đối an toàn tới tệp tin trong thư mục assets.
    Nếu tệp tin không tồn tại, trả về chuỗi rỗng.
    """
    full_path = os.path.join(ASSETS_DIR, filename)
    return full_path if os.path.exists(full_path) else ""

def get_asset_icon(filename: str) -> QIcon:
    """
    Tải đối tượng QIcon từ thư mục assets để gắn vào Button, Window,...
    """
    path = get_asset_path(filename)
    return QIcon(path) if path else QIcon()

def get_asset_pixmap(filename: str, width: int = 0, height: int = 0) -> QPixmap:
    """
    Tải đối tượng QPixmap từ thư mục assets và tùy chọn scale kích thước.
    """
    path = get_asset_path(filename)
    if not path:
        return QPixmap()
    pix = QPixmap(path)
    if width > 0 and height > 0 and not pix.isNull():
        return pix.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    return pix


# =========================================================================
# 2. COMPONENT: DIALOG EMOJI PICKER (TUẦN 1 - NGÔ GIA BẢO)
# =========================================================================
class EmojiPickerDialog(QWidget):
    """
    Hộp thoại (Dialog) chọn Emoji.
    Chức năng chính:
    1. Chọn Emoji -> In ra Console / Terminal theo đúng yêu cầu đề bài.
    2. Phát Signal 'emoji_selected' để UI bên ngoài (gui_main.py) bắt sự kiện.
    3. Tự động chèn Emoji vào con trỏ của khung nhập liệu (QLineEdit, QTextEdit, AutoResizingTextEdit).
    """
    # Signal phát ra mã Emoji được người dùng chọn
    emoji_selected = pyqtSignal(str)

    def __init__(self, parent_input_field=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chọn Emoji")
        self.resize(320, 240)
        self.setWindowFlags(Qt.WindowType.Tool)  # Hiển thị dạng popup nổi trên ứng dụng chính

        # Gán icon cửa sổ từ thư mục assets
        icon_path = get_asset_path("emoji_icon.png") or get_asset_path("app_icon.png")
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

        self.parent_input_field = parent_input_field

        # Danh sách mã Emoji cơ bản & phổ biến (Unicode chuẩn)
        self.emoji_list = [
            "😀", "😂", "🥰", "😎", "🤔", "🙄",
            "😭", "😡", "👍", "👎", "👋", "🎉",
            "🔥", "❤️", "💔", "💯", "✅", "❌",
            "✨", "🤝", "🚀", "💪", "💡", "☕"
        ]

        self.init_ui()

    def init_ui(self):
        # Bố cục giao diện Dark Theme đồng bộ với toàn bộ Chat App
        self.setStyleSheet("""
            QWidget {
                background-color: #242526;
                color: #e4e6eb;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)

        # Thanh tiêu đề (Header bar) kèm nút đóng nhanh ✕
        header_layout = QHBoxLayout()
        title = QLabel("😊 Chọn biểu tượng cảm xúc")
        title.setStyleSheet("font-weight: bold; font-size: 13px; color: #f2f3f5;")
        header_layout.addWidget(title)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #b0b3b8;
                font-weight: bold;
                border: none;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: #3a3b3c;
                color: #ffffff;
            }
        """)
        btn_close.clicked.connect(self.hide)
        header_layout.addWidget(btn_close)

        layout.addLayout(header_layout)

        # Lưới Emoji (Grid Layout: 6 cột x 4 hàng)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(6)

        row, col = 0, 0
        max_cols = 6  # 6 emoji trên mỗi hàng

        for emoji in self.emoji_list:
            btn = QPushButton(emoji)
            btn.setFixedSize(42, 42)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(f"Chọn {emoji}")
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 20px;
                    background-color: #3a3b3c;
                    border: 1px solid #4e4f50;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: #0084ff;
                    border: 1px solid #0084ff;
                }
                QPushButton:pressed {
                    background-color: #0066cc;
                }
            """)

            # Gắn sự kiện click
            btn.clicked.connect(lambda checked, e=emoji: self.on_emoji_clicked(e))
            grid_layout.addWidget(btn, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        layout.addLayout(grid_layout)

    def on_emoji_clicked(self, selected_emoji):
        """
        Xử lý khi người dùng click vào một Emoji:
        1. In ra Terminal / Console (Yêu cầu đề bài Tuần 1).
        2. Phát Signal PyQt để các widget khác có thể lắng nghe.
        3. Tự động chèn Emoji vào khung nhập liệu (QLineEdit, QTextEdit, AutoResizingTextEdit).
        4. Ẩn dialog sau khi đã chọn.
        """
        # 1. Yêu cầu chính: In ra terminal/console khi click chọn Emoji
        print(f"[TEST EMOJI] Bạn vừa chọn: {selected_emoji}")

        # 2. Phát Signal
        self.emoji_selected.emit(selected_emoji)

        # 3. Chèn Emoji vào con trỏ của ô nhập liệu (nếu có)
        if self.parent_input_field:
            if hasattr(self.parent_input_field, "insertPlainText"):
                # Hỗ trợ QTextEdit / AutoResizingTextEdit (chèn tại vị trí con trỏ)
                self.parent_input_field.insertPlainText(selected_emoji)
                self.parent_input_field.setFocus()
            elif hasattr(self.parent_input_field, "insert"):
                # Hỗ trợ QLineEdit (chèn tại vị trí con trỏ)
                self.parent_input_field.insert(selected_emoji)
                self.parent_input_field.setFocus()
            elif hasattr(self.parent_input_field, "text") and hasattr(self.parent_input_field, "setText"):
                current_text = self.parent_input_field.text()
                self.parent_input_field.setText(current_text + selected_emoji)

        # 4. Đóng popup
        self.hide()


# =========================================================================
# 3. COMPONENT: HỘP THOẠI CHỌN NGƯỜI ĐỂ FORWARD (NGÔ GIA BẢO - BẢNG PHÂN CÔNG)
# =========================================================================
class ForwardDialog(QDialog):
    """
    Hộp thoại (Dialog) chọn người dùng để chuyển tiếp (Forward) tin nhắn.
    Theo phân công tổng quan: "Hộp thoại chọn người để Forward".
    Tuần 4: Pop-up danh sách người dùng để Forward khi click chuột phải vào bong bóng chat.
    """
    # Signal phát ra khi người dùng xác nhận chuyển tiếp: (người_nhận, nội_dung)
    forward_confirmed = pyqtSignal(str, str)

    def __init__(self, message_content: str, online_users: list = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chuyển tiếp tin nhắn (Forward)")
        self.resize(380, 460)
        self.message_content = message_content
        self.online_users = online_users or ["all", "Trần Thuận Trí", "Trương Gia Bân", "Lý Huỳnh Bích Trâm", "Nguyễn Gia Bảo", "Trần Trung Trực"]

        # Gán icon cửa sổ
        icon_path = get_asset_path("app_icon.png")
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

        self.init_ui()

    def _extract_username(self, user_item) -> str:
        """Hỗ trợ trích xuất tên người dùng dù đầu vào là chuỗi string hay dictionary {username, avatar}"""
        if isinstance(user_item, dict):
            return user_item.get("username", "Unknown")
        return str(user_item).strip()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #242526;
                color: #e4e6eb;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Tiêu đề
        lbl_title = QLabel("↗️ Chuyển tiếp tin nhắn tới:")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #f2f3f5;")
        layout.addWidget(lbl_title)

        # Xem trước nội dung tin nhắn sẽ forward
        preview_box = QLabel(f"💬 \"{self.message_content}\"")
        preview_box.setWordWrap(True)
        preview_box.setStyleSheet("""
            QLabel {
                background-color: #3a3b3c;
                color: #e4e6eb;
                border-left: 3px solid #0084ff;
                padding: 8px 12px;
                border-radius: 4px;
                font-style: italic;
                font-size: 13px;
            }
        """)
        layout.addWidget(preview_box)

        # Ô tìm kiếm người nhận (Search filter)
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Tìm người nhận hoặc phòng...")
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background-color: #18191a;
                color: #ffffff;
                border: 1px solid #3e3e42;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #0084ff;
            }
        """)
        self.txt_search.textChanged.connect(self.filter_users)
        layout.addWidget(self.txt_search)

        # Danh sách người nhận
        lbl_list = QLabel("Chọn người nhận:")
        lbl_list.setStyleSheet("font-size: 12px; color: #b0b3b8; font-weight: bold;")
        layout.addWidget(lbl_list)

        self.user_list_widget = QListWidget()
        self.user_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #18191a;
                border: 1px solid #3e3e42;
                border-radius: 6px;
                padding: 4px;
                color: #f2f3f5;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #0084ff;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #3a3b3c;
            }
        """)

        layout.addWidget(self.user_list_widget)

        # Nạp dữ liệu danh sách người dùng
        self.populate_user_list()

        # Nút xác nhận & hủy
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Hủy")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #3a3b3c;
                color: #e4e6eb;
                padding: 8px 16px;
                border-radius: 6px;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4e4f50;
            }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_send = QPushButton("Chuyển tiếp")
        btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_send.setStyleSheet("""
            QPushButton {
                background-color: #0084ff;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 6px;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0073e6;
            }
        """)
        btn_send.clicked.connect(self.on_confirm_forward)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_send)
        layout.addLayout(btn_layout)

    def populate_user_list(self):
        """Nạp danh sách người nhận vào QListWidget"""
        self.user_list_widget.clear()

        # Mục mặc định: Phòng chung (all)
        item_all = QListWidgetItem("🌐 Tất cả mọi người (Phòng chung - all)")
        item_all.setData(Qt.ItemDataRole.UserRole, "all")
        self.user_list_widget.addItem(item_all)

        for u in self.online_users:
            uname = self._extract_username(u)
            if uname and uname != "all":
                item = QListWidgetItem(f"👤 {uname}")
                item.setData(Qt.ItemDataRole.UserRole, uname)
                self.user_list_widget.addItem(item)

        if self.user_list_widget.count() > 0:
            self.user_list_widget.setCurrentRow(0)

    def set_online_users(self, new_users: list):
        """Cập nhật danh sách người dùng online động"""
        self.online_users = new_users or []
        self.populate_user_list()

    def filter_users(self, query: str):
        """Lọc danh sách người dùng theo từ khóa tìm kiếm"""
        query = query.strip().lower()
        for i in range(self.user_list_widget.count()):
            item = self.user_list_widget.item(i)
            text = item.text().lower()
            item.setHidden(query not in text and query != "")

    def on_confirm_forward(self):
        current_item = self.user_list_widget.currentItem()
        if current_item:
            receiver = current_item.data(Qt.ItemDataRole.UserRole)
            print(f"[FORWARD] Chuyển tiếp tin nhắn '{self.message_content}' tới: {receiver}")
            self.forward_confirmed.emit(receiver, self.message_content)
        self.accept()


# =========================================================================
# 4. COMPONENT: MENU CHUỘT PHẢI CONTEXT MENU (TUẦN 4 - NGÔ GIA BẢO)
# =========================================================================
def create_message_context_menu(parent_widget, message_dict: dict,
                                on_reply=None, on_forward=None, on_copy=None,
                                online_users: list = None,
                                on_forward_confirmed=None) -> QMenu:
    """
    Tạo Context Menu chuẩn khi click chuột phải vào 1 bong bóng chat (MessageItem).
    Nhiệm vụ Tuần 4 (Ngô Gia Bảo):
    - 💬 Trả lời (Reply)
    - ↗️ Chuyển tiếp (Forward) -> Pop-up danh sách người dùng để Forward (ForwardDialog)
    - 📋 Sao chép văn bản (Copy)
    """
    menu = QMenu(parent_widget)
    menu.setStyleSheet("""
        QMenu {
            background-color: #242526;
            color: #e4e6eb;
            border: 1px solid #3e3e42;
            border-radius: 8px;
            padding: 4px;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 13px;
        }
        QMenu::item {
            padding: 7px 24px;
            border-radius: 4px;
        }
        QMenu::item:selected {
            background-color: #0084ff;
            color: #ffffff;
        }
        QMenu::separator {
            height: 1px;
            background-color: #3e3e42;
            margin: 4px 8px;
        }
    """)

    content = message_dict.get("content") or message_dict.get("text", "")
    sender = message_dict.get("sender", "Unknown")

    # Action 1: Trả lời (Reply)
    act_reply = QAction("💬 Trả lời tin nhắn này", menu)
    if on_reply:
        act_reply.triggered.connect(lambda: on_reply(message_dict))
    menu.addAction(act_reply)

    # Action 2: Chuyển tiếp (Forward) - TUẦN 4: POP-UP DANH SÁCH NGƯỜI DÙNG ĐỂ FORWARD
    act_forward = QAction("↗️ Chuyển tiếp (Forward)...", menu)

    def trigger_forward_popup():
        if on_forward:
            on_forward(message_dict)
        else:
            # Mặc định: Pop-up ForwardDialog với danh sách người dùng online
            users = online_users() if callable(online_users) else online_users
            dialog = ForwardDialog(
                message_content=content,
                online_users=users,
                parent=parent_widget
            )
            if on_forward_confirmed:
                dialog.forward_confirmed.connect(on_forward_confirmed)
            dialog.exec()

    act_forward.triggered.connect(trigger_forward_popup)
    menu.addAction(act_forward)

    menu.addSeparator()

    # Action 3: Sao chép (Copy)
    act_copy = QAction("📋 Sao chép nội dung", menu)

    def copy_text():
        clipboard = QGuiApplication.clipboard()
        if clipboard and content:
            clipboard.setText(content)
            print(f"[CONTEXT MENU] Đã copy vào Clipboard: {content}")
        if on_copy:
            on_copy(content)

    act_copy.triggered.connect(copy_text)
    menu.addAction(act_copy)

    return menu


def attach_context_menu_to_message(widget: QWidget, message_dict: dict,
                                   get_online_users=None,
                                   on_reply=None,
                                   on_forward=None,
                                   on_forward_confirmed=None,
                                   on_copy=None):
    """
    Hàm tiện ích chính Tuần 4 của Ngô Gia Bảo:
    Gắn Context Menu chuột phải trực tiếp vào bong bóng chat (MessageItem hoặc widget tin nhắn).
    Khi click chuột phải vào widget hoặc các phần tử bên trong:
    - Bật Context Menu tại vị trí chuột.
    - Chọn 'Chuyển tiếp': Tự động Pop-up danh sách người dùng để Forward.
    - Chọn 'Trả lời': Kích hoạt callback on_reply.
    - Chọn 'Sao chép': Tự động chép văn bản vào Clipboard.
    """
    widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def show_context_menu(point):
        users = get_online_users() if callable(get_online_users) else get_online_users
        menu = create_message_context_menu(
            parent_widget=widget,
            message_dict=message_dict,
            on_reply=on_reply,
            on_forward=on_forward,
            on_copy=on_copy,
            online_users=users,
            on_forward_confirmed=on_forward_confirmed
        )
        menu.exec(widget.mapToGlobal(point))

    widget.customContextMenuRequested.connect(show_context_menu)

    # Đảm bảo các widget con (như QLabel chứa nội dung) cũng kích hoạt Context Menu này
    for child in widget.findChildren(QLabel):
        child.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        child.customContextMenuRequested.connect(
            lambda p, c=child: show_context_menu(c.mapTo(widget, p))
        )


# =========================================================================
# KHU VỰC TEST CHẠY ĐỘC LẬP (DEMO TỔNG HỢP TUẦN 4 - NGÔ GIA BẢO)
# =========================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Cửa sổ demo giả lập
    test_window = QWidget()
    test_window.setWindowTitle("Test Module gui_actions.py (Tuần 4) - Ngô Gia Bảo (TV6)")
    test_window.resize(520, 480)
    test_window.setStyleSheet("background-color: #18191a; color: #f2f3f5;")

    # Gán icon từ thư mục assets
    app_icon = get_asset_icon("app_icon.png")
    if not app_icon.isNull():
        test_window.setWindowIcon(app_icon)

    test_layout = QVBoxLayout(test_window)
    test_layout.setContentsMargins(16, 16, 16, 16)
    test_layout.setSpacing(10)

    # Tiêu đề hướng dẫn Tuần 4
    header_box = QLabel("📋 TUẦN 4: GẮN CONTEXT MENU CHUỘT PHẢI & POP-UP FORWARD")
    header_box.setStyleSheet("font-size: 14px; font-weight: bold; color: #0084ff; padding-bottom: 2px;")
    test_layout.addWidget(header_box)

    guide_lbl = QLabel("👉 Hãy CLICK CHUỘT PHẢI vào bất kỳ bong bóng chat bên dưới để mở Context Menu:")
    guide_lbl.setStyleSheet("color: #e4e6eb; font-size: 12px; font-style: italic;")
    test_layout.addWidget(guide_lbl)

    # Danh sách người online mẫu
    mock_online_users = ["all", "Trần Thuận Trí", "Trương Gia Bân", "Lý Huỳnh Bích Trâm", "Nguyễn Gia Bảo", "Trần Trung Trực"]

    # Khung giả lập bong bóng chat để test chuột phải
    chat_box = QWidget()
    chat_box.setStyleSheet("background-color: #242526; border-radius: 8px; padding: 8px;")
    chat_box_layout = QVBoxLayout(chat_box)
    chat_box_layout.setSpacing(10)

    # Bong bóng 1: Tin nhắn từ bạn bè
    bubble_friend = QWidget()
    bubble_friend.setStyleSheet("background-color: #3a3b3c; border-radius: 12px; padding: 10px;")
    bf_layout = QVBoxLayout(bubble_friend)
    bf_layout.setContentsMargins(10, 8, 10, 8)
    lbl_friend_name = QLabel("Trần Thuận Trí")
    lbl_friend_name.setStyleSheet("color: #4dabf7; font-weight: bold; font-size: 12px;")
    lbl_friend_msg = QLabel("Anh em ơi, tiến độ hoàn thành Tuần 4 (Reply & Forward) đến đâu rồi?")
    lbl_friend_msg.setWordWrap(True)
    lbl_friend_msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    lbl_friend_msg.setStyleSheet("color: #ffffff; font-size: 13px;")
    bf_layout.addWidget(lbl_friend_name)
    bf_layout.addWidget(lbl_friend_msg)

    # Bong bóng 2: Tin nhắn của mình
    bubble_me = QWidget()
    bubble_me.setStyleSheet("background-color: #0084ff; border-radius: 12px; padding: 10px;")
    bm_layout = QVBoxLayout(bubble_me)
    bm_layout.setContentsMargins(10, 8, 10, 8)
    lbl_me_name = QLabel("Ngô Gia Bảo (Bạn)")
    lbl_me_name.setStyleSheet("color: #d0ebff; font-weight: bold; font-size: 12px;")
    lbl_me_msg = QLabel("Tôi đã hoàn thành gắn Context Menu chuột phải: Pop-up danh sách người dùng để Forward rồi nhé!")
    lbl_me_msg.setWordWrap(True)
    lbl_me_msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    lbl_me_msg.setStyleSheet("color: #ffffff; font-size: 13px;")
    bm_layout.addWidget(lbl_me_name)
    bm_layout.addWidget(lbl_me_msg)

    chat_box_layout.addWidget(bubble_friend)
    chat_box_layout.addWidget(bubble_me)
    test_layout.addWidget(chat_box)

    # Nhãn trạng thái hiển thị log trực tiếp trên giao diện
    lbl_status = QLabel("Console Log: Chưa có thao tác nào. Click chuột phải vào bong bóng chat để thử!")
    lbl_status.setStyleSheet("color: #38d9a9; font-size: 12px; font-weight: bold; padding: 4px;")
    lbl_status.setWordWrap(True)

    # GẮN CONTEXT MENU CHUỘT PHẢI VÀO CẢ 2 BONG BÓNG CHAT QUA HÀM TIỆN ÍCH TUẦN 4
    dict_msg_friend = {
        "sender": "Trần Thuận Trí",
        "content": "Anh em ơi, tiến độ hoàn thành Tuần 4 (Reply & Forward) đến đâu rồi?"
    }
    dict_msg_me = {
        "sender": "Ngô Gia Bảo",
        "content": "Tôi đã hoàn thành gắn Context Menu chuột phải: Pop-up danh sách người dùng để Forward rồi nhé!"
    }

    def on_reply_demo(msg):
        lbl_status.setText(f"Console Log: [REPLY] Đang chuẩn bị trả lời tin nhắn: \"{msg.get('content')}\"")

    def on_forward_demo(receiver, content):
        lbl_status.setText(f"Console Log: [FORWARD SUCCESS] Đã chuyển tiếp tới '{receiver}': \"{content}\"")

    def on_copy_demo(txt):
        lbl_status.setText(f"Console Log: [COPY SUCCESS] Đã sao chép vào bộ nhớ tạm: \"{txt}\"")

    attach_context_menu_to_message(
        widget=bubble_friend,
        message_dict=dict_msg_friend,
        get_online_users=lambda: mock_online_users,
        on_reply=on_reply_demo,
        on_forward_confirmed=on_forward_demo,
        on_copy=on_copy_demo
    )

    attach_context_menu_to_message(
        widget=bubble_me,
        message_dict=dict_msg_me,
        get_online_users=lambda: mock_online_users,
        on_reply=on_reply_demo,
        on_forward_confirmed=on_forward_demo,
        on_copy=on_copy_demo
    )

    # Khung nhập liệu & nút tính năng Tuần 1 / Tuần 3
    test_layout.addWidget(QLabel("--- Hoặc thử các tính năng độc lập (Emoji Picker & Ô nhập liệu) ---"))

    txt_input = QLineEdit()
    txt_input.setPlaceholderText("Gõ tin nhắn hoặc click nút chọn Emoji bên dưới...")
    txt_input.setStyleSheet("""
        QLineEdit {
            background-color: #242526;
            color: #ffffff;
            border: 1px solid #3e3e42;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 13px;
        }
        QLineEdit:focus {
            border: 1px solid #0084ff;
        }
    """)
    test_layout.addWidget(txt_input)

    btn_row = QHBoxLayout()

    # Nút 1: Mở Emoji Picker
    btn_show_emoji = QPushButton(" 😊 Mở Emoji Picker")
    emoji_icon = get_asset_icon("emoji_icon.png")
    if not emoji_icon.isNull():
        btn_show_emoji.setIcon(emoji_icon)
        btn_show_emoji.setIconSize(QSize(18, 18))
    btn_show_emoji.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_show_emoji.setStyleSheet("""
        QPushButton {
            font-size: 13px;
            font-weight: bold;
            padding: 8px 14px;
            background-color: #0084ff;
            color: white;
            border-radius: 6px;
            border: none;
        }
        QPushButton:hover {
            background-color: #0073e6;
        }
    """)

    # Nút 2: Mở Forward Dialog trực tiếp
    btn_forward = QPushButton("↗️ Pop-up Forward riêng")
    btn_forward.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_forward.setStyleSheet("""
        QPushButton {
            font-size: 13px;
            font-weight: bold;
            padding: 8px 14px;
            background-color: #3a3b3c;
            color: white;
            border-radius: 6px;
            border: none;
        }
        QPushButton:hover {
            background-color: #4e4f50;
        }
    """)

    btn_row.addWidget(btn_show_emoji)
    btn_row.addWidget(btn_forward)
    test_layout.addLayout(btn_row)

    test_layout.addWidget(lbl_status)

    # Khởi tạo EmojiPickerDialog và kết nối sự kiện
    emoji_dialog = EmojiPickerDialog(parent_input_field=txt_input)
    btn_show_emoji.clicked.connect(emoji_dialog.show)
    emoji_dialog.emoji_selected.connect(lambda e: lbl_status.setText(f"Console Log: [TEST EMOJI] Bạn vừa chọn: {e}"))

    # Khởi tạo ForwardDialog demo trực tiếp
    def open_forward_demo():
        msg_text = txt_input.text().strip() or "Nội dung tin nhắn mẫu cần chuyển tiếp"
        dialog = ForwardDialog(message_content=msg_text, online_users=mock_online_users, parent=test_window)
        dialog.forward_confirmed.connect(lambda rec, txt: lbl_status.setText(f"Console Log: [FORWARD SUCCESS] Chuyển tiếp tới '{rec}': \"{txt}\""))
        dialog.exec()

    btn_forward.clicked.connect(open_forward_demo)

    test_window.show()
    sys.exit(app.exec())
