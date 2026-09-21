# CLAUDE.md — project memory

Persistent notes for this repository (`ayushsingh08-ds`, the GitHub profile
repo). Read this before changing anything; update it after every task.

## What this project is

The repository *is* the GitHub profile page. There is no application, no dev
server and no package manifest: a single Python generator reads a JSON config
and writes `README.md` plus every image the README displays.

```
profile.json          content (name, role, about, stack, projects, ...)  <- edit this
generate.py           geometry + the whole page, compiled from profile.json
assets/cards/*.svg    generated cards -- never hand-edit, regenerated wholesale
assets/cards/dark/*.svg  the same cards mapped to GitHub's dark palette
assets/base64_icons.json  offline icon set (tech-stack chips)
assets/github_stats.json  fetched stats cache (audit record: source/auth/dates)
assets/contributions.json fetched 12-month contribution calendar cache
assets/header_background_optimized.jpg  UNUSED since the typographic hero (see below)
profile-3d-contrib/   UNUSED since the local contribution card (see below)
scratch/              disposable tooling (preview + measurement harness), not published
.github/workflows/profile-3d.yml  daily compile + commit (the only CI)
```

## Commands

```bash
python generate.py               # the whole build: cards + README.md (stdlib only)
python scratch/build_preview.py   # README.md -> scratch/preview.html (inlines card SVGs)
python scratch/qc.py              # all cards -> scratch/qc.html (measurement harness)
python scratch/check_readme.py    # asserts README.md structure (rows, alts, assets, anchors)
```

`generate.py` validates every card as XML before writing `README.md` and exits
non-zero if any card is malformed — that check exists because two builds shipped
silently broken images (see "Bugs this project has already hit"). The `scratch/`
checks are run by hand; nothing in CI depends on them.

After regenerating, run `check_readme.py` and re-measure `qc.html`; the expected
output is 27 images in rows of `1 4 1 2 1 1 1 2 1 1 1 1 1 1 2 1 1 4`, zero
overflow issues and 12–35px of bottom slack per card.

## Design system

One content axis. `GRID = 850` is the width of a full-width block; rows are
sized so that row + gaps also equals `GRID`, which is why every block in the
published page shares the same left and right edge:

| row | card width | row total |
|---|---|---|
| single | 850 | 850 |
| pair | 419 | ~849 |
| quad | 203 | ~847 |

Tokens live at the top of `generate.py`: warm off-white surface `#fffdfa`,
hairline border `#e5dacf`, charcoal ink `#2c1e1e`, muted `#7a6a65`, single
terracotta accent `#b05a30`. Type: Outfit (display), Inter (body), Courier Prime
(uppercase labels, indices, chips). Radii: 10px cards, 8px buttons, 4px chips.

Section order: header (monogram/name/contact) → nav row → hero → CTAs →
at-a-glance grid → About → Tech Stack → principles | currently building → Next →
Featured Projects → GitHub Analytics → closing → contact row.

### Two themes, one geometry

Every card is compiled twice: the cream original and a GitHub-dark counterpart
in `assets/cards/dark/`, produced by mapping the palette through
`DARK_COLORS` in `generate.py` rather than by drawing the cards again — the two
themes differ in colour only, so the geometry cannot drift. Dark surfaces,
borders and text greys are GitHub's own tokens (`#161b22` surface, `#30363d`
border, `#e6edf3`/`#c9d1d9`/`#8b949e`/`#7d8590` text); the accent stays
terracotta, brightened to `#e08d63` so it still carries on a dark surface.

The README offers both with `<picture><source media="(prefers-color-scheme:
dark)" srcset="assets/cards/dark/X.svg"><img src="assets/cards/X.svg" …>` —the
mechanism GitHub documents for theme-aware images. The inner `<img>` is the
light image *and* the fallback for any host that ignores `<picture>`.

Rules that keep the pair honest:

* **Any colour a card uses must be in `DARK_COLORS`.** An unmapped colour aborts
  the build — otherwise it would leak into the dark cards as a bright patch.
* `BUTTON_TEXT` (`#fdf9f3`) exists only so the mapping stays 1:1: the primary
  button's text is a distinct token from `SURFACE_TINT`, because on dark the tile
  stays dark while the button text inverts to `#0d1117`.
* `scratch/check_readme.py` asserts that each light/dark pair has identical
  `viewBox`/`width`/`height`, so the two themes cannot silently diverge.

## GitHub rendering constraints (all load-bearing)

1. **Every card image sits inside its own `<p align="center">` on one line.** A
   line holding one complete tag is a CommonMark HTML block (type 7), emitted
   *without* a wrapping `<p>`; bare `<img>` lines then flow inline and cards
   share rows. Do not "tidy" those paragraphs away.
2. **Only `src`, `width` and `alt` survive sanitising.** No inline styles, no
   `height` attribute (a fixed height plus the host's `max-width: 100%` squashes
   the image on narrow viewports). Cards scale proportionally instead.
3. **Cards are XML documents.** HTML-only entities (`&middot;`, `&rarr;`,
   `&nbsp;`, `&rsquo;`) and unclosed void tags (`<img>`) make the browser drop
   the entire image with no warning. Use literal characters (`·`, `→`, `’`) and
   self-close `<img />`. `&amp;` is fine.
4. **Anchors.** GitHub serves heading ids as `id="user-content-<slug>"` and
   strips the prefix client-side, so `href="#featured-projects"` works. The nav
   row's four buttons rely on this; heading text therefore must slugify to
   `about`, `tech-stack`, `featured-projects`, `github-analytics`.
5. **No external image hosts.** The README is self-contained: GitHub
   removes `github-readme-stats.vercel.app` and `streak-stats.demolab.com`
   whenever those deployments hiccup, which is what emptied the analytics section
   once. Analytics are fetched at build time and drawn locally.
6. Rows wrap below ~852px of column width (that is fine and intended: a wrapped
   card still fills the column). The GitHub profile column is `container-lg`
   (max-width 1012px), so a normal desktop window renders every row as designed.
7. **Theme-aware images use `<picture>` + `prefers-color-scheme`**, per GitHub's
   own announcement of the feature. `srcset` is written as a repository-relative
   path, the same shape as `src`; GitHub rewrites relative `srcset` the way it
   rewrites `src` (that rewrite initially shipped broken in 2022 and was fixed).
   This is the one part of the theme work that cannot be checked from here — see
   "Unverified / open issues".

## Decisions taken (and why)

- **Typographic hero, no photo banner.** The old header was a JPEG with a cream
  gradient overlay behind the text; a minimalist editorial hero carries the same
  information without the gradient. `assets/header_background_optimized.jpg` is
  therefore unreferenced (kept in git, safe to delete).
- **Four info columns inside one 850px card** rather than four 200px cards. Four
  200px cards need 836px and wrapped 3 + 1 on some windows; four columns in one
  image can never go ragged, and it freed the page from a 5th stacked row.
- **Local contribution calendar replaces the 3D isometric graph.** The
  `yoshi389111/github-profile-3d-contrib` action (1280×850, animated, seasonal
  palette) and its `profile-3d-contrib/*.svg` output are no longer referenced;
  that CI step was removed. `assets/cards/contrib.svg` is a 7×53 warm-toned
  heatmap drawn from `assets/contributions.json`.
- **Languages card replaced the third-party streak card**, and stats/languages
  numbers are cached in a committed file that records `source` (`api` / `cache` /
  `default`), `auth` and `fetched_at`/`checked_at`.
- **Progress bars are labelled "self-assessed".** `currently_building` percentages
  are the owner's own estimates and cannot be verified against those
  repositories, so the card says so instead of asserting a number. Planned work
  sits in its own card labelled "planned, not started".
- **Tech stack de-duplicated**: every icon now appears in exactly one category
  (29 chips). `postgresql` was removed from Languages and `kubernetes` from Data &
  Streaming, and the categories were re-cut so a technology never repeats.
- **`profile.json` keys removed**: `academic` (superseded by the shorter `kicker`)
  and `what_i_build` (superseded by `focus` + the About card). Both were
  superseded by the target page structure, not dropped for convenience; recover
  from git history if their sections come back.
- **Cards deleted** with their sections: the "What I build" grid, the old
  "Upcoming projects" card (content now in the "Next" card), the sticky-note
  footer with the John Johnson quote (decorative, and the sticky note was
  rotated handwriting), and the 110×32 icon buttons.

## Bugs this project has already hit (do not reintroduce)

1. `github-readme-stats.vercel.app` went down and published a section of broken
   images → all analytics are local now.
2. A failed LinkedIn-icon fetch wrote an empty `src` → that icon fetch is gone
   entirely (the contact row is text).
3. Four 200px cards wrapped 3 + 1 on a laptop → fixed by the single info card.
4. HTML entities in card content (`&middot;`) made 7 cards unparseable XML, and an
   unclosed `<img>` broke an 8th; both were invisible in the source and in a
   local render until measured in a browser → hence the XML validation step.

## Verification performed (2026-09-21)

| check | command / method | result |
|---|---|---|
| build | `python generate.py` | 27 cards + README, "Validated: every card is well-formed XML" |
| reproducibility | two consecutive `python generate.py` runs | byte-identical (md5 of every card + README + both caches) |
| card overflow | `scratch/qc.html` + `preview_evaluate(window.qc(1))` | 27/27 cards: no clipped content, 12–35px bottom slack |
| images render | preview: `img.naturalWidth` on all 27 | 27/27 load, 0 broken |
| row layout | preview: image groups at 1000/980/900/860/800px | at ≥860px every row is 852px wide in the order `1 4 1 2 1 1 1 2 1 1 1 1 1 1 2 1 1 4`; rows wrap below that |
| README structure | `python scratch/check_readme.py` | 27 images = 27 card files, every image inside a block tag with alt text and an existing asset, no bare `<img>` lines, no tables, anchors resolve |
| workflow | `yaml.safe_load` on the CI file | parses, 4 steps, name "Compile profile README" |
| encoding | byte check for `·` `→` `’` in the cards | present as real UTF-8, no entities |
| link check | `curl -o /dev/null -w '%{http_code}'` | 6/6 GitHub URLs 200; LinkedIn 999 (bot block, unchanged from before); resume link dead |
| copy accuracy | every card's numbers traced to `profile.json` or the fetches | see "Unverified / open" |
| **published page** (after commit `5f5704a`) | `curl https://github.com/ayushsingh08-ds` | 27 images, 19 image paragraphs with counts `1 4 1 2 1 1 1 2 1 1 1 1 1 1 0 2 1 1 4`, no external image, no table |
| dark theme geometry | `python scratch/check_readme.py` | 27 light + 27 dark cards, 27 `<picture>` blocks, every pair identical in size, rows unchanged |
| dark theme rendering | preview: draw each data URI to a canvas and sample pixels | hero/card corner samples `#fffdfa`+`#e5dacf` in light, `#161b22`+`#30363d` in dark |
| dark theme layout | `scratch/qc.html` (now measures both sets) | 54/54 cards, no clipped content, 17px minimum bottom slack |
| theme switching | preview's Auto/Light/Dark buttons | forcing dark makes the browser load the dark source; forced light returns the light `<img>` |
| published anchors | nav hrefs vs heading permalink ids | `about`, `tech-stack`, `featured-projects`, `github-analytics` all resolve |
| published assets | 27 raw `/raw/main/assets/cards/*.svg` URLs with `-L` | 27/27 → 200 (after the `/raw/` → raw.githubusercontent redirect) |

## Unverified / open issues

- **The Resume link is dead.** `profile.json` → `about_me.resume_url` (a Google
  Drive file) answers `400 / "Page not found"` for anonymous visitors. It is
  published as-is because only the owner can supply a working URL; fix the value
  in `profile.json` and rebuild.
- Anchors are confirmed on the live page: GitHub renders each heading as
  `<h2 class="heading-element">Text</h2>` plus a sibling
  `<a id="user-content-<slug>" class="anchor" href="#<slug>">`, so renaming a
  heading means renaming the nav item in `NAV_ITEMS` too (or the slug changes).
- GitHub wraps every image that is not already inside a link in an `<a>` to the
  card's blob, so unlinked cards are clickable to their source file. Cards that
  need a specific destination (CTAs, nav, contact, projects) are wrapped in their
  own `<a>` in `generate.py`.
- Cards are images: on a phone the smallest card text (9–10.5px at 850px wide)
  scales to ~4–5px. A `<picture>` + `media` variant per card is the fix.
- **Unverified until the next push: relative `srcset` rewriting.** The dark
  variants are referenced with repository-relative paths, like `src`. If GitHub
  does not rewrite them, dark-mode readers get a broken image instead of the dark
  card (light mode is unaffected, because the `<img src>` stays verified). Check
  the served markup for `srcset="/ayushsingh08-ds/ayushsingh08-ds/raw/main/..."`
  after deploying; if it is still relative, switch `card_image()` in
  `generate.py` to the root-absolute form `/owner/repo/raw/main/…` and rebuild.
- Contributions are read by parsing `github.com/users/<user>/contributions`. GitHub
  can change that markup at any time; the failure mode is a cached calendar (and,
  with no cache at all, an empty card), never a broken image.
- Cards use `foreignObject` + `@import` Google Fonts — the combination GitHub's
  SVG proxy and Safari handle least reliably. If a font ever fails, the card
  falls back to a system font and reflows inside its fixed box.
- A local build records `"auth": "anonymous"` in `assets/github_stats.json` while
  CI records `"token"` — that one-line diff is the audit record, not drift.
- Unused leftovers: `assets/header_background_optimized.jpg`, `profile-3d-contrib/`
  (10 SVGs, ~2MB) and the `github`/`linkedin` entries in `assets/base64_icons.json`.
- `scratch/` is intentionally untracked build tooling; do not treat it as part of
  the published profile.
