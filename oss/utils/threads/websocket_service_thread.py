import asyncio
import json
import os
import queue
import threading
import time

import websockets
from cherrypy.process import plugins

ws = []
metrics_queue = queue.Queue()
lat_queue = queue.Queue()


class WebSocketServiceThread(plugins.SimplePlugin):
    """Background thread that sends metrics to the websockets"""

    def __init__(self, bus):
        super().__init__(bus)
        self.t = None

    def start(self):
        """Plugin entrypoint"""

        self.t = threading.Thread(target=self.run_server)
        self.t.daemon = True
        self.t.start()

    def run_server(self):
        while True:
            try:
                asyncio.run(send_metrics())
            except Exception as e:
                print(f"Could not start WebSocket server: {e}")
                time.sleep(5)  # delay before attempting to restart


async def send_metrics():
    async with websockets.serve(receive_connection, "0.0.0.0", os.getenv("OSS_WS_PORT")):
        while True:
            try:
                if not metrics_queue.empty():
                    metrics = metrics_queue.get_nowait()
                    for websocket in ws:
                        await websocket.send(json.dumps(metrics))
                if not lat_queue.empty():
                    lat = lat_queue.get()
                    for websocket in ws:
                        await websocket.send(json.dumps(lat))
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Error in sending metrics: {e}")
                break  # exit the loop if there is an error


async def receive_connection(websocket, path):
    ws.append(websocket)
    try:
        async for message in websocket:
            pass
    except Exception as e:
        print(f"Error in WebSocket: {e}")
    finally:
        ws.remove(websocket)