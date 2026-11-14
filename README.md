# Bangladesh: law history in git


The law of Bangladesh in git: one file per section or Article, one paragraph per line, so `git blame` and `git diff` work line by line. The official site publishes only the current text of each law and keeps no earlier versions, so each law starts as one commit, its text as retrieved on 2026-10-28; later retrievals are added as later commits, and the history grows forward from that day.

Part of [lexifina/global-law](https://github.com/lexifina/global-law), one git history for every country's law: this is Bangladesh's national law, which global-law reads at `bangladesh/national/acts/`.

**What is in it now:** the Constitution and 589 laws in force that the official Laws of Bangladesh site publishes in English (347 Acts, 138 Ordinances, 67 President's Orders and 37 Regulations), in 13,576 section and Article files, with the site's 6,234 amendment footnotes kept word for word and listed in [`data/amendments.csv`](data/amendments.csv). [`laws.csv`](laws.csv) lists every law with its number, date and folder.

Each law is in `<kind>/<year>/<number>/`, one file per section (`act/1860/45/section-302.md` is section 302 of the Penal Code, Act No. XLV of 1860); the Constitution is `constitution/`, one file per Article. Laws of a provincial legislature before 1971 carry it in front of the kind (`bengal-act`, `east-pakistan-ordinance`).

The text is in English, as the site publishes it. Under Article 153 of the Constitution, the Bengali text prevails where the two differ.

## Questions as git commands

| Question | Command |
| --- | --- |
| Every change to Article 27 of the Constitution | `git log -p --word-diff -- constitution/article-27.md` |
| Which commit wrote each line of Article 27? | `git blame constitution/article-27.md` |
| Every version of the Constitution, with the day it was retrieved | `git log --format="%h %(trailers:key=In-force,valueonly,separator=) %an" -- constitution` |
| Article 27 as published on a date (2026-10-28 or later) | `python tools/in_force_on.py 2026-11-01 constitution article-27` |

**Outside git**, we also host this record publicly, for free:

- **[Ask Claude about Bangladeshi law](https://global-law.lexifina.com/v1/try_claude?country=bangladesh)**: opens Claude with a first question ready.
- **[Ask ChatGPT](https://global-law.lexifina.com/v1/try_chatgpt?country=bangladesh)**: the same question in ChatGPT.
- **[Call the API in your browser](https://global-law.lexifina.com/v1/search_law?query=bail&jurisdictions=bangladesh)**: a search of Bangladeshi law for "bail", returned as JSON. See the [documentation here](https://lexifina.com/api/global-law).

Both assistants read the record through the free Global law connector (MCP, `https://global-law.lexifina.com/mcp`); the first time, the chat gives you the link that adds it. Ask in English.

**Host it yourself easily.** All it takes is git and Python, and the tools run on your machine:

```sh
git clone --depth 1 https://github.com/lexifina/global-law && cd global-law
python3 tools/countries.py add bangladesh/national/acts
python3 tools/law.py show 2026-11-01 bangladesh/national/acts/constitution/article-27.md
```

Opened in Claude Code, Cursor, VS Code or Codex, the clone also starts a local MCP server with the same tools ([MCP.md](https://github.com/lexifina/global-law/blob/main/MCP.md)).

## Dates

Each law-text commit is dated at noon, Asia/Dhaka (UTC+6), and carries its day in its `In-force:` and `Consolidated:` trailers:

- every law's first commit is dated 2026-10-28, the day its page was retrieved (`Date-source: retrieved`): the site gives no date for its texts, so this is not the day any amendment took effect;
- the date the site prints under a law's title (its assent or making) is the `Published:` trailer and the `date` column of `laws.csv`;
- `tools/in_force_on.py` answers for 2026-10-28 and later; for an earlier date it says there is no version.

Every law-text commit is credited to the publisher, `Laws of Bangladesh (Legislative and Parliamentary Affairs Division)`, not to a law: without the earlier text nobody can tell which words an amendment wrote. The footnotes say which law inserted, substituted or omitted what; 2,784 of them are matched in `data/amendments.csv` to an amending law on the site.

## How it is checked

- `tools/build/check_repo.py`, which does not use the builder's parser, reads every law back from git and compares its letters and digits, text and footnotes, with its page on the site; in the run [`REPRODUCE.md`](REPRODUCE.md) records, none of the 590 laws differed.
- [`data/source-sha256.tsv`](data/source-sha256.tsv) has the sha256 of every page the build read, and the build is deterministic: two builds from the same pages give the same HEAD.
- History is append-only: no merge commits, no dates going backwards, and every commit's trailers parse; `tools/in_force_on.py` gives the stored text and refuses an earlier date.

## What it does not show

- **Any text before 2026-10-28.** The site keeps no earlier versions.
- **The 760 laws in force that the site has only in Bengali** (almost every law made since 1987), listed in [`data/bengali-only.csv`](data/bengali-only.csv); their texts are on the `bengali` branch, not on `main`.
- **The 333 laws** of the site's 1,685-law index **marked repealed** ([`data/repealed.csv`](data/repealed.csv)).
- **Rules, regulations made under Acts, notifications and SROs**: the site publishes the laws themselves.
- **Pictures and table layout**: pictures are marked `[image]` and table cells joined with ` | `.

## Sources

| Source | Kind | Past versions | Notes |
| --- | --- | --- | --- |
| [Laws of Bangladesh](http://bdlaws.minlaw.gov.bd) (Legislative and Parliamentary Affairs Division, Ministry of Law, Justice and Parliamentary Affairs) | Official laws site: the Constitution, Acts, Ordinances, President's Orders, Regulations | no, current text only | No date for its texts; footnotes name the law and provision behind each change |

## Licence

See [`LICENSE`](LICENSE). The texts are copied unchanged from the Laws of Bangladesh site, which states no licence for reuse; under the Copyright Act, 2023 the work of the law-making authority is a Government work, and no provision was found that allows reproducing it (see [`SOURCES.md`](SOURCES.md)). Lexifina's own contributions (the tools, the arrangement and the commit messages) are CC0 1.0.

No AI model wrote or changed legal text; the scripts, documentation and checks were written by an AI model (see [`REPRODUCE.md`](REPRODUCE.md)).

## More

From [lexifina/global-law](https://github.com/lexifina/global-law):

- [FEATURES.md](https://github.com/lexifina/global-law/blob/main/FEATURES.md): every feature, and what every corpus must support (`git blame`, `law.py`, the MCP tools)
- [FAQ.md](https://github.com/lexifina/global-law/blob/main/FAQ.md): questions and answers · [CONTRIBUTING.md](https://github.com/lexifina/global-law/blob/main/CONTRIBUTING.md): proposing changes · [MCP.md](https://github.com/lexifina/global-law/blob/main/MCP.md): the MCP server · [REPRODUCE.md](https://github.com/lexifina/global-law/blob/main/REPRODUCE.md): how it was built · [CHANGELOG.md](https://github.com/lexifina/global-law/blob/main/CHANGELOG.md)
- [FRESHNESS.md](https://github.com/lexifina/global-law/blob/main/FRESHNESS.md): how current each corpus is · [Monitoring](https://github.com/lexifina/global-law/tree/main/monitoring): whether updates are running · [WATCHING.md](https://github.com/lexifina/global-law/blob/main/WATCHING.md): how each official source is watched for changes
- [performance/](https://github.com/lexifina/global-law/tree/main/performance): how fast the tools are, measured
- [visualisations/](https://github.com/lexifina/global-law/tree/main/visualisations): charts and bridges across the world's law
- [Vulnerabilities](https://github.com/lexifina/global-law/tree/main/vulnerabilities): mistakes in legislation as published
