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
