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
        return (
            int(self.pygame.K_RIGHT in self._held)
            - int(self.pygame.K_LEFT in self._held),
            int(self.pygame.K_UP in self._held)
            - int(self.pygame.K_DOWN in self._held),
        )
