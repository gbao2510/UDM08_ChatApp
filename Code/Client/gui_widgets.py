import sys
import re
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QHBoxLayout, 
    QVBoxLayout, QScrollArea, QSpacerItem, QSizePolicy,
    QTextEdit, QPushButton, QFrame
)
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QColor, QTextDocument, QTextOption
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QEvent, QTimer, QSize

# =========================================================================
# BẢNG MẪU CSS (QSS) CHUẨN ĐỒNG BỘ CHO TOÀN BỘ WIDGETS
# =========================================================================

SCROLLBAR_QSS = """
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: #BCC0C4;
    min-height: 28px;
    border-radius: 3px;
}
QScrollBar::handle:vertical:hover {
    background-color: #8A8D91;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
"""

CHAT_SCROLL_QSS = """
QScrollArea#chatScrollArea {
    background-color: #FFFFFF;
    border: 1px solid #E4E6EB;
    border-radius: 12px;
}
""" + SCROLLBAR_QSS


# =========================================================================
# TIỆN ÍCH XỬ LÝ TỰ ĐỘNG BẺ DÒNG THÔNG MINH CHO TỪ SIÊU DÀI
# =========================================================================

def wrap_unbroken_words(text: str, max_chunk: int = 25) -> str:
    """
    Tự động chèn ký tự ngắt dòng mềm (Zero-Width Space \\u200b) vào các chuỗi 
    ký tự liền nhau không có khoảng trắng vượt quá max_chunk (như cccccc... hoặc URL dài).
    Giúp QLabel/bong bóng chat tự động bẻ dòng xuống dòng mới kể cả khi spam ký tự,
    ngăn chặn triệt để hiện tượng bong bóng bị kéo ngang tràn viền hoặc bị cắt cụt chữ.
    """
    if not text:
        return ""
    return re.sub(r'(\S{' + str(max_chunk) + r'})', lambda m: m.group(1) + '\u200b', str(text))


# =========================================================================
# COMPONENT 1: AVATAR TRÒN CÓ HIỆU ỨNG HOVER
# =========================================================================

class CircularAvatar(QLabel):
    """
    Widget hiển thị avatar cắt tròn với hiệu ứng viền hover mượt mà và tooltip
    """
    def __init__(self, size=36, image_path=None, parent=None):
        super().__init__(parent)
        self.size = size
        self.image_path = image_path
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            CircularAvatar {
                border-radius: %dpx;
                border: 1.5px solid transparent;
            }
            CircularAvatar:hover {
                border: 1.5px solid #0084FF;
            }
        """ % (self.size // 2))
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


# =========================================================================
# COMPONENT 2: NHÃN BONG BÓNG CHAT TỰ ĐỘNG XUỐNG DÒNG (CHATBUBBLELABEL)
# =========================================================================

class ChatBubbleLabel(QLabel):
    """
    QLabel chuyên dụng cho bong bóng chat:
    1. Text ngắn: nằm gọn trên 1 dòng, co theo text, không bị ép xuống 2 dòng vô lý.
    2. Text dài có khoảng trắng: trải dài tối đa max_width rồi tự động xuống dòng mượt mà.
    3. Text dài không có khoảng trắng (như ccccc... hoặc link): tự động bẻ dòng xuống nhiều hàng, không tràn, không cắt chữ.
    """
    def __init__(self, text="", max_width=380, parent=None):
        self.raw_text = text
        self.max_width = max_width
        formatted = wrap_unbroken_words(text, 25)
        super().__init__(formatted, parent)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

    def setText(self, text):
        self.raw_text = text
        super().setText(wrap_unbroken_words(text, 25))

    def text(self) -> str:
        return getattr(self, "raw_text", super().text())

    def sizeHint(self) -> QSize:
        doc = QTextDocument()
        doc.setDefaultFont(self.font())
        doc.setDocumentMargin(0)
        
        opt = QTextOption()
        opt.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        doc.setDefaultTextOption(opt)
        doc.setPlainText(super().text())
        
        doc.setTextWidth(-1)
        ideal_text_w = doc.idealWidth()
        
        # Padding ngang từ stylesheet (padding: 8px 14px -> 28px ngang, 16px dọc)
        pad_w = 28
        pad_h = 16
        max_content_w = self.max_width - pad_w
        
        if ideal_text_w <= max_content_w:
            actual_w = max(16, int(ideal_text_w) + 2)
            doc.setTextWidth(actual_w)
            actual_h = int(doc.size().height())
        else:
            actual_w = max_content_w
            doc.setTextWidth(actual_w)
            actual_h = int(doc.size().height())
            
        return QSize(actual_w + pad_w, actual_h + pad_h)


# =========================================================================
# COMPONENT 3: BONG BÓNG CHAT (MESSAGEITEM)
# =========================================================================

class MessageItem(QWidget):
    """
    Widget đại diện cho 1 bong bóng chat:
    - Tự động xuống dòng chuẩn xác cho mọi tin nhắn (kể cả chuỗi dài ccccc... hoặc link)
    - Hiệu ứng hover nổi bật trên bong bóng chat
    - Nút Reply xuất hiện mượt mà khi hover vào tin nhắn
    - Hộp trích dẫn (Quote Box) bo góc cao cấp
    - Phân biệt tin nhắn bản thân (gradient xanh) và người khác (xám nhạt)
    """
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
        quote_box.setMaximumWidth(380)
        quote_box.setCursor(Qt.CursorShape.PointingHandCursor)

        quote_layout = QVBoxLayout(quote_box)
        quote_layout.setContentsMargins(10, 6, 12, 6)
        quote_layout.setSpacing(2)

        sender_title = f"↩ {reply_sender}" if reply_sender else "↩ Trích dẫn"
        lbl_reply_sender = QLabel(sender_title)
        lbl_reply_sender.setStyleSheet("font-weight: 600; font-size: 11px; color: #0084FF; font-family: 'Segoe UI', sans-serif;")

        # Áp dụng tự ngắt dòng cho nội dung trích dẫn
        lbl_reply_text = QLabel(wrap_unbroken_words(clean_text, 25))
        lbl_reply_text.setWordWrap(True)
        lbl_reply_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl_reply_text.setStyleSheet("color: #65676B; font-size: 12px; font-family: 'Segoe UI', sans-serif;")

        quote_layout.addWidget(lbl_reply_sender)
        quote_layout.addWidget(lbl_reply_text)

        quote_box.setStyleSheet("""
            QFrame#quoteBox {
                background-color: #F0F2F5;
                border: 1px solid #E4E6EB;
                border-left: 3.5px solid #0084FF;
                border-top-left-radius: 4px;
                border-bottom-left-radius: 4px;
                border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;
            }
            QFrame#quoteBox:hover {
                background-color: #E7ECF3;
                border-left: 3.5px solid #0073E6;
            }
            #quoteBox QLabel {
                background: transparent;
                border: none;
            }
        """)

        return quote_box

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 3, 10, 3)
        main_layout.setSpacing(8)

        content_vbox = QVBoxLayout()
        content_vbox.setSpacing(2)

        quote_widget = self.create_quote_widget()

        # Dùng ChatBubbleLabel để tự động xuống dòng chuẩn xác
        self.lbl_msg = ChatBubbleLabel(self.message, max_width=380)
        self.lbl_msg.installEventFilter(self)

        # Nút tròn nhỏ ký hiệu ❞ để reply với hiệu ứng hover mượt mà
        self.btn_reply = QPushButton("❞")
        self.btn_reply.setObjectName("btnReply")
        self.btn_reply.setFixedSize(28, 28)
        self.btn_reply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reply.setToolTip("Trả lời tin nhắn này")
        self.btn_reply.setStyleSheet("""
            QPushButton#btnReply {
                background-color: #FFFFFF;
                border: 1px solid #CED0D4;
                border-radius: 14px;
                color: #65676B;
                font-size: 13px;
                font-weight: bold;
                padding-bottom: 2px;
            }
            QPushButton#btnReply:hover {
                background-color: #E7F3FF;
                border: 1.5px solid #0084FF;
                color: #0084FF;
            }
            QPushButton#btnReply:pressed {
                background-color: #D0E7FF;
                border: 1.5px solid #0066CC;
            }
        """)
        self.btn_reply.clicked.connect(self._on_reply_clicked)
        self.btn_reply.hide()

        bubble_row = QHBoxLayout()
        bubble_row.setContentsMargins(0, 0, 0, 0)
        bubble_row.setSpacing(6)

        if self.is_self:
            # Bong bóng chat của chính mình (gradient xanh Messenger sang trọng)
            self.lbl_msg.setObjectName("bubbleSelf")
            self.lbl_msg.setStyleSheet("""
                QLabel#bubbleSelf {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0084FF, stop:1 #0068E0);
                    color: #FFFFFF;
                    border-radius: 16px;
                    border-bottom-right-radius: 4px;
                    padding: 8px 14px;
                    font-size: 14px;
                    font-family: 'Segoe UI', -apple-system, Roboto, sans-serif;
                }
                QLabel#bubbleSelf:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #108CFF, stop:1 #0072F5);
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
            # Tên người gửi
            lbl_name = QLabel(self.sender_name)
            lbl_name.setObjectName("senderName")
            lbl_name.setStyleSheet("""
                QLabel#senderName {
                    color: #65676B;
                    font-size: 11px;
                    font-weight: 600;
                    margin-left: 6px;
                    margin-bottom: 2px;
                    font-family: 'Segoe UI', sans-serif;
                }
            """)
            content_vbox.addWidget(lbl_name)

            if quote_widget:
                content_vbox.addWidget(quote_widget, alignment=Qt.AlignmentFlag.AlignLeft)

            # Bong bóng chat của đối phương (xám nhạt Messenger hiện đại)
            self.lbl_msg.setObjectName("bubbleOther")
            self.lbl_msg.setStyleSheet("""
                QLabel#bubbleOther {
                    background-color: #E4E6EB;
                    color: #050505;
                    border-radius: 16px;
                    border-bottom-left-radius: 4px;
                    padding: 8px 14px;
                    font-size: 14px;
                    font-family: 'Segoe UI', -apple-system, Roboto, sans-serif;
                }
                QLabel#bubbleOther:hover {
                    background-color: #DADDE1;
                }
            """)
            bubble_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
            bubble_row.addWidget(self.lbl_msg, alignment=Qt.AlignmentFlag.AlignLeft)
            bubble_row.addWidget(self.btn_reply, alignment=Qt.AlignmentFlag.AlignVCenter)
            content_vbox.addLayout(bubble_row)

            avatar = CircularAvatar(size=36, image_path=self.avatar_path)
            avatar.setToolTip(f"Ảnh đại diện của {self.sender_name}")
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


# =========================================================================
# COMPONENT 4: THANH XEM TRƯỚC TRÍCH DẪN (REPLY PREVIEW BAR)
# =========================================================================

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
        self.lbl_title.setStyleSheet("color: #0084FF; font-weight: bold; font-size: 12px; font-family: 'Segoe UI', sans-serif;")

        self.lbl_content = QLabel("")
        self.lbl_content.setStyleSheet("color: #65676B; font-size: 12px; font-family: 'Segoe UI', sans-serif;")
        self.lbl_content.setWordWrap(True)

        text_layout.addWidget(self.lbl_title)
        text_layout.addWidget(self.lbl_content)

        layout.addLayout(text_layout, stretch=1)

        # Nút hủy ✕ bên phải với hiệu ứng hover
        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("btnCloseReply")
        self.btn_close.setFixedSize(26, 26)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setToolTip("Hủy trả lời")
        self.btn_close.setStyleSheet("""
            QPushButton#btnCloseReply {
                background-color: transparent;
                border: none;
                border-radius: 13px;
                color: #65676B;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#btnCloseReply:hover {
                background-color: #E4E6EB;
                color: #FA383E;
            }
            QPushButton#btnCloseReply:pressed {
                background-color: #D8DADF;
            }
        """)
        self.btn_close.clicked.connect(self.clear_reply)
        layout.addWidget(self.btn_close, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.setStyleSheet("""
            QFrame#replyPreviewBar {
                background-color: #F0F4F9;
                border: 1px solid #D0DFEF;
                border-left: 4px solid #0084FF;
                border-top-left-radius: 4px;
                border-bottom-left-radius: 4px;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QFrame#replyPreviewBar:hover {
                background-color: #E8F0FA;
                border-color: #B8D4F0;
                border-left: 4px solid #0073E6;
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
        self.lbl_content.setText(wrap_unbroken_words(clean_content, 25))
        self.show()

    def clear_reply(self):
        """Xóa dữ liệu reply và ẩn thanh xem trước"""
        self.current_reply = None
        self.lbl_title.setText("")
        self.lbl_content.setText("")
        self.hide()


# =========================================================================
# COMPONENT 5: Ô NHẬP TIN NHẮN TỰ CO GIÃN (AUTORESIZINGTEXTEDIT)
# =========================================================================

class AutoResizingTextEdit(QTextEdit):
    """
    Ô nhập văn bản tự động xuống dòng và co giãn chiều cao theo nội dung:
    - Bấm Enter: Gửi tin nhắn.
    - Bấm Shift + Enter: Xuống dòng mới.
    - Tự động mở rộng từ 38px lên tối đa 120px (vượt quá 120px sẽ tự hiện thanh cuộn).
    - Tự động bẻ dòng kể cả khi gặp chuỗi dài liên tục.
    - Hiệu ứng hover và focus viền xanh Messenger tinh tế.
    """
    send_requested = pyqtSignal()

    def __init__(self, parent=None, min_height=38, max_height=120):
        super().__init__(parent)
        self.min_height = min_height
        self.max_height = max_height

        self.setObjectName("inputMessage")
        self.setPlaceholderText("Nhập tin nhắn...")
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFixedHeight(self.min_height)

        # Cấu hình bẻ dòng thông minh trong ô nhập
        opt = QTextOption()
        opt.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.document().setDefaultTextOption(opt)

        self.textChanged.connect(self.adjust_height)

        self.setStyleSheet("""
            QTextEdit#inputMessage {
                background-color: #F0F2F5;
                color: #050505;
                border: 1.5px solid #E4E6EB;
                border-radius: 19px;
                padding: 7px 14px;
                font-size: 14px;
                font-family: 'Segoe UI', -apple-system, Roboto, sans-serif;
            }
            QTextEdit#inputMessage:hover {
                background-color: #F7F8FA;
                border: 1.5px solid #CCD0D5;
            }
            QTextEdit#inputMessage:focus {
                background-color: #FFFFFF;
                border: 1.5px solid #0084FF;
            }
        """ + SCROLLBAR_QSS)

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


# =========================================================================
# COMPONENT 6: KHUNG CUỘN CHAT CHUYÊN DỤNG VỚI TỰ ĐỘNG CUỘN ĐÁY
# =========================================================================

class ChatScrollArea(QScrollArea):
    """
    QScrollArea chuyên dụng cho khung chat:
    - Tự động cuộn xuống đáy khi có tin nhắn mới (rangeChanged & layout reflow)
    - Cung cấp hàm scroll_to_bottom() nhiều nhịp (multi-stage timer) đảm bảo không kẹt cuộn
    - Thanh cuộn mỏng, tinh tế phong cách hiện đại
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chatScrollArea")
        self.setWidgetResizable(True)
        self.setStyleSheet(CHAT_SCROLL_QSS)
        self._auto_scroll = True

        # Tự động cuộn khi khoảng giá trị rangeChanged thay đổi (nội dung dài ra)
        self.verticalScrollBar().rangeChanged.connect(self._on_range_changed)

    def _on_range_changed(self, min_val, max_val):
        if self._auto_scroll:
            self.verticalScrollBar().setValue(max_val)

    def scroll_to_bottom(self, force: bool = True):
        """
        Cuộn tức thì và đảm bảo bằng multi-stage QTimer
        để đối phó với hiện tượng layout trễ khi render bóng chat mới.
        """
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())
        # Nhịp 1: ngay sau khi event loop xử lý layout xong
        QTimer.singleShot(0, lambda: bar.setValue(bar.maximum()))
        # Nhịp 2: sau 30ms khi font metrics và word wrap hoàn tất
        QTimer.singleShot(30, lambda: bar.setValue(bar.maximum()))
        # Nhịp 3: dự phòng bảo đảm 100% chạm đáy
        QTimer.singleShot(80, lambda: bar.setValue(bar.maximum()))


# =========================================================================
# SIGNAL BRIDGE
# =========================================================================

class MessageSignalBridge(QObject):
    """Signal phát dictionary gói tin JSON nhận được từ Server/NetworkClient"""
    message_received = pyqtSignal(dict)


# =========================================================================
# KHỐI TEST CHẠY THỬ ĐỘC LẬP (PREVIEW GIAO DIỆN)
# =========================================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = QWidget()
    window.setObjectName("mainChatWindow")
    window.setWindowTitle("Messenger Widget Demo - UDM08 Chat App")
    window.resize(520, 680)
    window.setStyleSheet("""
        QWidget#mainChatWindow {
            background-color: #F0F2F5;
            font-family: 'Segoe UI', -apple-system, Roboto, sans-serif;
        }
    """)

    outer_layout = QVBoxLayout(window)
    outer_layout.setContentsMargins(12, 12, 12, 12)
    outer_layout.setSpacing(10)

    # Header Bar mô phỏng sang trọng
    header_bar = QFrame()
    header_bar.setObjectName("chatHeaderBar")
    header_bar.setStyleSheet("""
        QFrame#chatHeaderBar {
            background-color: #FFFFFF;
            border: 1px solid #E4E6EB;
            border-radius: 10px;
        }
    """)
    header_layout = QHBoxLayout(header_bar)
    header_layout.setContentsMargins(14, 10, 14, 10)
    header_layout.setSpacing(10)

    # Chấm xanh trạng thái trực tuyến
    lbl_status_dot = QLabel("●")
    lbl_status_dot.setStyleSheet("color: #31A24C; font-size: 15px; margin-right: -4px;")
    lbl_app_title = QLabel("Phòng Chat Nhóm")
    lbl_app_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #050505;")
    lbl_subtitle = QLabel("• Đang hoạt động")
    lbl_subtitle.setStyleSheet("font-size: 12px; color: #31A24C; font-weight: 500;")

    header_layout.addWidget(lbl_status_dot)
    header_layout.addWidget(lbl_app_title)
    header_layout.addWidget(lbl_subtitle)
    header_layout.addStretch()

    outer_layout.addWidget(header_bar)

    # Vùng hiển thị tin nhắn (sử dụng ChatScrollArea tự cuộn xuống đáy)
    scroll = ChatScrollArea()
    scroll_content = QWidget()
    scroll_content.setStyleSheet("background: transparent;")
    chat_list_layout = QVBoxLayout(scroll_content)
    chat_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    chat_list_layout.setContentsMargins(8, 10, 8, 10)
    chat_list_layout.setSpacing(8)

    scroll.setWidget(scroll_content)
    outer_layout.addWidget(scroll, stretch=1)

    # Thanh xem trước khi reply (nằm ngay phía trên khung nhập liệu)
    reply_bar = ReplyPreviewBar()

    # XỬ LÝ KHI NGƯỜI DÙNG BẤM NÚT REPLY Ở BẤT KỲ MESSAGEITEM
    def handle_reply_requested(reply_dict: dict):
        reply_bar.set_reply_target(reply_dict)
        input_text.setFocus()

    # HÀM TỰ ADD MESSAGEITEM KHI NHẬN DICT TỪ SIGNAL VÀ TỰ CUỘN XUỐNG ĐÁY
    def add_message_item(data: dict):
        """
        Nhận gói tin JSON chuẩn, thêm MessageItem và tự động cuộn xuống đáy.
        """
        sender = data.get("sender", "Ẩn danh")
        text = data.get("content") or data.get("text") or data.get("message") or ""
        reply_to = data.get("reply_to")
        avatar_path = data.get("avatar_path") or data.get("avatar")
        
        # Tự động xác định tin của bản thân
        is_self = (sender == "Tôi") or data.get("is_self", False)

        item = MessageItem(
            sender_name=sender, 
            message=text, 
            is_self=is_self, 
            avatar_path=avatar_path,
            reply_to=reply_to
        )
        item.reply_requested.connect(handle_reply_requested)
        chat_list_layout.addWidget(item)

        # Kích hoạt tự cuộn xuống đáy ngay lập tức
        scroll.scroll_to_bottom(force=True)

    # Khởi tạo Signal và nối sự kiện với hàm add_message_item
    msg_bridge = MessageSignalBridge()
    msg_bridge.message_received.connect(add_message_item)

    # Bơm Mock data chuẩn theo đúng cấu trúc gói tin
    mock_messages = [
        {"type": "chat", "sender": "Ngô Gia Bảo", "content": "Tiến độ hoàn thành như nào rồi các bạn?"},
        {"type": "chat", "sender": "Tôi", "content": "Tớ vừa hoàn thiện component MessageItem với hiệu ứng hover và auto-scroll xịn sò!"},
        {"type": "chat", "sender": "Lý Huỳnh Bích Trâm", "content": "Socket client tuần này gửi nhận chuỗi JSON cơ bản mượt mà rồi nhé."},
        {"type": "chat", "sender": "Tôi", "content": "Thử nghiệm tin nhắn dài tự động xuống dòng và co giãn chiều cao xem bong bóng chat có hoạt động chuẩn không nào."},
        {"type": "chat", "sender": "Ngô Gia Bảo", "content": "Tuyệt vời, test thử tính năng trích dẫn phản hồi nhé!", "reply_to": {"sender": "Tôi", "content": "Tớ vừa hoàn thiện component MessageItem với hiệu ứng hover và auto-scroll xịn sò!"}},
        {"type": "chat", "sender": "Tôi", "content": "Đã thêm ô trích dẫn phía trên bong bóng chat chuẩn theo UI Messenger và có hiệu ứng hover cực đẹp!", "reply_to": {"sender": "Ngô Gia Bảo", "content": "Tuyệt vời, test thử tính năng trích dẫn phản hồi nhé!"}},
    ]

    for data in mock_messages:
        msg_bridge.message_received.emit(data)

    # Đặt thanh xem trước trích dẫn ngay phía trên khung nhập liệu
    outer_layout.addWidget(reply_bar)

    # Khung nhập liệu ở đáy
    input_box = QFrame()
    input_box.setObjectName("inputBoxFrame")
    input_box.setStyleSheet("""
        QFrame#inputBoxFrame {
            background-color: #FFFFFF;
            border: 1px solid #E4E6EB;
            border-radius: 24px;
            padding: 4px;
        }
    """)
    input_container = QHBoxLayout(input_box)
    input_container.setContentsMargins(6, 4, 6, 4)
    input_container.setSpacing(8)

    input_text = AutoResizingTextEdit(min_height=38, max_height=120)

    btn_send = QPushButton("Gửi")
    btn_send.setObjectName("btnSend")
    btn_send.setFixedSize(65, 38)
    btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_send.setStyleSheet("""
        QPushButton#btnSend {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0084FF, stop:1 #0073E6);
            color: #FFFFFF;
            font-weight: 600;
            border-radius: 19px;
            font-size: 14px;
            border: none;
        }
        QPushButton#btnSend:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1A8DFF, stop:1 #0080FF);
        }
        QPushButton#btnSend:pressed {
            background: #005BB5;
            padding-top: 2px;
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
        
        # Phát Signal add_message_item tự động bắt, add vào ScrollArea và tự cuộn xuống đáy
        msg_bridge.message_received.emit(packet)
        input_text.clear()
        input_text.setFixedHeight(input_text.min_height)
        scroll.scroll_to_bottom(force=True)

    btn_send.clicked.connect(send_message)
    input_text.send_requested.connect(send_message)

    input_container.addWidget(input_text, stretch=1)
    input_container.addWidget(btn_send, alignment=Qt.AlignmentFlag.AlignBottom)

    outer_layout.addWidget(input_box)

    # Cuộn xuống đáy sau khi nạp xong dữ liệu khởi tạo
    QTimer.singleShot(100, lambda: scroll.scroll_to_bottom(force=True))

    window.show()
    sys.exit(app.exec())
