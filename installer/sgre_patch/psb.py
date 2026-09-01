"""Minimal reader for PSB (M2 Packaged Struct Binary), versions 2-4.

Follows FreeMote's Psb.cs. Read-only: enough to walk an archive index and a
compiled .ks scene tree.
"""
import io
import struct


class StrRef(str):
    """A resolved string that remembers which table slot it came from.

    Subclasses str so every existing reader keeps working unchanged, while
    reinjection can walk the same tree and learn *which* table entry to
    overwrite. Without this the index is lost at parse time and the only way
    back is a full PSB re-encode.
    """
    __slots__ = ("index",)

    def __new__(cls, value, index):
        obj = super().__new__(cls, value)
        obj.index = index
        return obj


class IntRef(int):
    """An integer that remembers where it sits in the file, and how wide it is.

    PSB writes an integer as one type byte (0x04 + width) then `width`
    little-endian bytes, so a value can be rewritten *in place* as long as it
    still fits the width it was written with. That is the only safe way to
    change a number: the entries tree is full of relative offsets, and any
    size change invalidates every one of them.

    No `__slots__` here: CPython rejects a non-empty one on an int subclass.
    """

    def __new__(cls, value, offset, width):
        obj = super().__new__(cls, value)
        obj.offset = offset
        obj.width = width
        return obj

    def fits(self, value: int) -> bool:
        if self.width == 0:
            return value == 0
        return 0 <= value < (1 << (8 * self.width))

    def poke(self, buf: bytearray, value: int) -> bool:
        """Write `value` over this integer in `buf`. False if it does not fit."""
        if not self.fits(value):
            return False
        if self.width:
            buf[self.offset:self.offset + self.width] = value.to_bytes(self.width, "little")
        return True


class Psb:
    def __init__(self, data: bytes, track_strings: bool = False, track_ints: bool = False):
        self.data = data
        self.track_strings = track_strings
        self.track_ints = track_ints
        if data[:4] != b"PSB\0":
            raise ValueError(f"not a PSB: {data[:4]!r}")
        self.version, self.header_encrypt = struct.unpack_from("<HH", data, 4)
        if self.header_encrypt != 0:
            raise NotImplementedError("PSB header is encrypted (needs a PSB uint key)")
        (self.header_length, self.off_names, self.off_strings, self.off_strings_data,
         self.off_chunk_offsets, self.off_chunk_lengths, self.off_chunk_data,
         self.off_entries) = struct.unpack_from("<8I", data, 8)

        f = io.BytesIO(data)
        f.seek(self.off_names)
        charset, names_data, name_indexes = self._array(f), self._array(f), self._array(f)
        self.names = self._load_names(charset, names_data, name_indexes)

        f.seek(self.off_strings)
        self.string_offsets = self._array(f)
        f.seek(self.off_chunk_offsets)
        self.chunk_offsets = self._array(f)
        f.seek(self.off_chunk_lengths)
        self.chunk_lengths = self._array(f)

        f.seek(self.off_entries)
        self.root = self._value(f)

    @staticmethod
    def _array(f):
        n = f.read(1)[0] - 0x0C
        count = int.from_bytes(f.read(n), "little") if n > 0 else 0
        if count == 0:
            f.read(1)
            return []
        m = f.read(1)[0] - 0x0C
        raw = f.read(count * m)
        return [int.from_bytes(raw[i * m:(i + 1) * m], "little") for i in range(count)]

    @staticmethod
    def _load_names(charset, names_data, name_indexes):
        """Walk the compressed name trie backwards, one character per hop."""
        names = []
        for index in name_indexes:
            out = bytearray()
            cur = names_data[index]
            while cur != 0:
                parent = names_data[cur]
                out.append(cur - charset[parent])
                cur = parent
            out.reverse()
            names.append(out.decode("utf-8", "replace"))
        return names

    def _string(self, idx):
        start = self.off_strings_data + self.string_offsets[idx]
        text = self.data[start:self.data.index(b"\0", start)].decode("utf-8", "replace")
        return StrRef(text, idx) if self.track_strings else text

    def strings(self):
        """The whole string table, in index order."""
        return [self._string(i) for i in range(len(self.string_offsets))]

    def _value(self, f):
        t = f.read(1)[0]
        if t in (0x00, 0x01):
            return None
        if t == 0x02:
            return False
        if t == 0x03:
            return True
        if t == 0x04:
            return IntRef(0, f.tell(), 0) if self.track_ints else 0
        if 0x05 <= t <= 0x0C:
            at = f.tell()
            value = int.from_bytes(f.read(t - 4), "little")
            return IntRef(value, at, t - 4) if self.track_ints else value
        if 0x0D <= t <= 0x14:
            f.seek(-1, io.SEEK_CUR)
            return self._array(f)
        if 0x15 <= t <= 0x18:
            return self._string(int.from_bytes(f.read(t - 0x14), "little"))
        if 0x19 <= t <= 0x1C:
            return {"__resource__": int.from_bytes(f.read(t - 0x18), "little")}
        if t == 0x1D:
            return 0.0
        if t == 0x1E:
            return struct.unpack("<f", f.read(4))[0]
        if t == 0x1F:
            return struct.unpack("<d", f.read(8))[0]
        if t == 0x20:                                   # list
            offsets = self._array(f)
            base = f.tell()
            out = []
            for off in offsets:
                f.seek(base + off)
                out.append(self._value(f))
            return out
        if t == 0x21:                                   # dict
            keys, offsets = self._array(f), self._array(f)
            base = f.tell()
            out = {}
            for k, off in zip(keys, offsets):
                f.seek(base + off)
                out[self.names[k]] = self._value(f)
            return out
        if 0x22 <= t <= 0x25:                           # extra chunk (v4)
            return {"__extra__": int.from_bytes(f.read(t - 0x21), "little")}
        raise ValueError(f"unknown PSB type 0x{t:02x} at offset {f.tell() - 1}")

    def resource(self, idx):
        start = self.off_chunk_data + self.chunk_offsets[idx]
        return self.data[start:start + self.chunk_lengths[idx]]
