"""MZS shell (mzs\0) for STEINS;GATE RE:BOOT: XOR(MT19937) + Zstandard.

Same algorithm as ../../tools/mzs.py, with MT19937 written out in pure Python
instead of borrowing numpy's RandomState. The keystream is byte-identical
(checked against numpy for several keys and key lengths); dropping numpy keeps
the redistributable .exe small and the build reproducible.

Key derivation, per FreeMote's PsbExtension.EncodeMdf:
    MD5(key) -> 4 little-endian uint32 -> MT19937 init_by_array
    -> little-endian uint32 keystream, cycled at `keylen`
    -> XOR over everything past the 8-byte mzs header.
"""
import hashlib
import struct

import zstandard

SEED = "Rk3nwA8ZYV0yV"
KEYLEN = 131
ZSTD_MAGIC = bytes([0x28, 0xB5, 0x2F, 0xFD])
MZS_MAGIC = b"mzs\0"

_N, _M = 624, 397
_MATRIX_A, _UPPER, _LOWER = 0x9908B0DF, 0x80000000, 0x7FFFFFFF
_MASK = 0xFFFFFFFF


class _MT19937:
    """Reference MT19937 seeded through init_by_array, as numpy seeds it."""

    def __init__(self, key):
        mt = [0] * _N
        mt[0] = 19650218
        for i in range(1, _N):
            mt[i] = (1812433253 * (mt[i - 1] ^ (mt[i - 1] >> 30)) + i) & _MASK
        i, j = 1, 0
        for _ in range(max(_N, len(key))):
            mt[i] = ((mt[i] ^ ((mt[i - 1] ^ (mt[i - 1] >> 30)) * 1664525))
                     + key[j] + j) & _MASK
            i, j = i + 1, j + 1
            if i >= _N:
                mt[0] = mt[_N - 1]
                i = 1
            if j >= len(key):
                j = 0
        for _ in range(_N - 1):
            mt[i] = ((mt[i] ^ ((mt[i - 1] ^ (mt[i - 1] >> 30)) * 1566083941))
                     - i) & _MASK
            i += 1
            if i >= _N:
                mt[0] = mt[_N - 1]
                i = 1
        mt[0] = _UPPER
        self.mt = mt
        self.idx = _N

    def _twist(self):
        mt = self.mt
        for k in range(_N - _M):
            y = (mt[k] & _UPPER) | (mt[k + 1] & _LOWER)
            mt[k] = mt[k + _M] ^ (y >> 1) ^ (_MATRIX_A if y & 1 else 0)
        for k in range(_N - _M, _N - 1):
            y = (mt[k] & _UPPER) | (mt[k + 1] & _LOWER)
            mt[k] = mt[k + (_M - _N)] ^ (y >> 1) ^ (_MATRIX_A if y & 1 else 0)
        y = (mt[_N - 1] & _UPPER) | (mt[0] & _LOWER)
        mt[_N - 1] = mt[_M - 1] ^ (y >> 1) ^ (_MATRIX_A if y & 1 else 0)
        self.idx = 0

    def next_uint32(self):
        if self.idx >= _N:
            self._twist()
        y = self.mt[self.idx]
        self.idx += 1
        y ^= y >> 11
        y ^= (y << 7) & 0x9D2C5680
        y ^= (y << 15) & 0xEFC60000
        y ^= y >> 18
        return y & _MASK


_ks_cache = {}


def keystream(key: str, keylen: int = KEYLEN) -> bytes:
    cached = _ks_cache.get((key, keylen))
    if cached is not None:
        return cached
    seeds = struct.unpack("<4I", hashlib.md5(key.encode("utf-8")).digest())
    mt = _MT19937(seeds)
    raw = b"".join(struct.pack("<I", mt.next_uint32())
                   for _ in range(keylen // 4 + 1))[:keylen]
    _ks_cache[(key, keylen)] = raw
    return raw


def _xor(body: bytes, ks: bytes) -> bytes:
    """XOR a blob against a cycling key. Big-int XOR beats a Python loop by
    orders of magnitude on the 24 MB body."""
    n = len(body)
    if n == 0:
        return b""
    pad = (ks * (n // len(ks) + 1))[:n]
    return (int.from_bytes(body, "big") ^ int.from_bytes(pad, "big")).to_bytes(n, "big")


def decrypt(blob: bytes, key: str, keylen: int = KEYLEN) -> bytes:
    return blob[:8] + _xor(blob[8:], keystream(key, keylen))


def unwrap(blob: bytes, key: str, keylen: int = KEYLEN):
    """Decrypt + zstd-decompress an mzs blob. Returns None if the key is wrong."""
    dec = decrypt(blob, key, keylen)
    if dec[8:12] != ZSTD_MAGIC:
        return None
    claimed = struct.unpack("<I", dec[4:8])[0]
    try:
        out = zstandard.ZstdDecompressor().decompress(dec[8:], max_output_size=claimed)
    except Exception:
        return None
    return out if len(out) == claimed else None


def wrap(data: bytes, key: str, keylen: int = KEYLEN, level: int = 19) -> bytes:
    """Inverse of unwrap: zstd-compress, XOR, prepend the 8-byte mzs header.

    The header itself is never XORed - decryption skips the first 8 bytes - so
    it is written after the payload is encrypted.

    Level 19 matches what the game itself used; the earlier default of 12
    inflated scenario_body.bin by 1.4 MB over the original. Keep in step with
    tools/mzs.py.
    """
    comp = zstandard.ZstdCompressor(level=level).compress(data)
    return MZS_MAGIC + struct.pack("<I", len(data)) + _xor(comp, keystream(key, keylen))


def open_blob(blob: bytes, key: str):
    """Unwrap if shelled, pass through if the entry is stored raw."""
    if blob[:4] != MZS_MAGIC:
        return blob
    return unwrap(blob, key)
