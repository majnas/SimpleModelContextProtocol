from mcp.server.fastmcp import FastMCP

# Create an MCP server.
mcp = FastMCP("SimpleMathServer")

# Define a tool named "add" that takes two integers and returns their sum.
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

# Define a tool named "mult" that takes two floats and returns their product.
@mcp.tool()
def mult(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b

if __name__ == "__main__":
    mcp.run()
