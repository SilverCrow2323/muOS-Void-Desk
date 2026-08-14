#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VOID AndroidStation v1.0 — Pocket Console Companion
SPDW Factory — RSPDW Lab
Kivy-based single-file app for Android (and desktop test)

DEPENDENCIES: kivy, paramiko, Pillow
BUILD: buildozer android debug (or run on desktop for testing)
"""

from __future__ import print_function

import base64
import json
import os
import re
import struct
import sys
import tempfile
import threading
import time
from datetime import datetime

try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.utils import get_color_from_hex

BG0 = get_color_from_hex("#0d0d1a")
BG1 = get_color_from_hex("#1a1a2e")
PANEL = get_color_from_hex("#111128")
CYAN = get_color_from_hex("#00ffcc")
MAGENTA = get_color_from_hex("#ff00ff")
ORANGE = get_color_from_hex("#ff6600")
RED = get_color_from_hex("#ff2244")
YELLOW = get_color_from_hex("#f0e130")
TEXT = get_color_from_hex("#e0e0e0")
TEXT_DIM = get_color_from_hex("#555577")
GRID_C = get_color_from_hex("#1e3a5f")
GREEN = get_color_from_hex("#00cc66")

Window.clearcolor = BG0

KV = """
#:import get_color_from_hex kivy.utils.get_color_from_hex
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

<HeaderBar@BoxLayout>:
    size_hint_y: None
    height: dp(48)
    canvas.before:
        Color:
            rgba: get_color_from_hex("#111128")
        Rectangle:
            pos: self.pos
            size: self.size
    Label:
        text: "VOID ANDROIDSTATION"
        font_size: sp(18)
        bold: True
        color: get_color_from_hex("#00ffcc")
        size_hint_x: 0.7
        padding: dp(12), 0
    Label:
        id: status_lbl
        text: "● OFFLINE"
        font_size: sp(12)
        color: get_color_from_hex("#555577")
        size_hint_x: 0.3
        halign: "right"
        padding: dp(10), 0

<NavButton@ToggleButton>:
    group: "nav"
    size_hint_y: None
    height: dp(56)
    background_normal: ""
    background_down: ""
    background_color: (0,0,0,0)
    color: get_color_from_hex("#555577")
    font_size: sp(11)
    bold: True
    canvas.before:
        Color:
            rgba: get_color_from_hex("#1a1a2e") if self.state == "down" else (0,0,0,0)
        Rectangle:
            pos: self.pos
            size: self.size
        Color:
            rgba: get_color_from_hex("#00ffcc") if self.state == "down" else (0,0,0,0)
        Line:
            points: [self.x, self.y+self.height, self.x+self.width, self.y+self.height]
            width: dp(2)

<MetricCard@BoxLayout>:
    orientation: "vertical"
    size_hint_y: None
    height: dp(80)
    padding: dp(8)
    canvas.before:
        Color:
            rgba: get_color_from_hex("#111128")
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(6)]
    Label:
        id: title
        text: "CPU"
        font_size: sp(11)
        color: get_color_from_hex("#555577")
        size_hint_y: 0.3
        halign: "left"
        text_size: self.size
    Label:
        id: value
        text: "--"
        font_size: sp(20)
        bold: True
        color: get_color_from_hex("#00ffcc")
        size_hint_y: 0.7
        halign: "center"
        valign: "middle"
        text_size: self.size

<ActionButton@Button>:
    background_normal: ""
    background_down: ""
    background_color: (0,0,0,0)
    color: get_color_from_hex("#0d0d1a")
    font_size: sp(12)
    bold: True
    canvas.before:
        Color:
            rgba: get_color_from_hex("#00ffcc") if self.state == "normal" else get_color_from_hex("#00cc99")
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(6)]

<MacroButton@Button>:
    background_normal: ""
    background_down: ""
    background_color: (0,0,0,0)
    color: get_color_from_hex("#e0e0e0")
    font_size: sp(11)
    bold: True
    macro_color: "#ff6600"
    canvas.before:
        Color:
            rgba: get_color_from_hex(self.macro_color) if self.state == "normal" else get_color_from_hex("#555577")
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(6)]

<DarkTextInput@TextInput>:
    background_normal: ""
    background_active: ""
    background_color: get_color_from_hex("#1a1a2e")
    foreground_color: get_color_from_hex("#e0e0e0")
    cursor_color: get_color_from_hex("#00ffcc")
    padding: dp(8), dp(8)
    font_size: sp(13)
    multiline: False

<DarkScrollText@TextInput>:
    background_normal: ""
    background_active: ""
    background_color: get_color_from_hex("#08080f")
    foreground_color: get_color_from_hex("#00cc99")
    cursor_color: get_color_from_hex("#00ffcc")
    padding: dp(8), dp(8)
    font_size: sp(11)
    readonly: True
    multiline: True

<DashboardScreen>:
    BoxLayout:
        orientation: "vertical"
        HeaderBar:
            id: header
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                padding: dp(12)
                spacing: dp(12)
                BoxLayout:
                    size_hint_y: None
                    height: dp(50)
                    spacing: dp(8)
                    ActionButton:
                        text: "CONNECT"
                        on_release: root.do_connect()
                    ActionButton:
                        text: "REFRESH"
                        on_release: root.do_refresh()
                    ActionButton:
                        text: "POWER OFF"
                        on_release: root.do_poweroff()
                        canvas.before:
                            Color:
                                rgba: get_color_from_hex("#ff2244") if self.state == "normal" else get_color_from_hex("#cc1133")
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [dp(6)]
                    ActionButton:
                        text: "REBOOT"
                        on_release: root.do_reboot()
                        canvas.before:
                            Color:
                                rgba: get_color_from_hex("#ff6600") if self.state == "normal" else get_color_from_hex("#cc5500")
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [dp(6)]
                GridLayout:
                    id: metrics_grid
                    cols: 2
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(8)
                    row_default_height: dp(80)
                    row_force_default: True
                Label:
                    id: info_lbl
                    text: "Tap CONNECT to start"
                    font_size: sp(12)
                    color: get_color_from_hex("#555577")
                    size_hint_y: None
                    height: dp(30)

<RemoteScreen>:
    BoxLayout:
        orientation: "vertical"
        HeaderBar:
            id: header
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                padding: dp(12)
                spacing: dp(12)
                BoxLayout:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(220)
                    canvas.before:
                        Color:
                            rgba: get_color_from_hex("#000000")
                        Rectangle:
                            pos: self.pos
                            size: self.size
                        Color:
                            rgba: get_color_from_hex("#1e3a5f")
                        Line:
                            rectangle: [self.x, self.y, self.width, self.height]
                            width: dp(1)
                    KivyImage:
                        id: screenshot_img
                        source: ""
                        allow_stretch: True
                        keep_ratio: True
                    Button:
                        id: capture_btn
                        text: "TAP TO CAPTURE"
                        size_hint_y: None
                        height: dp(36)
                        background_normal: ""
                        background_color: (0,0,0,0.5)
                        color: get_color_from_hex("#00ffcc")
                        on_release: root.capture_screenshot()
                Label:
                    text: "QUICK ACTIONS"
                    font_size: sp(12)
                    bold: True
                    color: get_color_from_hex("#555577")
                    size_hint_y: None
                    height: dp(24)
                GridLayout:
                    cols: 3
                    size_hint_y: None
                    height: dp(120)
                    spacing: dp(6)
                    ActionButton:
                        text: "VOL -"
                        on_release: root.quick_cmd("amixer sset Master 5%-")
                    ActionButton:
                        text: "VOL +"
                        on_release: root.quick_cmd("amixer sset Master 5%+")
                    ActionButton:
                        text: "BRIGHT -"
                        on_release: root.quick_cmd("echo $(( $(cat /sys/class/backlight/*/brightness 2>/dev/null | head -1) - 10 )) > /sys/class/backlight/*/brightness 2>/dev/null || true")
                    ActionButton:
                        text: "BRIGHT +"
                        on_release: root.quick_cmd("echo $(( $(cat /sys/class/backlight/*/brightness 2>/dev/null | head -1) + 10 )) > /sys/class/backlight/*/brightness 2>/dev/null || true")
                    ActionButton:
                        text: "KILL GAME"
                        on_release: root.quick_cmd("killall retroarch drastic PPSSPP mupen64plus flycast scummvm pico8 PortMaster 2>/dev/null; true")
                        canvas.before:
                            Color:
                                rgba: get_color_from_hex("#ff2244") if self.state == "normal" else get_color_from_hex("#cc1133")
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [dp(6)]
                    ActionButton:
                        text: "SCREENSHOT"
                        on_release: root.capture_screenshot()
                BoxLayout:
                    size_hint_y: None
                    height: dp(36)
                    Label:
                        text: "MACRO DECK"
                        font_size: sp(12)
                        bold: True
                        color: get_color_from_hex("#555577")
                        size_hint_x: 0.7
                    Button:
                        text: "EDIT"
                        size_hint_x: 0.3
                        background_normal: ""
                        background_color: (0,0,0,0)
                        color: get_color_from_hex("#ff00ff")
                        on_release: root.open_macro_editor()
                GridLayout:
                    id: macro_grid
                    cols: 3
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(6)
                    row_default_height: dp(56)
                    row_force_default: True

<FilesScreen>:
    BoxLayout:
        orientation: "vertical"
        HeaderBar:
            id: header
        BoxLayout:
            orientation: "vertical"
            padding: dp(12)
            spacing: dp(8)
            Label:
                text: "LOCAL FILE"
                font_size: sp(11)
                color: get_color_from_hex("#555577")
                size_hint_y: None
                height: dp(20)
            BoxLayout:
                size_hint_y: None
                height: dp(44)
                DarkTextInput:
                    id: local_path
                    hint_text: "/storage/emulated/0/roms/game.gba"
                Button:
                    text: "BROWSE"
                    size_hint_x: None
                    width: dp(80)
                    background_normal: ""
                    background_color: get_color_from_hex("#1a1a2e")
                    color: get_color_from_hex("#00ffcc")
                    on_release: root.open_file_chooser()
            Label:
                text: "REMOTE PATH"
                font_size: sp(11)
                color: get_color_from_hex("#555577")
                size_hint_y: None
                height: dp(20)
            DarkTextInput:
                id: remote_path
                hint_text: "/mnt/mmc/MUOS/rom/Game Boy Advance/"
                size_hint_y: None
                height: dp(44)
            ActionButton:
                text: "SEND VIA SFTP"
                size_hint_y: None
                height: dp(50)
                on_release: root.send_file()
            Label:
                id: file_status
                text: "Ready"
                font_size: sp(12)
                color: get_color_from_hex("#555577")
                size_hint_y: None
                height: dp(30)
            Widget:
                size_hint_y: 1

<TerminalScreen>:
    BoxLayout:
        orientation: "vertical"
        HeaderBar:
            id: header
        BoxLayout:
            orientation: "vertical"
            padding: dp(12)
            spacing: dp(8)
            DarkScrollText:
                id: term_output
                hint_text: "Terminal output will appear here..."
                size_hint_y: 0.85
            BoxLayout:
                size_hint_y: None
                height: dp(50)
                spacing: dp(8)
                DarkTextInput:
                    id: term_input
                    hint_text: "Enter command..."
                    size_hint_x: 0.8
                    on_text_validate: root.run_command()
                ActionButton:
                    text: "RUN"
                    size_hint_x: 0.2
                    on_release: root.run_command()

<SettingsScreen>:
    BoxLayout:
        orientation: "vertical"
        HeaderBar:
            id: header
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                padding: dp(16)
                spacing: dp(12)
                Label:
                    text: "CONNECTION"
                    font_size: sp(14)
                    bold: True
                    color: get_color_from_hex("#00ffcc")
                    size_hint_y: None
                    height: dp(30)
                Label:
                    text: "IP Address"
                    font_size: sp(11)
                    color: get_color_from_hex("#555577")
                    size_hint_y: None
                    height: dp(20)
                DarkTextInput:
                    id: cfg_ip
                    hint_text: "192.168.1.100"
                Label:
                    text: "SSH Port"
                    font_size: sp(11)
                    color: get_color_from_hex("#555577")
                    size_hint_y: None
                    height: dp(20)
                DarkTextInput:
                    id: cfg_port
                    hint_text: "22"
                    input_filter: "int"
                Label:
                    text: "Username"
                    font_size: sp(11)
                    color: get_color_from_hex("#555577")
                    size_hint_y: None
                    height: dp(20)
                DarkTextInput:
                    id: cfg_user
                    hint_text: "root"
                Label:
                    text: "Password"
                    font_size: sp(11)
                    color: get_color_from_hex("#555577")
                    size_hint_y: None
                    height: dp(20)
                DarkTextInput:
                    id: cfg_pass
                    hint_text: "root"
                    password: True
                BoxLayout:
                    size_hint_y: None
                    height: dp(40)
                    CheckBox:
                        id: cfg_auto
                        size_hint_x: None
                        width: dp(40)
                        color: get_color_from_hex("#00ffcc")
                    Label:
                        text: "Auto-connect on startup"
                        font_size: sp(12)
                        color: get_color_from_hex("#e0e0e0")
                BoxLayout:
                    size_hint_y: None
                    height: dp(50)
                    spacing: dp(8)
                    ActionButton:
                        text: "SAVE & CONNECT"
                        on_release: root.save_and_connect()
                    ActionButton:
                        text: "DISCONNECT"
                        on_release: root.do_disconnect()
                        canvas.before:
                            Color:
                                rgba: get_color_from_hex("#ff2244") if self.state == "normal" else get_color_from_hex("#cc1133")
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [dp(6)]
                Label:
                    text: "MACROS (JSON)"
                    font_size: sp(14)
                    bold: True
                    color: get_color_from_hex("#ff00ff")
                    size_hint_y: None
                    height: dp(30)
                DarkScrollText:
                    id: cfg_macros
                    hint_text: '[{"label":"Kill","cmd":"killall retroarch","color":"#ff2244"}]'
                    size_hint_y: None
                    height: dp(200)
                ActionButton:
                    text: "SAVE MACROS"
                    size_hint_y: None
                    height: dp(44)
                    on_release: root.save_macros()
"""

PROBE_SCRIPT = r"""
echo "PROBE_BEGIN"
read c1 < /proc/stat; sleep 0.3; read c2 < /proc/stat
echo "CPU_STAT1=$(echo $c1 | cut -d' ' -f2-)"
echo "CPU_STAT2=$(echo $c2 | cut -d' ' -f2-)"
echo "LOAD=$(cut -d' ' -f1-3 /proc/loadavg)"
echo "UPTIME=$(cut -d' ' -f1 /proc/uptime)"
echo "MEMTOTAL=$(awk '/MemTotal/{print $2}' /proc/meminfo)"
echo "MEMAVAIL=$(awk '/MemAvailable/{print $2}' /proc/meminfo)"
for p in /sys/class/power_supply/*; do
  [ -f "$p/capacity" ] || continue
  echo "BAT_CAP=$(cat $p/capacity 2>/dev/null)"
  echo "BAT_STATUS=$(cat $p/status 2>/dev/null)"
  break
done
for z in /sys/class/thermal/thermal_zone*; do
  [ -f "$z/temp" ] || continue
  echo "TEMP=$(cat $z/type 2>/dev/null):$(cat $z/temp)"
done
for m in /mnt/mmc /mnt/sdcard /; do
  df -k "$m" 2>/dev/null | awk -v M="$m" 'NR==2{printf "DISK=%s:%s:%s:%s\n", M, $2, $3, $5}'
done
for i in wlan0 eth0 usb0; do
  [ -d "/sys/class/net/$i" ] || continue
  ip=$(ip -4 -o addr show $i 2>/dev/null | awk '{split($4,a,"/"); print a[1]}')
  [ -n "$ip" ] && echo "NET=$i:$ip"
done
awk '/wlan/{printf "WIFI_SIG=%s\n", $4}' /proc/net/wireless 2>/dev/null
for b in /sys/class/backlight/*; do
  [ -f "$b/brightness" ] || continue
  echo "BRIGHT=$(cat $b/brightness):$(cat $b/max_brightness 2>/dev/null)"
  break
done
vol=$(amixer sget Master 2>/dev/null | awk -F'[][]' '/\[/{print $2; exit}' | tr -d '%')
[ -n "$vol" ] && echo "VOL=$vol"
app=""
for d in /proc/[0-9]*; do
  [ -r "$d/cmdline" ] || continue
  cmd=$(tr '\0' ' ' < "$d/cmdline" 2>/dev/null)
  case "$cmd" in
    *retroarch*) app="RETROARCH"; break;;
    */drastic*|*DraStic*) app="DRASTIC"; break;;
    *PPSSPP*|*ppsspp*) app="PPSSPP"; break;;
    *mupen64plus*) app="MUPEN64"; break;;
    *flycast*) app="FLYCAST"; break;;
    *scummvm*) app="SCUMMVM"; break;;
    *pico8*) app="PICO8"; break;;
    *PortMaster*) app="PORTMASTER"; break;;
  esac
done
if [ -z "$app" ]; then
  for d in /proc/[0-9]*; do
    [ -r "$d/comm" ] || continue
    c=$(cat "$d/comm" 2>/dev/null)
    case "$c" in
      mux*) app="MUOS:$c"; break;;
    esac
  done
fi
echo "APP=${app:-IDLE}"
echo "PROBE_END"
"""


def parse_probe(text):
    s = {"temps": [], "disks": [], "raw": text}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        if key in ("CPU_STAT1", "CPU_STAT2"):
            try:
                vals = [int(x) for x in val.split()]
                idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
                s[key] = (idle, sum(vals))
            except Exception:
                pass
        elif key == "LOAD":
            try:
                s["load"] = [float(x) for x in val.split()[:3]]
            except Exception:
                s["load"] = []
        elif key == "UPTIME":
            try:
                s["uptime_s"] = float(val)
            except Exception:
                pass
        elif key in ("MEMTOTAL", "MEMAVAIL", "BAT_CAP", "VOL"):
            try:
                s[key.lower()] = int(val)
            except Exception:
                s[key.lower()] = val
        elif key in ("BAT_STATUS", "APP", "WIFI_SIG"):
            s[key.lower()] = val
        elif key == "TEMP":
            try:
                zone, t = val.split(":", 1)
                tc = int(t) / 1000.0
                if 0 < tc < 150:
                    s["temps"].append({"zone": zone, "temp_c": round(tc, 1)})
            except Exception:
                pass
        elif key == "DISK":
            try:
                mount, total, used, pct = val.split(":")
                s["disks"].append({"mount": mount,
                                   "total_mb": round(int(total) / 1024, 0),
                                   "used_mb": round(int(used) / 1024, 0),
                                   "pct": int(pct.rstrip("%"))})
            except Exception:
                pass
        elif key == "NET":
            try:
                iface, ip = val.split(":")
                s.setdefault("nets", []).append({"iface": iface, "ip": ip})
            except Exception:
                pass
        elif key == "BRIGHT":
            try:
                cur, mx = val.split(":")
                s["brightness"] = int(cur)
                s["brightness_max"] = int(mx or 255)
            except Exception:
                pass
    if "CPU_STAT1" in s and "CPU_STAT2" in s:
        didle = s["CPU_STAT2"][0] - s["CPU_STAT1"][0]
        dtot = s["CPU_STAT2"][1] - s["CPU_STAT1"][1]
        s["cpu_pct"] = round(100.0 * (1.0 - didle / dtot), 1) if dtot > 0 else 0.0
    if "memtotal" in s:
        total = s["memtotal"]
        used = total - s.get("memavail", 0)
        s["ram"] = {"total_mb": round(total / 1024, 0), "used_mb": round(used / 1024, 0),
                    "pct": round(100.0 * used / total, 1) if total else 0.0}
    s["ts"] = time.time()
    return s


class ConsoleClient(object):
    def __init__(self):
        self.client = None
        self.connected = False
        self.lock = threading.Lock()
        self.ip = None
        self.port = None
        self.user = None
        self.password = None

    def connect(self, ip, port, user, password):
        if not HAS_PARAMIKO:
            return False
        with self.lock:
            self.disconnect()
            try:
                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.client.connect(
                    ip, port=int(port), username=user, password=password,
                    timeout=8, banner_timeout=8, auth_timeout=8
                )
                self.connected = True
                self.ip = ip
                self.port = int(port)
                self.user = user
                self.password = password
                return True
            except Exception as e:
                self.connected = False
                self.client = None
                raise e

    def disconnect(self):
        with self.lock:
            self.connected = False
            try:
                if self.client:
                    self.client.close()
            except Exception:
                pass
            self.client = None

    def exec_cmd(self, cmd, timeout=8):
        if not self.connected or not self.client:
            return None, "Not connected"
        try:
            stdin, stdout, stderr = self.client.exec_command(cmd, timeout=timeout)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            return out, err
        except Exception as e:
            return None, str(e)

    def put_file(self, local_path, remote_path):
        if not self.connected or not self.client:
            return False, "Not connected"
        try:
            transport = self.client.get_transport()
            sftp = paramiko.SFTPClient.from_transport(transport)
            parts = remote_path.strip("/").split("/")
            dir_path = "/" + "/".join(parts[:-1]) if len(parts) > 1 else "/"
            cur = ""
            for p in dir_path.strip("/").split("/"):
                cur += "/" + p
                try:
                    sftp.stat(cur)
                except FileNotFoundError:
                    try:
                        sftp.mkdir(cur)
                    except Exception:
                        pass
            sftp.put(local_path, remote_path)
            sftp.close()
            return True, "OK"
        except Exception as e:
            return False, str(e)

    def grab_fb(self):
        if not self.connected:
            return None
        try:
            meta = self.exec_cmd(
                "cat /sys/class/graphics/fb0/virtual_size; "
                "cat /sys/class/graphics/fb0/bits_per_pixel; "
                "cat /sys/class/graphics/fb0/stride; "
                "cat /sys/class/graphics/fb0/red /sys/class/graphics/fb0/green "
                "/sys/class/graphics/fb0/blue 2>/dev/null; "
                "fbset 2>/dev/null | grep -E 'geometry|mode' | head -3; "
                "cat /sys/class/graphics/fb0/modes 2>/dev/null | head -1",
                timeout=6
            )
            if meta[1]:
                return None
            lines = [x.strip() for x in meta[0].splitlines() if x.strip()]
            if len(lines) < 2:
                return None

            vw, vh = (int(x) for x in lines[0].replace(",", " ").split()[:2])
            bpp = int(lines[1])
            stride = int(lines[2]) if len(lines) > 2 and lines[2].isdigit() else None

            real_w, real_h = vw, vh
            for ln in lines[3:]:
                if ln.startswith("geometry"):
                    parts = ln.split()
                    if len(parts) >= 3:
                        try:
                            real_w = int(parts[1])
                            real_h = int(parts[2])
                        except ValueError:
                            pass
                elif "x" in ln and "p" in ln:
                    m = re.search(r'(\d+)x(\d+)', ln)
                    if m:
                        real_w = int(m.group(1))
                        real_h = int(m.group(2))

            h = real_h if vh > real_h * 1.5 else vh
            w = vw if vw == real_w else real_w

            fmt = {"r": (11, 5), "g": (5, 6), "b": (0, 5)}
            if bpp == 32:
                fmt = {"r": (16, 8), "g": (8, 8), "b": (0, 8)}
            try:
                if len(lines) >= 6:
                    fmt = {"r": tuple(int(v) for v in lines[3].split(",")),
                           "g": tuple(int(v) for v in lines[4].split(",")),
                           "b": tuple(int(v) for v in lines[5].split(","))}
            except Exception:
                pass

            b64 = self.exec_cmd(
                "base64 /dev/fb0 2>/dev/null || dd if=/dev/fb0 bs=65536 2>/dev/null | base64",
                timeout=25
            )
            if b64[1]:
                return None
            try:
                raw = base64.b64decode(b64[0])
            except Exception:
                return None

            if stride is None:
                stride = vw * (bpp // 8)
            need = stride * h
            if len(raw) < need:
                return None

            rgb = bytearray(w * h * 3)
            ro, rl = fmt["r"]
            go, gl = fmt["g"]
            bo, bl = fmt["b"]
            rmax = (1 << rl) - 1
            gmax = (1 << gl) - 1
            bmax = (1 << bl) - 1
            shift = bpp // 8
            di = 0
            for y in range(h):
                row = y * stride
                if shift == 2:
                    vals = struct.unpack_from("<{}H".format(w), raw, row)
                    for v in vals:
                        rgb[di] = (((v >> ro) & rmax) * 255 // rmax)
                        rgb[di + 1] = (((v >> go) & gmax) * 255 // gmax)
                        rgb[di + 2] = (((v >> bo) & bmax) * 255 // bmax)
                        di += 3
                else:
                    vals = struct.unpack_from("<{}I".format(w), raw, row)
                    for v in vals:
                        rgb[di] = (((v >> ro) & rmax) * 255 // rmax)
                        rgb[di + 1] = (((v >> go) & gmax) * 255 // gmax)
                        rgb[di + 2] = (((v >> bo) & bmax) * 255 // bmax)
                        di += 3
            return w, h, bytes(rgb)
        except Exception:
            return None

class ConfigManager(object):
    DEFAULT_MACROS = [
        {"label": "Kill RetroArch", "cmd": "killall retroarch", "color": "#ff2244"},
        {"label": "Reboot", "cmd": "reboot", "color": "#ff6600"},
        {"label": "Power Off", "cmd": "poweroff", "color": "#ff2244"},
        {"label": "SysInfo", "cmd": "uname -a && uptime", "color": "#f0e130"},
        {"label": "List ROMs", "cmd": "ls /mnt/mmc/MUOS/rom/ 2>/dev/null || ls /mnt/sdcard/rom/ 2>/dev/null", "color": "#ff00ff"},
        {"label": "Screenshot", "cmd": "cat /dev/fb0 | base64", "color": "#00ffcc"},
    ]

    def __init__(self, app):
        self.app = app
        self.data = {
            "ip": "192.168.1.100",
            "port": 22,
            "user": "root",
            "password": "",
            "auto_connect": False,
            "macros": list(self.DEFAULT_MACROS),
        }
        self.load()

    def _path(self):
        try:
            base = self.app.user_data_dir
        except Exception:
            base = os.path.expanduser("~")
        return os.path.join(base, ".void_androidstation.json")

    def load(self):
        p = self._path()
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    loaded = json.load(f)
                    self.data.update(loaded)
            except Exception:
                pass

    def save(self):
        p = self._path()
        try:
            with open(p, "w") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass


class DashboardScreen(Screen):
    def __init__(self, **kwargs):
        super(DashboardScreen, self).__init__(**kwargs)
        self.app = App.get_running_app()
        self.metrics = [
            ("CPU", "cpu_pct", "%"),
            ("RAM", "ram", "MB"),
            ("BATTERY", "bat_cap", "%"),
            ("TEMP", "temps", "°C"),
            ("DISK", "disks", ""),
            ("APP", "app", ""),
        ]
        self.metric_widgets = {}

    def on_enter(self):
        Clock.schedule_once(self._build_metrics, 0)
        self._update_status()

    def _build_metrics(self, dt):
        grid = self.ids.metrics_grid
        grid.clear_widgets()
        self.metric_widgets = {}
        for title, key, unit in self.metrics:
            card = MetricCard()
            card.ids.title.text = title
            card.ids.value.text = "--"
            grid.add_widget(card)
            self.metric_widgets[key] = card

    def _update_status(self):
        hdr = self.ids.header
        if self.app.client.connected:
            hdr.ids.status_lbl.text = "● ONLINE"
            hdr.ids.status_lbl.color = CYAN
        else:
            hdr.ids.status_lbl.text = "● OFFLINE"
            hdr.ids.status_lbl.color = TEXT_DIM

    def do_connect(self):
        def worker():
            cfg = self.app.config.data
            try:
                self.app.client.connect(cfg["ip"], cfg["port"], cfg["user"], cfg["password"])
                Clock.schedule_once(lambda dt: self._on_connect_ok(), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self._on_connect_err(str(e)), 0)
        threading.Thread(target=worker, daemon=True).start()

    def _on_connect_ok(self):
        self._update_status()
        self.ids.info_lbl.text = "Connected to {}@{}".format(
            self.app.config.data["user"], self.app.config.data["ip"]
        )
        self.ids.info_lbl.color = CYAN
        self.do_refresh()

    def _on_connect_err(self, msg):
        self._update_status()
        self.ids.info_lbl.text = "Connection failed: " + msg
        self.ids.info_lbl.color = RED

    def do_refresh(self):
        if not self.app.client.connected:
            self.ids.info_lbl.text = "Not connected"
            self.ids.info_lbl.color = ORANGE
            return

        def worker():
            out, err = self.app.client.exec_cmd(PROBE_SCRIPT, timeout=10)
            if err and not out:
                Clock.schedule_once(lambda dt: self._on_probe_err(err), 0)
                return
            stats = parse_probe(out)
            Clock.schedule_once(lambda dt: self._update_metrics(stats), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _on_probe_err(self, msg):
        self.ids.info_lbl.text = "Probe error: " + msg[:100]
        self.ids.info_lbl.color = RED

    def _update_metrics(self, stats):
        for key, card in self.metric_widgets.items():
            val = "--"
            color = CYAN
            if key == "cpu_pct":
                v = stats.get("cpu_pct", 0)
                val = "{:.1f}%".format(v)
                color = ORANGE if v > 70 else CYAN
            elif key == "ram":
                ram = stats.get("ram", {})
                used = ram.get("used_mb", 0)
                total = ram.get("total_mb", 0)
                val = "{}/{} MB".format(int(used), int(total))
                color = ORANGE if ram.get("pct", 0) > 80 else CYAN
            elif key == "bat_cap":
                cap = stats.get("bat_cap", "N/A")
                val = "{}%".format(cap) if isinstance(cap, int) else str(cap)
                color = GREEN if isinstance(cap, int) and cap > 30 else RED
            elif key == "temps":
                temps = stats.get("temps", [])
                if temps:
                    t = max(t["temp_c"] for t in temps)
                    val = "{:.1f}°C".format(t)
                    color = RED if t > 70 else (ORANGE if t > 50 else CYAN)
                else:
                    val = "N/A"
            elif key == "disks":
                disks = stats.get("disks", [])
                if disks:
                    d = disks[0]
                    val = "{}% used".format(d.get("pct", 0))
                    color = RED if d.get("pct", 0) > 90 else CYAN
                else:
                    val = "N/A"
            elif key == "app":
                val = stats.get("app", "IDLE")
                color = MAGENTA
            card.ids.value.text = val
            card.ids.value.color = color
        self.ids.info_lbl.text = "Last update: " + datetime.now().strftime("%H:%M:%S")
        self.ids.info_lbl.color = TEXT

    def do_poweroff(self):
        self._confirm("Power Off", "poweroff")

    def do_reboot(self):
        self._confirm("Reboot", "reboot")

    def _confirm(self, action, cmd):
        if not self.app.client.connected:
            self.ids.info_lbl.text = "Not connected"
            return
        content = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(10))
        content.add_widget(Label(text="Execute {}?".format(action), color=TEXT, font_size=sp(16)))
        btn_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        popup = Popup(title="Confirm", content=content, size_hint=(0.8, 0.3), auto_dismiss=False)

        def do_it():
            popup.dismiss()
            threading.Thread(target=lambda: self.app.client.exec_cmd(cmd), daemon=True).start()
            self.ids.info_lbl.text = action + " sent"

        def cancel():
            popup.dismiss()

        btn_box.add_widget(Button(text="YES", on_release=lambda x: do_it(), background_color=RED, color=BG0))
        btn_box.add_widget(Button(text="NO", on_release=lambda x: cancel(), background_color=BG1, color=TEXT))
        content.add_widget(btn_box)
        popup.open()


class RemoteScreen(Screen):
    def __init__(self, **kwargs):
        super(RemoteScreen, self).__init__(**kwargs)
        self.app = App.get_running_app()

    def on_enter(self):
        self._update_status()
        self._build_macros()

    def _update_status(self):
        hdr = self.ids.header
        if self.app.client.connected:
            hdr.ids.status_lbl.text = "● ONLINE"
            hdr.ids.status_lbl.color = CYAN
        else:
            hdr.ids.status_lbl.text = "● OFFLINE"
            hdr.ids.status_lbl.color = TEXT_DIM

    def quick_cmd(self, cmd):
        if not self.app.client.connected:
            self.ids.capture_btn.text = "NOT CONNECTED"
            return

        def worker():
            out, err = self.app.client.exec_cmd(cmd, timeout=6)
            result = (out or "") + (err or "")
            Clock.schedule_once(lambda dt: self._show_result(result[:200]), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _show_result(self, text):
        self.ids.capture_btn.text = text[:60] if text else "OK"

    def capture_screenshot(self):
        if not self.app.client.connected:
            self.ids.capture_btn.text = "NOT CONNECTED"
            return
        self.ids.capture_btn.text = "CAPTURING..."

        def worker():
            result = self.app.client.grab_fb()
            if result:
                w, h, rgb = result
                Clock.schedule_once(lambda dt: self._show_screenshot(w, h, rgb), 0)
            else:
                Clock.schedule_once(lambda dt: self._screenshot_err(), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _show_screenshot(self, w, h, rgb):
        try:
            img = Image.frombytes("RGB", (w, h), rgb)
            tmp = os.path.join(tempfile.gettempdir(), "void_as_cap.png")
            img.save(tmp, "PNG")
            self.ids.screenshot_img.source = tmp
            self.ids.screenshot_img.reload()
            self.ids.capture_btn.text = "{}x{} CAPTURED".format(w, h)
        except Exception as e:
            self.ids.capture_btn.text = "ERROR: " + str(e)[:40]

    def _screenshot_err(self):
        self.ids.capture_btn.text = "CAPTURE FAILED"

    def _build_macros(self):
        grid = self.ids.macro_grid
        grid.clear_widgets()
        macros = self.app.config.data.get("macros", [])
        for m in macros:
            btn = MacroButton(text=m.get("label", "???"), macro_color=m.get("color", "#ff6600"))
            btn.bind(on_release=lambda inst, cmd=m.get("cmd", ""): self._run_macro(cmd))
            grid.add_widget(btn)
        while len(grid.children) < 6:
            grid.add_widget(Widget())
        grid.height = grid.minimum_height

    def _run_macro(self, cmd):
        self.quick_cmd(cmd)

    def open_macro_editor(self):
        self.app.sm.current = "settings"


class FilesScreen(Screen):
    def __init__(self, **kwargs):
        super(FilesScreen, self).__init__(**kwargs)
        self.app = App.get_running_app()

    def on_enter(self):
        self._update_status()

    def _update_status(self):
        hdr = self.ids.header
        if self.app.client.connected:
            hdr.ids.status_lbl.text = "● ONLINE"
            hdr.ids.status_lbl.color = CYAN
        else:
            hdr.ids.status_lbl.text = "● OFFLINE"
            hdr.ids.status_lbl.color = TEXT_DIM

    def open_file_chooser(self):
        content = BoxLayout(orientation="vertical")
        start_path = os.path.expanduser("~")
        chooser = FileChooserListView(path=start_path, filters=["*"])
        content.add_widget(chooser)
        btn_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(6))
        popup = Popup(title="Select File", content=content, size_hint=(0.9, 0.8), auto_dismiss=False)

        def select():
            if chooser.selection:
                self.ids.local_path.text = chooser.selection[0]
            popup.dismiss()

        def cancel():
            popup.dismiss()

        btn_box.add_widget(Button(text="SELECT", on_release=lambda x: select()))
        btn_box.add_widget(Button(text="CANCEL", on_release=lambda x: cancel()))
        content.add_widget(btn_box)
        popup.open()

    def send_file(self):
        local = self.ids.local_path.text.strip()
        remote = self.ids.remote_path.text.strip()
        if not local or not remote:
            self.ids.file_status.text = "Select file and enter remote path"
            self.ids.file_status.color = ORANGE
            return
        if not os.path.exists(local):
            self.ids.file_status.text = "Local file not found"
            self.ids.file_status.color = RED
            return
        if not self.app.client.connected:
            self.ids.file_status.text = "Not connected"
            self.ids.file_status.color = RED
            return
        self.ids.file_status.text = "Sending..."
        self.ids.file_status.color = ORANGE

        def worker():
            ok, msg = self.app.client.put_file(local, remote)
            if ok:
                Clock.schedule_once(lambda dt: self._send_ok(os.path.basename(local)), 0)
            else:
                Clock.schedule_once(lambda dt: self._send_err(msg), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _send_ok(self, name):
        self.ids.file_status.text = "Sent: " + name
        self.ids.file_status.color = CYAN

    def _send_err(self, msg):
        self.ids.file_status.text = "Error: " + msg[:80]
        self.ids.file_status.color = RED


class TerminalScreen(Screen):
    def __init__(self, **kwargs):
        super(TerminalScreen, self).__init__(**kwargs)
        self.app = App.get_running_app()
        self.history = []

    def on_enter(self):
        self._update_status()

    def _update_status(self):
        hdr = self.ids.header
        if self.app.client.connected:
            hdr.ids.status_lbl.text = "● ONLINE"
            hdr.ids.status_lbl.color = CYAN
        else:
            hdr.ids.status_lbl.text = "● OFFLINE"
            hdr.ids.status_lbl.color = TEXT_DIM

    def run_command(self):
        cmd = self.ids.term_input.text.strip()
        if not cmd:
            return
        if not self.app.client.connected:
            self._append("Not connected\n")
            return
        self.history.append(cmd)
        self.ids.term_input.text = ""
        self._append("$ " + cmd + "\n")

        def worker():
            out, err = self.app.client.exec_cmd(cmd, timeout=15)
            result = (out or "") + (err or "")
            Clock.schedule_once(lambda dt: self._append(result + "\n"), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _append(self, text):
        self.ids.term_output.text += text
        self.ids.term_output.cursor = (len(self.ids.term_output.text), 0)


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super(SettingsScreen, self).__init__(**kwargs)
        self.app = App.get_running_app()

    def on_enter(self):
        cfg = self.app.config.data
        self.ids.cfg_ip.text = cfg.get("ip", "")
        self.ids.cfg_port.text = str(cfg.get("port", 22))
        self.ids.cfg_user.text = cfg.get("user", "")
        self.ids.cfg_pass.text = cfg.get("password", "")
        self.ids.cfg_auto.active = cfg.get("auto_connect", False)
        self.ids.cfg_macros.text = json.dumps(cfg.get("macros", []), indent=2, ensure_ascii=False)
        self._update_status()

    def _update_status(self):
        hdr = self.ids.header
        if self.app.client.connected:
            hdr.ids.status_lbl.text = "● ONLINE"
            hdr.ids.status_lbl.color = CYAN
        else:
            hdr.ids.status_lbl.text = "● OFFLINE"
            hdr.ids.status_lbl.color = TEXT_DIM

    def save_and_connect(self):
        cfg = self.app.config.data
        cfg["ip"] = self.ids.cfg_ip.text.strip()
        try:
            cfg["port"] = int(self.ids.cfg_port.text.strip())
        except ValueError:
            cfg["port"] = 22
        cfg["user"] = self.ids.cfg_user.text.strip()
        cfg["password"] = self.ids.cfg_pass.text.strip()
        cfg["auto_connect"] = self.ids.cfg_auto.active
        self.app.config.save()

        def worker():
            try:
                self.app.client.connect(cfg["ip"], cfg["port"], cfg["user"], cfg["password"])
                Clock.schedule_once(lambda dt: self._update_status(), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self._show_err(str(e)), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _show_err(self, msg):
        self.ids.header.ids.status_lbl.text = "● ERROR"
        self.ids.header.ids.status_lbl.color = RED

    def do_disconnect(self):
        self.app.client.disconnect()
        self._update_status()

    def save_macros(self):
        try:
            macros = json.loads(self.ids.cfg_macros.text)
            self.app.config.data["macros"] = macros
            self.app.config.save()
            self.ids.header.ids.status_lbl.text = "● MACROS SAVED"
            self.ids.header.ids.status_lbl.color = CYAN
        except Exception:
            self.ids.header.ids.status_lbl.text = "● JSON ERROR"
            self.ids.header.ids.status_lbl.color = RED


class VOIDAndroidStation(App):
    def build(self):
        Builder.load_string(KV)
        self.client = ConsoleClient()
        self.config = ConfigManager(self)

        root = BoxLayout(orientation="vertical")
        self.sm = ScreenManager(transition=SlideTransition(duration=0.2))
        self.sm.add_widget(DashboardScreen(name="dashboard"))
        self.sm.add_widget(RemoteScreen(name="remote"))
        self.sm.add_widget(FilesScreen(name="files"))
        self.sm.add_widget(TerminalScreen(name="terminal"))
        self.sm.add_widget(SettingsScreen(name="settings"))
        root.add_widget(self.sm)

        nav = BoxLayout(size_hint_y=None, height=dp(56))
        self.nav_buttons = {}
        for name, label in [
            ("dashboard", "DASH"),
            ("remote", "REMOTE"),
            ("files", "FILES"),
            ("terminal", "TERM"),
            ("settings", "SETUP"),
        ]:
            btn = NavButton(text=label)
            btn.bind(on_release=lambda inst, n=name: self._switch_screen(n))
            nav.add_widget(btn)
            self.nav_buttons[name] = btn
        root.add_widget(nav)

        self._update_nav("dashboard")
        self.sm.bind(current=lambda inst, val: self._update_nav(val))

        if self.config.data.get("auto_connect"):
            Clock.schedule_once(self._auto_connect, 1.0)

        return root

    def _switch_screen(self, name):
        self.sm.current = name

    def _update_nav(self, name):
        for n, btn in self.nav_buttons.items():
            btn.state = "down" if n == name else "normal"

    def _auto_connect(self, dt):
        cfg = self.config.data
        try:
            self.client.connect(cfg["ip"], cfg["port"], cfg["user"], cfg["password"])
        except Exception:
            pass


if __name__ == "__main__":
    VOIDAndroidStation().run()
