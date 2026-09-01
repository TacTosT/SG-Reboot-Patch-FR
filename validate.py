#!/usr/bin/env python
"""Check a French translation batch against its source for mechanical faults.

Structured output only enforces *shape*, never completeness or tag fidelity, so
every batch gets audited here before it is allowed near the game files.

    python validate.py extracted/resg00_01.jsonl extracted/sample_fr.jsonl
"""
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TIPS_TSV = os.path.join(HERE, "prompt", "tips_glossary.tsv")

PAUSE = re.compile(r"%p[^;]*;")
# The source writes tips tags both as <tips,20,x> and <tips, 20, x> — tolerate
# whitespace, or every spaced source tag reads as "the model invented a tag".
TIPS = re.compile(r"<tips,\s*(\d+)\s*,([^>]*)>")
NEWLINE = "\\n"
NBSP = " "


def label_matches(a: str, b: str) -> bool:
    """Tolerate the variation a real sentence forces on a glossary lemma.

    The glossary stores a lemma; in running text it legitimately takes an
    article, a plural, or a sentence-initial capital. Flagging those buries the
    genuine mismatches under noise.
    """
    def norm(s):
        s = s.strip().lower()
        s = re.sub(r"^(?:l[ea] |l['’]|les |un |une |des )", "", s)
        return s.rstrip("s")
    return bool(a) and bool(b) and norm(a) == norm(b)


def load_tips():
    if not os.path.exists(TIPS_TSV):
        return {}
    with open(TIPS_TSV, encoding="utf-8") as f:
        return {int(r["id"]): r["fr"] for r in csv.DictReader(f, delimiter="\t") if r["fr"]}


def check(src_path, fr_path):
    src = {}
    with open(src_path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            src[r["id"]] = r

    fr = {}
    dupes = []
    with open(fr_path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["id"] in fr:
                dupes.append(r["id"])
            fr[r["id"]] = r["fr"]

    tips_fr = load_tips()
    problems = []

    # Completeness, in both directions.
    for i in sorted(set(src) - set(fr)):
        problems.append((i, "MISSING", "no translation returned for this id"))
    for i in sorted(set(fr) - set(src)):
        problems.append((i, "UNKNOWN_ID", "id not present in the source batch"))
    for i in dupes:
        problems.append((i, "DUPLICATE", "id returned more than once"))

    for i in sorted(set(src) & set(fr)):
        ja = src[i]["texts"].get("ja", "")
        out = fr[i]

        if not out.strip():
            problems.append((i, "EMPTY", "empty translation"))
            continue

        for label, pat in (("%p", PAUSE), ("<tips,", TIPS)):
            a, b = len(pat.findall(ja)), len(pat.findall(out))
            if a != b:
                problems.append((i, "TAG_COUNT", f"{label}: source has {a}, translation has {b}"))

        a, b = ja.count(NEWLINE), out.count(NEWLINE)
        if a != b:
            problems.append((i, "NEWLINE", f"\\n: source has {a}, translation has {b}"))

        # Compare as multisets: French routinely reorders two tips terms within
        # a sentence ("la théorie de la relativité d'Einstein" vs the Japanese
        # order). What matters is that the same indices are present, each still
        # carrying its own label — not the order they appear in.
        src_ids = sorted(int(n) for n, _ in TIPS.findall(ja))
        out_ids = sorted(int(n) for n, _ in TIPS.findall(out))
        if src_ids != out_ids:
            problems.append((i, "TIPS_INDEX", f"indices {src_ids} became {out_ids}"))

        for n, label in TIPS.findall(out):
            want = tips_fr.get(int(n))
            if want and not label_matches(label, want):
                problems.append((i, "TIPS_LABEL", f"tips {n}: got {label!r}, glossary says {want!r}"))

        if NBSP in out:
            problems.append((i, "NBSP", "contains a non-breaking space (U+00A0)"))
        if "..." in out:
            problems.append((i, "ELLIPSIS", "uses ... instead of the … character"))

    return src, fr, problems


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, fr, problems = check(sys.argv[1], sys.argv[2])
    print(f"source lines     : {len(src):,}")
    print(f"translated lines : {len(fr):,}")
    print(f"problems         : {len(problems)}\n")
    for i, kind, msg in problems:
        print(f"  [{kind:11}] {i}\n                {msg}")
    if not problems:
        print("  clean - every id present, every tag preserved.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
