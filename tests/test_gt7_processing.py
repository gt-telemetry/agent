from gt7_processing import decrypt_packet, GT7Packet

class DummyPacket:
    def __init__(self, data):
        self.data = data

# Test decrypt_packet with invalid magic
def test_decrypt_packet_invalid_magic():
    # 0x40:0x44 is IV, but magic at start is wrong
    data = b'\x00' * 100
    result = decrypt_packet(data)
    assert result == b''

# Test GT7Packet with None
def test_gt7packet_none():
    pkt = GT7Packet(None)
    assert not hasattr(pkt, 'package_id')

# You can add more tests for valid packet parsing if you have sample data
