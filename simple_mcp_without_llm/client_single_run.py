import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

async def main():
    # Set up server parameters:
    # Here we launch the server using the command "python math_server.py".
    server_params = StdioServerParameters(
        command="python",
        args=["math_server.py"]
    )
    
    # Connect to the server using STDIO transport.
    async with stdio_client(server_params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            # Initialize the session (handshake with the server).
            await session.initialize()
            
            # Optionally, list the available tools.
            tools = await session.list_tools()
            tool_names = [tool.name for tool in tools.tools]
            print("Available tools:", tool_names)
            
            # Call the "add" tool with two numbers.
            result = await session.call_tool("add", {"a": 3, "b": 5})
            print("Result of add(3, 5):", result)

            # Call the "mult" tool with two numbers.
            result = await session.call_tool("mult", {"a": 2.5, "b": 5.1})
            print("Result of add(2.5, 5.1):", result)

if __name__ == "__main__":
    asyncio.run(main())