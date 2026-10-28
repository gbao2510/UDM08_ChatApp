<<<<<<< Updated upstream:Code/Gui_main.py

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
=======
import os
import sys

# Đảm bảo nhận diện đúng các module cùng thư mục Client và thư mục gốc Project
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QFrame, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Liên kết module gui_actions.py và network_worker.py
from gui_actions import EmojiPickerDialog
from network_worker import NetworkClient


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chat Application - Team Client (Tuần 2: Quản lý Online)")
        self.resize(900, 620)
        self.setMinimumSize(750, 500)

        # Cài đặt giao diện & Mock data ban đầu
        self.setup_ui()
        self.load_mock_data()

        # Liên kết các module chức năng
        self.emoji_dialog = EmojiPickerDialog(parent_input_field=self.txt_message)
        self.network_client = None

    def setup_ui(self):
        # Widget trung tâm - Đặt nền tối thống nhất (Dark Mode)
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #1e1f22; color: #f2f3f5;")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # 1. KHU VỰC CẤU HÌNH MẠNG & USERNAME (TOP BAR)
        network_box = QFrame()
        network_box.setStyleSheet("""
            QFrame {
                background-color: #2b2d31;
                border: 1px solid #383a40;
                border-radius: 8px;
            }
        """)
        network_layout = QHBoxLayout(network_box)
        network_layout.setContentsMargins(14, 10, 14, 10)
        network_layout.setSpacing(10)

        # Tên người dùng (Username)
        lbl_user = QLabel("User:")
        lbl_user.setStyleSheet("border: none; font-weight: bold; color: #f2f3f5; font-size: 13px;")
        
        self.txt_username = QLineEdit("Gia Bảo")
        self.txt_username.setPlaceholderText("Tên bạn")
        self.txt_username.setFixedWidth(100)
        self.txt_username.setStyleSheet("""
            QLineEdit {
                background-color: #1e1f22;
                color: #ffffff;
                border: 1px solid #383a40;
                border-radius: 5px;
                padding: 5px 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #5865f2;
            }
        """)

        lbl_ip = QLabel("Server IP:")
        lbl_ip.setStyleSheet("border: none; font-weight: bold; color: #f2f3f5; font-size: 13px;")
        
        self.txt_ip = QLineEdit("127.0.0.1")
        self.txt_ip.setPlaceholderText("VD: 127.0.0.1")
        self.txt_ip.setFixedWidth(120)
        self.txt_ip.setStyleSheet("""
            QLineEdit {
                background-color: #1e1f22;
                color: #ffffff;
                border: 1px solid #383a40;
                border-radius: 5px;
                padding: 5px 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #5865f2;
            }
        """)

        lbl_port = QLabel("Port:")
        lbl_port.setStyleSheet("border: none; font-weight: bold; color: #f2f3f5; font-size: 13px;")
        
        self.txt_port = QLineEdit("5000")
        self.txt_port.setPlaceholderText("Port")
        self.txt_port.setFixedWidth(65)
        self.txt_port.setStyleSheet("""
            QLineEdit {
                background-color: #1e1f22;
                color: #ffffff;
                border: 1px solid #383a40;
                border-radius: 5px;
                padding: 5px 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #5865f2;
            }
        """)

        self.btn_connect = QPushButton("Kết nối")
        self.btn_connect.setStyleSheet("""
            QPushButton {
                background-color: #5865f2;
                color: white;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 5px;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4752c4;
            }
            QPushButton:disabled {
                background-color: #383a40;
                color: #80848e;
            }
        """)
        self.btn_connect.clicked.connect(self.demo_connect_action)

        self.lbl_status = QLabel("Trạng thái: Chưa kết nối")
        self.lbl_status.setStyleSheet("border: none; color: #949ba4; font-style: italic; font-size: 13px;")

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

        # 2.1 Sidebar: Danh sách bạn bè / Online Users (Nhiệm vụ Tuần 2)
        sidebar_layout = QVBoxLayout()
        self.lbl_online = QLabel("Online Users")
        self.lbl_online.setStyleSheet("color: #f2f3f5; font-weight: bold; font-size: 13px; margin-bottom: 2px;")
        
        self.list_users = QListWidget()
        self.list_users.setFixedWidth(230)
        self.list_users.setStyleSheet("""
            QListWidget {
                border: 1px solid #383a40;
                border-radius: 8px;
                background-color: #2b2d31;
                color: #f2f3f5;
                font-size: 13px;
            }
            QListWidget::item {
                color: #f2f3f5;
                padding: 10px;
                border-bottom: 1px solid #35373c;
            }
            QListWidget::item:hover {
                background-color: #35373c;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #404249;
                color: #5865f2;
                font-weight: bold;
                border-radius: 4px;
            }
        """)
        sidebar_layout.addWidget(self.lbl_online)
        sidebar_layout.addWidget(self.list_users)
        body_layout.addLayout(sidebar_layout)

        # 2.2 Chat Area: Khung hiển thị tin nhắn
        chat_layout = QVBoxLayout()
        lbl_chat = QLabel("Phòng Chat Chung")
        lbl_chat.setStyleSheet("color: #f2f3f5; font-weight: bold; font-size: 13px; margin-bottom: 2px;")

        self.list_messages = QListWidget()
        self.list_messages.setStyleSheet("""
            QListWidget {
                border: 1px solid #383a40;
                border-radius: 8px;
                background-color: #2b2d31;
                padding: 8px;
            }
            QListWidget::item {
                margin: 4px 0px;
                padding: 10px 14px;
                border-radius: 8px;
                background-color: #313338;
                color: #f2f3f5;
                border: 1px solid #383a40;
                font-size: 13px;
            }
            QListWidget::item:hover {
                background-color: #35373c;
            }
            QListWidget::item:selected {
                background-color: #383a40;
                color: #ffffff;
                border: 1px solid #5865f2;
            }
        """)
        chat_layout.addWidget(lbl_chat)
        chat_layout.addWidget(self.list_messages)
        body_layout.addLayout(chat_layout, stretch=1)

        main_layout.addLayout(body_layout, stretch=1)

        # 3. KHU VỰC NHẬP TIN NHẮN (BOTTOM BAR)
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        # Nút Emoji (liên kết với gui_actions.py)
        self.btn_emoji = QPushButton("😊")
        self.btn_emoji.setFixedSize(40, 40)
        self.btn_emoji.setToolTip("Chọn Emoji (gui_actions.py)")
        self.btn_emoji.setStyleSheet("""
            QPushButton {
                background-color: #2b2d31;
                color: white;
                font-size: 18px;
                border: 1px solid #383a40;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #35373c;
            }
        """)
        self.btn_emoji.clicked.connect(self.demo_emoji_click)

        # Ô nhập tin nhắn
        self.txt_message = QLineEdit()
        self.txt_message.setPlaceholderText("Nhập tin nhắn... (Nhấn Enter để gửi)")
        self.txt_message.setFixedHeight(40)
        self.txt_message.setStyleSheet("""
            QLineEdit {
                background-color: #2b2d31;
                color: #ffffff;
                border: 1px solid #383a40;
                border-radius: 6px;
                padding: 0 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #5865f2;
            }
        """)
        self.txt_message.returnPressed.connect(self.send_message)

        # Nút gửi
        self.btn_send = QPushButton("Gửi")
        self.btn_send.setFixedHeight(40)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #2b8a3e;
                color: white;
                font-weight: bold;
                padding: 0 20px;
                border-radius: 6px;
                border: none;
                font-size: 13px;
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
        """Nạp dữ liệu mẫu ban đầu trước khi kết nối Server"""
        # Mock Online Users
        mock_users = [
            "🟢 Trần Thuận Trí ",
            "🟢 Trương Gia Bân",
            "🟢 Lý Huỳnh Bích Trâm",
            "🟢 Nguyễn Gia Bảo ",
            "🟢 Trần Trung Trực",
            "⚪ Ngô Gia Bảo "
        ]
        self.list_users.clear()
        for user in mock_users:
            self.list_users.addItem(QListWidgetItem(user))
        self.lbl_online.setText(f"Online Users ({len(mock_users)})")

        # Mock Messages
        mock_messages = [
            "[Hệ thống]: Chào mừng bạn đến với phòng chat! Hãy kết nối Server để đồng bộ danh sách online."
        ]
        for msg in mock_messages:
            self.list_messages.addItem(QListWidgetItem(msg))

        self.list_messages.scrollToBottom()

    # =========================================================================
    # NHIỆM VỤ TUẦN 2: BẮT SIGNAL CẬP NHẬT DANH SÁCH NGƯỜI ONLINE LÊN SIDEBAR
    # =========================================================================
    def update_online_users(self, user_list):
        """
        Cập nhật toàn bộ danh sách người dùng online lên sidebar
        khi nhận được signal danh sách từ Server
        """
        self.list_users.clear()
        my_name = self.txt_username.text().strip()

        for user in user_list:
            if isinstance(user, dict):
                name = user.get("username", "Unknown")
            else:
                name = str(user).strip()

            if not name:
                continue

            # Đánh dấu (Bạn) nếu trùng tên
            if name == my_name:
                item_text = f"🟢 {name} (Bạn)"
            else:
                item_text = f"🟢 {name}"

            self.list_users.addItem(QListWidgetItem(item_text))

        self.lbl_online.setText(f"Online Users ({self.list_users.count()})")

    def add_online_user(self, username):
        """Thêm 1 người dùng mới online vào sidebar"""
        if not username:
            return
        my_name = self.txt_username.text().strip()
        display_name = f"{username} (Bạn)" if username == my_name else username

        # Kiểm tra xem user đã tồn tại chưa
        for i in range(self.list_users.count()):
            if username in self.list_users.item(i).text():
                return

        self.list_users.addItem(QListWidgetItem(f"🟢 {display_name}"))
        self.lbl_online.setText(f"Online Users ({self.list_users.count()})")

    def remove_online_user(self, username):
        """Xóa 1 người dùng vừa rời mạng khỏi sidebar"""
        if not username:
            return
        for i in range(self.list_users.count()):
            item = self.list_users.item(i)
            if username in item.text():
                self.list_users.takeItem(i)
                break
        self.lbl_online.setText(f"Online Users ({self.list_users.count()})")

    def send_message(self):
        """Xử lý gửi tin nhắn lên giao diện và gửi qua NetworkClient"""
        text = self.txt_message.text().strip()
        if not text:
            return

        my_name = self.txt_username.text().strip() or "Bạn"

        # Thêm tin nhắn của mình vào danh sách UI
        new_item = QListWidgetItem(f"{my_name} [Vừa xong]: {text}")
        self.list_messages.addItem(new_item)
        self.list_messages.scrollToBottom()
        self.txt_message.clear()

        # Gửi dữ liệu qua NetworkClient nếu đã kết nối
        if self.network_client and self.network_client.is_running:
            payload = {
                "type": "msg",
                "sender": my_name,
                "receiver": "all",
                "content": text
            }
            self.network_client.send_data(payload)

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

        # Dừng kết nối cũ nếu có
        if self.network_client and self.network_client.is_running:
            self.network_client.stop()

        # Khởi tạo NetworkClient và liên kết các tín hiệu (Signals)
        self.network_client = NetworkClient(host=ip, port=port)
        self.network_client.connected_signal.connect(self.on_connected)
        self.network_client.disconnected_signal.connect(self.on_disconnected)
        self.network_client.received_signal.connect(self.on_message_received)
        self.network_client.error_signal.connect(self.on_network_error)

        self.lbl_status.setText(f"Đang kết nối tới {ip}:{port}...")
        self.lbl_status.setStyleSheet("border: none; color: #4dabf7; font-style: italic; font-size: 13px;")
        self.network_client.connect_to_server(ip, port)

    def on_connected(self):
        """Xử lý khi kết nối Server thành công: Gửi gói login để Server ghi nhận online"""
        self.lbl_status.setText("Trạng thái: Đã kết nối Server")
        self.lbl_status.setStyleSheet("border: none; color: #40c057; font-weight: bold; font-size: 13px;")
        self.btn_connect.setEnabled(False)
        self.txt_username.setEnabled(False)
        self.txt_ip.setEnabled(False)
        self.txt_port.setEnabled(False)

        # Gửi thông điệp login kèm username để Server đồng bộ danh sách online (Tuần 2)
        my_name = self.txt_username.text().strip()
        login_packet = {
            "type": "login",
            "username": my_name
        }
        self.network_client.send_data(login_packet)

    def on_disconnected(self):
        """Xử lý khi ngắt kết nối khỏi Server"""
        self.lbl_status.setText("Trạng thái: Đã ngắt kết nối")
        self.lbl_status.setStyleSheet("border: none; color: #949ba4; font-style: italic; font-size: 13px;")
        self.btn_connect.setEnabled(True)
        self.txt_username.setEnabled(True)
        self.txt_ip.setEnabled(True)
        self.txt_port.setEnabled(True)

        # Đổi trạng thái danh sách người dùng sang offline khi mất kết nối
        self.lbl_online.setText("Online Users (Đã ngắt kết nối)")
        for i in range(self.list_users.count()):
            item = self.list_users.item(i)
            item.setText(item.text().replace("🟢", "⚪"))

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
        Nhận và phân luồng dữ liệu JSON từ Server:
        - Đồng bộ danh sách online (Tuần 2)
        - Nhận tin nhắn chat
        """
        if not isinstance(data, dict):
            self.list_messages.addItem(QListWidgetItem(str(data)))
            self.list_messages.scrollToBottom()
            return

        msg_type = data.get("type", "")

        # 1. Bắt signal cập nhật toàn bộ danh sách online từ Server
        if msg_type in ("online_list", "online_users", "user_list", "login_ack"):
            user_list = data.get("online_users") or data.get("users") or data.get("data") or []
            self.update_online_users(user_list)
            return

        # 2. Bắt signal khi có 1 user mới vừa kết nối
        if msg_type in ("user_join", "user_online"):
            new_user = data.get("username", "")
            self.add_online_user(new_user)
            self.list_messages.addItem(QListWidgetItem(f"[Hệ thống]: {new_user} đã tham gia phòng chat."))
            self.list_messages.scrollToBottom()
            return

        # 3. Bắt signal khi có 1 user vừa ngắt kết nối
        if msg_type in ("user_leave", "user_offline"):
            left_user = data.get("username", "")
            self.remove_online_user(left_user)
            self.list_messages.addItem(QListWidgetItem(f"[Hệ thống]: {left_user} đã rời phòng chat."))
            self.list_messages.scrollToBottom()
            return

        # 4. Bắt tin nhắn chat thông thường
        sender = data.get("sender", "Server")
        content = data.get("content", str(data))
        msg_str = f"[{sender}]: {content}"
        self.list_messages.addItem(QListWidgetItem(msg_str))
        self.list_messages.scrollToBottom()

    def demo_emoji_click(self):
        """Mở Emoji Picker từ gui_actions.py"""
        if hasattr(self, 'emoji_dialog') and self.emoji_dialog:
            self.emoji_dialog.show()

    def closeEvent(self, event):
        """Dọn dẹp tài nguyên khi tắt ứng dụng"""
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
>>>>>>> Stashed changes:Code/Client/gui_main.py
