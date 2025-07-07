# Factorio MCP Server
from fle.env.protocols.mcp import mcp

# Command-line interface for the MCP server
if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="Factorio Learning Environment MCP Server"
    )
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "sse"],
        help="Transport mechanism to use (stdio or sse)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for SSE server (if using sse transport)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port for SSE server (if using sse transport)",
    )

    args = parser.parse_args()

    if args.transport == "stdio":
        print("Starting Factorio MCP server with stdio transport")
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        print(
            f"Starting Factorio MCP server with SSE transport on {args.host}:{args.port}"
        )
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        print(f"Unknown transport: {args.transport}")
        sys.exit(1)
