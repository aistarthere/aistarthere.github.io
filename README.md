# AI Start Here (static site)

Live URL (once deployed): https://aistarthere.github.io/ (repo `aistarthere/aistarthere.github.io`, branch `main`, root).

Content lives in `data/*.json`. `build.py` pre-renders it into `index.html` (so the page works with JavaScript off) and generates `index.md`, `llms.txt`, `llms-full.txt`, `robots.txt` and `sitemap.xml`. `app.js` only adds extras: menu, filter, copy buttons, live votes and embeds.

    python3 build.py             # after any JSON / site.json / config.js edit (idempotent)
    python3 build.py --assets    # redraw og-image.png + favicons (brand changes only)
    ./qa.sh                      # full QA, PASS/FAIL summary, non-zero exit on FAIL
    python3 -m http.server 8765  # preview at http://localhost:8765

## Where things live
- `site.json`: base URL, title, description, X handle (empty until @aistarthere exists)
- `config.js`: service placeholders (Tally, vote CSV, beehiiv, GoatCounter). Empty = "coming soon". Rebuild after editing.
- `data/basics.json`: AI 101 questions (`title`, short `answer`, `body`, `sources`). Also feeds the FAQPage JSON-LD.
- `data/models.json`: Latest models table + ItemList JSON-LD. `source` must be the lab's own page; unknown fields say `TODO`.
- `data/news.json`, `data/try.json`, `data/automations.json` (`id` is the vote key; don't rename it once voting is live)
- In `index.html`, only edit outside the `<!-- build:NAME -->` markers.
- `qa/`: helpers for `qa.sh`. Node QA tools install to `../tools/qa-node`; reports go to `../qa-reports/`.

Full maintenance loop: `../content/runbook.md`.
