#!/usr/bin/env python3
"""Check the built docs/ folder for dead links and leftover problems.

Run:  py tools/check_links.py        (Windows)
      python3 tools/check_links.py   (macOS, Linux)

Exit code 0 when there are no problems, 1 otherwise.
Warnings (such as sample Drive links) do not fail the check.
"""

import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "docs")

SKIP_PREFIXES = ("http://", "https://", "//", "mailto:", "tel:", "data:", "#", "javascript:")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def load_redirect_sources():
    sources = set()
    p = os.path.join(SITE, "_redirects")
    if os.path.isfile(p):
        for line in read(p).splitlines():
            parts = line.split()
            if parts and not line.startswith("#"):
                sources.add(parts[0])
    return sources


def address_exists(href, redirects):
    path = href.split("#", 1)[0].split("?", 1)[0]
    if path in redirects:
        return True
    rel = path.lstrip("/")
    target = os.path.join(SITE, *[p for p in rel.split("/") if p])
    if path == "" or path.endswith("/"):
        return os.path.isfile(os.path.join(target, "index.html"))
    if os.path.isfile(target):
        return True
    return os.path.isfile(os.path.join(target, "index.html"))


def strip_for_links(text):
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"(<script\b[^>]*>).*?(</script>)", r"\1\2", text, flags=re.S | re.I)
    text = re.sub(r"<style\b.*?</style>", "", text, flags=re.S | re.I)
    return text


def visible_text(text):
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<script\b.*?</script>", "", text, flags=re.S | re.I)
    text = re.sub(r"<style\b.*?</style>", "", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(text)


def main():
    if not os.path.isdir(SITE):
        print("docs/ not found. Run the build first.")
        return 1

    redirects = load_redirect_sources()
    pages = []
    for folder, _dirs, files in os.walk(SITE):
        for name in files:
            if name.endswith(".html"):
                pages.append(os.path.join(folder, name))
    pages.sort()

    warnings = []
    problems = []

    for p in pages:
        rel = os.path.relpath(p, SITE).replace(os.sep, "/")
        raw = read(p)

        if "YOUR_FILE_ID" in raw:
            warnings.append("%s: still contains YOUR_FILE_ID (sample link)" % rel)

        for m in re.finditer(r"""(?:href|src)\s*=\s*["']([^"']*)["']""", strip_for_links(raw)):
            href = m.group(1).strip()
            if not href or href.lower().startswith(SKIP_PREFIXES):
                continue
            if not href.startswith("/"):
                problems.append("%s: internal link does not start with /: %s" % (rel, href))
            elif not address_exists(href, redirects):
                problems.append("%s: dead link: %s" % (rel, href))

        text = visible_text(raw)
        if "-->" in text:
            problems.append("%s: stray --> in visible text" % rel)
        if re.search(r"\bAdvertisement\b", text):
            problems.append("%s: the word Advertisement appears in visible text" % rel)
        if "example.com" in text:
            problems.append("%s: example.com appears in visible text" % rel)
        if 'name="google-adsense-account"' not in raw:
            problems.append("%s: missing google-adsense-account meta tag" % rel)
        is_redirect = 'http-equiv="refresh"' in raw  # small redirect pages
        if not is_redirect and '<header class="top">' not in raw:
            problems.append('%s: missing <header class="top">' % rel)
        if not is_redirect and '<footer class="site">' not in raw:
            problems.append('%s: missing <footer class="site">' % rel)

    print("Checked %d pages." % len(pages))
    for w in warnings:
        print("WARNING: " + w)
    for pr in problems:
        print("PROBLEM: " + pr)
    if problems:
        print("%d problem(s) found." % len(problems))
        return 1
    print("OK: no problems.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
