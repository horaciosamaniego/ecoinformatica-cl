#!/usr/bin/env python3
"""
Make the _redirects rules work on GitHub Pages.

Cloudflare Pages and Netlify read _redirects natively and issue real 301s.
GitHub Pages does not — it has no redirect layer at all. This script gets as
close as a purely static host allows:

  1. Exact paths (no wildcard) become small HTML stub files that do a
     meta-refresh plus a rel=canonical pointing at the new URL.
  2. Wildcard paths are compiled into a table baked into 404.html. GitHub
     Pages serves 404.html for any unmatched path, so the page reads
     location.pathname, matches it against the table, and forwards.

The honest caveat: both mechanisms return HTTP 200 (stubs) or 404 (the
catch-all), never 301. Browsers follow them fine and readers land in the right
place, but search engines treat them as weaker signals than a real redirect.
If preserving link equity from cited URLs matters, host on Cloudflare Pages or
Netlify instead and let _redirects do its job properly.

Run as part of build.sh — no need to call it directly.
"""

from __future__ import annotations

import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REDIRECTS = ROOT / "_redirects"
SITE = ROOT / "_site"

STUB = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Redirigiendo… / Redirecting…</title>
<link rel="canonical" href="{abs_target}">
<meta http-equiv="refresh" content="0; url={target}">
<meta name="robots" content="noindex">
<style>
  body {{ background:#ECEFE9; color:#101F1B; font-family:Georgia,serif;
          margin:0; display:grid; place-items:center; min-height:100vh; padding:2rem; }}
  a {{ color:#2F7F70; }}
</style>
</head>
<body>
<p>Esta página se movió. / This page has moved.<br>
<a href="{target}">Continuar / Continue</a></p>
<script>window.location.replace({target_json});</script>
</body>
</html>
"""

NOT_FOUND = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Página no encontrada / Page not found — Ecoinformática</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{ background:#ECEFE9; color:#101F1B; font-family:Georgia,serif;
          margin:0; display:grid; place-items:center; min-height:100vh;
          padding:2rem; line-height:1.6; }}
  main {{ max-width:44ch; }}
  .eyebrow {{ font-family:ui-monospace,monospace; font-size:.72rem;
              letter-spacing:.14em; text-transform:uppercase; color:#3D5A4C; }}
  h1 {{ font-family:"IBM Plex Sans Condensed",system-ui,sans-serif;
        font-size:1.9rem; line-height:1.15; margin:.5rem 0 1rem; }}
  a {{ color:#2F7F70; }}
</style>
</head>
<body>
<main>
  <span class="eyebrow">Error 404</span>
  <h1>Esta página no existe.<br>This page doesn't exist.</h1>
  <p>Puede que el enlace sea de una versión anterior del sitio.<br>
     The link may point at an older version of this site.</p>
  <p><a href="/">Ir al inicio</a> · <a href="/en/">Go to the English home page</a></p>
</main>
<script>
// Wildcard rules compiled from _redirects. GitHub Pages serves this page for
// any unmatched path, so we can still forward old URLs from here.
var RULES = {rules_json};
(function () {{
  var path = window.location.pathname.replace(/\\/+$/, "") || "/";
  for (var i = 0; i < RULES.length; i++) {{
    if (path === RULES[i][0] || path.indexOf(RULES[i][0] + "/") === 0) {{
      window.location.replace(RULES[i][1]);
      return;
    }}
  }}
}})();
</script>
</body>
</html>
"""

SITE_URL = "https://www.ecoinformatica.cl"


def parse_redirects(text: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Split _redirects into (exact, wildcard) rule lists."""
    exact: list[tuple[str, str]] = []
    wildcard: list[tuple[str, str]] = []

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        source, target = parts[0], parts[1]

        if source.endswith("/*"):
            wildcard.append((source[:-2] or "/", target))
        elif "*" in source:
            continue  # mid-path wildcards aren't expressible statically
        else:
            exact.append((source, target))

    # Longest prefix first, so /site/foo beats /site.
    wildcard.sort(key=lambda r: len(r[0]), reverse=True)
    return exact, wildcard


def main() -> int:
    if not SITE.exists():
        print(f"error: {SITE} not found — run build.sh first", file=sys.stderr)
        return 1
    if not REDIRECTS.exists():
        print(f"note: no {REDIRECTS}, skipping")
        return 0

    exact, wildcard = parse_redirects(REDIRECTS.read_text(encoding="utf-8"))

    written = 0
    for source, target in exact:
        dest = SITE / source.lstrip("/") / "index.html"
        if dest.exists():
            continue  # never clobber a real page
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            STUB.format(
                target=html.escape(target, quote=True),
                abs_target=html.escape(SITE_URL + target, quote=True),
                target_json=json.dumps(target),
            ),
            encoding="utf-8",
        )
        written += 1

    (SITE / "404.html").write_text(
        NOT_FOUND.format(rules_json=json.dumps(wildcard)),
        encoding="utf-8",
    )

    # Stops GitHub Pages running Jekyll over the output, which would otherwise
    # strip any directory beginning with an underscore.
    (SITE / ".nojekyll").touch()

    print(f"wrote {written} redirect stubs, 404.html ({len(wildcard)} wildcard rules), .nojekyll")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
