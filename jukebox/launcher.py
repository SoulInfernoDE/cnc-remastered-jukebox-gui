# -*- coding: utf-8 -*-
"""Reads the game launcher's own artwork out of its executable.

The window Steam opens when you press Play belongs to ClientLauncherG.exe, a
Windows binary.  Unlike the jukebox it has no .BUI layout - its interface is a
set of bitmaps in the executable's PE resource section:

    106   560x616   the window background, with the header plate
    107   255x208   Tiberian Dawn button          (109 = hovered)
    110   255x208   Red Alert button              (111 = hovered)
    114   515x99    Map Editor button             (115 = hovered)
    112    30x30    close button                  (113 = hovered)

Nothing is copied out of the game: the resources are read at runtime from the
installation, exactly as the textures and fonts are.
"""

import os
import struct

from PyQt5.QtCore import QRect, Qt, pyqtSignal
from PyQt5.QtGui import (QBrush, QColor, QFont, QImage, QLinearGradient,
                         QPainter, QPen)
from PyQt5.QtWidgets import QApplication, QWidget

RT_BITMAP = 2
LAUNCHER_EXE = "ClientLauncherG.exe"

# Resource id -> what it is.  Hover variants sit one id above their base.
PARTS = {"background": 106, "td": 107, "ra": 110, "editor": 114, "close": 112}
HOVER = {"td": 109, "ra": 111, "editor": 115, "close": 113}


class LauncherArt(object):
    """The launcher's bitmaps, decoded on demand."""

    def __init__(self, game_dir):
        self.path = os.path.join(game_dir, LAUNCHER_EXE)
        self._cache = {}
        self._index = {}
        try:
            self._index = _read_bitmaps(self.path)
        except Exception:
            self._index = {}

    @property
    def available(self):
        return bool(self._index)

    def part(self, name, hovered=False):
        rid = (HOVER if hovered else PARTS).get(name, PARTS.get(name))
        if rid is None or rid not in self._index:
            rid = PARTS.get(name)
        if rid not in self._index:
            return None
        if rid in self._cache:
            return self._cache[rid]
        img = _decode_dib(self._index[rid])
        self._cache[rid] = img
        return img


def _read_bitmaps(path):
    """-> {resource id: DIB bytes} for every RT_BITMAP in the executable."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:2] != b"MZ":
        raise ValueError("not a PE file")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("no PE header")
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    optsize = struct.unpack_from("<H", data, pe + 20)[0]
    plus = struct.unpack_from("<H", data, pe + 24)[0] == 0x20B
    dd = pe + 24 + (112 if plus else 96)
    res_rva = struct.unpack_from("<I", data, dd + 2 * 8)[0]
    if not res_rva:
        raise ValueError("no resource directory")

    sections = []
    so = pe + 24 + optsize
    for i in range(nsec):
        vsize, vaddr, rsize, raddr = struct.unpack_from("<IIII", data, so + i * 40 + 8)
        sections.append((vaddr, max(vsize, rsize), raddr))

    def to_offset(rva):
        for vaddr, size, raddr in sections:
            if vaddr <= rva < vaddr + size:
                return raddr + (rva - vaddr)
        return None

    base = to_offset(res_rva)
    out = {}

    def walk(off, level, rid):
        named, ided = struct.unpack_from("<HH", data, off + 12)
        for i in range(named + ided):
            e = off + 16 + i * 8
            key, child = struct.unpack_from("<II", data, e)
            if key & 0x80000000:
                key = None                       # named types are not wanted
            if child & 0x80000000:
                walk(base + (child & 0x7FFFFFFF), level + 1,
                     key if level == 1 else rid)
            elif level == 0 or rid is not None:
                drva, dsize = struct.unpack_from("<II", data, base + child)
                start = to_offset(drva)
                if start is not None and rid is not None:
                    out[rid] = data[start:start + dsize]

    # Level 0 holds the resource types; only RT_BITMAP matters.
    named, ided = struct.unpack_from("<HH", data, base + 12)
    for i in range(named + ided):
        e = base + 16 + i * 8
        key, child = struct.unpack_from("<II", data, e)
        if key == RT_BITMAP and child & 0x80000000:
            walk(base + (child & 0x7FFFFFFF), 1, None)
    return out


def _decode_dib(dib):
    """A packed DIB (no file header) -> QImage."""
    hsize, w, h, planes, bits = struct.unpack_from("<IiiHH", dib, 0)
    comp, _, _, _, clrused, _ = struct.unpack_from("<IIiiII", dib, 16)
    if comp != 0 or bits not in (24, 32):
        return None
    ncol = clrused if clrused else (1 << bits if bits <= 8 else 0)
    off = hsize + ncol * 4
    stride = ((w * bits + 31) // 32) * 4
    flip = h > 0                                 # positive height is bottom-up
    rows = abs(h)
    if len(dib) - off < stride * rows:
        return None
    fmt = QImage.Format_RGB888 if bits == 24 else QImage.Format_ARGB32
    img = QImage(dib[off:off + stride * rows], w, rows, stride,
                 QImage.Format_RGB888 if bits == 24 else QImage.Format_ARGB32)
    img = img.rgbSwapped() if bits == 24 else img
    return (img.mirrored(False, True) if flip else img).copy()


# Where each button sits on the 560x616 background, measured by compositing
# the parts back onto it and checking them against the real window.
LAYOUT = {"td": (22, 278), "ra": (283, 278),
          "editor": (22, 494), "close": (524, 10)}
BASE_SIZE = (560, 616)

# The extra row this project adds.  The background is grown by repeating a
# seam of bare inner panel, so the frame and the logo keep their proportions
# instead of being stretched.  The seam is taken from the gap between the two
# button rows, which is the only clean stretch of panel there is - cutting it
# from just under the Map Editor slot drags that slot's edge along and the
# repeat shows as stripes.
SEAM_Y = 594                            # where the background is cut
EXTRA_ROW = (22, 599, 515, 99)          # x, y, w, h of the Jukebox slot


def extended_background(art, extra=EXTRA_ROW[3] + 12):
    """The launcher background with room for one more button underneath.

    The strip is filled with the panel's own median colour rather than a
    repeated slice: every horizontal band of that background carries some
    structure - a slot edge, a rivet line - and tiling any of them shows up as
    ribbing.  A flat fill under the same inner shadow the real slots sit in is
    both cleaner and closer to what the panel looks like between them.
    """
    bg = art.part("background")
    if bg is None:
        return None
    w, h = bg.width(), bg.height()
    sample = bg.copy(QRect(30, 250, w - 60, 20)).scaled(1, 1)
    panel = QColor(sample.pixel(0, 0))

    out = QImage(w, h + extra, QImage.Format_ARGB32)
    out.fill(0)
    p = QPainter(out)
    p.drawImage(QRect(0, 0, w, SEAM_Y), bg, QRect(0, 0, w, SEAM_Y))

    strip = QRect(0, SEAM_Y, w, extra)
    grad = QLinearGradient(0, strip.top(), 0, strip.bottom())
    grad.setColorAt(0.0, panel.darker(118))
    grad.setColorAt(0.45, panel)
    grad.setColorAt(1.0, panel.darker(126))
    p.fillRect(strip, QBrush(grad))
    # The frame rails at either side carry on through the added strip.
    p.drawImage(QRect(0, SEAM_Y, 22, extra), bg, QRect(0, 300, 22, extra))
    p.drawImage(QRect(w - 22, SEAM_Y, 22, extra), bg,
                QRect(w - 22, 300, 22, extra))

    p.drawImage(QRect(0, SEAM_Y + extra, w, h - SEAM_Y), bg,
                QRect(0, SEAM_Y, w, h - SEAM_Y))
    p.end()
    return out


class LauncherButton(QWidget):
    """A Jukebox button in the launcher's style, shown beside its window.

    The launcher cannot be extended from inside: it is a Windows executable
    that runs before the game, reads no mod data, and the Steam Workshop for
    this title only carries maps and game-logic mods.  Replacing it is no good
    either - ClientG.exe takes no game-selection argument and the launcher
    records the choice nowhere, so a stand-in chooser could only hand off to
    the real launcher and would put a second selection step in the way.

    So this sits next to it instead: the game still starts exactly as before,
    and the jukebox is one click from pressing Play.
    """

    clicked = pyqtSignal()

    def __init__(self, art, accent, emblem=None, parent=None):
        super(LauncherButton, self).__init__(parent)
        self.art = art
        self.accent = accent
        self.emblem = emblem
        self._hover = False
        self._panel = self._sample_panel()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint |
                            Qt.WindowStaysOnTopHint)
        self.setMouseTracking(True)
        self.setFixedSize(232, 96)

    def _sample_panel(self):
        bg = self.art.part("background") if self.art else None
        if bg is None:
            return QColor(34, 36, 38)
        return QColor(bg.copy(QRect(30, 250, 500, 20)).scaled(1, 1).pixel(0, 0))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = self.rect()
        grad = QLinearGradient(0, r.top(), 0, r.bottom())
        grad.setColorAt(0.0, self._panel.lighter(118))
        grad.setColorAt(0.5, self._panel)
        grad.setColorAt(1.0, self._panel.darker(128))
        p.setPen(QPen(QColor(12, 13, 14), 3))
        p.setBrush(QBrush(grad))
        p.drawRect(r.adjusted(1, 1, -2, -2))

        slot = r.adjusted(9, 9, -10, -10)
        p.setPen(QPen(QColor(150, 156, 162) if self._hover
                      else QColor(92, 98, 104), 2))
        p.setBrush(QColor(10, 11, 12, 210))
        p.drawRect(slot)

        if self.emblem is not None and not self.emblem.isNull():
            side = slot.height() - 20
            p.drawImage(QRect(slot.x() + 12, slot.center().y() - side // 2,
                              side, side), self.emblem)
        f = QFont(self.font())
        f.setPixelSize(max(13, slot.height() // 3))
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(238, 238, 238) if self._hover else QColor(196, 200, 204))
        p.drawText(slot.adjusted(slot.height() - 4, 0, -8, 0),
                   Qt.AlignCenter, "JUKEBOX")
        p.end()

    def enterEvent(self, _):
        self._hover = True
        self.update()

    def leaveEvent(self, _):
        self._hover = False
        self.update()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag = ev.globalPos() - self.frameGeometry().topLeft()
        else:
            self._drag = None

    def mouseMoveEvent(self, ev):
        if getattr(self, "_drag", None) and ev.buttons() & Qt.LeftButton:
            self.move(ev.globalPos() - self._drag)

    def mouseReleaseEvent(self, ev):
        moved = getattr(self, "_moved", False)
        self._drag = None
        if ev.button() == Qt.LeftButton and not moved:
            self.clicked.emit()

    def place_beside_launcher(self):
        """Bottom-right of the screen, clear of the launcher's own window."""
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        g = screen.availableGeometry()
        self.move(g.right() - self.width() - 40, g.bottom() - self.height() - 60)
