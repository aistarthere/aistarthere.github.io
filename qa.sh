#!/usr/bin/env bash
# AI Start Here: QA pass. Safe to run on a schedule. Prints a PASS/WARN/FAIL summary and
# exits non-zero if anything FAILs.   Usage: site/qa.sh [--offline] [--no-lighthouse]
# Env: SITE_DIR (default: this script's folder), QA_PORT (default 8799), QA_OUT (report dir).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SITE="${SITE_DIR:-$HERE}"
ROOT="$(cd "$HERE/.." && pwd)"
TOOLS="$ROOT/tools/qa-node"
OUT="${QA_OUT:-$ROOT/qa-reports/$(date +%Y-%m-%dT%H%M)}"
PORT="${QA_PORT:-8799}"
OFFLINE=""; LH=1
for a in "$@"; do case "$a" in --offline) OFFLINE="--offline";; --no-lighthouse) LH=0;; esac; done
mkdir -p "$OUT"
declare -a SUMMARY; FAILS=0; WARNS=0
pass(){ SUMMARY+=("PASS  $1"); }
warn(){ SUMMARY+=("WARN  $1"); WARNS=$((WARNS+1)); }
fail(){ SUMMARY+=("FAIL  $1"); FAILS=$((FAILS+1)); }

# 0. Tooling (installs once into tools/qa-node and the user's Python; all free/open source)
if [ ! -d "$TOOLS/node_modules/axe-core" ]; then (mkdir -p "$TOOLS" && cd "$TOOLS" && npm init -y >/dev/null && npm i -s axe-core lighthouse vnu-jar >/dev/null 2>&1); fi
python3 -c "import playwright" 2>/dev/null || pip install -q --break-system-packages playwright >/dev/null 2>&1
python3 -m playwright install chromium >/dev/null 2>&1 || true

# 1. JSON source files parse
bad=0; for f in "$SITE"/data/*.json; do python3 -m json.tool "$f" >/dev/null 2>&1 || { bad=1; echo "bad JSON: $f"; }; done
[ $bad = 0 ] && pass "data/*.json parse" || fail "data/*.json has invalid JSON"

# 2. Pre-render is current and idempotent
if [ -f "$SITE/build.py" ]; then
  if python3 "$SITE/build.py" --check >"$OUT/build.txt" 2>&1; then pass "build.py --check: generated files match data/*.json"
  else fail "build.py --check: generated files are stale. Run: python3 site/build.py"; fi
else fail "no build.py: content is only rendered by JavaScript"; fi

# 3. Required SEO / AI files
for f in robots.txt sitemap.xml llms.txt llms-full.txt index.md og-image.png favicon.svg favicon.ico apple-touch-icon.png; do
  [ -s "$SITE/$f" ] && pass "file present: $f" || fail "missing file: $f"; done
if [ -s "$SITE/og-image.png" ]; then
  dim=$(python3 -c "from PIL import Image;im=Image.open('$SITE/og-image.png');print('%dx%d'%im.size)" 2>/dev/null)
  [ "$dim" = "1200x630" ] && pass "og-image.png is 1200x630" || fail "og-image.png is $dim, want 1200x630"; fi
python3 - "$SITE" >"$OUT/meta.txt" 2>&1 <<'PY'
import sys, json, re, pathlib
s = pathlib.Path(sys.argv[1]); h = (s/"index.html").read_text()
need = {"title": r"<title>[^<]{10,70}</title>", "meta description": r'<meta name="description" content="[^"]{50,170}"',
        "canonical": r'<link rel="canonical"', "og:image": r'property="og:image"', "twitter:card": r'name="twitter:card"',
        "favicon": r'rel="icon"', "llms.txt describedby": r'rel="describedby"', "markdown alternate": r'type="text/markdown"'}
miss = [k for k, rx in need.items() if not re.search(rx, h)]
blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S); types = []
try:
    for b in blocks:
        d = json.loads(b); g = d.get("@graph", [d]); types += [x.get("@type") for x in g]
except Exception as e: miss.append(f"JSON-LD parse error: {e}")
for t in ("WebSite", "Organization", "FAQPage", "ItemList"):
    if t not in types: miss.append(f"JSON-LD {t}")
r = (s/"robots.txt").read_text() if (s/"robots.txt").exists() else ""
for bot in ("GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User", "PerplexityBot", "Perplexity-User", "Google-Extended", "Googlebot", "Bingbot", "Applebot", "Applebot-Extended", "CCBot"):
    if not re.search(rf"User-agent:\s*{re.escape(bot)}\s*\nAllow:\s*/", r, re.I): miss.append(f"robots.txt allow {bot}")
if "Sitemap:" not in r: miss.append("robots.txt Sitemap line")
l = (s/"llms.txt").read_text() if (s/"llms.txt").exists() else ""
if not re.match(r"\ufeff?# .+\n\n> .+", l): miss.append("llms.txt: H1 then blockquote (llmstxt.org format)")
print("\n".join(miss)); sys.exit(1 if miss else 0)
PY
[ $? = 0 ] && pass "head tags, JSON-LD (WebSite/Organization/FAQPage/ItemList), robots AI bots, llms.txt format" || fail "SEO/AI checks: $(tr '\n' ';' <"$OUT/meta.txt")"
grep -q "BASE_URL_PLACEHOLDER" "$SITE/index.html" 2>/dev/null && warn "BASE_URL is still the placeholder (set baseUrl in site/site.json)"
curl -s -o /dev/null -w "%{http_code}" --max-time 15 https://aistarthere.github.io/ 2>/dev/null | grep -q "^200$" && pass "live site https://aistarthere.github.io/ responds 200" || warn "live site https://aistarthere.github.io/ not reachable yet (not deployed?)"

# 4. HTML validation (Nu Html Checker, the W3C validator engine)
if command -v java >/dev/null && [ -f "$TOOLS/node_modules/vnu-jar/build/dist/vnu.jar" ]; then
  java -jar "$TOOLS/node_modules/vnu-jar/build/dist/vnu.jar" --format json "$SITE/index.html" 2>"$OUT/vnu.json"
  read -r e w < <(python3 -c "import json;m=json.load(open('$OUT/vnu.json'))['messages'];print(sum(x['type']=='error' for x in m),sum(x['type']!='error' for x in m))")
  [ "$e" = 0 ] && pass "HTML valid (vnu): 0 errors, $w warnings/info" || fail "HTML validation (vnu): $e errors, $w warnings (see $OUT/vnu.json)"
elif command -v tidy >/dev/null; then
  tidy -q -e "$SITE/index.html" >"$OUT/tidy.txt" 2>&1; e=$(grep -c "Error:" "$OUT/tidy.txt"); [ "$e" = 0 ] && pass "HTML (tidy): 0 errors" || fail "HTML (tidy): $e errors"
else warn "no HTML validator available (install Java for vnu, or tidy)"; fi

# 5. Local server
python3 -m http.server "$PORT" -d "$SITE" >/dev/null 2>&1 & SRV=$!; trap 'kill $SRV 2>/dev/null' EXIT; sleep 1
URL="http://localhost:$PORT/"

# 6. Links
python3 "$HERE/qa/check_links.py" "$SITE" $OFFLINE >"$OUT/links.txt" 2>&1
lj=$(tail -1 "$OUT/links.txt")
lf=$(python3 -c "import json,sys;print(json.loads(sys.argv[1])['links_fail'])" "$lj" 2>/dev/null || echo "?")
lw=$(python3 -c "import json,sys;print(json.loads(sys.argv[1])['links_warn'])" "$lj" 2>/dev/null || echo "?")
[ "$lf" = 0 ] && pass "links: $lj" || fail "links: $lf broken (see $OUT/links.txt)"
[ "$lw" != 0 ] && [ "$lw" != "?" ] && warn "links: $lw returned 401/403/429 to the checker (bot protection; open by hand if worried)"

# 7. Browser: console errors, a11y (axe-core), 375px + 1280px overflow, JS-disabled content
python3 "$HERE/qa/browser_checks.py" "$URL" "$TOOLS/node_modules/axe-core/axe.min.js" "$OUT" >"$OUT/browser.txt" 2>&1
if [ -f "$OUT/browser.json" ]; then
  eval "$(python3 - "$OUT/browser.json" <<'PY'
import json,sys; r=json.load(open(sys.argv[1]))
ser=[v for v in r['axe_violations'] if v['impact'] in ('serious','critical')]
print(f"CE={len(r['console_errors'])} FR={len(r['failed_requests'])} AX={len(r['axe_violations'])} AXS={len(ser)} OVM={int(r['overflow']['mobile']['ok'])} OVD={int(r['overflow']['desktop']['ok'])} NOJS={int(r['nojs_ok'])} MENU={int(r.get('mobile_menu_opens') is True)}")
PY
)"
  [ "$CE" = 0 ] && pass "console errors: 0" || fail "console errors: $CE"
  [ "$FR" = 0 ] && pass "failed network requests: 0" || fail "failed network requests: $FR"
  [ "$AXS" = 0 ] && pass "axe-core: 0 serious/critical ($AX total violations across both viewports)" || fail "axe-core: $AXS serious/critical violations ($AX total)"
  [ "$AX" != 0 ] && [ "$AXS" = 0 ] && warn "axe-core: $AX minor/moderate violations (see $OUT/browser.json)"
  [ "$OVM" = 1 ] && pass "mobile 375px: no horizontal overflow" || fail "mobile 375px: page scrolls sideways"
  [ "$OVD" = 1 ] && pass "desktop 1280px: no horizontal overflow" || fail "desktop 1280px: horizontal overflow"
  [ "$MENU" = 1 ] && pass "mobile menu opens" || fail "mobile menu does not open"
  [ "$NOJS" = 1 ] && pass "JS disabled: all sections have content" || fail "JS disabled: sections are empty (crawlers see nothing)"
else fail "browser checks did not run (see $OUT/browser.txt)"; fi

# 8. Lighthouse (mobile emulation, Lighthouse defaults)
if [ $LH = 1 ]; then
  CHROME_PATH="${CHROME_PATH:-$(python3 -c "from playwright.sync_api import sync_playwright as s;p=s().start();print(p.chromium.executable_path);p.stop()" 2>/dev/null)}"
  CHROME_PATH="$CHROME_PATH" "$TOOLS/node_modules/.bin/lighthouse" "$URL" --quiet --output=json --output-path="$OUT/lighthouse.json" \
    --only-categories=performance,accessibility,best-practices,seo --chrome-flags="--headless=new --no-sandbox" >/dev/null 2>&1
  if [ -s "$OUT/lighthouse.json" ]; then
    while read -r cat score; do
      if [ "$score" = "None" ]; then warn "lighthouse $cat: no score"; continue; fi
      min=90; [ "$cat" = performance ] && min=80
      [ "$score" -ge "$min" ] && pass "lighthouse $cat: $score" || { [ "$cat" = performance ] && warn "lighthouse $cat: $score (<$min; localhost numbers vary)" || fail "lighthouse $cat: $score (<$min)"; }
    done < <(python3 -c "import json;c=json.load(open('$OUT/lighthouse.json'))['categories'];[print(k, None if v['score'] is None else round(v['score']*100)) for k,v in c.items()]")
  else warn "lighthouse did not run"; fi
fi

echo; echo "== AI Start Here QA $(date '+%Y-%m-%d %H:%M %Z') :: $SITE"
printf '%s\n' "${SUMMARY[@]}"
echo "== RESULT: $([ $FAILS = 0 ] && echo PASS || echo FAIL)  fails=$FAILS warns=$WARNS  reports: $OUT"
[ $FAILS = 0 ]
