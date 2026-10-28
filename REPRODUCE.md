# Reproducing this repository

Built on 2026-10-29 from the Laws of Bangladesh pages retrieved on 2026-10-28, by the scripts in `tools/build/` (copied there as run). The sha256 of every page the build read is in [`data/source-sha256.tsv`](data/source-sha256.tsv), so a copy of those pages can be checked byte for byte before rebuilding. How the pages were retrieved is not part of this record.

| Script | sha256 |
| --- | --- |
| parse.py | `ad7bc45436229a264b921e57641cc6fb791f4bb670ed9ec22ccd08460db5d107` |
| build.py | `05f984c892521b14ef5f45c1d58c3c698cac062bf3e92e98430663d6c01b2ba4` |
| docs.py | `da47a390b69d19c55d1e1c06b116dde98b4ae8394ce3e9555482ba45336a2025` |
| check_repo.py | `e871114ea7c1cff42de5e4f51ea4103c7b7e55c86c830520c36ec40fe83fc0fd` |

Tools: Python 3.12 (standard library only) and git 2.46. [`data/source-sha256.tsv`](data/source-sha256.tsv) lists every page the build read: the site's chronological index, both pages of every law (`act-<id>.html` and `act-details-<id>.html`), and the two error answers.

## Steps

With the retrieved pages in place where `CACHE` in parse.py and build.py points (each matching its sha256 in `data/source-sha256.tsv`, kept as served, UTF-16 or UTF-8), set `GITLAW_PUBLIC_REBUILD=1` (the publish check is Lexifina's own and is not part of this record):

```sh
# 1. Build. --today is the latest date allowed and is recorded as corpus.json "built"; every commit is dated by the
#    retrieval day. The target folder is deleted and made again.
python -X utf8 build.py ../../../bangladesh-law-build --today 2026-10-29 --workers 4
# 2. Check every law's letters and digits against its page, and the history and the on-date tool.
python -X utf8 check_repo.py ../../../bangladesh-law-build
# 3. Global preflight and the shared smoke tests.
python scripts/global-law/check_corpus.py ../bangladesh-law-build
python scripts/test_corpus.py ../bangladesh-law-build tools/in_force_on.py
python scripts/test_noon.py ../bangladesh-law-build
```

## What the build produced

- 1,685 laws in the index: 333 repealed (`data/repealed.csv`) and 1,350 in force. Of these, 590 with an English text are built (1 Constitution, 347 Acts, 138 Ordinances, 67 President's Orders, 37 Regulations; 98 of them made by the Bengal (29), East Bengal (22) or East Pakistan (47) legislatures), and 760 with a Bengali text only are listed, not built (`data/bengali-only.csv`). The list also has the 1 Bengali text left out for its English version.
- 13,576 section and Article files, plus title.md and index.txt per law.
- 591 commits on `main`: 590 consolidated (one per law) and one documentation commit, all dated 2026-10-28 at 12:00 +0600.
- 6,234 footnotes (`data/amendments.csv`): 6,037 print the amending law's number, and 2,784 are matched to an amending law on the site (75 distinct laws), 2,780 with its date.

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
python tools/in_force_on.py 2026-10-28 act/1860/45 section-302
```

Two builds from the same pages give the same `git rev-parse HEAD`.

Results of `check_repo.py` on the previous build from the same retrieved pages: 590 laws read back from git and compared with the raw pages, 8,517,914 letters and digits in the texts and 877,213 in the footnotes; 0 laws differ in their text and 0 in their footnotes. 591 commits: 0 without a parseable In-force, 0 backwards, 0 after the build day, 0 merges, 0 with a carriage return; the on-date tool right for 7 of 7 samples.

## What AI did and did not do

The scripts, documentation and checks were written by Claude Code running Claude Opus 5.5 (`claude-opus-5-5`), following Lexifina's shared rules for these repositories. No AI model wrote or changed any legal text, and no model runs during parsing, building or checking. The text is the publisher's, read from its pages and split by fixed rules. The English renderings of the Copyright Act, 2023 in SOURCES.md are working translations for that note only.
