"""
GT7 Telemetry Packet Processing
------------------------------
Handles decryption and parsing of GT7 UDP telemetry packets.
"""

import struct
from Crypto.Cipher import Salsa20
from datetime import timedelta
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

GT7_UDP_PORT = 33740
GT7_HEARTBEAT_PORT = 33739
HEARTBEAT_INTERVAL = 1.5
SALSA20_KEY = b"Simulator Interface Packet GT7 ver 0.0"

def decrypt_packet(data: bytes) -> bytearray:
    """
    Decrypts a GT7 UDP packet using Salsa20 cipher.

    Args:
        data (bytes): Encrypted packet data.

    Returns:
        bytearray: Decrypted packet data, or empty bytearray if invalid.
    """
    key = SALSA20_KEY
    oiv = data[0x40:0x44]
    iv1 = int.from_bytes(oiv, byteorder='little')
    iv2 = iv1 ^ 0xDEADBEAF
    iv = bytearray()
    iv.extend(iv2.to_bytes(4, 'little'))
    iv.extend(iv1.to_bytes(4, 'little'))
    cipher = Salsa20.new(key[0:32], bytes(iv))
    decrypted = cipher.decrypt(data)
    magic = int.from_bytes(decrypted[0:4], byteorder='little')
    if magic != 0x47375330:
        return bytearray(b'')
    return decrypted

class GT7Packet:
    """
    Represents a parsed GT7 telemetry packet.
    Extracts and stores various telemetry fields from decrypted data.
    """
    def __init__(self, ddata: Optional[bytes]) -> None:
        """
        Initializes GT7Packet from decrypted data.

        Args:
            ddata (Optional[bytes]): Decrypted packet data.
        """
        if not ddata:
            return
        self.package_id = struct.unpack('i', ddata[0x70:0x70 + 4])[0]
        self.best_lap = struct.unpack('i', ddata[0x78:0x78 + 4])[0]
        self.last_lap = struct.unpack('i', ddata[0x7C:0x7C + 4])[0]
        self.current_lap = struct.unpack('h', ddata[0x74:0x74 + 2])[0]
        self.current_gear = struct.unpack('B', ddata[0x90:0x90 + 1])[0] & 0b00001111
        self.suggested_gear = struct.unpack('B', ddata[0x90:0x90 + 1])[0] >> 4
        self.fuel_capacity = struct.unpack('f', ddata[0x48:0x48 + 4])[0]
        self.current_fuel = struct.unpack('f', ddata[0x44:0x44 + 4])[0]
        self.boost = struct.unpack('f', ddata[0x50:0x50 + 4])[0] - 1
        self.tyre_diameter_FL = struct.unpack('f', ddata[0xB4:0xB4 + 4])[0]
        self.tyre_diameter_FR = struct.unpack('f', ddata[0xB8:0xB8 + 4])[0]
        self.tyre_diameter_RL = struct.unpack('f', ddata[0xBC:0xBC + 4])[0]
        self.tyre_diameter_RR = struct.unpack('f', ddata[0xC0:0xC0 + 4])[0]
        self.tyre_speed_FL = abs(3.6 * self.tyre_diameter_FL * struct.unpack('f', ddata[0xA4:0xA4 + 4])[0])
        self.tyre_speed_FR = abs(3.6 * self.tyre_diameter_FR * struct.unpack('f', ddata[0xA8:0xA8 + 4])[0])
        self.tyre_speed_RL = abs(3.6 * self.tyre_diameter_RL * struct.unpack('f', ddata[0xAC:0xAC + 4])[0])
        self.tyre_speed_RR = abs(3.6 * self.tyre_diameter_RR * struct.unpack('f', ddata[0xB0:0xB0 + 4])[0])
        self.car_speed = 3.6 * struct.unpack('f', ddata[0x4C:0x4C + 4])[0]
        if self.car_speed > 0:
            self.tyre_slip_ratio_FL = '{:6.2f}'.format(self.tyre_speed_FL / self.car_speed)
            self.tyre_slip_ratio_FR = '{:6.2f}'.format(self.tyre_speed_FR / self.car_speed)
            self.tyre_slip_ratio_RL = '{:6.2f}'.format(self.tyre_speed_RL / self.car_speed)
            self.tyre_slip_ratio_RR = '{:6.2f}'.format(self.tyre_speed_RR / self.car_speed)
        self.time_on_track = timedelta(seconds=round(struct.unpack('i', ddata[0x80:0x80 + 4])[0] / 1000))
        self.total_laps = struct.unpack('h', ddata[0x76:0x76 + 2])[0]
        self.current_position = struct.unpack('h', ddata[0x84:0x84 + 2])[0]
        self.total_positions = struct.unpack('h', ddata[0x86:0x86 + 2])[0]
        self.car_id = struct.unpack('i', ddata[0x124:0x124 + 4])[0]
        self.throttle = struct.unpack('B', ddata[0x91:0x91 + 1])[0] / 2.55
        self.rpm = struct.unpack('f', ddata[0x3C:0x3C + 4])[0]
        self.rpm_rev_warning = struct.unpack('H', ddata[0x88:0x88 + 2])[0]
        self.brake = struct.unpack('B', ddata[0x92:0x92 + 1])[0] / 2.55
        self.rpm_rev_limiter = struct.unpack('H', ddata[0x8A:0x8A + 2])[0]
        self.estimated_top_speed = struct.unpack('h', ddata[0x8C:0x8C + 2])[0]
        self.clutch = struct.unpack('f', ddata[0xF4:0xF4 + 4])[0]
        self.clutch_engaged = struct.unpack('f', ddata[0xF8:0xF8 + 4])[0]
        self.rpm_after_clutch = struct.unpack('f', ddata[0xFC:0xFC + 4])[0]
        self.oil_temp = struct.unpack('f', ddata[0x5C:0x5C + 4])[0]
        self.water_temp = struct.unpack('f', ddata[0x58:0x58 + 4])[0]
        self.oil_pressure = struct.unpack('f', ddata[0x54:0x54 + 4])[0]
        self.ride_height = 1000 * struct.unpack('f', ddata[0x38:0x38 + 4])[0]
        self.tyre_temp_FL = struct.unpack('f', ddata[0x60:0x60 + 4])[0]
        self.tyre_temp_FR = struct.unpack('f', ddata[0x64:0x64 + 4])[0]
        self.suspension_fl = struct.unpack('f', ddata[0xC4:0xC4 + 4])[0]
        self.suspension_fr = struct.unpack('f', ddata[0xC8:0xC8 + 4])[0]
        self.tyre_temp_rl = struct.unpack('f', ddata[0x68:0x68 + 4])[0]
        self.tyre_temp_rr = struct.unpack('f', ddata[0x6C:0x6C + 4])[0]
        self.suspension_rl = struct.unpack('f', ddata[0xCC:0xCC + 4])[0]
        self.suspension_rr = struct.unpack('f', ddata[0xD0:0xD0 + 4])[0]
        self.gear_1 = struct.unpack('f', ddata[0x104:0x104 + 4])[0]
        self.gear_2 = struct.unpack('f', ddata[0x108:0x108 + 4])[0]
        self.gear_3 = struct.unpack('f', ddata[0x10C:0x10C + 4])[0]
        self.gear_4 = struct.unpack('f', ddata[0x110:0x110 + 4])[0]
        self.gear_5 = struct.unpack('f', ddata[0x114:0x114 + 4])[0]
        self.gear_6 = struct.unpack('f', ddata[0x118:0x118 + 4])[0]
        self.gear_7 = struct.unpack('f', ddata[0x11C:0x11C + 4])[0]
        self.gear_8 = struct.unpack('f', ddata[0x120:0x120 + 4])[0]
        self.position_x = struct.unpack('f', ddata[0x04:0x04 + 4])[0]
        self.position_y = struct.unpack('f', ddata[0x08:0x08 + 4])[0]
        self.position_z = struct.unpack('f', ddata[0x0C:0x0C + 4])[0]
        self.velocity_x = struct.unpack('f', ddata[0x10:0x10 + 4])[0]
        self.velocity_y = struct.unpack('f', ddata[0x14:0x14 + 4])[0]
        self.velocity_z = struct.unpack('f', ddata[0x18:0x18 + 4])[0]
        self.rotation_pitch = struct.unpack('f', ddata[0x1C:0x1C + 4])[0]
        self.rotation_yaw = struct.unpack('f', ddata[0x20:0x20 + 4])[0]
        self.rotation_roll = struct.unpack('f', ddata[0x24:0x24 + 4])[0]
        self.angular_velocity_x = struct.unpack('f', ddata[0x2C:0x2C + 4])[0]
        self.angular_velocity_y = struct.unpack('f', ddata[0x30:0x30 + 4])[0]
        self.angular_velocity_z = struct.unpack('f', ddata[0x34:0x34 + 4])[0]
        self.is_paused = bin(struct.unpack('B', ddata[0x8E:0x8E + 1])[0])[-2] == '1'
        self.in_race = bin(struct.unpack('B', ddata[0x8E:0x8E + 1])[0])[-1] == '1'
        self.is_paused = self.is_paused == 1
        self.in_race = self.in_race == 1

    def to_dict(self) -> Dict[str, Any]:
        """
        Returns a dictionary of selected telemetry fields.

        Returns:
            Dict[str, Any]: Dictionary of key telemetry values.
        """
        return {
            'package_id': self.package_id,
            'current_gear': self.current_gear,
            'car_speed': self.car_speed,
            'throttle': self.throttle,
            'brake': self.brake,
            'position_x': self.position_x,
            'position_y': self.position_y,
            'position_z': self.position_z
        }

    def to_track_dict(self) -> Dict[str, float]:
        """
        Returns a dictionary with only position data.

        Returns:
            Dict[str, float]: Dictionary of position values.
        """
        return {
            'position_x': self.position_x,
            'position_y': self.position_y,
            'position_z': self.position_z,
        }

def send_heartbeat(ps_ip: str, sock: Any) -> None:
    """
    Sends a heartbeat packet to the PlayStation to keep telemetry stream alive.

    Args:
        ps_ip (str): PlayStation IP address.
        sock (Any): UDP socket object.
    """
    heartbeat = b'A'
    try:
        sock.sendto(heartbeat, (ps_ip, GT7_HEARTBEAT_PORT))
    except Exception as e:
        raise GT7HeartbeatError(f"Failed to send heartbeat: {e}")

class GT7HeartbeatError(Exception):
    """Raised when GT7 heartbeat fails or encounters an error."""
    pass