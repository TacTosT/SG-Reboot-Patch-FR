#!/usr/bin/env python
"""Deterministic terminology corrections on an already-translated file.

Terminology is a find/replace problem, not a translation problem. Sending these
back through the API costs money, takes hours, and risks the model changing
something you did not ask it to change. Two files, applied in this order:

  prompt/terminology_fixes.tsv   global rules (regex or literal), every line
  prompt/line_fixes.tsv          one reviewed edit per line: id, before, after

A line fix only applies if the line still reads exactly `before`, so an edit
can never land on text it was not written for. A line that already reads
`after` counts as done, which makes `--apply` safe to re-run.

    python fix_terms.py --survey                 # what's actually in the file
    python fix_terms.py --dry-run                # what the rules would change
    python fix_terms.py --apply                  # write it (keeps a .bak)
"""
import argparse
import collections
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(HERE, "prompt", "terminology_fixes.tsv")
LINE_FIXES = os.path.join(HERE, "prompt", "line_fixes.tsv")
DEFAULT_TARGET = os.path.join(HERE, "extracted", "all_fr.jsonl")

# Patterns used only by --survey, to show what the translation actually
# contains before you commit to a rule.
SURVEY = {
    "ruby tags still present": r"\[[^\]]{1,40},\d+\][^\s.,;:!?»]*(?:\s+[^\s.,;:!?»]+){0,5}",
    "micro-ondes variants": r"[Mm]icro-ondes[^.,;:!?»]{0,34}",
    "porte de pierre variants": r"(?:[Ll]a |[Ll]')?[Pp]orte de [Pp]ierre du [Dd]estin",
    "bare Steins Gate": r"Steins[ ;]?Gate",
}


def load_rules():
    if not os.path.exists(RULES):
        sys.exit(f"missing rules file: {RULES}")
    rules = []
    with open(RULES, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                sys.exit(f"{RULES}:{n}: expected at least 3 tab-separated fields")
            kind, pattern, repl = parts[0].strip(), parts[1], parts[2]
            note = parts[3] if len(parts) > 3 else ""
            if kind not in ("regex", "literal"):
                sys.exit(f"{RULES}:{n}: kind must be 'regex' or 'literal', got {kind!r}")
            compiled = re.compile(pattern if kind == "regex" else re.escape(pattern))
            rules.append((compiled, repl, note, n))
    return rules


def load_line_fixes():
    """{id: (before, after, note, line_no)} from prompt/line_fixes.tsv."""
    fixes = {}
    if not os.path.exists(LINE_FIXES):
        return fixes
    with open(LINE_FIXES, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                sys.exit(f"{LINE_FIXES}:{n}: expected id, before, after (tab-separated)")
            if parts[0] in fixes:
                sys.exit(f"{LINE_FIXES}:{n}: {parts[0]} already has a fix")
            fixes[parts[0]] = (parts[1], parts[2], parts[3] if len(parts) > 3 else "", n)
    return fixes


def apply_line_fixes(rows, fixes):
    """Returns (applied, already_done, stale) — stale ones are left untouched."""
    applied, done, stale = 0, 0, []
    by_id = {r["id"]: r for r in rows}
    for id_, (before, after, _note, n) in fixes.items():
        r = by_id.get(id_)
        if r is None:
            stale.append((n, id_, "no such id"))
        elif r["fr"] == after:
            done += 1
        elif r["fr"] == before:
            r["fr"] = after
            applied += 1
        else:
            stale.append((n, id_, "line no longer reads `before`"))
    return applied, done, stale


def load_rows(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


TIPS_TAG = re.compile(r"<tips,\s*\d+\s*,([^>]*)>")


def strip_added_tips(rows, source_path):
    """Remove tips tags the model added where the source had none.

    The game links a term to its Tips entry on first mention only. The model,
    seeing a glossary term it recognises, helpfully tags every later occurrence
    too — which would sprinkle clickable links the writers never put there.
    Only the tag is removed; the label text stays in the sentence.
    """
    with open(source_path, encoding="utf-8") as f:
        src = {json.loads(l)["id"]: json.loads(l) for l in f}
    fixed, samples = 0, []
    for r in rows:
        s = src.get(r["id"])
        if not s or TIPS_TAG.search(s["texts"].get("ja", "")):
            continue                      # source has tags here: leave it alone
        if not TIPS_TAG.search(r["fr"]):
            continue
        before = r["fr"]
        r["fr"] = TIPS_TAG.sub(r"\1", r["fr"])
        fixed += 1
        if len(samples) < 5:
            samples.append((r["id"], before, r["fr"]))
    return fixed, samples


def cmd_survey(rows):
    for label, pat in SURVEY.items():
        counter = collections.Counter()
        rx = re.compile(pat)
        for r in rows:
            for m in rx.findall(r["fr"]):
                counter[m if isinstance(m, str) else m[0]] += 1
        print(f"--- {label} ---  ({sum(counter.values())} occurrences)")
        for text, n in counter.most_common(10):
            print(f"  {n:5}  {text!r}")
        if not counter:
            print("  (none)")
        print()


def apply_rules(rows, rules):
    """Returns (changed_rows, per-rule counts, samples)."""
    counts = collections.Counter()
    samples = collections.defaultdict(list)
    changed = 0
    for r in rows:
        before = r["fr"]
        text = before
        for rx, repl, _note, line_no in rules:
            text, n = rx.subn(repl, text)
            if n:
                counts[line_no] += n
                if len(samples[line_no]) < 3:
                    samples[line_no].append((r["id"], before, text))
        if text != before:
            r["fr"] = text
            changed += 1
    return changed, counts, samples


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", default=DEFAULT_TARGET)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--survey", action="store_true", help="show what's in the file")
    g.add_argument("--dry-run", action="store_true", help="show what would change")
    g.add_argument("--apply", action="store_true", help="write the corrections")
    args = ap.parse_args()

    rows = load_rows(args.target)
    print(f"{len(rows):,} translated lines in {args.target}\n")

    if args.survey:
        cmd_survey(rows)
        return

    rules = load_rules()
    changed, counts, samples = apply_rules(rows, rules)

    for rx, repl, note, line_no in rules:
        n = counts.get(line_no, 0)
        flag = " " if n else "  (no match — rule may be stale)"
        print(f"[rule {line_no}] {n:5} replacements{flag} {note}")
        for _id, before, after in samples.get(line_no, [])[:1]:
            b = re.sub(r"\s+", " ", before)[:96]
            a = re.sub(r"\s+", " ", after)[:96]
            print(f"          before: {b}")
            print(f"          after : {a}")
    print(f"\n{sum(counts.values()):,} replacements across {changed:,} lines")

    fixes = load_line_fixes()
    applied, done, stale = apply_line_fixes(rows, fixes)
    print(f"line fixes: {applied} applied, {done} already done, {len(stale)} stale")
    for n, id_, why in stale:
        print(f"  [line_fixes.tsv:{n}] {id_}: {why}")
    if stale:
        sys.exit("stale line fixes — review them before applying anything")

    if args.apply:
        shutil.copy2(args.target, args.target + ".bak")
        with open(args.target, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"written. backup at {args.target}.bak")
    else:
        print("dry run — nothing written. Re-run with --apply to commit.")


if __name__ == "__main__":
    main()
