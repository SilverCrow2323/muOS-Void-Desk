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
