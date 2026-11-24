#!/usr/bin/env bash
# Publish dist/nomad-radar.html to GitHub Pages.
#
# Pages is configured to serve the `main` branch at its root, so the page is
# committed there as index.html. Note the cost of that choice: the page is a
# ~20MB build artifact, so every publish adds another ~20MB blob to main's
# history permanently, for everyone who clones. An orphan gh-pages branch that
# is replaced each publish would avoid that; serving from main does not.
# .nojekyll stops Pages running the file through Jekyll.
set -euo pipefail
cd "$(dirname "$0")"

PAGE="dist/nomad-radar.html"
[ -f "$PAGE" ] || { echo "no $PAGE - run ./build.sh first"; exit 1; }

size=$(stat -c%s "$PAGE")
echo "page:    $(( size / 1048576 )) MB"
echo "version: $(cat VERSION)"
# GitHub blocks files over 100MB outright and warns above 50MB.
[ "$size" -lt 52428800 ] || { echo "page exceeds 50MB - lower NOMAD_SHIP_SCALE"; exit 1; }

cp "$PAGE" index.html
touch .nojekyll
git add index.html .nojekyll
git commit -q -m "Publish Nomad Radar v$(cat VERSION)" || echo "  (page unchanged)"
git push -q origin HEAD:main

echo "pushed to main"
echo "https://granterogers.github.io/nomad-map/"
