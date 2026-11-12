from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pygame_nexus_keeps_all_legacy_menu_destinations_and_icons():
    main = (ROOT / "desk" / "main.py").read_text(encoding="utf-8")
    const = (ROOT / "desk" / "const.py").read_text(encoding="utf-8")

    # The original ten routes retain their numeric IDs; the four compatibility
    # destinations are appended instead of shifting any existing activation.
    assert 'self.menu_icons = [' in main
    for icon in ('"games"', '"develop"', '"community"', '"outerdesk"'):
        assert icon in main
        assert icon in const
    assert '("GAMES"' in main
    assert '("SVILUPPO" if it else "DEVELOP"' in main
    assert '("COMMUNITY",' in main
    assert '("OUTERDESK",' in main


def test_pygame_nexus_legacy_destinations_dispatch_to_existing_hubs():
    main = (ROOT / "desk" / "main.py").read_text(encoding="utf-8")
    expected = {
        '10: "games"',
        '11: "develop"',
        '12: "community"',
        '13: "outerdesk"',
    }
    for route in expected:
        assert route in main
    assert 'elif i in (10, 11, 12, 13):' in main
    hubs = (ROOT / "desk" / "hubs" / "__init__.py").read_text(
        encoding="utf-8"
    )
    for module in ("games", "develop", "community", "outerdesk"):
        assert f"desk.hubs.{module} import" in hubs
