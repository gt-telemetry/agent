"""
Lap Data Utilities
-----------------
Functions for formatting lap times, saving lap data locally or to backend.
"""

import os
import urllib3
import json
import queue
import threading
import logging
from typing import Optional, Any, List
from .backend import upload_lap, JWTValidationError, LapUploadError
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class LapSaveError(Exception):
    """Raised when saving a lap locally or remotely fails."""
    pass
class LapWriterError(Exception):
    """Raised when lap writer thread fails."""
    pass

def lap_writer(lap_write_queue: queue.Queue, jwt_token: Optional[str], backend_url: str, failure_event: threading.Event) -> None:
    """
    Worker thread for writing lap data either locally or to backend.
    Signals failure to the main thread via failure_event.

    Args:
        lap_write_queue (queue.Queue): Queue containing lap data and lap time.
        jwt_token (Optional[str]): JWT token for backend upload, None for local save.
        backend_url (str): Backend API URL.
        failure_event (threading.Event): Event to signal failure.
    """
    while not failure_event.is_set():
        try:
            lap_data, lap_time = lap_write_queue.get()
            if not jwt_token:
                logger.debug("Saving lap locally.")
                save_lap_locally(lap_data, lap_time)
            else:
                logger.debug("Uploading lap to backend.")
                save_lap(lap_data, lap_time, jwt_token, backend_url)
            lap_write_queue.task_done()
        except Exception as e:
            logger.error(f"Lap writer error: {e}")
            failure_event.set()
            return
        

def format_lap_time(lap_time_ms: int) -> str:
    """
    Formats lap time in milliseconds to MM-SS-MMM string.

    Args:
        lap_time_ms (int): Lap time in milliseconds.

    Returns:
        str: Formatted lap time string.
    """
    seconds = lap_time_ms // 1000
    ms = lap_time_ms % 1000
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}-{seconds:02d}-{ms:03d}"

def save_lap_locally(lap_packets: List[Any], lap_time_ms: int) -> None:
    """
    Saves lap data locally as a JSON file.

    Args:
        lap_packets (List[Any]): List of lap packet data.
        lap_time_ms (int): Lap time in milliseconds.
    """
    lap_time_str = format_lap_time(lap_time_ms)
    filename = f"lap_{lap_time_str}.json"
    try:
        os.makedirs("laps", exist_ok=True)
        with open(f"laps/{filename}", 'w') as f:
            f.write(json.dumps(lap_packets, indent=2))
        print(f"Lap {filename} saved locally.")
    except Exception as e:
        raise LapSaveError(f"Error saving lap locally: {e}")

def save_lap(lap_packets: List[Any], lap_time_ms: int, jwt_token: str, backend_url: str) -> None:
    """
    Uploads lap data to backend API.

    Args:
        lap_packets (List[Any]): List of lap packet data.
        lap_time_ms (int): Lap time in milliseconds.
        jwt_token (str): JWT token for authentication.
        backend_url (str): Backend API URL.

    Raises:
        RuntimeError: If upload fails or JWT token is missing.
    """
    lap_time_str = format_lap_time(lap_time_ms)
    filename = f"lap_{lap_time_str}.json"
    payload = {
        'lap_id': filename,
        'data': lap_packets
    }
    try:
        upload_lap(jwt_token, backend_url, payload)
        print(f"Lap {filename} uploaded to backend.")
    except JWTValidationError as e:
        raise JWTValidationError(f"Invalid JWT token: {e}")
    except LapUploadError as e:
        raise LapUploadError(f"Lap upload error: {e}")
    except Exception as e:
        raise LapSaveError(f"Failed to upload lap: {e}")
