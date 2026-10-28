import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QGridLayout, 
                             QPushButton, QVBoxLayout, QLabel, QLineEdit)
from PyQt6.QtCore import Qt

class EmojiPickerDialog(QWidget):
    """
    Hộp thoại (Dialog) chọn Emoji dành cho Tuần 1.
    Chức năng: Chọn Emoji -> In ra Console & Tự đính kèm vào khung nhập liệu.
    """
    def __init__(self, parent_input_field=None):
        super().__init__()
        self.setWindowTitle("Chọn Emoji")
        self.resize(300, 200)
        self.setWindowFlags(Qt.WindowType.Tool)  # Hiển thị dạng cửa sổ phụ nổi lên
        
        self.parent_input_field = parent_input_field
        
        # Danh sách mã Emoji cơ bản (Unicode)
        self.emoji_list = [
            "😀", "😂", "🥰", "😎", "🤔", "🙄",
            "😭", "😡", "👍", "👎", "👋", "🎉",
            "🔥", "❤️", "💔", "💯", "✅", "❌"
        ]
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        title = QLabel("Danh sách Emoji")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Bố trí các nút bấm theo dạng lưới (Grid Layout)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(5)
        
        row, col = 0, 0
        max_cols = 6  # 6 icon trên mỗi hàng
        
        for emoji in self.emoji_list:
            btn = QPushButton(emoji)
            btn.setFixedSize(40, 40)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 20px; 
                    background-color: #2D2D30; 
                    border: 1px solid #3E3E42; 
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #3E3E42;
                }
            """)
            
            # Gắn sự kiện bấm nút
            btn.clicked.connect(lambda checked, e=emoji: self.on_emoji_clicked(e))
            grid_layout.addWidget(btn, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
                
        layout.addLayout(grid_layout)

    def on_emoji_clicked(self, selected_emoji):
        # Yêu cầu Tuần 1: In ra terminal/console khi click chọn Emoji
        print(f"[TEST EMOJI] Bạn vừa chọn: {selected_emoji}")
        
        # Chèn Emoji vào khung text (nếu có)
        if self.parent_input_field:
            current_text = self.parent_input_field.text()
            self.parent_input_field.setText(current_text + selected_emoji)
            
        self.hide()


# ==========================================
# KHU VỰC TEST CHẠY ĐỘC LẬP (DEMO TUẦN 1)
# ==========================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Tạo cửa sổ giả lập để kiểm tra chức năng
    test_window = QWidget()
    test_window.setWindowTitle("Test Emoji Picker - Ngô Gia Bảo (TV6)")
    test_window.resize(350, 120)
    
    test_layout = QVBoxLayout(test_window)
    
    txt_input = QLineEdit()
    txt_input.setPlaceholderText("Emoji chọn sẽ xuất hiện ở đây...")
    txt_input.setStyleSheet("font-size: 14px; padding: 6px;")
    
    btn_show_emoji = QPushButton("😊 Mở bảng Emoji")
    btn_show_emoji.setStyleSheet("font-size: 14px; padding: 6px; background-color: #007ACC; color: white; border-radius: 4px;")
    
    test_layout.addWidget(txt_input)
    test_layout.addWidget(btn_show_emoji)
    
    # Khởi tạo dialog và nối sự kiện
    emoji_dialog = EmojiPickerDialog(parent_input_field=txt_input)
    btn_show_emoji.clicked.connect(emoji_dialog.show)
    
    test_window.show()
    sys.exit(app.exec())