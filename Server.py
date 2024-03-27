import socket
import threading
import time

BROADCAST_PORT = 13117  # Known broadcast port
GAME_DURATION = 30  # Game duration in seconds


class ClientHandler(threading.Thread):

    def __init__(self, client_socket, client_address):
        super().__init__()
        self.client_socket = client_socket
        self.client_address = client_address

    def run(self):
        print(f"New connection from {self.client_address}")

        # Send welcome message
        welcome_message = f"Welcome to the game! Enter your player name followed by a newline:\n".encode()
        self.client_socket.sendall(welcome_message)

        # Receive player name from client
        player_name = self.client_socket.recv(1024).decode().strip()
        print(f"Player '{player_name}' connected.")

        while True:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    break
                print(f"Received from {player_name}: {data.decode()}")
            except socket.timeout:
                pass

        print(f"Connection with {player_name} closed.")
        self.client_socket.close()


def send_offer_message(server_port, server_address):
    broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    broadcast_socket.bind((server_address, BROADCAST_PORT))

    try:
        while True:
            print("Sending offer message...")
            offer_message = b"\xab\xcd\xdc\xba"  # Magic cookie
            offer_message += b"\x02"  # Message type: 0x2 for offer
            offer_message += bytes("ServerName".ljust(32), 'utf-8')  # Server name
            offer_message += server_port.to_bytes(2, byteorder='big')  # Server port
            broadcast_socket.sendto(offer_message, ('<broadcast>', BROADCAST_PORT))
            time.sleep(2)

    except KeyboardInterrupt:
        broadcast_socket.close()


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('', 0))  # Bind to any available interface
    server_socket.listen(5)

    server_port = server_socket.getsockname()[1]  # Get the dynamically assigned port
    server_address = server_socket.getsockname()[0]
    print(f"Server started, listening on IP address {server_address} port {server_port}...")

    offer_thread = threading.Thread(target=send_offer_message, args=(server_port, server_address, ))
    offer_thread.daemon = True
    offer_thread.start()

    clients = []
    game_start_time = time.time()
    print("here")
    try:
        while True:
            if time.time() - game_start_time >= GAME_DURATION:
                print("Game duration exceeded. Exiting...")
                break

            client_socket, client_address = server_socket.accept()
            print(f"New connection from {client_address}")

            client_handler = ClientHandler(client_socket, client_address)
            client_handler.start()
            clients.append(client_handler)

    except KeyboardInterrupt:
        print("Server stopped by user.")

    for client in clients:
        client.join()

    server_socket.close()


if __name__ == "__main__":
    main()
