"""
GT7 Telemetry Agent
-------------------
Main agent script for collecting and saving GT7 telemetry laps.
Handles session management, lap writing, and communication with backend or local storage.
"""

import argparse
import socket
import sys
import time
import threading
import queue
import getpass
import re
import logging
from typing import Optional, Any
from gt7_processing import GT7_UDP_PORT, GT7_HEARTBEAT_PORT, HEARTBEAT_INTERVAL, decrypt_packet, GT7Packet, send_heartbeat, GT7HeartbeatError
from common.lap import lap_writer, LapWriterError
from common.backend import test_jwt_token, session_heartbeat_thread, JWTValidationError, SessionHeartbeatError



BACKEND_URL = 'https://api.gt-telemetry.com'


def main() -> None:
    """
    Main entry point for GT7 telemetry agent.
    Handles argument parsing, session setup, socket communication, and lap recording.
    """
    parser = argparse.ArgumentParser(description="GT7 Telemetry Lap Saver")
    parser.add_argument('--ps_ip', help='PlayStation IP address')
    parser.add_argument('--track', action='store_true', help='Record only positional value to save track layout')
    parser.add_argument('--local', action='store_true', help='Store laps locally instead of uploading to GT Telemetry')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    # Configure logging for debug only if verbose is set
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.CRITICAL,
        format='[%(levelname)s] %(name)s:\t\t %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Prompt for PlayStation IP if not provided
    if not args.ps_ip:
        while True:
            try:
                ps_ip: str = input('Enter PlayStation IPv4 address: ')
            except (KeyboardInterrupt, EOFError):
                print("Exiting...")
                sys.exit(0)
            # Simple IPv4 validation
            if re.match(r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', ps_ip):
                break
            else:
                print("Invalid IPv4 address format. Please try again.")
    else:
        ps_ip: str = args.ps_ip

    local_ip: str = "0.0.0.0"

    # Set up UDP socket for listening
    try:
        logger.debug(f"Setting up receive socket on port {GT7_UDP_PORT}")
        recv_sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        recv_sock.bind(("", GT7_UDP_PORT))
    except Exception as e:
        print(f"Error binding receive socket")
        logger.debug(e)
        sys.exit(1)

    # Set up UDP socket for sending heartbeats, bind to local_ip
    try:
        logger.debug(f"Setting up send socket on port {GT7_HEARTBEAT_PORT}")
        send_sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_sock.bind((local_ip, 0))  # Bind to local IP and ephemeral port
    except Exception as e:
        print(f"Error binding send socket")
        logger.debug(e)
        sys.exit(1)

    last_heartbeat: float = 0
    current_lap: list[Any] = []
    lap_number: Optional[int] = None
    recording_started: bool = False

    if not args.local:
        # Prompt for local or remote lap saving method
        while True:
            try:
                save_method: str = input('Do you want to save your laps locally [l] or remotely on GT Telemetry App [r]: ')
            except (KeyboardInterrupt, EOFError):
                print("Exiting...")
                sys.exit(0)
            if save_method.lower() == 'r':
                break
            elif save_method.lower() == 'l':
                break
            else:
                print("Invalid option. Please enter 'l' for local or 'r' for remote.")

        if save_method.lower() == 'r':
            # Prompt for JWT token at startup and test it
            while True:
                try:
                    jwt_token: str = getpass.getpass('Paste your JWT token (input hidden): ')
                    test_jwt_token(jwt_token, BACKEND_URL)
                    print("JWT token is valid.")
                    break
                except (KeyboardInterrupt, EOFError):
                    print("Exiting...")
                    sys.exit(0)
                except JWTValidationError as e:
                    print("Invalid JWT token. Please try again.")
                    logger.debug(e)
                except Exception as e:
                    print(f"Error occurred during JWT token validation")
                    logger.debug(e)
                    sys.exit(1)

            # --- Start session heartbeat thread with failure event ---
            logger.debug("Starting session heartbeat thread.")
            heartbeat_failure_event = threading.Event()
            heartbeat_thread = threading.Thread(target=session_heartbeat_thread, args=(jwt_token, BACKEND_URL, heartbeat_failure_event), daemon=True)
            heartbeat_thread.start()

        else:
            jwt_token = None
            print("Laps will be saved locally.")
    else:
        jwt_token = None
        print("Laps will be saved locally.")

    # Set up lap write queue and writer thread with failure event
    logger.debug("Starting lap writer thread.")
    lap_write_queue: queue.Queue = queue.Queue()
    lap_failure_event = threading.Event()
    lap_writer_thread = threading.Thread(target=lap_writer, args=(lap_write_queue, jwt_token, BACKEND_URL, lap_failure_event), daemon=True)
    lap_writer_thread.start()

    try:
        while True:
            # Check for heartbeat failure event
            if 'heartbeat_failure_event' in locals() and heartbeat_failure_event.is_set():
                raise SessionHeartbeatError("Heartbeat failure detected. Exiting...")
            # Check for lap writer failure event
            if 'lap_failure_event' in locals() and lap_failure_event.is_set():
                raise LapWriterError("Lap writer failure detected. Exiting...")

            now: float = time.time()
            if now - last_heartbeat > HEARTBEAT_INTERVAL:
                send_heartbeat(ps_ip, send_sock)
                last_heartbeat = now

            recv_sock.settimeout(0.1)
            try:
                data: bytes
                addr: Any
                data, addr = recv_sock.recvfrom(4096)
                decrypted: bytes = decrypt_packet(data)
                if not decrypted:
                    continue
                packet: Optional[GT7Packet] = GT7Packet(decrypted)

                if not packet or getattr(packet, 'is_paused', True):
                    continue
                # Lap change detection
                if lap_number is not None and \
                packet.current_lap != 0 and packet.current_lap > lap_number:
                    # Start recording only after the first lap increment
                    if not recording_started or lap_number == 0:
                        recording_started = True
                        lap_number = packet.current_lap
                        current_lap = []
                        current_lap.append(packet)
                        continue
                    lap_time: int = packet.last_lap
                    if args.track:
                        logger.debug(f"Lap completed (track mode). Saving positional data only.")
                        lap_write_queue.put(([p.to_track_dict() for p in current_lap], lap_time))
                    else:
                        logger.debug(f"Lap completed. Saving telemetry data.")
                        lap_write_queue.put(([p.to_dict() for p in current_lap], lap_time))
                    current_lap = []

                lap_number = packet.current_lap
                current_lap.append(packet)
            except socket.timeout as e:
                # Nothing to do here, just continue executing the agent
                continue
    except KeyboardInterrupt:
        print("Exiting...")
        #Exit threads gracefully
        if "heartbeat_thread" in locals():
            heartbeat_thread.join(timeout=2)
        if "lap_writer_thread" in locals():
            lap_writer_thread.join(timeout=2)
        sys.exit(0)
    except GT7HeartbeatError as e:
        print(f"GT7 heartbeat error: {e}")
        logger.debug(e)
        #Exit threads gracefully
        if "heartbeat_thread" in locals():
            heartbeat_thread.join(timeout=2)
        if "lap_writer_thread" in locals():
            lap_writer_thread.join(timeout=2)
        sys.exit(1)
    except (SessionHeartbeatError, LapWriterError) as e:
        logger.debug(e)
        #Exit threads gracefully
        if "heartbeat_thread" in locals():
            heartbeat_thread.join(timeout=2)
        if "lap_writer_thread" in locals():
            lap_writer_thread.join(timeout=2)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        logger.debug(e)
        #Exit threads gracefully
        if "heartbeat_thread" in locals():
            heartbeat_thread.join(timeout=2)
        if "lap_writer_thread" in locals():
            lap_writer_thread.join(timeout=2)
        sys.exit(1)

if __name__ == "__main__":
    main()
