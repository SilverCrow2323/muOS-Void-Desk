from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_qwasar_studio_profile_contract_keeps_v1_compatibility():
    schema = read_json("schemas/voiddesk-profile.schema.json")
    example = read_json("examples/studio-profile-minimal.json")

    assert schema["title"] == "QWASAR Desk Profile"
    assert schema["additionalProperties"] is False
    assert "minimumVoidDeskVersion" in schema["properties"]["compatibility"]["properties"]
    assert "minimumVoidDeskVersion" in example["compatibility"]
    assert re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,63}", example["id"])
    assert example["name"] == "QWASAR Desk Starter"
    assert example["author"] == "QWASAR Studio"

    for key in schema["required"]:
        assert key in example, f"starter profile is missing required key: {key}"


def test_qwasar_studio_plugin_contract_preserves_v1_publisher_identity():
    schema = read_json("schemas/voiddesk-plugin.schema.json")
    publisher = schema["properties"]["publisher"]["properties"]
    compatibility = schema["properties"]["compatibility"]["properties"]

    assert schema["title"] == "QWASAR Desk Official Plugin Manifest"
    assert publisher["id"]["const"] == "voiddesk-official"
    assert publisher["displayName"]["const"] == "Void Desk Official"
    assert "minimumVoidDeskVersion" in compatibility
    assert "maximumVoidDeskVersion" in compatibility


def test_studio_architecture_documents_brand_and_security_boundary():
    doc = (ROOT / "docs" / "STUDIO_ARCHITECTURE.md").read_text(
        encoding="utf-8"
    )
    assert doc.startswith("# QWASAR Studio — Technical Architecture")
    assert "Version 1 compatibility identifiers" in doc
    assert "Profiles are data only" in doc
    assert "The hosted Studio API is a future component" in doc
    assert "device-initiated outbound HTTPS" in doc
