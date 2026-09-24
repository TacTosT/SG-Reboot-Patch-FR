"""Build and apply the French patch on a user's own copy of the game.

Nothing from the game is redistributed: the package ships only `all_fr.jsonl`
(the French lines) and rebuilds `scenario_body.bin` from the files already on
the player's disk.

French goes into the game's **English** language slot - the slot exists in
every scene and the engine already knows how to draw it, so no engine change is
needed. Play with the game set to English and the text is French.

  * `.ks` scenario entries - string table replaced, everything else byte-exact.
  * every other entry - copied over as its original *packed* bytes, never
    re-compressed, so it cannot be corrupted.
  * `scenario_info.psb.m` - offsets and lengths are poked in place, each
    keeping the byte width the game gave it. The tree is never re-encoded:
    a re-encoded index parses identically but the engine chokes on it.
"""
import collections
import contextlib
import hashlib
import json
import os
import re
import shutil
import time

from .mzs import SEED, open_blob, unwrap, wrap
from .psb import IntRef, Psb, StrRef
from .psb_write import rebuild_strings

TARGETS = ("scenario_info.psb.m", "scenario_body.bin")
BACKUP_DIRNAME = "_fr_backup"
STAMP = "patch_fr.json"

STEAM_VERIFY = ("Steam > clic droit sur le jeu > Propriétés > "
                "Fichiers installés > Vérifier l'intégrité des fichiers.")
NEED_ADMIN = ("Impossible d'écrire dans le dossier du jeu.\n\n"
              "Fermez le jeu s'il est ouvert. Sinon, relancez ce programme en "
              "tant qu'administrateur (clic droit > Exécuter en tant "
              "qu'administrateur).")


class PatchError(Exception):
    """Something the user needs to read, phrased for a player, not a dev."""


class Cancelled(Exception):
    pass


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def backup_dir(game_dir):
    return os.path.join(game_dir, BACKUP_DIRNAME)


def has_backup(game_dir):
    return all(os.path.isfile(os.path.join(backup_dir(game_dir), t)) for t in TARGETS)


def read_stamp(game_dir):
    try:
        with open(os.path.join(backup_dir(game_dir), STAMP), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def load_fr(fr_path):
    out = {}
    with open(fr_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                out[rec["id"]] = rec["fr"]
    return out


class Archive:
    """One <kind>_info.psb.m / <kind>_body.bin pair, read from `src_dir`."""

    def __init__(self, kind, src_dir):
        self.kind = kind
        self.src_dir = src_dir
        self.index_name = kind + "_info.psb.m"
        with open(os.path.join(src_dir, self.index_name), "rb") as f:
            self.raw_index = f.read()
        data = unwrap(self.raw_index, SEED + self.index_name)
        if data is None:
            raise PatchError(
                "Impossible de lire les fichiers du jeu : "
                + self.index_name + " n'a pas pu être déchiffré.\n"
                "Le jeu a peut-être été mis à jour, ou ses fichiers sont déjà "
                "modifiés par un autre patch.")
        self.plain_index = data
        self.index = Psb(data)
        self.file_info = self.index.root.get("file_info") or {}
        self.suffix = next((s for s in (self.index.root.get("expire_suffix_list") or [])
                            if isinstance(s, str)), "")
        with open(os.path.join(src_dir, kind + "_body.bin"), "rb") as f:
            self.body = f.read()

    def names(self):
        """Entry names in on-disk order."""
        return [k for k, _ in sorted(self.file_info.items(), key=lambda kv: kv[1][0])]

    def packed(self, name):
        off, length = self.file_info[name]
        return self.body[off:off + length]

    def read(self, name):
        blob = self.packed(name)
        # Most archives key on name+suffix; entries carrying their own full
        # extension key on the bare name.
        for key in (SEED + name + self.suffix, SEED + name):
            data = open_blob(blob, key)
            if data is not None:
                return data
        raise PatchError("Entrée illisible dans l'archive : " + name)


# Inline markup, as the engine's own length accounting sees it. Fitted against
# every variant of every shipped scenario file: reproduces the stored
# display_length on 98,367/98,367 of them. Keep in step with inject.py.
PAUSE = re.compile(r"%[a-zA-Z][^;]*;")                  # %p; %p-1; — not displayed
FURIGANA = re.compile(r"\[([^\]\[]*?)(?:,(\d+))?\]")    # [reading] / [reading,N]
ESCAPE = re.compile(re.escape("\\") + "(.)", re.S)      # \n line break, \# escape


def display_len(text):
    """The character count the engine stores alongside a line.

    Pause codes and furigana brackets drop out, `\\n` counts as nothing, any
    other `\\X` counts as the escaped character alone, and `<tips,N,...>` tags
    count raw — markup included.
    """
    plain = FURIGANA.sub("", PAUSE.sub("", text))
    return len(ESCAPE.sub(lambda m: "" if m.group(1) == "n" else m.group(1), plain))


def flat_form(text):
    """The `\\n`-free variant a line carries for the backlog and one-line views."""
    return text.replace("\\n", "")


def patch_one(packed_psb, name, fr):
    """Return (new_psb_bytes, replaced, conflicts, lengths) for one .ks entry."""
    psb = Psb(packed_psb, track_strings=True, track_ints=True)
    langs = [l for l in (psb.root.get("languages") or []) if isinstance(l, str)]
    if "en" not in langs:
        return None, 0, 0, 0
    slot = 1 + langs.index("en")            # [0] is the Japanese original

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
            text = fr.get(name + ":" + (label or "") + ":" + str(i))
            if text:
                wanted[v[1].index][text] += 1
                variants.append(v)

    if not wanted:
        return None, 0, 0, 0

    strings = psb.strings()
    conflicts = sum(1 for c in wanted.values() if len(c) > 1)
    winner = {}
    for idx, counter in wanted.items():
        winner[idx] = counter.most_common(1)[0][0]
        strings[idx] = winner[idx]

    # display_length is poked into the entries tree in place, keeping its
    # original byte width, so the tree's internal offsets never move and the
    # string-table rebuild below stays valid.
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


def build(src_dir, fr_path, progress=None, should_stop=None):
    """Rebuild body + index from `src_dir`. Returns (body, index, stats)."""
    def tick(frac, message):
        if should_stop and should_stop():
            raise Cancelled()
        if progress:
            progress(frac, message)

    tick(0.0, "Lecture des traductions...")
    fr = load_fr(fr_path)

    tick(0.03, "Ouverture de l'archive du jeu...")
    arc = Archive("scenario", src_dir)
    order = arc.names()

    body = bytearray()
    new_info = {}
    stats = dict(patched=0, copied=0, lines=0, conflicts=0, lengths=0)

    for n, name in enumerate(order):
        original_packed = arc.packed(name)
        if name.endswith(".ks"):
            out, count, conf, dlen = patch_one(arc.read(name), name, fr)
            if out is not None:
                blob = wrap(out, SEED + name + arc.suffix)
                stats["patched"] += 1
                stats["lines"] += count
                stats["conflicts"] += conf
                stats["lengths"] += dlen
            else:
                blob = original_packed
                stats["copied"] += 1
        else:
            blob = original_packed          # never re-compressed: cannot corrupt
            stats["copied"] += 1
        new_info[name] = [len(body), len(blob)]
        body += blob
        tick(0.05 + 0.9 * (n + 1) / len(order),
             "Traduction des scénarios... {}/{}".format(n + 1, len(order)))

    tick(0.96, "Mise à jour de l'index...")
    # The offsets and lengths are poked in place, never re-encoded. Our encoder
    # picks the minimum byte width per integer; the game's writer pads many of
    # them one byte wider. A re-encoded index parses identically and still
    # loads most entries, but some scene transitions then fail and drop
    # silently back to the title screen. Keep every integer at its own width.
    idx = Psb(arc.plain_index, track_ints=True)
    buf = bytearray(arc.plain_index)
    for entry, (off_ref, len_ref) in idx.root["file_info"].items():
        want = new_info[entry]
        if not (off_ref.poke(buf, want[0]) and len_ref.poke(buf, want[1])):
            raise PatchError("L'archive dépasse ce que son index peut adresser. "
                             "Rien n'a été écrit.")
    new_index = bytes(buf)

    # Prove the patched index still parses and points where we think it does.
    check = Psb(new_index)
    if check.root["file_info"] != new_info or len(new_index) != len(arc.plain_index):
        raise PatchError("Vérification interne échouée (index). Rien n'a été écrit.")

    tick(0.99, "Compression finale...")
    return bytes(body), wrap(new_index, SEED + arc.index_name), stats


def same_file(a, b):
    """Cheap equality: size first, hash only if the sizes agree."""
    try:
        if os.path.getsize(a) != os.path.getsize(b):
            return False
        return sha256(a) == sha256(b)
    except OSError:
        return False


def status(game_dir, fr_path=None):
    """'installed' | 'original' | 'unknown' - cheap, no rebuild."""
    if not has_backup(game_dir):
        return "original"
    body = os.path.join(game_dir, "scenario_body.bin")
    stamp = read_stamp(game_dir)
    if stamp:
        try:
            cur = sha256(body)
        except OSError:
            return "unknown"
        if cur == stamp.get("patched_sha"):
            return "installed"
        if cur == stamp.get("original_sha"):
            return "original"
        return "unknown"
    # Backup but no stamp (restored, or the stamp was deleted by hand).
    return "original" if same_file(body, os.path.join(backup_dir(game_dir),
                                                      "scenario_body.bin")) else "unknown"


def _check_writable(game_dir):
    # Only catches a read-only folder on Windows, not missing permissions:
    # `_writing` below handles those when the write is actually refused.
    if not os.access(game_dir, os.W_OK):
        raise PatchError(NEED_ADMIN)


@contextlib.contextmanager
def _writing():
    """Turn a refused write into a message the player can act on."""
    try:
        yield
    except PermissionError:
        raise PatchError(NEED_ADMIN) from None


def _backup_ok(game_dir):
    """True if the backup holds the originals of the files now on disk.

    False after a game update (the backup is last version's) or if the backup
    no longer matches the hash noted when it was made.
    """
    if not has_backup(game_dir) or status(game_dir) == "unknown":
        return False
    stamp = read_stamp(game_dir)
    return not stamp or stamp.get("original_sha") == sha256(
        os.path.join(backup_dir(game_dir), "scenario_body.bin"))


def _save_backup(game_dir, say):
    """Copy the live files into the backup, each one verified before it lands."""
    bdir = backup_dir(game_dir)
    os.makedirs(bdir, exist_ok=True)
    for t in TARGETS:
        source = os.path.join(game_dir, t)
        tmp = os.path.join(bdir, t + ".fr_tmp")
        shutil.copyfile(source, tmp)
        if sha256(source) != sha256(tmp):
            os.remove(tmp)
            raise PatchError("La sauvegarde de " + t + " a échoué. Rien n'a été modifié.")
        os.replace(tmp, os.path.join(bdir, t))
        say("Sauvegarde : " + t)


def _write_stamp(game_dir, data):
    path = os.path.join(backup_dir(game_dir), STAMP)
    with open(path + ".fr_tmp", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(path + ".fr_tmp", path)


def _replace_together(game_dir, files, say):
    """Put body and index in place as one step, as far as the disk allows.

    The two files only make sense as a pair: a French body with the original
    index (or the reverse) is a broken game. So every new file is written in
    full next to its target first, and only then are they renamed into place,
    back to back. A crash while writing leaves the game untouched.

    `files` is a list of (target name, bytes or path of a file to copy).
    """
    tmps = []
    try:
        for target, content in files:
            tmp = os.path.join(game_dir, target + ".fr_tmp")
            tmps.append(tmp)
            if isinstance(content, bytes):
                with open(tmp, "wb") as f:
                    f.write(content)
            else:
                shutil.copyfile(content, tmp)
        for (target, _), tmp in zip(files, tmps):
            os.replace(tmp, os.path.join(game_dir, target))
            say("Écrit : " + target)
    finally:
        for tmp in tmps:
            try:
                os.remove(tmp)
            except OSError:
                pass


def install(game_dir, fr_path, progress=None, should_stop=None, log=None):
    """Patch the game. Idempotent: re-running rebuilds from the backup."""
    def say(msg):
        if log:
            log(msg)

    _check_writable(game_dir)
    current_body = os.path.join(game_dir, "scenario_body.bin")

    # Is the existing backup still the original of *these* game files? If the
    # game was updated under us, the old backup holds last version's scenarios
    # and rebuilding from it would quietly reinstate them.
    fresh_backup = _backup_ok(game_dir)
    if fresh_backup:
        say("Sauvegarde d'origine trouvée : reconstruction à partir des fichiers d'origine.")
    elif has_backup(game_dir):
        say("Les fichiers du jeu ont changé depuis la dernière sauvegarde "
            "(mise à jour du jeu ?) : une nouvelle sauvegarde va être faite.")

    src = backup_dir(game_dir) if fresh_backup else game_dir
    body, index, stats = build(src, fr_path, progress, should_stop)

    # Building from the live files and getting them back unchanged means they
    # are already French - so there is no original here to save.
    if not fresh_backup and (os.path.getsize(current_body) == len(body)
                             and sha256(current_body) == hashlib.sha256(body).hexdigest()):
        raise PatchError(
            "Le patch est déjà installé sur cette copie du jeu, mais aucune "
            "sauvegarde utilisable des fichiers d'origine n'a été trouvée.\n\n"
            "Pour revenir à l'anglais : " + STEAM_VERIFY)

    with _writing():
        if not fresh_backup:
            _save_backup(game_dir, say)
        # The stamp goes down *before* the swap. Stopped before it, the files
        # on disk still match `original_sha` and read as untouched; after it,
        # they match `patched_sha`. The status is right either way.
        _write_stamp(game_dir, {
            "patch": "STEINS;GATE RE:BOOT — traduction française",
            "installed": time.strftime("%Y-%m-%d %H:%M:%S"),
            "lines": stats["lines"],
            "patched_sha": hashlib.sha256(body).hexdigest(),
            "original_sha": sha256(os.path.join(backup_dir(game_dir), "scenario_body.bin")),
        })
        _replace_together(game_dir, [("scenario_body.bin", body),
                                     ("scenario_info.psb.m", index)], say)
    return stats


def uninstall(game_dir, log=None):
    """Put the original files back - only if they really are the originals.

    The backup is only restored over files this patch wrote. After a game
    update it holds last version's scenarios, and restoring it would mix two
    versions of the game.
    """
    def say(msg):
        if log:
            log(msg)

    if not has_backup(game_dir):
        raise PatchError("Aucune sauvegarde trouvée dans ce dossier.\n\n"
                         "Pour revenir à l'anglais : " + STEAM_VERIFY)
    state = status(game_dir)
    if state == "original":
        raise PatchError("Le jeu est déjà en version d'origine : rien à restaurer.")
    if state != "installed":
        raise PatchError(
            "Les fichiers du jeu ont changé depuis l'installation du patch "
            "(mise à jour du jeu ?). Restaurer l'ancienne sauvegarde abîmerait "
            "le jeu : rien n'a été modifié.\n\n"
            "Pour revenir à l'anglais : " + STEAM_VERIFY)
    if not _backup_ok(game_dir):
        raise PatchError("La sauvegarde des fichiers d'origine est endommagée : "
                         "rien n'a été modifié.\n\n"
                         "Pour revenir à l'anglais : " + STEAM_VERIFY)

    _check_writable(game_dir)
    bdir = backup_dir(game_dir)
    with _writing():
        _replace_together(game_dir, [(t, os.path.join(bdir, t)) for t in TARGETS], say)
        os.remove(os.path.join(bdir, STAMP))
