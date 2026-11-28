/* Developer password dialog. Loaded only when someone opens the Developers link.
   The Worker address is filled in by build.py. */
(function () {
  var BASE = "__WORKER__/api/";
  var KEY = "wisrutdevpassword";
  var overlay = null, input, msg, btn, current = {};

  function store(v) { try { if (v === null) sessionStorage.removeItem(KEY); else sessionStorage.setItem(KEY, v); } catch (e) {} }
  function saved() { try { return sessionStorage.getItem(KEY) || ""; } catch (e) { return ""; } }

  function verify(password) {
    var ctl = (typeof AbortController !== "undefined") ? new AbortController() : null;
    var timer = setTimeout(function () { if (ctl) ctl.abort(); }, 20000);
    return fetch(BASE + "dev-login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: password }), signal: ctl ? ctl.signal : undefined
    }).then(function (res) {
      clearTimeout(timer);
      return res.json().catch(function () { return {}; }).then(function (data) { return { status: res.status, ok: res.ok, data: data }; });
    }, function (err) { clearTimeout(timer); throw err; });
  }

  function say(text, bad) { msg.textContent = text; msg.className = bad ? "dev-bad" : "meta"; }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text) n.textContent = text;
    return n;
  }

  function build() {
    overlay = el("div", "dev-gate");
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-labelledby", "dev-gate-title");
    overlay.hidden = true;
    var card = el("div", "dev-gate-card");
    var h = el("h2", "", "Developer password"); h.id = "dev-gate-title";
    card.appendChild(h);
    card.appendChild(el("p", "meta", "Enter the password to open the Developers tools."));
    var form = document.createElement("form");
    var label = el("label", "", "Password"); label.setAttribute("for", "dev-password");
    input = el("input"); input.type = "password"; input.id = "dev-password"; input.autocomplete = "current-password";
    msg = el("p", "meta"); msg.setAttribute("role", "status");
    btn = el("button", "btn", "Unlock"); btn.type = "submit";
    var cancel = el("a", "dev-cancel", "Cancel"); cancel.href = "#";
    form.appendChild(label); form.appendChild(input); form.appendChild(msg); form.appendChild(btn); form.appendChild(cancel);
    card.appendChild(form); overlay.appendChild(card); document.body.appendChild(overlay);

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      if (!input.value) { say("Enter the password.", true); return; }
      var typed = input.value;
      btn.disabled = true; say("Checking...", false);
      verify(typed).then(function (x) {
        btn.disabled = false;
        if (x.ok) {
          store(typed); close();
          if (current.onSuccess) current.onSuccess(typed); else window.location.href = "/developers/";
          return;
        }
        if (x.status === 401) { store(null); say("Wrong password.", true); input.value = ""; input.focus(); return; }
        say((x.data && x.data.error) || "Something went wrong (" + x.status + ").", true);
      }).catch(function () {
        btn.disabled = false;
        say("Could not reach the server. Check your connection and try again.", true);
      });
    });
    cancel.addEventListener("click", function (ev) { ev.preventDefault(); cancelled(); });
    overlay.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") { cancelled(); return; }
      if (ev.key !== "Tab") return;
      var items = [input, btn, cancel], idx = items.indexOf(document.activeElement);
      if (btn.disabled) items = [input, cancel];
      if (ev.shiftKey && idx <= 0) { ev.preventDefault(); items[items.length - 1].focus(); }
      else if (!ev.shiftKey && idx === items.length - 1) { ev.preventDefault(); items[0].focus(); }
    });
  }

  function close() {
    if (overlay) overlay.hidden = true;
    document.body.classList.remove("dev-open");
  }
  function cancelled() { close(); if (current.onCancel) current.onCancel(); }

  function open(opts) {
    current = opts || {};
    if (!overlay) build();
    input.value = ""; btn.disabled = false;
    say(current.message || "", !!current.message);
    document.body.classList.add("dev-open");
    overlay.hidden = false;
    try { input.focus(); } catch (e) {}
  }

  window.wisrutGate = { open: open, close: close, verify: verify, store: store, saved: saved };
})();
