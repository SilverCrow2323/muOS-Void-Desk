# ============================================================================
#  VOID DESK — CONTROLLER Hub
#  Mapping, Devices, Profiles, External Controllers, Binding Engine
# ============================================================================

from desk.hubs import HubMixin


class ControllerHub(HubMixin):
    """Controller input mapping and management."""

    def __init__(self, app):
        self.app = app

    def map(self):
        """Button mapping."""
        self.app.push("map")

    def devices(self):
        """Connected controller devices."""
        app = self.app
        app.ctrl_scan()
        app.ctrl_sel = 0
        app.push("ctrldevices")