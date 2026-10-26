#!/usr/bin/env python3
"""Headless-browser checks: console errors, failed requests, axe-core a11y,
horizontal overflow at 375px and 1280px, content present with JS disabled,
and screenshots. Usage: browser_checks.py URL AXE_JS_PATH OUT_DIR"""
import json, sys, pathlib
from playwright.sync_api import sync_playwright

URL, AXE, OUT = sys.argv[1], pathlib.Path(sys.argv[2]).read_text(), pathlib.Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
res = {"console_errors": [], "failed_requests": [], "axe_violations": [], "overflow": {}, "nojs": {}}

with sync_playwright() as p:
    b = p.chromium.launch()
    for name, vp in (("desktop", {"width": 1280, "height": 900}), ("mobile", {"width": 375, "height": 812})):
        ctx = b.new_context(viewport=vp, device_scale_factor=1, is_mobile=(name == "mobile"), has_touch=(name == "mobile"))
        pg = ctx.new_page()
        pg.on("console", lambda m, n=name: m.type == "error" and res["console_errors"].append(f"[{n}] {m.text}"))
        pg.on("pageerror", lambda e, n=name: res["console_errors"].append(f"[{n}] pageerror: {e}"))
        pg.on("requestfailed", lambda r, n=name: res["failed_requests"].append(f"[{n}] {r.url} {r.failure}"))
        pg.on("response", lambda r, n=name: r.status >= 400 and res["failed_requests"].append(f"[{n}] {r.status} {r.url}"))
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(500)
        sw, cw = pg.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        res["overflow"][name] = {"scrollWidth": sw, "clientWidth": cw, "ok": sw <= cw}
        if name == "mobile":
            # open the mobile menu to make sure it works
            try:
                pg.click(".menu-btn"); res["mobile_menu_opens"] = pg.evaluate("document.querySelector('.nav').classList.contains('open')"); pg.click(".menu-btn")
            except Exception as e: res["mobile_menu_opens"] = f"error: {e}"
        pg.add_script_tag(content=AXE)
        axe = pg.evaluate("async () => (await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21a','wcag21aa','best-practice']}})).violations.map(v => ({id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length, sample: v.nodes.slice(0,2).map(n => n.target.join(' '))}))")
        for v in axe: v["viewport"] = name
        res["axe_violations"] += axe
        pg.screenshot(path=str(OUT / f"{name}.png"), full_page=(name == "mobile"))
        if name == "desktop": pg.screenshot(path=str(OUT / "desktop-full.png"), full_page=True)
        ctx.close()
    # JS disabled: what a non-JS crawler sees
    ctx = b.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 900})
    pg = ctx.new_page(); pg.goto(URL, wait_until="load")
    res["nojs"] = pg.evaluate("""() => ({
      model_rows: document.querySelectorAll('#models-body tr').length,
      news_items: document.querySelectorAll('#news-list li').length,
      basics_cards: document.querySelectorAll('#basics-cards .card').length,
      try_cards: document.querySelectorAll('#try-cards .card').length,
      automations: document.querySelectorAll('#auto-list .auto').length,
      faq_items: document.querySelectorAll('#faq .faq-item').length,
      h1: document.querySelectorAll('h1').length,
      jsonld_blocks: document.querySelectorAll('script[type="application/ld+json"]').length
    })""")
    ctx.close(); b.close()

nj = res["nojs"]
res["nojs_ok"] = all(nj.get(k, 0) > 0 for k in ("model_rows", "news_items", "basics_cards", "try_cards", "automations")) and nj.get("h1") == 1
(OUT / "browser.json").write_text(json.dumps(res, indent=2))
print(json.dumps(res, indent=2))
