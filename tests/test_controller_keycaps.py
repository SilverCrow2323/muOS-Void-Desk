from __future__ import annotations

import pygame

from desk import icons


def test_controller_keycaps_render_face_shoulder_direction_and_system_keys():
    pygame.font.init()
    surface = pygame.Surface((560, 30), pygame.SRCALPHA)
    x = 2
    for label in ("A", "B", "X", "Y", "L1", "R1", "START", "SELECT",
                  "MENU", "LEFT", "RIGHT", "STICK"):
        width = icons.draw_button(surface, label, x, 4, 20,
                                  (100, 220, 235))
        assert width == icons.button_keycap_width(label, 20)
        assert width > 0
        x += width + 3

    assert surface.get_bounding_rect().width > 0
    assert surface.get_bounding_rect().height > 0


def test_controller_keycap_width_is_stable_for_face_and_shoulder_labels():
    assert icons.button_keycap_width("A", 20) == 20
    assert icons.button_keycap_width("L1", 20) > icons.button_keycap_width("A", 20)
    assert icons.button_keycap_width("START", 20) > icons.button_keycap_width("L1", 20)

def test_controls_guide_uses_keycaps_and_current_desktop_bindings():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    source = (root / "desk" / "main.py").read_text(encoding="utf-8")

    assert 'control_guide = self.info_title in (' in source
    assert 'self.draw_info_keycaps(' in source
    assert 'self.btn_names(self.cur_map().get(action, []))' in source
    assert "physical positions depend" in source
    assert "on the active firmware and controller profile" in source
