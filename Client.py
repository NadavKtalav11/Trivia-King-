import errno
import msvcrt
import socket
import threading
import sys
import readchar
import time

import select

BROADCAST_PORT = 13117  # Known broadcast port
TEAM_NAME = "YourTeamName"  # Predefined team name

class Client:
    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.settimeout(3)  # Timeout for socket operations
        self.state = "looking_for_server"
        self.connected = False
        self.server_address = None  # Dynamically assigned server address
        self.server_port = None  # Dynamically assigned server port
        self.player_name = None
        self.input_thread = None
        self.game_ended = False
        self.input_condition = threading.Condition()

    def receive_broadcast(self):
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        try:
            print("Listening for server broadcast...")
            broadcast_socket.bind(('', BROADCAST_PORT))

            while True:
                data, addr = broadcast_socket.recvfrom(1024)
                magic_cookie = data[:4]
                message_type = data[4]

                if magic_cookie == b"\xab\xcd\xdc\xba" and message_type == 0x2:
                    self.server_address = addr[0]
                    self.server_port = int.from_bytes(data[37:39], byteorder='big')
                    print(f"Received server broadcast from {self.server_address}:{self.server_port}")
                    break
                if self.server_address:
                    return
                time.sleep(1)


        except KeyboardInterrupt:
            print("here")
            pass





    def connect_to_server(self):
        try:
            print(f"Connecting to the server at {self.server_address}:{self.server_port}...")
            self.client_socket.connect((self.server_address, self.server_port))
            self.connected = True
            self.state = "waiting_for_game_start"
            print("Connected to the server!")

            # Send player name to the server
            self.player_name = input("Enter your player name: ")
            self.client_socket.sendall(self.player_name.encode()) # Send player name with newline

        except socket.timeout:
            print("Connection timed out. No servers found.")
            self.receive_broadcast()

    def handle_user_input(self):
        while True:
            if self.game_ended:
                return
            input_char = 'l'
            first = True
            while ((input_char.strip().upper() not in ['Y', 'N', 'F', 'T', ]) &
                   (input_char.strip() not in ['0', '1', ])):
                if not first:
                    print("please insert only N,Y,F,T,0 or 1")
                first = False
                input_char = input()
            self.client_socket.sendall(input_char.encode())
            self.input_condition.acquire()
            self.input_condition.wait()
            self.input_condition.release()



    def receive_data_from_server(self):
        while True:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    break
                if "please insert" in data.decode().strip():
                    self.input_condition.acquire()
                    self.input_condition.notify_all()
                    self.input_condition.release()

                print("Received from server:", data.decode().strip())

                if "Congratulations to" in data.decode().strip():
                    self.game_ended =True
                    self.input_condition.acquire()
                    self.input_condition.notify_all()
                    self.input_condition.release()
                    return

            except socket.timeout:
                pass
            finally:
                time.sleep(0.3)


    def run(self):

        while not self.server_address:  # Wait until the server address is determined
            self.receive_broadcast()
            time.sleep(0.5)

        self.connect_to_server()

        self.input_thread = threading.Thread(target=self.handle_user_input)
        self.input_thread.daemon = True
        self.input_thread.start()

        self.receive_data_from_server()

        self.input_thread.join()
        self.client_socket.close()
        return


def main():
    while 1:
        client = Client()
        client.run()

if __name__ == "__main__":
    main()
