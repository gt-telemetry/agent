import argparse
import socket
import sys
import time
import threading
import queue
import json
import getpass
import re
from gt7_processing import GT7_UDP_PORT, HEARTBEAT_INTERVAL, decrypt_packet, GT7Packet, send_heartbeat
from lap import save_lap, format_lap_time

def main():
    parser = argparse.ArgumentParser(description="GT7 Telemetry Lap Saver")
    parser.add_argument('--ps_ip', help='PlayStation IP address')
    parser.add_argument('--track', action='store_true', help='Record only positional value to save track layout')
    args = parser.parse_args()

    # Prompt for PlayStation IP if not provided
    if not args.ps_ip:
        while True:
            try:
                ps_ip = input('Enter PlayStation IPv4 address: ')
            except (KeyboardInterrupt, EOFError):
                print("\nExiting...")
                sys.exit(0)
            # Simple IPv4 validation
            if re.match(r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', ps_ip):
                break
            else:
                print("Invalid IPv4 address format. Please try again.")
    else:
        ps_ip = args.ps_ip

    local_ip = "0.0.0.0" 

    # Set up UDP socket for listening
    try:
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        recv_sock.bind(("", GT7_UDP_PORT))
    except Exception as e:
        print(f"Error binding receive socket: {e}")
        sys.exit(1)

    # Set up UDP socket for sending heartbeats, bind to local_ip
    try:
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_sock.bind((local_ip, 0))  # Bind to local IP and ephemeral port
    except Exception as e:
        print(f"Error binding send socket: {e}")
        sys.exit(1)

    last_heartbeat = 0
    current_lap = []
    best_lap = []
    best_lap_time = float('inf')
    lap_number = None
    recording_started = False

    # Prompt for JWT token at startup and test it
    while True:
        try:
            jwt_token = getpass.getpass('Paste your JWT token (input hidden): ')
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            sys.exit(0)
        from lap import test_jwt_token
        if test_jwt_token(jwt_token):
            print("JWT token is valid.")
            break
        else:
            print("Invalid JWT token. Please try again.")

    # Set up lap write queue and writer thread
    lap_write_queue = queue.Queue()
    def lap_writer():
        while True:
            lap_data, lap_time = lap_write_queue.get()
            try:
                save_lap(lap_data, lap_time, jwt_token)
            except Exception as e:
                print(e)
                sys.exit(1)
            lap_write_queue.task_done()
    threading.Thread(target=lap_writer, daemon=True).start()

    try:
        while True:
            now = time.time()
            if now - last_heartbeat > HEARTBEAT_INTERVAL:
                send_heartbeat(ps_ip, send_sock)
                last_heartbeat = now

            recv_sock.settimeout(0.1)
            try:
                data, addr = recv_sock.recvfrom(4096)
                decrypted = decrypt_packet(data)
                if not decrypted:
                    continue
                packet = GT7Packet(decrypted)

                if not packet or getattr(packet, 'is_paused', True):
                    continue
                # Lap change detection
                if lap_number is not None and \
                packet.current_lap != 0  and packet.current_lap > lap_number:
                    # Start recording only after the first lap increment
                    if not recording_started or lap_number == 0:
                        recording_started = True
                        lap_number = packet.current_lap
                        current_lap = []
                        current_lap.append(packet)
                        continue
                    lap_time = packet.last_lap
                    is_best = lap_time is not None and lap_time > 0 and lap_time < best_lap_time
                    if args.track:
                        lap_write_queue.put(([p.to_track_dict() for p in current_lap], lap_time))
                    else:
                        lap_write_queue.put(([p.to_dict() for p in current_lap], lap_time))
                    if is_best:
                        best_lap = current_lap.copy()
                        best_lap_time = lap_time
                    current_lap = []

                lap_number = packet.current_lap
                current_lap.append(packet)
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        print("Exiting...")
        sys.exit(0)

if __name__ == "__main__":
    main()
