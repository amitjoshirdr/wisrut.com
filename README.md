# Wisrut site

This folder builds wisrut.com. You edit one spreadsheet (`notes.csv`), run one command, and the whole site is rebuilt into `docs/`. The site is hosted on GitHub Pages, which serves the `docs/` folder.

## What each folder is

| Name | What it is | Do you edit it? |
|---|---|---|
| `notes.csv` | One row per note. This is where you add notes. | Yes |
| `content/` | Optional small HTML files that show note text directly on a page. | Yes, when needed |
| `assets/site.css` | The one stylesheet for the whole site. | Rarely |
| `build.py` | The script that builds the site. | Rarely |
| `tools/check_links.py` | Finds dead links and leftover problems. | No |
| `legacy/` | The six original files. Kept as the source for Margo, Search, Privacy and Terms. | **Never** |
| `docs/` | The finished website. Generated. GitHub Pages serves this folder. | **Never** |

The folder must be called `docs`. GitHub Pages can only serve the repo root or a folder with that name.

## One-time setup

1. Install Python 3.8 or newer from python.org. On Windows, tick "Add Python to PATH" and the `py` launcher.
2. Install Visual Studio Code and open this folder in it.
3. When VS Code offers the recommended extensions, accept them. You get Live Server, a CSV editor and CSV colouring.

## The everyday loop

1. Open `notes.csv` and add or change rows.
2. Press **Ctrl+Shift+B**. This builds the site and then checks the links.
3. Right-click `docs/index.html` and choose **Open with Live Server** to preview. Check a note on a narrow window.
4. If the checker reports a problem, fix it and press Ctrl+Shift+B again. Warnings about `YOUR_FILE_ID` are normal while sample rows exist.
5. Commit and push. Commit the `docs/` folder too, because GitHub Pages serves it.

You can also run the steps by hand: `py build.py` then `py tools/check_links.py` on Windows, or `python3 build.py` then `python3 tools/check_links.py` elsewhere.

## notes.csv columns

| Column | What to enter |
|---|---|
| `university`, `course`, `semester`, `subject`, `topic` | Exact names. **Identical spelling groups notes together**, so write "Semester 3" the same way every time. |
| `title` | The note title. Rows without a title are skipped. |
| `author` | The teacher's name. Shows "Wisrut" if empty. |
| `updated` | Date as `YYYY-MM-DD`. |
| `summary` | Three lines in the teacher's own words. |
| `link` | Google Drive, Docs, PDF or YouTube link. Starts with `https://`. For Drive PDFs, set sharing to **Anyone with the link can view** so the preview shows on the page. |
| `syllabus_url` | Optional. Official syllabus link. |
| `body_file` | Optional. File name of a small HTML file in `content/` to show text directly on the page. |

Every row needs a `link` or a `body_file`, otherwise the build prints a warning.

If a cell contains a comma, put the whole cell in double quotes. A spreadsheet program does this for you when you save as CSV (UTF-8).

When your real notes are in, **delete the four sample rows** (the ones whose title ends in "(sample)").

## Going live on GitHub Pages

GitHub Pages has no private preview for a branch, so test locally with Live Server first.

1. Make a copy of the repo before you start.
2. Make sure the repo has no old `site/` folder. Delete it if it is there. The new build writes to `docs/`.
3. Commit and push the `docs/` folder to `main`.
4. On github.com open the repo, then **Settings > Pages**. Under **Build and deployment** set **Source** to **Deploy from a branch**, **Branch** to `main` and the folder to `/docs`. Click **Save**.
5. Under **Custom domain** the value should be `wisrut.com`. The `CNAME` file in `docs/` keeps it there. Tick **Enforce HTTPS** when GitHub allows it.
6. Wait a minute or two, then open `https://wisrut.com/`. Test Home, a note, Current affairs, Search, Support, and an old address such as `/margo.html`.

**Rollback:** on github.com open the commit history, find the commit before the restructure, and use **Revert** on it. GitHub Pages redeploys within a minute or two.

DNS stays as it is in Cloudflare: four `A` records to GitHub's addresses and a `www` CNAME to `amitjoshirdr.github.io`.

## Old addresses

GitHub Pages does not read `_redirects`. For each old address (`/margo.html`, `/search.html`, `/privacy.html`, `/terms.html`) the build writes a small page that sends visitors to the new address. The `REDIRECTS` list in `build.py` controls this.

## Rules

- Never edit anything in `docs/`. It is wiped on every build.
- Never edit anything in `legacy/`.
- Never rename or remove a published address without adding a redirect for the old one (add it to `REDIRECTS` in `build.py`).
- Do not change Margo or Search logic in this pass. Frame and styling only.
- Notes must be in the teacher's own words or openly licensed. Link to files on the teacher's own storage. Do not re-host other people's PDFs or question papers.
