import socket
import threading
import sqlite3
from cryptography.fernet import Fernet

# Database setup
conn = sqlite3.connect("chat_messages.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        username TEXT,
        message TEXT,
        recipient TEXT
    )
""")
conn.commit()

# Generate or load encryption key
try:
    with open("key.key", "rb") as key_file:
        key = key_file.read()
except FileNotFoundError:
    key = Fernet.generate_key()
    with open("key.key", "wb") as key_file:
        key_file.write(key)

cipher = Fernet(key)
clients = {}

def broadcast(message, sender, recipient="all"):
    """Send a message to all clients or a specific client."""
    encrypted_msg = cipher.encrypt(message.encode())
    for client, username in clients.items():
        if recipient == "all" or username == recipient:
            try:
                client.send(encrypted_msg)
            except:
                client.close()
                del clients[client]

def handle_client(client):
    """Handle communication with a single client."""
    try:
        client.send(cipher.encrypt("Enter your username: ".encode()))
        username = cipher.decrypt(client.recv(1024)).decode()
        clients[client] = username
        broadcast(f"{username} has joined the chat.", "Server")
        print(f"{username} connected.")

        while True:
            try:
                encrypted_msg = client.recv(1024)
                msg = cipher.decrypt(encrypted_msg).decode()

                if msg.startswith("@"):
                    # Show all available users when @ is pressed
                    user_list = [user for user in clients.values()]
                    user_list_str = ", ".join(user_list)
                    client.send(cipher.encrypt(f"Available users: {user_list_str}".encode()))

                    # Private message
                    recipient, private_msg = msg.split(" ", 1)
                    recipient = recipient[1:]  # Remove '@'

                    # Check if recipient exists
                    found = False
                    for client_conn, client_username in clients.items():
                        if client_username == recipient:
                            client_conn.send(cipher.encrypt(f"[Private from {username}]: {private_msg}".encode()))
                            found = True
                            break

                    if not found:
                        client.send(cipher.encrypt(f"User {recipient} not found.".encode()))
                else:
                    # Group message
                    broadcast(f"{username}: {msg}", username)
                    cursor.execute("INSERT INTO messages VALUES (?, ?, ?)", (username, msg, "all"))
                conn.commit()

            except:
                break
    finally:
        print(f"{clients[client]} has disconnected.")
        broadcast(f"{clients[client]} has left the chat.", "Server")
        client.close()
        del clients[client]

def accept_connections(server_socket):
    """Accept new connections."""
    while True:
        client, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client,)).start()

# Server setup
def start_server():
    host = "0.0.0.0"
    port = 12345
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(50)
    print("Server started on port 12345...")
    accept_connections(server_socket)

start_server()
