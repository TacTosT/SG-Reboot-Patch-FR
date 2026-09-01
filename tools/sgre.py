"""Archive access for STEINS;GATE RE:BOOT (wind3d11data/*_info.psb.m + *_body.bin).

Each archive is an index PSB (itself mzs-shelled, key = SEED + index filename)
listing entries by name -> [offset, length] into the body. Every entry is
independently mzs-shelled with key = SEED + entry_name + expire_suffix.
"""
import os

from mzs import SEED, open_blob, unwrap
from psb import Psb

DEFAULT_GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\SGRE\wind3d11data"


def find_game_dir(explicit=None):
    if explicit:
        return explicit
    env = os.environ.get("SGRE_DIR")
    if env:
        return env
    return DEFAULT_GAME_DIR


class Archive:
    """One <kind>_info.psb.m / <kind>_body.bin pair."""

    def __init__(self, kind: str, game_dir=None):
        self.kind = kind
        self.game_dir = find_game_dir(game_dir)
        index_name = f"{kind}_info.psb.m"
        with open(os.path.join(self.game_dir, index_name), "rb") as f:
            raw = f.read()
        data = unwrap(raw, SEED + index_name)
        if data is None:
            raise RuntimeError(f"failed to decrypt {index_name} - wrong seed?")
        self.index = Psb(data)
        self.file_info = self.index.root.get("file_info") or {}
        self.suffix = next(
            (s for s in (self.index.root.get("expire_suffix_list") or []) if isinstance(s, str)), "")
        self._body_path = os.path.join(self.game_dir, f"{kind}_body.bin")
        self._body = None

    @property
    def body(self):
        if self._body is None:
            with open(self._body_path, "rb") as f:
                self._body = f.read()
        return self._body

    def names(self):
        """Entry names in on-disk order."""
        return [k for k, _ in sorted(self.file_info.items(), key=lambda kv: kv[1][0])]

    def read(self, name: str) -> bytes:
        off, length = self.file_info[name]
        blob = self.body[off:off + length]
        # Most archives key on name+suffix; entries that already carry their
        # own full extension (the font archive) key on the bare name.
        for key in (SEED + name + self.suffix, SEED + name):
            data = open_blob(blob, key)
            if data is not None:
                return data
        raise RuntimeError(f"failed to decrypt entry {name!r}")

    def psb(self, name: str) -> Psb:
        return Psb(self.read(name))
