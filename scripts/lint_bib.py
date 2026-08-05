#!/usr/bin/env python3
"""
Check shared/references.bib before you publish it.

    python3 scripts/lint_bib.py

ORCID exports are messy: the same paper often arrives two or three times from
different sources, DOIs go missing, titles come through in ALL CAPS or with
stray LaTeX. This reports what needs a human eye. It changes nothing — it only
tells you what to look at.

Findings are grouped by severity:

  ERROR   the entry will render badly or wrongly
  WARN    it will render, but something is probably wrong
  NOTE    cosmetic, fix if you care
"""

from __future__ import annotations

import pathlib
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_pubs import parse_bib  # reuse the exact parser the site uses

ROOT = pathlib.Path(__file__).resolve().parent.parent
BIB = ROOT / "shared" / "references.bib"

# Entry types where a missing journal name is expected, not a problem.
NO_VENUE_OK = {"phdthesis", "mastersthesis", "techreport", "unpublished", "misc", "book"}


def norm_title(t: str) -> str:
    """Aggressive normalisation for duplicate detection."""
    return re.sub(r"[^a-z0-9]", "", t.lower())


def main() -> int:
    if not BIB.exists():
        print(f"error: {BIB} not found", file=sys.stderr)
        return 1

    raw = BIB.read_text(encoding="utf-8")
    entries = parse_bib(raw)
    findings: list[tuple[str, str, str]] = []   # (severity, key, message)

    def add(sev, key, msg):
        findings.append((sev, key, msg))

    # ── duplicate detection ────────────────────────────────────────────────
    by_title = defaultdict(list)
    for e in entries:
        if e.get("title"):
            by_title[norm_title(e["title"])].append(e["__key__"])
    for title_norm, keys in by_title.items():
        if len(keys) > 1:
            add("ERROR", ", ".join(keys), f"{len(keys)} entries share a title — likely duplicates")

    by_doi = defaultdict(list)
    for e in entries:
        if e.get("doi"):
            by_doi[e["doi"].lower().strip()].append(e["__key__"])
    for doi, keys in by_doi.items():
        if len(keys) > 1:
            add("ERROR", ", ".join(keys), f"same DOI on {len(keys)} entries: {doi}")

    dup_keys = [k for k, n in Counter(e["__key__"] for e in entries).items() if n > 1]
    for k in dup_keys:
        add("ERROR", k, "citation key used more than once")

    # ── per-entry checks ───────────────────────────────────────────────────
    for e in entries:
        key = e["__key__"] or "(no key)"
        kind = e["__type__"]

        if not e.get("author"):
            add("ERROR", key, "no author field — will render an empty byline")
        if not e.get("title"):
            add("ERROR", key, "no title")

        year = re.sub(r"\D", "", e.get("year", ""))
        if not year:
            add("ERROR", key, "no usable year — will sort to the bottom under '0000'")
        elif not (1900 < int(year) < 2100):
            add("WARN", key, f"implausible year: {year}")

        venue = e.get("journal") or e.get("booktitle") or e.get("publisher")
        if not venue and kind not in NO_VENUE_OK:
            add("WARN", key, f"no journal/booktitle on a @{kind}")

        if not e.get("doi") and not e.get("url"):
            add("WARN", key, "no DOI or URL — title will not be clickable")

        title = e.get("title", "")
        if title and title == title.upper() and len(title) > 12:
            add("NOTE", key, "title is ALL CAPS")
        if re.search(r"\\[a-zA-Z]+", title):
            add("NOTE", key, "unhandled LaTeX command in title")
        if not e.get("keywords"):
            add("NOTE", key, "no keywords — entry will show no tags")

        author = e.get("author", "")
        if author and " and " not in author and "," not in author and " " in author:
            add("NOTE", key, "single author with no comma — check 'Last, First' format")
        if re.search(r"\bet\s+al\b", author, re.I):
            add("WARN", key, "'et al.' inside the author field — list real names instead")

    # ── report ─────────────────────────────────────────────────────────────
    print(f"\n{len(entries)} entries in {BIB.relative_to(ROOT)}\n")

    years = [int(re.sub(r"\D", "", e.get("year", "")) or 0) for e in entries]
    real = [y for y in years if y]
    if real:
        print(f"  year range   {min(real)}–{max(real)}")
    print(f"  with DOI     {sum(1 for e in entries if e.get('doi'))}/{len(entries)}")
    print(f"  with tags    {sum(1 for e in entries if e.get('keywords'))}/{len(entries)}")
    kinds = Counter(e["__type__"] for e in entries)
    print(f"  types        {', '.join(f'{k}×{n}' for k, n in kinds.most_common())}")

    order = {"ERROR": 0, "WARN": 1, "NOTE": 2}
    findings.sort(key=lambda f: order[f[0]])

    if not findings:
        print("\n  clean — nothing to fix\n")
        return 0

    counts = Counter(f[0] for f in findings)
    print("\n" + "─" * 68)
    current = None
    for sev, key, msg in findings:
        if sev != current:
            print()
            current = sev
        print(f"  {sev:<6} {key:<28} {msg}")

    print("\n" + "─" * 68)
    print("  " + "  ".join(f"{n} {s.lower()}" for s, n in counts.most_common()) + "\n")

    return 1 if counts.get("ERROR") else 0


if __name__ == "__main__":
    raise SystemExit(main())
    