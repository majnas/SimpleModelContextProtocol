import asyncio
from typing import Optional, Dict, List
from contextlib import AsyncExitStack
import json
import sys
import argparse
import glob
import os
from icecream import ic

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize OpenAI client
        self.openai = OpenAI()
        # Dictionary to store sessions and transports for each server
        self.sessions: Dict[str, ClientSession] = {}
        self.transports: Dict[str, tuple] = {}
        self.exit_stack = AsyncExitStack()


    async def connect_docker_server(self, server_name: str, docker_args: List[str]):
        """
        Connect to an MCP server that’s packaged as a Docker image
        over STDIO (no HTTP ports).
        """
        from mcp.client.stdio import stdio_client

        # Build the StdioServerParameters for Docker
        params = StdioServerParameters(
            command="docker",
            args=docker_args,
            env=None
        )
        # Launch and hook up STDIO transport → session
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(params))
        stdio, protocol = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(stdio, protocol))
        await session.initialize()

        self.sessions[server_name] = session
        self.transports[server_name] = (stdio, protocol)

        # sanity check: list tools
        resp = await session.list_tools()
        print(f"🔌 Connected to Docker server “{server_name}” with tools:",
            [t.name for t in resp.tools])


    async def connect_to_server(self, server_name: str, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_name: Unique identifier for the server (e.g., 'math', 'weather')
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError(f"Server script {server_script_path} must be a .py or .js file")

        if not os.path.exists(server_script_path):
            raise FileNotFoundError(f"Server script {server_script_path} does not exist")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        # Set up stdio transport and session
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio, protocol = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(stdio, protocol))

        # Initialize session
        await session.initialize()

        # Store session and transport
        self.sessions[server_name] = session
        self.transports[server_name] = (stdio, protocol)

        # List available tools
        response = await session.list_tools()
        tools = response.tools
        print(f"\nConnected to {server_name} server ({server_script_path}) with tools:", [tool.name for tool in tools])

    async def get_all_tools(self) -> List[Dict]:
        """Aggregate tools from all connected servers"""
        available_tools = []
        for server_name, session in self.sessions.items():
            response = await session.list_tools()
            for tool in response.tools:
                # Include server_name in tool metadata to route calls later
                available_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                        "server_name": server_name  # Custom metadata
                    }
                })
        return available_tools

    async def process_query(self, query: str) -> str:
        """Process a query using GPT-4o and available tools"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        # Get all available tools from connected servers
        available_tools = await self.get_all_tools()

        # Initial OpenAI API call
        response = self.openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1000,
            tools=available_tools if available_tools else None
        )

        # Process response and handle tool calls
        tool_results = []
        final_text = []

        # Get the first message
        message = response.choices[0].message

        if message.content:
            final_text.append(message.content)

        if message.tool_calls:
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                # Find the server that owns this tool
                server_name = None
                for tool in available_tools:
                    if tool["function"]["name"] == tool_name:
                        server_name = tool["function"]["server_name"]
                        break

                if server_name is None:
                    final_text.append(f"[Error: Tool {tool_name} not found]")
                    continue

                # Execute tool call on the appropriate session
                session = self.sessions[server_name]
                result = await session.call_tool(tool_name, tool_args)
                tool_results.append({"call": tool_name, "result": result})
                final_text.append(f"[Calling tool {tool_name} on {server_name} server with args {tool_args}]")

                # Continue conversation with tool results
                messages.append({
                    "role": "assistant",
                    "content": message.content if message.content else None,
                    "tool_calls": [tool_call.model_dump()]  # Using model_dump() to avoid deprecation warning
                })
                messages.append({
                    "role": "tool",
                    "content": result.content,
                    "tool_call_id": tool_call.id
                })

                # Get next response from GPT-4o
                response = self.openai.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    max_tokens=1000,
                    tools=available_tools if available_tools else None
                )

                final_text.append(response.choices[0].message.content)

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main(args):
    # Handle server argument
    server_arg = args.server
    print(server_arg)

    # Initialize client
    client = MCPClient()

    try:
        if server_arg.endswith(':docker'):
            # e.g. "filesystem:docker"
            server_name, _ = server_arg.split(':', 1)

            current_directory = os.getcwd()
            data_dir = os.path.join(current_directory, "data_dir_to_mount")
            cfg_dir = os.path.join(current_directory, "config_dir_to_mount")

            docker_args = [
                "run", "-i", "--rm",
                "--mount", f"type=bind,src={data_dir},dst=/projects/Data",
                "--mount", f"type=bind,src={cfg_dir},dst=/projects/Config,ro",
                "mcp/filesystem",
                "/projects"
            ]

            await client.connect_docker_server(server_name, docker_args)

        elif (server_arg.endswith('.py') or server_arg.endswith('.js')) and os.path.isfile(server_arg):
            # your existing Python/Node script handler…
            server_name = os.path.splitext(os.path.basename(server_arg))[0]
            await client.connect_to_server(server_name, server_arg)
        elif '*' in server_arg:
            # Glob pattern
            pattern = server_arg
            server_files = glob.glob(pattern)
            if not server_files:
                print(f"No server scripts found matching pattern: {pattern}")
                sys.exit(1)
            for server_path in server_files:
                if server_path.endswith('.py'):
                    server_name = os.path.splitext(os.path.basename(server_path))[0]
                    await client.connect_to_server(server_name, server_path)
        else:
            print(f"Invalid server argument: {server_arg}. Must be a .py file or a glob pattern like ./*_mcp_server.py")
            sys.exit(1)

        # Start the chat loop
        await client.chat_loop()

    finally:
        await client.cleanup()

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="MCP Client for connecting to server scripts")
    parser.add_argument(
        "--server",
        required=True,
        help="Path to server script (e.g., math_mcp_server.py) or glob pattern (e.g., ./*_mcp_server.py)"
    )
    args = parser.parse_args()

    asyncio.run(main(args))