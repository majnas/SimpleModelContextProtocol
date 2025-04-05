# host.py
import mcp
import openai

def add(a, b):
    return a + b

def ask_llm(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def host_example():
    # Initialize OpenAI
    # openai.api_key = "your-api-key-here"  # Replace with your actual OpenAI API key!
    
    # Create host and register functions
    host = mcp.McpHost('localhost', 8001) #changed to McpHost
    host.register_function('add', add)
    host.register_function('ask_llm', ask_llm)
    host.start()

if __name__ == "__main__":
    host_example()