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

  var names = ["note", "search", "free", "parts"];
  function showTool(name) {
    $("dev-app").classList.toggle("parts-mode", name === "parts");
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
    $("dev-app").className = "has-result";
    if (window.innerWidth < 1000) $("dev-out").scrollIntoView();
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

  /* ---------- Build in parts ---------- */
  var SAVE = "wisrutdevbuild";
  var bp = { done: 0, lastStart: -1, lastText: "" };
  function bpSave() {
    try { localStorage.setItem(SAVE, JSON.stringify({ idea: $("p-idea").value, code: $("p-code").value, done: bp.done, lastStart: bp.lastStart, lastText: bp.lastText })); } catch (e) {}
  }
  function bpLoad() {
    try {
      var o = JSON.parse(localStorage.getItem(SAVE) || "null");
      if (!o) return;
      $("p-idea").value = o.idea || ""; $("p-code").value = o.code || "";
      bp.done = o.done || 0; bp.lastStart = typeof o.lastStart === "number" ? o.lastStart : -1; bp.lastText = o.lastText || "";
    } catch (e) {}
  }
  function planLines() {
    var out = [], re = /^\s*PART\s+(\d+)\s*[:.\-]\s*(.+)$/gim, m, seen = {};
    while ((m = re.exec($("p-idea").value)) !== null) {
      var n = parseInt(m[1], 10);
      if (!seen[n]) { seen[n] = true; out.push({ n: n, title: m[2].trim() }); }
    }
    out.sort(function (a, b) { return a.n - b.n; });
    return out;
  }
  function bpProgress() {
    var plan = planLines();
    var t = plan.length ? "Plan: " + plan.length + " part" + (plan.length === 1 ? "" : "s") + ". Built so far: " + bp.done + "." : "No plan yet. Press Make a plan, or just press Build next part for a single request.";
    if (plan.length && bp.done >= plan.length) t += " All parts are built. Check the preview.";
    $("p-progress").textContent = t;
    $("p-next").textContent = plan.length && bp.done < plan.length ? "Build part " + (bp.done + 1) + " of " + plan.length : (plan.length ? "Add another part" : "Build next part");
  }
  function bpSay(t, bad) { var m = $("p-status"); m.textContent = t; m.className = bad ? "dev-bad" : "meta"; }

  function checkBalance(code) {
    var tags = ["div", "section", "details", "table", "ul", "ol", "svg", "summary", "script", "style"], bad = [];
    tags.forEach(function (t) {
      var open = (code.match(new RegExp("<" + t + "(\\s|>)", "gi")) || []).length;
      var close = (code.match(new RegExp("</" + t + ">", "gi")) || []).length;
      if (open !== close) bad.push("<" + t + "> opened " + open + ", closed " + close);
    });
    return bad;
  }

  function codeSummary(code) {
    if (!code.trim()) return "(nothing yet)";
    var out = [];
    var st = code.match(/<style[^>]*>[\s\S]*?<\/style>/i);
    if (st) out.push("STYLES SO FAR:\n" + st[0].slice(0, 7000));
    var ids = [], re = /\sid="([^"]+)"/g, m;
    while ((m = re.exec(code)) !== null) ids.push(m[1]);
    if (ids.length) out.push("IDS ALREADY USED: " + ids.join(", "));
    var heads = [], re2 = /<h([1-3])[^>]*>([\s\S]*?)<\/h\1>/gi;
    while ((m = re2.exec(code)) !== null) heads.push("h" + m[1] + ": " + m[2].replace(/<[^>]+>/g, "").trim().slice(0, 80));
    if (heads.length) out.push("HEADINGS SO FAR:\n" + heads.join("\n"));
    out.push("LAST PART OF THE CODE (for continuity):\n" + code.slice(-2500));
    return out.join("\n\n");
  }

  function bpBusy(b) { setBusy(b); }

  function callWorker(mode, prompt, maxTokens, onOk) {
    bpBusy(true);
    post("dev", { password: PW, mode: mode, prompt: prompt, max_tokens: maxTokens }, 170000).then(function (x) {
      bpBusy(false);
      if (x.status === 401) { gate.store(null); ask("The password was not accepted. Enter it again."); return; }
      if (!x.ok) { bpSay((x.data && x.data.error) ? x.data.error + (x.data.details ? " (" + String(x.data.details).slice(0, 160) + ")" : "") : "Something went wrong (" + x.status + ").", true); return; }
      onOk(String(x.data.response || ""));
    }).catch(function () {
      bpBusy(false);
      bpSay("Could not reach the server, or it took too long. Your work is saved. Try the same step again.", true);
    });
  }

  function stripPlan(t) {
    var i = t.search(/^\s*PLAN \(you can edit[^\n]*$/m);
    if (i >= 0) t = t.slice(0, i);
    var k = t.search(/^\s*(TOTAL:|PART\s+\d+\s*[:.\-])/im);
    if (k >= 0) t = t.slice(0, k);
    return t.replace(/\s+$/, "");
  }

  $("p-plan").addEventListener("click", function () {
    var idea = val("p-idea");
    if (!idea) { bpSay("Write the idea first.", true); return; }
    bpSay("Making a plan...", false);
    var base = stripPlan(idea);
    callWorker("plan", "IDEA AND CONTEXT:\n" + base, 1200, function (text) {
      $("p-idea").value = base + "\n\nPLAN (you can edit these lines)\n" + text.trim() + "\n";
      bp.done = 0; bp.lastStart = -1; bp.lastText = "";
      bpSave(); bpProgress();
      bpSay("Plan ready. Check it, change it if you like, then press Build part 1.", false);
    });
  });

  $("p-next").addEventListener("click", function () {
    var idea = val("p-idea"), plan = planLines(), code = $("p-code").value;
    if (!idea) { bpSay("Write the idea first.", true); return; }
    var n = plan.length ? Math.min(bp.done, plan.length - 1) : bp.done;
    var title = plan.length && plan[n] ? plan[n].title : "Continue the file";
    var total = plan.length || 1;
    var position = !code.trim() ? (total === 1 ? "only" : "first") : (plan.length && bp.done >= plan.length - 1 && bp.done < plan.length ? "last" : "middle");
    if (!plan.length && code.trim()) position = "middle";
    if (plan.length && bp.done >= plan.length) position = "middle";
    var prompt = "IDEA AND CONTEXT (with the PLAN):\n" + idea +
      "\n\n---\nWRITE NOW: part " + (bp.done + 1) + " of " + total + ": " + title +
      "\nPOSITION: " + position +
      "\n\nCODE SO FAR (summary):\n" + codeSummary(code);
    bpSay("Building part " + (bp.done + 1) + "... a part can take up to a minute.", false);
    callWorker("part", prompt, 6000, function (text) {
      var cur = $("p-code").value;
      bp.lastStart = cur.length; bp.lastText = (cur && !/\n$/.test(cur) ? "\n" : "") + text.replace(/^\s+|\s+$/g, "") + "\n";
      $("p-code").value = cur + bp.lastText;
      bp.done += 1;
      bpSave(); bpProgress();
      var bad = checkBalance($("p-code").value);
      bpSay(bad.length && position === "last" ? "Part added, but check these tags: " + bad.join("; ") + ". Use Redo last part if it looks wrong." :
            bad.length ? "Part added. Open tags so far: " + bad.join("; ") + " (normal until the last part)." : "Part added. Use Preview to see the file so far.", false);
    });
  });

  $("p-redo").addEventListener("click", function () {
    var code = $("p-code").value;
    if (bp.lastStart < 0 || code.slice(bp.lastStart) !== bp.lastText) { bpSay("I can only remove the last part if you have not edited the code since. Remove it by hand.", true); return; }
    $("p-code").value = code.slice(0, bp.lastStart);
    bp.done = Math.max(0, bp.done - 1); bp.lastStart = -1; bp.lastText = "";
    bpSave(); bpProgress(); bpSay("Last part removed. Press the build button to try it again.", false);
  });

  function bpDoc() {
    var c = $("p-code").value;
    if (!/<\/html>/i.test(c)) c += "\n</body></html>";
    return c;
  }
  $("p-preview").addEventListener("click", function () {
    var f = $("p-frame"); f.hidden = false; f.srcdoc = bpDoc(); f.scrollIntoView({ block: "nearest" });
  });
  $("p-copy").addEventListener("click", function () {
    var t = $("p-code"); t.focus(); t.select(); var ok = false;
    try { ok = document.execCommand("copy"); } catch (e) {}
    bpSay(ok ? "Copied." : "Select the text and copy it by hand.", !ok);
  });
  $("p-download").addEventListener("click", function () {
    var blob = new Blob([bpDoc()], { type: "text/html;charset=utf-8" });
    var a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "wisrut-page.html";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
  });
  $("p-clear").addEventListener("click", function () {
    if (!window.confirm("Clear the idea, the plan and the code? This cannot be undone.")) return;
    $("p-idea").value = ""; $("p-code").value = ""; bp.done = 0; bp.lastStart = -1; bp.lastText = "";
    try { localStorage.removeItem(SAVE); } catch (e) {}
    $("p-frame").hidden = true; bpProgress(); bpSay("Cleared.", false);
  });
  var saveTimer = null;
  function later() { clearTimeout(saveTimer); saveTimer = setTimeout(function () { bpSave(); bpProgress(); }, 600); }
  $("p-idea").addEventListener("input", later);
  $("p-code").addEventListener("input", later);
  bpLoad(); bpProgress();

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
  $("dev-preview-btn").addEventListener("click", function () { preview().scrollIntoView({ block: "nearest" }); });
  $("dev-print").addEventListener("click", function () {
    var f = preview();
    f.onload = function () { try { f.contentWindow.focus(); f.contentWindow.print(); } catch (e) { say("Use Preview, then your browser's print option.", true); } };
  });
})();
