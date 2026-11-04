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
    """
    # Signal phát ra khi người dùng xác nhận chuyển tiếp: (người_nhận, nội_dung)
    forward_confirmed = pyqtSignal(str, str)

    def __init__(self, message_content: str, online_users: list = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chuyển tiếp tin nhắn (Forward)")
        self.resize(360, 420)
        self.message_content = message_content
        self.online_users = online_users or ["all", "Thuận Trí", "Gia Bân", "Bích Trâm", "Trung Trực"]

        # Gán icon cửa sổ
        icon_path = get_asset_path("app_icon.png")
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

        self.init_ui()

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
        layout.setSpacing(12)

        # Tiêu đề
        lbl_title = QLabel("↗️ Chuyển tiếp tin nhắn tới:")
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #f2f3f5;")
        layout.addWidget(lbl_title)

        # Xem trước nội dung tin nhắn sẽ forward
        preview_box = QLabel(f"💬 \"{self.message_content}\"")
        preview_box.setWordWrap(True)
        preview_box.setStyleSheet("""
            QLabel {
                background-color: #3a3b3c;
                color: #b0b3b8;
                border-left: 3px solid #0084ff;
                padding: 8px 12px;
                border-radius: 4px;
                font-style: italic;
            }
        """)
        layout.addWidget(preview_box)

        # Danh sách người nhận
        lbl_list = QLabel("Chọn người nhận hoặc kênh:")
        lbl_list.setStyleSheet("font-size: 12px; color: #b0b3b8;")
        layout.addWidget(lbl_list)

        self.user_list_widget = QListWidget()
        self.user_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #18191a;
                border: 1px solid #3e3e42;
                border-radius: 6px;
                padding: 4px;
                color: #f2f3f5;
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

        # Nạp các người nhận
        item_all = QListWidgetItem("🌐 Tất cả mọi người (Phòng chung - all)")
        item_all.setData(Qt.ItemDataRole.UserRole, "all")
        self.user_list_widget.addItem(item_all)

        for u in self.online_users:
            if u != "all":
                item = QListWidgetItem(f"👤 {u}")
                item.setData(Qt.ItemDataRole.UserRole, u)
                self.user_list_widget.addItem(item)

        self.user_list_widget.setCurrentRow(0)
        layout.addWidget(self.user_list_widget)

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

    def on_confirm_forward(self):
        current_item = self.user_list_widget.currentItem()
        if current_item:
            receiver = current_item.data(Qt.ItemDataRole.UserRole)
            print(f"[FORWARD] Chuyển tiếp tin nhắn '{self.message_content}' tới: {receiver}")
            self.forward_confirmed.emit(receiver, self.message_content)
        self.accept()


# =========================================================================
# 4. COMPONENT: MENU CHUỘT PHẢI CONTEXT MENU (NGÔ GIA BẢO - BẢNG PHÂN CÔNG)
# =========================================================================
def create_message_context_menu(parent_widget, message_dict: dict,
                                on_reply=None, on_forward=None, on_copy=None) -> QMenu:
    """
    Tạo Context Menu chuẩn khi click chuột phải vào 1 bong bóng chat (MessageItem).
    Bao gồm các chức năng:
    - 💬 Trả lời (Reply)
    - ↗️ Chuyển tiếp (Forward)
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
        }
        QMenu::item {
            padding: 6px 20px;
            border-radius: 4px;
        }
        QMenu::item:selected {
            background-color: #0084ff;
            color: #ffffff;
        }
    """)

    content = message_dict.get("content") or message_dict.get("text", "")
    sender = message_dict.get("sender", "Unknown")

    # Action 1: Trả lời (Reply)
    act_reply = QAction("💬 Trả lời tin nhắn này", menu)
    if on_reply:
        act_reply.triggered.connect(lambda: on_reply(message_dict))
    menu.addAction(act_reply)

    # Action 2: Chuyển tiếp (Forward)
    act_forward = QAction("↗️ Chuyển tiếp (Forward)...", menu)
    if on_forward:
        act_forward.triggered.connect(lambda: on_forward(message_dict))
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


# =========================================================================
# KHU VỰC TEST CHẠY ĐỘC LẬP (DEMO TỔNG HỢP - NGÔ GIA BẢO)
# =========================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Cửa sổ demo giả lập
    test_window = QWidget()
    test_window.setWindowTitle("Test Module gui_actions.py - Ngô Gia Bảo (TV6)")
    test_window.resize(460, 220)
    test_window.setStyleSheet("background-color: #18191a; color: #f2f3f5;")

    # Gán icon từ thư mục assets
    app_icon = get_asset_icon("app_icon.png")
    if not app_icon.isNull():
        test_window.setWindowIcon(app_icon)

    test_layout = QVBoxLayout(test_window)
    test_layout.setContentsMargins(16, 16, 16, 16)
    test_layout.setSpacing(10)

    # Ô nhập văn bản
    txt_input = QLineEdit()
    txt_input.setPlaceholderText("Emoji chọn sẽ tự động chèn vào đây...")
    txt_input.setStyleSheet("""
        QLineEdit {
            background-color: #242526;
            color: #ffffff;
            border: 1px solid #3e3e42;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 14px;
        }
        QLineEdit:focus {
            border: 1px solid #0084ff;
        }
    """)

    btn_row = QHBoxLayout()

    # Nút 1: Mở Emoji Picker
    btn_show_emoji = QPushButton(" Mở Emoji Picker")
    emoji_icon = get_asset_icon("emoji_icon.png")
    if not emoji_icon.isNull():
        btn_show_emoji.setIcon(emoji_icon)
        btn_show_emoji.setIconSize(QSize(20, 20))
    btn_show_emoji.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_show_emoji.setStyleSheet("""
        QPushButton {
            font-size: 13px;
            font-weight: bold;
            padding: 8px 12px;
            background-color: #0084ff;
            color: white;
            border-radius: 6px;
            border: none;
        }
        QPushButton:hover {
            background-color: #0073e6;
        }
    """)

    # Nút 2: Mở Forward Dialog
    btn_forward = QPushButton("↗️ Thử Forward")
    btn_forward.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_forward.setStyleSheet("""
        QPushButton {
            font-size: 13px;
            font-weight: bold;
            padding: 8px 12px;
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

    # Nhãn trạng thái hiển thị log trực tiếp trên giao diện
    lbl_status = QLabel("Console Log: Hãy click mở Emoji hoặc Forward để xem log in ra terminal")
    lbl_status.setStyleSheet("color: #b0b3b8; font-size: 12px; font-style: italic;")

    test_layout.addWidget(txt_input)
    test_layout.addLayout(btn_row)
    test_layout.addWidget(lbl_status)

    # Khởi tạo EmojiPickerDialog và kết nối sự kiện
    emoji_dialog = EmojiPickerDialog(parent_input_field=txt_input)
    btn_show_emoji.clicked.connect(emoji_dialog.show)
    emoji_dialog.emoji_selected.connect(lambda e: lbl_status.setText(f"Console Log: [TEST EMOJI] Bạn vừa chọn: {e}"))

    # Khởi tạo ForwardDialog demo
    def open_forward_demo():
        msg_text = txt_input.text().strip() or "Nội dung tin nhắn mẫu cần chuyển tiếp"
        dialog = ForwardDialog(message_content=msg_text, parent=test_window)
        dialog.forward_confirmed.connect(lambda rec, txt: lbl_status.setText(f"Console Log: [FORWARD] Chuyển tiếp tới '{rec}'"))
        dialog.exec()

    btn_forward.clicked.connect(open_forward_demo)

    test_window.show()
    sys.exit(app.exec())
