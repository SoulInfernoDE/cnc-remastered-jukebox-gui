# -*- coding: utf-8 -*-
"""The jukebox window, drawn from the game's own layout, textures and fonts.

Geometry comes from the .BUI layout files (see layout.py), the skin from
TEXTURES_SRGB.MEG, the typefaces from DATA\\ART\\FONTS inside CONFIG.MEG, and
every caption from MASTERTEXTFILE_<LANG>.LOC in the system's language.  The
window keeps the 4:3 aspect of the background texture, so a widget rectangle
maps straight onto the rendered surface.
"""

import json
import os
import math
import random
import subprocess
import time

from PyQt5.QtCore import QPoint, QRect, QRectF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import (QBrush, QColor, QFont, QFontDatabase, QFontMetrics,
                         QLinearGradient, QPainter, QPainterPath, QPen, QPixmap)
from PyQt5.QtWidgets import QWidget

from .assets import Atlas, Textures
from .audio import Player, play_effect
from .layout import Layout

FONTS = {"francker": "DATA\\ART\\FONTS\\FRANCKERW1G-CONDENSEDREG.TTF",
         "orbitron": "DATA\\ART\\FONTS\\RA_ORBITRON.TTF",
         "russell":  "DATA\\ART\\FONTS\\RUSSEL SQUARE.TTF",
         "cjk":      "DATA\\ART\\FONTS\\NOTOSANSCJKTC-REGULAR.TTF"}

SKIN_BUI = {
    "soviet": "DATA\\ART\\GUI\\RA\\RA_UI_MUSICJUKEBOX_SOVIET.BUI",
    "allied": "DATA\\ART\\GUI\\RA\\RA_UI_MUSICJUKEBOX_ALLIED.BUI",
    "td":     "DATA\\ART\\GUI\\UI_MUSICJUKEBOX.BUI",
}

# Sampled from the game's own screens.
ACCENT = {"soviet": QColor(200, 40, 40), "allied": QColor(60, 120, 210),
          "td":     QColor(190, 150, 40)}
TEXT = QColor(222, 222, 222)
TEXT_DIM = QColor(165, 165, 165)
TEXT_GREEN = QColor(90, 210, 90)
GOLD = QColor(232, 176, 46)

# Sprites from MT_COMMANDBAR_COMMON, the shared UI atlas.  The jukebox layouts
# name these but they exist in no archive as files of their own; see
# docs/JUKEBOX-UI.md.
SPRITES = {
    "soviet": {
        "button":      "RA_UI_MAINBTN_NORMAL.TGA",
        "button_hot":  "RA_UI_MAINBTN_SELECTED.TGA",
        "check_on":    "RA_UI_OPTIONS_CHECK_BOX_CHECK.TGA",
        "check_off":   "RA_UI_OPTIONS_CHECK_BOX_UNCHECKED.TGA",
        "fill":        "RA_UI_JUKEBOX_SLIDERBAR_FILL_SOVIET.TGA",
        "ball":        "RA_UI_OPTIONS_SLIDERBAR_BALL.TGA",
        "play":        "UI_RA_JUKEBOX_PAUSEPLAY_BTN_NORMAL.TGA",
        "play_hot":    "UI_RA_JUKEBOX_PAUSEPLAY_BTN_HOVERED.TGA",
        "row_hover":   "RA_UI_JUKEBOX_HOVERSTATE_SOVIET.TGA",
    },
    "allied": {
        "button":      "RA_UI_MAINBTN_NORMAL.TGA",
        "button_hot":  "RA_UI_MAINBTN_SELECTED.TGA",
        "check_on":    "RA_UI_OPTIONS_CHECK_BOX_CHECK_ALLIED.TGA",
        "check_off":   "RA_UI_OPTIONS_CHECK_BOX_UNCHECKED_ALLIED.TGA",
        "fill":        "RA_UI_JUKEBOX_SLIDERBAR_FILL_ALLIED.TGA",
        "ball":        "RA_UI_OPTIONS_SLIDERBAR_BALL_BLUE.TGA",
        "play":        "UI_RA_JUKEBOX_PAUSEPLAY_BTN_NORMAL.TGA",
        "play_hot":    "UI_RA_JUKEBOX_PAUSEPLAY_BTN_HOVERED.TGA",
        "row_hover":   "RA_UI_JUKEBOX_HOVERSTATE_ALLIED.TGA",
    },
    "td": {
        "button":      "UI_BUTTON_MAIN_08_MID.TGA",
        "button_hot":  "UI_BUTTON_MAIN_PRESSED_08_MID.TGA",
        "check_on":    "UI_OPTIONS_CHECK_BOX_CHECK.TGA",
        "check_off":   "UI_OPTIONS_CHECK_BOX_UNCHECKED.TGA",
        "fill":        "UI_OPTIONS_SLIDERBAR_FILL.TGA",
        "ball":        "UI_OPTIONS_SLIDERBAR_BALL.TGA",
        "play":        "UI_JUKEBOX_PLAYPAUSE_BTN_ON.TGA",
        "play_hot":    "UI_JUKEBOX_PLAYPAUSE_BTN_HOVER.TGA",
        "row_hover":   None,
    },
}
TRACK_ICON = {"Tiberian_Dawn": "UI_JUKEBOX_CNCTD_ICON.TGA",
              "Red_Alert": "UI_JUKEBOX_CNCRA_ICON.TGA"}

# The faction emblem shown while a skin is "under construction".
SKIN_LOGO = {"td": "UI_SIDEBAR_FACTIONLOGO_GDI.TGA",
             "soviet": "UI_SIDEBAR_FACTIONLOGO_SOVIET.TGA",
             "allied": "UI_SIDEBAR_FACTIONLOGO_ALLIES.TGA"}

# Each game's own construction sounds, by stem; see GameData.sfx().
SKIN_SFX = {
    "td":     {"building": "TDR_SFX_EVA_BLDGING1",
               "complete": "TDR_SFX_EVA_CONSTRU1",
               "place":    "TDR_SFX_CONSTRU2"},
    "soviet": {"building": "RAR_SFX_EVA_ABLDGIN1",
               "complete": "RAR_SFX_EVA_CONSCMP1",
               "place":    "RAR_SFX_PLACBLDG"},
    "allied": {"building": "RAR_SFX_EVA_ABLDGIN1",
               "complete": "RAR_SFX_EVA_CONSCMP1",
               "place":    "RAR_SFX_PLACBLDG"},
}
SKIN_ORDER = ("soviet", "allied", "td")
BUILD_SECONDS = 3.0

# The two brass bolts on the header plate, measured on the background texture
# (centres and radius, normalised against it).
BOLT_LEFT = (0.06613, 0.07131, 0.01574)
BOLT_RIGHT = (0.93325, 0.07264, 0.01620)
FOLDER_BUTTON = (0.12500, 0.07131, 0.01500)

PROJECT_URL = "https://github.com/SoulInfernoDE/cnc-remastered-jukebox"
SLIDER_MINUS = "UI_OPTIONS_SLIDERBAR_MINUS.TGA"
SLIDER_PLUS = "UI_OPTIONS_SLIDERBAR_PLUS.TGA"

# The solid part of the background texture, measured on its alpha channel:
# x 47..2113, y 33..1585 of 2160x1620.  Same for all three skins.
CROP = (0.02176, 0.02037, 0.95648, 0.95802)
FRAME_ASPECT = 2066 / 1552.0


def config_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "cnc-jukebox", "playlist.json")


def hms(seconds):
    s = int(seconds)
    return "%d:%02d:%02d" % (s // 3600, s % 3600 // 60, s % 60)


def mmss(seconds):
    s = int(seconds)
    return "%02d:%02d" % (s // 60, s % 60)


class _IconTrack(object):
    """Stands in for a Track when only the game emblem is being drawn."""

    __slots__ = ("is_ra", "game")

    def __init__(self, is_ra):
        self.is_ra = is_ra
        self.game = "Red_Alert" if is_ra else "Tiberian_Dawn"


class Hit(object):
    """A rectangle that reacts to the mouse, optionally with a hover hint."""

    __slots__ = ("rect", "kind", "data", "tip")

    def __init__(self, rect, kind, data=None, tip=None):
        self.rect, self.kind, self.data, self.tip = rect, kind, data, tip


class JukeboxWindow(QWidget):

    closed = pyqtSignal()

    def __init__(self, data, skin="soviet", parent=None):
        super(JukeboxWindow, self).__init__(parent)
        self.data = data
        self.skin = skin if skin in SKIN_BUI else "soviet"
        self.accent = ACCENT[self.skin]

        self.layout_ = Layout(data.config.get(SKIN_BUI[self.skin]))
        self.tex = Textures(data.textures)
        self.atlas = Atlas(data.textures)
        self._sprite_cache = {}
        self.bg_img, self.scan_img = self.tex.skin(self.skin)
        self.menu_img = self.tex.menu_background(self.skin)
        self._bg_cache = None
        self._scan_cache = None
        self._menu_cache = None

        self._load_fonts()

        self.filters = {"Tiberian_Dawn": True, "Red_Alert": True,
                        "Remaster": True, "Classic": False, "Bonus": True}
        self.shuffle = True
        self.gap = 0.0                     # seconds, 0..30
        self.volume = 0.8
        self.playlist = []                 # Track objects, in order
        self.sel_available = None
        self.sel_playlist = None
        self.scroll = {"available": 0.0, "playlist": 0.0}
        self._drag = None
        self.current = None
        self._status = ""

        self.player = Player(self)
        self.player.set_volume(self.volume)
        self.player.positionChanged.connect(lambda _: self.update())
        self.player.stateChanged.connect(lambda _: self.update())
        self.player.trackFinished.connect(self._advance)
        self.player.failed.connect(self._on_audio_error)

        self._drag_window = None          # offset while dragging the window
        self._hover = None                # Hit under the cursor
        self._spin = 0.0                  # rotation of the playing track emblem
        self._build = None                # skin-change sequence, see _tick_build

        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(33)
        self._spin_timer.timeout.connect(self._on_spin)
        self._spin_timer.start()

        self._restore()
        # Frameless, so only the jukebox itself is on screen.  Dragging is
        # handled in the mouse events below.
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setMouseTracking(True)
        self.setMinimumSize(880, 660)
        self.resize(1240, 930)
        self.setWindowTitle("%s - %s" % (data.text("TEXT_JUKEBOX", "Jukebox"),
                                         data.text("TEXT_JUKEBOX_PLAYLIST_EDITOR")))

    # -- setup -----------------------------------------------------------
    def _load_fonts(self):
        self.font_families = {}
        for key, path in FONTS.items():
            raw = self.data.config.get(path)
            if raw is None:
                continue
            fid = QFontDatabase.addApplicationFontFromData(raw)
            fams = QFontDatabase.applicationFontFamilies(fid) if fid != -1 else []
            if fams:
                self.font_families[key] = fams[0]
        # Red Alert's screens use Orbitron; Tiberian Dawn uses Francker.
        self._ui_family = self.font_families.get(
            "orbitron" if self.skin != "td" else "francker",
            self.font_families.get("francker", "DejaVu Sans"))
        self._cjk_family = self.font_families.get("cjk", "")

    def _on_spin(self):
        """Turns the emblem of the playing track, and drives the build clock."""
        busy = False
        if self.player.state == "playing" and self.current is not None:
            self._spin = (self._spin + 4.0) % 360.0
            busy = True
        if self._build is not None:
            self._tick_build()
            busy = True
        if busy:
            self.update()

    def sprite(self, key, w, h):
        """A skin sprite scaled to w x h, cached.  None when unavailable."""
        name = SPRITES[self.skin].get(key) if key in SPRITES[self.skin] else key
        if not name or w <= 0 or h <= 0:
            return None
        ck = (name, w, h)
        hit = self._sprite_cache.get(ck)
        if hit is not None or ck in self._sprite_cache:
            return hit
        img = self.atlas.sprite(name)
        pm = None
        if img is not None and not img.isNull():
            pm = QPixmap.fromImage(img.scaled(w, h, Qt.IgnoreAspectRatio,
                                              Qt.SmoothTransformation))
        self._sprite_cache[ck] = pm
        return pm

    def font(self, frac, bold=False):
        """A font whose pixel size is a fraction of the window height."""
        f = QFont(self._ui_family)
        f.setPixelSize(max(8, int(round(self.height() * frac))))
        f.setBold(bold)
        if self._cjk_family:
            f.setFamilies([self._ui_family, self._cjk_family])
        return f

    # -- persistence -----------------------------------------------------
    def _restore(self):
        try:
            with open(config_path(), encoding="utf-8") as f:
                st = json.load(f)
        except (OSError, ValueError):
            return
        by_name = {t.filename.lower(): t for t in self.data.tracks}
        self.playlist = [by_name[n.lower()] for n in st.get("playlist", [])
                         if n.lower() in by_name]
        self.filters.update({k: bool(v) for k, v in st.get("filters", {}).items()
                             if k in self.filters})
        self.shuffle = bool(st.get("shuffle", self.shuffle))
        self.gap = float(st.get("gap", self.gap))
        self.volume = float(st.get("volume", self.volume))
        self.player.set_volume(self.volume)

    def save(self):
        p = config_path()
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"playlist": [t.filename for t in self.playlist],
                           "filters": self.filters, "shuffle": self.shuffle,
                           "gap": self.gap, "volume": self.volume}, f, indent=1)
        except OSError:
            pass

    # -- model -----------------------------------------------------------
    @property
    def available(self):
        f = self.filters
        out = []
        for t in self.data.tracks:
            if not f.get(t.game, True):
                continue
            if not f.get(t.type, True):
                continue
            out.append(t)
        return out

    def _advance(self):
        if not self.playlist:
            return
        if self.shuffle:
            nxt = random.choice(self.playlist)
        else:
            try:
                i = self.playlist.index(self.current)
            except ValueError:
                i = -1
            nxt = self.playlist[(i + 1) % len(self.playlist)]
        QTimer.singleShot(int(self.gap * 1000), lambda: self.play(nxt))

    def play(self, track):
        self.current = track
        self._status = ""
        self.player.load(self.data.track_wav(track))
        self.update()

    # -- changing the skin, the way the game puts up a building -----------
    def start_skin_change(self):
        """Building sound, faction emblem under a build clock, then the swap."""
        if self._build is not None:
            return
        nxt = SKIN_ORDER[(SKIN_ORDER.index(self.skin) + 1) % len(SKIN_ORDER)]
        self._build = {"t0": time.monotonic(), "target": nxt, "stage": 0}
        self._play_sfx(nxt, "building")
        self.update()

    def _play_sfx(self, skin, which):
        stem = SKIN_SFX.get(skin, {}).get(which)
        if stem:
            play_effect(self.data.sfx(stem), min(1.0, self.volume + 0.15))

    def _tick_build(self):
        b = self._build
        if b is None:
            return
        elapsed = time.monotonic() - b["t0"]
        if b["stage"] == 0 and elapsed >= BUILD_SECONDS:
            b["stage"] = 1                       # clock full: construction done
            self._play_sfx(b["target"], "complete")
            b["t0"] = time.monotonic()
        elif b["stage"] == 1 and elapsed >= 0.9:
            target = b["target"]
            self._build = None
            self.apply_skin(target)
            self._play_sfx(target, "place")      # the building goes down

    def apply_skin(self, name):
        if name not in SKIN_BUI:
            return
        self.skin = name
        self.accent = ACCENT[name]
        self.layout_ = Layout(self.data.config.get(SKIN_BUI[name]))
        self.bg_img, self.scan_img = self.tex.skin(name)
        self.menu_img = self.tex.menu_background(name)
        self._bg_cache = self._scan_cache = self._menu_cache = None
        self._sprite_cache = {}
        self._load_fonts()
        self.save()
        self.update()

    def _on_audio_error(self, msg):
        self._status = msg
        self.update()

    # -- geometry --------------------------------------------------------
    def surface(self):
        """Where the skin is drawn, so that its solid frame fills the window.

        The background texture carries a soft drop shadow around the metal
        frame - in the game it blends into the menu behind it, but a standalone
        window must not show it as a black margin.  Measured on the alpha
        channel, the fully opaque frame occupies x 47..2113, y 33..1585 of the
        2160x1620 texture, so the drawing surface is scaled up by that inset
        and the shadow falls outside the window.  Widget rectangles are
        resolved against the same surface and therefore stay aligned.
        """
        W, H = self.width(), self.height()
        cw = min(W, int(H * FRAME_ASPECT))
        ch = int(cw / FRAME_ASPECT)
        cx, cy = (W - cw) // 2, (H - ch) // 2
        sw, sh = cw / CROP[2], ch / CROP[3]
        return QRect(int(round(cx - CROP[0] * sw)), int(round(cy - CROP[1] * sh)),
                     int(round(sw)), int(round(sh)))

    def r(self, key):
        s = self.surface()
        x, y, w, h = self.layout_[key].px(s.width(), s.height())
        return QRect(s.x() + x, s.y() + y, w, h)

    def row_height(self):
        return max(14, self.r("available_row").height())

    # -- painting --------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.fillRect(self.rect(), QColor(8, 8, 10))
        s = self.surface()

        # The menu background sits behind everything; Tiberian Dawn's list
        # panels are transparent and show it through.
        if self.menu_img is not None:
            if self._menu_cache is None or self._menu_cache.size() != self.size():
                self._menu_cache = QPixmap.fromImage(
                    self.menu_img.scaled(self.size(), Qt.KeepAspectRatioByExpanding,
                                         Qt.SmoothTransformation))
            p.drawPixmap(0, 0, self._menu_cache)
            # The layouts stack a Background_Darken over it; without a strong
            # dim the menu artwork reads straight through Tiberian Dawn's
            # transparent list panels.
            p.fillRect(self.rect(), QColor(6, 10, 8, 226))

        if self.bg_img is not None:
            if self._bg_cache is None or self._bg_cache.size() != s.size():
                self._bg_cache = QPixmap.fromImage(
                    self.bg_img.scaled(s.size(), Qt.IgnoreAspectRatio,
                                       Qt.SmoothTransformation))
            p.drawPixmap(s, self._bg_cache)
        if self.scan_img is not None:
            if self._scan_cache is None or self._scan_cache.size() != s.size():
                self._scan_cache = QPixmap.fromImage(
                    self.scan_img.scaled(s.size(), Qt.IgnoreAspectRatio,
                                         Qt.SmoothTransformation))
            p.setOpacity(0.5)
            p.drawPixmap(s, self._scan_cache)
            p.setOpacity(1.0)

        self.hits = []
        self._paint_header(p)
        self._paint_chrome(p)
        self._paint_lists(p)
        self._paint_transfer_buttons(p)
        self._paint_options(p)
        self._paint_now_playing(p)
        self._paint_footer(p)
        self._paint_build_overlay(p)
        self._paint_tooltip(p)
        p.end()

    def _text(self, p, rect, s, frac, color=TEXT, align=Qt.AlignLeft | Qt.AlignVCenter,
              bold=False, elide=True):
        p.setFont(self.font(frac, bold))
        p.setPen(color)
        if elide:
            fm = QFontMetrics(p.font())
            s = fm.elidedText(s, Qt.ElideRight, rect.width())
        p.drawText(rect, align, s)

    def _paint_header(self, p):
        t = self.data
        self._text(p, self.r("title"), t.text("TEXT_JUKEBOX_PLAYLIST_EDITOR"),
                   0.0345, TEXT, Qt.AlignHCenter | Qt.AlignVCenter)
        r = self.r("notice")
        p.setFont(self.font(0.0135))
        p.setPen(TEXT_DIM)
        p.drawText(r, Qt.AlignHCenter | Qt.AlignVCenter | Qt.TextWordWrap,
                   t.text("TEXT_JUKEBOX_OVERRIDES_GAME_LOGIC_NOTIFICATION"))

    def _circle(self, spec):
        s = self.surface()
        cx = s.x() + spec[0] * s.width()
        cy = s.y() + spec[1] * s.height()
        r = spec[2] * s.width()
        return QRect(int(cx - r), int(cy - r), int(2 * r), int(2 * r))

    def _paint_chrome(self, p):
        """The two bolts and the folder button, as hit areas over the skin.

        The bolts are part of the background texture, so nothing is drawn over
        them - only a soft ring while hovered, to show they can be used.
        """
        t = self.data
        left = self._circle(BOLT_LEFT)
        right = self._circle(BOLT_RIGHT)
        for rect, kind, tip in (
                (left, "github", t.text("TEXT_JUKEBOX", "Jukebox") + " - GitHub"),
                (right, "skin", self._skin_tip())):
            hovered = self._hover is not None and self._hover.kind == kind
            if hovered:
                p.setPen(QPen(QColor(255, 220, 130, 200), max(2, rect.width() // 10)))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(rect.adjusted(-3, -3, 3, 3))
            self.hits.append(Hit(rect, kind, tip=tip))

        folder = self._circle(FOLDER_BUTTON)
        self._paint_folder(p, folder,
                           self._hover is not None and self._hover.kind == "folder")
        self.hits.append(Hit(folder, "folder", tip=self.data.soundtrack_dir()))

    def _skin_tip(self):
        nxt = SKIN_ORDER[(SKIN_ORDER.index(self.skin) + 1) % len(SKIN_ORDER)]
        names = {"td": self.data.text("TEXT_JUKEBOX_FILTER_TD"),
                 "soviet": self.data.text("TEXT_JUKEBOX_FILTER_RA"),
                 "allied": self.data.text("TEXT_JUKEBOX_FILTER_RA")}
        side = {"soviet": " (Soviet)", "allied": " (Allied)", "td": ""}
        return names.get(nxt, nxt) + side.get(nxt, "")

    def _paint_folder(self, p, rect, hovered):
        """A folder drawn in the skin's own accent colour."""
        p.save()
        p.setRenderHint(QPainter.Antialiasing, True)
        c = self.accent.lighter(150) if hovered else self.accent
        w, h = rect.width(), rect.height()
        body = QRectF(rect.x(), rect.y() + h * 0.26, w, h * 0.60)
        tab = QRectF(rect.x(), rect.y() + h * 0.14, w * 0.44, h * 0.18)
        p.setPen(QPen(QColor(18, 18, 20), max(1, w // 14)))
        p.setBrush(c.darker(140))
        p.drawRoundedRect(tab, w * 0.06, w * 0.06)
        p.setBrush(c)
        p.drawRoundedRect(body, w * 0.08, w * 0.08)
        p.setPen(QPen(c.lighter(170), max(1, w // 16)))
        p.drawLine(int(body.left() + w * 0.14), int(body.top() + h * 0.14),
                   int(body.right() - w * 0.14), int(body.top() + h * 0.14))
        p.restore()

    def _list_geometry(self, which):
        box = self.r(which + "_list")
        inner = QRect(box.x() + 4, box.y() + 3,
                      box.width() - self.r(which + "_scroll").width() - 8,
                      box.height() - 6)
        return box, inner

    def _paint_lists(self, p):
        t = self.data
        av, pl = self.available, self.playlist
        total_av = sum(x.seconds or 0 for x in av)
        total_pl = sum(x.seconds or 0 for x in pl)

        self._text(p, self.r("available_label"),
                   "%s (%d / %d) - %s" % (t.text("TEXT_JUKEBOX_AVAILABLE_TRACKS_WITH_COUNTS"),
                                          len(av), len(t.tracks), hms(total_av)),
                   0.0165, TEXT)
        self._text(p, self.r("playlist_label"),
                   "%s (%d) - %s" % (t.text("TEXT_JUKEBOX_CUSTOM_PLAYLIST_TRACKS_WITH_COUNT"),
                                     len(pl), hms(total_pl)),
                   0.0165, TEXT_GREEN)

        self._paint_list(p, "available", av, self.sel_available)
        self._paint_list(p, "playlist", pl, self.sel_playlist)

    def _paint_list(self, p, which, items, selected):
        box, inner = self._list_geometry(which)
        rh = self.row_height()
        p.save()
        p.setClipRect(inner)
        first = int(self.scroll[which] // rh)
        y0 = inner.y() - int(self.scroll[which] % rh)
        n = inner.height() // rh + 2
        for i in range(first, min(first + n, len(items))):
            track = items[i]
            y = y0 + (i - first) * rh
            row = QRect(inner.x(), y, inner.width(), rh)
            if track is selected:
                pm = self.sprite("row_hover", row.width(), row.height())
                if pm is not None:
                    p.drawPixmap(row, pm)
                else:
                    p.fillRect(row, QColor(self.accent.red(), self.accent.green(),
                                           self.accent.blue(), 130))
            if track is self.current:
                p.fillRect(QRect(row.x(), row.y(), 3, row.height()), GOLD)
            icon_w = int(rh * 0.95)
            self._paint_track_icon(p, QRect(row.x() + 4, row.y() + 1,
                                            icon_w, rh - 2), track)
            time_w = int(inner.width() * 0.14)
            self._text(p, QRect(row.x() + icon_w + 12, row.y(),
                                inner.width() - icon_w - time_w - 18, rh),
                       track.title, 0.0150, TEXT)
            self._text(p, QRect(row.right() - time_w, row.y(), time_w, rh),
                       track.duration_text, 0.0150, TEXT,
                       Qt.AlignRight | Qt.AlignVCenter, elide=False)
            self.hits.append(Hit(row, "row_" + which, track))
        p.restore()
        self._paint_scrollbar(p, which, len(items) * rh, inner.height())

    def _paint_track_icon(self, p, rect, track):
        """The game's own 28x28 emblem for the track's title, out of the atlas.

        If the atlas is unavailable the emblems are drawn instead: a brass ring
        for Tiberian Dawn, a hammer and sickle for Red Alert.
        """
        side = min(rect.width(), rect.height())
        if side <= 0:
            return
        box = QRect(rect.x(), rect.y() + (rect.height() - side) // 2, side, side)
        pm = self.sprite(TRACK_ICON.get(track.game, ""), side, side)
        if pm is not None:
            spin = (track is self.current and self.player.state == "playing")
            if spin:
                p.save()
                p.setRenderHint(QPainter.SmoothPixmapTransform, True)
                p.translate(box.center())
                p.rotate(self._spin)
                p.drawPixmap(QRect(-side // 2, -side // 2, side, side), pm)
                p.restore()
            else:
                p.drawPixmap(box, pm)
            return
        p.save()
        p.setRenderHint(QPainter.Antialiasing, True)
        c = QRectF(box).center()
        rad = side * 0.40
        p.translate(c)
        if track.is_ra:
            p.setPen(QPen(QColor(228, 196, 48), max(1.5, rad * 0.24),
                          Qt.SolidLine, Qt.RoundCap))
            p.drawArc(QRectF(-rad * .95, -rad * .95, rad * 1.9, rad * 1.9),
                      -30 * 16, 210 * 16)
            p.drawLine(QPoint(int(-rad * .82), int(rad * .48)),
                       QPoint(int(rad * .30), int(rad * .95)))
        else:
            p.setPen(QPen(QColor(206, 158, 60), max(1.5, rad * 0.30)))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPoint(0, 0), int(rad * .80), int(rad * .80))
        p.restore()

    def _paint_scrollbar(self, p, which, content_h, view_h):
        if content_h <= view_h:
            return                                   # nothing to scroll
        bar = self.r(which + "_scroll")
        p.fillRect(bar, QColor(0, 0, 0, 90))
        frac = view_h / float(content_h)
        knob_h = max(18, int(bar.height() * frac))
        maxscroll = content_h - view_h
        pos = int((bar.height() - knob_h) * (self.scroll[which] / maxscroll))
        knob = QRect(bar.x() + 1, bar.y() + pos, bar.width() - 2, knob_h)
        p.fillRect(knob, self.accent)
        self.hits.append(Hit(bar, "scroll_" + which, (content_h, view_h)))

    # -- buttons ---------------------------------------------------------
    def _plate(self, p, rect, label, enabled=True):
        pm = self.sprite("button", rect.width(), rect.height())
        if pm is not None:
            p.drawPixmap(rect, pm)
            self._text(p, rect, label, 0.0165,
                       TEXT if enabled else QColor(120, 120, 120),
                       Qt.AlignCenter, elide=True)
            return
        g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        g.setColorAt(0.0, QColor(126, 130, 134))
        g.setColorAt(0.5, QColor(78, 82, 86))
        g.setColorAt(1.0, QColor(46, 49, 52))
        p.setBrush(QBrush(g))
        p.setPen(QPen(QColor(28, 30, 32), 2))
        p.drawRect(rect.adjusted(1, 1, -1, -1))
        p.setPen(QPen(QColor(168, 172, 176), 1))
        p.drawLine(rect.x() + 3, rect.y() + 2, rect.right() - 3, rect.y() + 2)
        self._text(p, rect, label, 0.0165,
                   TEXT if enabled else QColor(120, 120, 120),
                   Qt.AlignCenter, elide=True)

    def _paint_transfer_buttons(self, p):
        t = self.data
        for key, kind, txt in (
                ("btn_add", "add", "TEXT_ADD_SONG"),
                ("btn_add_all", "add_all", "TEXT_ADD_ALL_SONGS"),
                ("btn_remove", "remove", "TEXT_REMOVE_SONG"),
                ("btn_remove_all", "remove_all", "TEXT_REMOVE_ALL_SONGS")):
            rect = self.r(key)
            self._plate(p, rect, t.text(txt).strip())
            self.hits.append(Hit(rect, kind))

    def _paint_footer(self, p):
        t = self.data
        for key, kind, txt in (("btn_cancel", "back", "TEXT_BACK"),
                               ("btn_apply", "apply", "TEXT_APPLY")):
            rect = self.r(key)
            self._plate(p, rect, t.text(txt))
            self.hits.append(Hit(rect, kind))

    # -- options ---------------------------------------------------------
    def _checkbox(self, p, rect, on, kind):
        side = min(rect.width(), rect.height())
        box = QRect(rect.x(), rect.y() + (rect.height() - side) // 2, side, side)
        pm = self.sprite("check_on" if on else "check_off", side, side)
        if pm is not None:
            p.drawPixmap(box, pm)
            self.hits.append(Hit(box, kind))
            return
        p.setPen(QPen(QColor(20, 20, 20), 2))
        p.setBrush(QColor(self.accent) if on else QColor(70, 26, 26)
                   if self.skin == "soviet" else QColor(40, 40, 46))
        p.drawRect(box.adjusted(1, 1, -1, -1))
        if on:
            p.setPen(QPen(QColor(255, 255, 255), max(2, side // 7),
                          Qt.SolidLine, Qt.RoundCap))
            p.drawLine(box.x() + side * 22 // 100, box.y() + side * 52 // 100,
                       box.x() + side * 42 // 100, box.y() + side * 72 // 100)
            p.drawLine(box.x() + side * 42 // 100, box.y() + side * 72 // 100,
                       box.x() + side * 78 // 100, box.y() + side * 26 // 100)
        self.hits.append(Hit(box, kind))

    def _paint_options(self, p):
        t = self.data
        rows = (("filter_td", "Tiberian_Dawn", "TEXT_JUKEBOX_FILTER_TD"),
                ("filter_ra", "Red_Alert", "TEXT_JUKEBOX_FILTER_RA"),
                ("filter_remaster", "Remaster", "TEXT_JUKEBOX_FILTER_REMASTERED"),
                ("filter_classic", "Classic", "TEXT_JUKEBOX_FILTER_CLASSIC"),
                ("filter_bonus", "Bonus", "TEXT_JUKEBOX_FILTER_BONUS"))
        for key, flag, txt in rows:
            self._checkbox(p, self.r(key + "_check"), self.filters[flag],
                           "filter:" + flag)
            label = self.r(key + "_text")
            if key in ("filter_td", "filter_ra"):
                icon = self.r(key + "_icon")
                probe = _IconTrack(key == "filter_ra")
                side = max(icon.width(), icon.height())
                self._paint_track_icon(
                    p, QRect(icon.center().x() - side // 2,
                             icon.center().y() - side // 2, side, side), probe)
            self._text(p, label, t.text(txt), 0.0165, TEXT)

        self._checkbox(p, self.r("shuffle_check"), self.shuffle, "shuffle")
        self._text(p, self.r("shuffle_text"),
                   t.text("TEXT_SHUFFLE_CUSTOM_PLAYLIST"), 0.0165, TEXT)

        self._text(p, self.r("gap_text"),
                   "%s: %d %s" % (t.text("TEXT_AMBIENT_MUSIC_GAP_DELAY_SECONDS_LABEL"),
                                  int(self.gap),
                                  t.text("TEXT_MUSIC_GAP_DELAY_TIME_SECONDS")),
                   0.0165, TEXT)
        self._slider(p, self.r("gap_slider"), self.gap / 30.0, "gap")

        self._text(p, self.r("volume_text"),
                   t.text("TEXT_VOLUME_JUKEBOX_MUSIC"), 0.0165, TEXT)
        self._slider(p, self.r("volume_slider"), self.volume, "volume")

    def _slider(self, p, rect, frac, kind):
        frac = max(0.0, min(1.0, frac))
        cy = rect.center().y()
        track = QRect(rect.x() + rect.height() // 2, cy - max(2, rect.height() // 6),
                      rect.width() - rect.height(), max(4, rect.height() // 3))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(26, 10, 10) if self.skin == "soviet" else QColor(20, 22, 28))
        p.drawRoundedRect(track, track.height() / 2.0, track.height() / 2.0)

        fw = int(track.width() * frac)
        if fw > 0:
            pm = self.sprite("fill", fw, track.height())
            if pm is not None:
                p.drawPixmap(QRect(track.x(), track.y(), fw, track.height()), pm)
            else:
                p.setBrush(self.accent)
                p.drawRoundedRect(QRect(track.x(), track.y(), fw, track.height()),
                                  track.height() / 2.0, track.height() / 2.0)

        kx = track.x() + fw
        ball = int(rect.height() * 1.05)
        pm = self.sprite("ball", ball, ball)
        if pm is not None:
            p.drawPixmap(QRect(kx - ball // 2, cy - ball // 2, ball, ball), pm)
        else:
            p.setBrush(self.accent.lighter(120))
            p.setPen(QPen(QColor(20, 20, 20), 1))
            p.drawEllipse(QPoint(kx, cy), ball // 2, ball // 2)

        sgn = int(rect.height() * 0.9)
        for name, x in ((SLIDER_MINUS, rect.x() - sgn - 4),
                        (SLIDER_PLUS, rect.right() + 4)):
            pm = self.sprite(name, sgn, sgn)
            if pm is not None:
                p.drawPixmap(QRect(x, cy - sgn // 2, sgn, sgn), pm)
        self.hits.append(Hit(rect.adjusted(-4, -6, 4, 6), "slider:" + kind))

    # -- now playing -----------------------------------------------------
    def _paint_now_playing(self, p):
        t = self.data
        btn = self.r("play_button")
        pm = self.sprite("play_hot" if self.player.state == "playing" else "play",
                         btn.width(), btn.height())
        if pm is not None:
            p.drawPixmap(btn, pm)
            self.hits.append(Hit(btn, "playpause"))
            self._paint_now_playing_text(p)
            return
        g = QLinearGradient(btn.topLeft(), btn.bottomLeft())
        g.setColorAt(0.0, QColor(120, 124, 128))
        g.setColorAt(0.5, QColor(74, 78, 82))
        g.setColorAt(1.0, QColor(44, 47, 50))
        p.setBrush(QBrush(g))
        p.setPen(QPen(QColor(28, 30, 32), 2))
        p.drawRect(btn.adjusted(1, 1, -1, -1))
        p.setPen(Qt.NoPen)
        p.setBrush(GOLD)
        h = btn.height() * 0.42
        cx, cy = btn.center().x(), btn.center().y()
        if self.player.state == "playing":
            bw = h * 0.30
            p.drawRect(QRectF(cx - bw * 1.7, cy - h / 2, bw, h))
            p.drawRect(QRectF(cx + bw * 0.7, cy - h / 2, bw, h))
        else:
            path = QPainterPath()
            path.moveTo(cx - h * 0.42, cy - h / 2)
            path.lineTo(cx + h * 0.58, cy)
            path.lineTo(cx - h * 0.42, cy + h / 2)
            path.closeSubpath()
            p.fillPath(path, GOLD)
        self.hits.append(Hit(btn, "playpause"))

        self._paint_now_playing_text(p)

    def _paint_now_playing_text(self, p):
        t = self.data
        if self._status:
            self._text(p, self.r("now_playing_text"), self._status, 0.0150,
                       QColor(230, 120, 120), Qt.AlignHCenter | Qt.AlignVCenter)
        elif self.current is not None:
            state = ("TEXT_JUKEBOX_TRACK_PLAYING_STATUS"
                     if self.player.state == "playing"
                     else "TEXT_JUKEBOX_TRACK_PAUSED_STATUS")
            self._text(p, self.r("now_playing_text"),
                       '"%s" : %s' % (self.current.title, t.text(state)),
                       0.0150, TEXT, Qt.AlignHCenter | Qt.AlignVCenter)

        dur = self.player.duration or (self.current.seconds if self.current else 0)
        self._text(p, self.r("elapsed_text"), mmss(self.player.position), 0.0135,
                   TEXT_DIM, Qt.AlignLeft | Qt.AlignVCenter, elide=False)
        self._text(p, self.r("total_text"), mmss(dur), 0.0135, TEXT_DIM,
                   Qt.AlignRight | Qt.AlignVCenter, elide=False)

        bar = self.r("progress")
        thin = max(3, bar.height() // 2)
        bar = QRect(bar.x(), bar.center().y() - thin // 2, bar.width(), thin)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(18, 18, 20))
        p.drawRect(bar)
        if dur:
            w = int(bar.width() * max(0.0, min(1.0, self.player.position / dur)))
            p.setBrush(QColor(196, 196, 196))
            p.drawRect(QRect(bar.x(), bar.y(), w, bar.height()))
        self.hits.append(Hit(self.r("progress_hit"), "seek"))

    def _paint_build_overlay(self, p):
        """The faction emblem under a build clock while the skin is changing.

        The clock is the one from the sidebar: a dark wedge that sweeps once
        around from the top, uncovering the emblem as it goes.
        """
        b = self._build
        if b is None:
            return
        s = self.surface()
        p.fillRect(self.rect(), QColor(0, 0, 0, 150))

        side = int(min(s.width(), s.height()) * 0.55)
        box = QRect(s.center().x() - side // 2, s.center().y() - side // 2, side, side)
        pm = self.sprite(SKIN_LOGO.get(b["target"], ""), side, side)
        if pm is not None:
            p.drawPixmap(box, pm)

        if b["stage"] == 0:
            frac = min(1.0, (time.monotonic() - b["t0"]) / BUILD_SECONDS)
            clock = QRect(box)
            clock.adjust(-box.width() // 12, -box.height() // 12,
                         box.width() // 12, box.height() // 12)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 205))
            # Qt angles count 1/16 degree counter-clockwise from 3 o'clock, so
            # the wedge starts at the top and retreats clockwise.
            start = int((90 - 360.0 * frac) * 16)
            span = int(-360.0 * (1.0 - frac) * 16)
            p.drawPie(clock, start, span)
            # The leading edge, so the sweep is readable at a glance.
            ang = math.radians(90 - 360.0 * frac)
            cx, cy = clock.center().x(), clock.center().y()
            rx, ry = clock.width() / 2.0, clock.height() / 2.0
            p.setPen(QPen(self.accent.lighter(160), max(2, clock.width() // 110)))
            p.drawLine(cx, cy, int(cx + math.cos(ang) * rx),
                       int(cy - math.sin(ang) * ry))
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(255, 255, 255, 70), max(1, clock.width() // 200)))
            p.drawEllipse(clock)

        label = self.data.text("TEXT_JUKEBOX_FILTER_TD" if b["target"] == "td"
                               else "TEXT_JUKEBOX_FILTER_RA")
        self._text(p, QRect(s.x(), box.bottom() + int(s.height() * 0.02),
                            s.width(), int(s.height() * 0.05)),
                   label, 0.030, TEXT, Qt.AlignCenter)

    def _paint_tooltip(self, p):
        h = self._hover
        if h is None or not h.tip:
            return
        p.setFont(self.font(0.0145))
        fm = QFontMetrics(p.font())
        pad = max(6, int(self.height() * 0.008))
        w = fm.horizontalAdvance(h.tip) + 2 * pad
        ht = fm.height() + pad
        x = min(max(4, h.rect.center().x() - w // 2), self.width() - w - 4)
        y = h.rect.bottom() + 6
        if y + ht > self.height():
            y = h.rect.top() - ht - 6
        box = QRect(x, y, w, ht)
        p.setPen(QPen(QColor(20, 20, 22), 2))
        p.setBrush(QColor(16, 16, 18, 235))
        p.drawRoundedRect(box, 3, 3)
        p.setPen(TEXT)
        p.drawText(box, Qt.AlignCenter, h.tip)

    def open_track_folder(self):
        path = self.data.soundtrack_dir()
        try:
            os.makedirs(path, exist_ok=True)
            subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        except OSError as e:
            self._status = str(e)
            self.update()

    # -- interaction -----------------------------------------------------
    def _hit(self, pos):
        for h in reversed(self.hits):
            if h.rect.contains(pos):
                return h
        return None

    def mousePressEvent(self, ev):
        h = self._hit(ev.pos())
        if h is None:
            # Nothing interactive here: start moving the frameless window.
            if ev.button() == Qt.LeftButton:
                self._drag_window = (ev.globalPos() -
                                     self.frameGeometry().topLeft())
            return
        kind = h.kind
        right = ev.button() == Qt.RightButton

        if kind == "row_available":
            self.sel_available = h.data
            if right:
                self._add(h.data)
            elif ev.type() == ev.MouseButtonDblClick:
                self.play(h.data)
        elif kind == "row_playlist":
            self.sel_playlist = h.data
            if right:
                self._remove(h.data)
            else:
                self.play(h.data)
        elif right:
            return
        elif kind == "add":
            self._add(self.sel_available)
        elif kind == "add_all":
            for t in self.available:
                self._add(t)
        elif kind == "remove":
            self._remove(self.sel_playlist)
        elif kind == "remove_all":
            self.playlist = []
        elif kind == "github":
            subprocess.Popen(["xdg-open", PROJECT_URL],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif kind == "skin":
            self.start_skin_change()
        elif kind == "folder":
            self.open_track_folder()
        elif kind == "playpause":
            if self.current is None and self.playlist:
                self.play(self.playlist[0])
            else:
                self.player.toggle()
        elif kind == "shuffle":
            self.shuffle = not self.shuffle
        elif kind.startswith("filter:"):
            flag = kind.split(":", 1)[1]
            self.filters[flag] = not self.filters[flag]
            self.scroll["available"] = 0.0
        elif kind.startswith("slider:") or kind == "seek":
            self._drag = kind
            self._drag_to(ev.pos())
        elif kind.startswith("scroll_"):
            self._drag = kind
            self._drag_to(ev.pos())
        elif kind == "apply":
            self.save()
            self.closed.emit()
            self.close()
        elif kind == "back":
            self.closed.emit()
            self.close()
        self.update()

    def mouseDoubleClickEvent(self, ev):
        h = self._hit(ev.pos())
        if h is not None and h.kind == "row_available":
            self.play(h.data)
        self.update()

    def mouseMoveEvent(self, ev):
        if self._drag_window is not None and ev.buttons() & Qt.LeftButton:
            self.move(ev.globalPos() - self._drag_window)
            return
        if self._drag:
            self._drag_to(ev.pos())
            self.update()
            return
        was = self._hover
        self._hover = self._hit(ev.pos())
        if was is not self._hover:
            self.update()

    def leaveEvent(self, _):
        if self._hover is not None:
            self._hover = None
            self.update()

    def mouseReleaseEvent(self, _):
        self._drag = None
        self._drag_window = None

    def _drag_to(self, pos):
        kind = self._drag
        if kind is None:
            return
        if kind == "slider:volume":
            r = self.r("volume_slider")
            self.volume = max(0.0, min(1.0, (pos.x() - r.x()) / float(r.width())))
            self.player.set_volume(self.volume)
        elif kind == "slider:gap":
            r = self.r("gap_slider")
            f = max(0.0, min(1.0, (pos.x() - r.x()) / float(r.width())))
            self.gap = round(f * 30.0)
        elif kind == "seek":
            r = self.r("progress")
            dur = self.player.duration
            if dur:
                f = max(0.0, min(1.0, (pos.x() - r.x()) / float(r.width())))
                self.player.seek(f * dur)
        elif kind.startswith("scroll_"):
            which = kind.split("_", 1)[1]
            bar = self.r(which + "_scroll")
            items = self.available if which == "available" else self.playlist
            _, inner = self._list_geometry(which)
            content = len(items) * self.row_height()
            if content > inner.height():
                f = max(0.0, min(1.0, (pos.y() - bar.y()) / float(bar.height())))
                self.scroll[which] = f * (content - inner.height())

    def wheelEvent(self, ev):
        for which in ("available", "playlist"):
            box, inner = self._list_geometry(which)
            if box.contains(ev.pos()):
                items = self.available if which == "available" else self.playlist
                content = len(items) * self.row_height()
                step = ev.angleDelta().y() / 120.0 * self.row_height() * 3
                self.scroll[which] = max(
                    0.0, min(max(0.0, content - inner.height()),
                             self.scroll[which] - step))
                self.update()
                return

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_Escape:
            self.closed.emit()
            self.close()
        elif ev.key() == Qt.Key_Space:
            self.player.toggle()
        elif ev.key() == Qt.Key_F11:
            self.showNormal() if self.isFullScreen() else self.showFullScreen()
        self.update()

    def resizeEvent(self, _):
        self._bg_cache = None
        self._scan_cache = None
        self._menu_cache = None

    def closeEvent(self, ev):
        self.save()
        self.player.stop()
        ev.accept()

    # -- playlist edits --------------------------------------------------
    def _add(self, track):
        if track is not None and track not in self.playlist:
            self.playlist.append(track)

    def _remove(self, track):
        if track in self.playlist:
            self.playlist.remove(track)
            if self.sel_playlist is track:
                self.sel_playlist = None
