from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_qwasar_branding_keeps_legacy_package_identifiers_documented():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "# VOID DESK" in readme
    assert "QWASAR-Env" in readme
    assert "Symbiotic Layer" in readme
    assert "`Void-Desk/`" in readme
    assert "`mux_launch.sh`" in readme
    assert "not a replacement firmware image today" in readme


def test_qwasar_env_product_map_documents_device_boundaries_and_love_gates():
    doc = (ROOT / "docs" / "PRODUCT_ECOSYSTEM_MAP.md").read_text(
        encoding="utf-8"
    )
    for term in (
        "QWASAR-Env",
        "Void Desk",
        "QWASAR Hub",
        "QWASAR Studio",
        "QWASAR Link",
        "Device A — H700 handheld",
        "LÖVE completion plan",
        "No QWASAR Hub, Studio, Link, or runtime repository needs to be created",
    ):
        assert term in doc


def test_studio_unifies_module_layout_and_release_workbenches():
    studio = (ROOT / "docs" / "STUDIO_ARCHITECTURE.md").read_text(
        encoding="utf-8"
    )
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for term in (
        "Module Forge",
        "Layout Designer",
        "Release Composer",
        "Community Library",
        "Full",
        "Essential",
        "Slim",
        "/v1/catalog/modules",
        "/v1/builds",
    ):
        assert term in studio
    assert "QWASAR Studio" in readme
    assert "one web app" in readme
    assert "APT package recipes target only the optional Debian/Ubuntu desktop image" in readme


def test_void_desk_module_contract_covers_composition_security_and_flavours():
    doc = (ROOT / "docs" / "MODULE_SYSTEM.md").read_text(encoding="utf-8")
    for term in (
        "The LEGO rule",
        "Profiles and layouts",
        "Desktop APT packages",
        "module.json",
        "hub.panel",
        "capabilities",
        "sandboxing",
        "Module Forge",
        "Layout Designer",
        "Release Composer",
        "Community Library",
        "Full",
        "Essential",
        "Slim",
        "APT operations are submitted through the existing Void Desk service job manager",
    ):
        assert term in doc


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

    integration = workflow.split("  linux-integration:", 1)[1]
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

def test_voiddesk_symbol_is_shared_by_site_and_pygame():
    symbol = ROOT / "assets" / "brand" / "voiddesk_symbol.svg"
    source = symbol.read_text(encoding="utf-8")
    builder = (ROOT / "tools" / "build_site.py").read_text(encoding="utf-8")
    icons = (ROOT / "desk" / "icons.py").read_text(encoding="utf-8")
    header = (ROOT / "desk" / "header.py").read_text(encoding="utf-8")

    assert "<circle" in source
    assert "M263 78 L94 352 H429 Z" in source
    assert "M263 352 V492" in source
    assert 'symbol = BRAND / "voiddesk_symbol.svg"' in builder
    assert 'key in ("voiddesk", "brand")' in icons
    assert 'icons.draw(surface, "voiddesk", 10, 8, 26, acc)' in header
    assert 'icons.draw(surface, "voiddesk", 12, 8, 26, acc)' in header

    for page in (
        "index.html",
        "architecture.html",
        "field-manual.html",
        "asset-atlas.html",
        "studio.html",
        "blueprint.html",
    ):
        html = (ROOT / "site" / page).read_text(encoding="utf-8")
        assert "voiddesk_symbol.svg" in html
