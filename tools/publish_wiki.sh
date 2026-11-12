#!/bin/sh
set -eu

REPO_URL="https://github.com/SilverCrow2323/Void-Desk-Project.wiki.git"
REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
SOURCE_DIR="$REPO_ROOT/wiki-source"
ASSET_DIR="$REPO_ROOT/docs/assets"
RESOURCE_DIR="$REPO_ROOT/resources"
BRAND_DIR="$REPO_ROOT/assets/brand"
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

# Publish diagrams, the project symbol, actual NEXUS navigation icons,
# and the distinct THE FORGE screen capture.
mkdir -p "$WIKI_DIR/assets/icons" "$WIKI_DIR/assets/brand" "$WIKI_DIR/assets/screens"

for asset in voiddesk-docs-banner.svg qwasar-system-map.svg nexus-v12-navigation.svg muos-profile-resolution.svg; do
    [ -f "$ASSET_DIR/$asset" ] || { echo "Missing documentation asset: $asset" >&2; exit 3; }
    cp "$ASSET_DIR/$asset" "$WIKI_DIR/assets/$asset"
done

[ -f "$BRAND_DIR/voiddesk_symbol.png" ] || { echo "Missing legacy Void Desk raster symbol" >&2; exit 4; }
cp "$BRAND_DIR/voiddesk_symbol.png" "$WIKI_DIR/assets/brand/voiddesk_symbol.png"
[ -f "$BRAND_DIR/voiddesk_symbol.svg" ] || { echo "Missing canonical Void Desk SVG symbol" >&2; exit 4; }
cp "$BRAND_DIR/voiddesk_symbol.svg" "$WIKI_DIR/assets/brand/voiddesk_symbol.svg"

for icon in workshop.png settings.png the_forge.png start.png rt_toolbox.png net_sphere.png muos.png media_vault.png info.png end.png; do
    [ -f "$RESOURCE_DIR/$icon" ] || { echo "Missing navigation icon: $icon" >&2; exit 5; }
    cp "$RESOURCE_DIR/$icon" "$WIKI_DIR/assets/icons/$icon"
done

[ -f "$RESOURCE_DIR/forge-menu.png" ] || { echo "Missing THE FORGE screen capture: forge-menu.png" >&2; exit 6; }
cp "$RESOURCE_DIR/forge-menu.png" "$WIKI_DIR/assets/screens/forge-menu.png"

cd "$WIKI_DIR"
git add -- *.md assets
if git diff --cached --quiet; then
    echo "Wiki is already up to date."
    exit 0
fi

git -c user.name="VoidDesk Wiki Publisher" \
    -c user.email="voiddesk-wiki@users.noreply.github.com" \
    commit -m "docs: publish Void Desk field manual and visual assets"
git push origin HEAD
echo "GitHub Wiki pages, diagrams, brand symbol, navigation icons and Forge screen published."
