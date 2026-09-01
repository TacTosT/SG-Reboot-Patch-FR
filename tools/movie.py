"""Movie files (wind3d11data/movie/*.webm) for STEINS;GATE RE:BOOT.

Unlike the `*_body.bin` archives these are **not** mzs-shelled: no `mzs\0`
header, no zstd, and the keystream cycles at **4096** bytes, not 131.

    key        = SEED + bare filename   (e.g. "…prologue01_en.webm")
    keystream  = MD5(key) -> MT19937 init_by_array -> LE uint32 stream
    cipher     = plaintext XOR keystream[i % 4096]   from byte 0

Recovered by known-plaintext against the WebM/EBML magic `1A 45 DF A3`; the
4096 cycle then fell out of the 154-byte Void element right after the
SeekHead, which is all zeros and therefore hands over the raw keystream.

Subtitles in these movies are **burned into the pixels** — that is why
`prologue01/02/03`, `fake_end` and `sgreboot_worldlinechange_pt01` each ship
four files (`.webm`, `_en`, `_sc`, `_tc`). The decrypted streams carry video
(+ audio) only, no subtitle track. The engine *does* have an unused overlay
path (`findMovieSubtitleData` in `script/savesystem` reads `movie/<name>.csv`,
`movie/<name>.json` or `config/<name>_subtitle.psb`), but this game ships no
such data.
"""
import hashlib
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mzs import SEED

MOVIE_KEYLEN = 4096


def keystream(name: str, keylen: int = MOVIE_KEYLEN) -> np.ndarray:
    seeds = np.frombuffer(hashlib.md5((SEED + name).encode("utf-8")).digest(), dtype="<u4")
    rs = np.random.RandomState(seeds)
    raw = np.asarray(rs._bit_generator.random_raw(keylen // 4 + 1), dtype="<u4").tobytes()
    return np.frombuffer(raw[:keylen], dtype=np.uint8)


def crypt(data: bytes, name: str) -> bytes:
    """XOR is its own inverse — the same call decrypts and re-encrypts."""
    ks = keystream(name)
    body = np.frombuffer(data, dtype=np.uint8)
    return (body ^ ks[np.arange(len(body)) % MOVIE_KEYLEN]).tobytes()


def convert(src: str, out: str, name: str = None) -> int:
    """Decrypt (or re-encrypt) `src` into `out`; `name` defaults to src's basename."""
    with open(src, "rb") as f:
        data = f.read()
    with open(out, "wb") as f:
        f.write(crypt(data, name or os.path.basename(src)))
    return len(data)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: movie.py <src.webm> <out.webm> [key-name]")
    print(convert(*sys.argv[1:]), "bytes")
