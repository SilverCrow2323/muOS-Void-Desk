#!/bin/sh
set -eu

REPO_URL="https://github.com/SilverCrow2323/Void-Desk-Project.wiki.git"
REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
SOURCE_DIR="$REPO_ROOT/wiki-source"
ASSET_DIR="$REPO_ROOT/docs/assets"
TEMP_ROOT="$(mktemp -d)"
WIKI_DIR="$TEMP_ROOT/wiki"

cleanup() { rm -rf "$TEMP_ROOT"; }
trap cleanup EXIT HUP INT TERM

if ! git clone "$REPO_URL" "$WIKI_DIR"; then
    cat >&2 <<'MSG'
The GitHub Wiki repository is not available yet.

GitHub creates the special .wiki.git repository only after its first page is
saved. Open the project Wiki, create a page titled "Home", paste wiki-source/Home.md,
save it, then rerun this script.
MSG
    exit 2
fi

for page in "$SOURCE_DIR"/*.md; do
    [ -f "$page" ] || continue
    [ "$(basename "$page")" = "README.md" ] && continue
    cp "$page" "$WIKI_DIR/"
done

# Wiki Markdown resolves image links against the Wiki repo itself.
mkdir -p "$WIKI_DIR/assets"
for asset in voiddesk-docs-banner.svg qwasar-system-map.svg nexus-v12-navigation.svg muos-profile-resolution.svg; do
    [ -f "$ASSET_DIR/$asset" ] || {
        echo "Missing documentation asset: $ASSET_DIR/$asset" >&2
        exit 3
    }
    cp "$ASSET_DIR/$asset" "$WIKI_DIR/assets/$asset"
done

cd "$WIKI_DIR"
git add -- *.md assets/*.svg
if git diff --cached --quiet; then
    echo "Wiki is already up to date."
    exit 0
fi

git -c user.name="VoidDesk Wiki Publisher" \
    -c user.email="voiddesk-wiki@users.noreply.github.com" \
    commit -m "docs: publish Void Desk field manual"
git push origin HEAD
echo "GitHub Wiki pages and visual assets published."
