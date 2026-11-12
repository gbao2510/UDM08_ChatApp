import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QHBoxLayout, 
    QVBoxLayout, QScrollArea, QSpacerItem, QSizePolicy,
    QTextEdit, QPushButton, QFrame
)
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QColor
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QEvent, QTimer

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
    reply_requested = pyqtSignal(dict)

    def __init__(self, sender_name: str, message: str, is_self: bool = False, avatar_path: str = None, reply_to=None, parent=None):
        if isinstance(reply_to, QWidget) and parent is None:
            parent = reply_to
            reply_to = None
        super().__init__(parent)
        self.is_self = is_self
        self.sender_name = sender_name
        self.message = message
        self.avatar_path = avatar_path
        self.reply_to = reply_to
        self.btn_reply = None
        self.lbl_msg = None
        self.init_ui()

    def create_quote_widget(self):
        """Tạo widget ô trích dẫn phía trên bong bóng chat khi có reply_to"""
        if not self.reply_to:
            return None

        if isinstance(self.reply_to, dict):
            reply_sender = self.reply_to.get("sender", "")
            reply_text = self.reply_to.get("content") or self.reply_to.get("text") or self.reply_to.get("message") or ""
        else:
            reply_sender = ""
            reply_text = str(self.reply_to)

        if not reply_sender and not reply_text:
            return None

        clean_text = " ".join(reply_text.split())
        if len(clean_text) > 100:
            clean_text = clean_text[:97] + "..."

        quote_box = QFrame()
        quote_box.setObjectName("quoteBox")
        quote_box.setMaximumWidth(400)

        quote_layout = QVBoxLayout(quote_box)
        quote_layout.setContentsMargins(10, 6, 12, 6)
        quote_layout.setSpacing(2)

        sender_title = f"↩ {reply_sender}" if reply_sender else "↩ Trích dẫn"
        lbl_reply_sender = QLabel(sender_title)
        lbl_reply_sender.setStyleSheet("font-weight: bold; font-size: 11px; color: #0084FF;")

        lbl_reply_text = QLabel(clean_text)
        lbl_reply_text.setWordWrap(True)
        lbl_reply_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl_reply_text.setStyleSheet("color: #65676B; font-size: 12px;")

        quote_layout.addWidget(lbl_reply_sender)
        quote_layout.addWidget(lbl_reply_text)

        quote_box.setStyleSheet("""
            QFrame#quoteBox {
                background-color: #F0F2F5;
                border: none;
                border-left: 3px solid #0084FF;
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            #quoteBox QLabel {
                background: transparent;
                border: none;
            }
        """)

        return quote_box

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 4, 10, 4)
        main_layout.setSpacing(8)

        content_vbox = QVBoxLayout()
        content_vbox.setSpacing(2)

        quote_widget = self.create_quote_widget()

        self.lbl_msg = QLabel(self.message)
        self.lbl_msg.setWordWrap(True)
        self.lbl_msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_msg.setMaximumWidth(400)
        self.lbl_msg.installEventFilter(self)

        # Nút tròn nhỏ ký hiệu ❞ để reply
        self.btn_reply = QPushButton("❞")
        self.btn_reply.setFixedSize(28, 28)
        self.btn_reply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reply.setToolTip("Trả lời tin nhắn này")
        self.btn_reply.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #D8DADF;
                border-radius: 14px;
                color: #65676B;
                font-size: 13px;
                font-weight: bold;
                padding-bottom: 2px;
            }
            QPushButton:hover {
                background-color: #E7F3FF;
                border: 1px solid #0084FF;
                color: #0084FF;
            }
            QPushButton:pressed {
                background-color: #D0E7FF;
            }
        """)
        self.btn_reply.clicked.connect(self._on_reply_clicked)
        self.btn_reply.hide()

        bubble_row = QHBoxLayout()
        bubble_row.setContentsMargins(0, 0, 0, 0)
        bubble_row.setSpacing(6)

        if self.is_self:
            self.lbl_msg.setStyleSheet("""
                QLabel {
                    background-color: #0084FF;
                    color: white;
                    border-radius: 14px;
                    padding: 8px 12px;
                    font-size: 14px;
                }
            """)
            if quote_widget:
                content_vbox.addWidget(quote_widget, alignment=Qt.AlignmentFlag.AlignRight)

            bubble_row.setAlignment(Qt.AlignmentFlag.AlignRight)
            bubble_row.addWidget(self.btn_reply, alignment=Qt.AlignmentFlag.AlignVCenter)
            bubble_row.addWidget(self.lbl_msg, alignment=Qt.AlignmentFlag.AlignRight)
            content_vbox.addLayout(bubble_row)

            main_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
            main_layout.addLayout(content_vbox)
        else:
            lbl_name = QLabel(self.sender_name)
            lbl_name.setStyleSheet("color: #757575; font-size: 11px; font-weight: bold; margin-left: 4px;")
            content_vbox.addWidget(lbl_name)

            if quote_widget:
                content_vbox.addWidget(quote_widget, alignment=Qt.AlignmentFlag.AlignLeft)

            self.lbl_msg.setStyleSheet("""
                QLabel {
                    background-color: #E4E6EB;
                    color: #050505;
                    border-radius: 14px;
                    padding: 8px 12px;
                    font-size: 14px;
                }
            """)
            bubble_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
            bubble_row.addWidget(self.lbl_msg, alignment=Qt.AlignmentFlag.AlignLeft)
            bubble_row.addWidget(self.btn_reply, alignment=Qt.AlignmentFlag.AlignVCenter)
            content_vbox.addLayout(bubble_row)

            avatar = CircularAvatar(size=36, image_path=self.avatar_path)
            main_layout.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignBottom)
            main_layout.addLayout(content_vbox)
            main_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

    def _on_reply_clicked(self):
        self.reply_requested.emit({
            "sender": self.sender_name,
            "content": self.message
        })

    def enterEvent(self, event):
        if self.btn_reply:
            self.btn_reply.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.btn_reply:
            self.btn_reply.hide()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.btn_reply:
            self.btn_reply.show()
        super().mousePressEvent(event)

    def eventFilter(self, watched, event):
        if watched == self.lbl_msg and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton and self.btn_reply:
                self.btn_reply.show()
        return super().eventFilter(watched, event)

# COMPONENT 3: THANH XEM TRƯỚC TRÍCH DẪN (REPLY PREVIEW BAR)

class ReplyPreviewBar(QFrame):
    """
    Thanh xem trước tin nhắn đang được trích dẫn (Reply Preview Bar),
    đặt ngay phía trên khung nhập liệu (AutoResizingTextEdit), mặc định ẩn (hide()).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_reply = None
        self.init_ui()
        self.hide()

    def init_ui(self):
        self.setObjectName("replyPreviewBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 8, 6)
        layout.setSpacing(8)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self.lbl_title = QLabel("↩ Đang trả lời")
        self.lbl_title.setStyleSheet("color: #0084FF; font-weight: bold; font-size: 12px;")

        self.lbl_content = QLabel("")
        self.lbl_content.setStyleSheet("color: #65676B; font-size: 12px;")
        self.lbl_content.setWordWrap(True)

        text_layout.addWidget(self.lbl_title)
        text_layout.addWidget(self.lbl_content)

        layout.addLayout(text_layout, stretch=1)

        # Nút hủy ✕ bên phải
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(26, 26)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setToolTip("Hủy trả lời")
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 13px;
                color: #65676B;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E4E6EB;
                color: #050505;
            }
            QPushButton:pressed {
                background-color: #D8DADF;
            }
        """)
        self.btn_close.clicked.connect(self.clear_reply)
        layout.addWidget(self.btn_close, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.setStyleSheet("""
            QFrame#replyPreviewBar {
                background-color: #F0F2F5;
                border: 1px solid #E4E6EB;
                border-left: 3px solid #0084FF;
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            #replyPreviewBar QLabel {
                background: transparent;
                border: none;
            }
        """)

    def set_reply_target(self, reply_data: dict):
        """Gán dữ liệu tin nhắn cần reply và hiển thị thanh xem trước"""
        if not reply_data:
            self.clear_reply()
            return
        self.current_reply = reply_data
        sender = reply_data.get("sender", "Ẩn danh")
        raw_content = reply_data.get("content") or reply_data.get("text") or reply_data.get("message") or ""
        clean_content = " ".join(raw_content.split())
        if len(clean_content) > 75:
            clean_content = clean_content[:72] + "..."
        self.lbl_title.setText(f"↩ Đang trả lời {sender}")
        self.lbl_content.setText(clean_content)
        self.show()

    def clear_reply(self):
        """Xóa dữ liệu reply và ẩn thanh xem trước"""
        self.current_reply = None
        self.lbl_title.setText("")
        self.lbl_content.setText("")
        self.hide()

# COMPONENT 4: Ô NHẬP TIN NHẮN TỰ CO GIÃN

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

    scroll.setWidget(scroll_content)
    outer_layout.addWidget(scroll)

    # Tự động cuộn xuống dưới cùng khi danh sách tin nhắn mở rộng
    def scroll_to_bottom():
        scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())

    scroll.verticalScrollBar().rangeChanged.connect(lambda min_val, max_val: scroll.verticalScrollBar().setValue(max_val))

    # Thanh xem trước khi reply (nằm ngay phía trên khung nhập liệu)
    reply_bar = ReplyPreviewBar()

    # XỬ LÝ KHI NGƯỜI DÙNG BẤM NÚT REPLY Ở BẤT KỲ MESSAGEITEM
    def handle_reply_requested(reply_dict: dict):
        reply_bar.set_reply_target(reply_dict)
        input_text.setFocus()

    # HÀM TỰ ADD MESSAGEITEM KHI NHẬN DICT TỪ SIGNAL
    def add_message_item(data: dict):
        """
        Nhận gói tin JSON chuẩn (từ Signal của Trâm hoặc Mock data),
        tự động bóc tách dữ liệu và thêm MessageItem vào ScrollArea.
        """
        sender = data.get("sender", "Ẩn danh")
        text = data.get("content") or data.get("text") or data.get("message") or ""
        reply_to = data.get("reply_to")
        
        #Tự động xác định tin của bản thân
        is_self = (sender == "Tôi") or data.get("is_self", False)

        item = MessageItem(sender_name=sender, message=text, is_self=is_self, reply_to=reply_to)
        item.reply_requested.connect(handle_reply_requested)
        chat_list_layout.addWidget(item)
        QTimer.singleShot(10, scroll_to_bottom)

    # Khởi tạo Signal và nối sự kiện với hàm add_message_item
    msg_bridge = MessageSignalBridge()
    msg_bridge.message_received.connect(add_message_item)

    # Bơm Mock data chuẩn theo đúng cấu trúc gói tin của Bân
    mock_messages = [
        {"type": "chat", "sender": "Ngô Gia Bảo", "content": "Tiến độ hoàn thành như nào rồi."},
        {"type": "chat", "sender": "Tôi", "content": "T đang hoàn thiện component MessageItem hiển thị độc lập."},
        {"type": "chat", "sender": "Lý Huỳnh Bích Trâm", "content": "Socket client tuần này gửi nhận chuỗi JSON cơ bản được rồi."},
        {"type": "chat", "sender": "Tôi", "content": "Thử nghiệm tin nhắn dài tự động xuống dòng và co giãn chiều cao xem bong bóng chat có hoạt động chuẩn không."},
        {"type": "chat", "sender": "Ngô Gia Bảo", "content": "Tuyệt vời, test thử tính năng trích dẫn phản hồi nhé!", "reply_to": {"sender": "Tôi", "content": "T đang hoàn thiện component MessageItem hiển thị độc lập."}},
        {"type": "chat", "sender": "Tôi", "content": "Đã thêm ô trích dẫn phía trên bong bóng chat chuẩn theo UI Messenger rồi nhé.", "reply_to": {"sender": "Ngô Gia Bảo", "content": "Tuyệt vời, test thử tính năng trích dẫn phản hồi nhé!"}},
    ]

    for data in mock_messages:
        msg_bridge.message_received.emit(data)

    # Đặt thanh xem trước trích dẫn ngay phía trên khung nhập liệu
    outer_layout.addWidget(reply_bar)

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
        
        # Đóng gói đúng format JSON: type, sender, content, (reply_to nếu có)
        packet = {
            "type": "chat",
            "sender": "Tôi",
            "content": text
        }
        if reply_bar.current_reply:
            packet["reply_to"] = reply_bar.current_reply
            reply_bar.clear_reply()
        
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