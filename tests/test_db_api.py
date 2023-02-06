from io import StringIO
from admin import *
import unittest
import pytest
import sys

class FlaskrTestCase(unittest.TestCase):
    conn = None
    cursor = None

    @pytest.fixture(autouse=True)
    def capsys(self, capsys):
        """Capsys hook into this class"""
        self.capsys = capsys

    # set up a new db for per test
    def setUp(self):
        self.conn = connect_db()
        self.cursor = self.conn.cursor()
        init_db(self.conn, self.cursor)
        self.orig_stdin = sys.stdin

    # destroy tables
    def tearDown(self):
        delete_tables(self.conn, self.cursor)
        self.conn.close()
        sys.stdin = self.orig_stdin

    
    # test cases
    def test_task_add(self):

        uuid = "testUUID123"
       
        # add task
        test_cli = CLI(self.conn,self.cursor)
        test_cli.add_task(uuid, "whoami")
        captured = self.capsys.readouterr()
        
        #Task added for testUUID
        assert "Task added for testUUID123" in captured.out
        self.conn.commit()

        test_cli.do_show(f"task {uuid}")
        captured = self.capsys.readouterr()
        
        assert "testUUID123 whoami" in captured.out

    def test_task_add_all(self):

        # register agents
        uuid1 = "testUUID1"
        uuid2 = "testUUID2"
        uuid3 = "testUUID3"

        test_cli = CLI(self.conn,self.cursor)

        test_cli.add_agent(uuid1, "linux", "192.168.1.1")
        test_cli.add_agent(uuid2, "linux", "192.168.1.1")
        test_cli.add_agent(uuid3, "windows", "192.168.1.1")        
       
        # add task
        
        test_cli.do_task("add all c2-shell id")
        captured = self.capsys.readouterr()
        
        #Task added for testUUID
        assert "\x1b[92mTask added for testUUID1\x1b[0m\n\x1b[92mTask added for testUUID2\x1b[0m\n\x1b[92mTask added for testUUID3\x1b[0m\n" == captured.out
        #self.conn.commit()

        test_cli.do_show(f"task all")
        captured = self.capsys.readouterr()
        
        assert "testUUID1 c2-shell id\ntestUUID2 c2-shell id\ntestUUID3 c2-shell id\n" == captured.out    


    def test_task_add_uuid(self):

        # register agents
        uuid1 = "testUUID1"
        #uuid2 = "testUUID2"
        #uuid3 = "testUUID3"

        test_cli = CLI(self.conn,self.cursor)

        test_cli.add_agent(uuid1, "linux", "192.168.1.1")
        #test_cli.add_agent(uuid2, "linux", "192.168.1.1")
        #test_cli.add_agent(uuid3, "windows", "192.168.1.1")        
       
        # add task
        
        test_cli.do_task(f"add {uuid1} c2-shell id")
        captured = self.capsys.readouterr()
        
        #Task added for testUUID
        assert "\x1b[92mTask added for testUUID1\x1b[0m\n" == captured.out
        #self.conn.commit()

        test_cli.do_show(f"task {uuid1}")
        captured = self.capsys.readouterr()
        
        assert "testUUID1 c2-shell id\n" == captured.out    


    def test_task_add_type_linux(self):

        # register agents
        uuid1 = "testUUID1"
        uuid2 = "testUUID2"
        uuid3 = "testUUID3"

        test_cli = CLI(self.conn,self.cursor)

        test_cli.add_agent(uuid1, "linux", "192.168.1.1")
        test_cli.add_agent(uuid2, "linux", "192.168.1.1")
        test_cli.add_agent(uuid3, "windows", "192.168.1.1")        
       
        # add task
        
        test_cli.do_task(f"add type=linux c2-shell id")
        captured = self.capsys.readouterr()
        
        #Task added for testUUID
        assert "\x1b[92mTask added for testUUID1\x1b[0m\n\x1b[92mTask added for testUUID2\x1b[0m\n" == captured.out
        #self.conn.commit()

        test_cli.do_show(f"task type=linux")
        captured = self.capsys.readouterr()
        
        assert "testUUID1 c2-shell id\ntestUUID2 c2-shell id\n" == captured.out    

        # confirm that only type=linux agents were changed
        test_cli.do_show(f"task type=windows")
        captured = self.capsys.readouterr()
        
        assert "" == captured.out    


    def test_task_add_type_linux(self):

        # register agents
        uuid1 = "testUUID1"
        uuid2 = "testUUID2"
        uuid3 = "testUUID3"

        test_cli = CLI(self.conn,self.cursor)

        test_cli.add_agent(uuid1, "linux", "192.168.1.1")
        test_cli.add_agent(uuid2, "windows", "192.168.1.1")
        test_cli.add_agent(uuid3, "windows", "192.168.1.1")        
       
        # add task
        
        test_cli.do_task(f"add type=windows c2-shell id")
        captured = self.capsys.readouterr()
        
        #Task added for testUUID
        assert "\x1b[92mTask added for testUUID2\x1b[0m\n\x1b[92mTask added for testUUID3\x1b[0m\n" == captured.out
        #self.conn.commit()

        test_cli.do_show(f"task type=windows")
        captured = self.capsys.readouterr()
        
        assert "testUUID2 c2-shell id\ntestUUID3 c2-shell id\n" == captured.out    

        # confirm that only type=linux agents were changed
        test_cli.do_show(f"task type=linux")
        captured = self.capsys.readouterr()
        
        assert "" == captured.out    


    def test_show_result_all(self):

        # register agents
        uuid1 = "testUUID1"
        uuid2 = "testUUID2"
        uuid3 = "testUUID3"

        test_cli = CLI(self.conn,self.cursor)

        test_cli.add_agent(uuid1, "linux", "192.168.1.1")
        test_cli.add_agent(uuid2, "windows", "192.168.1.1")
        test_cli.add_agent(uuid3, "windows", "192.168.1.1")        
       
        # add task
        
        test_cli.add_result(uuid1, "root")
        test_cli.add_result(uuid2, "root")
        test_cli.add_result(uuid3, "root")
        captured = self.capsys.readouterr()        

        test_cli.do_show(f"result all")
        captured = self.capsys.readouterr()
        
        assert "testUUID1 root\ntestUUID2 root\ntestUUID3 root\n" == captured.out    


    def test_show_result_type(self):

        # register agents
        uuid1 = "testUUID1"
        uuid2 = "testUUID2"
        uuid3 = "testUUID3"

        test_cli = CLI(self.conn,self.cursor)

        test_cli.add_agent(uuid1, "linux", "192.168.1.1")
        test_cli.add_agent(uuid2, "windows", "192.168.1.1")
        test_cli.add_agent(uuid3, "windows", "192.168.1.1")        
       
        # add task
        
        test_cli.add_result(uuid1, "root")
        #test_cli.add_result(uuid2, "root")
        #test_cli.add_result(uuid3, "root")
        captured = self.capsys.readouterr()        

        test_cli.do_show(f"result type=linux")
        captured = self.capsys.readouterr()
        
        assert "testUUID1 root\n" == captured.out    
        
        test_cli.do_show(f"result type=windows")
        captured = self.capsys.readouterr()
        
        assert "" == captured.out    


    def test_show_result_uuid(self):

        # register agents
        uuid1 = "testUUID1"
        uuid2 = "testUUID2"
        uuid3 = "testUUID3"

        test_cli = CLI(self.conn,self.cursor)

        test_cli.add_agent(uuid1, "linux", "192.168.1.1")
        test_cli.add_agent(uuid2, "windows", "192.168.1.1")
        test_cli.add_agent(uuid3, "windows", "192.168.1.1")        
       
        # add task
        
        test_cli.add_result(uuid1, "root")
        test_cli.add_result(uuid2, "kali")
        test_cli.add_result(uuid3, "commander")
        captured = self.capsys.readouterr()        

        test_cli.do_show(f"result {uuid1}")
        captured = self.capsys.readouterr()        
        assert "testUUID1 root\n" == captured.out    
        
        test_cli.do_show(f"result {uuid2}")
        captured = self.capsys.readouterr()        
        assert "testUUID2 kali\n" == captured.out    

        test_cli.do_show(f"result {uuid3}")
        captured = self.capsys.readouterr()        
        assert "testUUID3 commander\n" == captured.out    
        


    def test_task_delete_all(self):

        # register agents
        uuid1 = "testUUID1"
        uuid2 = "testUUID2"
        uuid3 = "testUUID3"

        test_cli = CLI(self.conn,self.cursor)

        test_cli.add_agent(uuid1, "linux", "192.168.1.1")
        test_cli.add_agent(uuid2, "linux", "192.168.1.1")
        test_cli.add_agent(uuid3, "windows", "192.168.1.1")        
       
        # add task
        
        test_cli.do_task("add all c2-shell id")
        captured = self.capsys.readouterr()
        
        #Task added for testUUID
        assert "\x1b[92mTask added for testUUID1\x1b[0m\n\x1b[92mTask added for testUUID2\x1b[0m\n\x1b[92mTask added for testUUID3\x1b[0m\n" == captured.out
        #self.conn.commit()

        test_cli.do_show(f"task all")
        captured = self.capsys.readouterr()        
        assert "testUUID1 c2-shell id\ntestUUID2 c2-shell id\ntestUUID3 c2-shell id\n" == captured.out    

        # delete all
        test_cli.do_task("delete all")
        captured = self.capsys.readouterr()        
        assert "OK!\n" == captured.out  

        test_cli.do_show(f"task all")
        captured = self.capsys.readouterr()        
        assert "" == captured.out  


        
    def test_task_delete_uuid(self):

        # register agents
        uuid1 = "testUUID1"
        uuid2 = "testUUID2"
        uuid3 = "testUUID3"

        test_cli = CLI(self.conn,self.cursor)

        test_cli.add_agent(uuid1, "linux", "192.168.1.1")
        test_cli.add_agent(uuid2, "linux", "192.168.1.1")
        test_cli.add_agent(uuid3, "windows", "192.168.1.1")        
       
        # add task
        
        test_cli.do_task("add all c2-shell id")
        captured = self.capsys.readouterr()
        
        #Task added for testUUID
        assert "\x1b[92mTask added for testUUID1\x1b[0m\n\x1b[92mTask added for testUUID2\x1b[0m\n\x1b[92mTask added for testUUID3\x1b[0m\n" == captured.out
        #self.conn.commit()

        test_cli.do_show(f"task all")
        captured = self.capsys.readouterr()        
        assert "testUUID1 c2-shell id\ntestUUID2 c2-shell id\ntestUUID3 c2-shell id\n" == captured.out    

        # delete all
        test_cli.do_task(f"delete {uuid1}")
        captured = self.capsys.readouterr()        
        assert "OK!\n" == captured.out  

        test_cli.do_show(f"task all")
        captured = self.capsys.readouterr()        
        assert "testUUID2 c2-shell id\ntestUUID3 c2-shell id\n" == captured.out  


    def test_task_delete_type(self):

        # register agents
        uuid1 = "testUUID1"
        uuid2 = "testUUID2"
        uuid3 = "testUUID3"

        test_cli = CLI(self.conn,self.cursor)

        test_cli.add_agent(uuid1, "linux", "192.168.1.1")
        test_cli.add_agent(uuid2, "linux", "192.168.1.1")
        test_cli.add_agent(uuid3, "windows", "192.168.1.1")        
       
        # add task
        
        test_cli.do_task("add all c2-shell id")
        captured = self.capsys.readouterr()
        
        #Task added for testUUID
        assert "\x1b[92mTask added for testUUID1\x1b[0m\n\x1b[92mTask added for testUUID2\x1b[0m\n\x1b[92mTask added for testUUID3\x1b[0m\n" == captured.out
        #self.conn.commit()

        test_cli.do_show(f"task all")
        captured = self.capsys.readouterr()        
        assert "testUUID1 c2-shell id\ntestUUID2 c2-shell id\ntestUUID3 c2-shell id\n" == captured.out    

        # delete all
        test_cli.do_task(f"delete type=linux")
        captured = self.capsys.readouterr()        
        assert "OK!\n" == captured.out  

        test_cli.do_show(f"task all")
        captured = self.capsys.readouterr()        
        assert "testUUID3 c2-shell id\n" == captured.out  


    def test_show_agent_all(self):

        # register agents
        uuid1 = "testUUID1"
        uuid2 = "testUUID2"
        uuid3 = "testUUID3"

        test_cli = CLI(self.conn,self.cursor)

        test_cli.add_agent(uuid1, "linux", "192.168.1.1")
        test_cli.add_agent(uuid2, "linux", "192.168.1.1")
        test_cli.add_agent(uuid3, "windows", "192.168.1.1")              

        test_cli.do_show(f"agent all")
        captured = self.capsys.readouterr()        
        assert "testUUID1 linux 192.168.1.1\ntestUUID2 linux 192.168.1.1\ntestUUID3 windows 192.168.1.1\n" == captured.out  


    def test_show_agent_uuid(self):

        # register agents
        uuid1 = "testUUID1"
        uuid2 = "testUUID2"
        uuid3 = "testUUID3"

        test_cli = CLI(self.conn,self.cursor)

        test_cli.add_agent(uuid1, "linux", "192.168.1.1")
        test_cli.add_agent(uuid2, "linux", "192.168.1.1")
        test_cli.add_agent(uuid3, "windows", "192.168.1.1")              

        test_cli.do_show(f"agent {uuid2}")
        captured = self.capsys.readouterr()        
        assert "testUUID2 linux 192.168.1.1\n" == captured.out  


    def test_show_agent_type(self):

        # register agents
        uuid1 = "testUUID1"
        uuid2 = "testUUID2"
        uuid3 = "testUUID3"

        test_cli = CLI(self.conn,self.cursor)

        test_cli.add_agent(uuid1, "linux", "192.168.1.1")
        test_cli.add_agent(uuid2, "linux", "192.168.1.1")
        test_cli.add_agent(uuid3, "windows", "192.168.1.1")              

        test_cli.do_show(f"agent type=linux")
        captured = self.capsys.readouterr()        
        assert "testUUID1 linux 192.168.1.1\ntestUUID2 linux 192.168.1.1\n" == captured.out  


    def test_find_active_agents(self):

        # register agents
        uuid1 = "testUUID1"
        uuid2 = "testUUID2"
        uuid3 = "testUUID3"

        test_cli = CLI(self.conn,self.cursor)

        test_cli.add_agent(uuid1, "linux", "192.168.1.1")
        test_cli.add_agent(uuid2, "linux", "192.168.1.1")
        test_cli.add_agent(uuid3, "windows", "192.168.1.1")              

        test_cli.do_show(f"agent all")

        #monkeypatch.setattr('builtins.input', lambda _: "Mark")

        
        captured = self.capsys.readouterr()        
        assert "testUUID1 linux 192.168.1.1\ntestUUID2 linux 192.168.1.1\ntestUUID3 windows 192.168.1.1\n" == captured.out 

        #test_cli.do_find("active agents") 
        # with mock.patch.object(__builtins__, 'input', lambda: 'Y'):
        sys.stdin = StringIO("Y")
        test_cli.do_find("active agents") 
        captured = self.capsys.readouterr()        
        assert "This will delete your database. Do you want to continue? (y/N):Deleted\n" == captured.out  

        test_cli.do_show(f"agent all")
        captured = self.capsys.readouterr()        
        assert "" == captured.out  