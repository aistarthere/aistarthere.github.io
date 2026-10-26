#!/usr/bin/env python3
"""Check every internal and external link/asset in the built site.
FAIL = 404/410/5xx/DNS/timeout on a link, or a missing local file.
WARN = 401/403/429/999 (usually bot protection; not proof the page is gone).
Usage: check_links.py SITE_DIR [--offline]"""
import json, re, sys, pathlib, concurrent.futures as cf
from urllib.parse import urlparse
from html.parser import HTMLParser
import requests

SITE = pathlib.Path(sys.argv[1]).resolve()
OFFLINE = "--offline" in sys.argv
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36 ai101-linkcheck"
PLACEHOLDER = "BASE_URL_PLACEHOLDER"
try: BASE = json.loads((SITE / "site.json").read_text())["baseUrl"].rstrip("/") + "/"
except Exception: BASE = None

class P(HTMLParser):
    def __init__(s): super().__init__(); s.urls=[]; s.ids=set()
    def handle_starttag(s, tag, attrs):
        a = dict(attrs)
        if "id" in a: s.ids.add(a["id"])
        for k in ("href", "src"):
            if a.get(k): s.urls.append(a[k])

def collect():
    urls, ids, anchors = set(), set(), set()
    for f in SITE.rglob("*.html"):
        if "qa" in f.relative_to(SITE).parts: continue
        p = P(); p.feed(f.read_text()); ids |= p.ids
        for u in p.urls:
            if u.startswith("#"): anchors.add(u[1:])
            else: urls.add(u)
    for f in SITE.glob("data/*.json"):
        for u in re.findall(r'https?://[^"\s]+', f.read_text()): urls.add(u)
    for f in list(SITE.glob("*.txt")) + list(SITE.glob("*.md")) + list(SITE.glob("*.xml")):
        if f.name == "README.md": continue
        for u in re.findall(r'https?://[^\s)<>"\]]+', f.read_text()):
            if "sitemaps.org/schemas" not in u: urls.add(u.rstrip(".,"))  # skip XML namespace
    return urls, ids, anchors

def check_ext(u):
    for method in ("head", "get"):
        try:
            r = requests.request(method, u, headers={"User-Agent": UA, "Accept-Language": "en"}, timeout=20, allow_redirects=True)
            if method == "head" and r.status_code in (403, 404, 405, 429, 500, 501): continue
            return u, r.status_code
        except requests.RequestException as e:
            err = type(e).__name__
    return u, err

def main():
    urls, ids, anchors = collect()
    fails, warns, ok = [], [], 0
    for a in sorted(anchors):
        if a and a not in ids: fails.append(f"missing anchor #{a}")
        else: ok += 1
    ext = []
    for u in sorted(urls):
        if PLACEHOLDER in u: continue  # canonical/OG placeholders until the real domain exists
        if u.startswith(("mailto:", "data:", "javascript:")): continue
        if BASE and u.startswith(BASE): u = "/" + u[len(BASE):]  # own-site URLs: check the local file (works before deploy)
        elif u.startswith(("http://", "https://")): ext.append(u); continue
        path = (SITE / urlparse(u).path.lstrip("/")).resolve()
        if path.is_dir(): path = path / "index.html"
        if path.exists(): ok += 1
        else: fails.append(f"missing local file: {u}")
    if not OFFLINE:
        with cf.ThreadPoolExecutor(12) as ex:
            for u, st in ex.map(check_ext, ext):
                if isinstance(st, int) and st < 400: ok += 1
                elif st in (401, 403, 429, 999): warns.append(f"{st} {u}")
                else: fails.append(f"{st} {u}")
    if warns:  # re-check bot-blocked links in a real headless browser before warning
        try:
            from playwright.sync_api import sync_playwright
            still = []
            with sync_playwright() as p:
                b = p.chromium.launch(); pg = b.new_page(user_agent=UA)
                for w in warns:
                    u = w.split(" ", 1)[1]
                    try: st = pg.goto(u, timeout=30000).status
                    except Exception as ex: st = type(ex).__name__
                    if isinstance(st, int) and st < 400: ok += 1
                    elif st in (404, 410): fails.append(f"{st} {u} (browser)")
                    else: still.append(f"{st} {u} (browser)")
                b.close()
            warns = still
        except ImportError: pass
    for w in warns: print("WARN", w)
    for f in fails: print("FAIL", f)
    print(json.dumps({"links_ok": ok, "links_warn": len(warns), "links_fail": len(fails), "external_checked": 0 if OFFLINE else len(ext)}))
    sys.exit(1 if fails else 0)

main()
