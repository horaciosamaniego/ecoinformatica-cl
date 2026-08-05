# ecoinformatica.cl

Bilingual (ES/EN) static site for the Laboratorio de Ecoinformática, Universidad
Austral de Chile. Built with [Quarto](https://quarto.org). No database, no plugins,
nothing to patch.

## Build it

You need Quarto installed (`quarto --version`). Then:

```bash
./build.sh
```

Spanish renders to `_site/`, English to `_site/en/`. For live-reloading while
editing a single language:

```bash
quarto preview site-es
```

## Structure

```
shared/
  ecoinformatica.scss   theme — palette, type, the "registro" ledger style
  hero-network.svg      homepage graphic
  references.bib        ← the only file you edit to update publications
scripts/
  build_pubs.py         regenerates both publication pages from the .bib
site-es/                Spanish project  → site root
site-en/                English project  → /en/
_redirects              old WordPress URLs → new pages
build.sh                renders both, assembles _site/
```

Two small Quarto projects rather than one, so that navbar labels are genuinely
translated instead of Spanish-with-English-content. `build.sh` copies the shared
theme into each before rendering; those copies are gitignored.

## Updating publications

1. Export your record from ORCID (**Works → Export → BibTeX**) or Zotero.
2. Save it over `shared/references.bib`.
3. Check it: `python3 scripts/lint_bib.py`
4. Fix whatever it flags, then `python3 scripts/build_pubs.py`.
5. Commit the regenerated `.qmd` files and push.

The linter changes nothing — it reports duplicates, missing years, missing DOIs
and formatting problems. ORCID exports routinely contain the same paper two or
three times from different sources, so step 3 is not optional in practice.

The generated pages are committed deliberately: the deploy step then needs only
Quarto, never Python. Optional BibTeX fields the generator understands:

- `doi` — turns the title into a link (falls back to `url`)
- `keywords` — rendered as tags beneath the entry

## Deploying

The repo lives on GitHub either way. The only question is who serves the HTML.

### Option A — GitHub Pages

`.github/workflows/publish.yml` builds and deploys on every push to `main`.

1. Repo **Settings → Pages → Source: GitHub Actions**.
2. **Settings → Pages → Custom domain**: `www.ecoinformatica.cl`, then **Save**.
3. Verify the domain under **Settings → Pages → Verify domain** (prevents takeover).
4. At NIC Chile, add a `CNAME` for `www` → `USERNAME.github.io` (no repo name),
   plus these `A` records on the apex so `ecoinformatica.cl` redirects to `www`:

   ```
   185.199.108.153
   185.199.109.153
   185.199.110.153
   185.199.111.153
   ```

5. Wait for the certificate, then tick **Enforce HTTPS** (can take up to 24h).

Note that publishing via Actions ignores any `CNAME` file — the domain comes
from the Settings field alone. Pages on a **public** repo is free; a private
source repo needs GitHub Pro.

**The catch:** GitHub Pages has no redirect layer, so `_redirects` is inert
there. `scripts/make_redirects.py` compensates — meta-refresh stubs for exact
paths, and a wildcard table baked into `404.html` (Pages serves it for any
unmatched path). Readers following old links land correctly. But those return
HTTP 200 or 404, never 301, so search engines treat them as weaker signals than
real redirects.

### Option B — Cloudflare Pages or Netlify

Same repo, same push-to-deploy. Build command `./build.sh`, output directory
`_site`. Both read `_redirects` natively and issue true 301s.

**Pick B if** the old URLs in your published papers matter enough to want proper
301s, or you want DNS and hosting in one place. **Pick A if** you'd rather keep
everything on GitHub and can live with the stubs.

## Still to do before this goes live

- [ ] Replace `shared/references.bib` with the real ORCID export — the four
      entries in there now are samples with no DOIs and no page numbers.
- [ ] Fill in the alumni years in `personas.qmd` / `people.qmd` (currently `——`).
      The years are what make that list a history rather than a roster.
- [ ] Check the project dates on the research pages — reconstructed from the old
      site, which only recorded start years.
- [ ] Add `shared/og-image.png` (1200×630) so shared links stop rendering as grey
      rectangles. A crop of the hero network on the dark field would do it.
- [ ] Decide whether `analizador.ecoinformatica.cl` stays, gets archived, or goes.

## Design notes

Palette is drawn from Valdivian temperate rainforest and oxidised copper — deep
forest ink `#101F1B`, lichen paper `#ECEFE9`, verdigris `#2F7F70`. Type is one
superfamily used in three registers: IBM Plex Sans Condensed for display, Plex
Serif for reading, Plex Mono for years, tags and labels.

The recurring element is the **registro**: a ledger row with a mono key on the
left and content on the right. Publications, projects and people all use it,
because in this lab all three genuinely are records indexed by time. It is the
one place the design spends any boldness; everything else stays quiet.