#!/bin/sh
set -eu

REPO_URL="https://github.com/SilverCrow2323/Void-Desk-Project.wiki.git"
SOURCE_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/../wiki-source" && pwd)"
TEMP_ROOT="$(mktemp -d)"
WIKI_DIR="$TEMP_ROOT/wiki"

cleanup() {
    rm -rf "$TEMP_ROOT"
}
trap cleanup EXIT HUP INT TERM

if ! git clone "$REPO_URL" "$WIKI_DIR"; then
    cat >&2 <<'EOF'
The GitHub Wiki repository is not available yet.

GitHub creates the special .wiki.git repository only after its first page is
saved. Open the project Wiki in a browser, create a page titled "Home" using
wiki-source/Home.md, save it, then rerun this script.
EOF
    exit 2
fi

find "$SOURCE_DIR" -maxdepth 1 -type f -name '*.md' -exec cp {} "$WIKI_DIR/" \;
cd "$WIKI_DIR"
git add -- *.md
if git diff --cached --quiet; then
    echo "Wiki is already up to date."
    exit 0
fi

git -c user.name="VoidDesk Wiki Publisher" \
    -c user.email="voiddesk-wiki@users.noreply.github.com" \
    commit -m "docs: publish VoidDesk project wiki"
git push origin HEAD
echo "GitHub Wiki pages published."
