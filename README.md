# Wisrut site

This folder builds wisrut.com. You edit one spreadsheet (`notes.csv`), run one command, and the whole site is rebuilt into `site/`.

## What each folder is

| Name | What it is | Do you edit it? |
|---|---|---|
| `notes.csv` | One row per note. This is where you add notes. | Yes |
| `content/` | Optional small HTML files that show note text directly on a page. | Yes, when needed |
| `assets/site.css` | The one stylesheet for the whole site. | Rarely |
| `build.py` | The script that builds the site. | Rarely |
| `tools/check_links.py` | Finds dead links and leftover problems. | No |
| `legacy/` | The six original files. Kept as the source for Margo, Search, Privacy and Terms. | **Never** |
| `site/` | The finished website. Generated. Cloudflare serves this folder. | **Never** |

## One-time setup

1. Install Python 3.8 or newer from python.org. On Windows, tick "Add Python to PATH" and the `py` launcher.
2. Install Visual Studio Code and open this folder in it.
3. When VS Code offers the recommended extensions, accept them. You get Live Server, a CSV editor and CSV colouring.

## The everyday loop

1. Open `notes.csv` and add or change rows.
2. Press **Ctrl+Shift+B**. This builds the site and then checks the links.
3. Right-click `site/index.html` and choose **Open with Live Server** to preview. Check a note on a narrow window.
4. If the checker reports a problem, fix it and press Ctrl+Shift+B again. Warnings about `YOUR_FILE_ID` are normal while sample rows exist.
5. Commit and push.

You can also run the steps by hand: `py build.py` then `py tools/check_links.py` on Windows, or `python3 build.py` then `python3 tools/check_links.py` elsewhere.

Live Server does not read `_redirects`, so old addresses such as `/margo.html` only redirect on the real site. Test those on the Cloudflare preview address.

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

## Git commands for the restructure branch

```
git checkout -b restructure
git add .
git commit -m "Restructure site"
git push -u origin restructure
```

Pushing the branch gives Cloudflare Pages a private preview address. The live site is not touched until you merge.

Make a copy of the repo before you merge.

## Cloudflare Pages steps

1. Push the `restructure` branch and open the preview address that Cloudflare shows. Test it on your phone: Home, a note, Current affairs, Search, Support, and an old address such as `/margo.html`.
2. When it looks right, go to **Settings > Builds**. Set the build command to **none** and the build output directory to **site**. Change this only when you are ready to merge, because it changes what the live site serves.
3. Merge `restructure` into `main`. Cloudflare Pages deploys it.
4. **Rollback:** open **Deployments** in the Pages dashboard and promote the previous deployment. The old site returns in seconds.

## Rules

- Never edit anything in `site/`. It is wiped on every build.
- Never edit anything in `legacy/`.
- Never rename or remove a published address without adding a redirect for the old one (add it to `REDIRECTS` in `build.py`).
- Do not change Margo or Search logic in this pass. Frame and styling only.
- Notes must be in the teacher's own words or openly licensed. Link to files on the teacher's own storage. Do not re-host other people's PDFs or question papers.
