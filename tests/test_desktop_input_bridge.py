from __future__ import annotations

from types import SimpleNamespace

from desk.desktop_input import DesktopInputBridge


class FakePygame:
    KEYDOWN = 1
    KEYUP = 2

    K_RETURN = 10
    K_a = 11
    K_ESCAPE = 12
    K_b = 13
    K_x = 14
    K_y = 15
    K_1 = 16
    K_2 = 17
    K_3 = 18
    K_4 = 19
    K_q = 20
    K_e = 21
    K_F8 = 22
    K_F9 = 23
    K_m = 24
    K_UP = 25
    K_DOWN = 26
    K_LEFT = 27
    K_RIGHT = 28

    JOYBUTTONDOWN = 31
    JOYHATMOTION = 32
    JOYAXISMOTION = 33
    JOYDEVICEADDED = 34
    JOYDEVICEREMOVED = 35
    CONTROLLERBUTTONDOWN = 36
    CONTROLLERBUTTONUP = 38
    CONTROLLERDEVICEREMOVED = 39
    CONTROLLERAXISMOTION = 37


def key_event(kind, key):
    return SimpleNamespace(type=kind, key=key)


def test_desktop_keyboard_mapping_matches_the_requested_controller_layout():
    pygame = FakePygame()
    bridge = DesktopInputBridge(pygame)

    expected = {
        pygame.K_RETURN: "A",
        pygame.K_a: "A",
        pygame.K_ESCAPE: "B",
        pygame.K_b: "B",
        pygame.K_x: "X",
        pygame.K_y: "Y",
        pygame.K_1: "L1",
        pygame.K_2: "L2",
        pygame.K_3: "R2",
        pygame.K_4: "R1",
        pygame.K_q: "L3",
        pygame.K_e: "R3",
        pygame.K_F8: "SELECT",
        pygame.K_F9: "START",
        pygame.K_m: "MENU",
    }
    assert bridge.keymap == expected


def test_poll_returns_actions_and_drains_the_queue_without_returning_none():
    pygame = FakePygame()
    bridge = DesktopInputBridge(pygame)
    bridge.handle_events([
        key_event(pygame.KEYDOWN, pygame.K_RETURN),
        key_event(pygame.KEYDOWN, pygame.K_x),
    ])

    assert bridge.poll() == ["A", "X"]
    assert bridge.poll() == []
    assert bridge.poll() is not None


def test_escape_is_back_and_only_m_opens_the_menu_action():
    pygame = FakePygame()
    bridge = DesktopInputBridge(pygame)
    bridge.handle_events([
        key_event(pygame.KEYDOWN, pygame.K_ESCAPE),
        key_event(pygame.KEYDOWN, pygame.K_m),
    ])

    assert bridge.poll() == ["B", "MENU"]


def test_dpad_arrow_keys_drive_hat_and_release_cleanly():
    pygame = FakePygame()
    bridge = DesktopInputBridge(pygame)
    bridge.handle_events([
        key_event(pygame.KEYDOWN, pygame.K_UP),
        key_event(pygame.KEYDOWN, pygame.K_RIGHT),
    ])
    assert bridge.hat() == (1, 1)
    assert bridge.poll() == []

    bridge.handle_events([key_event(pygame.KEYUP, pygame.K_RIGHT)])
    assert bridge.hat() == (0, 1)
    bridge.handle_events([key_event(pygame.KEYUP, pygame.K_UP)])
    assert bridge.hat() == (0, 0)


def test_poll_raw_returns_stable_button_identities_and_drains_once():
    pygame = FakePygame()
    bridge = DesktopInputBridge(pygame)
    bridge.handle_events([
        key_event(pygame.KEYDOWN, pygame.K_RETURN),
        key_event(pygame.KEYDOWN, pygame.K_1),
        key_event(pygame.KEYDOWN, pygame.K_F9),
    ])

    assert bridge.poll_raw() == [304, 310, 315]
    assert bridge.poll() == []

def test_desktop_runtime_uses_the_shared_bridge_and_never_returns_none_from_poll():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    launcher = (root / "voiddesk.py").read_text(encoding="utf-8")
    assert "from desk.desktop_input import DesktopInputBridge" in launcher
    assert "input_bridge.handle_events(evs)" in launcher
    assert "evinput.poll = input_bridge.poll" in launcher
    assert "evinput.poll_raw = input_bridge.poll_raw" in launcher
    assert "evinput.hat = input_bridge.hat" in launcher
    assert "lambda: _q.copy() and _q.clear()" not in launcher

def test_desktop_joystick_buttons_match_the_standard_gamepad_layout():
    pygame = FakePygame()
    bridge = DesktopInputBridge(pygame)
    events = [
        SimpleNamespace(type=pygame.JOYBUTTONDOWN, button=0),
        SimpleNamespace(type=pygame.JOYBUTTONDOWN, button=1),
        SimpleNamespace(type=pygame.JOYBUTTONDOWN, button=4),
        SimpleNamespace(type=pygame.JOYBUTTONDOWN, button=5),
        SimpleNamespace(type=pygame.JOYBUTTONDOWN, button=8),
        SimpleNamespace(type=pygame.JOYBUTTONDOWN, button=9),
        SimpleNamespace(type=pygame.JOYBUTTONDOWN, button=10),
    ]
    bridge.handle_events(events)
    assert bridge.poll() == ["A", "B", "L1", "R1", "L3", "R3", "MENU"]


def test_desktop_gamepad_hat_and_trigger_axes_are_supported():
    pygame = FakePygame()
    bridge = DesktopInputBridge(pygame)
    bridge.handle_events([
        SimpleNamespace(type=pygame.JOYHATMOTION, instance_id=7, value=(-1, 1)),
        SimpleNamespace(type=pygame.JOYAXISMOTION, instance_id=7, axis=4, value=0.9),
        SimpleNamespace(type=pygame.JOYAXISMOTION, instance_id=7, axis=5, value=0.8),
    ])
    assert bridge.hat() == (-1, 1)
    assert bridge.poll() == ["L2", "R2"]


def test_gamepad_trigger_axis_queues_only_once_until_released():
    pygame = FakePygame()
    bridge = DesktopInputBridge(pygame)
    for value in (0.7, 0.8, 0.9):
        bridge.handle_events([
            SimpleNamespace(type=pygame.JOYAXISMOTION, instance_id=2, axis=4, value=value)
        ])
    assert bridge.poll() == ["L2"]
    bridge.handle_events([
        SimpleNamespace(type=pygame.JOYAXISMOTION, instance_id=2, axis=4, value=0.0),
        SimpleNamespace(type=pygame.JOYAXISMOTION, instance_id=2, axis=4, value=0.9),
    ])
    assert bridge.poll() == ["L2"]

class FakeJoystickDevice:
    def __init__(self, device_index):
        self.device_index = device_index
        self.instance_id = 100 + device_index
        self.initialized = False
        self.closed = False

    def init(self):
        self.initialized = True

    def get_instance_id(self):
        return self.instance_id

    def quit(self):
        self.closed = True


class FakeJoystickModule:
    def __init__(self, count=1):
        self.count = count
        self.initialized = False
        self.devices = {}

    def init(self):
        self.initialized = True

    def get_count(self):
        return self.count

    def Joystick(self, device_index):
        device = FakeJoystickDevice(device_index)
        self.devices[device_index] = device
        return device


def test_desktop_gamecontroller_events_use_standardized_button_order():
    pygame = FakePygame()
    bridge = DesktopInputBridge(pygame)
    bridge.handle_events([
        SimpleNamespace(type=pygame.CONTROLLERBUTTONDOWN, instance_id=4, button=9),
        SimpleNamespace(type=pygame.CONTROLLERBUTTONDOWN, instance_id=4, button=10),
        SimpleNamespace(type=pygame.CONTROLLERBUTTONDOWN, instance_id=4, button=11),
    ])
    assert bridge.poll() == ["L1", "R1", "UP"]


def test_gamecontroller_dpad_buttons_drive_hat_until_released():
    pygame = FakePygame()
    bridge = DesktopInputBridge(pygame)

    bridge.handle_events([
        SimpleNamespace(type=pygame.CONTROLLERBUTTONDOWN, instance_id=12, button=11),
        SimpleNamespace(type=pygame.CONTROLLERBUTTONDOWN, instance_id=12, button=14),
    ])
    assert bridge.hat() == (1, 1)
    assert bridge.poll() == []

    bridge.handle_events([
        SimpleNamespace(type=pygame.CONTROLLERBUTTONUP, instance_id=12, button=14),
    ])
    assert bridge.hat() == (0, 1)

    bridge.handle_events([
        SimpleNamespace(type=pygame.CONTROLLERDEVICEREMOVED, instance_id=12),
    ])
    assert bridge.hat() == (0, 0)


def test_desktop_joystick_initialization_and_hotplug_lifecycle():
    pygame = FakePygame()
    joystick_module = FakeJoystickModule(count=1)
    pygame.joystick = joystick_module

    bridge = DesktopInputBridge(pygame)
    assert joystick_module.initialized is True
    assert joystick_module.devices[0].initialized is True
    assert 100 in bridge._joysticks

    bridge.handle_events([
        SimpleNamespace(type=pygame.JOYDEVICEADDED, device_index=1)
    ])
    assert joystick_module.devices[1].initialized is True
    assert 101 in bridge._joysticks

    bridge.handle_events([
        SimpleNamespace(type=pygame.JOYDEVICEREMOVED, instance_id=101)
    ])
    assert 101 not in bridge._joysticks
    assert joystick_module.devices[1].closed is True
