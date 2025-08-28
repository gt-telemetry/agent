"""
BackendUtilities
-----------------
Functions for interacting with the backend API, and validating JWT tokens.
"""

import requests
import time
import threading
import logging

logger = logging.getLogger(__name__)

class SessionHeartbeatError(Exception):
    """Raised when session heartbeat fails or encounters an error."""
    pass

class JWTValidationError(Exception):
    """Raised when JWT token validation fails."""
    pass

class LapUploadError(Exception):
    """Raised when lap upload fails."""
    pass

def session_heartbeat_thread(jwt_token: str, backend_url: str, failure_event: threading.Event) -> None:
    """
    Sends periodic heartbeat to backend to keep session alive.
    Signals failure to the main thread via failure_event.

    Args:
        jwt_token (str): JWT token for authentication.
        backend_url (str): Backend API URL.
        failure_event (threading.Event): Event to signal failure.
    """
    while not failure_event.is_set():
        try:
            resp = requests.post(f"{backend_url}/session/heartbeat", headers={"Authorization": f"Bearer {jwt_token}"}, timeout=10, verify=False)
            if not resp.ok:
                failure_event.set()
                return
            logger.debug("Session heartbeat successful.")
            time.sleep(60)
        except Exception as e:
            failure_event.set()
            return
        

def validate_jwt_token(jwt_token: str, backend_url: str) -> bool:
    """
    Validates JWT token with backend API.

    Args:
        jwt_token (str): JWT token for authentication.
        backend_url (str): Backend API URL.

    Returns:
        bool: True if token is valid, False otherwise.
    """
    headers = {
        'Authorization': f'Bearer {jwt_token}'
    }
    try:
        logger.debug("Validating JWT token with backend.")
        resp = requests.get(f"{backend_url}/laps/", headers=headers, verify=False)
        resp.raise_for_status()
        return True
    except Exception as e:
        raise JWTValidationError(f"JWT token validation failed: {e}")

def upload_lap(jwt_token: str, backend_url: str, lap_data: dict) -> None:
    """
    Uploads a single lap to the backend API.

    Args:
        jwt_token (str): JWT token for authentication.
        backend_url (str): Backend API URL.
        lap_data (dict): Lap data to upload.

    Raises:
        RuntimeError: If upload fails or JWT token is missing.
    """
    if not jwt_token:
        raise JWTValidationError('A valid JWT token must be provided')
    headers = {
        'Authorization': f'Bearer {jwt_token}'
    }
    try:
        resp = requests.post(f"{backend_url}/laps", headers=headers, json=lap_data, verify=False)
        resp.raise_for_status()
        logger.debug("Lap uploaded successfully.")
    except Exception as e:
        raise LapUploadError(f"Failed to upload lap: {e}")
