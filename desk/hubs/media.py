# ============================================================================
#  VOID DESK — MEDIA Hub
#  Radio, Voidcast, Library, BGM Normalize
# ============================================================================

import os
import time

from desk.hubs import HubMixin


class MediaHub(HubMixin):
    """Media playback and management."""

    def __init__(self, app):
        self.app = app

    def radio(self):
        """Internet radio player."""
        app = self.app
        mpv, ffplay, _ = app.check_media_deps()
        if not mpv and not ffplay:
            app.notify("Void Radio", "mpv/ffplay non trovati: installa i player multimediali", "warning")
            return
        app.play_media_boot("radio")
        app.radio_tab = "all"
        app.radio_sel = 0
        app.push("radio")

    def voidcast(self):
        """Voidcast IPTV suite."""
        app = self.app
        app.play_media_boot("iptv")
        app.voidcast_enter()

    def library(self):
        """Media library browser."""
        from desk.main import MEDIA_EXTS
        app = self.app
        app.play_media_boot("library")
        app.fm_open(ext_filter=MEDIA_EXTS)

    def bgmnorm(self):
        """BGM normalization."""
        app = self.app
        app.play_media_boot("normalize")
        dirs = []
        for mount in ("/mnt/mmc", "/mnt/sdcard"):
            for cand in ("MUOS/theme", "BGM", "Music", "bgm", "music"):
                path = os.path.join(mount, cand)
                if os.path.isdir(path):
                    dirs.append(path)
        app.bgm_files = app.run_busy(app.t("checking"),
                                     lambda: app.bgm_scan(dirs)) or []
        app.bgm_sel = 0
        app.bgm_marked = set()
        app.bgm_conv_sel = 0
        app.bgm_opt_sel = 0
        app.bgm_theme_sel = 0
        app.bgm_log_view_scroll = 0
        app.bgm_log_view_lines = []
        app.bgm_result_msg = ""
        app.bgm_processing = False
        app.bgm_process_done = False
        app.bgm_process_total = 0
        app.bgm_process_idx = 0
        app.bgm_process_log = []
        app.bgm_preview_file = None
        app.bgm_preview_proc = None
        app.bgm_file_infos = {}
        app.push("bgmmain")

    def media_vault_enter(self):
        """Avvia la transizione di Media Vault."""
        app = self.app
        app.media_vault_phase = "intro"
        app.media_vault_anim_t0 = time.time()
        app.media_vault_sel = 0
        app.play("media_vault_open")
        app.push("media_vault")