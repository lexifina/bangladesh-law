# Reproducing this repository

Built on {{TODAY}} from the Laws of Bangladesh pages retrieved on {{RETRIEVED}}, by the scripts in `tools/build/` (copied there as run). The sha256 of every page the build read is in [`data/source-sha256.tsv`](data/source-sha256.tsv), so a copy of those pages can be checked byte for byte before rebuilding. How the pages were retrieved is not part of this record.

| Script | sha256 |
| --- | --- |
| parse.py | `{{SHA_PARSE_PY}}` |
| build.py | `{{SHA_BUILD_PY}}` |
| docs.py | `{{SHA_DOCS_PY}}` |
| check_repo.py | `{{SHA_CHECK_REPO_PY}}` |

Tools: Python 3.12 (standard library only) and git 2.46. [`data/source-sha256.tsv`](data/source-sha256.tsv) lists every page the build read: the site's chronological index, both pages of every law (`act-<id>.html` and `act-details-<id>.html`), and the two error answers.

## Steps

With the retrieved pages in place where `CACHE` in parse.py and build.py points (each matching its sha256 in `data/source-sha256.tsv`, kept as served, UTF-16 or UTF-8), set `GITLAW_PUBLIC_REBUILD=1` (the publish check is Lexifina's own and is not part of this record):

```sh
# 1. Build. --today is the latest date allowed and is recorded as corpus.json "built"; every commit is dated by the
#    retrieval day. The target folder is deleted and made again.
python -X utf8 build.py ../../../bangladesh-law-build --today {{TODAY}} --workers 4
# 2. Check every law's letters and digits against its page, and the history and the on-date tool.
python -X utf8 check_repo.py ../../../bangladesh-law-build
# 3. Global preflight and the shared smoke tests.
python scripts/global-law/check_corpus.py ../bangladesh-law-build
python scripts/test_corpus.py ../bangladesh-law-build tools/in_force_on.py
python scripts/test_noon.py ../bangladesh-law-build
```

## What the build produced

- {{INDEX}} laws in the index: {{REPEALED}} repealed (`data/repealed.csv`) and {{IN_FORCE}} in force. Of these, {{LAWS}} with an English text are built (1 Constitution, {{ACTS}} Acts, {{ORDINANCES}} Ordinances, {{ORDERS}} President's Orders, {{REGULATIONS}} Regulations; {{PROVINCIAL}} of them made by the Bengal ({{BENGAL}}), East Bengal ({{EAST_BENGAL}}) or East Pakistan ({{EAST_PAKISTAN}}) legislatures), and {{BENGALI_ONLY}} with a Bengali text only are listed, not built (`data/bengali-only.csv`). The list also has the {{BENGALI_WITH_ENGLISH}} Bengali text left out for its English version.
- {{UNITS}} section and Article files, plus title.md and index.txt per law.
- {{COMMITS}} commits on `main`: {{LAWS}} consolidated (one per law) and one documentation commit, all dated {{RETRIEVED}} at 12:00 +0600.
- {{FOOTNOTES}} footnotes (`data/amendments.csv`): {{FOOTNOTES_WITH_LAW}} print the amending law's number, and {{FOOTNOTES_WITH_SITE}} are matched to an amending law on the site ({{AMENDING_LAWS}} distinct laws), {{FOOTNOTES_WITH_DATE}} with its date.

## Decisions made by hand

- Scope, for now: the laws in force that the site has in English. A law is English when its title has no Bengali letters and its text has more Latin than Bengali letters (the site gives a few Bengali laws English titles). Laws in force with a Bengali text only are listed in `data/bengali-only.csv` and not built. The user has not decided whether to add them. Where the site links a Bengali text of an English law, the English one is built and the Bengali one is linked.
- Left out: laws the index marks `[Repealed]`, or whose text page carries the site's repeal notice.
- One commit per law, `Kind: consolidated`, authored by the publisher, dated by the retrieval day: the site gives no date for its texts. `In-force:` and `Consolidated:` give that day. `Published:` is the date printed under the title.
- Commit times are noon in Dhaka, UTC+6. Bangladesh kept daylight saving time only from 2009-06-19 to 2009-12-31, and no commit falls in it.
- Section files are named from the table of contents (`2A. ...` gives `section-2A`, `171-I. ...` gives `section-171I`, Bengali letters map to A, B, ...). Where a contents line has no number, the text's own first line is tried. A row with no number anywhere is part of the unit above it and joins its file. A row that opens a Part or Chapter and says it was omitted or repealed gets a file named from that heading.
- Folders: `<kind>/<year>/<number>`, with the year from the index and the number from the number line. Provincial laws get the legislature in front of the kind, read from the title ("(East Bengal Act)") or the number line ("BENGAL REGULATION V OF 1799"). Two laws with the same key: the second (by site id) gets `-<site id>`, listed in `data/issues.csv`.
- Footnotes: each is copied word for word to the end of the file that first cites it, and any footnote no line cites goes to title.md, so none is lost. In `data/amendments.csv` the kind of change is the first of substituted, inserted, added, omitted, repealed, renumbered and amended that its wording names, otherwise "note". The amending law is the law number printed after the note's last "by" (or the last one printed), matched to the index by legislature, kind, number and year. An English title must also appear in the note. The amending provision is the "section ..." or "Article ..." after "by".
- The documentation commit is dated by the retrieval day, not the run day, so a rebuild on another day gives the same hashes.

## Checks

```sh
git rev-list --merges --count main      # 0
python -X utf8 check_repo.py ../bangladesh-law-build
python tools/in_force_on.py {{RETRIEVED}} act/1860/45 section-302
```

Two builds from the same pages give the same `git rev-parse HEAD`.

{{CHECK}}

## What AI did and did not do

The scripts, documentation and checks were written by Claude Code running Claude Opus 5.5 (`claude-opus-5-5`), following Lexifina's shared rules for these repositories. No AI model wrote or changed any legal text, and no model runs during parsing, building or checking. The text is the publisher's, read from its pages and split by fixed rules. The English renderings of the Copyright Act, 2023 in SOURCES.md are working translations for that note only.
