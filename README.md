# stevenjhubbard-work

Source for **[work.stevenjhubbard.com](https://work.stevenjhubbard.com/)** — the full work archive for Steven J. Hubbard. Twenty-four engagements from 2000 to now, each shown as the site actually looked during the engagement.

Same hand-written approach as the apex site: HTML, CSS, and vanilla JavaScript, no framework, no build step. `index.html` is the whole site.

## Layout

| Path | What it is |
|---|---|
| `index.html` | The site. Source of truth — edit this. |
| `capture.py` | Screenshot harness. Shoots live sites and Wayback captures at 2000×1250, converts to WebP. |
| `captures.json` | Which Wayback timestamp each image came from. Written by `capture.py`. |
| `assets/webp/` | What ships — `<id>.webp` at 2000px, `<id>@sm.webp` at 1000px |
| `assets/raw/` | The source PNGs, kept so images can be re-derived at other sizes |

## Develop

```bash
python3 -m http.server 4318
```

## Re-shoot the images

```bash
python3 capture.py
```

Skips anything already in `assets/webp/`, so a bare run only fills gaps. Pass ids to force a re-shoot:

```bash
python3 capture.py lexmark tivo
```

## Two things worth knowing before touching capture.py

**The availability API lies about dates.** `archive.org/wayback/available` accepts a timestamp and will happily return a capture a decade away — it offered a 2012 Lexmark homepage for a 2022 engagement. Everything resolves through the CDX API instead, which honours a real date range and returns nothing rather than something wrong. Month-precision bounds keep the index scan small; a whole-year range on a domain the size of lexmark.com times the CDX server out.

**Headless Chrome writes the PNG and then sometimes declines to exit.** The file is the success signal, not the process exit code. `shoot()` waits, kills, and then judges by whether a plausible-sized file landed.

## Provenance

Every image carries a badge saying where it came from — **Live**, **Archived**, **Own archive**, or **No capture**. The counts: 4 live, 10 archived, 6 carried over, 4 that cannot be rendered at all. They add to 24, and the hero stats are derived from the same tally.

### Three domain collisions

The most dangerous failure here is not a missing capture, it is a capture of the wrong company. Three domains have since been reassigned, and the archive serves the new owner's site with no indication anything changed:

| Domain | What the archive actually holds |
|---|---|
| `primastudio.com` | VB Racing / Hopkins Honda, a motorsport site. The real Prima Studio is dancewear. |
| `odysay.com` | A Korean developer's personal résumé page. The real OdySay is a fashion label. |
| `llsupply.com` | An Antiguan distributor of the same name, not the West Coast home & garden client. |

All three use the apex site's images instead. **Do not "fix" these by re-shooting them** — the capture will succeed and be wrong. They are removed from `SHOTS` with a comment saying why.

### Three that cannot be rendered

Two sites were built entirely in Flash — `eurorscg.com` and `digitalbrewing.com` — and archive at 3–5 KB of SWF references with zero image elements. `horizonmedia.com` is a client-rendered application: 34 KB of markup, forty-one script tags, no images, and archived JavaScript that will never hydrate.

These three get a `.shot--gone` block instead of an image: the domain, why nothing renders, and a link to the archive record. Substituting a later redesign would have been easy and dishonest.

`nationalflashback.com` was the fourth. Its 2000–2008 captures are Flash too, but the domain later carried Steven's own portfolio, so `nflashback.webp` is the August 2019 capture of that, and the caption says so rather than passing it off as the original.

### Two more caveats, stated on the page

- **Lexmark** — the bare `lexmark.com` host has no 2022-era captures; the archived homepage of that period lives at `lexmark.com/en_us.html`.
- **Puzzle Theory** — never archived during the 2002–2005 engagement. The 2011 capture is the earliest that survives.

Terra Firma Music, The Liquor Store SF, and First Presbyterian Church also carry over apex-site images, at 1300px rather than 2000px — their `srcset` descriptors say 1300w, not 2000w.

### Nimblefish is enlarged

The 2005 layout is fixed-width and renders about 720px wide inside a 2000px window. The shipped image is cropped to the content and rescaled onto a canvas of the page's own background colour. The caption says it is enlarged.

## Deploy

Its own Vercel project (`stevenjhubbard-work`, team `gamecat2300`), on `work.stevenjhubbard.com`. A push to `main` is a production deploy; there is no staging branch. Deliberately separate from the apex site's project so a push to one never redeploys the other.

DNS needs no manual step — the zone's nameservers are Vercel's, so adding the domain to the project created the record.

Shares the apex site's GA4 property (`G-TGMML7BB0S`) so the archive reports alongside it instead of as an unattributed domain.

© Steven Hubbard LLC. Archived captures courtesy of the Internet Archive. Code is reusable; the written content and résumé detail are not.
