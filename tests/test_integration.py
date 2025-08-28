import threading
import queue
from common.lap import lap_writer

def test_lap_writer_thread_local(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    lap_write_queue = queue.Queue()
    failure_event = threading.Event()
    # Put a lap to be saved locally
    lap_write_queue.put(([{"car_speed": 100}], 61000))
    t = threading.Thread(target=lap_writer, args=(lap_write_queue, None, '', failure_event))
    t.start()
    lap_write_queue.join()
    assert not failure_event.is_set()
    t.join(timeout=2)
    files = list(tmp_path.glob("laps/*.json"))
    assert len(files) == 1
