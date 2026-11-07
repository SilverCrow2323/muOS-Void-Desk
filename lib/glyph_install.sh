# --- installazione glifo nel tema attivo (POSIX sh, compatibile 2601.x) ---
# uso: INSTALL_GLYPH <percorso_png> <nome_glifo>
INSTALL_GLYPH() {
	IG_PNG="$1"
	IG_NAME="$2"
	[ -f "$IG_PNG" ] || return 0

	# percorso legacy (muOS < 2601)
	IG_LEGACY="/opt/muos/share/theme/active/glyph/muxapp"
	[ -d "$IG_LEGACY" ] && cp -f "$IG_PNG" "$IG_LEGACY/$IG_NAME.png" 2>/dev/null

	# percorso 2601.x: tema attivo indicato in /opt/muos/config/theme/active
	IG_THEME=""
	[ -r /opt/muos/config/theme/active ] && IG_THEME="$(cat /opt/muos/config/theme/active 2>/dev/null)"
	if [ -n "$IG_THEME" ]; then
		for IG_BASE in \
			"/opt/muos/browse/SD1 (mmc)/MUOS/theme/$IG_THEME/glyph/muxapp" \
			"/opt/muos/browse/SD2 (sdcard)/MUOS/theme/$IG_THEME/glyph/muxapp" \
			"/run/muos/storage/theme/$IG_THEME/glyph/muxapp" \
			"/mnt/mmc/MUOS/theme/$IG_THEME/glyph/muxapp" \
			"/mnt/sdcard/MUOS/theme/$IG_THEME/glyph/muxapp"; do
			[ -d "$IG_BASE" ] && cp -f "$IG_PNG" "$IG_BASE/$IG_NAME.png" 2>/dev/null
		done
	fi
	return 0
}
