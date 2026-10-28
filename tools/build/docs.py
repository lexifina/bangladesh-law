"""README, REPRODUCE.md, SOURCES.md, LICENSE, corpus.json, laws.csv, data/ and tools for the Bangladesh law
repository (called by build.py; every file is generated, so a rebuild keeps them current)."""
import csv
import hashlib
import io
import json
import os
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
REPO_FILES = HERE / 'repo'
CACHE = HERE / '.cache'
SITE = 'http://bdlaws.minlaw.gov.bd'
# Published with the record: what a reader needs to rebuild from the retrieved pages and check the result. How the
# pages were retrieved stays private (the rule of 2026-10-29), and publish_gate checks every file before it is written.
BUILD_FILES = ('parse.py', 'build.py', 'docs.py', 'check_repo.py')
sys.path.insert(0, str(HERE.parent / 'gitlaw_common'))
try:
    from publish_gate import publish_gate
except ImportError:          # an outside reader rebuilding from the published tools: no private rule to apply
    if os.environ.get('GITLAW_PUBLIC_REBUILD') != '1':
        raise SystemExit('publish gate missing: run from lexifina/scripts, or set GITLAW_PUBLIC_REBUILD=1')

    def publish_gate(files):
        return files
TEMPLATES = ('README.md', 'REPRODUCE.md', 'SOURCES.md', 'LICENSE')
KIND_PLURAL = {'act': 'Acts', 'ordinance': 'Ordinances', 'president-order': "President's Orders",
               'regulation': 'Regulations'}

# folder kinds: constitution, act, ordinance, president-order, regulation, each of the last four optionally led by
# the legislature that made it (bengal-, east-bengal-, east-pakistan-); a second law with one key gets -<site id>
CITATION = {
    'file': r'(constitution|(?:(?:bengal|east-bengal|east-pakistan)-)?(?:act|ordinance|president-order|regulation)'
            r'/[0-9]{4}/[0-9a-z]+(?:-[0-9]+)?)/(?:section|article)-([0-9]+[A-Za-z]*)(?:~[0-9]+)?\.md',
    'cites': '([Ss]ection|[Aa]rticle|[Ss]\\.|[Aa]rt\\.) ?{n}([^0-9A-Za-z]|$)',
}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _csv(rows: list[list]) -> bytes:
    out = io.StringIO()
    w = csv.writer(out, lineterminator='\n')
    for r in rows:
        w.writerow(r)
    return out.getvalue().encode('utf-8')


def source_sums() -> str:
    """sha256 of every cached page the build reads: the index and each law's two pages (and the two error answers)."""
    paths = [CACHE / 'index.html', CACHE / 'fetched_on.txt'] + sorted((CACHE / 'raw').iterdir(), key=lambda p: p.name)
    paths = [p for p in paths if p.is_file() and not p.name.endswith('.tmp')]
    sums = [_sha(p) for p in paths]
    return ''.join(f'{p.relative_to(CACHE).as_posix()}\t{h}\n' for p, h in zip(paths, sums))


def _n(v) -> str:
    return '' if v is None else str(v)


def render(laws, repealed, skipped_bn, bengali_only, issues, amend, today: str, day: str) -> dict[str, bytes]:
    import parse as P
    index_rows = P.index_rows()
    kinds = Counter(l['kind'] for l in laws)
    provincial = Counter(l['origin'] for l in laws if l.get('origin'))
    units = sum(l['units'] for l in laws)
    bn_kinds = Counter(m.get('kind') or 'unknown' for m in bengali_only)
    with_law = sum(1 for a in amend if a[4] or a[5])
    with_site = sum(1 for a in amend if a[8])
    with_date = sum(1 for a in amend if a[7])
    amending = {a[8] for a in amend if a[8]}
    am_kinds = Counter(a[3] for a in amend)
    years = sorted(l['year'] for l in laws if l.get('year'))
    positional = sum(1 for i in issues if 'files named by position' in i[2])
    ver = HERE / 'verification.json'
    v = json.loads(ver.read_text('utf-8')) if ver.exists() else None
    if v:
        check = (f"Results of `check_repo.py` on the previous build from the same retrieved pages: {v['laws']:,} laws read back "
                 f"from git and compared with the raw pages, {v['chars']:,} letters and digits in the texts and "
                 f"{v['note_chars']:,} in the footnotes; {v['text_mismatch']} laws differ in their text and "
                 f"{v['note_mismatch']} in their footnotes. {v['commits']:,} commits: {v['bad_trailers']} without a "
                 f"parseable In-force, {v['backwards']} backwards, {v['future']} after the build day, {v['merges']} "
                 f"merges, {v['crs']} with a carriage return; the on-date tool right for {v['tool_ok']} of "
                 f"{v['tool_samples']} samples.")
    else:
        check = 'Not yet run on this build: run `check_repo.py` (below).'

    stats = {
        'today': today, 'retrieved': day, 'index': len(index_rows), 'in_force': len(laws) + len(bengali_only),
        'laws': len(laws), 'constitution': kinds.get('constitution', 0), 'acts': kinds.get('act', 0),
        'ordinances': kinds.get('ordinance', 0), 'orders': kinds.get('president-order', 0),
        'regulations': kinds.get('regulation', 0), 'provincial': sum(provincial.values()),
        'bengal': provincial.get('bengal', 0), 'east_bengal': provincial.get('east-bengal', 0),
        'east_pakistan': provincial.get('east-pakistan', 0),
        'units': units, 'commits': len(laws) + 1, 'footnotes': len(amend), 'footnotes_with_law': with_law,
        'footnotes_with_site': with_site, 'footnotes_with_date': with_date, 'amending_laws': len(amending),
        'repealed': len(repealed), 'bengali_only': len(bengali_only),
        'bengali_only_acts': bn_kinds.get('act', 0), 'bengali_only_ordinances': bn_kinds.get('ordinance', 0),
        'bengali_with_english': len(skipped_bn), 'issues': len(issues), 'positional': positional,
        'bengali_linked': sum(1 for l in laws if l.get('bengali_id')),
        'oldest': years[0] if years else '', 'newest': years[-1] if years else '',
        'check': check,
        'amendment_kinds': dict(sorted(am_kinds.items())),
    }
    stats['unfetched'] = len(index_rows) - len(laws) - len(bengali_only) - len(repealed) - len(skipped_bn)
    sha = {name: _sha(HERE / name) for name in BUILD_FILES}
    texts = {}
    for name in TEMPLATES:
        t = (REPO_FILES / name).read_text('utf-8')
        for k, val in stats.items():
            if isinstance(val, (str, int)):
                t = t.replace('{{' + k.upper() + '}}', f'{val:,}' if isinstance(val, int) and k not in ('oldest', 'newest') else str(val))
        for n, h in sha.items():
            t = t.replace('{{SHA_' + n.upper().replace('.', '_') + '}}', h)
        if '{{' in t:
            raise SystemExit(f'{name}: unfilled placeholder near {t[t.index("{{"):t.index("{{") + 40]!r}')
        texts[name] = t

    laws_csv = _csv([['path', 'title', 'kind', 'legislature', 'number', 'number_as_printed', 'year', 'date', 'units',
                      'footnotes', 'bengali_version', 'site_id', 'source']] +
                    [[l['dir'] + '/', l['title'], l['kind'], l.get('origin', ''), _n(l['number']),
                      l['det']['kind_line'].strip('() ').strip(), _n(l['year']), l['published'] or '', l['units'],
                      l['notes'], f"{SITE}/act-{l['bengali_id']}.html" if l.get('bengali_id') else '', l['id'],
                      f"{SITE}/act-details-{l['id']}.html"] for l in sorted(laws, key=lambda x: x['dir'])])
    amend_csv = _csv([['law', 'provision', 'footnote', 'kind', 'amending_law', 'amending_law_number',
                       'amending_provision', 'amending_law_date', 'amending_law_source', 'text']] + amend)

    def short(m):
        return [m['id'], m.get('title') or m['index_title'], m.get('kind') or '', _n(m.get('number')),
                _n(m.get('year')), m.get('published') or '']
    bn_csv = _csv([['site_id', 'title', 'kind', 'number', 'year', 'date', 'status', 'source']] +
                  [short(m) + ['in force; the site has its text only in Bengali; not included yet',
                               f"{SITE}/act-details-{m['id']}.html"] for m in sorted(bengali_only, key=lambda x: x['id'])] +
                  [short(m) + [f"in force; Bengali text of {SITE}/act-{m['act']['other_id']}.html, which is included",
                               f"{SITE}/act-details-{m['id']}.html"] for m in sorted(skipped_bn, key=lambda x: x['id'])])
    rep_csv = _csv([['site_id', 'title', 'language', 'kind', 'number', 'year', 'date', 'repeal_note', 'source']] +
                   [[m['id'], m.get('title') or m['index_title'], m.get('language', ''), m.get('kind') or '',
                     _n(m.get('number')), _n(m.get('year')), m.get('published') or '', m['det']['repealed'],
                     f"{SITE}/act-details-{m['id']}.html"] for m in sorted(repealed, key=lambda x: x['id'])])
    iss_csv = _csv([['site_id', 'title', 'issue']] + issues)

    corpus = {
        'corpus': 'bd/national/acts',
        'name': 'Laws of Bangladesh: the laws in force that the official site publishes in English',
        'label': 'Bangladesh',
        'language': 'en',
        'history': 'current-only',
        'laws': {'constitution': stats['constitution'], 'acts': stats['acts'], 'ordinances': stats['ordinances'],
                 'president_orders': stats['orders'], 'regulations': stats['regulations']},
        'not_included': {'bengali_only': stats['bengali_only'], 'list': 'data/bengali-only.csv',
                         'note': 'laws in force that the site has only in Bengali; whether to add them is not decided'},
        'history_from': day,
        'record_to': day,
        'record_note': ('The Laws of Bangladesh site (bdlaws.minlaw.gov.bd) publishes only the current text of each '
                        f'law, so each law has one version here: the text as retrieved on {day}. There is no '
                        'line-by-line history before that day. The amendment footnotes are kept in the files and '
                        'parsed into data/amendments.csv. Only the laws the site has in English are included; the '
                        f"{stats['bengali_only']} laws in force that it has only in Bengali are listed in "
                        'data/bengali-only.csv.'),
        'built': today,
        'baseline_trailer': 'Consolidated',
        'in_force_trailer': 'In-force',
        'dates': {'commit': 'the day the pages were retrieved', 'baseline_trailer': 'Consolidated',
                  'other_trailers': ['Published'],
                  'time': '12:00 Asia/Dhaka (UTC+6)', 'before_1970': 'not used: every commit is dated ' + day},
        'author': {'consolidated': 'Laws of Bangladesh (Legislative and Parliamentary Affairs Division)',
                   'amendment': 'none yet',
                   'unexplained': 'Laws of Bangladesh (Legislative and Parliamentary Affairs Division)'},
        'citation': CITATION,
        'scope': {
            'trailer': 'Applies',
            'groups': 'any one line',
            'conditions': 'all of a line',
            'when_absent': 'not extracted for Bangladesh; savings and transitional rules are in the amending laws',
            'default_reach': {
                'rule': 'presumption against retroactivity',
                'meaning': 'a repeal does not affect anything done, rights acquired or proceedings pending under the '
                           'repealed law unless a different intention appears',
                'authority': 'General Clauses Act, 1897 (Act No. X of 1897), section 6 (effect of repeal)',
                'decided_here': False,
            },
        },
        'tool': 'tools/in_force_on.py',
    }
    files = {
        'corpus.json': (json.dumps(corpus, indent=2, ensure_ascii=False) + '\n').encode('utf-8'),
        'laws.csv': laws_csv,
        'data/amendments.csv': amend_csv,
        'data/bengali-only.csv': bn_csv,
        'data/repealed.csv': rep_csv,
        'data/issues.csv': iss_csv,
        'data/stats.json': (json.dumps({k: v for k, v in stats.items() if k != 'check'}, indent=1, sort_keys=True,
                                       ensure_ascii=False) + '\n').encode('utf-8'),
        'data/source-sha256.tsv': source_sums().encode('utf-8'),
        'tools/in_force_on.py': (REPO_FILES / 'tools' / 'in_force_on.py').read_bytes(),
    }
    for name, t in texts.items():
        files[name] = t.encode('utf-8')
    for name in BUILD_FILES:
        files[f'tools/build/{name}'] = (HERE / name).read_bytes()
    for name in TEMPLATES:
        files[f'tools/build/repo/{name}'] = (REPO_FILES / name).read_bytes()
    files['tools/build/repo/tools/in_force_on.py'] = (REPO_FILES / 'tools' / 'in_force_on.py').read_bytes()
    for k, b in files.items():
        if b'\r' in b and not k.startswith('tools/build/'):
            raise SystemExit(f'{k}: carriage return')
    return publish_gate(files)
