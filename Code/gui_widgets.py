import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QHBoxLayout, 
    QVBoxLayout, QScrollArea, QSpacerItem, QSizePolicy,
    QTextEdit, QPushButton
)
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QColor
from PyQt6.QtCore import Qt, pyqtSignal, QObject

# COMPONENT 1: AVATAR TRÒN 

class CircularAvatar(QLabel):
    """Widget hiển thị avatar cắt tròn"""
    def __init__(self, size=36, image_path=None, parent=None):
        super().__init__(parent)
        self.size = size
        self.setFixedSize(size, size)
        self.image_path = image_path
        self.update_avatar()

    def update_avatar(self):
        pixmap = QPixmap(self.image_path) if self.image_path else QPixmap(self.size, self.size)
        if not self.image_path or pixmap.isNull():
            pixmap.fill(QColor("#B0BEC5"))

        scaled_pixmap = pixmap.scaled(
            self.size, self.size, 
            Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
            Qt.TransformationMode.SmoothTransformation
        )

        rounded = QPixmap(self.size, self.size)
        rounded.fill(Qt.GlobalColor.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, self.size, self.size)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, scaled_pixmap)
        painter.end()

        self.setPixmap(rounded)

#COMPONENT 2: BONG BÓNG CHAT 

class MessageItem(QWidget):
    """Widget đại diện cho 1 bong bóng chat"""
    def __init__(self, sender_name: str, message: str, is_self: bool = False, avatar_path: str = None, parent=None):
        super().__init__(parent)
        self.is_self = is_self
        self.sender_name = sender_name
        self.message = message
        self.avatar_path = avatar_path
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 4, 10, 4)
        main_layout.setSpacing(8)

        content_vbox = QVBoxLayout()
        content_vbox.setSpacing(2)

        lbl_msg = QLabel(self.message)
        lbl_msg.setWordWrap(True)
        lbl_msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl_msg.setMaximumWidth(400)

        if self.is_self:
            lbl_msg.setStyleSheet("""
                QLabel {
                    background-color: #0084FF;
                    color: white;
                    border-radius: 14px;
                    padding: 8px 12px;
                    font-size: 14px;
                }
            """)
            content_vbox.addWidget(lbl_msg, alignment=Qt.AlignmentFlag.AlignRight)
            main_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
            main_layout.addLayout(content_vbox)
        else:
            lbl_name = QLabel(self.sender_name)
            lbl_name.setStyleSheet("color: #757575; font-size: 11px; font-weight: bold; margin-left: 4px;")
            content_vbox.addWidget(lbl_name)

            lbl_msg.setStyleSheet("""
                QLabel {
                    background-color: #E4E6EB;
                    color: #050505;
                    border-radius: 14px;
                    padding: 8px 12px;
                    font-size: 14px;
                }
            """)
            content_vbox.addWidget(lbl_msg, alignment=Qt.AlignmentFlag.AlignLeft)

            avatar = CircularAvatar(size=36, image_path=self.avatar_path)
            main_layout.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignBottom)
            main_layout.addLayout(content_vbox)
            main_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

# COMPONENT 3: Ô NHẬP TIN NHẮN TỰ CO GIÃN

class AutoResizingTextEdit(QTextEdit):
    """
    Ô nhập văn bản tự động xuống dòng và co giãn chiều cao theo nội dung:
    - Bấm Enter: Gửi tin nhắn.
    - Bấm Shift + Enter: Xuống dòng mới.
    - Tự động mở rộng từ 38px lên tối đa 120px (vượt quá 120px sẽ tự hiện thanh cuộn).
    """
    send_requested = pyqtSignal()

    def __init__(self, parent=None, min_height=38, max_height=120):
        super().__init__(parent)
        self.min_height = min_height
        self.max_height = max_height

        self.setPlaceholderText("Nhập tin nhắn...")
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFixedHeight(self.min_height)
        self.textChanged.connect(self.adjust_height)

        self.setStyleSheet("""
            QTextEdit {
                background-color: #F0F2F5;
                color: #050505;
                border: 1px solid #E4E6EB;
                border-radius: 19px;
                padding: 6px 14px;
                font-size: 14px;
            }
            QTextEdit:focus {
                background-color: #FFFFFF;
                border: 1px solid #0084FF;
            }
        """)

    def adjust_height(self):
        doc_height = int(self.document().size().height()) + 12
        new_height = max(self.min_height, min(doc_height, self.max_height))
        self.setFixedHeight(new_height)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.send_requested.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

# SIGNAL BRIDGE
class MessageSignalBridge(QObject):
    """Signal phát dictionary gói tin JSON nhận được từ Server/NetworkClient"""
    message_received = pyqtSignal(dict)

# KHỐI TEST CHẠY THỬ ĐỘC LẬP

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("Test widget messageitem")
    window.resize(500, 620)

    outer_layout = QVBoxLayout(window)
    outer_layout.setContentsMargins(8, 8, 8, 8)
    outer_layout.setSpacing(8)

    # Vùng hiển thị tin nhắn (ScrollArea)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
    scroll_content = QWidget()
    chat_list_layout = QVBoxLayout(scroll_content)
    chat_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    # HÀM TỰ ADD MESSAGEITEM KHI NHẬN DICT TỪ SIGNAL
    def add_message_item(data: dict):
        """
        Nhận gói tin JSON chuẩn (từ Signal của Trâm hoặc Mock data),
        tự động bóc tách dữ liệu và thêm MessageItem vào ScrollArea.
        """
        sender = data.get("sender", "Ẩn danh")
        text = data.get("content") or data.get("text") or data.get("message") or ""
        
        #Tự động xác định tin của bản thân
        is_self = (sender == "Tôi") or data.get("is_self", False)

        item = MessageItem(sender_name=sender, message=text, is_self=is_self)
        chat_list_layout.addWidget(item)
        QApplication.processEvents()
        scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())

    # Khởi tạo Signal và nối sự kiện với hàm add_message_item
    msg_bridge = MessageSignalBridge()
    msg_bridge.message_received.connect(add_message_item)

    # Bơm Mock data chuẩn theo đúng cấu trúc gói tin của Bân
    mock_messages = [
        {"type": "chat", "sender": "Ngô Gia Bảo", "content": "Tiến độ hoàn thành như nào rồi."},
        {"type": "chat", "sender": "Tôi", "content": "T đang hoàn thiện component MessageItem hiển thị độc lập."},
        {"type": "chat", "sender": "Lý Huỳnh Bích Trâm", "content": "Socket client tuần này gửi nhận chuỗi JSON cơ bản được rồi."},
        {"type": "chat", "sender": "Tôi", "content": "Thử nghiệm tin nhắn dài tự động xuống dòng và co giãn chiều cao xem bong bóng chat có hoạt động chuẩn không."},
    ]

    for data in mock_messages:
        msg_bridge.message_received.emit(data)

    scroll.setWidget(scroll_content)
    outer_layout.addWidget(scroll)

    # Khung nhập liệu ở đáy
    input_container = QHBoxLayout()
    input_container.setSpacing(8)
    input_text = AutoResizingTextEdit(min_height=38, max_height=120)

    btn_send = QPushButton("Send")
    btn_send.setFixedSize(56, 38)
    btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_send.setStyleSheet("""
        QPushButton {
            background-color: #0084FF;
            color: white;
            font-weight: bold;
            border-radius: 19px;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #0073E6;
        }
        QPushButton:pressed {
            background-color: #005BB5;
        }
    """)

    def send_message():
        text = input_text.toPlainText().strip()
        if not text:
            return
        
        #Đóng gói đúng format JSON: type, sender, content
        packet = {
            "type": "chat",
            "sender": "Tôi",
            "content": text
        }
        
        # Phát Signal add_message_item tự động bắt và add vào ScrollArea
        msg_bridge.message_received.emit(packet)
        input_text.clear()
        input_text.setFixedHeight(input_text.min_height)

    btn_send.clicked.connect(send_message)
    input_text.send_requested.connect(send_message)

    input_container.addWidget(input_text)
    input_container.addWidget(btn_send, alignment=Qt.AlignmentFlag.AlignBottom)

    outer_layout.addLayout(input_container)

    window.show()
    sys.exit(app.exec())