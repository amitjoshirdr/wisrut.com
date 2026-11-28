/* Developers page script. The Worker address is filled in by build.py. */
(function () {
  var PW = "";
  var lastText = "";
  var gate = window.wisrutGate;
  var $ = function (id) { return document.getElementById(id); };

  function post(path, obj, timeoutMs) {
    var ctl = (typeof AbortController !== "undefined") ? new AbortController() : null;
    var timer = setTimeout(function () { if (ctl) ctl.abort(); }, timeoutMs || 30000);
    return fetch("__WORKER__/api/" + path, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(obj), signal: ctl ? ctl.signal : undefined
    }).then(function (res) {
      clearTimeout(timer);
      return res.json().catch(function () { return {}; }).then(function (data) { return { status: res.status, ok: res.ok, data: data }; });
    }, function (err) { clearTimeout(timer); throw err; });
  }

  /* ---------- the password dialog ---------- */
  function home() { window.location.href = "/"; }
  function showApp(password) { PW = password; $("dev-app").hidden = false; }
  function ask(message) {
    PW = ""; $("dev-app").hidden = true;
    gate.open({ onSuccess: showApp, onCancel: home, message: message });
  }

  if (!gate) {
    $("dev-msg").textContent = "The password dialog did not load. Reload the page.";
  } else if (gate.saved()) {
    gate.verify(gate.saved()).then(function (x) {
      if (x.ok) showApp(gate.saved()); else { gate.store(null); ask(""); }
    }).catch(function () { ask("Could not reach the server. Enter the password to try again."); });
  } else {
    ask("");
  }

  /* ---------- the tools ---------- */
  function say(t, bad) { var m = $("dev-msg"); m.textContent = t; m.className = bad ? "dev-bad" : "meta"; }

  var names = ["note", "search", "free"];
  function showTool(name) {
    for (var i = 0; i < names.length; i++) {
      $("dev-panel-" + names[i]).hidden = names[i] !== name;
      $("dev-tab-" + names[i]).setAttribute("aria-pressed", names[i] === name ? "true" : "false");
    }
  }
  names.forEach(function (n) { $("dev-tab-" + n).addEventListener("click", function () { showTool(n); }); });
  showTool("note");

  function val(id) { return ($(id).value || "").trim(); }

  function buildNotePrompt() {
    var parts = [];
    function add(label, id) { var v = val(id); if (v) parts.push(label + ": " + v); }
    add("University", "n-univ"); add("Course", "n-course"); add("Semester", "n-sem");
    add("Subject", "n-subject"); add("Unit or topic", "n-unit"); add("Language", "n-lang");
    add("Exam pattern", "n-pattern");
    var syl = val("n-syllabus");
    if (!syl) return "";
    parts.push("SYLLABUS TEXT:\n" + syl);
    var pyq = val("n-pyq"); if (pyq) parts.push("PREVIOUS-YEAR QUESTIONS:\n" + pyq);
    var res = val("n-resources"); if (res) parts.push("BOOKS AND OTHER MATERIAL:\n" + res);
    var extra = val("n-extra"); if (extra) parts.push("EXTRA INSTRUCTIONS:\n" + extra);
    return parts.join("\n");
  }

  function looksLikeHtml(t) { return /^\s*(<!doctype|<html|<body|<div|<section|<article|<h1)/i.test(t); }

  function setBusy(b) {
    var btns = document.querySelectorAll(".dev-run");
    for (var i = 0; i < btns.length; i++) btns[i].disabled = b;
  }

  function showResult(text, sources, grounded) {
    lastText = text;
    $("dev-out").hidden = false;
    $("dev-text").value = text;
    $("dev-preview").hidden = true;
    var box = $("dev-sources");
    while (box.firstChild) box.removeChild(box.firstChild);
    if (sources && sources.length) {
      var h = document.createElement("p"); h.className = "meta";
      h.textContent = grounded ? "Sources used:" : "Sources:";
      box.appendChild(h);
      var ul = document.createElement("ul");
      sources.forEach(function (s) {
        if (!s || !/^https?:/i.test(s.uri || "")) return;
        var li = document.createElement("li"), a = document.createElement("a");
        a.href = s.uri; a.rel = "noopener noreferrer"; a.target = "_blank";
        a.textContent = s.title || s.uri; li.appendChild(a); ul.appendChild(li);
      });
      box.appendChild(ul);
    }
    $("dev-status").textContent = text.length + " characters." + (looksLikeHtml(text) ? " This looks like a web page: use Preview to see it." : "");
    $("dev-out").scrollIntoView();
  }

  function run(mode, prompt, maxTokens) {
    if (!prompt) { say(mode === "note" ? "Paste the syllabus text first. The guide must follow your syllabus." : "Write your request first.", true); return; }
    say("Working. A long guide can take a minute or two.", false);
    setBusy(true);
    post("dev", { password: PW, mode: mode, prompt: prompt, max_tokens: maxTokens }, 170000).then(function (x) {
      setBusy(false);
      if (x.status === 401) { say("", false); gate.store(null); ask("The password was not accepted. Enter it again."); return; }
      if (!x.ok) { say((x.data && x.data.error) ? x.data.error + (x.data.details ? " (" + String(x.data.details).slice(0, 160) + ")" : "") : "Something went wrong (" + x.status + ").", true); return; }
      say("Done.", false);
      showResult(String(x.data.response || ""), x.data.sources || [], !!x.data.grounded);
    }).catch(function () {
      setBusy(false);
      say("Could not reach the server, or it took too long. Try again, or ask for a smaller piece (one unit at a time).", true);
    });
  }

  $("dev-run-note").addEventListener("click", function () { run("note", buildNotePrompt(), 8000); });
  $("dev-run-search").addEventListener("click", function () { run("search", val("s-query"), 3000); });
  $("dev-run-free").addEventListener("click", function () {
    var kind = $("f-kind").value, req = val("f-request");
    run("free", req ? "Output type: " + kind + "\n" + req : "", 8000);
  });

  $("dev-copy").addEventListener("click", function () {
    var t = $("dev-text"); t.focus(); t.select();
    var done = false;
    try { done = document.execCommand("copy"); } catch (e) {}
    if (navigator.clipboard && !done) { navigator.clipboard.writeText(lastText).then(function () { say("Copied.", false); }); return; }
    say(done ? "Copied." : "Select the text and copy it by hand.", !done);
  });

  $("dev-download").addEventListener("click", function () {
    var isHtml = looksLikeHtml(lastText);
    var blob = new Blob([lastText], { type: isHtml ? "text/html;charset=utf-8" : "text/plain;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = isHtml ? "wisrut-note.html" : "wisrut-result.txt";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
  });

  function docFor(text) {
    if (looksLikeHtml(text)) return text;
    var d = document.createElement("div"); d.textContent = text;
    return '<!doctype html><meta charset="utf-8"><body style="font:15px system-ui,sans-serif;white-space:pre-wrap;padding:12px">' + d.innerHTML + "</body>";
  }
  function preview() { var f = $("dev-preview"); f.hidden = false; f.srcdoc = docFor(lastText); return f; }
  $("dev-preview-btn").addEventListener("click", function () { preview().scrollIntoView(); });
  $("dev-print").addEventListener("click", function () {
    var f = preview();
    f.onload = function () { try { f.contentWindow.focus(); f.contentWindow.print(); } catch (e) { say("Use Preview, then your browser's print option.", true); } };
  });
})();
