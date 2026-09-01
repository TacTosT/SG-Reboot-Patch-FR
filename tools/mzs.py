"""MZS shell (mzs\\0) for STEINS;GATE RE:BOOT: XOR(MT19937) + Zstandard.

Key derivation, per FreeMote's PsbExtension.EncodeMdf:
    MD5(key) -> 4 little-endian uint32 -> MT19937 init_by_array
    -> little-endian uint32 keystream, cycled at `keylen`
    -> XOR over everything past the 8-byte mzs header.

The seed below was recovered by a known-plaintext attack: the decrypted
payload must begin with the Zstandard magic 28 B5 2F FD, which pins the
first MT19937 output and lets candidate keys be tested without the game
ever running. Verified against all nine *_info.psb.m files.
"""
import hashlib
import struct

import numpy as np
import zstandard

SEED = "Rk3nwA8ZYV0yV"
KEYLEN = 131
ZSTD_MAGIC = bytes([0x28, 0xB5, 0x2F, 0xFD])
MZS_MAGIC = b"mzs\0"


def keystream(key: str, keylen: int = KEYLEN) -> bytes:
    seeds = np.frombuffer(hashlib.md5(key.encode("utf-8")).digest(), dtype="<u4")
    rs = np.random.RandomState(seeds)
    raw = rs._bit_generator.random_raw(keylen // 4 + 1)
    return np.asarray(raw, dtype="<u4").tobytes()[:keylen]


def decrypt(blob: bytes, key: str, keylen: int = KEYLEN) -> bytes:
    ks = np.frombuffer(keystream(key, keylen), dtype=np.uint8)
    body = np.frombuffer(blob[8:], dtype=np.uint8)
    return blob[:8] + (body ^ ks[np.arange(len(body)) % len(ks)]).tobytes()


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

    The header itself is never XORed — decryption skips the first 8 bytes — so
    it is written after the payload is encrypted.

    Level 19 because that is roughly what the game itself used: recompressing
    the shipped entries lands between level 19 and 22, and the earlier default
    of 12 inflated `scenario_body.bin` by 1.4 MB over the original. At 19 the
    French body comes out *smaller* than the stock one, so the patch never
    grows the archive.
    """
    comp = zstandard.ZstdCompressor(level=level).compress(data)
    ks = np.frombuffer(keystream(key, keylen), dtype=np.uint8)
    body = np.frombuffer(comp, dtype=np.uint8)
    enc = (body ^ ks[np.arange(len(body)) % len(ks)]).tobytes()
    return MZS_MAGIC + struct.pack("<I", len(data)) + enc


def open_blob(blob: bytes, key: str):
    """Unwrap if shelled, pass through if the entry is stored raw."""
    if blob[:4] != MZS_MAGIC:
        return blob
    return unwrap(blob, key)
