"""Surgical rewrite of a PSB's string table, leaving everything else byte-exact.

A full PSB encoder is not needed here, and would be riskier. In the scenario
files the section order is always

    header | names | entries | str_offsets | str_data | chunk_*

so the value tree (`entries`) — the part with fragile internal relative offsets
— sits *before* the strings and never moves. Entries reference strings by
index, not by offset, so as long as the string count is unchanged the tree
stays valid verbatim. Only the two string sections are rebuilt, the chunk
sections shift by a known delta, and the header offsets plus its Adler32 are
recomputed.

Verified by round-tripping every scenario file with its own strings and
comparing byte-for-byte against the original.
"""
import struct
import zlib


def byte_width(value: int) -> int:
    """Minimum little-endian byte count for an unsigned value (never 0)."""
    width = 0
    while value:
        width += 1
        value >>= 8
    return max(width, 1)


def encode_array(values) -> bytes:
    """PsbArray: [0x0C+n][count:n][0x0C+m][value:m]*count."""
    count = len(values)
    nw = byte_width(count)
    out = bytearray()
    out.append(0x0C + nw)
    out += count.to_bytes(nw, "little")
    if count == 0:
        out.append(0x0D)          # entry-width byte; the reader consumes it
        return bytes(out)
    mw = byte_width(max(values))
    out.append(0x0C + mw)
    for v in values:
        out += v.to_bytes(mw, "little")
    return bytes(out)


def encode_value(value, name_index, string_index) -> bytes:
    """Serialize one PSB value. Mirrors Psb._value exactly.

    Container offsets are relative to the byte *after* the offset array, so a
    container can be built children-first with no circular sizing problem.
    """
    if value is None:
        return b"\x01"
    if value is True:
        return b"\x03"
    if value is False:
        return b"\x02"
    if isinstance(value, int):
        if value == 0:
            return b"\x04"
        w = byte_width(value)
        return bytes([0x04 + w]) + value.to_bytes(w, "little")
    if isinstance(value, float):
        if value == 0.0:
            return b"\x1D"
        return b"\x1F" + struct.pack("<d", value)
    if isinstance(value, str):
        idx = string_index[value]
        w = byte_width(idx) if idx else 1
        return bytes([0x14 + w]) + idx.to_bytes(w, "little")
    if isinstance(value, list):
        parts = [encode_value(v, name_index, string_index) for v in value]
        offs, cur = [], 0
        for p in parts:
            offs.append(cur)
            cur += len(p)
        return b"\x20" + encode_array(offs) + b"".join(parts)
    if isinstance(value, dict):
        keys = list(value.keys())
        parts = [encode_value(value[k], name_index, string_index) for k in keys]
        offs, cur = [], 0
        for p in parts:
            offs.append(cur)
            cur += len(p)
        return (b"\x21" + encode_array([name_index[k] for k in keys])
                + encode_array(offs) + b"".join(parts))
    raise TypeError(f"cannot encode {type(value).__name__}: {value!r}")


def rebuild_entries(data: bytes, root, name_index, string_index) -> bytes:
    """Replace the entries tree. Names and strings are reused unchanged, so
    only the sections after `entries` shift.

    ⚠️ DO NOT use this on the archive index. `encode_value` picks the minimum
    byte width for every integer; the game's own writer pads many of them one
    byte wider (in `scenario_info.psb.m`, 61 offsets and 32 lengths, plus a
    float32 where we would write a float64). The result parses identically and
    the engine loads most entries from it, but some scene transitions then fail
    and drop silently back to the title screen — verified by shipping an
    untouched body with nothing but a re-encoded index.

    Poke the numbers in place instead, keeping each one's original width; see
    `IntRef.poke` and the index handling in `inject.py`.
    """
    hl, onm, ost, osd, oco, ocl, ocd, oen = struct.unpack_from("<8I", data, 8)
    tree = encode_value(root, name_index, string_index)
    delta = (oen + len(tree)) - ost

    out = bytearray(data[:oen]) + tree + data[ost:]
    struct.pack_into("<8I", out, 8, hl, onm, ost + delta, osd + delta,
                     oco + delta, ocl + delta, ocd + delta, oen)
    struct.pack_into("<I", out, 0x28, zlib.adler32(bytes(out[8:0x28])) & 0xFFFFFFFF)
    return bytes(out)


def rebuild_strings(data: bytes, strings) -> bytes:
    """Return `data` with its string table replaced by `strings` (same count)."""
    hl, onm, ost, osd, oco, ocl, ocd, oen = struct.unpack_from("<8I", data, 8)

    blob = bytearray()
    offsets = []
    for s in strings:
        offsets.append(len(blob))
        blob += s.encode("utf-8") + b"\0"

    arr = encode_array(offsets)
    new_osd = ost + len(arr)
    new_oco = new_osd + len(blob)
    delta = new_oco - oco

    out = bytearray(data[:ost]) + arr + blob + data[oco:]
    struct.pack_into("<8I", out, 8, hl, onm, ost, new_osd,
                     new_oco, ocl + delta, ocd + delta, oen)
    # v3+ carries an Adler32 over the eight offsets. FreeMote notes it is not
    # always checked on v3 but always on v4 — cheap to keep correct.
    struct.pack_into("<I", out, 0x28, zlib.adler32(bytes(out[8:0x28])) & 0xFFFFFFFF)
    return bytes(out)
