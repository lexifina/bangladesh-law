"""Parse the cached pages of the Laws of Bangladesh (bdlaws.minlaw.gov.bd) into laws and units.

The index (laws-of-bangladesh-chronological-index.html) lists every law with its site id. Each law has
  act-<id>.html          its table of contents (section numbers and names), its publication date, and a link to
                          the other-language version where one exists ("Open Bangla Version" / "Open English Version")
  act-details-<id>.html  the whole text: title, number, date, preamble, Part/Chapter headings, each section's name and
                          text, and every footnote (the amendment notes) at the end.
"""
import datetime
import html as htmlmod
import re
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).parent
CACHE = HERE / '.cache'
RAW = CACHE / 'raw'

BN_DIGITS = str.maketrans('\u09e6\u09e7\u09e8\u09e9\u09ea\u09eb\u09ec\u09ed\u09ee\u09ef', '0123456789')
# Bengali letters used as section suffixes (2\u0995 = 2A), in alphabetical order
BN_LETTERS = ('\u0995\u0996\u0997\u0998\u0999\u099a\u099b\u099c\u099d\u099e\u099f\u09a0\u09a1\u09a2\u09a3\u09a4'
              '\u09a5\u09a6\u09a7\u09a8\u09aa\u09ab\u09ac\u09ad\u09ae\u09af\u09b0\u09b2\u09b6\u09b7\u09b8\u09b9')
BENGALI = re.compile('[\u0980-\u09ff]')
DANDA = '\u0964\u09f7'  # dari and the Bengali currency numerator four, both used as the section-number stop
EN_MONTHS = {m: i for i, m in enumerate(['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
                                         'september', 'october', 'november', 'december'], 1)}
BN_MONTHS = {
    '\u099c\u09be\u09a8\u09c1\u09df\u09be\u09b0\u09bf': 1, '\u099c\u09be\u09a8\u09c1\u09af\u09bc\u09be\u09b0\u09bf': 1,
    '\u099c\u09be\u09a8\u09c1\u09df\u09be\u09b0\u09c0': 1,
    '\u09ab\u09c7\u09ac\u09cd\u09b0\u09c1\u09df\u09be\u09b0\u09bf': 2, '\u09ab\u09c7\u09ac\u09cd\u09b0\u09c1\u09af\u09bc\u09be\u09b0\u09bf': 2,
    '\u09ab\u09c7\u09ac\u09cd\u09b0\u09c1\u09df\u09be\u09b0\u09c0': 2,
    '\u09ae\u09be\u09b0\u09cd\u099a': 3, '\u098f\u09aa\u09cd\u09b0\u09bf\u09b2': 4, '\u09ae\u09c7': 5,
    '\u099c\u09c1\u09a8': 6, '\u099c\u09c1\u09b2\u09be\u0987': 7, '\u0986\u0997\u09b8\u09cd\u099f': 8,
    '\u0986\u0997\u09b7\u09cd\u099f': 8, '\u09b8\u09c7\u09aa\u09cd\u099f\u09c7\u09ae\u09cd\u09ac\u09b0': 9,
    '\u0985\u0995\u09cd\u099f\u09cb\u09ac\u09b0': 10, '\u0985\u0995\u09cd\u099f\u09cb\u09ac\u09b0\u09c7': 10,
    '\u09a8\u09ad\u09c7\u09ae\u09cd\u09ac\u09b0': 11, '\u09a1\u09bf\u09b8\u09c7\u09ae\u09cd\u09ac\u09b0': 12,
}


def decode(b: bytes) -> str:
    if b[:2] in (b'\xfe\xff', b'\xff\xfe'):
        return b.decode('utf-16')
    return b.decode('utf-8', 'replace')


def read(name: str) -> str | None:
    p = RAW / name
    return decode(p.read_bytes()) if p.exists() else None


def norm(s: str) -> str:
    s = s.replace('\xa0', ' ').replace('\u2002', ' ').replace('\u2003', ' ').replace('\u2009', ' ')
    s = s.replace('\xad', '').replace('\ufeff', '').replace('\u200b', '')
    return re.sub(r'\s+', ' ', s).strip()


def roman(s: str) -> int | None:
    s = s.upper()
    if not s or not re.fullmatch(r'[IVXLCDM]+', s):
        return None
    vals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    total = 0
    for i, ch in enumerate(s):
        v = vals[ch]
        total += -v if i + 1 < len(s) and vals[s[i + 1]] > v else v
    return total


def number(s: str) -> int | None:
    s = norm(s).translate(BN_DIGITS)
    if re.fullmatch(r'\d+', s):
        return int(s)
    return roman(s)


BN_MONTH_PREFIX = [('\u099c\u09be\u09a8\u09c1', 1), ('\u09ab\u09c7\u09ac\u09cd\u09b0\u09c1', 2), ('\u09ae\u09be\u09b0\u09cd\u099a', 3),
                   ('\u098f\u09aa\u09cd\u09b0\u09bf\u09b2', 4), ('\u099c\u09c1\u09b2\u09be', 7), ('\u099c\u09c1\u09a8', 6),
                   ('\u0986\u0997', 8), ('\u09b8\u09c7\u09aa\u09cd\u099f', 9), ('\u0985\u0995\u09cd\u099f\u09cb', 10),
                   ('\u09a8\u09ad\u09c7', 11), ('\u09a1\u09bf\u09b8\u09c7', 12), ('\u09ae\u09c7', 5)]


def month_of(w: str) -> int | None:
    w = w.strip().lower()
    for name, i in EN_MONTHS.items():
        if len(w) >= 3 and name.startswith(w.rstrip('.')):
            return i
    w = w.replace('\u09af\u09bc', '\u09df')
    for pre, i in BN_MONTH_PREFIX:
        if w.startswith(pre) and (i != 5 or w == pre):
            return i
    return None


def parse_day(s: str) -> str | None:
    """'[ 11th September, 1836 ]', '[ March 1, 1972 ]', '[ 12th March,1942 ]', Bengali '[ \u09e9\u09e6 \u099c\u09c1\u09a8, \u09e7\u09ef\u09ee\u09ee ]'."""
    s = norm(s).strip('[] ').translate(BN_DIGITS)
    s = re.sub(r'[,]+', ' ', s)
    s = re.sub(r'(\d)(?=[^\d\s])(?!st|nd|rd|th)', r'\1 ', s)
    s = norm(s)
    m = re.fullmatch(r'(\d{1,2})(?:st|nd|rd|th)?\s+(\S+)\s+(\d{4})', s)
    if m:
        d, mo, y = int(m.group(1)), month_of(m.group(2)), int(m.group(3))
    else:
        m = re.fullmatch(r'(\S+)\s+(\d{1,2})(?:st|nd|rd|th)?\s+(\d{4})', s)
        if not m:
            return None
        d, mo, y = int(m.group(2)), month_of(m.group(1)), int(m.group(3))
    if not mo or not 1 <= d <= 31 or not 1700 <= y <= 2100:
        return None
    try:
        datetime.date(y, mo, d)
    except ValueError:
        return None
    return f'{y:04d}-{mo:02d}-{d:02d}'


# ---------------------------------------------------------------------------------------------------- index

def index_rows() -> list[dict]:
    t = decode((CACHE / 'index.html').read_bytes())
    rows = []
    for m in re.finditer(r'<tr>(.*?)</tr>', t, flags=re.S):
        tds = re.findall(r'<td>(.*?)</td>', m.group(1), flags=re.S)
        if len(tds) != 3:
            continue
        sid = re.search(r'/act-(\d+)\.html', tds[0])
        if not sid:
            continue
        a = re.search(r'<a([^>]*)>(.*?)</a>', tds[0], flags=re.S)
        rows.append({'id': int(sid.group(1)), 'index_title': norm(htmlmod.unescape(re.sub(r'<[^>]+>', '', a.group(2)))),
                     'repealed_in_index': 'text-style-repealed' in a.group(1),
                     'index_no': norm(re.sub(r'<[^>]+>', '', tds[1])), 'index_year': norm(re.sub(r'<[^>]+>', '', tds[2]))})
    return rows


# ---------------------------------------------------------------------------------------------------- act page

def act_page(sid: int) -> dict | None:
    t = read(f'act-{sid}.html')
    if t is None:
        return None
    other = re.search(r'<a class="text-success[^"]*" href="/act-(\d+)\.html">\s*\[\s*Open\s+(Bangla|English)\s+Version\s*\]', t)
    toc = []
    for m in re.finditer(r'<a href="/act-%d/(section|part|chapter)-(\d+)\.html">\s*(.*?)\s*</a>' % sid, t, flags=re.S):
        if m.group(1) == 'section':
            toc.append((int(m.group(2)), norm(htmlmod.unescape(re.sub(r'<[^>]+>', '', m.group(3))))))
    uploads = sorted(set(re.findall(r'href="(/upload/[^"]+)"', t)))
    return {'other_id': int(other.group(1)) if other else None, 'other_lang': other.group(2) if other else None,
            'toc': toc, 'uploads': uploads}


# ---------------------------------------------------------------------------------------------------- details page

class Lines(HTMLParser):
    """An HTML fragment as lines: block elements end a line; table cells are joined with ' | '; a footnote
    (<span class='footnote' title=...><sup>n</sup></span>) becomes [^n]; images become [image]."""
    BLOCK = {'p', 'div', 'li', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'table', 'tr', 'blockquote', 'section',
             'center', 'dl', 'dt', 'dd', 'tbody', 'thead', 'pre'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self.cur: list[str] = []
        self.skip = 0
        self.fn_depth = 0       # inside a footnote span: collect its number
        self.fn_text: list[str] = []
        self.stack: list[str] = []
        self.cell = 0
        self.cells = 0

    def flush(self):
        s = norm(''.join(self.cur))
        if s:
            self.lines.append(s)
        self.cur = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('br', 'img', 'hr', 'input', 'meta', 'link', 'col'):
            if self.skip or self.fn_depth:
                return
            if tag == 'img':
                self.cur.append(' [image] ')
            elif tag == 'br':
                if self.cell:
                    self.cur.append(' ')
                else:
                    self.flush()
            return
        self.stack.append(tag)
        if tag in ('script', 'style', 'button') or self.skip:
            self.skip += 1
            return
        if self.fn_depth:
            self.fn_depth += 1
            return
        if tag == 'span' and 'footnote' in (a.get('class') or '').split():
            self.fn_depth = 1
            self.fn_text = []
            return
        if tag in ('td', 'th'):
            if self.cells:
                self.cur.append(' | ')
            self.cells += 1
            self.cell += 1
            return
        if tag == 'tr':
            self.flush()
            self.cells = 0
            return
        if tag in self.BLOCK:
            if self.cell:
                self.cur.append(' ')
            else:
                self.flush()

    def handle_endtag(self, tag):
        if tag not in self.stack:
            return
        while self.stack:
            t = self.stack.pop()
            self._end(t)
            if t == tag:
                break

    def _end(self, tag):
        if self.skip:
            self.skip -= 1
            return
        if self.fn_depth:
            self.fn_depth -= 1
            if self.fn_depth == 0:
                n = norm(''.join(self.fn_text)).translate(BN_DIGITS)
                self.cur.append(f'[^{n}]')
            return
        if tag in ('td', 'th'):
            self.cell = max(0, self.cell - 1)
            return
        if tag == 'tr':
            self.flush()
            self.cells = 0
            return
        if tag in self.BLOCK:
            if self.cell:
                self.cur.append(' ')
            else:
                self.flush()

    def handle_data(self, data):
        if self.skip:
            return
        if self.fn_depth:
            self.fn_text.append(data)
            return
        self.cur.append(data)

    def close(self):
        super().close()
        while self.stack:
            self._end(self.stack.pop())
        self.flush()


def lines(fragment: str) -> list[str]:
    p = Lines()
    p.feed(fragment)
    p.close()
    return p.lines


ROW = re.compile(r'<div class="row lineremoves\s*">')
GROUP = re.compile(r'<div class="act-(part|chapter)-group[^"]*">(.*?)</div>', re.S)


def details(sid: int) -> dict | None:
    t = read(f'act-details-{sid}.html')
    if t is None:
        return None
    i = t.find('<section class="bg-act-section')
    j = t.find('<section class="copy-right')
    if i < 0 or j < 0:
        return None
    body = t[i:j]
    h3 = re.search(r'<h3>(.*?)</h3>', body, re.S)
    h4 = re.search(r'<h4[^>]*>(.*?)</h4>', body, re.S)
    date = re.search(r'<p class="pull-right print-center publish-date">(.*?)</p>', body, re.S)
    repealed = re.search(r'<section class="bt-act-repealed[^"]*">(.*?)</section>', body, re.S)
    fn_at = body.find('<div class="footnoteListAll">')
    main = body[:fn_at] if fn_at >= 0 else body
    notes_html = body[fn_at:] if fn_at >= 0 else ''
    # preamble: between the search bar section and the first row of sections
    first_row = ROW.search(main)
    pre_from = main.find('lineremove"')
    pre_from = main.find('>', pre_from) + 1
    head_part = main[pre_from:first_row.start()] if first_row else main[pre_from:]
    head_part = head_part[:head_part.rfind('<section')] if first_row and '<section' in head_part else head_part
    title_lines = lines(h3.group(1)) if h3 else []
    kind_line = norm(htmlmod.unescape(re.sub(r'<[^>]+>', '', h4.group(1)))) if h4 else ''
    date_line = norm(htmlmod.unescape(re.sub(r'<[^>]+>', '', date.group(1)))) if date else ''
    rows = []
    if first_row:
        parts = ROW.split(main[first_row.start():])[1:]
        for p in parts:
            heads = []
            # Part and Chapter headings (##), then any heading over a group of sections inside a Chapter (###:
            # 'Of the Right of Private Defence'), in the order the page prints them, all before the section name
            pre = p[:p.find('<div class="col-sm-3 txt-head"')] if '<div class="col-sm-3 txt-head"' in p else p
            for g in re.finditer(r'<div class="act-(?:part|chapter)-group[^"]*">(.*?)</div>|'
                                 r'<p class="act-section-head[^"]*">(.*?)</p>', pre, re.S):
                if g.group(1) is not None:
                    heads += [('##', l) for l in lines(g.group(1))]
                else:
                    heads += [('###', l) for l in lines(g.group(2))]
            hd = re.search(r'<div class="col-sm-3 txt-head"[^>]*>(.*?)</div>\s*<div class="col-sm-9 txt-details"', p, re.S)
            dt = re.search(r'<div class="col-sm-9 txt-details"[^>]*>(.*)', p, re.S)
            name = lines(hd.group(1)) if hd else []
            text = []
            if dt:
                frag = dt.group(1)
                # the row ends with the closing tags of txt-details and the row; drop everything after the last row close
                frag = re.sub(r'</div>\s*</div>\s*(?:<hr/>.*)?$', '', frag.rstrip(), flags=re.S)
                frag = re.sub(r'</section>.*$', '', frag, flags=re.S)
                text = lines(frag)
            rows.append({'heads': heads, 'name': name, 'text': text})
    notes = []
    for m in re.finditer(r"<li class='footnoteList'>(.*?)</li>", notes_html, re.S):
        nm = re.search(r'<sup[^>]*>(.*?)</sup>', m.group(1), re.S)
        n = norm(re.sub(r'<[^>]+>', '', nm.group(1))).translate(BN_DIGITS) if nm else ''
        rest = re.sub(r'^.*?</h6>', '', m.group(1), count=1, flags=re.S)
        links = [int(x) for x in re.findall(r"href='/act-(\d+)\.html'", rest)]
        notes.append({'n': n, 'text': norm(' '.join(lines(rest))), 'links': links})
    return {'title_lines': title_lines, 'kind_line': kind_line, 'date_line': date_line,
            'preamble': lines(head_part), 'rows': rows, 'notes': notes,
            'repealed': norm(' '.join(lines(repealed.group(1)))) if repealed else '',
            'n_li': notes_html.count("class='footnoteList'")}


def kind_of(kind_line: str, title: str) -> tuple[str, str]:
    """(folder kind, number text) from the page's number line, e.g. '( ACT NO. XXI OF 1836 )'."""
    k = kind_line.strip('() ').strip()
    m = re.match(r"(?i)^(.*?)\s*(?:NO\.?\s*)?([0-9IVXLCivxlc]+)\s+OF\s+(\d{4})$", k.translate(BN_DIGITS))
    if m and not BENGALI.search(m.group(1)):
        k = k.translate(BN_DIGITS)
    m = re.match(r"(?i)^(.*?)\s*(?:NO\.?\s*)?([0-9IVXLCivxlc]+)\s+OF\s+(\d{4})$", k)
    if m:
        word = m.group(1).upper()
        if 'ORDINANCE' in word:
            kind = 'ordinance'
        elif 'ORDER' in word:
            kind = 'president-order'
        elif 'REGULATION' in word:
            kind = 'regulation'
        else:
            kind = 'act'
        return kind, m.group(2)
    m = re.match(r'^([\u09e6-\u09ef0-9]{4})\s*\u09b8\u09a8\u09c7\u09b0\s*([\u09e6-\u09ef0-9]+)\s*\u09a8\u0982\s*(\S+)$', k)
    if m:
        word = m.group(3)
        kind = 'ordinance' if word.startswith('\u0985\u09a7\u09cd\u09af\u09be\u09a6\u09c7\u09b6') else (
            'president-order' if '\u0986\u09a6\u09c7\u09b6' in word else 'act')
        return kind, m.group(2)
    return '', ''


def unit_name(label: str, constitution: bool) -> str | None:
    """'2A. The state religion' -> section-2A; '\u09e8\u0995\u09f7 ...' -> section-2A."""
    s = label.translate(BN_DIGITS)
    m = re.match(r'^\[?(\d+(?:[ -]?[A-Z]{1,2}(?![a-z]))?[A-Za-z]*)\s*(?:\.|[%s]|$)' % DANDA, s)
    if not m:
        m = re.match(r'^\[?(\d+)([%s]+)\s*[%s.]' % (BN_LETTERS, DANDA), s)
        if not m:
            return None
        suf = ''.join(chr(ord('A') + BN_LETTERS.index(c)) for c in m.group(2))
        num = m.group(1) + suf
    else:
        num = m.group(1).replace(' ', '').replace('-', '')
        num = num.upper() if not re.fullmatch(r'\d+[a-z]+', num) else num
    return f"{'article' if constitution else 'section'}-{num}"
