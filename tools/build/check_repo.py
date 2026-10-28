"""Check the Bangladesh law repository against the raw pages of bdlaws.minlaw.gov.bd.

    python -X utf8 check_repo.py ../bangladesh-law-build [--no-record]

1. Letters and digits: for every law in laws.csv, the files read back from git (main, in index.txt order) hold
   exactly the letters, digits and marks of the law's act-details page, in order. The source side does not use
   parse.py or build.py: the page is cut between the act's title section and the copyright section, split at the
   footnote list, its <script>, <style> and <button> elements dropped, every tag removed and entities unescaped;
   then only characters of Unicode classes L, M and N are kept, with Bengali digits read as ASCII digits. The text
   and the footnotes are compared separately (the build moves each footnote to the file that first cites it): the
   git side's footnotes are the `[^n]: ...` lines, in number order, each led by its number as the site's list is.
2. Trailers: every commit's message parses with `git interpret-trailers --parse` and has an In-force date.
3. History: no merges, no In-force date going backwards or after the build day, no carriage return in any message.
4. Tool: tools/in_force_on.py prints sample sections exactly as stored, and refuses a date before the record.
Writes scripts/bangladesh-law/verification.json (read by docs.py into REPRODUCE.md) unless --no-record.
"""
import csv
import html
import io
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).parent
RAW = HERE / '.cache' / 'raw'
BN_DIGITS = str.maketrans('\u09e6\u09e7\u09e8\u09e9\u09ea\u09eb\u09ec\u09ed\u09ee\u09ef', '0123456789')
NOTE = re.compile(r'^\[\^(\d+)\]: (.*)$')
TAG = re.compile(r'''<[A-Za-z][^\s/>]*(?:\s*/(?!>)|\s+[^\s/>=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+))?)*\s*/?>'''
                 r'|</[A-Za-z][^>]*>|<![^>]*>', re.S)


def keep(s: str) -> str:
    s = s.translate(BN_DIGITS)
    return ''.join(c for c in s if unicodedata.category(c)[0] in 'LMN')


def strip_html(h: str) -> str:
    h = re.sub(r'(?is)<(script|style|button)\b.*?</\1\s*>', ' ', h)
    h = re.sub(r'(?s)<!--.*?-->', ' ', h)
    # tags as HTML reads them: attribute values quoted with " or ' end at the same quote (and may hold '>': the site
    # nests a link in a title="..."), or are unquoted; title='Agriculturists' Loans Act' is three attributes
    h = TAG.sub(' ', h)
    return html.unescape(h)


def source(site_id: str) -> tuple[str, str]:
    b = (RAW / f'act-details-{site_id}.html').read_bytes()
    t = b.decode('utf-16') if b[:2] in (b'\xfe\xff', b'\xff\xfe') else b.decode('utf-8', 'replace')
    i = t.index('<section class="bg-act-section')
    j = t.index('<section class="copy-right')
    body = t[i:j]
    k = body.find('<div class="footnoteListAll">')
    main, notes = (body[:k], body[k:]) if k >= 0 else (body, '')
    return keep(strip_html(main)), keep(strip_html(notes))


def git(repo: Path, *a: str) -> str:
    return subprocess.run(['git', '-C', str(repo), '-c', 'core.quotepath=false', *a], capture_output=True,
                          encoding='utf-8', check=True).stdout


class Blobs:
    def __init__(self, repo: Path):
        self.p = subprocess.Popen(['git', '-C', str(repo), 'cat-file', '--batch'], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE)

    def get(self, spec: str) -> str | None:
        self.p.stdin.write(spec.encode('utf-8') + b'\n')
        self.p.stdin.flush()
        head = self.p.stdout.readline().split()
        if head[-1] == b'missing':
            return None
        data = self.p.stdout.read(int(head[2]))
        self.p.stdout.read(1)
        return data.decode('utf-8')


def mine(blobs: Blobs, path: str) -> tuple[str, str]:
    idx = blobs.get(f'main:{path}/index.txt')
    text, notes = [], {}
    for fn in idx.split():
        for line in blobs.get(f'main:{path}/{fn}').split('\n'):
            m = NOTE.match(line)
            if m:
                notes[int(m.group(1))] = m.group(1) + m.group(2)
            else:
                text.append(line.replace('[image]', ''))
    return keep('\n'.join(text)), keep(''.join(notes[n] for n in sorted(notes)))


def first_diff(a: str, b: str) -> str:
    k = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    return f'at {k}: git {a[max(0, k - 20):k + 30]!r} vs source {b[max(0, k - 20):k + 30]!r} ({len(a)} vs {len(b)})'


def main() -> None:
    repo = Path(sys.argv[1]).resolve()
    record = '--no-record' not in sys.argv
    blobs = Blobs(repo)
    laws = list(csv.DictReader(io.StringIO(git(repo, 'show', 'main:laws.csv'))))
    bad_text, bad_notes, chars, note_chars = [], [], 0, 0
    for l in laws:
        path = l['path'].rstrip('/')
        st, sn = source(l['site_id'])
        gt, gn = mine(blobs, path)
        chars += len(st)
        note_chars += len(sn)
        if gt != st:
            bad_text.append(f'{path}: text {first_diff(gt, st)}')
        if gn != sn:
            bad_notes.append(f'{path}: footnotes {first_diff(gn, sn)}')
    print(f'letters and digits: {len(laws)} laws, {chars:,} in the texts and {note_chars:,} in the footnotes; '
          f'{len(bad_text)} laws differ in the text, {len(bad_notes)} in the footnotes')
    for m in (bad_text + bad_notes)[:20]:
        print('  ', m)

    log = git(repo, 'log', '--reverse', '--first-parent', '--format=%H%x1f%B%x1e', 'main').split('\x1e')
    built_day = json.loads(git(repo, 'show', 'main:corpus.json'))['built']
    bad = back = future = crs = 0
    last = ''
    for entry in log:
        entry = entry.strip('\n')
        if not entry:
            continue
        h, msg = entry.split('\x1f', 1)
        crs += '\r' in msg
        parsed = subprocess.run(['git', 'interpret-trailers', '--parse'], input=msg, capture_output=True,
                                encoding='utf-8').stdout
        tr = dict(x.split(': ', 1) for x in parsed.splitlines() if ': ' in x)
        d = tr.get('In-force', '')
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', d):
            bad += 1
            continue
        back += d < last
        future += d > built_day
        last = d
    merges = int(git(repo, 'rev-list', '--merges', '--count', 'main').strip())
    commits = int(git(repo, 'rev-list', '--count', 'main').strip())
    print(f'history: {commits} commits, {bad} without a parseable In-force, {back} backwards, {future} after '
          f'{built_day}, {merges} merges, {crs} with a carriage return')

    day = (HERE / '.cache' / 'fetched_on.txt').read_text('utf-8').strip()
    samples = [('constitution', 'article-27'), ('constitution', 'article-7A'), ('act/1860/45', 'section-302'),
               ('act/1860/45', 'section-124A'), ('act/1897/10', 'section-6'), ('act/1872/1', 'section-3'),
               ('act/1908/5', 'section-9')]
    ok = 0
    for law, unit in samples:
        want = blobs.get(f'main:{law}/{unit}.md')
        r = subprocess.run([sys.executable, '-X', 'utf8', 'tools/in_force_on.py', day, law, unit], cwd=repo,
                           capture_output=True, encoding='utf-8')
        later = subprocess.run([sys.executable, '-X', 'utf8', 'tools/in_force_on.py', '2030-01-01', law, unit],
                               cwd=repo, capture_output=True, encoding='utf-8')
        early = subprocess.run([sys.executable, '-X', 'utf8', 'tools/in_force_on.py', '2026-10-27', law, unit],
                               cwd=repo, capture_output=True, encoding='utf-8')
        good = want is not None and r.stdout == want and later.stdout == want and early.returncode != 0
        ok += good
        print(('   ok ' if good else '   TOOL MISMATCH ') + f'{law} {unit}' + ('' if good else f' {(r.stdout or r.stderr)[:120]!r}'))
    print(f'tool: {ok}/{len(samples)} samples right')
    if record:
        (HERE / 'verification.json').write_text(json.dumps({
            'laws': len(laws), 'chars': chars, 'note_chars': note_chars, 'text_mismatch': len(bad_text),
            'note_mismatch': len(bad_notes), 'commits': commits, 'bad_trailers': bad, 'backwards': back,
            'future': future, 'merges': merges, 'crs': crs, 'tool_samples': len(samples), 'tool_ok': ok},
            indent=1, sort_keys=True) + '\n', 'utf-8')
    fails = len(bad_text) + len(bad_notes) + bad + back + future + merges + crs + (len(samples) - ok)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
