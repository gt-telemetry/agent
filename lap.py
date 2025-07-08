import os
import json
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def format_lap_time(lap_time_ms):
    seconds = lap_time_ms // 1000
    ms = lap_time_ms % 1000
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}-{seconds:02d}-{ms:03d}"

def save_lap(lap_packets, lap_time_ms, jwt_token):
    lap_time_str = format_lap_time(lap_time_ms)
    filename = f"lap_{lap_time_str}.json"
    backend_url = os.environ.get('BACKEND_URL', 'https://localhost:8000')
    if not jwt_token:
        raise RuntimeError('A valid JWT token must be provided')
    payload = {
        'lap_id': filename,
        'data': lap_packets
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {jwt_token}'
    }
    try:
        resp = requests.post(f"{backend_url}/laps", headers=headers, json=payload, verify=False)
        resp.raise_for_status()
        print(f"Lap {filename} uploaded to backend.")
    except Exception as e:
        raise RuntimeError(f"Failed to upload lap {filename}: {e}")

def test_jwt_token(jwt_token):
    backend_url = os.environ.get('BACKEND_URL', 'https://localhost:8000')
    headers = {
        'Authorization': f'Bearer {jwt_token}'
    }
    try:
        resp = requests.get(f"{backend_url}/laps/", headers=headers, verify=False)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"JWT token validation failed: {e}")
        return False
