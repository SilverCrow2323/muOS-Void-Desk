#!/bin/sh
# Shared XFCE mount-state probe. Source this file, then call:
#   vd_mount_present "$APP_DIR" "$mount_path"
#
# Return codes:
#   0 = definitely mounted
#   1 = definitely not mounted
#   2 = state is unknown; callers must stop without mounting or chrooting
vd_mount_present() {
    _vd_app_dir=$1
    _vd_mount_path=$2
    _vd_python=${PY3:-}

    if [ -z "$_vd_python" ]; then
        _vd_python="$(command -v python3 2>/dev/null || true)"
    fi
    if [ -z "$_vd_python" ]; then
        echo "[mount] python3 unavailable; mount state is unknown" >&2
        return 2
    fi

    _vd_result=$(
        PYTHONPATH="$_vd_app_dir/desk${PYTHONPATH:+:$PYTHONPATH}" \
            "$_vd_python" -c \
            'import sys
try:
    with open("/proc/mounts", "r") as stream:
        mount_table = stream.read()
    if not mount_table.strip():
        raise RuntimeError("/proc/mounts is empty")
    import imgmount
    mounted = imgmount.is_mounted(sys.argv[1])
except Exception as exc:
    print("[mount] state check failed: {}".format(exc), file=sys.stderr)
    sys.exit(2)
print("mounted" if mounted else "unmounted")' \
            "$_vd_mount_path"
    )
    _vd_status=$?
    if [ "$_vd_status" -ne 0 ]; then
        echo "[mount] state check failed; refusing to change mount state" >&2
        return 2
    fi

    case "$_vd_result" in
        mounted)
            return 0
            ;;
        unmounted)
            return 1
            ;;
        *)
            echo "[mount] unexpected state-check output; mount state is unknown" >&2
            return 2
            ;;
    esac
}

# Ensure a path is mounted, but invoke the mount command only when the parser
# positively reports it as unmounted. Unknown state is a hard stop.
vd_mount_ensure() {
    VD_MOUNT_CREATED=0
    _vd_app_dir=$1
    _vd_mount_path=$2
    shift 2

    vd_mount_present "$_vd_app_dir" "$_vd_mount_path"
    _vd_state=$?
    case "$_vd_state" in
        0)
            return 0
            ;;
        1)
            if [ "$#" -eq 0 ]; then
                echo "[mount] missing mount command for $_vd_mount_path" >&2
                return 2
            fi
            "$@"
            _vd_mount_rc=$?
            if [ "$_vd_mount_rc" -eq 0 ]; then
                VD_MOUNT_CREATED=1
            fi
            return "$_vd_mount_rc"
            ;;
        *)
            echo "[mount] refusing mount because state is unknown: $_vd_mount_path" >&2
            return 2
            ;;
    esac
}
