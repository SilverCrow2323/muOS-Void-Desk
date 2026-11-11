#!/bin/sh
# Shared XFCE mount-state probe. Source this file, then call:
#   vd_mount_present "$APP_DIR" "$mount_path"
#
# Return codes are deliberately fail-closed:
#   0 = mounted (or unable to verify safely)
#   1 = definitely not mounted
vd_mount_present() {
    _vd_app_dir=$1
    _vd_mount_path=$2
    _vd_python=${PY3:-}

    if [ -z "$_vd_python" ]; then
        _vd_python="$(command -v python3 2>/dev/null || true)"
    fi
    if [ -z "$_vd_python" ]; then
        echo "[mount] python3 unavailable; refusing to assume the image is unmounted" >&2
        return 0
    fi

    PYTHONPATH="$_vd_app_dir/desk${PYTHONPATH:+:$PYTHONPATH}" \
        "$_vd_python" -c \
        'import imgmount, sys; sys.exit(0 if imgmount.is_mounted(sys.argv[1]) else 1)' \
        "$_vd_mount_path"
    _vd_status=$?
    if [ "$_vd_status" -gt 1 ]; then
        echo "[mount] state check failed; refusing to stack another mount" >&2
        return 0
    fi
    return "$_vd_status"
}
