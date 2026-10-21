import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QHBoxLayout, 
    QVBoxLayout, QScrollArea, QSpacerItem, QSizePolicy
)
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QColor
from PyQt6.QtCore import Qt

class CircularAvatar(QLabel):
    "Widget hiển thị avatar cắt tròn"
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

class MessageItem(QWidget):
    "Widget đại diện cho 1 bong bóng chat"
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

# Khối chạy thử nghiệm độc lập với Mock Data
if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("Test widget messageitem")
    window.resize(480, 550)

    outer_layout = QVBoxLayout(window)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll_content = QWidget()
    chat_list_layout = QVBoxLayout(scroll_content)
    chat_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    mock_messages = [
        {"sender": "Ngô Gia Bảo", "text": "Tiến độ hoàn thành như nào rồi.", "is_self": False},
        {"sender": "Tôi", "text": "T đang hoàn thiện component MessageItem hiển thị độc lập.", "is_self": True},
        {"sender": "Lý Huỳnh Bích Trâm", "text": "Socket client tuần này gửi nhận chuỗi JSON cơ bản được rồi.", "is_self": False},
        {"sender": "Tôi", "text": "Thử nghiệm tin nhắn dài tự động xuống dòng và co giãn chiều cao xem bong bóng chat có hoạt động chuẩn không.", "is_self": True},
    ]

    for data in mock_messages:
        item = MessageItem(
            sender_name=data["sender"], 
            message=data["text"], 
            is_self=data["is_self"]
        )
        chat_list_layout.addWidget(item)

    scroll.setWidget(scroll_content)
    outer_layout.addWidget(scroll)

    window.show()
    sys.exit(app.exec())