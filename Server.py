import socket
import threading
import time
import random
from datetime import datetime
from datetime import timedelta
from Questions import Questions
#import  colorama 
#colorama.init()


BROADCAST_PORT = 13117  # Known broadcast port
GAME_DURATION = 30  # Game duration in seconds
ANSWER_TIME_LIMIT = 10  # Time limit in seconds for answering each question
STATE_WAITING_FOR_CLIENTS = 0
STATE_GAME_MODE = 1


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


"""
    Thread class to handle each client connection.

    Attributes:
        client_socket (socket): The socket object for client communication.
        client_address (tuple): The client's address (host, port).
        player_name (str): The name of the player connected.
        server (Server): Reference to the server instance.
        wait_lock (threading.Condition): Lock for synchronizing client answers.
    """
class ClientHandler(threading.Thread):

    """
        Initialize the ClientHandler instance.

        Args:
            client_socket (socket): The socket object for client communication.
            client_address (tuple): The client's address (host, port).
            player_name (str): The name of the player connected.
            server (Server): Reference to the server instance.
        """
    def __init__(self, client_socket, client_address, player_name , server):
        super().__init__()
        self.client_socket = client_socket
        self.client_address = client_address
        self.player_name = player_name
        self.server = server
        self.wait_lock = server.answer_lock



    """
        Receive and process input from the connected client.

        This method continuously listens for input from the client and handles it accordingly.
        """    
    def get_input(self):
        client_socket = self.client_socket
        while True:
            try:
                client_socket.settimeout(0.1)
                received_response = client_socket.recv(1024).decode().strip().upper()
                client_socket.settimeout(None)
                # Map the received response to true or false
                if received_response in ['Y', 'T', '1']:
                    received_response = True
                elif received_response in ['N', 'F', '0']:
                    received_response = False
                else:
                    break
                print(Bcolors.CYAN + f"{self.player_name} sends {received_response}" + Bcolors.ENDC)
                self.wait_lock.acquire()
                self.server.curr_answer_handler = self
                self.server.curr_answer = received_response
                self.wait_lock.release()

            except socket.timeout:
                pass
            except OSError:
                #self.server.removeclient(self)
                break

    """
        Run method for the client handler thread.

        Sends welcome messages and processes client input.
        """
    def run(self):

        print(f"{Bcolors.OKBLUE }New connection from {self.client_address} - Player '{self.player_name}' {Bcolors.ENDC}")

        welcome_message = f"Welcome to the game, {self.player_name}!\n".encode()
        self.client_socket.sendall(welcome_message)
        welcome_message = f"Waiting for all the players to join, and then we'll start immediately.".encode()
        self.client_socket.sendall(welcome_message)
        self.get_input()




    def get_name(self):
        return self.player_name

"""
    Class representing the game server.

    Handles client connections, game logic, and broadcasting.
    """
class Server:

    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = []
        self.removed_clients = set()
        self.state = STATE_WAITING_FOR_CLIENTS
        self.game_start_time = None
        self.game_end_time = None
        self.last_client_connect_time = None
        self.winnerName = None
        self.quesBank = None
        self.answer_lock = threading.Condition()
        self.curr_answer_handler = None
        self.curr_answer = None
        self.has_winner = False
        self.counterNames = 1
        self.times_up = False
        self.answer_updated = False
        self.clients_lock = threading.Condition()
        self.player_names = []
        self.counter_rounds = 1



    """
        Get the broadcast address with the last octet set to 255.

        Returns:
            str: The broadcast address.
        """
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


    def counterDec(self):
        to_return = self.counterNames
        self.counterNames = self.counterNames+1
        return to_return


    """
        Start broadcasting server offer messages.

        Args:
            server_port (int): The server port.
            server_address (str): The server IP address.
        """
    def start_broadcast(self,server_port,server_address):
        broadcast_thread = threading.Thread(target=self.send_offer_message, args=(server_port, server_address,))
        broadcast_thread.daemon = True
        broadcast_thread.start()
        self.server_socket.settimeout(0.3)
        self.last_client_connect_time = None
        while True:
            try:
                client_socket, client_address = self.server_socket.accept()
                print(f"{Bcolors.OKGREEN }New connection from {client_address} {Bcolors.ENDC}")
                client_socket.settimeout(0.1)
                player_name = client_socket.recv(1024).decode().strip()
                counter = self.counterDec()
                player_name = f"{player_name} {counter}"
                if player_name is not None:
                    self.player_names.append(player_name)
                    print(Bcolors.YELLOW + f"Player '{player_name}' connected." + Bcolors.ENDC)
                    client_handler = ClientHandler(client_socket, client_address, player_name,self)
                    client_handler.start()
                    self.clients_lock.acquire()
                    self.clients.append(client_handler)
                    self.clients_lock.release()
                    self.last_client_connect_time = time.time()
            except socket.timeout:
                time.sleep(0.5)
                if self.last_client_connect_time:
                    if time.time() - self.last_client_connect_time > 10:
                        self.run_game()
                        return


    """
        Send offer messages to broadcast address.

        Args:
            server_port (int): The server port.
            server_address (str): The server IP address.
        """
    def send_offer_message(self, server_port, server_address):
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        broadcast_socket.bind(("", BROADCAST_PORT))
        broadcast_address = self.get_address_with_255()
        try:
            while True:
                if self.last_client_connect_time is not None and time.time() - self.last_client_connect_time > 10:
                    break  # Stop sending offers if no client connected within 10 seconds
                print(f"{Bcolors.OKCYAN}Sending offer message... {Bcolors.ENDC}")

                offer_message = b"\xab\xcd\xdc\xba"  # Magic cookie
                offer_message += b"\x02"  # Message type: 0x2 for offer
                offer_message += bytes("BestServerEver".ljust(32), 'utf-8')  # Server name
                offer_message += server_port.to_bytes(2, byteorder='big')  # Server port
                broadcast_socket.sendto(offer_message, (broadcast_address, BROADCAST_PORT))
                time.sleep(2)

        except KeyboardInterrupt:
            print("error 1")
            time.sleep(0.3)


    """
        Ask a question to all connected clients.

        Returns:
            str: The question asked.
        """
    def ask_question(self):
        question, answer = self.quesBank.get_random_question()
        self.removed_clients = set()
        disconnected_clients = set()
        question_message = f"Question: {question}\n".encode()
        for client in self.clients:
            client_socket = client.client_socket
            try:
                client_socket.sendall(question_message)
                client_socket.sendall(b"please insert your answer:\n")
            except OSError:
                disconnected_clients.add(client)
        self.remove_disconected_clients(disconnected_clients)
        print(Bcolors.BOLD + question_message.decode() + Bcolors.ENDC)
        print(Bcolors.HEADER + "send to clients - please insert your answer:" + Bcolors.ENDC)

        return answer



    def tie_end_game(self):       
        self.game_end_time = time.time()
        game_over = f"Game over!\n It's a tie \n"
        game_end_datetime = datetime.fromtimestamp(self.game_end_time)
        game_start_datetime = datetime.fromtimestamp(self.game_start_time)
        game_total_time = game_end_datetime - game_start_datetime
        # Extract hours, minutes, and seconds from the game duration
        hours = game_total_time.seconds // 3600
        minutes = (game_total_time.seconds % 3600) // 60
        seconds = game_total_time.seconds % 60
        #print(f"{Bcolors.HEADER}Game over!\n" + Bcolors.ENDC)

        for client in self.clients:
            sock = client.client_socket
            try:
                sock.sendall(game_over.encode())
            except Exception:
                print("exeption")
                pass

        time.sleep(4)
        for client in self.clients:
            try:
                client.client_socket.close()
            except Exception as e:
                pass
        self.server_socket.close()
       # print(game_over)
        print(Bcolors.RED + "Game over!\n its a Tie" + Bcolors.ENDC)
        print(Bcolors.UNDERLINE + "Some statistics for the soul..." + Bcolors.ENDC)
        print(Bcolors.RED + "Game start time: " + game_start_datetime.strftime("%Y-%m-%d %H:%M:%S") + Bcolors.ENDC)
        print(Bcolors.RED + "Game end time: " + game_end_datetime.strftime("%Y-%m-%d %H:%M:%S") + Bcolors.ENDC)
        print(Bcolors.RED + "Game duration: " + f"{hours} hours, {minutes} minutes, {seconds} seconds" + Bcolors.ENDC)
        print(Bcolors.OKCYAN + "Players who participated:" + Bcolors.ENDC)
        for name in self.player_names:
            print(name)
        print(Bcolors.WARNING + f"Total rounds: {self.counter_rounds-1}\n" + Bcolors.ENDC)


    """
        Process the answer received from a client.

        Args:
            answer (bool): The answer received.
            handler (ClientHandler): The client handler instance.
            correct_answer (bool): The correct answer to the question.
        """
    def deal_with_answer(self, answer, handler, correct_answer):
        name = handler.get_name()
        disconnected_clients = set()
        if correct_answer == answer:
            text = f"{name} is Correct!, {name} won!!\n"
            self.winnerName = name
            print(Bcolors.OKGREEN + f"{name} is Correct!, {name} won!! \n" + Bcolors.ENDC)
            for curr in self.clients:
                if curr != handler:
                    try:
                        curr.client_socket.sendall(text.encode())
                    except ConnectionResetError or ConnectionAbortedError:
                        disconnected_clients.add(curr)
            self.remove_disconected_clients(disconnected_clients)
            if len(self.clients) == 0:
                return
            self.end_game()
            self.has_winner = True
            return
        else:
            text = f"{name} is suspended\n"
            print(Bcolors.RED + f"{name} is Incorrect\n" + Bcolors.ENDC)
            self.counter_rounds += 1

            for curr in self.clients:
                try:
                    curr.client_socket.sendall(text.encode())
                except Exception:
                    disconnected_clients.add(curr)
            self.remove_disconected_clients(disconnected_clients)

            text = f"you are wrong please wait to the next round of questions\n"
            handler.client_socket.sendall(text.encode())
            self.remove(handler)

    """
        Wait for answers from all connected clients.

        Args:
            correct_answer (bool): The correct answer to the question.
        """
    def wait_for_answers(self, correct_answer):
        start_time = time.time()
        has_answer = False
        self.times_up = False
        while time.time() - start_time < 10:
            if len(self.removed_clients) == len(self.clients):
                break
            self.answer_lock.acquire()
            self.answer_lock.wait(timeout=0.3)
            if self.curr_answer_handler is not None:
                has_answer = True
                answer = self.curr_answer
                handler = self.curr_answer_handler
                self.curr_answer_handler = None
                self.curr_answer = None

                self.answer_lock.release()
                if handler not in self.removed_clients:
                    self.deal_with_answer(answer, handler, correct_answer)
                    if len(self.clients) == 0:
                        return
                    if self.has_winner:
                        return
            else:
                self.answer_lock.release()
        if not has_answer:
            self.times_up = True

    """
        Remove a client from the server.

        Args:
            c (ClientHandler): The client handler instance to remove.
        """
    def remove(self, c):
        self.clients_lock.acquire()
        self.removed_clients.add(c)
        self.clients_lock.release()

    def remove_disconected_clients(self, disconnected_list):
        self.clients_lock.acquire()
        for client in disconnected_list:
            self.clients.remove(client)
            if client in self.removed_clients:
                self.removed_clients.remove(client)
        self.clients_lock.release()

    """
        Run the game logic.

        Manages asking questions, receiving answers, and determining the winner.
        """
    def run_game(self):
        self.quesBank = Questions()
        disconnected_clients = set()
        print(Bcolors.WARNING + "Starting the game..." + Bcolors.ENDC)

        self.game_start_time = time.time()
        while not self.quesBank.no_repeated_questions_remaining():
            if len(self.clients) == 0:
                print("starting new game")
                return
            correct_answer = self.ask_question()
            if len(self.clients) == 0:
                print("starting new game")
                return
            self.wait_for_answers(correct_answer)
            if len(self.clients) == 0:
                print("starting new game")
                return
            if self.winnerName is None:
                if self.times_up:
                    for client in self.clients:
                        client_socket = client.client_socket
                        try:
                            client_socket.sendall(b"Time's up!\n")
                        except ConnectionResetError or ConnectionAbortedError:
                            disconnected_clients.add(client)
                    self.remove_disconected_clients(disconnected_clients)
                    print(Bcolors.RED + "Time's up!\n" + Bcolors.ENDC)
                    self.counter_rounds +=1
                    self.times_up = False
                time.sleep(0.1)
            else:
                break
        if self.quesBank.no_repeated_questions_remaining():
            print("no more Questions -its a tie")
            self.tie_end_game()
            return
            
        

    """
        Run the game server.

        Handles client connections, broadcasting, and game execution.
        """
    def run(self):
        self.server_socket.bind(('', BROADCAST_PORT))  # Bind to any available interface
        self.server_socket.listen(5)

        server_port = self.server_socket.getsockname()[1]  # Get the dynamically assigned port
        server_address = socket.gethostbyname(socket.gethostname())
        print(f"{Bcolors.HEADER }Server started, listening on IP address {server_address} port {server_port}...{Bcolors.ENDC}")
        self.start_broadcast(server_port, server_address)
        return

    """
        End the game and display statistics.

        Calculates game duration, winner, and prints relevant information.
        """
    def end_game(self):       
        self.game_end_time = time.time()
        game_over = f"Game over!\nCongratulations to the winner: {self.winnerName}\n"
        game_end_datetime = datetime.fromtimestamp(self.game_end_time)
        game_start_datetime = datetime.fromtimestamp(self.game_start_time)
        game_total_time = game_end_datetime - game_start_datetime
        # Extract hours, minutes, and seconds from the game duration
        hours = game_total_time.seconds // 3600
        minutes = (game_total_time.seconds % 3600) // 60
        seconds = game_total_time.seconds % 60
        #print(f"{Bcolors.HEADER}Game over!\n" + Bcolors.ENDC)

        for client in self.clients:
            sock = client.client_socket
            try:
                sock.sendall(game_over.encode())
            except Exception:
                print("exeption")
                pass

        time.sleep(4)
        for client in self.clients:
            try:
                client.client_socket.close()
            except Exception as e:
                pass
        self.server_socket.close()
       # print(game_over)
        print(Bcolors.RED + "Game over!\n" + Bcolors.ENDC)
        print(Bcolors.DARKCYAN + f"Congratulations to the winner: {self.winnerName}\n" + Bcolors.ENDC)
        print(Bcolors.UNDERLINE + "Some statistics for the soul..." + Bcolors.ENDC)
        print(Bcolors.RED + "Game start time: " + game_start_datetime.strftime("%Y-%m-%d %H:%M:%S") + Bcolors.ENDC)
        print(Bcolors.RED + "Game end time: " + game_end_datetime.strftime("%Y-%m-%d %H:%M:%S") + Bcolors.ENDC)
        print(Bcolors.RED + "Game duration: " + f"{hours} hours, {minutes} minutes, {seconds} seconds" + Bcolors.ENDC)
        print(Bcolors.OKCYAN + "Players who participated:" + Bcolors.ENDC)
        for name in self.player_names:
            print(name)
        print(Bcolors.WARNING + f"Total rounds: {self.counter_rounds}\n" + Bcolors.ENDC)


"""
    Main function to run the server.

    Starts the server and runs it indefinitely.
    """
def main():
    while True:
        server = Server()
        server.run()
        time.sleep(1)


if __name__ == "__main__":
    main()
