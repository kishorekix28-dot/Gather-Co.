/* FAQ page: renders FAQ records fetched from the REST API (SQL-backed). */
(function () {
  "use strict";
  const list = document.getElementById("faqList");
  const status = document.getElementById("faqStatus");
  const search = document.getElementById("faqSearch");
  const catSel = document.getElementById("faqCategory");
  let all = [];
  let timer = null;

  function esc(s) { return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
  function md(s) { return esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>"); }

  function render(items) {
    const cat = catSel.value;
    const shown = cat ? items.filter((f) => f.category === cat) : items;
    if (!shown.length) {
      list.innerHTML = '<div class="card"><div class="empty-state"><i class="bi bi-search"></i><h3>No FAQs match your search</h3><p>Try another keyword or ask the assistant.</p></div></div>';
      return;
    }
    list.innerHTML = shown.map((f, i) => `
      <div class="accordion-item faq-item" data-testid="faq-item" data-faq-id="${f.id}">
        <h2 class="accordion-header"><button class="accordion-button ${i ? "collapsed" : ""}" type="button" data-bs-toggle="collapse" data-bs-target="#faq-${f.id}" aria-expanded="${i ? "false" : "true"}">
          <span class="badge-soft badge-info me-2">${esc(f.category)}</span>${esc(f.question)}</button></h2>
        <div id="faq-${f.id}" class="accordion-collapse collapse ${i ? "" : "show"}" data-bs-parent="#faqList"><div class="accordion-body">${md(f.answer)}</div></div>
      </div>`).join("");
  }

  async function load(url) {
    status.classList.remove("d-none");
    status.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Loading FAQs…';
    try {
      const res = await fetch(url, { headers: { Accept: "application/json" }, credentials: "same-origin" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      const items = Array.isArray(data) ? data : data.results;
      status.classList.add("d-none");
      return items;
    } catch (e) {
      status.innerHTML = '<div class="alert alert-danger mb-0 w-100"><i class="bi bi-exclamation-triangle me-1"></i>Could not load FAQs (' + esc(e.message) + '). Please refresh, or ask the assistant.</div>';
      return null;
    }
  }

  async function init() {
    const items = await load("/api/faqs/");
    if (!items) return;
    all = items;
    [...new Set(all.map((f) => f.category))].sort().forEach((c) => catSel.insertAdjacentHTML("beforeend", `<option>${esc(c)}</option>`));
    document.querySelector(".page-header p").insertAdjacentHTML("beforeend", ` <span class="badge-soft badge-in" data-testid="faq-count">${all.length} FAQs</span>`);
    render(all);
    try {
      const res = await fetch("/api/errors/", { headers: { Accept: "application/json" } });
      const errs = await res.json();
      document.getElementById("errorSummary").innerHTML = `The assistant explains ${errs.length} HTTP error codes: ` +
        errs.map((e) => `<a href="#" data-open-assistant data-question="What does error ${e.code} mean?">${e.code}</a>`).join(", ") + ".";
    } catch (e) { document.getElementById("errorSummary").textContent = "Ask the assistant what an error code means."; }
  }

  search.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const q = search.value.trim();
      if (!q) { render(all); return; }
      const items = await load("/api/faqs/search/?q=" + encodeURIComponent(q));
      if (items) render(items);
    }, 250);
  });
  catSel.addEventListener("change", () => search.value.trim() ? search.dispatchEvent(new Event("input")) : render(all));
  document.getElementById("faqSearchForm").addEventListener("submit", (e) => e.preventDefault());
  init();
})();
