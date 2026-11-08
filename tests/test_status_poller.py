import threading
import time

from desk.sysinfo import StatusPoller


def _wait_until(predicate, timeout=1.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return bool(predicate())


def test_snapshot_does_not_wait_for_slow_system_probe():
    started = threading.Event()
    release = threading.Event()

    def read_status():
        started.set()
        release.wait(1.0)
        return {"bt": True}

    poller = StatusPoller(read_status, interval=60, initial={"bt": None})

    before = time.perf_counter()
    assert poller.snapshot() == {"bt": None}
    elapsed = time.perf_counter() - before

    assert elapsed < 0.1
    assert started.wait(0.5)

    # Repeated reads stay immediate and don't start parallel probes.
    for _ in range(20):
        assert poller.snapshot() == {"bt": None}

    release.set()
    assert _wait_until(lambda: poller.snapshot().get("bt") is True)


def test_snapshot_returns_a_copy_of_cached_state():
    poller = StatusPoller(lambda: {"wifi": 3}, interval=60,
                          initial={"wifi": 2})
    first = poller.snapshot()
    first["wifi"] = 99
    assert poller.snapshot()["wifi"] == 2


def test_failed_probe_does_not_leave_poller_stuck():
    attempts = []

    def read_status():
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("probe failed")
        return {"vol": 70}

    poller = StatusPoller(read_status, interval=0.1, initial={"vol": None})
    poller.snapshot()
    assert _wait_until(lambda: len(attempts) == 1)

    time.sleep(0.12)
    poller.snapshot()
    assert _wait_until(lambda: poller.snapshot().get("vol") == 70)
