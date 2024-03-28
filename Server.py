import socket
import threading
import time
import random

from Questions import Questions

BROADCAST_PORT = 13117  # Known broadcast port
GAME_DURATION = 30  # Game duration in seconds
ANSWER_TIME_LIMIT = 10  # Time limit in seconds for answering each question
STATE_WAITING_FOR_CLIENTS = 0
STATE_GAME_MODE = 1
quesBank = Questions()

class ClientHandler(threading.Thread):
    def __init__(self, client_socket, client_address, player_name):
        super().__init__()
        self.client_socket = client_socket
        self.client_address = client_address
        self.player_name = player_name
        self.score = 0
        self.wait_lock = threading.Condition()

    def run(self):

        print(f"New connection from {self.client_address} - Player '{self.player_name}'")
        welcome_message = f"Welcome to the game, {self.player_name}!\n".encode()
        self.client_socket.sendall(welcome_message)
        welcome_message = f"Waiting for all the players to join, and then we'll start immediately.".encode()
        self.client_socket.sendall(welcome_message)

    def get_name(self):
        return self.player_name

class Server:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = []
        self.removed_clients = set()
        self.state = STATE_WAITING_FOR_CLIENTS
        self.game_start_time = None
        self.last_client_connect_time = None
        self.winnerName = ""



    def start_BroadCast(self , server_port , server_address):
        broadcast_thread = threading.Thread(target=self.send_offer_message, args=(server_port, server_address,))
        broadcast_thread.daemon = True
        broadcast_thread.start()

        try:
            while True:
                client_socket, client_address = self.server_socket.accept()
                print(f"New connection from {client_address}")

                player_name = client_socket.recv(1024).decode().strip()
                print(f"Player '{player_name}' connected.")
                client_handler = ClientHandler(client_socket, client_address, player_name)
                client_handler.start()
                self.clients.append(client_handler)
                self.last_client_connect_time = time.time()
                while True:
                    if time.time() - self.last_client_connect_time > 10:
                        self.run_game()
                        return
        except KeyboardInterrupt:
            print("Server stopped by user.")


    def send_offer_message(self, server_port, server_address):
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        broadcast_socket.bind((server_address, BROADCAST_PORT))

        try:
            while True:
                if self.last_client_connect_time is not None and time.time() - self.last_client_connect_time > 10:
                    break  # Stop sending offers if no client connected within 10 seconds

                print("Sending offer message...")
                offer_message = b"\xab\xcd\xdc\xba"  # Magic cookie
                offer_message += b"\x02"  # Message type: 0x2 for offer
                offer_message += bytes("ServerName".ljust(32), 'utf-8')  # Server name
                offer_message += server_port.to_bytes(2, byteorder='big')  # Server port
                broadcast_socket.sendto(offer_message, ('<broadcast>', BROADCAST_PORT))
                time.sleep(2)

        except KeyboardInterrupt:
            print("error 1")


    def remove(self, c):
        self.removed_clients.add(c)

    def run_game(self):
        print("Starting the game...")
        self.game_start_time = time.time()
        while not quesBank.no_repeated_questions_remaining():
            question, answer = quesBank.get_random_question()
            for client in self.clients:
                client_socket = client.client_socket
                client_name = client.get_name()
                question_message = f"Question: {question}\n".encode()
                client_socket.sendall(question_message)
                print(question_message.decode())
                client_socket.sendall(b"please insert your answer:\n")
                print("please insert your answer:")
                try:
                    client_socket.settimeout(ANSWER_TIME_LIMIT)
                    received_response = client_socket.recv(1024).decode().strip().upper()
                    client_socket.settimeout(None)

                    # Map the received response to true or false
                    if received_response in ['Y', 'T', '1']:
                        received_response = True
                    elif received_response in ['N', 'F', '0']:
                        received_response = False
                    print(f"{client.get_name()} sends {received_response}\n")

                    # Compare the received response with the correct answer
                    if received_response == answer:
                        text = f"{client_name} is Correct!, {client_name} won!!\n"
                        self.winnerName = client_name
                        print(f"{client_name} is Correct!, {client_name} won!! \n")
                        client_socket.sendall(text.encode())
                        self.end_game()
                        return
                    else:
                        text = f"{client_name} is Incorrect\n"
                        print(f"{client_name} is Incorrect \n")
                        client_socket.sendall(text.encode())
                        self.remove(client)
                except socket.timeout:
                    client_socket.sendall(b"Time's up!\n")
                    print("Time's up!\n")
        print("here\n")
        self.end_game()





    def run(self):
        self.server_socket.bind(('', 0))  # Bind to any available interface
        self.server_socket.listen(5)

        server_port = self.server_socket.getsockname()[1]  # Get the dynamically assigned port
        server_address = self.server_socket.getsockname()[0]
        print(f"Server started, listening on IP address {server_address} port {server_port}...")
        self.start_BroadCast(server_port, server_address)
        return


    def end_game(self):
        game_over = f"Game over!\nCongratulations to the winner: {self.winnerName}\n"
        for client in self.clients:
            sock = client.client_socket
            sock.sendall(game_over.encode())
        print(game_over)
        self.server_socket.close()


def main():
    while True:
        server = Server()
        server.run()

if __name__ == "__main__":
    main()
