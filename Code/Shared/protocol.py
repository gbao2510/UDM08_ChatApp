import json
import datetime

# ==========================================
# PHẦN 1: CÁC ĐỊNH DẠNG JSON CHUẨN (Thống nhất cho cả 6 người)
# ==========================================

# 1. Gói Client gửi khi đăng nhập
def make_login_packet(username, avatar_name="default.png"):
    return {
        "type": "login",
        "username": username,
        "avatar": avatar_name
    }

# 2. Gói Server trả về sau khi đăng nhập (Bắt buộc phải có để UI biết đã vào được chưa)
def make_login_ack(status="success", online_users=None):
    if online_users is None:
        online_users = []
    return {
        "type": "login_ack",
        "status": status, # "success" hoặc "fail"
        "online_users": online_users # Ví dụ: ["hoang_an", "minh_beo"]
    }

# 3. Gói tin nhắn bình thường
def make_msg_packet(sender, receiver, content):
    return {
        "type": "msg",
        "msg_id": 0, # Mặc định là 0, Server nhận được sẽ tự động đánh số đè lên
        "sender": sender,
        "receiver": receiver, # "all" nếu chat nhóm, hoặc "tên_người_nhận" nếu chat riêng
        "content": content,
        "timestamp": str(datetime.datetime.now().strftime("%H:%M:%S"))
    }

# 4. Gói Reply (Phải chứa cả nội dung gốc để UI vẽ lại khối trích dẫn)
def make_reply_packet(sender, receiver, content, original_msg_dict):
    return {
        "type": "reply",
        "msg_id": 0,
        "sender": sender,
        "receiver": receiver,
        "content": content,
        "reply_to": original_msg_dict, # Đính kèm nguyên cái dict của tin nhắn cũ vào đây
        "timestamp": str(datetime.datetime.now().strftime("%H:%M:%S"))
    }

# 5. Gói Forward 
def make_forward_packet(sender, receiver, original_content):
    return {
        "type": "forward",
        "msg_id": 0,
        "sender": sender,
        "receiver": receiver,
        "content": original_content,
        "timestamp": str(datetime.datetime.now().strftime("%H:%M:%S"))
    }

# ==========================================
# PHẦN 2: CƠ CHẾ ĐÓNG GÓI CHỐNG DÍNH GÓI TIN TCP
# ==========================================

def encode_message(data_dict):
    """
    Biến Dictionary thành chuỗi JSON, mã hóa UTF-8 (để gửi được Emoji).
    QUAN TRỌNG: Thêm ký tự '\n' ở cuối để làm mốc cắt gói tin.
    """
    json_str = json.dumps(data_dict, ensure_ascii=False)
    # Thêm '\n' làm cọc tiêu phân cách giữa các gói tin liên tiếp
    return (json_str + "\n").encode('utf-8')

def decode_messages(byte_stream):
    """
    Nhận luồng byte từ socket, cắt theo dấu '\n' và trả về danh sách các Dictionary.
    Dùng hàm này ở cả Server và Client mỗi khi gọi socket.recv()
    """
    messages = []
    decoded_str = byte_stream.decode('utf-8')
    
    # Cắt chuỗi dựa vào cọc tiêu '\n'
    packets = decoded_str.split('\n')
    
    for packet in packets:
        if packet.strip(): # Bỏ qua các khoảng trắng rỗng do nhát cắt cuối cùng tạo ra
            try:
                msg_dict = json.loads(packet)
                messages.append(msg_dict)
            except json.JSONDecodeError:
                print(f"[LỖI BỎ QUA] Gói tin không chuẩn JSON: {packet}")
                
    return messages
