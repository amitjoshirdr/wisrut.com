"""Build the Wisrut static site.
Run py build.py or python3 build.py.
Reads notes.csv, content/, and legacy/; writes and rebuilds site/.
"""

import csv
import html
import json
import re
import shutil
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "site"
LEGACY = ROOT / "legacy"
SITE = "https://wisrut.com"
CONTACT = "amitjoshi.work@outlook.com"
ADSENSE = "ca-pub-8690358052933130"
POLICY_DATE = "24 November 2026"
RAZORPAY_ID = "pl_T1cW8snj5ecBYS"

NAV = [("Notes", "/notes/"), ("Current affairs", "/current-affairs/"), ("Search", "/search/"), ("Support", "/support/")]
FOOT = [("About", "/about/"), ("Contact", "/contact/"), ("Privacy", "/privacy/"), ("Terms", "/terms/"), ("For businesses", "/for-business/")]
REDIRECTS = [("/margo.html", "/current-affairs/"), ("/search.html", "/search/"), ("/privacy.html", "/privacy/"), ("/terms.html", "/terms/")]
ADS_SCRIPT = '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=' + ADSENSE + '" crossorigin="anonymous"></script>'


def slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", str(s).strip().lower())).strip("-")


def e(s):
    return html.escape(str(s), quote=True)


def crumbs(items):
    parts = []
    for label, url in items:
        text = e(label)
        parts.append('<a href="' + e(url) + '">' + text + '</a>' if url else text)
    return '<nav class="crumbs" aria-label="Breadcrumb">' + " &rsaquo; ".join(parts) + '</nav>'


def write(path, content):
    target = str(path)
    if target.endswith(".html") or target.endswith(".txt") or target.endswith(".xml") or target.endswith("_redirects"):
        dest = OUT / target.lstrip("/")
    else:
        dest = OUT / target.strip("/") / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")


def shell(title, desc, body, path, active="", wide=False, app=False, head_extra="", ads_script=False, index=True):
    nav_links = []
    for label, url in NAV:
        attrs = ' aria-current="page"' if url == active else ""
        nav_links.append('<a href="' + url + '"' + attrs + ">" + e(label) + "</a>")
    foot_links = []
    for label, url in FOOT:
        foot_links.append('<a href="' + url + '">' + e(label) + "</a>")
    classes = "app" if app else ""
    wide_class = " wide" if wide else ""
    robots = "" if index else '  <meta name="robots" content="noindex, nofollow">\n'
    ads = ADS_SCRIPT if ads_script else ""
    html_text = "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n" \
        "  <meta charset=\"UTF-8\">\n" \
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n' \
        '  <meta name="google-adsense-account" content="' + ADSENSE + '">\n' \
        "  <title>" + e(title) + "</title>\n" \
        '  <meta name="description" content="' + e(desc) + '\">\n' + robots \
        '  <link rel="canonical" href="' + SITE + path + '\">\n' \
        '  <link rel="stylesheet" href="/site.css">\n' + ads + "\n" + head_extra + "\n</head>\n" \
        '<body class="' + classes + '">\n' \
        '<header class="top"><a class="brand" href="/">Wisrut</a><nav aria-label="Primary">' + "".join(nav_links) + '</nav></header>\n' \
        '<main class="' + wide_class.strip() + '">' + body + '</main>\n' \
        '<footer class="site"><nav aria-label="Footer">' + "".join(foot_links) + '</nav></footer>\n</body>\n</html>\n'
    return html_text


def convert_app(name, title, desc, path, active, ads):
    source = (LEGACY / name).read_text(encoding="utf-8")
    style_match = re.search(r"(?is)<style[^>]*>(.*?)</style>", source)
    css = style_match.group(1) if style_match else ""
    css = re.sub(r"(?m)^\s*body\s*\{[^}]*\}", "", css, count=1)
    head_extra = "<style>\n" + css + "\n</style>"

    body_match = re.search(r"(?is)<body[^>]*>(.*)</body>", source)
    body = body_match.group(1) if body_match else ""
    first_h1 = re.search(r"(?is)<h1\b", body)
    if first_h1:
        body = body[first_h1.start():]

    body = re.sub(r'<[^>]*class="[^"]*ad-slot[^"]*"[^>]*>.*?</(?:div|section)>', "", body, flags=re.S)
    body = re.sub(r"(?is)<footer\b.*?</footer>", "", body)
    body = re.sub(r"(?m)^\s*-->\s*$", "", body)
    body = re.sub(r"(?is)<[^>]*>Advertisement\s*(?:<[^>]*>)*", "", body)
    body = re.sub(r"(?i)Advertisement", "", body)

    page = shell(title, desc, body, path, active=active, wide=True, app=True, head_extra=head_extra, ads_script=ads)
    write(path, page)


def convert_policy(name, path, title):
    source = (LEGACY / name).read_text(encoding="utf-8")
    match = re.search(r'(?is)<div\s+class="page">(.*)</div>\s*</body>', source)
    inner = match.group(1) if match else ""
    inner = re.sub(r"\[your(?:\-|‑|‑)?email@example\.com\]", '<a href="mailto:' + CONTACT + '">' + e(CONTACT) + '</a>', inner)
    inner = re.sub(r"Last updated:\s*[^<]+", "Last updated: " + POLICY_DATE, inner)
    inner = '<article class="doc">' + inner + '</article>'
    page = shell(title, "Wisrut policy information", inner, path, active="/support/")
    write(path, page)


def read_notes():
    notes = []
    with (ROOT / "notes.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle):
            row = {key: value.strip() for key, value in raw.items()}
            if not row.get("title"):
                continue
            if not row.get("link") and not row.get("body_file"):
                print("WARNING: note has neither link nor body_file: " + row["title"])
            row["path"] = "/notes/college/" + "/".join(slug(row[key]) for key in ("university", "course", "semester", "subject", "topic")) + "/"
            notes.append(row)
    return notes


def make_drive_preview(link):
    match = re.search(r"drive\.google\.com/file/d/([^/]+)", link or "")
    if not match:
        return "", ""
    file_id = match.group(1)
    if file_id == "YOUR_FILE_ID":
        return "", ""
    preview = '<iframe class="preview" src="https://drive.google.com/file/d/' + e(file_id) + '/preview" loading="lazy" title="Note preview"></iframe>'
    return preview, file_id


def doc(path, title, desc, inner, active=""):
    body = '<article class="doc"><h1>' + e(title) + '</h1>' + inner + '</article>'
    write(path, shell(title, desc, body, path, active=active))


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True, exist_ok=True)

    convert_app("margo.html", "Current affairs for exams · Margo on Wisrut", "Daily exam-focused current affairs", "/current-affairs/", "/current-affairs/", True)
    convert_app("search.html", "AI search · Margo on Wisrut", "Ask an exam question and get an AI answer", "/search/", "/search/", False)
    convert_policy("privacy.html", "/privacy/", "Privacy · Wisrut")
    convert_policy("terms.html", "/terms/", "Terms · Wisrut")

    notes = read_notes()
    tree = {}
    for row in notes:
        university = row["university"]
        course = row["course"]
        semester = row["semester"]
        subject = row["subject"]
        tree.setdefault(university, {}).setdefault(course, {}).setdefault(semester, {}).setdefault(subject, []).append(row)

    urls = []

    home_cards = '<div class="cards"><a class="card" href="/notes/"><strong>College notes</strong><span>Find your syllabus</span></a><a class="card" href="/current-affairs/"><strong>Current affairs</strong><span>Daily brief for exam preparation</span></a><a class="card" href="/search/"><strong>Search</strong><span>Ask a question, get an AI answer</span></a></div>'
    recent = sorted([n for n in notes if n.get("updated")], key=lambda n: n["updated"], reverse=True)[:6]
    recent_html = ""
    if recent:
        items = []
        for n in recent:
            items.append('<li><a href="' + e(n["path"]) + '"><span>' + e(n["title"]) + '</span><span class="small">Updated ' + e(n["updated"]) + '</span></a></li>')
        recent_html = '<h2>Recently updated notes</h2><ul class="list">' + "".join(items) + '</ul>'
    home_body = '<h1>Free notes and current affairs for students</h1><p class="lead">Notes that follow your syllabus, shared by teachers. Today’s news in one place.</p>' + home_cards + recent_html
    write("/", shell("Wisrut", "Free notes and current affairs for students", home_body, "/", active="/notes/"))

    subject_count = {}
    semester_urls = []
    for university, courses in tree.items():
        for course, semesters in courses.items():
            for semester, subjects in semesters.items():
                sem_path = "/notes/college/" + slug(university) + "/" + slug(course) + "/" + slug(semester) + "/"
                semester_urls.append((university, course, semester, sem_path))
                urls.append(sem_path)
                items = []
                subject_paths = []
                for subject, subject_notes in subjects.items():
                    subject_path = sem_path + slug(subject) + "/"
                    subject_paths.append(subject_path)
                    urls.append(subject_path)
                    count = len(subject_notes)
                    label = str(count) + (" note" if count == 1 else " notes")
                    items.append('<li><a href="' + subject_path + '"><span>' + e(subject) + '</span><span class="small">' + label + '</span></a></li>')
                    sem_crumb = crumbs([("Notes", "/notes/"), (university, None), (course, None), (semester, None)])
                    sem_body = sem_crumb + '<h1>' + e(university) + " · " + e(semester) + '</h1><p class="lead">' + e(university) + " · " + e(course) + '</p><ul class="list">' + "".join(items) + '</ul>'
                write(sem_path, shell(university + " · " + semester + " · Wisrut", "Notes for " + university + " " + course + " " + semester, sem_body, sem_path, active="/notes/"))

                for subject, subject_notes in subjects.items():
                    subject_path = sem_path + slug(subject) + "/"
                    subject_items = []
                    for n in subject_notes:
                        right = "Updated " + n["updated"] if n.get("updated") else ""
                        subject_items.append('<li><a href="' + e(n["path"]) + '"><span>' + e(n["title"]) + '</span><span class="small">' + e(right) + '</span></a></li>')
                    subject_crumb = crumbs([("Notes", "/notes/"), (university, None), (course, None), (semester, None), (subject, None)])
                    subject_body = subject_crumb + '<h1>' + e(subject) + '</h1><p class="lead">' + e(university) + " · " + e(course) + " · " + e(semester) + '</p><ul class="list">' + "".join(subject_items) + '</ul>'
                    write(subject_path, shell(subject + " · " + university + " · Wisrut", "Study notes for " + subject, subject_body, subject_path, active="/notes/"))

                    for index, n in enumerate(subject_notes):
                        urls.append(n["path"])
                        preview, file_id = make_drive_preview(n.get("link", ""))
                        note_crumb = crumbs([("Notes", "/notes/"), (university, None), (course, None), (semester, None), (subject, subject_path), (n["title"], None)])
                        meta = '<p class="meta">By ' + e(n.get("author", "")) + (" · Updated " + e(n["updated"]) if n.get("updated") else "") + '</p>'
                        parts = [note_crumb, '<h1>' + e(n["title"]) + '</h1>', meta]
                        if n.get("summary"):
                            parts.append('<section class="sum"><h2>In 3 lines</h2><p>' + e(n["summary"]) + '</p></section>')
                        if preview:
                            parts.append(preview)
                        if n.get("link"):
                            parts.append('<p><a class="btn" href="' + e(n["link"]) + '" target="_blank" rel="noopener">Open the full note</a></p><p class="small">This file opens on the teacher’s own storage. Wisrut does not host it.</p>')
                        if n.get("body_file"):
                            body_path = ROOT / "content" / n["body_file"]
                            if body_path.is_file():
                                parts.append('<div class="body">' + body_path.read_text(encoding="utf-8") + '</div>')
                            else:
                                print("WARNING: missing body file " + n["body_file"])
                        if n.get("syllabus_url"):
                            parts.append('<p><a href="' + e(n["syllabus_url"]) + '" target="_blank" rel="noopener">Official syllabus</a></p>')
                        report_subject = "Report: " + n["title"]
                        parts.append('<p><a href="mailto:' + CONTACT + '?subject=' + e(report_subject) + '">Report a problem with this note</a></p>')
                        pn = []
                        if index > 0:
                            pn.append('<a href="' + e(subject_notes[index - 1]["path"]) + '">← Previous</a>')
                        if index + 1 < len(subject_notes):
                            pn.append('<a href="' + e(subject_notes[index + 1]["path"]) + '">Next →</a>')
                        parts.append('<nav class="pn">' + "".join(pn) + '</nav>')
                        note_body = "".join(parts)
                        title = n["title"] + " · " + subject + " · Wisrut"
                        write(n["path"], shell(title, n.get("summary", n["title"]), note_body, n["path"], active="/notes/"))

    tree_json = {u: {c: {s: "/notes/college/" + slug(u) + "/" + slug(c) + "/" + slug(s) + "/" for s in cs} for c, cs in courses.items()} for u, courses in tree.items()}
    tree_text = json.dumps(tree_json, ensure_ascii=False).replace("</", "<\\/")
    semester_items = []
    for university, course, semester, url in semester_urls:
        semester_items.append('<li><a href="' + url + '"><span>' + e(university + " · " + course + " · " + semester) + '</span><span class="small">View subjects</span></a></li>')
    script = '''<script>
const notesTree = ''' + tree_text + ''';
const universitySelect = document.getElementById("university-select");
const courseSelect = document.getElementById("course-select");
const semesterSelect = document.getElementById("semester-select");
function fillSelect(select, values) {
  select.textContent = "";
  values.forEach(function(value) { const option = document.createElement("option"); option.textContent = value; option.value = value; select.appendChild(option); });
}
function updateCourses() {
  const courses = Object.keys(notesTree[universitySelect.value] || {});
  fillSelect(courseSelect, courses);
  updateSemesters();
}
function updateSemesters() {
  const courses = notesTree[universitySelect.value] || {};
  const semesters = Object.keys(courses[courseSelect.value] || {});
  fillSelect(semesterSelect, semesters);
}
universitySelect.addEventListener("change", updateCourses);
courseSelect.addEventListener("change", updateSemesters);
document.getElementById("notes-pick").addEventListener("submit", function(event) {
  event.preventEvent;
  event.preventDefault();
  const courses = notesTree[universitySelect.value] || {};
  const url = (courses[courseSelect.value] || {})[semesterSelect.value];
  if (url) window.location.href = url;
});
updateCourses();
</script>'''
    script = script.replace("{{", "{").replace("}}", "}")
    notes_body = '<h1>Find your notes</h1><p class="lead">Pick your university, course and semester.</p>' \
        '<form class="pick" id="notes-pick"><label>University<select id="university-select"></select></label><label>Course<select id="course-select"></select></label><label>Semester<select id="semester-select"></select></label><button class="btn" type="submit">Show subjects</button></form>' \
        '<h2>All semesters</h2><ul class="list">' + "".join(semester_items) + '</ul>' + script
    write("/notes/", shell("College notes · Wisrut", "Find college notes by university, course and semester", notes_body, "/notes/", active="/notes/"))

    doc("/about/", "About Wisrut", "About Wisrut and its study tools", '<p>Wisrut is a free study site for college students in India. It is run by Amit Joshi.</p><h2>How the notes are made</h2><ul><li>Notes are written or chosen by teachers in their own words.</li><li>Every note shows author and last updated date.</li><li>Each note links to the official syllabus where available.</li><li>Files stay on the teacher’s own storage and Wisrut does not host them.</li><li>AI-written text is labelled and can be wrong.</li></ul><h2>Margo</h2><p><a href="/current-affairs/">Current affairs</a> and <a href="/search/">search</a> are both Margo tools.</p><h2>Are you a teacher?</h2><p><a href="mailto:' + CONTACT + '?subject=Teacher note enquiry">Email</a> your name, institution and phone number to ' + e(CONTACT) + '.</p>', "/")
    doc("/contact/", "Contact", "Contact Wisrut", '<p>Email: <a href="mailto:' + CONTACT + '">' + e(CONTACT) + '</a></p><ul><li><a href="/report/">Report a problem with an item or page</a>.</li><li>Teachers who want to share notes can email us.</li><li><a href="/for-business/">For businesses</a> enquiries should use that page.</li></ul>', "/support/")
    doc("/report/", "Report a problem", "Report a problem on Wisrut", '<p>A reported item is hidden first and investigated afterwards.</p><p><a class="btn" href="mailto:' + CONTACT + '?subject=Report%20a%20problem%20on%20Wisrut">Email a report</a></p><p>Include the page address and a short description.</p>', "/support/")
    razorpay = '<form><script src="https://checkout.razorpay.com/v1/payment-button.js" data-payment_button_id="' + RAZORPAY_ID + '" async></script></form>'
    doc("/support/", "Support Wisrut", "Support Wisrut", '<p>Wisrut stays free for students. We use light ads to cover costs, and you can also support the project if you find it useful. There is no pressure.</p>' + razorpay + '<h2>Need help?</h2><p>Email <a href="mailto:' + CONTACT + '">' + e(CONTACT) + '</a> or <a href="/report/">report a problem</a>.</p>', "/support/")
    doc("/for-business/", "RupForm", "RupForm helps owner-run businesses", '<p class="lead">RupForm helps owner-run businesses in the Rudrapur–Pantnagar belt replace repetitive office work with systems that run on their own.</p><p><strong>One broken process fixed in 30 days, or you do not pay the monthly fee.</strong></p><h2>How it works</h2><ul><li>A free 30-minute visit with a one-page list of top three manual processes.</li><li>A fixed-scope 30-day pilot on one process using Tally, Excel and WhatsApp.</li><li>An optional monthly care plan if the pilot works.</li></ul><p><a href="mailto:' + CONTACT + '?subject=RupForm%20enquiry">Email a RupForm enquiry</a></p>', "/")
    write("/404.html", shell("Page not found", "Page not found", '<h1>Page not found</h1><p><a href="/">Return to the home page</a></p>', "/404.html", active="", index=False))

    (OUT / "site.css").write_bytes((ROOT / "assets" / "site.css").read_bytes())
    redirect_lines = [source + " " + target + " 301" for source, target in REDIRECTS]
    (OUT / "_redirects").write_text("\n".join(redirect_lines) + "\n", encoding="utf-8")
    (OUT / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: " + SITE + "/sitemap.xml\n", encoding="utf-8")

    fixed = ["/", "/notes/", "/current-affairs/", "/search/", "/support/", "/about/", "/contact/", "/report/", "/privacy/", "/terms/", "/for-business/"]
    sitemap_urls = fixed + urls
    seen = set()
    url_xml = []
    for url in sitemap_urls:
        if url not in seen:
            seen.add(url)
            url_xml.append("  <url><loc>" + e(SITE + url) + "</loc></url>")
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(url_xml) + "\n</urlset>\n"
    (OUT / "sitemap.xml").write_text(sitemap, encoding="utf-8")

    page_count = sum(1 for p in OUT.rglob("*.html") if p.is_file())
    print("Built " + str(len(notes)) + " notes and " + str(page_count) + " pages into site.")


if __name__ == "__main__":
    main()
