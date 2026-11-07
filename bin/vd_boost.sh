#!/bin/sh
# ============================================================================
#  VOIDDESK // vd_boost — prestazioni del desktop, reversibili.
#
#  Viene SOURCE-ato da xfce_launch.sh (eredita MNT, DATA, XLOG, PROG, VDLANG,
#  PY3). Fa tre cose, tutte annullate al teardown per lasciare muOS intatto:
#
#  1) SWAP  — con 1GB di RAM e' la differenza tra "GIMP parte" e "GIMP
#     uccide la sessione". Prova zram (compressione in RAM: veloce, zero
#     usura SD); se il kernel muOS non ha il modulo, ripiega su uno
#     swapfile da 512MB DENTRO l'immagine ext4 (creato una tantum).
#  2) GOVERNOR — cpufreq a "performance" per la sessione: niente cali a
#     mezzo giro mentre trascini le finestre. Ripristinato all'uscita.
#  3) SYSCTL — swappiness e dirty ratio tarati sul tipo di swap e sulla SD.
#
#  Nota tecnica: mkswap/swapon/swapoff girano NEL chroot (util-linux c'e'
#  di sicuro nell'immagine Ubuntu; il BusyBox di muOS non e' garantito).
#  Lo swap e' globale del kernel: attivarlo dal chroot vale per tutti.
# ============================================================================

VD_SYSFS_CPU="${VD_SYSFS_CPU:-/sys/devices/system/cpu/cpufreq}"
VD_SYS_ZRAM="${VD_SYS_ZRAM:-/sys/block/zram0}"
VD_PROC_SWAPS="${VD_PROC_SWAPS:-/proc/swaps}"
VD_PROC_MEM="${VD_PROC_MEM:-/proc/meminfo}"
VD_PROC_VM="${VD_PROC_VM:-/proc/sys/vm}"
VD_STATE="${VD_STATE:-/tmp/.vd_boost_state}"
SWAPFILE_REL="var/cache/vd_swap"

BLOG() { echo "$(date) boost: $*" >>"$XLOG"; }

CHR() {
	if [ -n "$VD_BOOST_DRYRUN" ]; then
		echo "CHROOT: $*"
		return 0
	fi
	chroot "$MNT" /usr/bin/env PATH=/usr/sbin:/usr/bin:/sbin:/bin "$@" \
		>>"$XLOG" 2>&1
}

_flag_off() {	# _flag_off chiave  -> 0 se la chiave e' false
	grep -q "\"$1\": *false" "$DATA/desk_config.json" 2>/dev/null
}

_swap_on() { ! _flag_off boost_swap && ! _flag_off boost; }
_cpu_on()  { ! _flag_off boost_cpu && ! _flag_off boost; }

_have_swap() {
	[ "$(wc -l <"$VD_PROC_SWAPS" 2>/dev/null || echo 1)" -gt 1 ]
}

_save_kv() { echo "$1=$2" >>"$VD_STATE"; }

_set_vm() {	# _set_vm nome valore  (salvando l'originale)
	P="$VD_PROC_VM/$1"
	[ -e "$P" ] || return 0
	_save_kv "vm.$1" "$(cat "$P" 2>/dev/null)"
	echo "$2" >"$P" 2>/dev/null
}

_info() {	# _info riga-it riga-en   -> accumulo in $DATA/.boost_info
	if [ "$VDLANG" = "en" ]; then echo "$2"; else echo "$1"; fi \
		>>"$DATA/.boost_info"
}

BOOST_SETUP() {
	: >"$VD_STATE"
	rm -f "$DATA/.boost_info"
	if ! _swap_on && ! _cpu_on; then
		BLOG "disattivato dalle opzioni"
		_info "disattivato dalle opzioni" "disabled in settings"
		return 0
	fi

	# ---- 1) governor -> performance -------------------------------------
	GOVSET=0
	_cpu_on || GOVSET=-1
	[ "$GOVSET" = -1 ] || \
	for POL in "$VD_SYSFS_CPU"/policy*; do
		[ -e "$POL/scaling_governor" ] || continue
		CUR="$(cat "$POL/scaling_governor" 2>/dev/null)"
		grep -qw performance "$POL/scaling_available_governors" 2>/dev/null \
			|| continue
		[ "$CUR" = "performance" ] && { GOVSET=1; continue; }
		_save_kv "gov:$POL" "$CUR"
		echo performance >"$POL/scaling_governor" 2>/dev/null && GOVSET=1
	done
	if [ "$GOVSET" = 1 ]; then
		BLOG "governor performance"
		_info "CPU: governor performance (in sessione)" \
		      "CPU: performance governor (in session)"
	fi

	# ---- 2) swap ---------------------------------------------------------
	if ! _swap_on; then
		BLOG "swap boost disattivato"
		_info "SWAP: boost disattivato" "SWAP: boost disabled"
	elif _have_swap; then
		BLOG "swap gia' attiva sul sistema: non tocco nulla"
		_info "SWAP: gia' attiva (muOS)" "SWAP: already active (muOS)"
	else
		_setup_swap
	fi

	# ---- 3) sysctl -------------------------------------------------------
	case "$(cat "$VD_STATE.swaptype" 2>/dev/null)" in
	zram)	_set_vm swappiness 100 ;;
	file)	_set_vm swappiness 30 ;;
	esac
	_set_vm vfs_cache_pressure 60
	_set_vm dirty_ratio 20
	_set_vm dirty_background_ratio 8
	return 0
}

_setup_swap() {
	# RAM/2, tetto 512MB
	MEMK="$(awk '/^MemTotal:/{print $2}' "$VD_PROC_MEM" 2>/dev/null)"
	[ -n "$MEMK" ] || MEMK=1048576
	DSK=$((MEMK / 2))
	[ "$DSK" -gt 524288 ] && DSK=524288

	# --- tentativo zram ---
	[ -e "$VD_SYS_ZRAM" ] || modprobe zram num_devices=1 2>>"$XLOG" || true
	if [ -e "$VD_SYS_ZRAM/disksize" ]; then
		ALGO=""
		if grep -qw lz4 "$VD_SYS_ZRAM/comp_algorithm" 2>/dev/null; then
			echo lz4 >"$VD_SYS_ZRAM/comp_algorithm" 2>/dev/null && ALGO="lz4"
		fi
		[ -n "$ALGO" ] || ALGO="$(sed 's/.*\[\(.*\)\].*/\1/' \
			"$VD_SYS_ZRAM/comp_algorithm" 2>/dev/null)"
		if echo $((DSK * 1024)) >"$VD_SYS_ZRAM/disksize" 2>/dev/null &&
			CHR mkswap /dev/zram0 && CHR swapon -p 100 /dev/zram0; then
			echo zram >"$VD_STATE.swaptype"
			BLOG "zram attiva: $((DSK / 1024))MB ($ALGO)"
			_info "SWAP: zram $((DSK / 1024))MB ($ALGO, in RAM)" \
			      "SWAP: $((DSK / 1024))MB zram ($ALGO, in RAM)"
			return 0
		fi
		BLOG "zram presente ma attivazione fallita: ripiego su file"
	else
		BLOG "kernel senza zram: ripiego su swapfile"
	fi

	# --- ripiego: swapfile dentro l'immagine ext4 ---
	F="$MNT/$SWAPFILE_REL"
	if [ ! -f "$F" ]; then
		FREEK="$(df -k "$MNT" 2>/dev/null | awk 'NR==2{print $4}')"
		if [ -z "$FREEK" ] || [ "$FREEK" -lt 800000 ]; then
			BLOG "poco spazio nell'immagine ($FREEK KB): niente swapfile"
			_info "SWAP: assente (poco spazio nell'immagine)" \
			      "SWAP: none (image almost full)"
			return 0
		fi
		PROG 56 "creo lo swapfile 512MB (una tantum)" \
		        "creating the 512MB swapfile (one-off)"
		BLOG "creo swapfile 512MB"
		if [ -n "$VD_BOOST_DRYRUN" ]; then
			echo "DD: $F 512MB"
			: >"$F"
		else
			dd if=/dev/zero of="$F" bs=1M count=512 2>>"$XLOG" || {
				rm -f "$F"
				BLOG "dd fallito"
				return 0
			}
		fi
		chmod 600 "$F"
	fi
	if CHR mkswap "/$SWAPFILE_REL" && CHR swapon -p 10 "/$SWAPFILE_REL"; then
		echo file >"$VD_STATE.swaptype"
		BLOG "swapfile attivo"
		_info "SWAP: file 512MB (nell'immagine ext4)" \
		      "SWAP: 512MB file (inside the ext4 image)"
	else
		BLOG "swapon del file fallito"
		_info "SWAP: attivazione fallita (vedi log)" \
		      "SWAP: activation failed (see log)"
	fi
}

BOOST_TEARDOWN() {
	# swap giu' PRIMA dell'umount (lo swapfile vive nell'immagine)
	case "$(cat "$VD_STATE.swaptype" 2>/dev/null)" in
	zram)
		CHR swapoff /dev/zram0
		echo 1 >"$VD_SYS_ZRAM/reset" 2>/dev/null
		rmmod zram 2>/dev/null || true
		BLOG "zram spenta"
		;;
	file)
		CHR swapoff "/$SWAPFILE_REL"
		BLOG "swapfile spento"
		;;
	esac
	rm -f "$VD_STATE.swaptype"
	# governor e sysctl come li avevo trovati
	[ -f "$VD_STATE" ] && while IFS='=' read -r K V; do
		case "$K" in
		gov:*)	echo "$V" >"${K#gov:}/scaling_governor" 2>/dev/null ;;
		vm.*)	echo "$V" >"$VD_PROC_VM/${K#vm.}" 2>/dev/null ;;
		esac
	done <"$VD_STATE"
	rm -f "$VD_STATE"
	return 0
}
