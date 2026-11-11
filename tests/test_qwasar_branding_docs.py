from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_qwasar_branding_keeps_legacy_package_identifiers_documented():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "# QWASAR DESK" in readme
    assert "Symbiotic Layer" in readme
    assert "`Void-Desk/`" in readme
    assert "`mux_launch.sh`" in readme
    assert "not a replacement firmware image today" in readme


def test_symbiotic_layer_has_recovery_and_reversibility_constraints():
    doc = (ROOT / "docs" / "SYMBIOTIC_LAYER.md").read_text(encoding="utf-8")
    assert "Application lifecycle" in doc
    assert "Recovery and uninstall contract" in doc
    assert "Do not modify bootloader partitions" in doc
    assert "SD1/SD2" in doc


def test_wiki_sidebar_references_existing_source_pages():
    wiki = ROOT / "wiki-source"
    sidebar = (wiki / "_Sidebar.md").read_text(encoding="utf-8")
    pages = re.findall(r"\]\(([^)]+)\)", sidebar)
    assert "Symbiotic-Layer" in pages
    for page in pages:
        assert (wiki / (page + ".md")).is_file(), page


def test_wiki_home_links_to_symbiotic_layer():
    home = (ROOT / "wiki-source" / "Home.md").read_text(encoding="utf-8")
    assert "QWASAR Desk" in home
    assert "[Symbiotic Layer roadmap](Symbiotic-Layer)" in home

def test_pygame_user_facing_copy_uses_qwasar_brand():
    source = (ROOT / "desk" / "main.py").read_text(encoding="utf-8")
    assert '"f_vdupd": "QWASAR Desk Update"' in source
    assert 'self.text("QWASAR DESK"' in source
    assert 'self.text("QWASAR OS -- READY"' in source
    assert 'bt = "QWASAR DESK"' in source
    assert 'intro.play(self.surface, pygame.display.flip, "QWASAR DESK"' in source
    assert 'bt = "Void-DESK"' not in source
    assert 'intro.play(self.surface, pygame.display.flip, "Void-DESK"' not in source
    assert '"Restart QWASAR Desk"' in source
    assert "riavvia QWASAR Desk" in source
    assert 'VoidDesk hand off and exit' not in source
    assert "VoidDesk wasn't built to be perfect" not in source
    assert '"VOID DESK"' not in source

def test_ci_uses_one_bounded_apt_install_and_system_python_for_integration():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    assert workflow.count("bash tools/ci_apt_install.sh") == 1
    assert "name: Lua, LÖVE and Rt:Tailscale-M integration" in workflow
    assert "cancel-in-progress: true" in workflow

    integration = workflow.split("  linux-integration:\\n", 1)[1]
    # Native Python modules are installed by APT, so this job must use Ubuntu's
    # system interpreter rather than setup-python's isolated interpreter.
    assert "actions/setup-python@v5" not in integration
    assert "python3-pyflakes python3-qrcode python3-opencv" in integration

    installer = (ROOT / "tools" / "ci_apt_install.sh").read_text(
        encoding="utf-8"
    )
    assert "azure\\.archive\\.ubuntu\\.com" in installer
    assert "timeout --kill-after=10s" in installer
    assert "Acquire::Retries=1" in installer
    assert "QWASAR_CI_APT_UPDATE_TIMEOUT:-120" in installer
    assert "QWASAR_CI_APT_INSTALL_TIMEOUT:-180" in installer
    assert "for attempt in 1 2; do" in installer
