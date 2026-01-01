import asyncio
import websockets
import sys

async def test_ws():
    uri = "ws://127.0.0.1:8000/ws/test_report_id"
    print(f"Attempting connection to {uri}")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected successfully!")
            await websocket.send('{"test": "ping"}')
            print("Sent message.")
            # Wait a bit
            await asyncio.sleep(0.5)
            print("Closing...")
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_ws())
