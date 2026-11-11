import os
import sys
import io
import pytest
from PyQt6.QtWidgets import QApplication, QLineEdit, QTextEdit, QDialog
from PyQt6.QtCore import Qt

# Đảm bảo import được module từ thư mục gốc
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

client_dir = os.path.join(project_root, "Code", "Client")
if client_dir not in sys.path:
    sys.path.insert(0, client_dir)

from Code.Client.gui_actions import (
    EmojiPickerDialog, ForwardDialog, create_message_context_menu,
    attach_context_menu_to_message,
    get_asset_path, get_asset_icon, get_asset_pixmap, ASSETS_DIR
)
from Test.clients import ResourceMonitor, save_report_to_file, REPORT_FILE


@pytest.fixture(scope="session")
def qapp():
    """Khởi tạo QApplication dùng chung cho các test GUI"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


# =========================================================================
# 1. KIỂM THỬ TUẦN 1: THƯ MỤC ASSETS VÀ CÁC HÀM TIỆN ÍCH
# =========================================================================
def test_assets_folder_exists():
    """Kiểm tra thư mục assets tồn tại"""
    assert os.path.exists(ASSETS_DIR), f"Thư mục assets không tồn tại tại {ASSETS_DIR}"
    assert os.path.isdir(ASSETS_DIR), "assets phải là thư mục"


def test_assets_required_files():
    """Kiểm tra sự hiện diện của các tệp tin icon và avatar bắt buộc"""
    required_files = [
        "app_icon.png",
        "default_avatar.png",
        "emoji_icon.png",
        "send_icon.png",
        "attach_icon.png",
        "avatar_user1.png",
        "avatar_user2.png",
        "avatar_user3.png",
        "avatar_user4.png",
        "README.md"
    ]
    for filename in required_files:
        path = get_asset_path(filename)
        assert os.path.exists(path), f"Thiếu tệp tin tài nguyên: {filename}"
        assert os.path.getsize(path) > 0, f"Tệp tin {filename} bị rỗng (0 bytes)"


def test_asset_helpers(qapp):
    """Kiểm tra các hàm get_asset_icon và get_asset_pixmap"""
    icon = get_asset_icon("emoji_icon.png")
    assert not icon.isNull(), "get_asset_icon không tải được emoji_icon.png"

    pixmap = get_asset_pixmap("app_icon.png", width=64, height=64)
    assert not pixmap.isNull(), "get_asset_pixmap không tải được app_icon.png"
    assert pixmap.width() <= 64 and pixmap.height() <= 64, "Scale kích thước pixmap không chuẩn"


# =========================================================================
# 2. KIỂM THỬ TUẦN 1: DIALOG EMOJI PICKER (IN RA CONSOLE & CHÈN TEXT)
# =========================================================================
def test_emoji_picker_console_output(qapp):
    """Kiểm tra yêu cầu Tuần 1: Khi chọn Emoji BẮT BUỘC in ra console"""
    txt = QLineEdit()
    picker = EmojiPickerDialog(parent_input_field=txt)

    # Chặn luồng stdout để kiểm tra dòng in ra console
    captured_output = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured_output
        picker.on_emoji_clicked("🔥")
    finally:
        sys.stdout = old_stdout

    output_str = captured_output.getvalue()
    assert "[TEST EMOJI] Bạn vừa chọn: 🔥" in output_str, f"Console không in đúng format: {output_str}"


def test_emoji_picker_insert_line_edit(qapp):
    """Kiểm tra chèn Emoji vào QLineEdit"""
    txt = QLineEdit("Xin chào ")
    picker = EmojiPickerDialog(parent_input_field=txt)
    picker.on_emoji_clicked("🎉")
    assert "🎉" in txt.text(), "Emoji không được chèn vào QLineEdit"


def test_emoji_picker_insert_text_edit(qapp):
    """Kiểm tra chèn Emoji vào QTextEdit (AutoResizingTextEdit)"""
    txt = QTextEdit()
    picker = EmojiPickerDialog(parent_input_field=txt)
    picker.on_emoji_clicked("🚀")
    assert "🚀" in txt.toPlainText(), "Emoji không được chèn vào QTextEdit"


def test_emoji_picker_signal(qapp):
    """Kiểm tra EmojiPickerDialog phát tín hiệu emoji_selected"""
    picker = EmojiPickerDialog()
    received = []
    picker.emoji_selected.connect(lambda e: received.append(e))
    picker.on_emoji_clicked("💯")
    assert received == ["💯"], "Tín hiệu emoji_selected không phát đúng ký tự emoji"


# =========================================================================
# 3. KIỂM THỬ TUẦN 2: SCRIPT STRESS TEST & GHI NHẬN SỐ LIỆU RAM/CPU
# =========================================================================
def test_resource_monitor():
    """Kiểm tra bộ giám sát tài nguyên Hardware Monitor trong clients.py"""
    monitor = ResourceMonitor(sample_interval=0.05)
    monitor.start()
    import time
    time.sleep(0.15)
    monitor.stop()

    summary = monitor.get_summary()
    assert "sys_cpu_avg" in summary
    assert "sys_cpu_peak" in summary
    assert "sys_ram_avg" in summary
    assert "sys_ram_peak" in summary
    assert summary["sys_ram_peak"] > 0, "Không đo được RAM hệ thống"


def test_report_generation(tmp_path):
    """Kiểm tra hàm lưu báo cáo kết quả kiểm thử 2 mức tải"""
    fake_results = [
        {
            "num_users": 10,
            "success_count": 10,
            "fail_count": 0,
            "success_rate": 100.0,
            "total_duration": 1.5,
            "avg_latency_ms": 12.5,
            "cpu_before": 15.0,
            "cpu_peak": 25.0,
            "cpu_avg": 20.0,
            "cpu_after": 14.5,
            "ram_before_pct": 80.0,
            "ram_peak_pct": 80.5,
            "ram_after_pct": 80.0,
            "server_ram_peak_mb": 24.5
        },
        {
            "num_users": 50,
            "success_count": 50,
            "fail_count": 0,
            "success_rate": 100.0,
            "total_duration": 2.8,
            "avg_latency_ms": 28.3,
            "cpu_before": 16.0,
            "cpu_peak": 48.0,
            "cpu_avg": 35.0,
            "cpu_after": 15.2,
            "ram_before_pct": 80.5,
            "ram_peak_pct": 81.2,
            "ram_after_pct": 80.6,
            "server_ram_peak_mb": 38.2
        }
    ]
    report_file = tmp_path / "test_report.txt"
    save_report_to_file(fake_results, filepath=str(report_file))

    assert os.path.exists(report_file), "Không tạo được file báo cáo"
    content = report_file.read_text(encoding="utf-8")
    assert "Mức 1: 10 Users" in content
    assert "Mức 2: 50 Users" in content
    assert "100.0%" in content


# =========================================================================
# 4. KIỂM THỬ MỞ RỘNG: FORWARD DIALOG & CONTEXT MENU (IMAGE 1)
# =========================================================================
def test_forward_dialog(qapp):
    """Kiểm tra Hộp thoại Forward"""
    dialog = ForwardDialog(message_content="Tin nhắn bí mật", online_users=["Thuận Trí", "Gia Bân"])
    assert dialog.user_list_widget.count() >= 3  # all + Thuận Trí + Gia Bân

    received = []
    dialog.forward_confirmed.connect(lambda rec, txt: received.append((rec, txt)))
    dialog.on_confirm_forward()
    assert len(received) == 1
    assert received[0][1] == "Tin nhắn bí mật"


def test_context_menu_creation(qapp):
    """Kiểm tra tạo Context Menu chuột phải"""
    dummy_widget = QLineEdit()
    msg_dict = {"sender": "Gia Bảo", "content": "Hello World"}

    menu = create_message_context_menu(dummy_widget, msg_dict)
    actions = [a.text() for a in menu.actions() if a.text()]
    assert any("Trả lời" in a for a in actions), "Thiếu action Reply"
    assert any("Chuyển tiếp" in a for a in actions), "Thiếu action Forward"
    assert any("Sao chép" in a for a in actions), "Thiếu action Copy"


# =========================================================================
# 5. KIỂM THỬ TUẦN 4 (NGÔ GIA BẢO): GẮN CONTEXT MENU CHUỘT PHẢI & POP-UP FORWARD
# =========================================================================
def test_forward_dialog_with_dict_users(qapp):
    """Tuần 4: Kiểm tra ForwardDialog nhận danh sách người dùng dạng Dict (từ Server Tuần 3/4)"""
    mock_dict_users = [
        {"username": "Trần Thuận Trí", "avatar": "avatar_user1.png"},
        {"username": "Trương Gia Bân", "avatar": "avatar_user2.png"},
        {"username": "Lý Huỳnh Bích Trâm", "avatar": "avatar_user3.png"}
    ]
    dialog = ForwardDialog(message_content="Nội dung mật", online_users=mock_dict_users)
    assert dialog.user_list_widget.count() == 4  # all + 3 users

    # Kiểm tra receiver được trích xuất là username string thuần túy chứ không phải dict
    dialog.user_list_widget.setCurrentRow(1)
    current_item = dialog.user_list_widget.currentItem()
    receiver = current_item.data(Qt.ItemDataRole.UserRole)
    assert receiver == "Trần Thuận Trí"

    received = []
    dialog.forward_confirmed.connect(lambda rec, txt: received.append((rec, txt)))
    dialog.on_confirm_forward()
    assert received == [("Trần Thuận Trí", "Nội dung mật")]


def test_forward_dialog_search_filter(qapp):
    """Tuần 4: Kiểm tra tính năng lọc / tìm kiếm người nhận trong ForwardDialog"""
    users = ["Trần Thuận Trí", "Trương Gia Bân", "Nguyễn Gia Bảo"]
    dialog = ForwardDialog(message_content="Test search", online_users=users)

    # Lọc theo từ khóa "Thuận"
    dialog.txt_search.setText("Thuận")
    visible_texts = [
        dialog.user_list_widget.item(i).text()
        for i in range(dialog.user_list_widget.count())
        if not dialog.user_list_widget.item(i).isHidden()
    ]
    assert len(visible_texts) == 1
    assert "Thuận Trí" in visible_texts[0]

    # Xóa tìm kiếm -> hiển thị lại toàn bộ
    dialog.txt_search.setText("")
    visible_count = sum(
        1 for i in range(dialog.user_list_widget.count())
        if not dialog.user_list_widget.item(i).isHidden()
    )
    assert visible_count == 4  # all + 3 users


def test_forward_dialog_dynamic_update_users(qapp):
    """Tuần 4: Kiểm tra cập nhật danh sách người dùng realtime qua set_online_users"""
    dialog = ForwardDialog(message_content="Test update", online_users=["A"])
    assert dialog.user_list_widget.count() == 2  # all + A

    dialog.set_online_users(["A", "B", "C"])
    assert dialog.user_list_widget.count() == 4  # all + A + B + C


def test_context_menu_forward_action_triggered(qapp):
    """Tuần 4: Kiểm tra action Forward trong Context Menu kích hoạt callback chính xác"""
    dummy_widget = QLineEdit()
    msg_dict = {"sender": "Bảo", "content": "Tin nhắn chuyển tiếp"}

    forward_called = []
    menu = create_message_context_menu(
        dummy_widget,
        msg_dict,
        on_forward=lambda m: forward_called.append(m)
    )

    # Tìm action Forward và kích hoạt
    act_forward = next(a for a in menu.actions() if "Chuyển tiếp" in a.text())
    act_forward.trigger()

    assert len(forward_called) == 1
    assert forward_called[0]["content"] == "Tin nhắn chuyển tiếp"


def test_attach_context_menu_to_message(qapp):
    """Tuần 4: Kiểm tra hàm tiện ích gắn Context Menu chuột phải lên widget tin nhắn"""
    from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout

    # Tạo 1 widget bong bóng chat giả lập
    bubble = QWidget()
    layout = QVBoxLayout(bubble)
    lbl_text = QLabel("Nội dung chat demo")
    layout.addWidget(lbl_text)

    msg_dict = {"sender": "Thuận Trí", "content": "Nội dung chat demo"}

    attach_context_menu_to_message(
        widget=bubble,
        message_dict=msg_dict,
        get_online_users=["all", "User1", "User2"]
    )

    # Widget và các con phải được cấu hình CustomContextMenu
    assert bubble.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu
    assert lbl_text.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu


