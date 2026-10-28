"""Append the laws in force that the site has only in Bengali to a clone of the published main (append-only).

    python -X utf8 append_bn.py <clone of lexifina/bangladesh-law> --today YYYY-MM-DD [--workers 4]

Main already holds the 590 English laws (one commit each, dated the retrieval day) and a documentation commit. This
script builds every law from the same cache exactly as build.py does, checks that the English laws' files equal
main's tree byte for byte, then writes on top of main, with git fast-import:

- one commit per Bengali-only law in force (same message shape, author, dates and trailers as build.py's commits;
  Language: bn), in build.py's order (year, kind, number, site id);
- one new documentation commit (README, REPRODUCE, SOURCES, corpus.json, laws.csv, data/), never replacing the old.

English folders keep the names main gives them; a Bengali law whose folder key is taken gets -<site id>, as build.py
does. Author dates are noon Dhaka on the retrieval day; committer dates are main's head committer time plus one second
per appended commit, so they never go backwards.
"""
import argparse
import csv
import io
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import build as B

HERE = Path(__file__).parent


def git(repo: Path, *a: str, inp: bytes | None = None) -> str:
    r = subprocess.run(['git', '-C', str(repo), *a], input=inp, capture_output=True)
    if r.returncode:
        sys.exit(f'git {a[0]}: ' + r.stderr.decode('utf-8', 'replace')[-2000:])
    return r.stdout.decode('utf-8')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('repo', type=Path)
    ap.add_argument('--today', required=True)
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()
    repo = args.repo.resolve()
    workers = max(1, min(args.workers, 4))
    day = (B.CACHE / 'fetched_on.txt').read_text().strip()

    head = git(repo, 'rev-parse', 'main').strip()
    if git(repo, 'rev-parse', 'origin/main').strip() != head:
        sys.exit('main must equal origin/main')
    published = list(csv.DictReader(io.StringIO(git(repo, 'show', 'main:laws.csv'))))
    pub_dir = {int(r['site_id']): r['path'].rstrip('/') for r in published}
    head_ct = int(git(repo, 'log', '-1', '--format=%ct', 'main').strip())

    laws, repealed, skipped_bn, bengali_only, issues, by_id = B.plan(args.today, None, workers)
    if {l['id'] for l in laws} != set(pub_dir):
        sys.exit('the English laws planned differ from main\'s laws.csv')
    for l in laws:
        if l['dir'] != pub_dir[l['id']]:
            sys.exit(f"site id {l['id']}: folder {l['dir']} here, {pub_dir[l['id']]} on main")

    # Bengali-only laws: folders after every English one is fixed (keys taken -> -<site id>)
    used = {l['dir']: l['id'] for l in laws}
    bn = []
    for m in sorted(bengali_only, key=lambda x: x['id']):
        if not m['kind']:
            issues.append([str(m['id']), m['index_title'], f"number line not recognised: {m['det']['kind_line']!r}"])
            continue
        if m['kind'] == 'constitution':
            issues.append([str(m['id']), m['title'], 'a Bengali Constitution text with no English pair; left out'])
            continue
        kind = f"{m['origin']}-{m['kind']}" if m['origin'] else m['kind']
        key = f"{kind}/{m['year']}/{m['number'] if m['number'] is not None else 'id' + str(m['id'])}"
        if key in used:
            issues.append([str(m['id']), m['title'], f"folder {key} already used by site id {used[key]}; this one is {key}-{m['id']}"])
            key = f"{key}-{m['id']}"
        used[key] = m['id']
        m['dir'] = key
        bn.append(m)
    bn.sort(key=lambda x: (x['year'] or 0, B.KIND_ORDER[x['kind']], x['number'] or 0, x['id']))
    left = [m for m in bengali_only if 'dir' not in m]

    allx = laws + bn
    with ProcessPoolExecutor(workers) as pool:
        built = list(pool.map(B.build_one, allx, chunksize=4))
    for law, (files, amend, iss) in zip(allx, built):
        law['units'] = sum(1 for p in files if not p.endswith(('/title.md', '/index.txt')))
        law['notes'] = len(amend)
        for i in iss:
            issues.append([str(law['id']), law['title'], i])

    # the English laws must read back from main byte for byte
    want = {}
    for law, (files, _, _) in zip(laws, built):
        for p, t in files.items():
            want[p] = t.encode('utf-8')
    tree = {}
    for line in git(repo, 'ls-tree', '-r', 'main').splitlines():
        meta, path = line.split('\t', 1)
        tree[path] = meta.split()[2]
    import hashlib
    bad = []
    for p, b in want.items():
        oid = hashlib.sha1(b'blob %d\0' % len(b) + b).hexdigest()
        if tree.get(p) != oid:
            bad.append(p)
    if bad:
        sys.exit(f'{len(bad)} English files differ from main, e.g. {bad[:5]}')
    for law in bn:
        if any(p.startswith(law['dir'] + '/') for p in tree):
            sys.exit(f"{law['dir']}: already on main")

    amend_rows = B.amendment_rows(allx, built, by_id)
    import docs as docmod
    docmod.REPO_FILES = HERE / 'repo-bn'
    docmod.BUILD_FILES = docmod.BUILD_FILES + ('append_bn.py',)
    docs = docmod.render(allx, repealed, skipped_bn, left, issues, amend_rows, args.today, day)
    print(f"{len(laws)} English + {len(bn)} Bengali laws, {len(left)} Bengali-only left out, "
          f"{sum(l['units'] for l in bn)} new units, {len(amend_rows)} footnotes, {len(issues)} issues", flush=True)

    buf = io.BytesIO()
    w = buf.write
    when = B.git_date(day)
    tz = '+0600'
    n = 0
    first = True
    for law, (files, _, _) in list(zip(allx, built))[len(laws):]:
        n += 1
        msg = B.message(law, day, law['units'], law['notes']).encode('utf-8')
        assert b'\r' not in msg
        w(b'commit refs/heads/main\n')
        w(f'author {B.PUBLISHER[0]} <{B.PUBLISHER[1]}> {when}\ncommitter {B.COMMITTER} {head_ct + n} {tz}\n'.encode())
        w(f'data {len(msg)}\n'.encode() + msg + b'\n')
        if first:
            w(f'from {head}\n'.encode())
            first = False
        for path, text in sorted(files.items()):
            t = text.encode('utf-8')
            w(f'M 100644 inline {path}\ndata {len(t)}\n'.encode() + t + b'\n')
        w(b'\n')
    n += 1
    msg = (f'Documentation: the laws in force that the site has only in Bengali\n\n'
           f'README, REPRODUCE, SOURCES, corpus.json, laws.csv and data/ for the {len(bn)} Bengali laws added on\n'
           f'top of the {len(laws)} English ones, all built from the bdlaws.minlaw.gov.bd pages retrieved on {day}.\n\n'
           f'Kind: documentation\nIn-force: {day}\n').encode()
    w(b'commit refs/heads/main\n')
    w(f'author {B.COMMITTER} {when}\ncommitter {B.COMMITTER} {head_ct + n} {tz}\n'.encode())
    w(f'data {len(msg)}\n'.encode() + msg + b'\n')
    if first:
        w(f'from {head}\n'.encode())
    old = set(tree)
    for path in sorted(p for p in old if not re.match(r'^(constitution|[a-z-]+/\d{4}/[^/]+)/', p) and p not in docs):
        w(f'D {path}\n'.encode())
    for path, data in sorted(docs.items()):
        w(f'M 100644 inline {path}\ndata {len(data)}\n'.encode() + data + b'\n')
    w(b'\n')
    git(repo, 'fast-import', '--quiet', inp=buf.getvalue())
    new = git(repo, 'rev-parse', 'main').strip()
    cnt = git(repo, 'rev-list', '--count', f'{head}..main').strip()
    print(f'appended {cnt} commits on {head[:10]}: main {new}', flush=True)


if __name__ == '__main__':
    main()
