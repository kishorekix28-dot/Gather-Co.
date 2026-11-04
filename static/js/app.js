/* StockPilot UI helpers */
(function () {
  "use strict";
  // Mobile sidebar
  document.querySelectorAll("[data-sidebar-toggle]").forEach((b) =>
    b.addEventListener("click", () => document.body.classList.toggle("sidebar-open")));
  document.querySelectorAll("[data-sidebar-close]").forEach((b) =>
    b.addEventListener("click", () => document.body.classList.remove("sidebar-open")));

  // Auto-dismiss success/info toasts
  document.querySelectorAll("#toastStack .alert-success, #toastStack .alert-info").forEach((el) => {
    setTimeout(() => { try { bootstrap.Alert.getOrCreateInstance(el).close(); } catch (e) { el.remove(); } }, 6000);
  });

  // Loading state on submit buttons
  document.querySelectorAll("form[data-loading]").forEach((form) => {
    form.addEventListener("submit", () => {
      const btn = form.querySelector("button[type=submit]");
      if (btn && form.checkValidity()) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Saving…';
      }
    });
  });

  // Auto-submit filter selects
  document.querySelectorAll("[data-autosubmit]").forEach((el) =>
    el.addEventListener("change", () => el.form && el.form.submit()));

  // Toggle supplier/unit cost fields on the stock movement form
  const typeSel = document.getElementById("id_transaction_type");
  if (typeSel) {
    const update = () => {
      const t = typeSel.value;
      document.querySelectorAll("[data-only-in]").forEach((el) => el.classList.toggle("d-none", t !== "IN"));
      const hint = document.getElementById("qtyLabel");
      if (hint) hint.textContent = t === "ADJ" ? "Counted quantity (new stock level)" : "Quantity";
    };
    typeSel.addEventListener("change", update);
    update();
  }
})();
