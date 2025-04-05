import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

async def chat_loop(session: ClientSession):
    """Run an interactive chat loop"""
    print("\nMCP Client Started!")
    print("Type your tool name or 'quit' to exit.")
    
    while True:
        try:
            query = input("\nEnter command (or 'quit' to exit): ").strip()
            
            if query.lower() == 'quit':
                print("Exiting chat loop.")
                break
            
            tools = await session.list_tools()
            tool_names = [tool.name for tool in tools.tools]
            print("Available tools:", tool_names)
            
            if query in tool_names:
                args = input(f"Enter arguments for {query} (JSON format): ")
                try:
                    import json
                    tool_args = json.loads(args)
                    result = await session.call_tool(query, tool_args)
                    print(f"\nResult: {result}")
                except json.JSONDecodeError:
                    print("Invalid JSON format. Please try again.")
            else:
                print("Unknown tool. Please enter a valid tool name.")
        
        except Exception as e:
            print(f"\nError: {str(e)}")

async def main():
    # Set up server parameters
    server_params = StdioServerParameters(
        command="python",
        args=["math_server.py"]
    )
    
    # Connect to the server using STDIO transport.
    async with stdio_client(server_params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            await chat_loop(session)

if __name__ == "__main__":
    asyncio.run(main())
