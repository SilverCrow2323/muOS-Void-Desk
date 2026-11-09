#!/bin/sh
# Compatibility entry point; all mount handling lives in the imgmount-aware
# Python manager so the ext4 image and loop device are cleaned up safely.
APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
exec python3 "$APP_DIR/bin/vd_apt_manage.py" "$@"
