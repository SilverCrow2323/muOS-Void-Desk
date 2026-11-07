# ============================================================================
#  VOID DESK — SHUTDOWN Hub
#  Shutdown menu, CRT off animation
# ============================================================================

from desk.hubs import HubMixin


class ShutdownHub(HubMixin):
    """System shutdown and power management."""

    def __init__(self, app):
        self.app = app

    def shutdown_menu(self, key):
        """Open the shutdown menu."""
        app = self.app
        if key == "A":
            app.push("shutdown")
        elif key == "B":
            app.pop_state()

    def crt_off(self):
        """Execute CRT off animation and shutdown."""
        app = self.app
        app.crt_off()
