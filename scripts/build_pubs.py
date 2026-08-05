#!/usr/bin/env python3
"""
Build the publications pages from shared/references.bib.

Run this whenever the .bib changes:

    python3 scripts/build_pubs.py

It writes site-es/publicaciones.qmd and site-en/publications.qmd, grouped by
year, newest first. The generated files are committed to the repo so that the
deploy step only ever needs Quarto — no Python, no R, no plugins.

Pure standard library on purpose: nothing to install, nothing to break.
"""

from __future__ import annotations

import pathlib
import re
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
BIB = ROOT / "shared" / "references.bib"

# ── BibTeX parsing ─────────────────────────────────────────────────────────

LATEX_ACCENTS = {
    r"\'a": "á", r"\'e": "é", r"\'i": "í", r"\'o": "ó", r"\'u": "ú",
    r"\'A": "Á", r"\'E": "É", r"\'I": "Í", r"\'O": "Ó", r"\'U": "Ú",
    r'\"a': "ä", r'\"o': "ö", r'\"u': "ü", r'\"A': "Ä", r'\"O': "Ö", r'\"U': "Ü",
    r"\~n": "ñ", r"\~N": "Ñ", r"\c c": "ç", r"\'n": "ń",
}


def clean(value: str) -> str:
    """Strip LaTeX noise from a field value."""
    for tex, char in LATEX_ACCENTS.items():
        value = value.replace("{" + tex + "}", char).replace(tex, char)
    value = value.replace("\\&", "&").replace("--", "–")
    value = re.sub(r"[{}]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def parse_bib(text: str) -> list[dict]:
    """Minimal BibTeX reader. Handles nested braces and quoted values."""
    entries = []
    for match in re.finditer(r"@(\w+)\s*\{", text):
        kind = match.group(1).lower()
        if kind in {"comment", "preamble", "string"}:
            continue

        # Walk forward to the matching close brace.
        i, depth = match.end(), 1
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        body = text[match.end():i - 1]

        key, _, rest = body.partition(",")
        entry = {"__type__": kind, "__key__": key.strip()}

        pos = 0
        while pos < len(rest):
            fm = re.compile(r"\s*(\w+)\s*=\s*").match(rest, pos)
            if not fm:
                break
            field, pos = fm.group(1).lower(), fm.end()

            if rest[pos] == "{":
                depth, start = 1, pos + 1
                pos += 1
                while pos < len(rest) and depth:
                    if rest[pos] == "{":
                        depth += 1
                    elif rest[pos] == "}":
                        depth -= 1
                    pos += 1
                value = rest[start:pos - 1]
            elif rest[pos] == '"':
                start = pos + 1
                pos += 1
                while pos < len(rest) and rest[pos] != '"':
                    pos += 1
                value = rest[start:pos]
                pos += 1
            else:
                start = pos
                while pos < len(rest) and rest[pos] not in ",\n":
                    pos += 1
                value = rest[start:pos]

            entry[field] = clean(value)
            while pos < len(rest) and rest[pos] in ", \n\t":
                pos += 1

        entries.append(entry)
    return entries


def format_authors(raw: str) -> str:
    """'Samaniego, Horacio and Milne, Bruce T.' -> 'H. Samaniego, B. T. Milne'"""
    out = []
    for name in re.split(r"\s+and\s+", raw):
        name = name.strip()
        if not name:
            continue
        if "," in name:
            last, first = (p.strip() for p in name.split(",", 1))
        else:
            parts = name.split()
            last, first = parts[-1], " ".join(parts[:-1])
        initials = " ".join(f"{p[0]}." for p in first.split() if p)
        out.append(f"{initials} {last}".strip())
    if len(out) > 8:
        return ", ".join(out[:8]) + " et al."
    return ", ".join(out)


# ── Page rendering ─────────────────────────────────────────────────────────

def render_entry(e: dict) -> str:
    authors = format_authors(e.get("author", ""))
    title = e.get("title", "Untitled")
    venue = e.get("journal") or e.get("booktitle") or e.get("publisher") or ""

    link = ""
    if e.get("doi"):
        link = f"https://doi.org/{e['doi']}"
    elif e.get("url"):
        link = e["url"]

    title_html = f"[{title}]({link})" if link else title

    meta = authors
    if venue:
        meta = f"{meta} · {venue}" if meta else venue

    tags = ""
    if e.get("keywords"):
        kw = " · ".join(k.strip() for k in re.split(r"[;,]", e["keywords"]) if k.strip())
        if kw:
            tags = f"\n[{kw}]{{.tags}}"

    return (
        "::: {.row-item}\n"
        f"[{e.get('year', '——')}]{{.key}}\n"
        "::: {.val}\n"
        f"[{title_html}]{{.title}}\n"
        f"[{meta}]{{.meta}}{tags}\n"
        ":::\n"
        ":::\n"
    )


PAGES = {
    "site-es/publicaciones.qmd": {
        "title": "Publicaciones",
        "description": "Publicaciones del Laboratorio de Ecoinformática, Universidad Austral de Chile.",
        "intro": (
            "Artículos, capítulos y trabajos en los que han participado integrantes del "
            "laboratorio. La lista se genera desde un único archivo BibTeX, así que "
            "actualizarla es reemplazar un archivo y volver a compilar."
        ),
        "count": "%d publicaciones",
    },
    "site-en/publications.qmd": {
        "title": "Publications",
        "description": "Publications from the Ecoinformatics Lab, Universidad Austral de Chile.",
        "intro": (
            "Articles, chapters and other work involving lab members. The list is "
            "generated from a single BibTeX file, so keeping it current means "
            "replacing one file and rebuilding."
        ),
        "count": "%d publications",
    },
}


def main() -> int:
    if not BIB.exists():
        print(f"error: {BIB} not found", file=sys.stderr)
        return 1

    entries = parse_bib(BIB.read_text(encoding="utf-8"))
    if not entries:
        print(f"error: no entries parsed from {BIB}", file=sys.stderr)
        return 1

    by_year = defaultdict(list)
    for e in entries:
        year = re.sub(r"\D", "", e.get("year", "")) or "0000"
        by_year[year].append(e)

    for path, cfg in PAGES.items():
        chunks = [
            "---",
            f'title: "{cfg["title"]}"',
            f'description: "{cfg["description"]}"',
            "---",
            "",
            "<!-- GENERATED by scripts/build_pubs.py — edit shared/references.bib, not this file. -->",
            "",
            cfg["intro"],
            "",
            f'[{cfg["count"] % len(entries)}]{{.eyebrow}}',
            "",
        ]
        chunks.append("::: {.registro}")
        for year in sorted(by_year, reverse=True):
            group = sorted(by_year[year], key=lambda e: e.get("author", ""))
            chunks.extend(render_entry(e) for e in group)
        chunks.append(":::\n")

        (ROOT / path).write_text("\n".join(chunks), encoding="utf-8")
        print(f"wrote {path}  ({len(entries)} entries, {len(by_year)} years)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
