
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QFrame, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chat Application - Team Client (Demo Tuần 1)")
        self.resize(850, 600)
        self.setMinimumSize(700, 500)

        # Cài đặt giao diện & Mock data
        self.setup_ui()
        self.load_mock_data()

    def setup_ui(self):
        # Widget trung tâm
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # 1. KHU VỰC CẤU HÌNH MẠNG (TOP BAR)
        network_box = QFrame()
        network_box.setStyleSheet("""
            QFrame {
                background-color: #f1f3f5;
                border: 1px solid #ced4da;
                border-radius: 8px;
            }
        """)
        network_layout = QHBoxLayout(network_box)
        network_layout.setContentsMargins(12, 8, 12, 8)

        lbl_ip = QLabel("Server IP:")
        lbl_ip.setStyleSheet("border: none; font-weight: bold;")
        self.txt_ip = QLineEdit("127.0.0.1")
        self.txt_ip.setPlaceholderText("VD: 192.168.1.10")
        self.txt_ip.setFixedWidth(140)

        lbl_port = QLabel("Port:")
        lbl_port.setStyleSheet("border: none; font-weight: bold;")
        self.txt_port = QLineEdit("8080")
        self.txt_port.setPlaceholderText("Port")
        self.txt_port.setFixedWidth(70)

        self.btn_connect = QPushButton("Kết nối")
        self.btn_connect.setStyleSheet("""
            QPushButton {
                background-color: #228be6;
                color: white;
                font-weight: bold;
                padding: 6px 14px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1c7ed6;
            }
        """)
        self.btn_connect.clicked.connect(self.demo_connect_action)

        self.lbl_status = QLabel("Trạng thái: Chưa kết nối (Chế độ Demo)")
        self.lbl_status.setStyleSheet("border: none; color: #868e96; font-style: italic;")

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
        body_layout.setSpacing(10)

        # 2.1 Sidebar: Danh sách bạn bè / Online Users
        sidebar_layout = QVBoxLayout()
        lbl_online = QLabel("Online Users (Mock)")
        lbl_online.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.list_users = QListWidget()
        self.list_users.setFixedWidth(200)
        self.list_users.setStyleSheet("""
            QListWidget {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background-color: #ffffff;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f1f3f5;
            }
            QListWidget::item:selected {
                background-color: #e7f5ff;
                color: #1971c2;
            }
        """)
        sidebar_layout.addWidget(lbl_online)
        sidebar_layout.addWidget(self.list_users)
        body_layout.addLayout(sidebar_layout)

        # 2.2 Chat Area: Khung hiển thị tin nhắn
        chat_layout = QVBoxLayout()
        lbl_chat = QLabel("Phòng Chat Chung")
        lbl_chat.setFont(QFont("Arial", 10, QFont.Weight.Bold))

        self.list_messages = QListWidget()
        self.list_messages.setStyleSheet("""
            QListWidget {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background-color: #f8f9fa;
                padding: 6px;
            }
            QListWidget::item {
                margin: 4px 0px;
                padding: 8px 12px;
                border-radius: 6px;
                background-color: white;
                border: 1px solid #e9ecef;
            }
        """)
        chat_layout.addWidget(lbl_chat)
        chat_layout.addWidget(self.list_messages)
        body_layout.addLayout(chat_layout, stretch=1)

        main_layout.addLayout(body_layout, stretch=1)

        # 3. KHU VỰC NHẬP TIN NHẮN (BOTTOM BAR)
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)

        # Nút Emoji (placeholder để kết nối gui_actions.py tuần sau)
        self.btn_emoji = QPushButton("😊")
        self.btn_emoji.setFixedSize(36, 36)
        self.btn_emoji.setToolTip("Chọn Emoji (sẽ kết nối gui_actions.py)")
        self.btn_emoji.clicked.connect(self.demo_emoji_click)

        # Ô nhập tin nhắn
        self.txt_message = QLineEdit()
        self.txt_message.setPlaceholderText("Nhập tin nhắn... (Nhấn Enter để gửi)")
        self.txt_message.setFixedHeight(36)
        self.txt_message.returnPressed.connect(self.send_message)

        # Nút gửi
        self.btn_send = QPushButton("Gửi")
        self.btn_send.setFixedHeight(36)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #2b8a3e;
                color: white;
                font-weight: bold;
                padding: 0 18px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #237032;
            }
        """)
        self.btn_send.clicked.connect(self.send_message)

        bottom_layout.addWidget(self.btn_emoji)
        bottom_layout.addWidget(self.txt_message, stretch=1)
        bottom_layout.addWidget(self.btn_send)

        main_layout.addLayout(bottom_layout)

    def load_mock_data(self):
        """Nạp dữ liệu giả lập (Mock Data) """
        # 1. Mock Online Users
        mock_users = [
            "🟢 Trần Thuận Trí (Server)",
            "🟢 Trương Gia Bân",
            "🟢 Lý Huỳnh Bích Trâm",
            "🟢 Nguyễn Gia Bảo ",
            "🟢 Trần Trung Trực",
            "⚪ Ngô Gia Bảo (Offline)"
        ]
        for user in mock_users:
            self.list_users.addItem(QListWidgetItem(user))

        # 2. Mock Messages
        mock_messages = [
            "[Hệ thống] 12:00 - Chào mừng đến với phòng chat!",
            "Trần Thuận Trí [12:01]: Server core đã hoàn thành ghi log.",
            "Trương Gia Bân [12:02]: Router parse JSON đang chạy unit test.",
            "Lý Huỳnh Bích Trâm [12:03]: NetworkClient QThread sẵn sàng kết nối.",
            "Nguyễn Gia Bảo [12:04]: Đã hoàn thành xong khung giao diện PyQt6!",
            "Trần Trung Trực [12:05]: Widget MessageItem sắp ghép nối nhé."
        ]
        for msg in mock_messages:
            self.list_messages.addItem(QListWidgetItem(msg))

        # Tự động cuộn xuống tin nhắn cuối cùng
        self.list_messages.scrollToBottom()

    def send_message(self):
        """Xử lý demo khi người dùng gửi tin nhắn"""
        text = self.txt_message.text().strip()
        if not text:
            return

        # Thêm tin nhắn của mình vào danh sách để demo tương tác
        new_item = QListWidgetItem(f"Bạn [Vừa xong]: {text}")
        self.list_messages.addItem(new_item)
        self.list_messages.scrollToBottom()
        self.txt_message.clear()

    def demo_connect_action(self):
        """Mô phỏng sự kiện bấm nút kết nối"""
        ip = self.txt_ip.text().strip()
        port = self.txt_port.text().strip()

        if not ip or not port:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ IP và Port!")
            return

        # Demo cập nhật giao diện
        self.lbl_status.setText(f"Đã lưu cấu hình: {ip}:{port} (Chờ tích hợp QThread)")
        self.lbl_status.setStyleSheet("border: none; color: #2b8a3e; font-weight: bold;")
        QMessageBox.information(
            self, 
            "Cấu hình mạng", 
            f"Đã lưu IP: {ip} | Port: {port}\nSẵn sàng kết nối với network_worker.py của Lý Huỳnh Bích Trâm!"
        )

    def demo_emoji_click(self):
        """Placeholder cho Emoji Picker"""
        QMessageBox.information(
            self,
            "Emoji Picker",
            
        )


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())