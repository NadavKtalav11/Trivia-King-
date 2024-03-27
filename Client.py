import socket
import threading
import sys
import time

BROADCAST_PORT = 13117  # Known broadcast port
GAME_DURATION = 30  # Game duration in seconds
TEAM_NAME = "YourTeamName"  # Predefined team name

class Client:
    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.settimeout(3)  # Timeout for socket operations
        self.state = "looking_for_server"
        self.connected = False
        self.server_address = None  # Dynamically assigned server address
        self.server_port = None  # Dynamically assigned server port

    def receive_broadcast(self):
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        try:
            print("Listening for server broadcast...")
            broadcast_socket.bind(('', BROADCAST_PORT))

            while not self.server_address:
                data, addr = broadcast_socket.recvfrom(1024)
                magic_cookie = data[:4]
                message_type = data[4]

                if magic_cookie == b"\xab\xcd\xdc\xba" and message_type == 0x2:
                    self.server_address = addr[0]
                    self.server_port = int.from_bytes(data[37:39], byteorder='big')
                    print(f"Received server broadcast from {self.server_address}:{self.server_port}")
                    break
        except KeyboardInterrupt:
            broadcast_socket.close()

    def connect_to_server(self):
        try:
            print(f"Connecting to the server at {self.server_address}:{self.server_port}...")
            self.client_socket.connect((self.server_address, self.server_port))
            #self.client_socket.connect(('127.0.0.1', self.server_port))
            self.connected = True
            self.state = "game_mode"
            print("Connected to the server!")

            # Send player name to the server
            player_name = input("Enter your player name: ")
            self.client_socket.sendall(player_name.encode() + b'\n')  # Send player name with newline
        except socket.timeout:
            print("Connection timed out. No servers found.")
            sys.exit()

    def handle_user_input(self):
        while True:
            if self.state == "game_mode":
                input_char = input("Enter a character (or 'quit' to exit): ")
                if input_char.lower() == "quit":
                    self.client_socket.close()
                    break
                self.client_socket.sendall(input_char.encode())
            elif self.state == "connecting_to_server":
                pass
            elif self.state == "looking_for_server":
                pass

    def receive_data_from_server(self):
        while True:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    break
                print("Received from server:", data.decode())
            except socket.timeout:
                pass

    def run(self):
        broadcast_thread = threading.Thread(target=self.receive_broadcast)
        broadcast_thread.daemon = True
        broadcast_thread.start()

        while not self.server_address:  # Wait until the server address is determined
            pass

        self.connect_to_server()

        input_thread = threading.Thread(target=self.handle_user_input)
        input_thread.daemon = True
        input_thread.start()

        receive_thread = threading.Thread(target=self.receive_data_from_server)
        receive_thread.daemon = True
        receive_thread.start()

        input_thread.join()  # Wait for input thread to finish (if it finishes, we exit)

def main():
    client = Client()
    client.run()

if __name__ == "__main__":
    main()