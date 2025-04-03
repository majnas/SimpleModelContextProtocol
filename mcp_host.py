import socket
import json
import threading
import openai
import signal
import sys

def add(a, b):
    return a + b

def process_with_llm(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def handle_request(conn, addr):
    print(f"Connected by {addr}")
    try:
        data = conn.recv(1024).decode('utf-8')
        if not data:
            print(f"Empty data received from {addr}")
            conn.close()
            return
            
        request = json.loads(data)
        
        result = None
        
        # Process the request based on function
        if request["function"] == "add":
            result = add(request["params"]["a"], request["params"]["b"])
        elif request["function"] == "ask_llm":
            result = process_with_llm(request["params"]["prompt"])
        
        # Send response back
        response = {"result": result}
        conn.sendall(json.dumps(response).encode('utf-8'))
    except Exception as e:
        print(f"Error handling request from {addr}: {e}")
        # Send error response
        error_response = {"error": str(e)}
        try:
            conn.sendall(json.dumps(error_response).encode('utf-8'))
        except:
            pass
    finally:
        conn.close()

def mcp_host():
    openai.api_key = "your-api-key-here"
    
    host = '127.0.0.1'
    port = 65433
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen()
        print(f"MCP Host listening on {host}:{port}")
        
        def signal_handler(sig, frame):
            print("\nShutting down server...")
            server.close()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        
        while True:
            conn, addr = server.accept()
            client_thread = threading.Thread(target=handle_request, args=(conn, addr))
            client_thread.start()

if __name__ == "__main__":
    mcp_host()