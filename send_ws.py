import asyncio
import websockets
import json

async def trigger():
    uri = "ws://127.0.0.1:8755/ws/test-session"
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({
            "type": "message",
            "content": "Hello! Please reply briefly."
        }))
        print("Message sent. Waiting for response...")
        while True:
            try:
                msg = await websocket.recv()
                print("Received:", msg)
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed by server.")
                break

asyncio.run(trigger())
