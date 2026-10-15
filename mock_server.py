import socket

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('127.0.0.1', 8080))
server.listen(1)

print("[MOCK SERVER] Đang chạy tại 127.0.0.1:8080... Chờ Client kết nối...")
conn, addr = server.accept()
print(f"[MOCK SERVER] Client đã kết nối từ {addr}")

# Nhận dữ liệu từ Client
data = conn.recv(1024).decode('utf-8')
print(f"[MOCK SERVER] Nhận từ Client: {data.strip()}")

# Gửi phản hồi lại cho Client (nhớ kèm \n)
response = '{"status": "success", "message": "Xin chao!"}\n'
conn.sendall(response.encode('utf-8'))
print("[MOCK SERVER] Đã gửi phản hồi về Client!")

conn.close()
server.close()