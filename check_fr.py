#!/usr/bin/env python
"""Check the French translation on its own — no game files needed.

`validate.py` compares against the Japanese source, which is not in the repo.
This one only needs `extracted/all_fr.jsonl`, so it can run anywhere, before
every build. It guards what has already gone wrong once:

  * characters no game font can draw, or that break the engine's word wrap;
  * typography: one apostrophe (’), no full-width ？！, no "...", no double space;
  * ruby spans: in bounds, free of markup, ending on a word boundary, and no
    article shown twice ("la « [x,N]la …" displays "la « la …");
  * terms settled once and for all (Shining Finger, Steins Gate…);
  * the installer shipping the same file as the one checked here.

    python check_fr.py          # exit code 1 if anything is found
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FR_FILE = os.path.join(HERE, "extracted", "all_fr.jsonl")
SHIPPED = os.path.join(HERE, "installer", "data", "all_fr.jsonl")

# (label, pattern) — anything matching is a problem.
FORBIDDEN = [
    ("glyphe absent des polices (ᵉ)", re.compile("ᵉ")),
    ("espace insécable", re.compile("[  ]")),
    ("apostrophe droite, utiliser ’", re.compile("'")),
    ("ponctuation pleine chasse ？！", re.compile("[？！]")),
    ("... au lieu de …", re.compile(r"\.\.\.")),
    ("vrai retour à la ligne, utiliser \\n", re.compile("\n")),
    ("espaces multiples", re.compile(r"(?<=\S) {2,}")),
    # Terms settled in prompt/glossary_fr.md — never translated, never in ruby.
    ("Shining Finger traduit", re.compile(
        r"masseuse|acupress|shiatsuk|ma[îi]tre(?:sse)? (?:du )?shiatsu", re.I)),
    ("Shining Finger en rubis", re.compile(r"\[Shining Finger,")),
    ("Shining Finger avec article", re.compile(r"\b(?:[Ll]a|[Ll]e|[Cc]ette) Shining Finger")),
    ("Steins Gate traduit", re.compile(r"Porte de Pierre du Destin", re.I)),
]

RUBY = re.compile(r"\[([^\]\[]*?),(\d+)\]")
ARTICLE = re.compile(r"(?:\b(?:la|le|les|cette|ce|cet|du|des|une|un|ma|mon)\s+|\bl’|\bde la\s+)"
                     r"(?:«\s*)?$", re.I)
BASE_ARTICLE = re.compile(r"(?:la |le |les |l’)", re.I)


def ruby_problems(text):
    for m in RUBY.finditer(text):
        n = int(m.group(2))
        base = text[m.end():m.end() + n + 1]
        after = text[m.end() + n + 1:m.end() + n + 2]
        if len(base) < n + 1 or re.search(r"[<>\[\]%\\]", base):
            yield f"rubis {m.group(0)} déborde sur la suite : {base!r}"
        elif base[-1:].isalpha() and after.isalpha():
            yield f"rubis {m.group(0)} coupe un mot : {base!r}|{after}"
        if ARTICLE.search(text[:m.start()]) and BASE_ARTICLE.match(base):
            yield f"rubis {m.group(0)} : article affiché deux fois"


def check(path=FR_FILE):
    problems = []
    seen = set()
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            try:
                row = json.loads(line)
                id_, text = row["id"], row["fr"]
            except (ValueError, KeyError):
                problems.append((f"ligne {n}", "JSON illisible ou sans id/fr"))
                continue
            if id_ in seen:
                problems.append((id_, "identifiant en double"))
            seen.add(id_)
            if not text.strip():
                problems.append((id_, "traduction vide"))
            for label, pat in FORBIDDEN:
                if pat.search(text):
                    problems.append((id_, label))
            for msg in ruby_problems(text):
                problems.append((id_, msg))

    with open(path, "rb") as a, open(SHIPPED, "rb") as b:
        if a.read() != b.read():
            problems.append(("installer/data/all_fr.jsonl",
                             "différent de extracted/all_fr.jsonl — recopier avant le build"))
    return len(seen), problems


def main():
    count, problems = check()
    print(f"{count:,} répliques contrôlées, {len(problems)} problème(s)")
    for where, what in problems:
        print(f"  {where}: {what}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
