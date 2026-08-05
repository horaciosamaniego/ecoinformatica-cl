#!/usr/bin/env bash
# Build both language sites into ./_site
#
#   ./build.sh
#
# Spanish renders to _site/          (www.ecoinformatica.cl/)
# English renders to _site/en/       (www.ecoinformatica.cl/en/)
#
# Each language is its own small Quarto project so that navigation labels can
# be properly translated. Shared assets are staged into both before rendering,
# and each project writes to its own scratch directory — so the order of the
# renders never matters and nothing gets cleaned out from under us.

set -euo pipefail
cd "$(dirname "$0")"

echo "→ cleaning"
rm -rf _build _site

echo "→ staging shared assets"
for d in site-es site-en; do
  mkdir -p "$d/assets"
  cp shared/ecoinformatica.scss "$d/assets/"
  cp shared/hero-network.svg    "$d/assets/"
  [ -f shared/og-image.png ] && cp shared/og-image.png "$d/assets/" || true
done

echo "→ rendering Spanish"
quarto render site-es

echo "→ rendering English"
quarto render site-en

echo "→ assembling _site"
mkdir -p _site
cp -R _build/es/. _site/
mkdir -p _site/en
cp -R _build/en/. _site/en/
cp _redirects _site/_redirects

echo "→ generating redirect stubs, 404 page and .nojekyll"
python3 scripts/make_redirects.py

echo "✓ done — open _site/index.html, or run: quarto preview site-es"
