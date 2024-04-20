import errno
import msvcrt
import os
import socket
import threading
import sys
# import readchar
import time
import random
import colorama
colorama.init()  # Initialize colorama for cross-platform colored output

import select

BROADCAST_PORT = 13117  # Known broadcast port
TEAM_NAME = "YourTeamName"  # Predefined team name


class Bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    YELLOW = '\033[33m'
    RED = '\033[31m'
    WHITE = '\033[37m'
    BLACK = '\033[30m'
    DARKCYAN = '\033[36m'
    DARKYELLOW = '\033[33m'
    DARKRED = '\033[31m'
    DARKWHITE = '\033[37m'


animals = ["Lion", "Elephant", "Giraffe", "Tiger", "Penguin",
           "Dolphin", "Koala", "Kangaroo", "Cheetah", "Zebra",
           "Gorilla", "Rhino", "Hippo", "Chimpanzee", "Alligator",
           "Parrot", "Ostrich", "Cheetah", "Lemur", "Panda"]

colors = ["Red", "Blue", "Green", "Yellow", "Purple",
          "Orange", "Pink", "Brown", "Black", "White",
          "Gray", "Gold", "Silver", "Turquoise", "Cyan",
          "Magenta", "Lime", "Indigo", "Teal", "Beige"]


class Client:
    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.settimeout(None)  # Timeout for socket operations
        self.connected = False
        self.server_address = None  # Dynamically assigned server address
        self.server_port = None  # Dynamically assigned server port
        self.player_name = None
        self.input_thread = None
        self.game_ended = False
        self.input_condition = threading.Condition()

    """
        Receive broadcast messages from the server to discover its address and port.

        This function listens for broadcast messages sent by the server to discover
        its address and port. It extracts the server address and port from the
        received message and stores them for later use in connecting to the server.
        """
    def receive_broadcast(self):
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        try:
         #   print(Bcolors.HEADER + "Listening for server broadcast..." + Bcolors.ENDC)
            print(f"{Bcolors.HEADER}Listening for server broadcast...{Bcolors.ENDC}")

            broadcast_socket.bind(('0.0.0.0', BROADCAST_PORT))

            while True:

                data, addr = broadcast_socket.recvfrom(1024)

                magic_cookie = data[:4]
                message_type = data[4]

                if magic_cookie == b"\xab\xcd\xdc\xba" and message_type == 0x2:
                    self.server_address = addr[0]
                    self.server_port = int.from_bytes(data[37:39], byteorder='big')
                    server_name_bytes = data[5:37].rstrip(b'\x00')
                    server_name = server_name_bytes.decode('utf-8').strip()
                    print(Bcolors.OKBLUE + f"Received offer from server {server_name} \n broadcast from address- {self.server_address} : port-  {self.server_port}" + Bcolors.ENDC)

                    break
                if self.server_address:
                    return
                time.sleep(1)

        except KeyboardInterrupt:
            print("here")
            pass

    """
        Generate a random player name using animals and colors.

        Returns:
            str: A randomly generated player name.
        """
    def generate_name(self):
        animal = random.choice(animals)
        color = random.choice(colors)
        return f"{color} {animal} "

    """
        Connect to the server using the discovered address and port.

        This function establishes a connection to the server using the server
        address and port discovered through broadcast messages. It sends the
        player's name to the server after establishing the connection.
        """
    def connect_to_server(self):
        try:
            print(Bcolors.WARNING + f"Connecting to the server at {self.server_address}:{self.server_port}..." + Bcolors.ENDC)
            self.client_socket.connect((self.server_address, self.server_port))
            self.connected = True
            print(Bcolors.OKGREEN + "Connected to the server!" + Bcolors.ENDC)

        # Send player name to the server
            self.player_name = self.generate_name()
            self.client_socket.sendall(self.player_name.encode())  # Send player name with newline

        except socket.timeout:
            print("Connection timed out. No servers found.")
            self.receive_broadcast()

    """
        Handle user input during the game.

        This function continuously listens for user input and sends it to the server.
        It checks if the game has ended to stop listening for input.
    """
    def handle_user_input(self):
        self.input_condition.acquire()
        self.input_condition.wait()
        self.input_condition.release()
        while True:
            try:
                if self.game_ended:
                    return
                pressed_key = None

                if msvcrt.kbhit():

                    pressed_key = msvcrt.getch()
                    print("your answer " + pressed_key.decode())
                    
                    if pressed_key.decode() is not None:
                        if pressed_key in ([b'Y', b'N', b'F', b'T', b'1', b'0', b'y', b'n', b'f', b't']):

                            self.input_condition.acquire()
                            self.client_socket.sendall(pressed_key + b'\n')
                            self.input_condition.wait()
                            self.input_condition.release()

                        else:
                            print("Please insert only Y, N, F, T, 0, or 1.")
                time.sleep(0.1)
            except ConnectionResetError or ConnectionAbortedError:
                return

    """
        Receive data from the server and process it accordingly.

        This function continuously receives data from the server and processes it
        according to the content. It handles user input prompts, game messages,
        and end-of-game notifications.
        """
    def receive_data_from_server(self):
        while True:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    break
                
                print(Bcolors.UNDERLINE + "Received from server:" + Bcolors.ENDC)
                print(Bcolors.BOLD + data.decode().strip() + Bcolors.ENDC)

                if "please insert" in data.decode().strip():
                    while msvcrt.kbhit():
                        msvcrt.getwch()
                        time.sleep(0.05)

                    self.input_condition.acquire()
                    self.input_condition.notify_all()
                    self.input_condition.release()

                if "Congratulations to" in data.decode().strip():
                    self.game_ended = True
                    self.input_condition.acquire()
                    self.input_condition.notify_all()
                    self.input_condition.release()
                    return
                
                if "its a tie" in data.decode().strip():
                    self.game_ended = True
                    self.input_condition.acquire()
                    self.input_condition.notify_all()
                    self.input_condition.release()
                    return

            except socket.timeout:
                pass
            except ConnectionResetError or ConnectionAbortedError:
                break
            finally:
                time.sleep(0.3)

    """
       Run the client application.

       This function is the director of the execution of the client application. It
       waits for the server address to be discovered, connects to the server,
       starts the user input handling thread, receives data from the server,
       and cleans up resources after the game ends.
       """
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
        try:
            client.run()
            time.sleep(2)
        except Exception:
            print("unexpected error- starting new game")
        finally:
            if client.client_socket:
                client.client_socket.close()


if __name__ == "__main__":
    main()