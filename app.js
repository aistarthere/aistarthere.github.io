/* Progressive enhancement only. All content is pre-rendered into index.html by build.py
   from data/*.json, so the page works without JavaScript. This file adds: mobile menu,
   model filter, copy buttons, live vote counts + sorting, the beehiiv embed and analytics. */
(function () {
  "use strict";
  const CFG = window.SITE_CONFIG || {};
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));

  // Mobile menu
  const btn = $(".menu-btn"), nav = $(".nav");
  if (btn && nav) {
    btn.addEventListener("click", () => { const o = nav.classList.toggle("open"); btn.setAttribute("aria-expanded", String(o)); btn.setAttribute("aria-label", o ? "Close menu" : "Open menu"); });
    nav.addEventListener("click", (e) => { if (e.target.tagName === "A") { nav.classList.remove("open"); btn.setAttribute("aria-expanded", "false"); } });
  }

  // 2. Model filter (hides rows of the pre-rendered table)
  const filterRow = $(".filter-row"), filter = $("#model-filter"), body = $("#models-body");
  if (filterRow && filter && body) {
    filterRow.hidden = false;
    const empty = document.createElement("tr"); empty.innerHTML = '<td colspan="6">No matches.</td>'; empty.hidden = true; body.appendChild(empty);
    filter.addEventListener("input", () => {
      const q = filter.value.trim().toLowerCase(); let shown = 0;
      $$("#models-body tr").forEach((tr) => { if (tr === empty) return; const hit = !q || tr.textContent.toLowerCase().includes(q); tr.hidden = !hit; shown += hit; });
      empty.hidden = shown > 0;
    });
  }

  // 4. Copy buttons
  $$(".copy").forEach((b) => { if (navigator.clipboard) b.hidden = false; });
  document.addEventListener("click", (e) => {
    const b = e.target.closest(".copy"); if (!b) return;
    const el = document.getElementById(b.dataset.target);
    navigator.clipboard.writeText(el.textContent).then(() => { b.textContent = "Copied ✓"; setTimeout(() => (b.textContent = "Copy prompt"), 1500); }).catch(() => {});
  });

  
  // 5. Votes: read the published counts CSV (idea,votes) and enable sorting
  const list = $("#auto-list"), sortWrap = $(".sort-wrap"), sort = $("#auto-sort");
  const cards = list ? $$("#auto-list .auto") : [];
  cards.forEach((c, i) => (c.dataset.idx = i));
  const render = () => {
    const by = sort.value;
    cards.slice().sort((a, b) => by === "votes" ? (+b.dataset.votes || 0) - (+a.dataset.votes || 0) || a.dataset.idx - b.dataset.idx : a.dataset.idx - b.dataset.idx)
      .forEach((c) => list.appendChild(c));
  };
  if (CFG.votesCsvUrl && list) {
    fetch(CFG.votesCsvUrl).then((r) => r.text()).then((csv) => {
      const votes = {};
      csv.trim().split(/\r?\n/).slice(1).forEach((line) => { const [id, n] = line.split(","); if (id) votes[id.trim().replace(/"/g, "")] = parseInt(n, 10) || 0; });
      cards.forEach((c) => { const span = c.querySelector(".count"); const n = votes[span.dataset.idea] || 0; span.textContent = n; c.dataset.votes = n; });
      sortWrap.hidden = false; sort.addEventListener("change", render); render();
    }).catch(() => {});
  }

  // 6. Newsletter embed
  const nl = $("#newsletter-embed");
  if (nl && CFG.beehiivEmbedScriptSrc) {
    nl.innerHTML = ""; const s = document.createElement("script"); s.src = CFG.beehiivEmbedScriptSrc; s.async = true; if (CFG.beehiivFormId) s.setAttribute("data-beehiiv-form", CFG.beehiivFormId); nl.appendChild(s);
  }
  if (CFG.beehiivPublicationUrl) {
    const a = document.createElement("a"); a.href = CFG.beehiivPublicationUrl; a.target = "_blank"; a.rel = "noopener"; a.textContent = "newsletter archive";
    const p = $("#newsletter-archive"); p.textContent = "Read past issues: "; p.appendChild(a);
  }

  // Analytics (privacy-friendly, only if configured)
  if (CFG.goatcounterCode) {
    const g = document.createElement("script"); g.async = true; g.src = "https://gc.zgo.at/count.js";
    g.dataset.goatcounter = `https://${CFG.goatcounterCode}.goatcounter.com/count`; document.body.appendChild(g);
  }
})();
