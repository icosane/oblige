#!/usr/bin/env python3
"""
Replace the JP lines in script_jp/*.ast with the EN lines from script_en/*.ast.

Everything in the JP files is kept as-is (block names, commands, CRLF line
endings, ...). Only the contents of the following are swapped for English:

  1. text   -> ja = { ... }   (dialogue / narration)
  2. select -> ja = { ... }   (choice menus)
  3. {"savetitle", text="..."} (save-slot titles)

Usage:
    python replace_jp_with_en.py [jp_dir] [en_dir] [out_dir]
Defaults: script_jp  script_en  script_out
"""
import difflib
import os
import re
import sys
import unicodedata

# ja = { ... } block at 3-tab indent, and the en = { ... } block right after it
JA_RE = re.compile(r'\n\t\t\tja = \{(.*?)\r?\n\t\t\t\},', re.S)
EN_RE = re.compile(r'\r?\n\t\t\ten = \{(.*?)\r?\n\t\t\t\},', re.S)
VO_RE = re.compile(r'\{"vo", file="([^"]+)"')
STR = r'"(?:[^"\\]|\\.)*"'
SAVETITLE_RE = re.compile(r'(\{"savetitle", text=)(' + STR + r')((?:, en=)(' + STR + r'))?')


def read(path):
    with open(path, encoding='utf-8', newline='') as f:
        return f.read()


def write(path, text):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)


def norm(s):
    """Whitespace-insensitive key (EN files sometimes drop trailing U+3000)."""
    return re.sub(r'\s+', '', s)


def tkey(s):
    """Title key: full-width/half-width differences are ignored."""
    return unicodedata.normalize('NFKC', s)


def find_blocks(s):
    """Return [(key, ja_span, en_text_or_None)] for every ja block in s."""
    out = []
    for m in JA_RE.finditer(s):
        # voice id of the same text block makes the key unique
        start = max(s.rfind('\t\ttext = {', 0, m.start()),
                    s.rfind('\t\tselect = {', 0, m.start()))
        vo = VO_RE.search(s[start:m.start()]) if start >= 0 else None
        key = (vo.group(1) if vo else '', norm(m.group(1)))
        en = EN_RE.match(s, m.end())
        out.append((key, m.span(1), en.group(1) if en else None))
    return out


def process(jp, en):
    stats = {'blocks': 0, 'replaced': 0, 'missed': 0, 'titles': 0}
    edits = []  # (start, end, new_text)

    # ---- dialogue + selects ------------------------------------------------
    jb, eb = find_blocks(jp), find_blocks(en)
    sm = difflib.SequenceMatcher(None, [b[0] for b in jb], [b[0] for b in eb],
                                 autojunk=False)
    stats['blocks'] = len(jb)
    matched = set()
    for a, b, size in sm.get_matching_blocks():
        for k in range(size):
            matched.add(a + k)
            if eb[b + k][2] is None:
                continue
            edits.append((jb[a + k][1][0], jb[a + k][1][1], eb[b + k][2]))
            stats['replaced'] += 1
    stats['missed'] = len(jb) - len(matched)

    # ---- savetitle ----------------------------------------------------------
    en_titles = {}
    for m in SAVETITLE_RE.finditer(en):
        if m.group(4):
            en_titles.setdefault(tkey(m.group(2)), []).append(m.group(4))
    for m in SAVETITLE_RE.finditer(jp):
        lst = en_titles.get(tkey(m.group(2)))
        if lst:
            edits.append((m.start(2), m.end(2), lst.pop(0) if len(lst) > 1 else lst[0]))
            stats['titles'] += 1

    # apply back-to-front so offsets stay valid
    for s0, e0, new in sorted(edits, reverse=True):
        jp = jp[:s0] + new + jp[e0:]
    return jp, stats


def main():
    jp_dir = sys.argv[1] if len(sys.argv) > 1 else 'script_jp'
    en_dir = sys.argv[2] if len(sys.argv) > 2 else 'script_en'
    out_dir = sys.argv[3] if len(sys.argv) > 3 else 'script_out'
    os.makedirs(out_dir, exist_ok=True)

    tot = {'blocks': 0, 'replaced': 0, 'missed': 0, 'titles': 0}
    copied = []
    for name in sorted(os.listdir(jp_dir)):
        jp_path = os.path.join(jp_dir, name)
        if not os.path.isfile(jp_path):
            continue
        en_path = os.path.join(en_dir, name)
        jp = read(jp_path)
        if not os.path.isfile(en_path):
            write(os.path.join(out_dir, name), jp)  # no EN counterpart: copy
            copied.append(name)
            continue
        out, st = process(jp, read(en_path))
        write(os.path.join(out_dir, name), out)
        for k in tot:
            tot[k] += st[k]
        if st['missed']:
            print(f'  [warn] {name}: {st["missed"]} of {st["blocks"]} JP blocks '
                  f'had no EN match and were left in Japanese')

    print(f'\nDone -> {out_dir}')
    print(f'  text/select blocks replaced : {tot["replaced"]} / {tot["blocks"]}')
    print(f'  save titles replaced        : {tot["titles"]}')
    print(f'  left in Japanese (no match) : {tot["missed"]}')
    if copied:
        print(f'  copied unchanged (no EN file): {", ".join(copied)}')


if __name__ == '__main__':
    main()
