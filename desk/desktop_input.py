# -*- coding: utf-8 -*-
"""Keyboard input bridge for the desktop Pygame runtime.

The handheld runtime reads Linux evdev directly. The desktop runtime has no
muOS /dev/input contract, so keyboard shortcuts are translated to the same
logical actions consumed by desk.main.App.run().
"""


class DesktopInputBridge:
    """Translate desktop keyboard events into the canonical Void Desk actions."""

    # Stable Linux BTN_* identities used when the controller mapper asks for
    # raw codes in desktop mode.
    RAW_CODES = {
        "A": 304,       # BTN_SOUTH
        "B": 305,       # BTN_EAST
        "Y": 306,       # BTN_C
        "X": 307,       # BTN_NORTH
        "L1": 310,      # BTN_TL
        "R1": 311,      # BTN_TR
        "L2": 312,      # BTN_TL2
        "R2": 313,      # BTN_TR2
        "SELECT": 314,  # BTN_SELECT
        "START": 315,   # BTN_START
        "MENU": 316,    # BTN_MODE
        "L3": 317,      # BTN_THUMBL
        "R3": 318,      # BTN_THUMBR
    }

    # SDL joystick fallback for common XInput-style desktop gamepads.
    JOY_BUTTON_ACTIONS = {
        0: "A", 1: "B", 2: "X", 3: "Y",
        4: "L1", 5: "R1", 6: "SELECT", 7: "START",
        8: "L3", 9: "R3", 10: "MENU",
    }
    # SDL GameController uses a standard logical button order.
    CONTROLLER_BUTTON_ACTIONS = {
        0: "A", 1: "B", 2: "X", 3: "Y",
        4: "SELECT", 5: "MENU", 6: "START",
        7: "L3", 8: "R3", 9: "L1", 10: "R1",
        11: "UP", 12: "DOWN", 13: "LEFT", 14: "RIGHT",
    }

    def __init__(self, pygame_module):
        self.pygame = pygame_module
        self.keymap = {
            pygame_module.K_RETURN: "A",
            pygame_module.K_a: "A",
            pygame_module.K_ESCAPE: "B",
            pygame_module.K_b: "B",
            pygame_module.K_x: "X",
            pygame_module.K_y: "Y",
            pygame_module.K_1: "L1",
            pygame_module.K_2: "L2",
            pygame_module.K_3: "R2",
            pygame_module.K_4: "R1",
            pygame_module.K_q: "L3",
            pygame_module.K_e: "R3",
            pygame_module.K_F8: "SELECT",
            pygame_module.K_F9: "START",
            pygame_module.K_m: "MENU",
        }
        self._queue = []
        self._held = set()
        self._joy_hats = {}
        self._trigger_states = {}
        self._joysticks = {}
        self._init_joysticks()

    def _open_joystick(self, device_index):
        joystick_module = getattr(self.pygame, "joystick", None)
        if joystick_module is None:
            return
        try:
            joystick = joystick_module.Joystick(device_index)
            joystick.init()
            instance_id = (
                joystick.get_instance_id()
                if hasattr(joystick, "get_instance_id")
                else joystick.get_id()
            )
            self._joysticks[instance_id] = joystick
        except Exception:
            # Desktop keyboard input remains usable if a controller cannot open.
            return

    def _init_joysticks(self):
        joystick_module = getattr(self.pygame, "joystick", None)
        if joystick_module is None:
            return
        try:
            joystick_module.init()
            for device_index in range(joystick_module.get_count()):
                self._open_joystick(device_index)
        except Exception:
            return

    @staticmethod
    def _trigger_pressed(value):
        # JOYAXISMOTION is float [-1, 1]; CONTROLLERAXISMOTION is int16.
        return value > (16384 if isinstance(value, int) else 0.5)

    def _queue_trigger(self, device, axis, value):
        action = {4: "L2", 5: "R2"}.get(axis)
        if action is None:
            return
        key = (device, action)
        pressed = self._trigger_pressed(value)
        previous = self._trigger_states.get(key, False)
        if pressed and not previous:
            self._queue.append(action)
        self._trigger_states[key] = pressed

    def handle_events(self, events):
        """Consume a batch from pygame.event.get() without stealing its events."""
        for event in events:
            if event.type == self.pygame.KEYDOWN:
                self._held.add(event.key)
                action = self.keymap.get(event.key)
                if action is not None:
                    self._queue.append(action)
            elif event.type == self.pygame.KEYUP:
                self._held.discard(event.key)
            elif event.type == getattr(self.pygame, "JOYBUTTONDOWN", None):
                action = self.JOY_BUTTON_ACTIONS.get(event.button)
                if action is not None:
                    self._queue.append(action)
            elif event.type == getattr(self.pygame, "JOYDEVICEADDED", None):
                self._open_joystick(event.device_index)
            elif event.type == getattr(self.pygame, "JOYHATMOTION", None):
                self._joy_hats[event.instance_id] = tuple(event.value)
            elif event.type == getattr(self.pygame, "JOYDEVICEREMOVED", None):
                self._joy_hats.pop(event.instance_id, None)
                joystick = self._joysticks.pop(event.instance_id, None)
                if joystick is not None:
                    try:
                        joystick.quit()
                    except Exception:
                        pass
                for key in [k for k in self._trigger_states if k[0] == event.instance_id]:
                    self._trigger_states.pop(key, None)
            elif event.type == getattr(self.pygame, "JOYAXISMOTION", None):
                self._queue_trigger(event.instance_id, event.axis, event.value)
            elif event.type == getattr(self.pygame, "CONTROLLERBUTTONDOWN", None):
                action = self.CONTROLLER_BUTTON_ACTIONS.get(event.button)
                if action is not None:
                    if action in ("UP", "DOWN", "LEFT", "RIGHT"):
                        self._queue.append(action)
                    else:
                        self._queue.append(action)
            elif event.type == getattr(self.pygame, "CONTROLLERAXISMOTION", None):
                self._queue_trigger(event.instance_id, event.axis, event.value)

    def poll(self):
        """Return a real list of queued actions, then drain the queue."""
        actions = list(self._queue)
        self._queue.clear()
        return actions

    def poll_raw(self):
        """Return evdev-compatible BTN_* identities for controller-map capture."""
        return [
            self.RAW_CODES[action]
            for action in self.poll()
            if action in self.RAW_CODES
        ]

    def hat(self):
        """D-pad keyboard equivalent: (x, y), with positive y meaning UP."""
        right = self.pygame.K_RIGHT in self._held
        left = self.pygame.K_LEFT in self._held
        up = self.pygame.K_UP in self._held
        down = self.pygame.K_DOWN in self._held
        for x, y in self._joy_hats.values():
            right = right or x > 0
            left = left or x < 0
            up = up or y > 0
            down = down or y < 0
        return (int(right) - int(left), int(up) - int(down))
