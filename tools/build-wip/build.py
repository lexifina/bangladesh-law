"""Build the Bangladesh law repository from the bdlaws.minlaw.gov.bd cache (fetch.py).

    python scripts/bangladesh-law/build.py ../bangladesh-law --today YYYY-MM-DD [--limit N] [--no-git]

The Laws of Bangladesh site publishes only the current text of each law, with footnotes saying which act inserted,
substituted or omitted which words. It keeps no earlier versions and gives no in-force dates. So this is a
current-only record:

1. Every law in force in the site's chronological index is one law here: the Constitution, Acts, Ordinances,
   President's Orders and Regulations. Laws the index marks [Repealed] are left out and listed in data/repealed.csv.
   Where the site has both an English and a Bengali text of one law, the English one is used and the Bengali one is
   linked (Bengali-version trailer); otherwise the law is in the one language the site has.
2. Each section (article, for the Constitution) is one file, one paragraph per line, its name as a `#` heading and
   any Part or Chapter headings above it as `##` lines. A footnote mark in the text is written [^n], and the
   footnote itself, word for word, at the end of the file that first cites it. title.md holds the title, number,
   date and preamble.
3. Each law is one commit, `Kind: consolidated`, by the publisher, dated noon Asia/Dhaka (UTC+6) on the day the text
   was retrieved, with `In-force:` that day. Footnotes are parsed into data/amendments.csv (unit, kind, amending act,
   its date where the site links to it). Nothing is credited to an amending act.
"""
import argparse
import csv
import io
import json
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import parse as P

HERE = Path(__file__).parent
CACHE = HERE / '.cache'
COMMITTER = 'Lexifina <bangladesh-law@lexifina.com>'
PUBLISHER = ('Laws of Bangladesh (Legislative and Parliamentary Affairs Division)', 'bdlaws@bdlaws-minlaw-gov-bd.invalid')
SITE = 'http://bdlaws.minlaw.gov.bd'
KIND_ORDER = {'constitution': 0, 'regulation': 1, 'act': 2, 'ordinance': 3, 'president-order': 4}
KIND_LABEL = {'constitution': 'Constitution', 'act': 'Act', 'ordinance': 'Ordinance', 'president-order': "President's Order",
              'regulation': 'Regulation'}

AM_KINDS = [
    ('substituted', r'(?i)substitut|\u09aa\u09cd\u09b0\u09a4\u09bf\u09b8\u09cd\u09a5\u09be\u09aa\u09bf\u09a4'),
    ('inserted', r'(?i)insert|\u09b8\u09a8\u09cd\u09a8\u09bf\u09ac\u09c7\u09b6\u09bf\u09a4'),
    ('added', r'(?i)\badded\b|\u09b8\u0982\u09af\u09cb\u099c\u09bf\u09a4|\u09af\u09c1\u0995\u09cd\u09a4'),
    ('omitted', r'(?i)omitt|\u09ac\u09bf\u09b2\u09c1\u09aa\u09cd\u09a4'),
    ('repealed', r'(?i)repeal|\u09b0\u09b9\u09bf\u09a4'),
    ('renumbered', r'(?i)re-?numbered|\u09aa\u09c1\u09a8\u0983\u09b8\u0982\u0996\u09cd\u09af\u09be\u09df\u09bf\u09a4'),
    ('amended', r'(?i)amend|\u09b8\u0982\u09b6\u09cb\u09a7\u09bf\u09a4'),
]
EN_ACT_NO = re.compile(r'\((?:(?:E\.\s*B\.|E\.\s*P\.|Bengal|East Pakistan|East Bengal)\s+)?(Act|Ordinance|Order|P\.\s*O\.|President\'s Order|Regulation)\s*(?:No\.?\s*)?([0-9IVXLC]+)\s+of\s+(\d{4})\)', re.I)
BN_ACT_NO = re.compile('([\u09e6-\u09ef]{4})\\s*\u09b8\u09a8\u09c7\u09b0\\s*([\u09e6-\u09ef]+)\\s*\u09a8\u0982\\s*(\\S+?)[)\\s,]')


def law_meta(row: dict) -> dict:
    """Everything about one law from its two pages (run in worker processes)."""
    sid = row['id']
    a = P.act_page(sid)
    d = P.details(sid)
    out = dict(row)
    out['act'] = a
    out['det'] = d
    if a is None or d is None:
        return out
    title = P.norm(re.sub(r'\[\^\d+\]', '', ' '.join(d['title_lines'])))
    out['title'] = title
    out['language'] = 'bn' if P.BENGALI.search(title) else 'en'
    if not P.kind_of(d['kind_line'], title)[0] and ('constitution' in title.lower() or '\u09b8\u0982\u09ac\u09bf\u09a7\u09be\u09a8' in title):
        kind, no = 'constitution', ''
    else:
        kind, no = P.kind_of(d['kind_line'], title)
    out['kind'] = kind
    out['number'] = P.number(no) if no else None
    out['number_text'] = no
    out['year'] = P.number(row['index_year'])
    out['published'] = P.parse_day(d['date_line'])
    return out


def unit_files(law: dict) -> tuple[dict, list, list]:
    """path -> text for one law, the amendment rows, and issues."""
    d, a = law['det'], law['act']
    base = law['dir']
    files: dict[str, str] = {}
    order: list[str] = []
    issues: list[str] = []
    notes = {n['n']: n for n in d['notes']}
    placed: set[str] = set()

    def with_notes(body: list[str]) -> list[str]:
        refs = []
        for l in body:
            for n in re.findall(r'\[\^(\d+)\]', l):
                if n not in placed and n not in refs:
                    refs.append(n)
        tail = []
        for n in refs:
            if n in notes:
                placed.add(n)
                tail.append(f"[^{n}]: {notes[n]['text']}")
        return body + ([''] + tail if tail else [])

    title_body = [f'# {l}' for l in d['title_lines'][:1]] + d['title_lines'][1:]
    if d['kind_line']:
        title_body.append(d['kind_line'])
    if d['date_line']:
        title_body.append(d['date_line'])
    title_body += d['preamble']
    title_lines = with_notes(title_body)
    toc = a['toc']
    rows = d['rows']
    named = len(toc) == len(rows)
    if not named:
        issues.append(f'table of contents lists {len(toc)} sections, the text has {len(rows)}; files named by position')
    used: dict[str, int] = {}
    unit_of_note: dict[str, str] = {}
    for i, r in enumerate(rows):
        name = P.unit_name(toc[i][1], law['kind'] == 'constitution') if named else None
        if not name:
            name = f'unit-{i + 1:03d}'
        if name in used:
            used[name] += 1
            name = f'{name}~{used[name]}'
        else:
            used[name] = 1
        body = [f'{h} {l}' for h, l in r['heads']] + [f'# {l}' for l in r['name']] + r['text']
        if not r['name'] and not r['text'] and not r['heads']:
            issues.append(f'{name}: empty row')
        before = set(placed)
        files[f'{base}/{name}.md'] = '\n'.join(with_notes(body)) + '\n'
        for n in placed - before:
            unit_of_note[n] = name
        order.append(f'{name}.md')
    # footnotes no line cites go to title.md, so none is lost
    rest = [n['n'] for n in d['notes'] if n['n'] not in placed]
    if rest:
        title_lines += ([''] if not any(l.startswith('[^') for l in title_lines) else []) + [
            f"[^{n}]: {notes[n]['text']}" for n in rest]
        for n in rest:
            placed.add(n)
            unit_of_note[n] = 'title'
    for n in d['notes']:
        unit_of_note.setdefault(n['n'], 'title')
    files[f'{base}/title.md'] = '\n'.join(title_lines) + '\n'
    files[f'{base}/index.txt'] = '\n'.join(['title.md'] + order) + '\n'
    amend = []
    for n in d['notes']:
        kind = next((k for k, rx in AM_KINDS if re.search(rx, n['text'])), 'note')
        amend.append({'unit': unit_of_note.get(n['n'], 'title'), 'footnote': n['n'], 'kind': kind,
                      'links': n['links'], 'text': n['text']})
    if len(notes) != d['n_li']:
        issues.append(f"{d['n_li']} footnotes listed, {len(notes)} distinct numbers")
    return files, amend, issues


def build_one(law: dict):
    return unit_files(law)


def git_date(day: str) -> str:
    """Noon in Dhaka (UTC+6 since 1951; no summer time except 2009, which does not touch these dates)."""
    y, m, dd = map(int, day.split('-'))
    ts = int(datetime(y, m, dd, 6, 0, tzinfo=timezone.utc).timestamp())
    return f'{ts} +0600'


def message(law: dict, day: str, n_units: int, n_notes: int) -> str:
    kl = KIND_LABEL[law['kind']]
    lang = 'Bengali' if law['language'] == 'bn' else 'English'
    num = f" ({law['det']['kind_line'].strip('() ').strip()})" if law['kind'] != 'constitution' and law['det']['kind_line'] else ''
    subject = f"{law['title']}{num}"
    body = [f"The current text of the {law['title']}, in {lang}, as the Laws of Bangladesh site",
            f"(bdlaws.minlaw.gov.bd, Legislative and Parliamentary Affairs Division) published it, retrieved on {day}.",
            '',
            'The site keeps only the current text of each law and gives no date for it, so this commit holds the',
            'whole law and is dated by the retrieval day; no line is credited to an amending act. The footnotes that',
            f"say which act changed which words are kept in the files ({n_notes} footnotes, {n_units} units) and listed in",
            'data/amendments.csv.']
    tr = ['Kind: consolidated', f'In-force: {day}', f'Consolidated: {day}', 'Date-source: retrieved',
          f"Law: {law['title']}", f"Law-kind: {law['kind']}"]
    if law['number'] is not None:
        tr.append(f"Law-number: {law['number']}")
    if law['year']:
        tr.append(f"Law-year: {law['year']}")
    if law['published']:
        tr.append(f"Published: {law['published']}")
    tr.append(f"Language: {law['language']}")
    if law.get('bengali_id'):
        tr.append(f"Bengali-version: {SITE}/act-{law['bengali_id']}.html")
    tr.append(f"Source: {SITE}/act-details-{law['id']}.html")
    return '\n'.join([subject, '', *body, '', *tr]) + '\n'


def plan(today: str, limit: int | None, workers: int):
    rows = P.index_rows()
    with ProcessPoolExecutor(workers) as pool:
        metas = list(pool.map(law_meta, rows, chunksize=8))
    by_id = {m['id']: m for m in metas}
    issues: list[list[str]] = []
    repealed, skipped_bn, laws = [], [], []
    for m in metas:
        if m['act'] is None or m['det'] is None:
            issues.append([str(m['id']), m['index_title'], 'page not fetched or unreadable'])
            continue
        if m['repealed_in_index'] or m['det']['repealed']:
            repealed.append(m)
            continue
        a = m['act']
        if a['other_lang'] == 'English':
            en = by_id.get(a['other_id'])
            if en and en.get('det') and not (en['repealed_in_index'] or en['det']['repealed']):
                skipped_bn.append(m)
                continue
        if a['other_lang'] == 'Bangla':
            m['bengali_id'] = a['other_id']
        if not m['kind']:
            issues.append([str(m['id']), m['index_title'], f"number line not recognised: {m['det']['kind_line']!r}"])
            continue
        laws.append(m)
    # folders: constitution/ ; <kind>/<year>/<number>; a second law with the same key gets -<site id>
    used = {}
    for m in sorted(laws, key=lambda x: x['id']):
        if m['kind'] == 'constitution':
            key = 'constitution'
        else:
            key = f"{m['kind']}/{m['year']}/{m['number'] if m['number'] is not None else 'id' + str(m['id'])}"
        if key in used:
            issues.append([str(m['id']), m['title'], f"folder {key} already used by site id {used[key]}; this one is {key}-{m['id']}"])
            key = f"{key}-{m['id']}"
        used[key] = m['id']
        m['dir'] = key
    laws.sort(key=lambda x: (x['year'] or 0, KIND_ORDER[x['kind']], x['number'] or 0, x['id']))
    if limit:
        laws = laws[:limit]
    return laws, repealed, skipped_bn, issues, by_id


def csv_bytes(rows) -> bytes:
    out = io.StringIO()
    w = csv.writer(out, lineterminator='\n')
    for r in rows:
        w.writerow(r)
    return out.getvalue().encode('utf-8')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('repo', type=Path)
    ap.add_argument('--today', required=True)
    ap.add_argument('--limit', type=int)
    ap.add_argument('--workers', type=int, default=8)
    args = ap.parse_args()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', args.today):
        sys.exit('--today must be YYYY-MM-DD')
    fetched_on = (CACHE / 'fetched_on.txt').read_text().strip()
    if fetched_on > args.today:
        sys.exit(f'retrieval date {fetched_on} is after --today')
    day = fetched_on

    laws, repealed, skipped_bn, issues, by_id = plan(args.today, args.limit, args.workers)
    with ProcessPoolExecutor(args.workers) as pool:
        built = list(pool.map(build_one, laws, chunksize=4))
    amend_rows = []
    for law, (files, amend, iss) in zip(laws, built):
        law['units'] = sum(1 for p in files if not p.endswith(('/title.md', '/index.txt')))
        law['notes'] = len(amend)
        for i in iss:
            issues.append([str(law['id']), law['title'], i])
        for r in amend:
            am_id = r['links'][0] if r['links'] else None
            am = by_id.get(am_id) if am_id else None
            m = EN_ACT_NO.search(r['text'])
            mb = BN_ACT_NO.search(r['text'] + ' ')
            am_no = f'{m.group(1)} {m.group(2)} of {m.group(3)}' if m else (
                f'{mb.group(3)} {P.number(mb.group(2))} of {P.number(mb.group(1))}' if mb else '')
            amend_rows.append([law['dir'], r['unit'], r['footnote'], r['kind'],
                               (am or {}).get('title', ''), am_no, (am or {}).get('published') or '',
                               f'{SITE}/act-{am_id}.html' if am_id else '', r['text']])

    import docs as docmod
    stats_extra = {'repealed': len(repealed), 'bengali_dropped': len(skipped_bn)}
    docs = docmod.render(laws, repealed, skipped_bn, issues, amend_rows, args.today, day, stats_extra)
    print(f"{len(laws)} laws, {sum(l['units'] for l in laws)} units, {len(amend_rows)} footnotes, "
          f"{len(repealed)} repealed left out, {len(skipped_bn)} Bengali texts with an English version, {len(issues)} issues", flush=True)

    repo = args.repo
    buf = io.BytesIO()
    w = buf.write
    when = git_date(day)
    for law, (files, _, _) in zip(laws, built):
        msg = message(law, day, law['units'], law['notes']).encode('utf-8')
        w(b'commit refs/heads/main\n')
        w(f'author {PUBLISHER[0]} <{PUBLISHER[1]}> {when}\ncommitter {COMMITTER} {when}\n'.encode())
        w(f'data {len(msg)}\n'.encode() + msg + b'\n')
        for path, text in sorted(files.items()):
            t = text.encode('utf-8')
            w(f'M 100644 inline {path}\ndata {len(t)}\n'.encode() + t + b'\n')
        w(b'\n')
    msg = (f'Documentation: README, REPRODUCE, SOURCES, corpus.json, tools and data\n\n'
           f'Built from the bdlaws.minlaw.gov.bd cache retrieved on {day}.\n\nKind: documentation\n'
           f'In-force: {day}\n').encode()
    w(b'commit refs/heads/main\n')
    w(f'author {COMMITTER} {when}\ncommitter {COMMITTER} {when}\n'.encode())
    w(f'data {len(msg)}\n'.encode() + msg + b'\n')
    for path, data in sorted(docs.items()):
        w(f'M 100644 inline {path}\ndata {len(data)}\n'.encode() + data + b'\n')
    w(b'\n')
    tmp = repo.parent / (repo.name + '.build')
    import shutil
    import os
    import stat

    def onerr(func, path, _):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    if tmp.exists():
        shutil.rmtree(tmp, onerror=onerr)
    subprocess.run(['git', 'init', '-q', '--bare', str(tmp)], check=True)
    r = subprocess.run(['git', '-C', str(tmp), 'fast-import', '--quiet', '--force'], input=buf.getvalue(), capture_output=True)
    if r.returncode:
        sys.exit(r.stderr.decode('utf-8', 'replace')[-3000:])
    head = subprocess.run(['git', '-C', str(tmp), 'rev-parse', 'main'], capture_output=True, text=True).stdout.strip()
    count = subprocess.run(['git', '-C', str(tmp), 'rev-list', '--count', 'main'], capture_output=True, text=True).stdout.strip()
    # bring the built main into the working repo as branch `build`
    subprocess.run(['git', '-C', str(repo), 'fetch', '-q', '--force', str(tmp.resolve()), 'main:build'], check=True)
    shutil.rmtree(tmp, onerror=onerr)
    print(f'built {count} commits, head {head} (branch build in {repo})', flush=True)


if __name__ == '__main__':
    main()
