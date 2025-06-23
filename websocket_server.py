import asyncio
import websockets
import json
import os
from metro_simulation import MetroAutomata

class MetroServer:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        shp_path = os.path.join(current_dir, "stcmetro_shp", "stcmetro_shp", "STC_Metro_lineas_utm14n.shp")
        afluencia_path = os.path.join(current_dir, "data-2025-06-19.csv")
        
        self.automata = MetroAutomata(shp_path, afluencia_path)
        self.connected = set()

    async def notify_clients(self):
        if not self.connected:
            return
        
        self.automata.step()
        message = json.dumps({
            'type': 'update',
            'data': self.automata.get_current_state()
        })
        
        await asyncio.gather(
            *[client.send(message) for client in self.connected]
        )

    async def register(self, websocket):
        self.connected.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            self.connected.remove(websocket)

    async def ws_handler(self, websocket, path):
        await self.register(websocket)

async def main():
    server = MetroServer()
    
    async with websockets.serve(server.ws_handler, "localhost", 8765):
        while True:
            await server.notify_clients()
            await asyncio.sleep(30)  # Actualizar cada 30 segundos

if __name__ == "__main__":
    print("Iniciando servidor websocket en ws://localhost:8765")
    asyncio.run(main())
