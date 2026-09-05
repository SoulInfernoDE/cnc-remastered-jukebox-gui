# -*- coding: utf-8 -*-
"""Loads the game's own textures into Qt images.

The jukebox textures are uncompressed 32-bit DDS whose channel masks
(R=0x00ff0000, G=0x0000ff00, B=0x000000ff, A=0xff000000) describe exactly the
memory layout of QImage.Format_ARGB32, so the pixel block after the 128-byte
header can be handed to Qt as-is.  Compressed textures are not handled; the
jukebox does not use any.

Nothing is cached to disk - the textures live only in the running process.
"""

import struct

from PyQt5.QtGui import QImage

DDS_MAGIC = b"DDS "
HEADER = 128


class TextureError(Exception):
    pass


def load_dds(data):
    """Uncompressed 32-bit DDS -> QImage (a private copy, safe to keep)."""
    if data[:4] != DDS_MAGIC:
        raise TextureError("not a DDS file")
    height, width = struct.unpack_from("<II", data, 12)
    pf_flags, fourcc, bits = struct.unpack_from("<I4sI", data, 80)
    if fourcc.strip(b"\x00"):
        raise TextureError("compressed DDS (%s) is not supported" % fourcc.decode("ascii", "replace"))
    if bits != 32:
        raise TextureError("%d-bit DDS is not supported" % bits)
    need = width * height * 4
    if len(data) - HEADER < need:
        raise TextureError("DDS payload truncated")
    img = QImage(data[HEADER:HEADER + need], width, height,
                 width * 4, QImage.Format_ARGB32)
    # QImage does not own the buffer above; copy so the bytes may be released.
    return img.copy()


class Textures(object):
    """Pulls the jukebox skin out of TEXTURES_SRGB.MEG on demand."""

    # skin -> (background, scanline overlay)
    SKINS = {
        "td":     ("UI_JUKEBOX_BG", "UI_JUKEBOX_SCANLINES"),
        "soviet": ("RA_UI_JUKEBOXBG_SOVIET", "RA_JUKEBOX_BG_SCANLINESRED"),
        "allied": ("RA_UI_JUKEBOXBG_ALLIED", "RA_JUKEBOX_BG_SCANLINESBLUE"),
    }
    ICONS = {"Tiberian_Dawn": "UI_JUKEBOX_CNCTD_ICON",
             "Red_Alert": "UI_JUKEBOX_CNCRA_ICON"}
    # The layouts put a full-screen Background behind the frame; the Tiberian
    # Dawn panels are transparent and rely on it showing through.
    MENU_BG = {"td": "UI_MAINMENUBG_01", "soviet": "UI_RA_MENU_BG",
               "allied": "UI_RA_MENU_BG"}

    def __init__(self, meg):
        self._meg = meg
        self._cache = {}

    def _named(self, stem):
        if stem in self._cache:
            return self._cache[stem]
        raw = self._meg.get("DATA\\ART\\TEXTURES\\SRGB\\%s.DDS" % stem)
        if raw is None:
            self._cache[stem] = None
            return None
        try:
            img = load_dds(raw)
        except TextureError:
            img = None
        self._cache[stem] = img
        return img

    def skin(self, name):
        bg, scan = self.SKINS[name]
        return self._named(bg), self._named(scan)

    def menu_background(self, skin):
        return self._named(self.MENU_BG.get(skin, ""))

    def icon(self, game):
        stem = self.ICONS.get(game)
        return self._named(stem) if stem else None

# ---------------------------------------------------------------------------
# MT_COMMANDBAR_COMMON - the shared UI sprite atlas
#
# The jukebox layouts name sprites like "ui_jukebox_cnctd_icon" that exist in
# no archive as a file of their own.  They live in a 6871x6716 atlas,
# MT_COMMANDBAR_COMMON.TGA (176 MiB, uncompressed 32-bit, bottom-left origin),
# indexed by MT_COMMANDBAR_COMMON.MTD:
#
#     uint32  0xFFFFFFFE           magic
#     int32   count
#     count x { uint32 namelen, char name[namelen], int32 rect[8], uint8 pad }
#
# where rect is (x, y, w, h, 0, 0, w, h) with y measured from the top.  The
# atlas is far too large to hold in memory, so only the rows a sprite occupies
# are read out of the archive.
# ---------------------------------------------------------------------------
ATLAS_MTD = "DATA\\ART\\TEXTURES\\SRGB\\MT_COMMANDBAR_COMMON.MTD"
ATLAS_TGA = "DATA\\ART\\TEXTURES\\SRGB\\MT_COMMANDBAR_COMMON.TGA"


class Atlas(object):

    def __init__(self, meg):
        self._meg = meg
        self._cache = {}
        self._index = {}
        self._tga = None
        raw = meg.get(ATLAS_MTD)
        if raw is None:
            return
        magic, count = struct.unpack_from("<Ii", raw, 0)
        o = 8
        for _ in range(count):
            if o + 4 > len(raw):
                break
            nlen = struct.unpack_from("<I", raw, o)[0]
            o += 4
            name = raw[o:o + nlen].rstrip(b"\x00").decode("ascii", "replace")
            o += nlen
            if o + 33 > len(raw):
                break
            self._index[name.upper()] = struct.unpack_from("<4i", raw, o)
            o += 33                       # 8 x int32 plus one padding byte
        hit = meg._index.get(ATLAS_TGA.lower())
        if hit is None:
            return
        size, base = hit
        head = meg.read(base, 18)
        if head[2] != 2 or head[16] != 32:            # uncompressed, 32-bit
            return
        w, h = struct.unpack_from("<HH", head, 12)
        self._tga = (base + 18 + head[0], w, h)

    def __contains__(self, name):
        return name.upper() in self._index and self._tga is not None

    def sprite(self, name):
        """-> QImage for one named sprite, or None."""
        key = name.upper()
        if key in self._cache:
            return self._cache[key]
        img = None
        if self._tga is not None and key in self._index:
            pix, w, h = self._tga
            x, y, sw, sh = self._index[key]
            if sw > 0 and sh > 0 and x >= 0 and y >= 0 and x + sw <= w and y + sh <= h:
                rows = []
                for r in range(y, y + sh):
                    fr = h - 1 - r                     # TGA origin is bottom-left
                    rows.append(self._meg.read(pix + (fr * w + x) * 4, sw * 4))
                buf = b"".join(rows)
                img = QImage(buf, sw, sh, sw * 4, QImage.Format_ARGB32).copy()
        self._cache[key] = img
        return img
