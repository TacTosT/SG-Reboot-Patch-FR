#!/usr/bin/env python
"""Extract dialogue from STEINS;GATE RE:BOOT into translation-ready files.

Each scenario entry is a compiled .ks scene tree. Dialogue lives in
scene["texts"], one entry per displayed line:

    [ speaker, [variants...], [voice...], line_index, stage_state ]

where variants[0] is the Japanese original and variants[1..] follow the
file's own "languages" list (currently ["en", "tc", "sc"]). Each variant is
[speaker, text, display_length, *alt_forms].

Usage:
    python extract_dialogue.py --list
    python extract_dialogue.py resg00_01.ks
    python extract_dialogue.py --chapter 00
    python extract_dialogue.py --all
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))

from sgre import Archive  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "extracted")

# Inline markup that must survive translation intact: ruby/furigana, tips
# links, and %p pause/dash codes. Tag-count parity is necessary but NOT
# sufficient for ruby - positional offsets do not survive rewording.
TAG_RE = re.compile(r"%[a-z]|<tips,|\[[^\]]*,\d+\]")
CJK_RE = re.compile(r"[぀-ヿ一-鿿]")
FILE_RE = re.compile(r"^resg(\w+?)_(\w+)\.ks$")


def parse_variant(v):
    if not isinstance(v, list) or len(v) < 2:
        return None
    return {
        "name": v[0],
        "text": v[1],
        "display_len": v[2] if len(v) > 2 else None,
        "alt": [a for a in v[3:] if isinstance(a, str)],
    }


def parse_entry(entry, languages):
    """One scene["texts"] element -> a flat record, or None if it holds no text."""
    if not isinstance(entry, list) or len(entry) < 2:
        return None
    speaker = entry[0] if isinstance(entry[0], str) else None
    raw_variants = entry[1] if isinstance(entry[1], list) else []
    codes = ["ja"] + list(languages)

    texts, names = {}, {}
    for i, v in enumerate(raw_variants):
        p = parse_variant(v)
        if p is None:
            continue
        code = codes[i] if i < len(codes) else f"lang{i}"
        texts[code] = p["text"]
        if p["name"]:
            names[code] = p["name"]
    if not texts:
        return None

    voice = voice_ms = None
    if len(entry) > 2 and isinstance(entry[2], list) and entry[2]:
        v0 = entry[2][0]
        if isinstance(v0, dict):
            voice = v0.get("voice")
            voice_ms = v0.get("time")

    ja = texts.get("ja", "")
    return {
        "speaker": speaker,
        "speaker_by_lang": names,
        "texts": texts,
        "voice": voice,
        "voice_ms": voice_ms,
        "line_index": entry[3] if len(entry) > 3 and isinstance(entry[3], int) else None,
        "has_tags": bool(TAG_RE.search(ja)),
        "ja_chars": len(ja),
    }


def extract_file(arc, name):
    psb = arc.psb(name)
    root = psb.root
    languages = [l for l in (root.get("languages") or []) if isinstance(l, str)]
    m = FILE_RE.match(name)
    chapter, part = (m.group(1), m.group(2)) if m else ("", "")

    rows = []
    for scene in root.get("scenes") or []:
        if not isinstance(scene, dict):
            continue
        label = scene.get("label") or ""
        for idx, entry in enumerate(scene.get("texts") or []):
            rec = parse_entry(entry, languages)
            if rec is None:
                continue
            rec.update({
                "id": f"{name}:{label}:{idx}",
                "file": name,
                "chapter": chapter,
                "part": part,
                "scene": label,
                "text_index": idx,
            })
            rows.append(rec)
    return rows, languages


def write_outputs(rows, stem):
    os.makedirs(OUTDIR, exist_ok=True)
    jsonl_path = os.path.join(OUTDIR, f"{stem}.jsonl")
    txt_path = os.path.join(OUTDIR, f"{stem}.txt")

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(txt_path, "w", encoding="utf-8") as f:
        scene = None
        for r in rows:
            if r["scene"] != scene:
                scene = r["scene"]
                f.write(f"\n{'=' * 70}\n{r['file']}  scene {scene}\n{'=' * 70}\n\n")
            head = r["speaker"] or "(narration)"
            tag = "  [TAGS]" if r["has_tags"] else ""
            v = f"  voice={r['voice']}" if r["voice"] else ""
            f.write(f"--- #{r['text_index']}  {head}{v}{tag}\n")
            for code in ("ja", "en"):
                if code in r["texts"]:
                    f.write(f"  {code.upper()}: {r['texts'][code]}\n")
            f.write("\n")
    return jsonl_path, txt_path


def summarize(rows, languages):
    ja_chars = sum(r["ja_chars"] for r in rows)
    en_words = sum(len(r["texts"].get("en", "").split()) for r in rows)
    voiced = sum(1 for r in rows if r["voice"])
    tagged = sum(1 for r in rows if r["has_tags"])
    speakers = {r["speaker"] for r in rows if r["speaker"]}
    print(f"  lines          : {len(rows):,}")
    print(f"  japanese chars : {ja_chars:,}")
    print(f"  english words  : {en_words:,}")
    print(f"  voiced lines   : {voiced:,}")
    print(f"  lines w/ tags  : {tagged:,}   <- need review after translation")
    print(f"  distinct speakers: {len(speakers)}")
    print(f"  languages       : ja + {languages}")
    # rate measured on the NEKOPARA pipeline run (Sonnet batch pricing)
    print(f"  est. batch cost: ${ja_chars * 0.000017:,.2f} (at $0.000017/JP char)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="scenario entries, e.g. resg00_01.ks")
    ap.add_argument("--list", action="store_true", help="list scenario entries and exit")
    ap.add_argument("--chapter", help="extract every resg<CH>_*.ks")
    ap.add_argument("--all", action="store_true", help="extract every .ks scenario file")
    ap.add_argument("--game-dir", help="override wind3d11data location")
    ap.add_argument("--stem", help="output basename (default: derived from selection)")
    args = ap.parse_args()

    arc = Archive("scenario", args.game_dir)
    ks = [n for n in arc.names() if n.endswith(".ks")]

    if args.list:
        print(f"{len(ks)} scenario scripts in {arc.game_dir}\n")
        for n in ks:
            off, length = arc.file_info[n]
            print(f"  {n:24} {length:>9,} bytes packed")
        return

    if args.all:
        targets, stem = ks, "all"
    elif args.chapter:
        targets = [n for n in ks if n.startswith(f"resg{args.chapter}_")]
        stem = f"chapter{args.chapter}"
        if not targets:
            sys.exit(f"no scripts for chapter {args.chapter!r}")
    elif args.files:
        targets = args.files
        stem = os.path.splitext(targets[0])[0] if len(targets) == 1 else "selection"
    else:
        ap.error("give a file, --chapter, --all, or --list")

    rows, languages = [], []
    for name in targets:
        if name not in arc.file_info:
            sys.exit(f"no such entry: {name}")
        r, langs = extract_file(arc, name)
        languages = languages or langs
        rows.extend(r)
        print(f"  {name:24} {len(r):>6,} lines")

    jsonl, txt = write_outputs(rows, args.stem or stem)
    print(f"\nwrote {jsonl}\n      {txt}\n")
    summarize(rows, languages)


if __name__ == "__main__":
    main()
