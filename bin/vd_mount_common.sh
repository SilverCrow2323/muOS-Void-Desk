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

    # Do not overload Python's exit code 1 to mean "not mounted": syntax,
    # import and runtime errors can also exit 1. Emit an explicit state token
    # only after the mount table and shared parser have both worked.
    _vd_result=$(
        PYTHONPATH="$_vd_app_dir/desk${PYTHONPATH:+:$PYTHONPATH}" \
            "$_vd_python" -c \
            'import sys
try:
    with open("/proc/mounts", "r") as stream:
        stream.read()
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
        echo "[mount] state check failed; refusing to stack another mount" >&2
        return 0
    fi

    case "$_vd_result" in
        mounted)
            return 0
            ;;
        unmounted)
            return 1
            ;;
        *)
            echo "[mount] unexpected state-check output; refusing to stack another mount" >&2
            return 0
            ;;
    esac
}
