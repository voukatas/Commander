import pytest
from c2_server import create_app
from admin import *

#export PYTHONPATH="/home/kali/Documents/projects/Commander/"

@pytest.fixture()
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
    })

    # other setup can go here

    yield app

    # clean up / reset resources here


@pytest.fixture()
def client(app):
    return app.test_client()
    


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def init_database():
    # Create the database and the database table
    conn = sqlite3.connect('c2.db', timeout=10)
    cursor = conn.cursor()
    init_db(conn, cursor)

    # # Insert user data

    yield  # this is where the testing happens!

    delete_tables(conn, cursor)


@pytest.fixture(scope='function')
def del_database():
    # Create the database and the database table
    conn = sqlite3.connect('c2.db', timeout=10)
    cursor = conn.cursor()
    #init_db(conn, cursor)

    # # Insert user data

    delete_tables(conn, cursor)

    yield  # this is where the testing happens!

    init_db(conn, cursor)
    