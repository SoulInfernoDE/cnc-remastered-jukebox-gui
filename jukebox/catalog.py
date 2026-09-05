# -*- coding: utf-8 -*-
"""The two catalogues behind the sound box: effects, and animated objects.

Both are read from the installation at runtime.  Note what is *not* here: a
mapping from a sound to "its" unit or building.  The games do not ship one -
checking all 508 sound stems against all 192 object names yields no match, and
the handful of substring hits are coincidence.  So the sound box presents two
catalogues side by side rather than pretending to derive one from the other.
"""

import io
import os
import re
import struct
import zipfile

from PyQt5.QtGui import QImage

# Sound stems carry the game and fidelity in a four-letter prefix.
PREFIX = {"TDC": ("Tiberian_Dawn", "Classic"),
          "TDR": ("Tiberian_Dawn", "Remaster"),
          "RAC": ("Red_Alert", "Classic"),
          "RAR": ("Red_Alert", "Remaster")}

# The kinds the stems fall into, in the order they should be listed.
KINDS = ("EVA", "Voice", "Effect")

OBJECT_ROOT = "DATA\\ART\\TEXTURES\\SRGB\\{}\\{}\\"
OBJECT_GAMES = (("Tiberian_Dawn", "TEXTURES_TD_SRGB.MEG"),
                ("Red_Alert", "TEXTURES_RA_SRGB.MEG"))
OBJECT_GROUPS = ("STRUCTURES", "UNITS", "VFX")


class Sound(object):
    __slots__ = ("stem", "label", "game", "fidelity", "kind", "archive",
                 "size", "offset")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


def subtitle_keys(stem):
    """The string-table keys holding what a spoken line actually says.

    The table drops the EVA_/UNT_ part, so RAR_SFX_EVA_1MINR is keyed
    TEXT_SFX_RAR_SFX_1MINR.  The classic-prefix key is tried first: both exist
    and hold the same line, but only the classic ones are translated - in the
    German table 56 of 122 carry German text while the remastered keys carry
    none.  Where the game itself never translated a line it stays English,
    which is what the game shows too.
    """
    base = re.sub(r"_(EVA|UNT)_", "_", stem)
    out = []
    classic = re.sub(r"^RAR_", "RAC_", re.sub(r"^TDR_", "TDC_", base))
    if classic != base:
        out.append("TEXT_SFX_" + classic)
    out.append("TEXT_SFX_" + base)
    return out


def _pretty(stem):
    s = re.sub(r"^(EVA|UNT)_", "", stem)
    s = s.replace("_", " ").replace(".", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s.title()


class SoundCatalog(object):
    """Every effect in the game, grouped by game, fidelity and kind."""

    def __init__(self, data):
        self.data = data
        self.sounds = []
        seen = set()
        for meg in data._sfx_list():
            for name, size, offset in meg.entries:
                base = name.split("\\")[-1]
                if not base.upper().endswith(".WAV"):
                    continue
                stem = base[:-4]
                stem = re.sub(r"_%s$" % re.escape(data.language), "", stem)
                m = re.match(r"^(TDC|TDR|RAC|RAR)_SFX_(.+)$", stem)
                if m:
                    game, fidelity = PREFIX[m.group(1)]
                    rest = m.group(2)
                else:
                    game, fidelity, rest = "Shared", "Remaster", stem
                if rest.startswith("EVA_"):
                    kind = "EVA"
                elif rest.startswith("UNT_"):
                    kind = "Voice"
                else:
                    kind = "Effect"
                key = (game, fidelity, rest)
                if key in seen:
                    continue
                seen.add(key)
                spoken = ""
                for key in subtitle_keys(stem):
                    spoken = data._text.get(key, "").strip()
                    if spoken:
                        break
                self.sounds.append(Sound(
                    stem=stem, label=spoken or _pretty(rest), game=game,
                    fidelity=fidelity, kind=kind, archive=meg,
                    size=size, offset=offset))
        self.sounds.sort(key=lambda s: (s.game, s.fidelity,
                                        KINDS.index(s.kind), s.label.lower()))

    def filtered(self, games, fidelities, kinds):
        return [s for s in self.sounds
                if s.game in games or s.game == "Shared"
                if s.fidelity in fidelities and s.kind in kinds]

    def wav(self, sound):
        return sound.archive.read(sound.offset, sound.size)


class GameObject(object):
    __slots__ = ("name", "label", "game", "group", "archive", "size", "offset")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


class ObjectCatalog(object):
    """Units, structures and effects, each a zip of frames in the archives."""

    def __init__(self, data):
        self.data = data
        self.objects = []
        self._frames = {}
        for game, arch in OBJECT_GAMES:
            meg = data.texture_archive(arch)
            if meg is None:
                continue
            for group in OBJECT_GROUPS:
                prefix = OBJECT_ROOT.format(game.upper(), group)
                for name, size, offset in meg.entries:
                    up = name.upper()
                    if not up.startswith(prefix) or not up.endswith(".ZIP"):
                        continue
                    stem = name.split("\\")[-1][:-4]
                    self.objects.append(GameObject(
                        name=stem, label=stem.title(), game=game,
                        group=group.title(), archive=meg,
                        size=size, offset=offset))
        self.objects.sort(key=lambda o: (o.game, o.group, o.name))

    def filtered(self, games, groups):
        return [o for o in self.objects
                if o.game in games and o.group in groups]

    def frames(self, obj, limit=48, max_side=320):
        """Decodes an object's frames, downscaled, and caches them.

        The archives hold uncompressed 32-bit TGA at up to 512x512 a frame, so
        a single object can be tens of megabytes; only what is shown is kept.
        """
        key = (obj.game, obj.name)
        hit = self._frames.get(key)
        if hit is not None:
            return hit
        out = []
        try:
            raw = obj.archive.read(obj.offset, obj.size)
            zf = zipfile.ZipFile(io.BytesIO(raw))
            names = sorted(n for n in zf.namelist()
                           if n.lower().endswith((".tga", ".dds")))
            step = max(1, len(names) // limit)
            for n in names[::step][:limit]:
                img = _decode(zf.read(n))
                if img is not None:
                    if img.width() > max_side or img.height() > max_side:
                        img = img.scaled(max_side, max_side, 1, 1)  # Keep, Smooth
                    out.append(img)
        except Exception:
            out = []
        self._frames[key] = out
        if len(self._frames) > 6:                 # keep memory bounded
            for k in list(self._frames)[:-6]:
                del self._frames[k]
        return out


def _decode(blob):
    if blob[:4] == b"DDS ":
        h, w = struct.unpack_from("<II", blob, 12)
        if len(blob) - 128 < w * h * 4:
            return None
        return QImage(blob[128:128 + w * h * 4], w, h, w * 4,
                      QImage.Format_ARGB32).copy()
    if len(blob) > 18 and blob[2] == 2 and blob[16] == 32:
        idlen = blob[0]
        w, h = struct.unpack_from("<HH", blob, 12)
        desc = blob[17]
        off = 18 + idlen
        if len(blob) - off < w * h * 4:
            return None
        img = QImage(blob[off:off + w * h * 4], w, h, w * 4,
                     QImage.Format_ARGB32).copy()
        if not desc & 0x20:                       # origin is bottom-left
            img = img.mirrored(False, True)
        return img
    return None
