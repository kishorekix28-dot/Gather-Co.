/* StockPilot global assistant widget */
(function () {
  "use strict";
  const root = document.getElementById("assistant-widget");
  if (!root) return;

  const win = document.getElementById("chatWindow");
  const launcher = document.getElementById("chatLauncher");
  const launcherIcon = document.getElementById("chatLauncherIcon");
  const body = document.getElementById("chatBody");
  const form = document.getElementById("chatForm");
  const input = document.getElementById("chatInput");
  const sendBtn = document.getElementById("chatSend");
  const suggestions = document.getElementById("chatSuggestions");
  const csrf = root.querySelector("input[name=csrfmiddlewaretoken]").value;
  const SOURCE_LABELS = { faq: "FAQ", error_database: "Error database", help_docs: "Help docs", ai_fallback: "Support ticket", system: "Assistant" };
  let historyLoaded = false;
  let busy = false;

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function format(text) {
    return escapeHtml(text).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  }
  function scroll() { body.scrollTop = body.scrollHeight; }

  function open() {
    win.classList.add("open");
    launcher.setAttribute("aria-expanded", "true");
    launcherIcon.className = "bi bi-x-lg";
    if (!historyLoaded) loadHistory();
    setTimeout(() => input.focus(), 50);
  }
  function close() {
    win.classList.remove("open");
    launcher.setAttribute("aria-expanded", "false");
    launcherIcon.className = "bi bi-chat-dots-fill";
  }
  function toggle() { win.classList.contains("open") ? close() : open(); }

  function addUser(text) {
    const el = document.createElement("div");
    el.className = "msg msg-user";
    el.textContent = text;
    body.appendChild(el);
    scroll();
  }

  function addBot(data) {
    const el = document.createElement("div");
    el.className = "msg msg-bot";
    el.dataset.testid = "bot-message";
    el.setAttribute("data-source", data.source || "");
    let html = format(data.reply || data.assistant_response || "");
    const ticketId = data.ticket ? data.ticket.ticket_id : data.ticket_id;
    if (ticketId) {
      html += `<div><span class="ticket-chip" data-testid="ticket-id"><i class="bi bi-ticket-perforated"></i>${escapeHtml(ticketId)}</span></div>`;
    }
    html += `<div class="msg-meta"><span class="msg-source src-${escapeHtml(data.source || "system")}">${escapeHtml(SOURCE_LABELS[data.source] || "Assistant")}</span>`;
    const messageId = data.message_id || data.id;
    if (messageId) {
      html += `<span class="ms-auto d-inline-flex gap-1">
        <button type="button" class="fb-btn" data-rating="up" aria-label="Helpful" data-testid="feedback-up"><i class="bi bi-hand-thumbs-up"></i></button>
        <button type="button" class="fb-btn" data-rating="down" aria-label="Not helpful" data-testid="feedback-down"><i class="bi bi-hand-thumbs-down"></i></button></span>`;
    }
    html += "</div>";
    el.innerHTML = html;
    if (messageId) el.dataset.messageId = messageId;
    body.appendChild(el);
    scroll();
  }

  function addError(text) {
    const el = document.createElement("div");
    el.className = "msg msg-error";
    el.setAttribute("role", "alert");
    el.innerHTML = `<i class="bi bi-exclamation-triangle me-1"></i>${escapeHtml(text)}`;
    body.appendChild(el);
    scroll();
  }

  function showTyping() {
    const el = document.createElement("div");
    el.className = "msg msg-bot typing";
    el.id = "chatTyping";
    el.setAttribute("aria-label", "Assistant is typing");
    el.innerHTML = "<span></span><span></span><span></span>";
    body.appendChild(el);
    scroll();
  }
  function hideTyping() { const t = document.getElementById("chatTyping"); if (t) t.remove(); }

  async function loadHistory() {
    historyLoaded = true;
    try {
      const res = await fetch(root.dataset.historyUrl, { credentials: "same-origin", headers: { Accept: "application/json" } });
      if (!res.ok) return;
      const data = await res.json();
      if (data.messages && data.messages.length) {
        if (suggestions) suggestions.remove();
        const sep = document.createElement("div");
        sep.className = "text-center small text-muted";
        sep.textContent = "Earlier in this session";
        body.appendChild(sep);
        data.messages.forEach((m) => { addUser(m.user_message); addBot(m); });
      }
    } catch (e) { /* history is optional */ }
  }

  async function send(text) {
    text = (text || "").trim();
    if (!text || busy) return;
    if (text.length > 1000) { addError("Messages are limited to 1000 characters."); return; }
    if (suggestions && suggestions.parentNode) suggestions.remove();
    busy = true;
    sendBtn.disabled = true;
    input.value = "";
    addUser(text);
    showTyping();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 20000);
    try {
      const res = await fetch(root.dataset.chatUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf, Accept: "application/json" },
        body: JSON.stringify({ message: text }),
        signal: controller.signal,
      });
      let data = null;
      try { data = await res.json(); } catch (e) { data = null; }
      hideTyping();
      if (!res.ok) {
        const fallback = { 400: "I couldn't read that message. Please rephrase it.", 403: "Your session expired. Please refresh the page and try again.",
          429: "You're sending messages too quickly. Please wait a minute.", 500: "The assistant hit a server error. Please try again shortly." };
        addError((data && data.error) || fallback[res.status] || `Request failed (HTTP ${res.status}).`);
        return;
      }
      addBot(data);
    } catch (err) {
      hideTyping();
      addError(err.name === "AbortError" ? "The assistant took too long to respond. Please try again." : "Network error – check your connection and try again.");
    } finally {
      clearTimeout(timer);
      busy = false;
      sendBtn.disabled = false;
      input.focus();
    }
  }

  async function sendFeedback(button) {
    const msg = button.closest(".msg");
    if (!msg || msg.dataset.rated) return;
    const rating = button.dataset.rating;
    msg.querySelectorAll(".fb-btn").forEach((b) => (b.disabled = true));
    button.classList.add("active");
    try {
      const res = await fetch(root.dataset.feedbackUrl, {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({ message_id: msg.dataset.messageId, rating: rating, feedback_text: rating === "up" ? "Helpful" : "Not helpful" }),
      });
      const meta = msg.querySelector(".msg-meta");
      const note = document.createElement("span");
      if (res.ok) {
        msg.dataset.rated = "1";
        note.className = "fb-thanks"; note.dataset.testid = "feedback-thanks";
        note.textContent = "Thanks for the feedback!";
      } else {
        note.className = "small text-danger";
        note.textContent = "Feedback could not be saved.";
        msg.querySelectorAll(".fb-btn").forEach((b) => (b.disabled = false));
      }
      meta.appendChild(note);
    } catch (e) {
      msg.querySelectorAll(".fb-btn").forEach((b) => (b.disabled = false));
    }
  }

  launcher.addEventListener("click", toggle);
  document.getElementById("chatClose").addEventListener("click", close);
  form.addEventListener("submit", (e) => { e.preventDefault(); send(input.value); });
  body.addEventListener("click", (e) => {
    const fb = e.target.closest(".fb-btn");
    if (fb) { sendFeedback(fb); return; }
    const sug = e.target.closest(".chat-suggestions button");
    if (sug) send(sug.textContent);
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && win.classList.contains("open")) close(); });
  document.addEventListener("click", (e) => {
    const trigger = e.target.closest("[data-open-assistant]");
    if (trigger) {
      e.preventDefault();
      open();
      const q = trigger.getAttribute("data-question");
      if (q) send(q);
    }
  });

  window.StockPilotAssistant = { open, close, send };
})();
