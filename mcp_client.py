# client.py
import mcp

def client_example():
    # Create client connection to server
    client = mcp.Client('localhost', 8000)
    
    # Call remote function
    result = client.call('add', a=5, b=3)
    print(f"Result: {result}")
    
    # Call LLM function
    response = client.call('ask_llm', prompt="What is machine learning?")
    print(f"LLM says: {response}")

if __name__ == "__main__":
    client_example()