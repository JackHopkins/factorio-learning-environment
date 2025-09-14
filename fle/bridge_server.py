# bridge_server.py
from fastapi import FastAPI, WebSocket
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from typing import Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

app = FastAPI()

# Add CORS middleware for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MCPBridge:
    def __init__(self):
        self.websocket_clients = []
        self.mcp_session: Optional[ClientSession] = None
        self.mcp_connected = False
        self.update_task = None
        self.mcp_connection_task = None

    async def connect_to_mcp(self):
        """Connect to the MCP server running in Claude Code"""
        try:
            # Connect to the standalone MCP server
            server_params = StdioServerParameters(
                command="python",
                args=["fle_mcp_server.py"],
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    self.mcp_session = session
                    await session.initialize()
                    self.mcp_connected = True
                    print("Connected to MCP server successfully")
                    
                    # Keep the connection alive
                    while self.mcp_connected:
                        await asyncio.sleep(1)
                        
        except Exception as e:
            print(f"Error connecting to MCP server: {e}")
            self.mcp_connected = False

    async def stream_updates(self):
        """Stream updates to all connected clients"""
        while True:
            try:
                if self.mcp_session and self.mcp_connected:
                    # Call the get_game_state tool
                    result = await self.mcp_session.call_tool(
                        "get_game_state",
                        arguments={}
                    )
                    
                    # Send to all connected WebSocket clients
                    disconnected = []
                    for client in self.websocket_clients:
                        try:
                            await client.send_json(result)
                        except:
                            disconnected.append(client)
                    
                    # Remove disconnected clients
                    for client in disconnected:
                        self.websocket_clients.remove(client)
                        
                await asyncio.sleep(0.5)  # Update every 500ms
            except Exception as e:
                print(f"Error streaming updates: {e}")
                await asyncio.sleep(1)


bridge = MCPBridge()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    bridge.websocket_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    finally:
        bridge.websocket_clients.remove(websocket)


@app.on_event("startup")
async def startup_event():
    """Start MCP connection and update streaming on server startup"""
    # Start MCP connection in background
    bridge.mcp_connection_task = asyncio.create_task(bridge.connect_to_mcp())
    # Start update streaming in background  
    bridge.update_task = asyncio.create_task(bridge.stream_updates())
    print("Bridge server started - connecting to MCP...")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on server shutdown"""
    bridge.mcp_connected = False
    if bridge.update_task:
        bridge.update_task.cancel()
    if bridge.mcp_connection_task:
        bridge.mcp_connection_task.cancel()


@app.get("/status")
async def get_status():
    """Get connection status"""
    return {
        "mcp_connected": bridge.mcp_connected,
        "websocket_clients": len(bridge.websocket_clients),
    }


@app.get("/stream")
async def stream_sse():
    """Server-Sent Events endpoint"""

    async def generate():
        while True:
            try:
                if bridge.mcp_session and bridge.mcp_connected:
                    state = await bridge.mcp_session.call_tool("get_game_state")
                    yield f"data: {json.dumps(state)}\n\n"
                else:
                    yield f"data: {json.dumps({'error': 'MCP not connected'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(generate(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)