# server.py
import mcp

def server_example():
    # Create server forwarding to host
    server = mcp.Server('localhost', 8000)
    server.connect_to_host('localhost', 8001)
    server.start()

if __name__ == "__main__":
    server_example()