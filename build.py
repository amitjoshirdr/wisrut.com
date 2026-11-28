#!/usr/bin/env python3
"""Build the Wisrut static site.

Run:  py build.py        (Windows)
      python3 build.py   (macOS, Linux)

Reads:  notes.csv, content/, legacy/, assets/site.css
Writes: docs/   (wiped and rebuilt on every run; never edit it by hand)
        GitHub Pages serves this folder, so the folder name must stay "docs".

Standard library only. Works on Python 3.8 or newer.
"""

import csv
import hashlib
import html
import json
import os
import re
import shutil
import sys
from urllib.parse import quote

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "docs")
LEGACY = os.path.join(ROOT, "legacy")
SITE = "https://wisrut.com"
CONTACT = "wisdomroots@outlook.com"
WORKER_URL = "https://margo-api.amitjoshirdr.workers.dev"  # same backend as Margo and Search; never change
TEACHER = "Mr Amit Joshi"
TEACHER_ROLE = "Assistant Professor"
ADSENSE = "ca-pub-8690358052933130"
POLICY_DATE = "24 November 2026"
RAZORPAY_ID = "pl_T1cW8snj5ecBYS"

NAV = [
    ("Notes", "/notes/"),
    ("Current affairs", "/current-affairs/"),
    ("Search", "/search/"),
    ("Support", "/support/"),
]
FOOT = [
    ("About", "/about/"),
    ("Contact", "/contact/"),
    ("Privacy", "/privacy/"),
    ("Terms", "/terms/"),
    ("For businesses", "/for-business/"),
    ("Developers", "/developers/"),
]
REDIRECTS = [
    ("/margo.html", "/current-affairs/"),
    ("/search.html", "/search/"),
    ("/privacy.html", "/privacy/"),
    ("/terms.html", "/terms/"),
]
ADS_SCRIPT = (
    '<script async src="https://pagead2.googlesyndication.com/pagead/js/'
    'adsbygoogle.js?client=%s" crossorigin="anonymous"></script>' % ADSENSE
)

MIDDOT = u"·"
RSQUO = u"’"

PAGE_COUNT = 0

# Opens the password dialog when the footer link "Developers" is clicked.
# The dialog code (/dev-gate.js) is loaded only at that moment, so ordinary
# visitors never download it. Without JavaScript the link opens /developers/.
OPEN_DEV_SCRIPT = (
    '<script>(function(){var a=document.querySelector(\'footer.site a[href="/developers/"]\');'
    'if(!a||location.pathname==="/developers/")return;'
    'a.addEventListener("click",function(e){e.preventDefault();'
    'if(window.wisrutGate){window.wisrutGate.open();return}'
    'var s=document.createElement("script");s.src="/dev-gate.js";'
    's.onload=function(){window.wisrutGate.open()};'
    's.onerror=function(){location.href="/developers/"};'
    'document.head.appendChild(s)})})();</script>\n'
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def slug(s):
    """Lowercase, runs of non-alphanumerics become one hyphen, strip hyphens."""
    t = re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")
    if not t:
        # Names with no Latin letters or digits (for example Hindi only).
        t = "item-" + hashlib.md5(str(s).encode("utf-8")).hexdigest()[:6]
    return t


def e(s):
    return html.escape(str(s), quote=True)


def crumbs(items):
    parts = []
    for label, url in items:
        if url:
            parts.append('<a href="%s">%s</a>' % (e(url), e(label)))
        else:
            parts.append(e(label))
    return '<p class="crumbs">' + " &rsaquo; ".join(parts) + "</p>"


def write(path, content):
    """Write a page or file under site/.

    Paths ending in .html, .txt, .xml, _redirects, CNAME or .nojekyll are
    written as given. Any other path such as /notes/ is written as
    <path>/index.html.
    """
    global PAGE_COUNT
    rel = path.strip("/")
    parts = [p for p in rel.split("/") if p]
    if path.endswith((".html", ".txt", ".xml", ".js", "_redirects", "CNAME", ".nojekyll")):
        target = os.path.join(OUT, *parts)
    else:
        target = os.path.join(OUT, *(parts + ["index.html"]))
    folder = os.path.dirname(target)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    with open(target, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    if target.endswith(".html"):
        PAGE_COUNT += 1


def shell(title, desc, body, path, active="", wide=False, app=False,
          head_extra="", ads_script=False, index=True):
    """Return a full page wrapped in the shared header and footer."""
    nav = ""
    for label, url in NAV:
        cur = ' aria-current="page"' if url == active else ""
        nav += '<a href="%s"%s>%s</a>' % (url, cur, e(label))
    foot = ""
    for label, url in FOOT:
        foot += '<a href="%s">%s</a>' % (url, e(label))

    head = "<!doctype html>\n"
    head += '<html lang="en">\n<head>\n'
    head += '<meta charset="utf-8">\n'
    head += '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
    head += "<title>%s</title>\n" % e(title)
    head += '<meta name="description" content="%s">\n' % e(desc)
    if not index:
        head += '<meta name="robots" content="noindex">\n'
    head += '<meta name="google-adsense-account" content="%s">\n' % ADSENSE
    head += '<link rel="canonical" href="%s">\n' % e(SITE + path)
    head += '<link rel="stylesheet" href="/site.css">\n'
    if ads_script:
        head += ADS_SCRIPT + "\n"
    if head_extra:
        head += head_extra + "\n"
    head += "</head>\n"

    body_class = ' class="app"' if app else ""
    main_class = ' class="wide"' if wide else ""
    out = head
    out += "<body%s>\n" % body_class
    out += '<header class="top">\n'
    out += '<a class="brand" href="/">Wisrut</a>\n'
    out += "<nav>%s</nav>\n" % nav
    out += "</header>\n"
    out += "<main%s>\n%s\n</main>\n" % (main_class, body)
    out += '<footer class="site">%s</footer>\n' % foot
    out += OPEN_DEV_SCRIPT
    out += "</body>\n</html>\n"
    return out


def doc(path, title, desc, inner, active=""):
    """Write a plain text page: <article class="doc"><h1>...</h1>...</article>."""
    body = '<article class="doc"><h1>%s</h1>%s</article>' % (e(title), inner)
    page_title = "%s %s Wisrut" % (title, MIDDOT)
    write(path, shell(page_title, desc, body, path, active=active))


def mailto(subject=None):
    if subject:
        return "mailto:%s?subject=%s" % (CONTACT, quote(subject))
    return "mailto:" + CONTACT


def contact_link(subject=None):
    return '<a href="%s">%s</a>' % (e(mailto(subject)), e(CONTACT))


def read_legacy(name):
    p = os.path.join(LEGACY, name)
    if not os.path.isfile(p):
        sys.exit("ERROR: missing legacy file: legacy/%s" % name)
    with open(p, encoding="utf-8") as f:
        return f.read()


SCRIPT_RE = re.compile(r"<script\b.*?</script>", re.S | re.I)


def protect_scripts(text):
    """Swap every <script> block for a token so no cleanup regex can touch it."""
    store = []

    def grab(m):
        store.append(m.group(0))
        return "@@SCRIPT%d@@" % (len(store) - 1)

    return SCRIPT_RE.sub(grab, text), store


def restore_scripts(text, store):
    for i, block in enumerate(store):
        text = text.replace("@@SCRIPT%d@@" % i, block)
    return text


# ---------------------------------------------------------------------------
# Moving Margo and Search into the shared layout
# ---------------------------------------------------------------------------
def convert_app(name, title, desc, path, active, ads):
    src = read_legacy(name)

    # 1. First <style> block, minus its first body { ... } rule.
    m = re.search(r"<style[^>]*>(.*?)</style>", src, re.S | re.I)
    css = m.group(1) if m else ""
    css = re.sub(r"(?m)^\s*body\s*\{[^}]*\}", "", css, count=1)
    head_extra = "<style>" + css + "</style>"

    # 2. Body content, then drop everything before the first <h1>.
    m = re.search(r"<body[^>]*>(.*)</body>", src, re.S | re.I)
    if not m:
        sys.exit("ERROR: no <body> found in legacy/%s" % name)
    inner, store = protect_scripts(m.group(1))
    cut = inner.lower().find("<h1")
    if cut < 0:
        sys.exit("ERROR: no <h1> found in legacy/%s" % name)
    inner = inner[cut:]

    # 3. Empty ad boxes.
    inner = re.sub(r'<div[^>]*class="[^"]*ad-slot[^"]*"[^>]*>.*?</div>', "",
                   inner, flags=re.S)
    # 4. Wrappers left empty.
    inner = re.sub(r'<div id="ads-sidebar">\s*</div>', "", inner)
    inner = re.sub(r'<div class="col" style="flex: 0 0 320px; min-width: 0;">\s*</div>',
                   "", inner)
    # 5. Old footer.
    inner = re.sub(r'<footer class="site-footer">.*?</footer>', "", inner,
                   flags=re.S)
    # 6. Stray --> lines.
    inner = re.sub(r"(?m)^\s*-->\s*$", "", inner)

    inner = restore_scripts(inner, store).strip()

    # 7. Write the page.
    write(path, shell(title, desc, inner, path, active=active, wide=True,
                      app=True, head_extra=head_extra, ads_script=ads))


def convert_policy(name, title, desc, path):
    src = read_legacy(name)
    m = re.search(r'<div class="page">(.*)</div>\s*</body>', src, re.S)
    if not m:
        sys.exit("ERROR: no <div class=\"page\"> found in legacy/%s" % name)
    inner = m.group(1)

    mail = '<a href="mailto:%s">%s</a>' % (CONTACT, CONTACT)
    inner, n_mail = re.subn(r"\[your.email@example\.com\]", lambda mm: mail, inner)
    inner, n_date = re.subn(r"Last updated:[^<]*",
                            lambda mm: "Last updated: " + POLICY_DATE,
                            inner, count=1)
    if n_mail != 1 or n_date != 1:
        print("WARNING: legacy/%s: email replaced %d time(s), date replaced %d time(s)"
              % (name, n_mail, n_date))

    body = '<article class="doc">' + inner.strip() + "</article>"
    write(path, shell(title, desc, body, path))


# ---------------------------------------------------------------------------
# Notes data
# ---------------------------------------------------------------------------
def clean_url(value, label, title):
    if value and not re.match(r"^https?://", value, re.I):
        print("WARNING: %s for %r is not an http(s) link and was ignored" % (label, title))
        return ""
    return value


def load_notes():
    notes = []
    csv_path = os.path.join(ROOT, "notes.csv")
    if not os.path.isfile(csv_path):
        sys.exit("ERROR: notes.csv not found")
    used = set()
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            r = {}
            for k, v in row.items():
                if k is None:
                    continue
                r[k.strip()] = (v or "").strip()
            if not r.get("title"):
                continue
            r["link"] = clean_url(r.get("link", ""), "link", r["title"])
            r["syllabus_url"] = clean_url(r.get("syllabus_url", ""), "syllabus_url", r["title"])
            if not r.get("link") and not r.get("body_file"):
                print("WARNING: note %r has neither link nor body_file" % r["title"])
            for key in ("university", "course", "semester", "subject", "topic"):
                if not r.get(key):
                    r[key] = "Other" if key != "topic" else r["title"]
            base = "/notes/college/" + "/".join(
                slug(r[k]) for k in ("university", "course", "semester", "subject", "topic")
            ) + "/"
            path = base
            n = 2
            while path in used:
                path = base[:-1] + "-%d/" % n
                n += 1
            if path != base:
                print("WARNING: note %r shares an address with another note; using %s" % (r["title"], path))
            used.add(path)
            r["path"] = path
            notes.append(r)
    return notes


def tree_child(parent, label):
    key = slug(label)
    kids = parent["kids"]
    if key not in kids:
        kids[key] = {"name": label, "slug": key, "kids": {}, "notes": []}
    elif kids[key]["name"] != label:
        print("WARNING: %r and %r are treated as the same name; check the spelling"
              % (kids[key]["name"], label))
    return kids[key]


def build_tree(notes):
    root = {"kids": {}}
    for n in notes:
        node = root
        for key in ("university", "course", "semester", "subject"):
            node = tree_child(node, n[key])
        node["notes"].append(n)
    return root


def count_label(n):
    return "%d note%s" % (n, "" if n == 1 else "s")


def updated_label(n):
    return ("Updated " + n["updated"]) if n.get("updated") else ""


# ---------------------------------------------------------------------------
# Notes pages
# ---------------------------------------------------------------------------
def drive_preview(link):
    m = re.search(r"drive\.google\.com/file/d/([A-Za-z0-9_-]+)", link or "")
    if not m or m.group(1) == "YOUR_FILE_ID":
        return ""
    return ('<iframe class="preview" loading="lazy" title="Note preview" '
            'src="https://drive.google.com/file/d/%s/preview"></iframe>' % e(m.group(1)))


def _split_blocks(css):
    """Split CSS text into (prelude, block) pairs at the top level."""
    out, i, n = [], 0, len(css)
    while i < n:
        k = css.find("{", i)
        if k < 0:
            break
        depth, j = 1, k + 1
        while j < n and depth:
            depth += {"{": 1, "}": -1}.get(css[j], 0)
            j += 1
        out.append((css[i:k].strip(), css[k + 1:j - 1]))
        i = j
    return out


def scope_css(css):
    """Limit a page's own CSS to the note body, so it cannot restyle the site.

    Rules for html, body and :root keep only custom properties (--name).
    Dark-mode rules, animations, transitions, @import and @font-face are dropped,
    because the site has one light theme and no web fonts.
    """
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"@(?:import|charset)[^;]*;", "", css)
    out = []
    for prelude, block in _split_blocks(css):
        if prelude.startswith("@"):
            if prelude.lower().startswith("@media") and "prefers-color-scheme" not in prelude \
                    and "print" not in prelude.lower():
                inner = scope_css(block)
                if inner:
                    out.append("%s{%s}" % (prelude, inner))
            continue
        decls = [d.strip() for d in block.split(";") if d.strip()]
        decls = [d for d in decls if not re.match(r"(animation|transition)", d, re.I)]
        sels = []
        for sel in prelude.split(","):
            sel = sel.strip()
            if not sel or sel == "*":
                continue
            if re.fullmatch(r"(?:html|body|:root)", sel, re.I):
                custom = [d for d in decls if d.startswith("--")]
                if custom:
                    out.append(".body{%s}" % ";".join(custom))
                continue
            m_body = re.match(r"^(?:html|body)(?=[.#:\[])", sel, re.I)
            if m_body:
                sels.append(".body" + sel[m_body.end():])
                continue
            sel = re.sub(r"^(?:html|body)\s+", "", sel, flags=re.I)
            sels.append(".body " + sel)
        if sels and decls:
            out.append("%s{%s}" % (",".join(sels), ";".join(decls)))
    return "\n".join(out)


def clean_body(raw, name):
    """Return the HTML to show inside <div class="body">.

    A plain fragment is used as it is. A complete HTML page is reduced to its
    <body>. Nothing in the body is removed: its scripts, its elements and its
    first <h1> stay (the <h1> becomes an <h2>, because the site page already has
    one h1, the note title). Only HTML comments are dropped. Its own CSS is kept,
    limited to the note body (see scope_css), so diagrams and boxes keep their
    colours without changing the rest of the site.
    """
    if not re.search(r"<(?:html|body)\b", raw, re.I):
        return raw
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
    styles = re.findall(r"<style\b[^>]*>(.*?)</style>", raw, re.S | re.I)
    m = re.search(r"<body[^>]*>(.*)</body>", raw, re.S | re.I)
    body = m.group(1) if m else raw
    body = re.sub(r"<style\b.*?</style>", "", body, flags=re.S | re.I)
    body = re.sub(r"<h1\b([^>]*)>(.*?)</h1>", r'<h2 class="guide-title"\1>\2</h2>', body, count=1, flags=re.S | re.I)
    for src in re.findall(r"<script\b[^>]*\bsrc\s*=\s*[\"']?(https?:[^\"' >]+)", body, re.I):
        print("WARNING: %s loads a script from %s. The site rules ask for no external JavaScript." % (name, src))
    mb = re.search(r"<body\b", raw, re.I)
    if mb:
        head_scripts = re.findall(r"<script\b.*?</script>", raw[:mb.start()], re.S | re.I)
        if head_scripts:
            body += "\n" + "\n".join(head_scripts)
    css = scope_css("\n".join(styles))
    if re.search(r"gradient|@keyframes", "\n".join(styles), re.I):
        print("WARNING: %s uses a gradient or animation in its CSS; the site rules ask for flat colours." % name)
    print("NOTE: %s is a full HTML page; using its body and its own CSS limited to the note "
          "(its scripts stay; comments are dropped; the first h1 becomes an h2)." % name)
    if css:
        body = "<style>\n%s\n</style>\n%s" % (css, body)
    return body.strip()


BIG_FILE_BYTES = 400 * 1024
_COPIED = set()


def content_path(body_file):
    """Return (absolute path, folder inside content/) for a body_file value.

    body_file may be a plain name (guide.html), a name without .html, or a
    path inside content/ (Marketing/Marketing.html). If the exact path is not
    found, the build looks for one file with that name anywhere under content/
    (capital letters ignored). Anything that leaves content/ is refused.
    """
    rel = body_file.strip().replace("\\", "/").lstrip("/")
    root = os.path.realpath(os.path.join(ROOT, "content"))

    def inside(p):
        return p == root or p.startswith(root + os.sep)

    candidates = [rel] if rel.lower().endswith((".html", ".htm")) else [rel + ".html", rel + ".htm", rel]
    for c in candidates:
        full = os.path.realpath(os.path.join(root, c))
        if inside(full) and os.path.isfile(full):
            return full, os.path.dirname(os.path.relpath(full, root).replace(os.sep, "/"))

    wanted = [os.path.basename(c).lower() for c in candidates]
    found = []
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.lower() in wanted:
                found.append(os.path.join(dirpath, f))
    if len(found) == 1:
        relfound = os.path.relpath(found[0], root).replace(os.sep, "/")
        print("NOTE: body_file %r was found as content/%s. Put that full path in notes.csv to be exact." % (body_file, relfound))
        return os.path.realpath(found[0]), os.path.dirname(relfound)
    if len(found) > 1:
        print("WARNING: body_file %r matches more than one file in content/. Write the full path, for example Marketing/Marketing.html." % body_file)
    return None, ""


REL_REF = re.compile(r"""\b(src|href)\s*=\s*(["'])([^"']*)\2""", re.I)
SKIP_REF = ("/", "#", "http://", "https://", "mailto:", "tel:", "data:", "javascript:")


def publish_assets(body, folder, note_title):
    """Copy files that a body refers to by a relative path (images and so on)
    to docs/files/<folder>/ and point the references there.

    A reference such as src="fig1.png" or src="images/fig1.png" is looked up
    next to the body file, inside content/. Missing files print a warning.
    """
    root = os.path.realpath(os.path.join(ROOT, "content"))
    base = os.path.realpath(os.path.join(root, folder))

    def fix(m):
        attr, quote, val = m.group(1), m.group(2), m.group(3).strip()
        if not val or val.lower().startswith(SKIP_REF):
            return m.group(0)
        name = re.split(r"[?#]", val)[0].replace("\\", "/")
        src = os.path.realpath(os.path.join(base, name))
        inside = src.startswith(root + os.sep)
        is_page = name.lower().endswith((".html", ".htm"))
        if not inside or not os.path.isfile(src) or is_page:
            if attr.lower() == "src":
                print("WARNING: %r refers to %r, which was not found next to its body file." % (note_title, val))
            return m.group(0)
        rel = os.path.relpath(src, root).replace(os.sep, "/")
        dest = os.path.join(OUT, "files", *rel.split("/"))
        if dest not in _COPIED:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(src, dest)
            _COPIED.add(dest)
            if os.path.getsize(src) > BIG_FILE_BYTES:
                print("WARNING: %s is %d KB. Large images are slow on mobile data; try under 400 KB."
                      % (rel, os.path.getsize(src) // 1024))
        return "%s=%s/files/%s%s" % (attr, quote, rel, quote)

    return REL_REF.sub(fix, body)


def note_page(n, sem_path, subj_path, siblings, idx, urls):
    uni, course, sem, subj = n["university"], n["course"], n["semester"], n["subject"]
    parts = [crumbs([
        ("Notes", "/notes/"), (uni, None), (course, None),
        (sem, sem_path), (subj, subj_path), (n["title"], None),
    ])]
    parts.append("<h1>%s</h1>" % e(n["title"]))

    author = n.get("author") or "Wisrut"
    if author.strip().lower() in ("amit joshi", "mr amit joshi"):
        author = "%s, %s" % (TEACHER, TEACHER_ROLE)
    meta = "By %s" % e(author)
    if n.get("updated"):
        meta += " %s Updated %s" % (MIDDOT, e(n["updated"]))
    parts.append('<p class="meta">%s</p>' % meta)

    if n.get("summary"):
        lines = [e(x.strip()) for x in n["summary"].splitlines() if x.strip()]
        parts.append('<div class="sum"><h2>In 3 lines</h2><p>%s</p></div>' % "<br>".join(lines))

    if n.get("link"):
        parts.append(drive_preview(n["link"]))
        parts.append('<p><a class="btn" href="%s" target="_blank" rel="noopener">Open the full note</a></p>'
                     % e(n["link"]))
        parts.append('<p class="small">This file opens on the teacher%ss own storage. Wisrut does not host it.</p>'
                     % RSQUO)

    if n.get("body_file"):
        bpath, folder = content_path(n["body_file"])
        if bpath and os.path.isfile(bpath):
            with open(bpath, encoding="utf-8-sig") as f:
                body_html = clean_body(f.read(), n["body_file"])
            body_html = publish_assets(body_html, folder, n["title"])
            parts.append('<div class="body">%s</div>' % body_html)
        else:
            print("WARNING: body_file %r for note %r was not found in content/"
                  % (n["body_file"], n["title"]))

    if n.get("syllabus_url"):
        parts.append('<p><a href="%s" target="_blank" rel="noopener">Official syllabus</a></p>'
                     % e(n["syllabus_url"]))

    parts.append('<p><a href="%s">Report a problem with this note</a></p>'
                 % e(mailto("Report: " + n["title"])))

    prev_html = "<span></span>"
    next_html = "<span></span>"
    if idx > 0:
        p = siblings[idx - 1]
        prev_html = '<a href="%s">&larr; Previous: %s</a>' % (e(p["path"]), e(p["title"]))
    if idx < len(siblings) - 1:
        nx = siblings[idx + 1]
        next_html = '<a href="%s">Next: %s &rarr;</a>' % (e(nx["path"]), e(nx["title"]))
    parts.append('<nav class="pn" aria-label="Previous and next notes">%s%s</nav>' % (prev_html, next_html))

    title = "%s %s %s %s %s" % (n["title"], MIDDOT, subj, MIDDOT, uni)
    desc = (n.get("summary") or ("%s notes for %s, %s." % (subj, course, sem)))
    desc = " ".join(desc.split())[:155]
    write(n["path"], shell(title, desc, "\n".join(x for x in parts if x), n["path"], active="/notes/"))
    urls.append(n["path"])


HUB_JS = """(function () {
  var tree = __TREE__;
  var u = document.getElementById('sel-u');
  var c = document.getElementById('sel-c');
  var s = document.getElementById('sel-s');
  var form = document.getElementById('pick');
  function keys(o) { return Object.keys(o || {}); }
  function fill(sel, list) {
    while (sel.firstChild) { sel.removeChild(sel.firstChild); }
    list.forEach(function (k) {
      var o = document.createElement('option');
      o.value = k;
      o.textContent = k;
      sel.appendChild(o);
    });
  }
  function onCourse() { fill(s, keys((tree[u.value] || {})[c.value])); }
  function onUni() { fill(c, keys(tree[u.value])); onCourse(); }
  fill(u, keys(tree));
  onUni();
  u.addEventListener('change', onUni);
  c.addEventListener('change', onCourse);
  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    var t = ((tree[u.value] || {})[c.value] || {})[s.value];
    if (t) { window.location.href = t; }
  });
  form.hidden = false;
})();"""


def build_notes(notes, tree, urls):
    base = "/notes/college/"
    js_tree = {}
    sem_rows = ""

    for u in tree["kids"].values():
        js_tree[u["name"]] = {}
        for c in u["kids"].values():
            js_tree[u["name"]][c["name"]] = {}
            for s in c["kids"].values():
                sem_path = "%s%s/%s/%s/" % (base, u["slug"], c["slug"], s["slug"])
                js_tree[u["name"]][c["name"]][s["name"]] = sem_path
                sem_rows += ('<li><a href="%s"><span>%s %s %s</span><span class="small">%s</span></a></li>'
                             % (e(sem_path), e(c["name"]), MIDDOT, e(s["name"]), e(u["name"])))

                # Semester page
                body = crumbs([("Notes", "/notes/"), (u["name"], None), (c["name"], None), (s["name"], None)])
                body += "<h1>%s %s %s</h1>" % (e(c["name"]), MIDDOT, e(s["name"]))
                body += '<p class="lead">%s</p>' % e(u["name"])
                rows = ""
                for sub in s["kids"].values():
                    sub_path = sem_path + sub["slug"] + "/"
                    rows += ('<li><a href="%s"><span>%s</span><span class="small">%s</span></a></li>'
                             % (e(sub_path), e(sub["name"]), count_label(len(sub["notes"]))))
                body += '<ul class="list">%s</ul>' % rows
                title = "%s %s %s %s %s" % (c["name"], MIDDOT, s["name"], MIDDOT, u["name"])
                desc = "Subjects and notes for %s, %s at %s." % (c["name"], s["name"], u["name"])
                write(sem_path, shell(title, desc, body, sem_path, active="/notes/"))
                urls.append(sem_path)

                for sub in s["kids"].values():
                    sub_path = sem_path + sub["slug"] + "/"
                    # Subject page
                    body = crumbs([("Notes", "/notes/"), (u["name"], None), (c["name"], None),
                                   (s["name"], sem_path), (sub["name"], None)])
                    body += "<h1>%s</h1>" % e(sub["name"])
                    body += '<p class="lead">%s %s %s %s %s</p>' % (
                        e(c["name"]), MIDDOT, e(s["name"]), MIDDOT, e(u["name"]))
                    rows = ""
                    for n in sub["notes"]:
                        rows += ('<li><a href="%s"><span>%s</span><span class="small">%s</span></a></li>'
                                 % (e(n["path"]), e(n["title"]), e(updated_label(n))))
                    body += '<ul class="list">%s</ul>' % rows
                    title = "%s %s %s %s %s" % (sub["name"], MIDDOT, c["name"], MIDDOT, s["name"])
                    desc = "Notes for %s, %s, %s." % (sub["name"], c["name"], s["name"])
                    write(sub_path, shell(title, desc, body, sub_path, active="/notes/"))
                    urls.append(sub_path)

                    # Note pages
                    for idx, n in enumerate(sub["notes"]):
                        note_page(n, sem_path, sub_path, sub["notes"], idx, urls)

    # Hub
    body = "<h1>Find your notes</h1>"
    body += '<p class="lead">Pick your university, course and semester.</p>'
    if notes:
        body += ('<form class="pick" id="pick" hidden>'
                 '<div><label for="sel-u">University</label><select id="sel-u"></select></div>'
                 '<div><label for="sel-c">Course</label><select id="sel-c"></select></div>'
                 '<div><label for="sel-s">Semester</label><select id="sel-s"></select></div>'
                 '<button class="btn" type="submit">Show subjects</button></form>')
        body += "<h2>All semesters</h2>"
        body += '<ul class="list">%s</ul>' % sem_rows
        tree_json = json.dumps(js_tree, ensure_ascii=True).replace("<", "\\u003c")
        body += "<script>\n%s\n</script>" % HUB_JS.replace("__TREE__", tree_json)
    else:
        body += "<p>No notes have been added yet.</p>"
    write("/notes/", shell("Find your notes %s Wisrut" % MIDDOT,
                           "Pick your university, course and semester to find free student notes.",
                           body, "/notes/", active="/notes/"))


# ---------------------------------------------------------------------------
# Home and info pages
# ---------------------------------------------------------------------------
def build_home(notes):
    body = "<h1>Free notes and current affairs for students</h1>"
    body += '<p class="lead">Teacher-written notes that follow your syllabus. Today%ss news in one place.</p>' % RSQUO
    body += '<div class="cards">'
    body += '<a class="card" href="/notes/"><strong>Student notes</strong><span>Find your syllabus</span></a>'
    body += '<a class="card" href="/current-affairs/"><strong>Current affairs</strong><span>Daily brief for exam preparation</span></a>'
    body += '<a class="card" href="/search/"><strong>Search</strong><span>Ask a question, get an AI answer</span></a>'
    body += "</div>"
    recent = sorted(notes, key=lambda n: n.get("updated", ""), reverse=True)[:6]
    if recent:
        body += "<h2>Recently updated notes</h2>"
        rows = ""
        for n in recent:
            rows += ('<li><a href="%s"><span>%s</span><span class="small">%s</span></a></li>'
                     % (e(n["path"]), e(n["title"]), e(updated_label(n))))
        body += '<ul class="list">%s</ul>' % rows
    write("/", shell("Wisrut %s Free notes and current affairs for students" % MIDDOT,
                     "Free teacher-written notes that follow your syllabus, and daily current affairs, for college students in India.",
                     body, "/"))


def build_developers():
    """The private Developers page, plus the dialog script it shares with the footer link.

    Files: assets/dev_page.html (markup), assets/dev.js (the tools), assets/dev_gate.js
    (the password dialog, also published as /dev-gate.js). Not in the menu, the sitemap
    or search results.
    """
    def read(name):
        with open(os.path.join(ROOT, "assets", name), encoding="utf-8") as f:
            return f.read().replace("__WORKER__", WORKER_URL)
    write("/dev-gate.js", read("dev_gate.js"))
    body = read("dev_page.html") + '<script src="/dev-gate.js"></script><script>' + read("dev.js") + "</script>"
    write("/developers/", shell("Developers %s Wisrut" % MIDDOT,
                                "Private tools for the site owner.", body, "/developers/",
                                index=False, wide=True))


def build_info():
    # About
    inner = "<p>Wisrut is a free study site for college students in India. </p>"
    inner += "<h2>How the notes are made</h2><ul>"
    for line in (
        "Notes are written or chosen by teachers, in their own words.",
        "Every note shows its author and the date it was last updated.",
        "Each note links to the official syllabus where one is available.",
        "Files stay on the teacher%ss own storage. Wisrut does not host them." % RSQUO,
        "AI-written text is labelled and can be wrong.",
    ):
        inner += "<li>%s</li>" % line
    inner += "</ul>"
    inner += ('<h2>Margo</h2><p>Margo is the set of AI tools on Wisrut: '
              '<a href="/current-affairs/">current affairs</a> and <a href="/search/">search</a>.</p>')
    inner += ('<h2>Are you a teacher?</h2><p>Email your name, institution and phone number to %s '
              'and we will talk about sharing your notes.</p>' % contact_link("Teacher enquiry"))
    doc("/about/", "About Wisrut", "Wisrut is a free study site for college students in India.", inner)

    # Contact
    inner = "<p>Email: %s</p><ul>" % contact_link()
    inner += '<li>To report a problem with a note or page, use the <a href="/report/">report page</a>.</li>'
    inner += "<li>Teachers who want to share notes can write to the same address.</li>"
    inner += '<li>Business owners can read about <a href="/for-business/">RupForm</a>.</li>'
    inner += "</ul>"
    doc("/contact/", "Contact", "How to contact Wisrut.", inner)

    # Report
    inner = ("<p>When you report a note or page, we hide it first and investigate afterwards.</p>"
             "<p>Please include the page address and a short description of the problem.</p>")
    inner += '<p><a class="btn" href="%s">Email a report</a></p>' % e(mailto("Report a problem on Wisrut"))
    doc("/report/", "Report a problem", "Report a problem with a note or page on Wisrut.", inner, active="/support/")

    # Support
    inner = ("<p>Wisrut stays free for students. We use light ads to cover costs, and you can also "
             "support the project if you find it useful. There is no pressure.</p>")
    inner += ('<form><script src="https://checkout.razorpay.com/v1/payment-button.js" '
              'data-payment_button_id="%s" async></script></form>' % RAZORPAY_ID)
    inner += '<h2>Need help?</h2><p>Email %s or <a href="/report/">report a problem</a>.</p>' % contact_link()
    doc("/support/", "Support Wisrut", "Support Wisrut, a free study site for students.", inner, active="/support/")

    # For business
    inner = ("<p class=\"lead\">RupForm helps owner-run businesses in the Rudrapur%sPantnagar belt "
             "replace repetitive office work with systems that run on their own.</p>" % u"–")
    inner += "<p><strong>One broken process fixed in 30 days, or you do not pay the monthly fee.</strong></p>"
    inner += "<h2>How it works</h2><ul>"
    inner += "<li>A free 30-minute visit, with a one-page list of your top three manual processes.</li>"
    inner += "<li>A fixed-scope 30-day pilot on one process, using Tally, Excel and WhatsApp.</li>"
    inner += "<li>An optional monthly care plan if the pilot works.</li>"
    inner += "</ul>"
    inner += ("<p>This page is for business owners. It is separate from the student site, "
              "and Wisrut does not sell anything to students.</p>")
    inner += "<p>Email: %s</p>" % contact_link("RupForm enquiry")
    doc("/for-business/", "RupForm for businesses",
        "RupForm helps owner-run businesses in the Rudrapur-Pantnagar belt replace repetitive office work.",
        inner)

    # 404
    body = '<article class="doc"><h1>Page not found</h1><p>This page does not exist. <a href="/">Go to the home page</a>.</p></article>'
    write("/404.html", shell("Page not found %s Wisrut" % MIDDOT, "Page not found.", body, "/404.html", index=False))


# ---------------------------------------------------------------------------
# Output files and main
# ---------------------------------------------------------------------------
def redirect_page(new):
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        "<title>Redirecting</title>\n"
        '<meta name="google-adsense-account" content="%s">\n'
        '<link rel="canonical" href="%s">\n'
        '<meta http-equiv="refresh" content="0; url=%s">\n'
        "</head>\n<body>\n"
        '<p>This page has moved to <a href="%s">%s</a>.</p>\n'
        "</body>\n</html>\n"
        % (ADSENSE, e(SITE + new), e(new), e(new), e(new))
    )


def write_support_files(urls):
    shutil.copyfile(os.path.join(ROOT, "assets", "site.css"), os.path.join(OUT, "site.css"))

    # GitHub Pages ignores _redirects, so each old address also gets a small
    # redirect page. The _redirects file is kept in case the site moves to
    # Cloudflare Pages or Netlify later.
    lines = ["%s %s 301" % (old, new) for old, new in REDIRECTS]
    write("/_redirects", "\n".join(lines) + "\n")
    for old, new in REDIRECTS:
        write(old, redirect_page(new))

    # Keeps wisrut.com attached to GitHub Pages and stops Jekyll processing.
    write("/CNAME", "wisrut.com\n")
    write("/.nojekyll", "")

    write("/robots.txt", "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE)

    fixed = ["/", "/notes/", "/current-affairs/", "/search/", "/support/", "/about/",
             "/contact/", "/report/", "/privacy/", "/terms/", "/for-business/"]
    seen = set()
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for p in fixed + urls:
        if p in seen:
            continue
        seen.add(p)
        xml += "  <url><loc>%s</loc></url>\n" % e(SITE + p)
    xml += "</urlset>\n"
    write("/sitemap.xml", xml)


_WARNINGS = []


def _print_counting(*args, **kw):
    text = " ".join(str(x) for x in args)
    if text.startswith("WARNING"):
        _WARNINGS.append(text)
    _real_print(*args, **kw)


_real_print = print
print = _print_counting


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)

    notes = load_notes()
    tree = build_tree(notes)
    urls = []

    build_home(notes)
    convert_app("margo.html", "Current affairs for exams %s Margo on Wisrut" % MIDDOT,
                "Daily exam-focused current affairs for competitive exams, in one quick scroll.",
                "/current-affairs/", "/current-affairs/", True)
    convert_app("search.html", "AI search %s Margo on Wisrut" % MIDDOT,
                "Ask a question and get an article-style AI answer.",
                "/search/", "/search/", False)
    convert_policy("privacy.html", "Privacy policy %s Wisrut" % MIDDOT,
                   "How Wisrut collects, uses and protects information.", "/privacy/")
    convert_policy("terms.html", "Terms of use %s Wisrut" % MIDDOT,
                   "The terms for using Wisrut and Margo.", "/terms/")
    build_notes(notes, tree, urls)
    build_info()
    build_developers()
    write_support_files(urls)

    print("Built %d notes and %d pages into docs." % (len(notes), PAGE_COUNT))
    if _WARNINGS:
        print("")
        print("ATTENTION: %d warning(s). Something may be missing from the site:" % len(_WARNINGS))
        for w in _WARNINGS:
            print("  - " + w)


if __name__ == "__main__":
    main()
