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
colorama.init()

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

    def receive_broadcast(self):
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        try:
           # print("Listening for server broadcast...")
            print(Bcolors.HEADER + "Listening for server broadcast..." + Bcolors.ENDC)

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
                   # print(f"Received offer from server {server_name} \n broadcast from address- {self.server_address} : port-  {self.server_port}")
                    print(Bcolors.OKBLUE + f"Received offer from server {server_name} \n broadcast from address- {self.server_address} : port-  {self.server_port}" + Bcolors.ENDC)

                    break
                if self.server_address:
                    return
                time.sleep(1)


        except KeyboardInterrupt:
            print("here")
            pass


    def generate_name(self):
        animal = random.choice(animals)
        color = random.choice(colors)
        return f"{color} {animal} "





    def connect_to_server(self):
        try:
           # print(f"Connecting to the server at {self.server_address}:{self.server_port}...")
            print(Bcolors.WARNING + f"Connecting to the server at {self.server_address}:{self.server_port}..." + Bcolors.ENDC)
            self.client_socket.connect((self.server_address, self.server_port))
            self.connected = True
           # print("Connected to the server!")
            print(Bcolors.OKGREEN + "Connected to the server!" + Bcolors.ENDC)

        # Send player name to the server
            self.player_name = self.generate_name()
            self.client_socket.sendall(self.player_name.encode())# Send player name with newline

        except socket.timeout:
            print("Connection timed out. No servers found.")
            self.receive_broadcast()

    def handle_user_input(self):
        #self.input_condition.acquire()
        #self.input_condition.wait()
        #self.input_condition.release()
        while True:
            try:
                if self.game_ended:
                    return
                pressed_key = None
                # print("before msvcrt.kbhit ")

                #if msvcrt.kbhit():
                pressed_key = input().strip().upper()

               # pressed_key = msvcrt.getch()
                if pressed_key is not None:
                    #if pressed_key in ([b'Y', b'N', b'F', b'T',b'1',b'0',b'y', b'n',b'f', b't']):
                     #   print("your answer " + pressed_key)
                      #  self.client_socket.sendall(pressed_key + b'\n')
                       #self.input_condition.wait()
                        #self.input_condition.release()
                   # else:
                        #print("your answer " + pressed_key)
                       # print("please insert only N,Y,F,T,0 or 1 -")
                    if pressed_key in ['Y', 'N', 'F', 'T', '1', '0']:
                        print("Your answer:", pressed_key)
                        self.client_socket.sendall(pressed_key.encode() + b'\n')
                        #self.input_condition.wait()
                        #self.input_condition.release()
                    else:
                        print("Please insert only Y, N, F, T, 0, or 1.")
                time.sleep(0.1)
            except ConnectionResetError or ConnectionAbortedError:
                return
    def receive_data_from_server(self):
        while True:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    break
               # print("Received from server:", data.decode().strip())
                print(Bcolors.UNDERLINE + "Received from server:" + Bcolors.ENDC)
                print(Bcolors.BOLD + data.decode().strip() + Bcolors.ENDC)



                if "please insert" in data.decode().strip():
                    while msvcrt.kbhit():
                        msvcrt.getwch()
                    self.input_condition.acquire()
                    self.input_condition.notify_all()
                    self.input_condition.release()



                if "Congratulations to" in data.decode().strip():
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
