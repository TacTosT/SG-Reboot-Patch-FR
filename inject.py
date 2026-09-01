#!/usr/bin/env python
"""Write the French translation into the game's own files.

French goes into the **English** language slot rather than a new one: the slot
already exists in every scene, the engine already knows how to display it, and
adding a fourth language would mean touching code we don't control. Play with
the game set to English and you get French.

What gets rewritten, and what deliberately does not:

  * `.ks` scenario entries — string table replaced, plus two numbers poked in
    place; everything else byte-exact (round-tripped against the originals).
  * each rewritten line's `display_length` — recomputed, because the engine
    drives the typewriter from it. See `display_len` below.
  * the `\n`-free alt forms a line carries — rewritten too, so the backlog
    shows French instead of the English it was built from.
  * non-`.ks` entries (charvoice, filelist, …) — copied over verbatim as their
    original *packed* bytes. Not re-compressed, so they cannot be corrupted.
  * `scenario_info.psb.m` — its offsets and lengths are poked in place, each
    keeping the byte width the game gave it. The tree is never re-encoded:
    doing so ships a semantically identical index the engine silently chokes
    on. See the comment in `build` — that bug cost an evening.

    python inject.py --dry-run     # build everything, write nothing
    python inject.py --apply       # patch the game (SHA256-verified backup)
    python inject.py --restore     # put the originals back
"""
import argparse
import collections
import hashlib
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))

from mzs import SEED, wrap                      # noqa: E402
from psb import IntRef, Psb, StrRef             # noqa: E402
from psb_write import rebuild_strings          # noqa: E402
from sgre import Archive, find_game_dir         # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FR_FILE = os.path.join(HERE, "extracted", "all_fr.jsonl")
BACKUP = os.path.join(HERE, "backup")
TARGETS = ("scenario_info.psb.m", "scenario_body.bin")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_fr():
    with open(FR_FILE, encoding="utf-8") as f:
        return {json.loads(l)["id"]: json.loads(l)["fr"] for l in f}


# Inline markup, as the engine's own length accounting sees it. The rules below
# were not guessed: they were fitted against every variant of every shipped
# scenario file and reproduce the stored display_length on 98,367/98,367 of
# them. Getting this wrong is silent — the text still renders, but the
# typewriter stops early or runs past the end of the line.
PAUSE = re.compile(r"%[a-zA-Z][^;]*;")     # %p; %p-1; — pause codes, not displayed
FURIGANA = re.compile(r"\[([^\]\[]*?)(?:,(\d+))?\]")   # [reading] / [reading,N]
ESCAPE = re.compile(re.escape("\\") + "(.)", re.S)     # \n line break, \# escape


def display_len(text: str) -> int:
    """The character count the engine stores alongside a line.

    Pause codes and furigana brackets are dropped, `\\n` counts as nothing and
    any other `\\X` escape counts as the escaped character alone. `<tips,N,…>`
    tags are the odd one out: they count *raw*, markup included.
    """
    plain = FURIGANA.sub("", PAUSE.sub("", text))
    return len(ESCAPE.sub(lambda m: "" if m.group(1) == "n" else m.group(1), plain))


def flat_form(text: str) -> str:
    """The `\\n`-free variant a line carries for the backlog and one-line views."""
    return text.replace("\\n", "")


def patch_one(packed_psb: bytes, name: str, fr: dict):
    """Return (new_psb_bytes, replaced, conflicts, lengths) for one .ks entry."""
    psb = Psb(packed_psb, track_strings=True, track_ints=True)
    langs = [l for l in (psb.root.get("languages") or []) if isinstance(l, str)]
    if "en" not in langs:
        return None, 0, 0, 0
    slot = 1 + langs.index("en")           # [0] is the Japanese original

    # A deduplicated string table means two lines with identical English share
    # one slot. Collect every French candidate per index and take the most
    # common; those lines already display identical English today, so one text
    # for both is no worse than what ships.
    wanted = collections.defaultdict(collections.Counter)
    variants = []
    for scene in psb.root.get("scenes") or []:
        if not isinstance(scene, dict):
            continue
        label = scene.get("label") or ""
        for i, entry in enumerate(scene.get("texts") or []):
            if not (isinstance(entry, list) and len(entry) > 1
                    and isinstance(entry[1], list)):
                continue
            if len(entry[1]) <= slot:
                continue
            v = entry[1][slot]
            if not (isinstance(v, list) and len(v) > 1 and isinstance(v[1], StrRef)):
                continue
            text = fr.get(f"{name}:{label}:{i}")
            if text:
                wanted[v[1].index][text] += 1
                variants.append(v)

    strings = psb.strings()
    conflicts = sum(1 for c in wanted.values() if len(c) > 1)
    winner = {idx: c.most_common(1)[0][0] for idx, c in wanted.items()}
    for idx, text in winner.items():
        strings[idx] = text

    # Both numbers below are poked into the entries tree in place. They keep
    # their original byte width, so the tree's internal offsets never move and
    # the string-table rebuild below stays valid.
    buf = bytearray(packed_psb)
    lengths = 0
    for v in variants:
        text = winner[v[1].index]
        if len(v) > 2 and isinstance(v[2], IntRef) and v[2].poke(buf, display_len(text)):
            lengths += 1
        flat = flat_form(text)
        for alt in v[3:]:
            if isinstance(alt, StrRef):
                strings[alt.index] = flat

    return rebuild_strings(bytes(buf), strings), len(wanted), conflicts, lengths


def build(game_dir):
    fr = load_fr()
    arc = Archive("scenario", game_dir)
    order = arc.names()                     # on-disk order

    body = bytearray()
    new_info = {}
    stats = dict(patched=0, copied=0, lines=0, conflicts=0, lengths=0)

    for name in order:
        off, length = arc.file_info[name]
        original_packed = arc.body[off:off + length]

        if name.endswith(".ks"):
            plain = arc.read(name)
            out, n, c, dl = patch_one(plain, name, fr)
            if out is not None and n:
                blob = wrap(out, SEED + name + arc.suffix)
                stats["patched"] += 1
                stats["lines"] += n
                stats["conflicts"] += c
                stats["lengths"] += dl
            else:
                blob = original_packed
                stats["copied"] += 1
        else:
            blob = original_packed          # never re-compressed: cannot corrupt
            stats["copied"] += 1

        new_info[name] = [len(body), len(blob)]
        body += blob

    index_name = "scenario_info.psb.m"
    with open(os.path.join(arc.game_dir, index_name), "rb") as f:
        raw_index = f.read()
    from mzs import unwrap
    plain_index = unwrap(raw_index, SEED + index_name)

    # The index's offsets and lengths are poked in place, never re-encoded.
    #
    # Re-encoding the tree is what broke the game for a whole evening: our
    # encoder picks the *minimum* byte width for each integer, while the game's
    # writes 61 of the offsets and 32 of the lengths one byte wider than they
    # need to be. The result parses identically and the game still loads most
    # entries from it — but it fails on some, and the failure is silent: the
    # scene transition just drops back to the title screen. Proven by shipping
    # an untouched body with nothing but a re-encoded index: same crash.
    #
    # In place, every value keeps the width the game gave it, so the tree stays
    # byte-for-byte what shipped and only the numbers move. `IntRef.poke`
    # refuses a value that would not fit, so an overflow is loud, not silent.
    idx = Psb(plain_index, track_ints=True)
    buf = bytearray(plain_index)
    for entry, (off_ref, len_ref) in idx.root["file_info"].items():
        want = new_info[entry]
        if not (off_ref.poke(buf, want[0]) and len_ref.poke(buf, want[1])):
            sys.exit(f"{entry}: offset/length no longer fits the index's own "
                     f"integer width — the archive grew past what it can address")
    new_index = bytes(buf)

    # Prove the patched index still parses and points where we think it does.
    check = Psb(new_index)
    assert check.root["file_info"] == new_info, "index patch failed"
    assert len(new_index) == len(plain_index), "index changed size"

    return bytes(body), wrap(new_index, SEED + index_name), stats


def cmd_restore(game_dir):
    missing = [t for t in TARGETS if not os.path.exists(os.path.join(BACKUP, t))]
    if missing:
        sys.exit(f"no backup for: {', '.join(missing)}")
    for t in TARGETS:
        shutil.copy2(os.path.join(BACKUP, t), os.path.join(game_dir, t))
        print(f"  restored {t}")
    print("originals restored.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--restore", action="store_true")
    ap.add_argument("--game-dir")
    args = ap.parse_args()

    game_dir = find_game_dir(args.game_dir)
    print(f"game: {game_dir}\n")

    if args.restore:
        cmd_restore(game_dir)
        return

    body, index, stats = build(game_dir)
    old_body = os.path.getsize(os.path.join(game_dir, "scenario_body.bin"))
    print(f"  scenarios patched : {stats['patched']}")
    print(f"  entries copied    : {stats['copied']}")
    print(f"  lines injected    : {stats['lines']:,}")
    print(f"  shared-slot lines : {stats['conflicts']}  (identical English today)")
    print(f"  lengths recomputed: {stats['lengths']:,}")
    print(f"  body.bin          : {old_body:,} -> {len(body):,} bytes "
          f"({(len(body) / old_body - 1) * 100:+.1f}%)")

    if args.dry_run:
        print("\ndry run — nothing written.")
        return

    os.makedirs(BACKUP, exist_ok=True)
    for t in TARGETS:
        src = os.path.join(game_dir, t)
        dst = os.path.join(BACKUP, t)
        if not os.path.exists(dst):
            shutil.copy2(src, dst)
            if sha256(src) != sha256(dst):
                sys.exit(f"backup of {t} does not match — aborting before any write")
            print(f"  backed up {t}")

    with open(os.path.join(game_dir, "scenario_body.bin"), "wb") as f:
        f.write(body)
    with open(os.path.join(game_dir, "scenario_info.psb.m"), "wb") as f:
        f.write(index)
    print("\npatch applied. Set the game's language to English to see French.")
    print("Undo with:  python inject.py --restore   (or Steam > Verify integrity)")


if __name__ == "__main__":
    main()
