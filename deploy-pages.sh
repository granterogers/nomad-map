#!/usr/bin/env bash
# Publish dist/nomad-radar.html to GitHub Pages as the site root.
#
# Pages is served from an orphan `gh-pages` branch that holds nothing but the
# page itself. Orphan, and force-pushed, because the page is a ~20MB build
# artifact: keeping it off the source branch stops every rebuild adding another
# 20MB blob to the history anyone cloning the repo has to download.
set -euo pipefail
cd "$(dirname "$0")"

PAGE="dist/nomad-radar.html"
[ -f "$PAGE" ] || { echo "no $PAGE - run ./build.sh first"; exit 1; }

size=$(stat -c%s "$PAGE")
echo "page: $(( size / 1048576 )) MB"
# GitHub blocks any file over 100MB outright and warns above 50MB.
[ "$size" -lt 52428800 ] || { echo "page exceeds 50MB - lower NOMAD_SHIP_SCALE"; exit 1; }

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp "$PAGE" "$work/index.html"
touch "$work/.nojekyll"          # stop Jekyll touching the file

git -C "$work" init -q
git -C "$work" checkout -q -b gh-pages
git -C "$work" add -A
git -C "$work" -c user.email="noreply@anthropic.com" -c user.name="Nomad Radar build" \
    commit -q -m "Publish Nomad Radar — $(date -u +%Y-%m-%dT%H:%MZ)"
git -C "$work" push -q --force "$(git remote get-url origin)" gh-pages

echo "pushed gh-pages"
echo "https://granterogers.github.io/nomad-map/"
