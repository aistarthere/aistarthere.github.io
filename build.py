#!/usr/bin/env python3
"""Pre-render data/*.json into static HTML so the page works with JavaScript off
(search crawlers and AI bots often don't run JS). JSON stays the source of truth.

  python3 build.py            write index.html, index.md, llms.txt, llms-full.txt, robots.txt, sitemap.xml
  python3 build.py --check    exit 1 if any generated file is out of date (used by qa.sh)
  python3 build.py --assets   also (re)draw og-image.png, favicon.ico/.svg, apple-touch-icon.png

Idempotent: output depends only on data/*.json, site.json and config.js, so running it
twice gives byte-identical files. Generated regions in index.html sit between
<!-- build:NAME --> and <!-- /build:NAME --> markers; edit everything else by hand.
"""
import html, json, re, sys, pathlib
from datetime import date
from urllib.parse import urlparse

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"
SITE = json.loads((HERE / "site.json").read_text())
BASE = SITE["baseUrl"].rstrip("/") + "/"

def load(name): return json.loads((DATA / f"{name}.json").read_text())
basics, models, news, tries, autos = (load(n) for n in ("basics", "models", "news", "try", "automations"))

def config_js():
    """Read the service URLs from config.js so pre-rendered vote/suggest links match the JS."""
    txt = (HERE / "config.js").read_text()
    return {k: v for k, v in re.findall(r'^\s*(\w+)\s*:\s*"([^"]*)"', txt, re.M)}
CFG = config_js()

e = lambda s: html.escape(str(s if s is not None else ""), quote=True)
def todo(s): return e(s).replace("TODO", '<span class="todo">TODO</span>')
def host(u):
    try: return urlparse(u).hostname.removeprefix("www.")
    except Exception: return u
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
def fmt(d):
    if not ISO.match(d or ""): return d
    y, m, dd = map(int, d.split("-")); return f"{dd} {date(y, m, dd).strftime('%b')} {y}"
def ext(u, text): return f'<a href="{e(u)}" rel="noopener" target="_blank">{text}</a>'
def updated(d, label="Last updated"):
    return f'<p class="updated">{label}: <time datetime="{e(d)}">{e(fmt(d))}</time></p>'
LAST_MOD = max(x["updated"] for x in (basics, models, news, tries, autos))

def model_sort(ms):
    iso = lambda x: x["released"] if ISO.match(x["released"]) else ""
    return sorted(ms, key=lambda x: iso(x), reverse=True)  # stable: undated rows keep file order at the bottom
MODELS = model_sort(models["models"])
FAQ = basics["cards"]

# ---------- HTML regions ----------
def r_basics():
    cards = []
    for c in FAQ:
        src = ""
        if c.get("sources"):
            links = " · ".join(ext(s["url"], e(s["label"])) if s["url"].startswith("http") else f'<a href="{e(s["url"])}">{e(s["label"])}</a>' for s in c["sources"])
            src = f'<p class="src">Source: {links}</p>'
        cards.append(f'<article class="card faq-item" id="{e(c["id"])}"><h3>{e(c["title"])}</h3><p class="answer"><strong>{e(c["answer"])}</strong></p><p>{e(c["body"])}</p>{src}</article>')
    more = "".join(f'<li>{ext(l["url"], e(l["label"]))}</li>' for l in basics["learnMore"])
    return f'''<h2 id="basics-h"><span class="num" aria-hidden="true">1</span> AI 101: what do I need to know first?</h2>
      <p class="section-intro answer">{e(basics["intro"])}</p>
      {updated(basics["updated"])}
      <div class="grid cards" id="basics-cards">{"".join(cards)}</div>
      <div class="learn-more"><strong>Go deeper (free):</strong><ul>{more}</ul></div>'''

def r_models():
    rows = []
    for m in MODELS:
        free_cls = ' class="free-yes"' if re.match(r"^yes", m["free"], re.I) else ""
        srcs = "".join(f'<li>{ext(u, e(host(u)))}</li>' for u in (m.get("source"), m.get("source2")) if u)
        rows.append(f'<tr><td>{e(m["company"])}</td><th scope="row" class="model">{e(m["model"])}</th><td>{todo(fmt(m["released"]))}</td><td>{todo(m["goodFor"])}</td><td{free_cls}>{todo(m["free"])}</td><td><ul class="srcs">{srcs}</ul></td></tr>')
    newest = next((m for m in MODELS if ISO.match(m["released"])), None)
    lead = f'The newest release in our table is {e(newest["model"])} from {e(newest["company"])} ({e(fmt(newest["released"]))}). ' if newest else ""
    return f'''<h2 id="models-h"><span class="num" aria-hidden="true">2</span> What are the latest AI models?</h2>
      <p class="section-intro answer">{lead}The big AI labs release new models every few weeks. Here's what's current and whether you can try it for free.</p>
      {updated(models["updated"], "Last checked")}
      <div class="filter-row" hidden>
        <label for="model-filter">Filter:</label>
        <input id="model-filter" type="search" placeholder="e.g. Claude, free, coding">
      </div>
      <div class="table-wrap" tabindex="0" role="region" aria-labelledby="models-caption">
        <table class="models">
          <caption id="models-caption">AI models from the major labs, newest first, with free-access status and sources</caption>
          <thead><tr><th scope="col">Company</th><th scope="col">Model</th><th scope="col">Released</th><th scope="col">Good for</th><th scope="col">Free access?</th><th scope="col">Source</th></tr></thead>
          <tbody id="models-body">{"".join(rows)}</tbody>
        </table>
      </div>
      <p class="fineprint">Rows only use each lab's own announcement or pricing page. "TODO" means we couldn't confirm it there yet.</p>'''

def r_news():
    items = "".join(f'<li><time datetime="{e(n["date"])}">{e(fmt(n["date"]))}</time><h3>{e(n["title"])}</h3><p>{todo(n["summary"])} {ext(n["source"], "Source: " + e(host(n["source"])))}</p><p class="why"><strong>Why it matters:</strong> {e(n["whyItMatters"])}</p></li>' for n in news["items"])
    top = news["items"][0]
    return f'''<h2 id="news-h"><span class="num" aria-hidden="true">3</span> What's new in AI this week?</h2>
      <p class="section-intro answer">Latest: {e(top["title"])} ({e(fmt(top["date"]))}). What happened, and why it matters to you.</p>
      {updated(news["updated"])}
      <ol class="news" id="news-list">{items}</ol>'''

def r_try():
    cards = []
    for i, t in enumerate(tries["items"]):
        src = f' {ext(t["source"], "Source: " + e(host(t["source"])))}' if t.get("source") else ""
        cards.append(f'<article class="card"><p class="tool">{e(t["tool"])}</p><h3>{e(t["title"])}</h3><p class="prompt" id="p{i}">{e(t["prompt"])}</p><button class="copy" type="button" data-target="p{i}" hidden>Copy prompt</button><p class="tip">{e(t["tip"])}{src}</p></article>')
    return f'''<h2 id="try-h"><span class="num" aria-hidden="true">4</span> What can I try with AI today?</h2>
      <p class="section-intro answer">Copy a prompt, paste it into a free chatbot, and see what happens. Each takes about five minutes.</p>
      {updated(tries["updated"])}
      <div class="grid cards" id="try-cards">{"".join(cards)}</div>'''

def r_autos():
    vote_url = CFG.get("tallyVoteFormUrl", ""); live = bool(vote_url); sug = CFG.get("tallySuggestFormUrl", "")
    out = []
    for a in autos["items"]:
        if live:
            u = f'{vote_url}{"&" if "?" in vote_url else "?"}idea={a["id"]}'
            vote = f'<a class="vote-btn" href="{e(u)}" rel="noopener" target="_blank" aria-label="Upvote {e(a["title"])}">▲</a><span class="count" data-idea="{e(a["id"])}">0</span><span class="label">votes</span>'
        else:
            vote = f'<button type="button" disabled aria-label="Upvote {e(a["title"])} (voting coming soon)">▲</button><span class="count" data-idea="{e(a["id"])}">0</span><span class="label">coming soon</span>'
        pills = "".join(f'<span class="pill">{e(t)}</span>' for t in [a["level"], "⏱ " + a["time"], *a["tools"]])
        steps = "".join(f"<li>{todo(s)}</li>" for s in a["steps"])
        out.append(f'<article class="auto" id="auto-{e(a["id"])}"><div class="vote">{vote}</div><div><h3>{e(a["title"])}</h3><div class="meta">{pills}</div><details><summary>Show the steps</summary><ol>{steps}</ol><p class="fineprint">Free-plan limits: {ext(a["freeLimitsSource"], e(host(a["freeLimitsSource"])))}</p></details></div></article>')
    sug_btn = (f'<a class="btn primary small" id="suggest" href="{e(sug)}" rel="noopener" target="_blank">💡 Suggest an idea</a>' if sug
               else '<span class="btn primary small is-disabled" id="suggest">💡 Suggestions: coming soon</span>')
    note = ("Votes refresh every few minutes. One vote per idea, please." if live else "Voting opens soon. Counts show 0 until it's live; there are no fake numbers here.")
    return f'''<h2 id="automations-h"><span class="num" aria-hidden="true">5</span> Which everyday tasks can I automate for free?</h2>
      <p class="section-intro answer">Logging emails to a spreadsheet, summarising form feedback and turning meeting notes into action items are good first automations. Every idea here uses free tools only, step by step. Upvote the ones you want expanded into full guides, or suggest your own.</p>
      {updated(autos["updated"])}
      <div class="auto-toolbar">
        <span class="sort-wrap" hidden><label for="auto-sort">Sort:</label>
        <select id="auto-sort"><option value="votes">Most votes</option><option value="default">Newest</option></select></span>
        {sug_btn}
      </div>
      <p class="placeholder-note" id="votes-note">{e(note)}</p>
      <div class="autos" id="auto-list">{"".join(out)}</div>'''

def r_head():
    t, d = SITE["title"], SITE["description"]
    return f'''<title>{e(t)}</title>
<meta name="description" content="{e(d)}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="google-site-verification" content="b8aQowdIF8Ybq-6g_K273DIwLxjHl_nhiGMAdsaDWd8">
<link rel="canonical" href="{e(BASE)}">
<link rel="alternate" type="text/markdown" href="index.md" title="This page as Markdown">
<link rel="describedby" type="text/markdown" href="llms.txt" title="llms.txt">
<link rel="icon" href="favicon.ico" sizes="32x32">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta name="theme-color" content="{e(SITE["themeColor"])}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(SITE["siteName"])}">
<meta property="og:title" content="{e(t)}">
<meta property="og:description" content="{e(d)}">
<meta property="og:url" content="{e(BASE)}">
<meta property="og:image" content="{e(BASE)}og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(SITE["ogImageAlt"])}">
<meta property="og:locale" content="{e(SITE["locale"])}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(t)}">
<meta name="twitter:description" content="{e(d)}">
<meta name="twitter:image" content="{e(BASE)}og-image.png">
<meta name="twitter:image:alt" content="{e(SITE["ogImageAlt"])}">''' + (f'\n<meta name="twitter:site" content="{e(SITE["xHandle"])}">' if SITE.get("xHandle") else "")

def jsonld():
    org = {"@type": "Organization", "@id": BASE + "#org", "name": SITE["organizationName"], "url": BASE,
           "logo": {"@type": "ImageObject", "url": BASE + "apple-touch-icon.png", "width": 180, "height": 180}}
    if SITE.get("xHandle"): org["sameAs"] = ["https://x.com/" + SITE["xHandle"].lstrip("@")]
    site = {"@type": "WebSite", "@id": BASE + "#website", "name": SITE["siteName"], "url": BASE, "description": SITE["description"],
            "inLanguage": SITE["lang"], "publisher": {"@id": BASE + "#org"}}
    page = {"@type": "WebPage", "@id": BASE + "#webpage", "url": BASE, "name": SITE["title"], "isPartOf": {"@id": BASE + "#website"},
            "inLanguage": SITE["lang"], "dateModified": LAST_MOD, "primaryImageOfPage": BASE + "og-image.png"}
    faq = {"@type": "FAQPage", "@id": BASE + "#basics", "name": "AI 101: what do I need to know first?",
           "mainEntity": [{"@type": "Question", "name": c["title"], "acceptedAnswer": {"@type": "Answer", "text": f'{c["answer"]} {c["body"]}'}} for c in FAQ]}
    items = {"@type": "ItemList", "@id": BASE + "#models", "name": "Latest AI models", "itemListOrder": "https://schema.org/ItemListOrderDescending",
             "numberOfItems": len(MODELS),
             "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": f'{m["model"]} ({m["company"]})', "url": m["source"],
                                  "description": m["goodFor"]} for i, m in enumerate(MODELS)]}
    graph = {"@context": "https://schema.org", "@graph": [org, site, page, faq, items]}
    return '<script type="application/ld+json">\n' + json.dumps(graph, ensure_ascii=False, indent=1).replace("</", "<\\/") + "\n</script>"

REGIONS = {"head": r_head, "jsonld": jsonld, "basics": r_basics, "models": r_models, "news": r_news, "try": r_try, "automations": r_autos}

def render_index(src):
    for name, fn in REGIONS.items():
        pat = re.compile(rf"(<!-- build:{name} -->)(.*?)(<!-- /build:{name} -->)", re.S)
        if not pat.search(src): sys.exit(f"index.html is missing the <!-- build:{name} --> markers")
        src = pat.sub(lambda m: m.group(1) + "\n" + fn() + "\n" + m.group(3), src, count=1)
    return src

# ---------- Markdown / text files ----------
def md_page():
    L = [f"# {SITE['siteName']}", "", f"> {SITE['description']}", "",
         "Content is researched with AI assistance and every fact links to the lab's or vendor's own page. \"TODO\" means we could not confirm a detail on that page yet.",
         f"Canonical page: {BASE}", "", "## AI 101: what do I need to know first?", "", f"_Last updated: {basics['updated']}_", ""]
    for c in FAQ:
        L += [f"### {c['title']}", "", f"**{c['answer']}** {c['body']}"]
        if c.get("sources"): L += ["", "Sources: " + ", ".join(f"[{s['label']}]({s['url'] if s['url'].startswith('http') else BASE + s['url']})" for s in c["sources"])]
        L.append("")
    L += ["Go deeper (free): " + ", ".join(f"[{l['label']}]({l['url']})" for l in basics["learnMore"]), "",
          "## What are the latest AI models?", "", f"_Last checked: {models['updated']}_", "",
          "| Company | Model | Released | Good for | Free access? | Sources |", "|---|---|---|---|---|---|"]
    for m in MODELS:
        s = " ".join(f"[{host(u)}]({u})" for u in (m.get("source"), m.get("source2")) if u)
        L.append(f"| {m['company']} | {m['model']} | {m['released']} | {m['goodFor']} | {m['free']} | {s} |".replace("\n", " "))
    L += ["", "## What's new in AI this week?", "", f"_Last updated: {news['updated']}_", ""]
    for n in news["items"]:
        L += [f"### {n['title']} ({n['date']})", "", f"{n['summary']} Why it matters: {n['whyItMatters']} [Source]({n['source']})", ""]
    L += ["## What can I try with AI today?", "", f"_Last updated: {tries['updated']}_", ""]
    for t in tries["items"]:
        L += [f"### {t['title']} ({t['tool']})", "", f"Prompt: \"{t['prompt']}\"", "", f"Tip: {t['tip']}" + (f" [Source]({t['source']})" if t.get("source") else ""), ""]
    L += ["## Which everyday tasks can I automate for free?", "", f"_Last updated: {autos['updated']}_", ""]
    for a in autos["items"]:
        L += [f"### {a['title']}", "", f"Level: {a['level']}. Time: {a['time']}. Tools: {', '.join(a['tools'])}.", ""]
        L += [f"{i}. {s}" for i, s in enumerate(a["steps"], 1)]
        L += ["", f"Free-plan limits: {a['freeLimitsSource']}", ""]
    L += ["## How do I get the weekly AI Start Here email?", "", "A free weekly email: one thing that changed, one thing to try, one automation. Signup opens soon on the page above.", ""]
    return "\n".join(L)

def llms_txt():
    newest = ", ".join(f"{m['model']} ({m['company']}, {m['released']})" for m in MODELS[:3])
    return "\n".join([
        f"# {SITE['siteName']}", "",
        f"> {SITE['description']} Written for busy adults (Ireland/EU first) who are new to AI. Free tools only.", "",
        "- Every model row and news item cites the AI lab's or vendor's own page; follow those links before quoting a detail.",
        "- \"TODO\" in the data means the detail was not on the lab's page when checked; do not fill it in by guessing.",
        "- Content is researched with AI assistance and is not affiliated with any AI company.",
        f"- Last updated {LAST_MOD}. Newest models listed: {newest}.", "",
        "## Main page", "",
        f"- [AI Start Here (Markdown version)]({BASE}index.md): the whole page: beginner FAQ, latest models table, news, prompts to try, free automations",
        f"- [AI Start Here (HTML)]({BASE}): the same content for people", "",
        "## Data (source of truth, JSON)", "",
        f"- [Latest models]({BASE}data/models.json): company, model, release date, good for, free access, source URLs",
        f"- [News]({BASE}data/news.json): dated items with summary, why it matters, source URL",
        f"- [AI 101 basics]({BASE}data/basics.json): beginner questions with short answers and sources",
        f"- [Things to try]({BASE}data/try.json): copyable prompts with the free tool to use",
        f"- [Automations]({BASE}data/automations.json): step-by-step free automations with free-plan limit links", "",
        "## Optional", "",
        f"- [llms-full.txt]({BASE}llms-full.txt): this file plus the full Markdown page in one file",
        f"- [Sitemap]({BASE}sitemap.xml)", ""])

def robots_txt():
    bots = [("OpenAI (https://platform.openai.com/docs/bots)", ["OAI-SearchBot", "ChatGPT-User", "GPTBot"]),
            ("Anthropic (https://support.claude.com/en/articles/8896518)", ["Claude-SearchBot", "Claude-User", "ClaudeBot"]),
            ("Perplexity (https://docs.perplexity.ai/guides/bots)", ["PerplexityBot", "Perplexity-User"]),
            ("Google (https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers)", ["Googlebot", "Google-Extended"]),
            ("Microsoft Bing, which also feeds Copilot search (https://www.bing.com/webmasters/help/which-crawlers-does-bing-use-8c184ec0)", ["Bingbot"]),
            ("Apple (https://support.apple.com/en-us/119829)", ["Applebot", "Applebot-Extended"]),
            ("Common Crawl, an open dataset many AI labs use (https://commoncrawl.org/ccbot)", ["CCBot"])]
    L = ["# AI Start Here. Search engines and AI assistants are welcome to read and cite this site.",
         "# Named groups below make that explicit for each AI crawler; tokens verified on the vendors' own docs.", "",
         "User-agent: *", "Allow: /", ""]
    for who, uas in bots:
        L.append(f"# {who}")
        for ua in uas: L += [f"User-agent: {ua}", "Allow: /", ""]
    L += [f"Sitemap: {BASE}sitemap.xml", ""]
    return "\n".join(L)

def sitemap():
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{e(BASE)}</loc><lastmod>{LAST_MOD}</lastmod></url>
</urlset>
'''

def outputs():
    md = md_page()
    return {"index.html": render_index((HERE / "index.html").read_text()), "index.md": md + "\n",
            "llms.txt": llms_txt(), "llms-full.txt": llms_txt() + "\n---\n\n" + md + "\n",
            "robots.txt": robots_txt(), "sitemap.xml": sitemap()}

# ---------- images (only with --assets) ----------
def assets():
    from PIL import Image, ImageDraw, ImageFont
    F = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"; FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font = lambda p, s: ImageFont.truetype(p, s) if pathlib.Path(p).exists() else ImageFont.load_default()
    W, H = 1200, 630; img = Image.new("RGB", (W, H), "#14161f"); px = img.load()
    for y in range(H):  # simple vertical gradient indigo -> near-black
        for x in range(W):
            t = (x / W) * 0.35 + (y / H) * 0.65
            px[x, y] = (int(79 * (1 - t) + 20 * t), int(70 * (1 - t) + 22 * t), int(229 * (1 - t) + 31 * t))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((80, 80, 200, 200), 28, fill="#ffffff"); d.text((140, 140), "AI", font=font(F, 56), fill="#4f46e5", anchor="mm")
    d.text((80, 260), "AI Start Here", font=font(F, 76), fill="#ffffff")
    d.text((80, 365), "Get useful with AI this week, for free.", font=font(FR, 42), fill="#e0e7ff")
    d.text((80, 425), "Basics · latest models · news · things to try · automations", font=font(FR, 30), fill="#c7d2fe")
    d.text((80, 530), "Every fact links to its source.", font=font(F, 30), fill="#ffffff")
    img.save(HERE / "og-image.png", optimize=True)
    def icon(n):
        im = Image.new("RGBA", (n, n), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
        dr.rounded_rectangle((0, 0, n - 1, n - 1), max(2, n // 5), fill="#4f46e5")
        dr.text((n / 2, n / 2 + n * 0.02), "AI", font=font(F, int(n * 0.46)), fill="#ffffff", anchor="mm"); return im
    icon(180).convert("RGB").save(HERE / "apple-touch-icon.png", optimize=True)
    icon(64).save(HERE / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    (HERE / "favicon.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="13" fill="#4f46e5"/>'
        '<text x="32" y="43" font-family="system-ui,Segoe UI,Arial,sans-serif" font-size="30" font-weight="800" text-anchor="middle" fill="#fff">AI</text></svg>\n')

def main():
    check = "--check" in sys.argv
    if "--assets" in sys.argv and not check: assets()
    stale = []
    for name, content in outputs().items():
        p = HERE / name
        if p.exists() and p.read_text() == content: continue
        if check: stale.append(name)
        else: p.write_text(content); print("wrote", name)
    if check:
        print("stale: " + ", ".join(stale) if stale else "up to date"); sys.exit(1 if stale else 0)

if __name__ == "__main__": main()
