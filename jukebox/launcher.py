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
import re
import struct

from PyQt5.QtCore import QRect, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QImage, QPainter
from PyQt5.QtWidgets import QApplication, QWidget

from . import xwin

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


# Where each button sits, correlated against a running launcher rather than
# eyeballed: its own bitmaps were slid over a screenshot of it and these are
# the offsets that fit.  The Map Editor row, which this file leans on, sits at
# x 24..538 and y 490..588 of a 560x618 window, with 29 rows of frame below
# it and eight of seam above.
LAYOUT = {"td": (25, 277), "ra": (285, 277),
          "editor": (24, 490), "close": (515, 14)}
BASE_SIZE = (560, 616)
ASPECT = BASE_SIZE[0] / float(BASE_SIZE[1])

# Which window on screen is the launcher's.  Not the title: it sets
# "CnCRemastered", the collection's name rather than the launcher's, and the
# game beside it answers to the same one - both windows even carry the same
# WM_CLASS, steam_app_1213210.  What separates them is the process, which
# Proton names after the Windows executable, so /proc/<pid>/comm reads
# "ClientLauncherG" for one and "ClientG" for the other.
LAUNCHER_PROCESS = "clientlauncherg"
LAUNCHER_TITLE = r"^CnCRemastered$|Command\s*&\s*Conquer.*Remastered"
ASPECT_TOL = 0.06

# The Map Editor slot is the shape this project borrows: a full-width row at
# the foot of the panel.  The strip taken as the base is the seam above such a
# row, the row itself and the frame that closes the window off - all three in
# one piece, so the side rails and rivets running down the edges come with it,
# and the green slot then covers the Map Editor exactly.
STRIP = (0, 480, 560, 136)              # seam, button row and closing frame
SLOT_AT = (24, 8)                       # the slot's place within the strip
CAP_H = 29                              # frame below the row, and the overlap
PANEL_H = STRIP[3]                      # 136

# The seam rows are cut from between the two half-width buttons, so they carry
# the divider that separates those.  A full-width row has nothing there, so
# that stretch is replaced by a copy of the plain metal beside it.
SEAM_ROWS = 8
DIVIDER = (245, 80)                     # x and width of the piece to replace
DIVIDER_FROM = 115                      # x of the plain metal it is taken from

# Inside the Map Editor bitmap.  The bevel is six pixels; the label band
# starts at 62; the planet occupies x 130..390, and its glow reaches a dozen
# pixels further on the hovered copy - which is the brighter of the two, so
# the clean noise is measured there and cut well clear of it.
INNER = (6, 6, 502, 89)
NOISE = ((14, 8, 100, 54), (404, 8, 100, 54))
BAND = (430, 62, 70, 33)

# Blue for Tiberian Dawn, red for Red Alert, and green here, which is what a
# music button is coloured everywhere.  How strongly matters: measured on the
# mean colour of each slot's noise, the game sits at saturation 47 for its
# blue and 97 for its red, on the 0..255 scale Qt uses.  Multiplying the
# slot's own greyscale by this tint lands on 85 - inside the family the
# launcher already established, rather than shouting past it.
GREEN = QColor(170, 255, 170)


def launcher_shaped(geo):
    """Does this window have the launcher's proportions, 560 by 616?"""
    w, h = geo[2], geo[3]
    return h > 0 and abs(w / float(h) - ASPECT) <= ASPECT_TOL


def find_launcher():
    """(window id, rectangle) of the launcher's window, or None.

    The process is asked first, because it answers without ambiguity.  Where
    the desktop reports no pid, the title has to do, and then the window's
    proportions are the guard - the game is never that shape.
    """
    fallback = None
    for win, title, pid, geo in xwin.windows():
        name = xwin.process_name(pid).lower()
        if name:
            if name == LAUNCHER_PROCESS:
                return win, geo
            continue          # a known process that is not it, title or not
        if fallback is None and re.search(LAUNCHER_TITLE, title, re.I) \
                and launcher_shaped(geo):
            fallback = (win, geo)
    return fallback


def green_slot(art, hovered=False):
    """The Map Editor slot, cleared of its planet and lettering, in green.

    The launcher tints each slot's noise by hue - 215 for Tiberian Dawn, 22
    for Red Alert - over one shared texture.  This does the same thing to the
    Map Editor's copy: the planet and the word are replaced by the clean noise
    from either side of them, and only the interior is tinted, so the metal
    bevel stays the colour the launcher drew it.
    """
    src = art.part("editor", hovered)
    if src is None:
        return None
    src = src.convertToFormat(QImage.Format_ARGB32)
    inner = QRect(*INNER)
    out = QImage(src)
    p = QPainter(out)
    p.setClipRect(inner)

    tiles = []
    for box in NOISE:
        t = src.copy(QRect(*box))
        tiles += [t, t.mirrored(True, False)]    # mirrored, or the repeat shows
    tw, th = tiles[0].width(), tiles[0].height()
    i, row, y = 0, 0, inner.top()
    while y < inner.bottom():
        # Each row starts at a different offset, or the tile joins would line
        # up into vertical seams - which the brighter hovered noise shows.
        x = inner.left() - (row * 43) % tw
        while x < inner.right():
            p.drawImage(x, y, tiles[i % len(tiles)])
            x += tw
            i += 1
        y += th
        row += 1
        i += 1
    band = src.copy(QRect(*BAND))
    x = inner.left()
    while x < inner.right():
        p.drawImage(x, BAND[1], band)
        x += band.width()
    p.end()

    tint = out.copy(inner).convertToFormat(QImage.Format_Grayscale8)
    tint = tint.convertToFormat(QImage.Format_ARGB32)
    p = QPainter(tint)
    p.setCompositionMode(QPainter.CompositionMode_Multiply)
    p.fillRect(tint.rect(), GREEN)
    p.end()
    p = QPainter(out)
    p.drawImage(inner.topLeft(), tint)
    p.end()
    return out


# The three app icons, overlapping left to right in front of the label.
ICON_SIDE = 84
ICON_STEP = 44
ICON_X = 8
ICON_CY = 45
LABEL_PX = 28

# The launcher's own hover does two things: it brightens the noise, which
# comes along with the hovered bitmap, and it turns the lettering from white
# to the slot's colour - the Map Editor's goes to (96, 189, 254).  Ours takes
# the same treatment in green: that blue's saturation and value at hue 120.
LABEL = QColor(228, 228, 228)
LABEL_HOVER = QColor.fromHsv(120, QColor(96, 189, 254).saturation(),
                             QColor(96, 189, 254).value())


def panel_image(art, icons, family, label, hovered=False):
    """The strip that goes under the launcher: gap, green slot, closing frame."""
    bg = art.part("background")
    slot = green_slot(art, hovered)
    if bg is None or slot is None:
        return None
    out = QImage(bg.copy(QRect(*STRIP))).convertToFormat(QImage.Format_ARGB32)
    p = QPainter(out)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    p.setRenderHint(QPainter.Antialiasing, True)
    patch = out.copy(QRect(DIVIDER_FROM, 0, DIVIDER[1], SEAM_ROWS))
    p.drawImage(DIVIDER[0], 0, patch)
    ox, oy = SLOT_AT
    p.drawImage(ox, oy, slot)
    for i in reversed(range(len(icons))):     # the leftmost ends up on top
        p.drawPixmap(QRect(ox + ICON_X + i * ICON_STEP,
                           oy + ICON_CY - ICON_SIDE // 2,
                           ICON_SIDE, ICON_SIDE), icons[i])
    f = QFont(family)
    f.setPixelSize(LABEL_PX)
    f.setBold(True)
    f.setLetterSpacing(QFont.PercentageSpacing, 115)
    p.setFont(f)
    p.setPen(LABEL_HOVER if hovered else LABEL)
    p.drawText(QRect(ox + INNER[0], oy + BAND[1], INNER[2], BAND[3]),
               Qt.AlignCenter, label)
    p.end()
    return out


class LauncherPanel(QWidget):
    """A Jukebox row drawn onto the bottom of the game's own launcher window.

    The launcher cannot be extended from inside: it is a Windows executable
    that runs before the game, reads no mod data, and the Steam Workshop for
    this title only carries maps and game-logic mods.  Replacing it is no good
    either - ClientG.exe takes no game-selection argument and the launcher
    records the choice nowhere, so a stand-in chooser could only hand off to
    the real launcher and would put a second selection step in the way.

    So this follows it instead.  The window manager knows where the launcher
    is, and this strip is placed over its bottom frame and carries its own,
    which makes the two read as a single window.  When the launcher goes -
    because a game was picked, or because it was closed - this goes with it.
    """

    clicked = pyqtSignal()
    launcherGone = pyqtSignal()

    POLL_MS = 300
    # A cold Proton start can take a while - shader caches, a prefix being
    # built - so the wait before giving up on a launcher is generous.  It
    # costs nothing: where X cannot be asked at all, the row stands on its
    # own straight away instead of waiting this out.
    PATIENCE_MS = 90000
    # And one missed look is not a departure.  A window can drop out of the
    # desktop's list for a moment while it is being restacked or redrawn, and
    # treating that as "the launcher is gone" would close the row for good.
    MISSES = 4

    def __init__(self, art, icons, family, label="JUKEBOX", parent=None):
        super(LauncherPanel, self).__init__(parent)
        self.art = art
        self._plain = panel_image(art, icons, family, label, False)
        self._lit = panel_image(art, icons, family, label, True)
        self._hover = False
        self._seen = False
        self._waited = 0
        self._missed = 0
        self._tied = 0
        self._drag = None
        self._moved = False
        self.setWindowTitle("Jukebox")
        # Not on top of everything: the row belongs to the launcher and hides
        # behind other applications exactly as the launcher does.  Staying
        # just above it is the window manager's job, told through the same
        # hint a dialog uses (see attach).
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setMouseTracking(True)
        self.setFixedSize(*BASE_SIZE[:1] + (PANEL_H,))

        self._timer = QTimer(self)
        self._timer.setInterval(self.POLL_MS)
        self._timer.timeout.connect(self._follow)

    # -- painting --------------------------------------------------------
    def paintEvent(self, _):
        img = self._lit if self._hover else self._plain
        p = QPainter(self)
        if img is None:
            p.fillRect(self.rect(), QColor(28, 30, 32))
            p.end()
            return
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.drawImage(self.rect(), img)
        p.end()

    def enterEvent(self, _):
        self._hover = True
        self.update()

    def leaveEvent(self, _):
        self._hover = False
        self.update()

    def mousePressEvent(self, ev):
        self._moved = False
        # While attached there is nowhere to drag to: the next poll would put
        # it straight back under the launcher.  Loose, it can be moved.
        self._drag = (ev.globalPos() - self.frameGeometry().topLeft()
                      if ev.button() == Qt.LeftButton and not self._seen
                      else None)

    def mouseMoveEvent(self, ev):
        if self._drag and ev.buttons() & Qt.LeftButton:
            self._moved = True
            self.move(ev.globalPos() - self._drag)

    def keyPressEvent(self, ev):
        # Only reachable when it is standing on its own; attached, it goes
        # when the launcher goes.
        if ev.key() == Qt.Key_Escape:
            self.stop_following()
            self.hide()
            self.launcherGone.emit()
        else:
            super(LauncherPanel, self).keyPressEvent(ev)

    def mouseReleaseEvent(self, ev):
        moved, self._moved, self._drag = self._moved, False, None
        if ev.button() == Qt.LeftButton and not moved:
            self.clicked.emit()

    # -- following the launcher ------------------------------------------
    def follow_launcher(self):
        """Waits for the launcher window, then stays underneath it."""
        self._follow()
        self._timer.start()

    def stop_following(self):
        self._timer.stop()

    def _follow(self):
        asking = xwin.available()
        found = find_launcher() if asking else None
        if found is None:
            if self._seen:
                self._missed += 1
                if self._missed < self.MISSES:   # a flicker, not a departure
                    return
                self._timer.stop()
                self.hide()
                self.launcherGone.emit()
                return
            self._waited += self.POLL_MS
            if not self.isVisible() and (not asking
                                         or self._waited >= self.PATIENCE_MS):
                self.place_fallback()            # no launcher: stand on its own
                self.show()
            return
        win, geo = found
        self._seen, self._missed = True, 0
        self.attach(geo)
        if not self.isVisible():
            self.show()
        self._stay_with(win)

    def _stay_with(self, launcher):
        """Keep the row immediately above the launcher, and nowhere else.

        The transient-for hint says the row belongs to that window, which is
        what most desktops need to keep the two together.  Where one ignores
        it, the stacking order says whether the launcher has come out on top,
        and only then is the row lifted - so it never floats over anything
        else the way an always-on-top window would.
        """
        me = int(self.winId())
        if launcher != self._tied:
            self._tied = launcher
            xwin.keep_above(me, launcher)
        order = xwin.stacking()
        try:
            if order.index(launcher) > order.index(me):
                self.raise_()
        except ValueError:
            pass

    def attach(self, geo):
        """Sit on the launcher's bottom frame, so the two look like one window.

        Measured on a running launcher, the Map Editor row ends 29 rows above
        the foot of the window, so that is where this one begins - covering
        the frame the launcher closes itself off with, and carrying its own.
        """
        x, y, w, h = geo
        scale = max(0.5, min(3.0, w / float(BASE_SIZE[0])))
        self.setFixedSize(w, int(round(PANEL_H * scale)))
        self.move(x, y + h - int(round(CAP_H * scale)))

    def place_fallback(self):
        """Bottom-right of the screen, for when the launcher cannot be found."""
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        g = screen.availableGeometry()
        self.setFixedSize(*BASE_SIZE[:1] + (PANEL_H,))
        self.move(g.right() - self.width() - 40, g.bottom() - self.height() - 60)
