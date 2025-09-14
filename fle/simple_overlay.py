#!/usr/bin/env python3
"""
Simplified overlay that connects to the bridge server to display Factorio game state.
This version focuses on just displaying the data from the MCP server.
"""

import asyncio
import json
import websocket
import threading
from nicegui import ui
from typing import Dict, Any, Optional

class SimpleOverlay:
    def __init__(self, bridge_url: str = "ws://localhost:8000/ws"):
        self.bridge_url = bridge_url
        self.ws = None
        self.latest_state = None
        self.connected = False
        
        # UI elements
        self.status_label = None
        self.score_label = None
        self.inventory_label = None
        self.entities_label = None
        self.position_label = None
        self.tick_label = None
        
    def connect_to_bridge(self):
        """Connect to the bridge server via WebSocket"""
        def on_message(ws, message):
            try:
                self.latest_state = json.loads(message)
                self.connected = True
            except Exception as e:
                print(f"Error parsing message: {e}")
        
        def on_error(ws, error):
            print(f"WebSocket error: {error}")
            self.connected = False
            
        def on_close(ws):
            print("WebSocket closed")
            self.connected = False
            
        def on_open(ws):
            print("Connected to bridge server")
            self.connected = True
        
        self.ws = websocket.WebSocketApp(
            self.bridge_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        # Run WebSocket in background thread
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
    def update_display(self):
        """Update UI with latest game state"""
        if not self.latest_state or "error" in self.latest_state:
            return
            
        try:
            # Update status
            self.status_label.set_text("🟢 Connected" if self.connected else "🔴 Disconnected")
            
            # Update score
            score = self.latest_state.get("score", 0)
            self.score_label.set_text(f"Score: {score:.2f}")
            
            # Update tick
            tick = self.latest_state.get("game_tick", 0)
            self.tick_label.set_text(f"Tick: {tick:,}")
            
            # Update position
            position = self.latest_state.get("position", {})
            if isinstance(position, dict):
                x = position.get("x", 0)
                y = position.get("y", 0)
                self.position_label.set_text(f"Position: ({x:.1f}, {y:.1f})")
            else:
                self.position_label.set_text(f"Position: {position}")
            
            # Update inventory
            inventory = self.latest_state.get("inventory", {})
            if inventory:
                inv_items = []
                for item, count in sorted(inventory.items(), key=lambda x: x[1], reverse=True)[:10]:
                    inv_items.append(f"{item}: {count}")
                self.inventory_label.set_text("\n".join(inv_items))
            else:
                self.inventory_label.set_text("Empty")
                
            # Update entities count
            entities = self.latest_state.get("entities", [])
            if isinstance(entities, list):
                self.entities_label.set_text(f"Entities: {len(entities)}")
            else:
                self.entities_label.set_text("Entities: N/A")
                
        except Exception as e:
            print(f"Error updating display: {e}")
    
    def create_ui(self):
        """Create the overlay UI"""
        with ui.card().classes('w-96 p-4 bg-gray-800 text-white'):
            ui.label('Factorio MCP Overlay').classes('text-xl font-bold mb-4')
            
            self.status_label = ui.label('🔴 Disconnected').classes('mb-2')
            
            # Game info
            with ui.column().classes('gap-2'):
                self.score_label = ui.label('Score: 0.00')
                self.tick_label = ui.label('Tick: 0')
                self.position_label = ui.label('Position: (0, 0)')
                self.entities_label = ui.label('Entities: 0')
            
            ui.separator()
            
            # Inventory
            ui.label('Top Inventory Items:').classes('mt-2 font-bold')
            self.inventory_label = ui.label('Empty').classes('text-sm font-mono')
            
        # Set up periodic updates
        ui.timer(0.1, self.update_display)
        
        # Connect to bridge on startup
        ui.timer(1.0, lambda: self.connect_to_bridge(), once=True)


def main():
    """Main entry point"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--bridge-url', default='ws://localhost:8000/ws', 
                       help='Bridge server WebSocket URL')
    parser.add_argument('--port', type=int, default=8081, help='Overlay UI port')
    args = parser.parse_args()
    
    overlay = SimpleOverlay(bridge_url=args.bridge_url)
    
    @ui.page('/')
    def index():
        overlay.create_ui()
    
    print(f"Starting overlay on http://localhost:{args.port}")
    print(f"Connecting to bridge at {args.bridge_url}")
    print("\nMake sure to:")
    print("1. Start the bridge server: python fle/simple_bridge.py")
    print("2. Run MCP commands in Claude Code to generate game state updates")
    
    ui.run(port=args.port, title='Factorio Overlay', dark=True)


if __name__ == "__main__":
    main()