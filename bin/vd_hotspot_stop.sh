#!/bin/sh
# ============================================================================
#  VOIDDESK // vd_hotspot_stop -- ferma l'hotspot nativo, ripristina la radio
#  Simmetrico allo start: ferma i processi (host o chroot, quello che sia),
#  e smonta il chroot SOLO se l'avevamo montato noi per l'occasione.
# ============================================================================
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA="$APP_DIR/data"
LOG="$DATA/hotspot.log"
IMG="$DATA/xfce.img"
MNT="${VD_XFCE_MNT:-$DATA/xfce_mnt}"
mkdir -p "$DATA"

IFACE="${VD_AP_IFACE:-}"
WLAN1_SYSFS="${VD_WLAN1_SYSFS:-/sys/class/net/wlan1}"
if [ -z "$IFACE" ]; then
	if [ -d "$WLAN1_SYSFS" ]; then
		IFACE=wlan1
	else
		IFACE=wlan0
	fi
fi
HOSTAPD_BIN="${VD_HOSTAPD_BIN:-hostapd}"
DNSMASQ_BIN="${VD_DNSMASQ_BIN:-dnsmasq}"
IP_BIN="${VD_IPCMD:-ip}"

MODE="$(cat "$DATA/.hotspot_mode" 2>/dev/null || echo host)"
echo "$(date) === hotspot stop (iface=$IFACE modalita'=$MODE) ===" >>"$LOG"

pkill -f "$HOSTAPD_BIN.*hostapd.conf" 2>/dev/null
pkill -f "$DNSMASQ_BIN.*dnsmasq_ap.conf" 2>/dev/null
if [ "$MODE" = "chroot" ]; then
	[ -f "$MNT/tmp/dnsmasq_ap.pid" ] && \
		kill "$(cat "$MNT/tmp/dnsmasq_ap.pid")" 2>/dev/null
	rm -f "$MNT/tmp/dnsmasq_ap.pid" 2>/dev/null
else
	if [ -f "$DATA/dnsmasq_ap.pid" ]; then
		kill "$(cat "$DATA/dnsmasq_ap.pid")" 2>/dev/null
		rm -f "$DATA/dnsmasq_ap.pid"
	fi
fi
rm -f "$DATA/.hotspot_active" "$DATA/.hotspot_mode"

"$IP_BIN" addr flush dev "$IFACE" 2>/dev/null
if [ "$IFACE" != "wlan0" ]; then
	"$IP_BIN" link set "$IFACE" down 2>/dev/null
else
	# avevamo fermato wpa_supplicant per liberare wlan0 per l'AP:
	# lo rimettiamo in piedi, altrimenti il wifi normale resta morto
	SYS_WPA_CONF="${VD_WPA_CONF:-/etc/wpa_supplicant.conf}"
	if [ -f "$SYS_WPA_CONF" ]; then
		"$IP_BIN" link set wlan0 up 2>/dev/null
		wpa_supplicant -B -i wlan0 -c "$SYS_WPA_CONF" \
			>>"$LOG" 2>&1
		sleep 2
		udhcpc -i wlan0 -n -q >>"$LOG" 2>&1 &
	fi
fi

if [ "$MODE" = "chroot" ] && [ -f "$DATA/.hotspot_dev_mounted" ]; then
	umount "$MNT/dev" 2>/dev/null || umount -l "$MNT/dev" 2>/dev/null
	rm -f "$DATA/.hotspot_dev_mounted"
fi

if [ "$MODE" = "chroot" ] && [ -f "$DATA/.hotspot_we_mounted" ]; then
	sleep 0.3
	umount "$MNT" 2>/dev/null || umount -l "$MNT" 2>/dev/null
	rm -f "$DATA/.hotspot_we_mounted"
fi

echo "$(date) hotspot fermato" >>"$LOG"
exit 0
