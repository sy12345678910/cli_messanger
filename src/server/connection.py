from dataclasses import dataclass
from fastapi import WebSocket

@dataclass
class ActiveClient:
    user_id: int
    username: str
    hard_id: str
    websocket: WebSocket
    
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[ActiveClient] = []

    async def connect(self, client: ActiveClient):
        if client not in self.active_connections:
            self.active_connections.append(client)

    async def disconnect(self, client: ActiveClient):
        if client in self.active_connections:
            self.active_connections.remove(client)

    async def send_message(self, message: str, client: ActiveClient):
        await client.websocket.send_text(message)

    async def broadcast(self, message: str):
        for client in list(self.active_connections):
            try:
                await client.websocket.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()