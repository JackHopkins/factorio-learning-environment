#!/usr/bin/env python3
"""
Simple bridge server that polls the MCP server for game state updates.
This version uses a shared file or direct API calls to communicate with the MCP server.
"""

from fastapi import FastAPI, WebSocket
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import os
from typing import Optional, Dict, Any
from pathlib import Path

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared state file location
STATE_FILE = Path("/tmp/factorio_game_state.json")
STATE_FILE.parent.mkdir(exist_ok=True)


class SimpleBridge:
    def __init__(self):
        self.websocket_clients = []
        self.last_state: Optional[Dict[str, Any]] = None
        self.update_task = None

    def read_game_state(self) -> Optional[Dict[str, Any]]:
        """Read game state from shared file"""
        try:
            if STATE_FILE.exists():
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error reading state file: {e}")
        return None

    async def stream_updates(self):
        """Stream updates to all connected clients"""
        while True:
            try:
                # Read current game state
                state = self.read_game_state()
                
                if state and state != self.last_state:
                    self.last_state = state
                    
                    # Send to all connected WebSocket clients
                    disconnected = []
                    for client in self.websocket_clients:
                        try:
                            await client.send_json(state)
                        except:
                            disconnected.append(client)
                    
                    # Remove disconnected clients
                    for client in disconnected:
                        self.websocket_clients.remove(client)
                        
                await asyncio.sleep(0.1)  # Poll every 100ms
            except Exception as e:
                print(f"Error streaming updates: {e}")
                await asyncio.sleep(1)


bridge = SimpleBridge()


@app.on_event("startup")
async def startup_event():
    """Start update streaming on server startup"""
    bridge.update_task = asyncio.create_task(bridge.stream_updates())
    print("Simple bridge server started - watching for game state updates...")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on server shutdown"""
    if bridge.update_task:
        bridge.update_task.cancel()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    bridge.websocket_clients.append(websocket)
    
    # Send current state immediately
    state = bridge.read_game_state()
    if state:
        await websocket.send_json(state)
    
    try:
        while True:
            await websocket.receive_text()
    finally:
        if websocket in bridge.websocket_clients:
            bridge.websocket_clients.remove(websocket)


@app.get("/state")
async def get_current_state():
    """Get current game state"""
    state = bridge.read_game_state()
    if state:
        return JSONResponse(state)
    return JSONResponse({"error": "No game state available"}, status_code=404)


@app.get("/status")
async def get_status():
    """Get server status"""
    return {
        "websocket_clients": len(bridge.websocket_clients),
        "has_state": bridge.last_state is not None,
        "state_file": str(STATE_FILE),
        "state_file_exists": STATE_FILE.exists()
    }


@app.post("/update")
async def update_state(state: Dict[str, Any]):
    """Manual endpoint to update game state (for testing)"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/stream")
async def stream_sse():
    """Server-Sent Events endpoint"""
    
    async def generate():
        last_sent = None
        while True:
            try:
                state = bridge.read_game_state()
                if state and state != last_sent:
                    last_sent = state
                    yield f"data: {json.dumps(state)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            await asyncio.sleep(0.1)

    return StreamingResponse(generate(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    print(f"Starting simple bridge server...")
    print(f"State file location: {STATE_FILE}")
    print(f"WebSocket endpoint: ws://localhost:8000/ws")
    print(f"SSE endpoint: http://localhost:8000/stream")
    print(f"Status endpoint: http://localhost:8000/status")
    uvicorn.run(app, host="0.0.0.0", port=8000)