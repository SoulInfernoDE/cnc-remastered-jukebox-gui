# -*- coding: utf-8 -*-
"""Reads the jukebox geometry out of the game's own .BUI layout files.

A .BUI is a 36-byte "CH" header followed by a zlib stream holding a tagged
property list.  Two tags carry what a rebuild needs:

    0x02, length 0x10   the widget rectangle, four floats (x, y, w, h)
                        normalised against the parent
    0x05, uint32 length the widget name

Widgets appear depth-first, and the rectangle of a widget precedes its name,
so pairing each rectangle with the next name recovers the flat list.  The
nesting itself is not encoded in a form we decode, so the ancestry of the few
widgets we care about is declared in PATHS below and resolved by walking that
flat list in order.

Sanity check for the whole model: the jukebox frame is stored as 0.75156 wide
by 1.00370 high.  On a 16:9 screen that is 12.02 by 9.03 units - exactly the
4:3 of the frame texture (2160x1620).  So the frame group is positioned in
screen space, and everything below it is relative to the group.
"""

import re
import struct
import zlib

# Widgets whose stored rectangle is in screen space rather than relative to
# the frame group.  Everything else nests normally.
SCREEN_SPACE = ("MusicJukeboxDialog", "SovietJukebox_Group", "AlliesJukebox_Group",
                "Header", "Apply_Button", "Cancel_Button", "Add_Song_Button",
                "Add_All_Songs_Button", "Remove_Song_Button",
                "Remove_All_Songs_Button", "Text_Loading")

# name -> chain of widget names from the frame group down to the widget
PATHS = {
    "available":            ["Available_Songs"],
    "available_label":      ["Available_Songs", "Available_Songs_Text"],
    "available_list":       ["Available_Songs", "Available_Songs_Listbox"],
    "available_row":        ["Available_Songs", "Available_Songs_Listbox_Sample_Entry"],
    "available_scroll":     ["Available_Songs", "Available_Songs_Listbox", "Scroll_Bar"],

    "playlist":             ["Custom_Playlist"],
    "playlist_label":       ["Custom_Playlist", "Custom_Playlist_Text"],
    "playlist_list":        ["Custom_Playlist", "Custom_Playlist_Listbox"],
    "playlist_row":         ["Custom_Playlist", "Custom_Playlist_Listbox_Sample_Entry"],
    "playlist_scroll":      ["Custom_Playlist", "Custom_Playlist_Listbox", "Scroll_Bar"],

    "filters":              ["Filter_List"],
    "filter_td_check":      ["Filter_List", "Filter_TD_Checkbox"],
    "filter_td_text":       ["Filter_List", "Filter_TD_Text"],
    "filter_td_icon":       ["Filter_List", "Tiberian_Dawn_Icon"],
    "filter_ra_check":      ["Filter_List", "Filter_RA_Checkbox"],
    "filter_ra_text":       ["Filter_List", "Filter_RA_Text"],
    "filter_ra_icon":       ["Filter_List", "Red_Alert_Icon"],
    "filter_remaster_check": ["Filter_List", "Filter_Remastered_Checkbox"],
    "filter_remaster_text": ["Filter_List", "Filter_Remastered_Text"],
    "filter_classic_check": ["Filter_List", "Filter_Classic_Checkbox"],
    "filter_classic_text":  ["Filter_List", "Filter_Classic_Text"],
    "filter_bonus_check":   ["Filter_List", "Filter_Bonus_Checkbox"],
    "filter_bonus_text":    ["Filter_List", "Filter_Bonus_Text"],

    "shuffle_check":        ["Filter_List", "Shuffle_Songs_Checkbox"],
    "shuffle_text":         ["Filter_List", "Shuffle_Songs_Text"],
    "gap_text":             ["Filter_List", "Gap_Delay_Text"],
    "gap_slider":           ["Filter_List", "Gap_Delay_Slider_Bar"],
    "volume_text":          ["Filter_List", "Volume_Slider_Music_Jukebox_Text"],
    "volume_slider":        ["Filter_List", "VOLUME_SLIDER_MUSIC_JUKEBOX"],

    "now_playing":          ["Current_Playing_Song"],
    "play_button":          ["Current_Playing_Song", "Play_Pause_Button"],
    "now_playing_text":     ["Current_Playing_Song", "Current_Playing_Song_Text"],
    "elapsed_text":         ["Current_Playing_Song", "Current_Playing_Song_Start_Time_Text"],
    "total_text":           ["Current_Playing_Song", "Current_Playing_Song_End_Time_Text"],
    "progress":             ["Current_Playing_Song", "Current_Playing_Song_Progress_Bar"],
    "progress_hit":         ["Current_Playing_Song",
                             "Current_Playing_Song_Progress_Invisible_Slider_Bar"],
}

# Widgets stored in screen space; resolved separately against the group.
SCREEN_PATHS = {
    "header":       ["Header"],
    "title":        ["Header", "Title_Text"],
    "notice":       ["Header", "Functionality_Notificiation_Text"],
    "btn_apply":    ["Apply_Button"],
    "btn_cancel":   ["Cancel_Button"],
    "btn_add":      ["Add_Song_Button"],
    "btn_add_all":  ["Add_All_Songs_Button"],
    "btn_remove":   ["Remove_Song_Button"],
    "btn_remove_all": ["Remove_All_Songs_Button"],
}


class Rect(object):
    __slots__ = ("x", "y", "w", "h")

    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h

    def inside(self, child):
        """Resolves a child rectangle stated relative to this one."""
        return Rect(self.x + child.x * self.w, self.y + child.y * self.h,
                    child.w * self.w, child.h * self.h)

    def scaled(self, W, H):
        return Rect(self.x * W, self.y * H, self.w * W, self.h * H)

    def px(self, W, H):
        r = self.scaled(W, H)
        return int(round(r.x)), int(round(r.y)), int(round(r.w)), int(round(r.h))

    def __repr__(self):
        return "Rect(%.5f, %.5f, %.5f, %.5f)" % (self.x, self.y, self.w, self.h)


def decompress(bui_bytes):
    off = bui_bytes.find(b"\x78\x9c")
    if off < 0:
        raise ValueError("no zlib stream in .BUI")
    return zlib.decompress(bui_bytes[off:])


def parse(bui_bytes):
    """-> ordered [(name, Rect)] as stored, without resolving the nesting."""
    u = decompress(bui_bytes)
    rects, names, i = [], [], 0
    while i < len(u) - 18:
        if u[i] == 0x02 and u[i + 1] == 0x10:
            f = struct.unpack_from("<4f", u, i + 2)
            if all(-2.0 <= v <= 2.0 for v in f) and (f[2] or f[3]):
                rects.append((i, Rect(*f)))
                i += 18
                continue
        if u[i] == 0x05 and u[i + 1] == 0 and u[i + 2] == 0 and u[i + 3] == 0:
            blen = struct.unpack_from("<I", u, i + 4)[0]
            if 2 < blen < 200:
                slen = struct.unpack_from("<H", u, i + 8)[0]
                if slen == blen - 2:
                    s = u[i + 10:i + 10 + slen]
                    if re.fullmatch(rb"[\x20-\x7e]+", s):
                        names.append((i, s.decode()))
                        i += 10 + slen
                        continue
        i += 1
    out = []
    for off, r in rects:
        nxt = [n for o, n in names if o > off]
        out.append((nxt[0] if nxt else "?", r))
    return out


class Layout(object):
    """Resolves every rectangle into coordinates relative to the frame group.

    The frame group is the window: it is exactly the background texture, so a
    widget's rectangle here maps straight onto the rendered window.
    """

    def __init__(self, bui_bytes):
        self.flat = parse(bui_bytes)
        self.group, grouped = self._find_group()
        screen = Rect(0.0, 0.0, 1.0, 1.0)
        self.rects = {}
        # Red Alert wraps the panel in a *Jukebox_Group, so those rectangles
        # are already relative to it.  Tiberian Dawn has no such group and
        # states them in screen space, which then has to be converted.
        for key, chain in PATHS.items():
            # Both cases resolve to absolute screen coordinates; only the
            # starting frame of reference differs.
            r = self._resolve(chain, self.group if grouped else screen)
            self.rects[key] = self._to_group(r)
        # The header and the buttons are in screen space in both layouts.
        for key, chain in SCREEN_PATHS.items():
            self.rects[key] = self._to_group(self._resolve(chain, screen))

    def _to_group(self, r):
        return Rect((r.x - self.group.x) / self.group.w,
                    (r.y - self.group.y) / self.group.h,
                    r.w / self.group.w, r.h / self.group.h)

    def _find_group(self):
        for name, r in self.flat:
            if name.endswith("Jukebox_Group"):
                return r, True
        # Tiberian Dawn has no group; its Frame widget occupies the same area.
        for name, r in self.flat:
            if name == "Frame" and 0.7 < r.w < 0.8:
                return r, False
        raise ValueError("no frame group in layout")

    def _resolve(self, chain, base):
        start, cur = 0, base
        for want in chain:
            for i in range(start, len(self.flat)):
                if self.flat[i][0] == want:
                    cur = cur.inside(self.flat[i][1])
                    start = i + 1
                    break
            else:
                raise KeyError("widget %r not found in layout" % want)
        return cur

    def __getitem__(self, key):
        return self.rects[key]
