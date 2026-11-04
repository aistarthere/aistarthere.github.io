/* Starter guide page: beehiiv signup embeds + analytics (same config as the home page). */
(() => {
  const CFG = window.SITE_CONFIG || {};
  if (CFG.beehiivEmbedScriptSrc) document.querySelectorAll(".nl-embed").forEach((nl) => {
    const load = () => { nl.innerHTML = ""; const s = document.createElement("script"); s.src = CFG.beehiivEmbedScriptSrc; s.async = true; if (CFG.beehiivFormId) s.setAttribute("data-beehiiv-form", CFG.beehiivFormId); nl.appendChild(s);
      new MutationObserver(() => nl.querySelectorAll("iframe:not([title])").forEach((f) => f.title = "Newsletter signup form")).observe(nl, { childList: true, subtree: true }); };
    if (!("IntersectionObserver" in window)) return load();
    const io = new IntersectionObserver((es) => { if (es.some((x) => x.isIntersecting)) { io.disconnect(); load(); } }, { rootMargin: "200px" }); io.observe(nl);
  });
  if (CFG.goatcounterCode) {
    const g = document.createElement("script"); g.async = true; g.src = "https://gc.zgo.at/count.js";
    g.dataset.goatcounter = `https://${CFG.goatcounterCode}.goatcounter.com/count`; document.body.appendChild(g);
  }
})();
