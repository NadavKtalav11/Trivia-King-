import socket
import threading
import time

from Questions import Questions

BROADCAST_PORT = 13117  # Known broadcast port
GAME_DURATION = 30  # Game duration in seconds
ANSWER_TIME_LIMIT = 10  # Time limit in seconds for answering each question
STATE_WAITING_FOR_CLIENTS = 0
STATE_GAME_MODE = 1





class ClientHandler(threading.Thread):
    def __init__(self, client_socket, client_address, player_name , server):
        super().__init__()
        self.client_socket = client_socket
        self.client_address = client_address
        self.player_name = player_name
        self.server = server
        self.wait_lock = server.answer_lock



    def get_input(self):
        while True:
            try:
                client_socket = self.client_socket
                client_socket.settimeout(0.3)
                received_response = client_socket.recv(1024).decode().strip().upper()
                client_socket.settimeout(None)
                # Map the received response to true or false
                if received_response in ['Y', 'T', '1']:
                    received_response = True
                elif received_response in ['N', 'F', '0']:
                    received_response = False
                print(f"{self.player_name} sends {received_response}\n")
                self.wait_lock.acquire()
                self.server.curr_answer_handler = self
                self.server.curr_answer = received_response
                self.wait_lock.release()

            except socket.timeout:
                pass
            except OSError:
                pass

    def run(self):

        print(f"New connection from {self.client_address} - Player '{self.player_name}'")
        welcome_message = f"Welcome to the game, {self.player_name}!\n".encode()
        self.client_socket.sendall(welcome_message)
        welcome_message = f"Waiting for all the players to join, and then we'll start immediately.".encode()
        self.client_socket.sendall(welcome_message)
        self.get_input()




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
        self.winnerName = None
        self.quesBank = None
        self.answer_lock = threading.Condition()
        self.curr_answer_handler = None
        self.curr_answer = None
        self.has_winner= False

    def get_address_with_255(self):
        # Create a UDP socket
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # connect to google DNS
            udp_socket.connect(("8.8.8.8", 80))
            # find local IP
            local_ip = udp_socket.getsockname()[0]

            # Extract the subnet address
            address_without_end = '.'.join(local_ip.split('.')[0:-1])

            # Construct the broadcast address
            address = address_without_end + ".255"

        finally:
            # Close the socket to release resources
            udp_socket.close()

        return address



    def start_broadcast(self,server_port,server_address):
        broadcast_thread = threading.Thread(target=self.send_offer_message, args=(server_port, server_address,))
        broadcast_thread.daemon = True
        broadcast_thread.start()
        self.server_socket.settimeout(1)
        self.last_client_connect_time = None
        while True:
            try:
                client_socket, client_address = self.server_socket.accept()
                player_name = None
                print(f"New connection from {client_address}")
                client_socket.settimeout(0.1)
                while player_name == None:
                    try:
                        player_name = client_socket.recv(1024).decode().strip()
                    except socket.timeout:
                            if self.last_client_connect_time is not None and self.last_client_connect_time < time.time():
                                break

                if player_name is not None:
                    print(f"Player '{player_name}' connected.")
                    client_handler = ClientHandler(client_socket, client_address, player_name,self)
                    client_handler.start()
                    self.clients.append(client_handler)
                    self.last_client_connect_time = time.time()
            except socket.timeout:
                if self.last_client_connect_time:
                    if time.time() - self.last_client_connect_time > 10:
                        self.run_game()
                        return



    def send_offer_message(self, server_port, server_address):
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        broadcast_socket.bind((server_address, BROADCAST_PORT))
        broadcast_address = self.get_address_with_255()
        try:
            while True:
                if self.last_client_connect_time is not None and time.time() - self.last_client_connect_time > 10:
                    break  # Stop sending offers if no client connected within 10 seconds

                print("Sending offer message...")
                offer_message = b"\xab\xcd\xdc\xba"  # Magic cookie
                offer_message += b"\x02"  # Message type: 0x2 for offer
                offer_message += bytes("BestServerEver".ljust(32), 'utf-8')  # Server name
                offer_message += server_port.to_bytes(2, byteorder='big')  # Server port
                broadcast_socket.sendto(offer_message, (broadcast_address, BROADCAST_PORT))
                time.sleep(2)

        except KeyboardInterrupt:
            print("error 1")



    def ask_question(self):
        question, answer = self.quesBank.get_random_question()
        self.removed_clients = set()
        for client in self.clients:
            client_socket = client.client_socket
            question_message = f"Question: {question}\n".encode()
            client_socket.sendall(question_message)
            print(question_message.decode())
            client_socket.sendall(b"please insert your answer:\n")
            print("send to clients - please insert your answer:")
        return answer

    def deal_with_answer(self, answer, handler, correct_answer):
        name = handler.get_name()
        if correct_answer == answer:
            text = f"{name} is Correct!, {name} won!!\n"
            self.winnerName = name
            print(f"{name} is Correct!, {name} won!! \n")
            for curr in self.clients:
                if curr!= handler:
                    curr.client_socket.sendall(text.encode())
            self.end_game()
            self.has_winner = True
            return
        else:
            text = f"{name} is suspended\n"
            print(f"{name} is Incorrect\n")
            for curr in self.clients:
                if curr.client_socket != handler:
                    curr.client_socket.sendall(text.encode())
            text = f"you are wrong please wait to the next round of questions\n"
            handler.client_socket.sendall(text.encode())
            self.remove(handler)


    def wait_for_answers(self, correct_answer):
        start_time = time.time()
        while time.time() - start_time < 10:
            if len(self.removed_clients) == len(self.clients):
                break
            self.answer_lock.acquire()
            self.answer_lock.wait(timeout=0.1)
            if self.curr_answer_handler is not None:
                answer = self.curr_answer
                handler = self.curr_answer_handler
                self.curr_answer_handler = None
                self.curr_answer = None
                self.answer_lock.release()
                if handler not in self.removed_clients:
                    self.deal_with_answer(answer, handler, correct_answer)
                    if self.has_winner:
                        return
            else:
                self.answer_lock.release()

    def remove(self, c):
        self.removed_clients.add(c)

    def run_game(self):
        self.quesBank = Questions()
        print("Starting the game...")
        self.game_start_time = time.time()
        while not self.quesBank.no_repeated_questions_remaining():
            correct_answer = self.ask_question()
            self.wait_for_answers(correct_answer)
            if self.winnerName is None:
                for client in self.clients:
                    client_socket = client.client_socket
                    client_socket.sendall(b"Time's up!\n")
                print("Time's up!\n")
            else:
                break


    def run(self):
        self.server_socket.bind(('', 0))  # Bind to any available interface
        self.server_socket.listen(5)

        server_port = self.server_socket.getsockname()[1]  # Get the dynamically assigned port
        server_address = socket.gethostbyname(socket.gethostname())
        print(f"Server started, listening on IP address {server_address} port {server_port}...")
        self.start_broadcast(server_port, server_address)
        return




    def end_game(self):
        game_over = f"Game over!\nCongratulations to the winner: {self.winnerName}\n"
        for client in self.clients:
            sock = client.client_socket
            sock.sendall(game_over.encode())
            sock.close()
        print(game_over)



def main():
    while True:
        server = Server()
        server.run()

if __name__ == "__main__":
    main()
