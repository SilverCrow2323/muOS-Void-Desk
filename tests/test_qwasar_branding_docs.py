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
    assert '"Restart QWASAR Desk"' in source
    assert "riavvia QWASAR Desk" in source
    assert 'VoidDesk hand off and exit' not in source
    assert "VoidDesk wasn't built to be perfect" not in source
    assert '"VOID DESK"' not in source

def test_ci_retries_apt_mirrors_and_keeps_independent_jobs_running():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    assert workflow.count("if: ${{ !cancelled() }}") == 3
    assert workflow.count("Acquire::Retries=1") == 3
    assert workflow.count("Acquire::http::Timeout=20") == 3
    assert workflow.count("Acquire::https::Timeout=20") == 3
    assert "LuaJIT installation failed after 3 attempts." in workflow
    assert "LÖVE dependency installation failed after 3 attempts." in workflow
