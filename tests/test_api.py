import pytest
from admin import *
import base64

def test_register_route(client, init_database):

    response = client.post("/register", data={"type":"linux"})    
    assert len(response.text) == 32
    assert response.status_code == 200


def test_register_route_failure(client, del_database):

    response = client.post("/register", data={"type":"linux"})
    assert len(response.text) == 18
    assert response.text == "FailedRegistration"
    assert response.status_code == 200


def test_tasks_route_is_None(client, init_database):

    response = client.post("/register", data={"type":"linux"})    
    assert len(response.text) == 32
    assert response.status_code == 200

    response = client.get(f"/tasks/{response.text}")    
    assert len(response.text) == 0
    assert response.status_code == 200


def test_tasks_route_is_id(client):

    conn = sqlite3.connect('c2.db', timeout=10)
    cursor = conn.cursor()

    init_db(conn, cursor)

    response = client.post("/register", data={"type":"linux"})        
    assert len(response.text) == 32
    assert response.status_code == 200
    
    test_cli = CLI(conn,cursor)
    test_cli.add_task(response.text, "id")
    conn.commit()

    response = client.get(f"/tasks/{response.text}")    
    assert response.text == "aWQ="
    assert response.status_code == 200

    delete_tables(conn, cursor)


def test_results_route(client, capsys):

    # init db
    conn = sqlite3.connect('c2.db', timeout=10)
    cursor = conn.cursor()

    init_db(conn, cursor)

    # register
    response = client.post("/register", data={"type":"linux"})    
    assert len(response.text) == 32
    assert response.status_code == 200

    uuid = response.text
    
    # add task
    test_cli = CLI(conn,cursor)
    test_cli.add_task(response.text, "whoami")
    conn.commit()

    # read tasks
    response = client.get(f"/tasks/{uuid}")    
    assert response.text == "d2hvYW1p"
    assert response.status_code == 200

    # send results
    res_b64 = base64.b64encode("kali".encode("utf-8"))
    response = client.post(f"/results/{uuid}", data={"result":res_b64})        
    assert len(response.text) == 0
    assert response.status_code == 200

    test_cli.do_show(f"result {uuid}")
    captured = capsys.readouterr()
    assert "kali" in captured.out
    
    delete_tables(conn, cursor)    


def test_reregister_mechanism(client, capsys):

    # init db
    conn = sqlite3.connect('c2.db', timeout=10)
    cursor = conn.cursor()

    init_db(conn, cursor)

    # read tasks
    response = client.get(f"/tasks/dummyuuid")
    print(f"response len: {len(response.text)}")
    print(f"response: {response.text}")
    
    # validate that c2-register was sent
    assert response.text == "YzItcmVnaXN0ZXI="    
    assert response.status_code == 200

    # register
    response = client.post("/register", data={"type":"linux"})    
    print(f"response reg len: {len(response.text)}")
    print(f"response reg : {response.text}")
    assert len(response.text) == 32
    assert response.status_code == 200

    uuid = response.text
    
    # add task
    test_cli = CLI(conn,cursor)
    test_cli.add_task(response.text, "whoami")
    conn.commit()

    # read tasks
    response = client.get(f"/tasks/{uuid}")
    print(f"response len: {len(response.text)}")
    print(f"response: {uuid}")
    assert response.text == "d2hvYW1p"
    assert response.status_code == 200

    # send results
    res_b64 = base64.b64encode("kali".encode("utf-8"))
    response = client.post(f"/results/{uuid}", data={"result":res_b64})    
    print(f"response reg len: {len(response.text)}")
    print(f"response reg : {response.text}")
    assert len(response.text) == 0
    assert response.status_code == 200

    test_cli.do_show(f"result {uuid}")
    captured = capsys.readouterr()
    assert "kali" in captured.out
    
    delete_tables(conn, cursor)   