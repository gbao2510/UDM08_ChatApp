import json


class ServerRouter:
    def __init__(self):
        self.next_msg_id = 1

    def parse_message(self, json_data):
        """Chuyển chuỗi JSON thành tin nhắn và gán msg_id."""
        try:
            message = json.loads(json_data)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("JSON không hợp lệ")

        if not isinstance(message, dict):
            raise ValueError("Tin nhắn phải là JSON object")

        message["msg_id"] = self.next_msg_id
        self.next_msg_id += 1

        return message