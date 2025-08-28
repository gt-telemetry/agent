import pytest
import json
from common.lap import format_lap_time, save_lap_locally

def test_format_lap_time():
    assert format_lap_time(61000) == '01-01-000'
    assert format_lap_time(123456) == '02-03-456'

# Test saving lap locally
@pytest.mark.usefixtures("tmp_path")
def test_save_lap_locally(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    packets = [{"car_speed": 100}]
    save_lap_locally(packets, 61000)
    files = list(tmp_path.glob("laps/*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert isinstance(data, list)
