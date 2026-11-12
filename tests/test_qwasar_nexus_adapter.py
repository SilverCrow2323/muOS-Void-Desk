from __future__ import annotations

from desk.qwasar.nexus_adapter import BASE_RINGS, compose_nexus_profile


def _workspace(workspace_id: str, order: int, **kwargs):
    return {"id": workspace_id, "order": order, **kwargs}


def test_missing_or_invalid_composition_keeps_exact_legacy_rings():
    rings, states = compose_nexus_profile(None)
    assert rings == BASE_RINGS
    assert rings == ((0,), (3, 5, 2, 6), (4, 1, 7, 8), (9,))
    assert states[1]["workspace_id"] is None
    assert states[6]["workspace_id"] is None

    assert compose_nexus_profile({"workspaces": "not-a-list"})[0] == BASE_RINGS


def test_profile_reorders_hides_and_disables_only_mapped_workspaces():
    composition = {
        "profile": {"id": "custom", "name": "Custom"},
        "workspaces": [
            _workspace("start-session", 0),
            _workspace("uplink", 1),
            _workspace("the-forge", 2, enabled=False),
            _workspace("media-vault", 3, visible=False),
            _workspace("settings", 4),
            _workspace("rt-toolbox", 5, label="MY TOOLBOX"),
            _workspace("info-community", 6),
            _workspace("end-node", 7),
        ],
    }

    rings, states = compose_nexus_profile(composition)

    assert rings[0] == (0,)
    # UPLINK moves before THE FORGE; hidden MEDIA VAULT disappears;
    # WORKSHOP remains in its legacy slot after the current workspaces.
    assert rings[1] == (5, 3, 6)
    assert rings[2] == (4, 1, 7, 8)
    assert rings[3] == (9,)
    assert states[3]["enabled"] is False
    assert states[3]["visible"] is True
    assert states[2]["visible"] is False
    assert states[4]["label"] == "MY TOOLBOX"
    assert states[6]["workspace_id"] is None
    assert states[1]["workspace_id"] is None


def test_protected_start_and_end_are_never_hidden_or_disabled_by_adapter():
    composition = {
        "workspaces": [
            _workspace("start-session", 0, enabled=False, visible=False),
            _workspace("end-node", 7, enabled=False, visible=False),
            _workspace("the-forge", 1, enabled=False, visible=True),
        ]
    }

    rings, states = compose_nexus_profile(composition)

    assert rings[0] == (0,)
    assert rings[3] == (9,)
    assert states[0]["enabled"] is True
    assert states[0]["visible"] is True
    assert states[9]["enabled"] is True
    assert states[9]["visible"] is True
    assert states[3]["enabled"] is False
    assert states[3]["visible"] is True


def test_legacy_nodes_keep_stable_identity_and_are_not_reinterpreted():
    composition = {
        "workspaces": [
            _workspace("start-session", 0),
            _workspace("the-forge", 1),
            _workspace("uplink", 2),
            _workspace("media-vault", 3),
            _workspace("rt-toolbox", 4),
            _workspace("settings", 5),
            _workspace("info-community", 6),
            _workspace("end-node", 7),
        ]
    }

    rings, states = compose_nexus_profile(composition)
    assert rings[1][-1] == 6
    assert rings[2][-1] == 1
    assert states[6]["workspace_id"] is None
    assert states[1]["workspace_id"] is None
