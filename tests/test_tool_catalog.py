import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_tool_catalog_has_unique_stable_ids_and_valid_hub_groups():
    catalog = json.loads((ROOT / "data" / "tool_catalog.json").read_text())
    assert catalog["schemaVersion"] == "1.0"
    categories = catalog["categories"]
    ids = [item["id"] for item in categories]
    assert len(ids) == len(set(ids))
    assert categories
    for category in categories:
        assert category["workspace"]
        assert category["hub"]
        assert category["tools"]
        assert len(category["tools"]) == len(set(category["tools"]))


def test_external_tool_inventory_matches_runtime_registry():
    catalog = json.loads((ROOT / "data" / "tool_catalog.json").read_text())
    runtime = json.loads((ROOT / "external" / "tools.json").read_text())
    listed = {item["id"] for item in catalog["externalTools"]}
    registered = {item["id"] for item in runtime["tools"]}
    assert listed == registered


def test_security_review_flags_are_catalog_entries():
    catalog = json.loads((ROOT / "data" / "tool_catalog.json").read_text())
    external_apps = {
        item["id"] for item in catalog["categories"]
        if item["id"] == "standalone-apps"
    }
    assert external_apps
    assert "little-mischief" in catalog["securityReview"]
