import time
import subprocess
import urllib.request
import json
import socketio
import os
import sys

def main():
    print("Starting test Flask server...")
    # Start Flask server in a subprocess
    env = os.environ.copy()
    env["PORT"] = "5005"
    env["FLASK_DEBUG"] = "false"
    env["AUTH_DISABLED"] = "true"   # bypass JWT verification in test mode
    env["SOCKETIO_ASYNC_MODE"] = "threading"  # use threading for test subprocess
    # Ensure PYTHONPATH includes the current directory so it can find backend module
    env["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Open a log file instead of using subprocess.PIPE to avoid buffer hangs
    log_file_path = os.path.join(os.path.dirname(__file__), "server_output.log")
    log_file = open(log_file_path, "w", encoding="utf-8")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "backend.app"],
        env=env,
        stdout=log_file,
        stderr=log_file,
        text=True
    )
    
    # Wait for server to start
    time.sleep(3.0)
    
    events_log = []
    
    # Initialize SocketIO client
    sio = socketio.Client()
    
    session_id = "test-session-999"
    
    @sio.on('connect')
    def on_connect():
        print("Connected to WebSocket server.")
        sio.emit('join_session', {'session_id': session_id})
        
    @sio.on('join_response')
    def on_join(data):
        print(f"Joined session room: {data}")
        
        # Once joined, trigger the planning endpoint
        print("Triggering trip planner API POST request...")
        post_data = json.dumps({
            "user_text": "I have $500 to spend on a trip to Japan",
            "session_id": session_id
        }).encode('utf-8')
        
        req = urllib.request.Request(
            "http://localhost:5005/api/plan-trip",
            data=post_data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer dev-token',   # bypassed when AUTH_DISABLED=true
            }
        )
        try:
            with urllib.request.urlopen(req) as response:
                resp_data = json.loads(response.read().decode('utf-8'))
                print(f"API Trigger Response: {resp_data}")
        except Exception as e:
            print(f"Error triggering API: {e}")
            sio.disconnect()

    @sio.on('outbound_flight_locked')
    def on_outbound(data):
        print(f"Received outbound_flight_locked: {data}")
        events_log.append({"event": "outbound_flight_locked", "data": data})

    @sio.on('inbound_flight_locked')
    def on_inbound(data):
        print(f"Received inbound_flight_locked: {data}")
        events_log.append({"event": "inbound_flight_locked", "data": data})

    @sio.on('hotel_locked')
    def on_hotel(data):
        print(f"Received hotel_locked: {data}")
        events_log.append({"event": "hotel_locked", "data": data})

    @sio.on('itinerary_locked')
    def on_itinerary(data):
        print(f"Received itinerary_locked: {data}")
        events_log.append({"event": "itinerary_locked", "data": data})

    @sio.on('item_swapped')
    def on_swapped(data):
        print(f"Received item_swapped broadcast event: {data}")
        events_log.append({"event": "item_swapped", "data": data})
        # After confirming swap was broadcasted, we can disconnect
        sio.disconnect()

    @sio.on('plan_completed')
    def on_completed(data):
        print(f"Received plan_completed: {data}")
        events_log.append({"event": "plan_completed", "data": data})
        
        # Test item swapping via HTTP POST
        print("Testing modular item swap endpoint...")
        swap_payload = json.dumps({
            "session_id": session_id,
            "item_type": "hotel",
            "option_index": 2  # Swap to Option 3: Hostel
        }).encode('utf-8')
        
        req = urllib.request.Request(
            "http://localhost:5005/api/swap-item",
            data=swap_payload,
            headers={'Content-Type': 'application/json'}
        )
        try:
            with urllib.request.urlopen(req) as response:
                resp_data = json.loads(response.read().decode('utf-8'))
                print(f"Swap Endpoint Response: {resp_data}")
        except Exception as e:
            print(f"Error testing swap API: {e}")
            sio.disconnect()

    try:
        sio.connect('http://localhost:5005')
        # Block until disconnected (e.g. by on_completed)
        sio.wait()
    except Exception as e:
        print(f"SocketIO Client Error: {e}")
    finally:
        # Clean up server
        print("Terminating server process...")
        server_process.terminate()
        try:
            server_process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            server_process.kill()
            
        log_file.close()
        
        # Read and print the server logs for visibility
        try:
            with open(log_file_path, "r", encoding="utf-8") as f:
                server_logs = f.read()
            print("--- SERVER LOGS ---")
            print(server_logs)
        except Exception as e:
            print(f"Failed to read server logs: {e}")
        
        # Save output logs to websocket_emitter_log.json
        output_path = os.path.join(os.path.dirname(__file__), "websocket_emitter_log.json")
        with open(output_path, "w") as f:
            json.dump(events_log, f, indent=2)
        print(f"Saved WebSocket event log to: {output_path}")

if __name__ == "__main__":
    main()
