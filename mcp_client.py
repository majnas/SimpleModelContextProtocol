import socket
import json
import time

def test_client():
    host = '127.0.0.1'
    port = 65433  # Connect directly to host for testing
    
    # Create test data
    data = {
        "function": "add",
        "params": {"a": 5, "b": 3}
    }
    
    # Connect to server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.connect((host, port))
            print("Connected to host")
            
            # Send data with proper encoding
            message = json.dumps(data)
            print(f"Sending: {message}")
            sock.sendall(message.encode('utf-8'))
            
            # Wait for response
            time.sleep(0.5)
            
            # Receive response
            response = sock.recv(1024).decode('utf-8')
            print(f"Raw response: {response}")
            
            if response:
                result = json.loads(response)
                print(f"Result: {result}")
            else:
                print("No response received")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_client()