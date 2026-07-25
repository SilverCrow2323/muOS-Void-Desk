#!/bin/sh
# ============================================================================
#  VOIDDESK // vd_hotspot_start -- hotspot nativo (hostapd + dnsmasq)
#
#  FORGE installa hostapd/dnsmasq DENTRO il chroot XFCE (xfce.img), non
#  sull'host muOS -- che di norma non ha apt/dpkg per installarli
#  direttamente. Questo script quindi: prova prima l'host (nel raro caso
#  in cui un build muOS li abbia gia'), poi cerca dentro il chroot e li
#  esegue via 'chroot', montando l'immagine se non lo e' gia'.
#
#  Uso: vd_hotspot_start.sh [5g]
#
#  Interfaccia: se il device ha una seconda radio (wlan1) la preferisce
#  (permette hotspot + tua connessione dati sulla stessa sessione); se ha
#  un solo chip wifi riusa wlan0 in modalita' AP (la connessione client
#  esistente si interrompe finche' l'hotspot resta attivo, inevitabile
#  con hardware a singola radio). Sovrascrivibile con VD_AP_IFACE.
# ============================================================================
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA="$APP_DIR/data"
LOG="$DATA/hotspot.log"
IMG="$DATA/xfce.img"
MNT="${VD_XFCE_MNT:-$DATA/xfce_mnt}"
mkdir -p "$DATA"

MODE5G=0
[ "$1" = "5g" ] && MODE5G=1

IFACE="${VD_AP_IFACE:-}"
WLAN1_SYSFS="${VD_WLAN1_SYSFS:-/sys/class/net/wlan1}"
if [ -z "$IFACE" ]; then
	if [ -d "$WLAN1_SYSFS" ]; then
		IFACE=wlan1
	else
		IFACE=wlan0
	fi
fi
CUSTOM_CF="$DATA/hotspot_custom.conf"
CUSTOM_SSID="" CUSTOM_PASS=""
if [ -f "$CUSTOM_CF" ]; then
	CUSTOM_SSID="$(grep '^SSID=' "$CUSTOM_CF" | head -1 | cut -d= -f2-)"
	CUSTOM_PASS="$(grep '^PASS=' "$CUSTOM_CF" | head -1 | cut -d= -f2-)"
fi
SUBNET="${VD_AP_SUBNET:-192.168.89}"
SSID="${VD_AP_SSID:-${CUSTOM_SSID:-VoidDesk-AP}}"
PASS="${VD_AP_PASS:-${CUSTOM_PASS:-voiddesk99}}"
CHAN="${VD_AP_CHAN:-$([ "$MODE5G" = 1 ] && echo 36 || echo 6)}"
HOSTAPD_BIN="${VD_HOSTAPD_BIN:-hostapd}"
DNSMASQ_BIN="${VD_DNSMASQ_BIN:-dnsmasq}"
IP_BIN="${VD_IPCMD:-ip}"
CHROOT_BIN="${VD_CHROOT_BIN:-chroot}"
MOUNT_BIN="${VD_MOUNT_BIN:-mount}"

echo "$(date) === hotspot start (iface=$IFACE ssid=$SSID 5g=$MODE5G) ===" \
	>>"$LOG"

# --- 1) sull'host, se per caso ci sono gia' -------------------------------
MODE=""
if command -v "$HOSTAPD_BIN" >/dev/null 2>&1 && \
		command -v "$DNSMASQ_BIN" >/dev/null 2>&1; then
	MODE="host"
	CONF="$DATA/hostapd.conf"
	DNSCONF="$DATA/dnsmasq_ap.conf"
	LEASEFILE="$DATA/dnsmasq_ap.leases"
	RUN_HOSTAPD="$HOSTAPD_BIN"
	RUN_DNSMASQ="$DNSMASQ_BIN"
fi

# --- 2) altrimenti dentro il chroot, dove FORGE li ha davvero installati --
WE_MOUNTED=0
if [ -z "$MODE" ]; then
	if [ ! -f "$IMG" ]; then
		echo "manca la base XFCE: installala prima da START SESSION" \
			| tee -a "$LOG"
		exit 2
	fi
	if ! "$MOUNT_BIN" | grep -q " $MNT "; then
		mkdir -p "$MNT"
		if "$MOUNT_BIN" -o loop "$IMG" "$MNT" 2>>"$LOG"; then
			WE_MOUNTED=1
		fi
	fi
	if [ ! -x "$MNT/usr/sbin/$HOSTAPD_BIN" ] || \
			[ ! -x "$MNT/usr/sbin/$DNSMASQ_BIN" ]; then
		{
			[ ! -x "$MNT/usr/sbin/$HOSTAPD_BIN" ] && \
				echo "manca hostapd: installa 'Hotspot (hostapd+dnsmasq)' dal FORGE"
			[ ! -x "$MNT/usr/sbin/$DNSMASQ_BIN" ] && \
				echo "manca dnsmasq: installa 'Hotspot (hostapd+dnsmasq)' dal FORGE"
		} | tee -a "$LOG"
		[ "$WE_MOUNTED" = 1 ] && "$MOUNT_BIN" 2>/dev/null | \
			grep -q " $MNT " && umount "$MNT" 2>/dev/null
		exit 2
	fi
	MODE="chroot"
	CONF="$MNT/tmp/hostapd.conf"
	DNSCONF="$MNT/tmp/dnsmasq_ap.conf"
	LEASEFILE="/tmp/dnsmasq_ap.leases"
	RUN_HOSTAPD="$CHROOT_BIN $MNT /usr/sbin/$HOSTAPD_BIN"
	RUN_DNSMASQ="$CHROOT_BIN $MNT /usr/sbin/$DNSMASQ_BIN"
	# senza /dev vero dentro il chroot, hostapd e dnsmasq non trovano
	# /dev/urandom e falliscono sempre sulla generazione delle chiavi
	# WPA -- e' il bug che ha tenuto l'hotspot rotto finora
	mkdir -p "$MNT/dev"
	if ! mountpoint -q "$MNT/dev" 2>/dev/null; then
		mount --bind /dev "$MNT/dev" 2>>"$LOG" && \
			echo "1" >"$DATA/.hotspot_dev_mounted"
	fi
	echo "1" >"$DATA/.hotspot_we_mounted" 2>/dev/null
fi
echo "$(date) modalita': $MODE" >>"$LOG"

pkill -f "$HOSTAPD_BIN.*hostapd.conf" 2>/dev/null
pkill -f "$DNSMASQ_BIN.*dnsmasq_ap.conf" 2>/dev/null
sleep 0.3

if [ "$IFACE" = "wlan0" ]; then
	# unica radio: wpa_supplicant gestisce gia' wlan0 per il wifi
	# normale (VOID > UPLINK > WiFi) e si rimetterebbe a litigare con
	# hostapd per l'interfaccia, vanificando la configurazione appena
	# scritta. Con una seconda radio (wlan1) non serve: resta libera
	# per la connessione dati mentre l'AP vive altrove.
	killall wpa_supplicant 2>/dev/null
	sleep 0.3
fi

rfkill unblock all 2>/dev/null
"$IP_BIN" link set "$IFACE" down 2>/dev/null
"$IP_BIN" addr flush dev "$IFACE" 2>/dev/null
"$IP_BIN" link set "$IFACE" up 2>/dev/null
"$IP_BIN" addr add "$SUBNET.1/24" dev "$IFACE" 2>/dev/null

mkdir -p "$(dirname "$CONF")" "$(dirname "$DNSCONF")" 2>/dev/null

{
	echo "interface=$IFACE"
	echo "driver=nl80211"
	echo "ssid=$SSID"
	if [ "$MODE5G" = 1 ]; then
		echo "hw_mode=a"
		echo "ieee80211n=1"
		echo "ieee80211ac=1"
	else
		echo "hw_mode=g"
		echo "ieee80211n=1"
	fi
	echo "channel=$CHAN"
	echo "wmm_enabled=1"
	echo "auth_algs=1"
	echo "wpa=2"
	echo "wpa_passphrase=$PASS"
	echo "wpa_key_mgmt=WPA-PSK"
	echo "wpa_pairwise=CCMP"
	echo "rsn_pairwise=CCMP"
	echo "ignore_broadcast_ssid=0"
} >"$CONF"

{
	echo "interface=$IFACE"
	echo "bind-interfaces"
	echo "dhcp-range=$SUBNET.10,$SUBNET.100,255.255.255.0,12h"
	echo "dhcp-option=3,$SUBNET.1"
	echo "dhcp-option=6,$SUBNET.1"
	echo "dhcp-leasefile=$LEASEFILE"
} >"$DNSCONF"

# NAT verso l'uscita dati, solo se l'AP vive su una radio diversa da wlan0
WLAN0_SYSFS="${VD_WLAN0_SYSFS:-/sys/class/net/wlan0}"
if [ "$IFACE" != "wlan0" ] && [ -d "$WLAN0_SYSFS" ]; then
	echo 1 >/proc/sys/net/ipv4/ip_forward 2>/dev/null
	iptables -t nat -C POSTROUTING -o wlan0 -j MASQUERADE 2>/dev/null || \
		iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE 2>/dev/null
	iptables -C FORWARD -i "$IFACE" -o wlan0 -j ACCEPT 2>/dev/null || \
		iptables -A FORWARD -i "$IFACE" -o wlan0 -j ACCEPT 2>/dev/null
	iptables -C FORWARD -i wlan0 -o "$IFACE" \
		-m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || \
		iptables -A FORWARD -i wlan0 -o "$IFACE" \
		-m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null
fi

if [ "$MODE" = "chroot" ]; then
	$RUN_HOSTAPD -B /tmp/hostapd.conf >>"$LOG" 2>&1
	HR=$?
	$RUN_DNSMASQ -C /tmp/dnsmasq_ap.conf \
		--pid-file=/tmp/dnsmasq_ap.pid >>"$LOG" 2>&1
else
	$RUN_HOSTAPD -B "$CONF" >>"$LOG" 2>&1
	HR=$?
	$RUN_DNSMASQ -C "$DNSCONF" --pid-file="$DATA/dnsmasq_ap.pid" \
		>>"$LOG" 2>&1
fi

if [ "$HR" = 0 ]; then
	sleep 1.5
	ALIVE=0
	if [ "$MODE" = "chroot" ]; then
		"$CHROOT_BIN" "$MNT" pgrep -x "$HOSTAPD_BIN" >/dev/null 2>&1 && \
			ALIVE=1
	else
		pgrep -x "$HOSTAPD_BIN" >/dev/null 2>&1 && ALIVE=1
	fi
	if [ "$ALIVE" = 1 ]; then
		echo "$(date) hostapd avviato ($MODE) e confermato attivo dopo " \
			"1.5s, ssid=$SSID subnet=$SUBNET.0/24" >>"$LOG"
		echo "$SSID" >"$DATA/.hotspot_active"
		echo "$MODE" >"$DATA/.hotspot_mode"
		exit 0
	else
		echo "$(date) hostapd si e' avviato ma e' GIA' MORTO dopo 1.5s " \
			"($MODE) -- controlla il canale/driver/interfaccia, il " \
			"motivo vero e' nelle righe sopra questa" >>"$LOG"
		rm -f "$DATA/.hotspot_active" "$DATA/.hotspot_mode"
		exit 1
	fi
else
	echo "$(date) hostapd FALLITO rc=$HR ($MODE)" >>"$LOG"
	exit 1
fi
