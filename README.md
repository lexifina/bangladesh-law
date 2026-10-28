# The laws of Bangladesh, as a git repository

The laws of Bangladesh in force that the official [Laws of Bangladesh](http://bdlaws.minlaw.gov.bd) site publishes in English: 590 laws (the Constitution, 347 Acts, 138 Ordinances, 67 President's Orders and 37 Regulations), each split into one file per section or Article (13,576 files), with one paragraph per line, so `git blame` and `git diff` work line by line. The site is run by the Legislative and Parliamentary Affairs Division of the Ministry of Law, Justice and Parliamentary Affairs.

**What this repository is not, yet: a history.** The site publishes only the current text of each law, with footnotes saying which law inserted, substituted or omitted which words. It keeps no earlier versions and gives no date for its texts. So each law is a single commit holding its whole text as retrieved on 2026-10-28, and there is no line-by-line history before that day (corpus.json `"history": "current-only"`). Later retrievals will be added as later commits, so the history grows forward from here. The footnotes are kept in the files, word for word, and parsed into [`data/amendments.csv`](data/amendments.csv).

**Only the laws with an English text, for now.** Of the 1,685 laws in the site's chronological index, 333 are marked repealed and 1,350 are in force. 590 of those have an English text and are here. The other 760 laws in force have a text only in Bengali (almost every law made since 1987 is in Bengali only). They are **not included yet**, and whether to add them has not been decided. They are listed in [`data/bengali-only.csv`](data/bengali-only.csv) with their links.

The record holds 590 laws in 591 commits.

## A lawyer's questions as git commands

| Question | Command |
| --- | --- |
| What does Article 27 of the Constitution say? | `python tools/in_force_on.py 2026-10-28 constitution article-27` |
| What does section 302 of the Penal Code say? | `python tools/in_force_on.py 2026-10-28 act/1860/45 section-302` |
| The whole of a law, in order | `python tools/in_force_on.py 2026-10-28 act/1872/1` |
| Which law changed a section, by its footnotes | `grep '^\[\^' act/1860/45/section-124A.md` |
| Everything an amending law touched, by the footnotes | `grep 'Ordinance No. XLI of 1985' data/amendments.csv` |
| What changed in a law since this build (after later builds) | `git log -p -- act/1860/45` |
| The list of laws, with their numbers and dates | [`laws.csv`](laws.csv) |

## The files

Each law is a folder `<kind>/<year>/<number>/`: `act/1860/45/` is Act No. XLV of 1860, the Penal Code. The kinds are `act`, `ordinance`, `president-order` and `regulation`. A law made by a provincial legislature before 1971 has the legislature in front: `bengal-act`, `bengal-regulation`, `east-bengal-act`, `east-bengal-regulation`, `east-pakistan-act`, `east-pakistan-ordinance` and `east-pakistan-regulation` (98 laws). That way Bengal Act III of 1913 and Act III of 1913 do not share a folder. Where two laws still share a number, year and kind, the second gets its site id: `act/1923/7-130`. The Constitution is `constitution/`. In each folder:

- `title.md`: the title, the law's number and date as the site prints them, and its long title and preamble;
- `section-12A.md` (`article-7A.md` in the Constitution): one file per section, starting with any Part or Chapter headings above it as `##` lines and any heading over a group of sections as `###`, then the section's name as a `#` line and its text, one paragraph per line. A row the site prints without a number of its own (an "Extent" line, a defined term with its own heading, an illustration) stays in the file of the section above it. A number printed twice gives `section-4~2.md`. A Part or Chapter the site shows only as omitted or repealed is `chapter-VII.md` or `part-III.md`;
- `index.txt`: the files in the order of the law.

A footnote mark is written `[^12]`, numbered as on the site. Each footnote is copied word for word at the end of the file that first cites it: `[^94]: The word "imprisonment" was substituted, for the word "transportation" by section 19 of the Penal Code (Amendment) Ordinance, 1985 (Ordinance No. XLI of 1985)`. Text is copied as the site gives it, with spaces collapsed. Nothing is reworded. Table cells are joined with ` | `, and pictures are marked `[image]`. Names of Bengali-language laws cited in English texts stay in Bengali, as on the site.

## The dates, and which one we use

The site gives no date for its texts. **Every commit is dated by the day the pages were retrieved, 2026-10-28**, at noon in Dhaka (UTC+6), and that date is in the `In-force:` and `Consolidated:` trailers (`Date-source: retrieved`). It says only that this was the published text on that day. It is not the date any amendment took effect. The date the site prints under each law's title (its date of assent or making) is the `Published:` trailer and the `date` column of laws.csv.

`tools/in_force_on.py` answers for 2026-10-28 and any later date. For an earlier date it says there is no version, because the source has none.

## What "author" means

Every law-text commit has the same author: `Laws of Bangladesh (Legislative and Parliamentary Affairs Division) <bdlaws@bdlaws-minlaw-gov-bd.invalid>`, with the trailer `Kind: consolidated`. The address cannot exist. The author is the publisher of the text, not a lawmaker. No line is credited to an amending law, because without the earlier text nobody can tell which words an amendment wrote. In the shared design for these repositories, a change is credited to an amending law only when the source shows the text before and after it.

The footnotes say which law did what. [`data/amendments.csv`](data/amendments.csv) has one row per footnote (6,234): the law and file it belongs to, the kind of change (substituted, omitted, inserted, added and so on), the amending law's number as printed (6,037 footnotes print one), the amending provision ("section 3 and 2nd Schedule"), and, where the amending law is itself on the site and could be matched by number, year and name (2,784 footnotes, 75 distinct laws), its title, date and link. The date is the one the site prints for the amending law. It is not a commencement date.

## What it does not show

- Any text before 2026-10-28. The site has none.
- The 760 laws in force whose text the site has only in Bengali ([`data/bengali-only.csv`](data/bengali-only.csv)). 1 English law here has a Bengali text too, linked in its `Bengali-version:` trailer, and 1 Bengali text is left out because its English version is here.
- The 333 laws the index marks repealed ([`data/repealed.csv`](data/repealed.csv)). One more, the Lunacy Act, 1912, marked repealed in the index, could not be read: the site answered with an error ([`data/issues.csv`](data/issues.csv)).
- Rules, regulations made under Acts, notifications and SROs. The site publishes the laws themselves.
- Pictures and the layout of tables.

Other things the build noticed are in [`data/issues.csv`](data/issues.csv) (3 rows).

This is a research aid. It is not legal advice, and it is not the authentic text of any law. For anything that matters, read the Bangladesh Gazette.

## How it is checked

`tools/build/` holds the build as it was run, and [`data/source-sha256.tsv`](data/source-sha256.tsv) has the sha256 of every retrieved page it read. The build is deterministic: from the same pages it gives the same commit hashes. See [`REPRODUCE.md`](REPRODUCE.md). Before publishing, the build was checked for these things:
- the letters and digits of every law, text and footnotes, equal those of its page on the site, read by a separate program (`check_repo.py`) that does not use the builder's parser;
- the text `tools/in_force_on.py` prints for sample sections is the stored text, and it refuses an earlier date;
- every commit's trailers parse, and there are no merges, no dates that go backwards and none after the build date;
- two builds from the same pages give the same HEAD.

## Licence

Source: the Laws of Bangladesh site (http://bdlaws.minlaw.gov.bd), Legislative and Parliamentary Affairs Division, Ministry of Law, Justice and Parliamentary Affairs, Government of Bangladesh. Its footer reads "Copyright © 2019, Legislative and Parliamentary Affairs Division" and states no licence. No provision of Bangladesh law was found that takes Acts out of copyright or allows them to be reproduced. The Copyright Act, 2023 counts the work of the law-making authority as a Government work, owned by the Government for 60 years. The details are in [`SOURCES.md`](SOURCES.md). **This repository is private, and stays private until that is settled.** Lexifina's own contributions (the tools, the arrangement and the commit messages) are CC0. See [`LICENSE`](LICENSE).
