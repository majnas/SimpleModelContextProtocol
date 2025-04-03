import socket
import json
import threading
import signal
import sys

def handle_client(conn, addr, host_address):
    print(f"Connected by {addr}")
    try:
        data = conn.recv(1024).decode('utf-8')
        if not data:
            print(f"Empty data received from {addr}")
            conn.close()
            return
            
        request = json.loads(data)
        
        # Forward request to MCP host
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as host_sock:
            host_sock.connect(host_address)
            host_sock.sendall(data.encode('utf-8'))
            
            # Get response from host
            host_response = host_sock.recv(1024).decode('utf-8')
            if host_response:
                conn.sendall(host_response.encode('utf-8'))
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        conn.close()

def mcp_server():
    host = '127.0.0.1'
    port = 65432
    host_address = ('127.0.0.1', 65433)  # MCP host address
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen()
        print(f"Server listening on {host}:{port}")
        
        def signal_handler(sig, frame):
            print("\nShutting down server...")
            server.close()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        
        while True:
            conn, addr = server.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr, host_address))
            client_thread.start()

if __name__ == "__main__":
    mcp_server()