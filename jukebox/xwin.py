# -*- coding: utf-8 -*-
"""Just enough X11 to find another program's window and read its geometry.

The game's launcher is a Windows binary running under Proton, so there is no
way to ask it anything - but the window manager knows where its window is, and
that is all this needs.  libX11 is loaded through ctypes rather than adding a
dependency: any machine showing an X session already has it.

Wayland sessions are out of reach by design, and the caller falls back to a
fixed position there.
"""

import ctypes
import ctypes.util
import os
import re

Atom = ctypes.c_ulong
Window = ctypes.c_ulong

_XA_CARDINAL = 6
_XA_WINDOW = 33
_XA_STRING = 31
_IS_VIEWABLE = 2


class _Attrs(ctypes.Structure):
    """XWindowAttributes, as far as map_state; the rest is not needed."""

    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int),
                ("width", ctypes.c_int), ("height", ctypes.c_int),
                ("border_width", ctypes.c_int), ("depth", ctypes.c_int),
                ("visual", ctypes.c_void_p), ("root", Window),
                ("c_class", ctypes.c_int), ("bit_gravity", ctypes.c_int),
                ("win_gravity", ctypes.c_int), ("backing_store", ctypes.c_int),
                ("backing_planes", ctypes.c_ulong),
                ("backing_pixel", ctypes.c_ulong),
                ("save_under", ctypes.c_int), ("colormap", ctypes.c_ulong),
                ("map_installed", ctypes.c_int), ("map_state", ctypes.c_int),
                ("all_event_masks", ctypes.c_long),
                ("your_event_mask", ctypes.c_long),
                ("do_not_propagate_mask", ctypes.c_long),
                ("override_redirect", ctypes.c_int),
                ("screen", ctypes.c_void_p)]


class _X(object):
    """The handful of libX11 calls used here, or nothing at all."""

    def __init__(self):
        self.lib = None
        self.dpy = None
        name = ctypes.util.find_library("X11")
        if not name:
            return
        try:
            lib = ctypes.CDLL(name)
        except OSError:
            return

        lib.XOpenDisplay.restype = ctypes.c_void_p
        lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
        lib.XDefaultRootWindow.restype = Window
        lib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        lib.XInternAtom.restype = Atom
        lib.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        lib.XGetWindowProperty.restype = ctypes.c_int
        lib.XGetWindowProperty.argtypes = [
            ctypes.c_void_p, Window, Atom, ctypes.c_long, ctypes.c_long,
            ctypes.c_int, Atom, ctypes.POINTER(Atom), ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte))]
        lib.XFree.argtypes = [ctypes.c_void_p]
        lib.XGetGeometry.restype = ctypes.c_int
        lib.XGetGeometry.argtypes = [
            ctypes.c_void_p, Window, ctypes.POINTER(Window),
            ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint),
            ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint)]
        lib.XTranslateCoordinates.restype = ctypes.c_int
        lib.XTranslateCoordinates.argtypes = [
            ctypes.c_void_p, Window, Window, ctypes.c_int, ctypes.c_int,
            ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(Window)]
        lib.XSetTransientForHint.argtypes = [ctypes.c_void_p, Window, Window]
        lib.XFlush.argtypes = [ctypes.c_void_p]
        lib.XGetWindowAttributes.restype = ctypes.c_int
        lib.XGetWindowAttributes.argtypes = [ctypes.c_void_p, Window,
                                             ctypes.POINTER(_Attrs)]
        lib.XQueryTree.restype = ctypes.c_int
        lib.XQueryTree.argtypes = [
            ctypes.c_void_p, Window, ctypes.POINTER(Window),
            ctypes.POINTER(Window), ctypes.POINTER(ctypes.POINTER(Window)),
            ctypes.POINTER(ctypes.c_uint)]
        lib.XSetErrorHandler.restype = ctypes.c_void_p
        lib.XSetErrorHandler.argtypes = [ctypes.c_void_p]

        dpy = lib.XOpenDisplay(None)
        if not dpy:
            return
        # A window can vanish between listing it and asking about it; the
        # default handler would take the whole process down for that.
        self._handler = ctypes.CFUNCTYPE(
            ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)(lambda d, e: 0)
        lib.XSetErrorHandler(self._handler)
        self.lib, self.dpy = lib, dpy

    @property
    def ok(self):
        return self.lib is not None

    def atom(self, name):
        return self.lib.XInternAtom(self.dpy, name.encode("ascii"), False)

    def prop(self, win, name, want):
        """One window property, as raw bytes plus its item count."""
        actual_type, fmt = Atom(), ctypes.c_int()
        nitems, after = ctypes.c_ulong(), ctypes.c_ulong()
        data = ctypes.POINTER(ctypes.c_ubyte)()
        rc = self.lib.XGetWindowProperty(
            self.dpy, win, self.atom(name), 0, 4096, False, want,
            ctypes.byref(actual_type), ctypes.byref(fmt), ctypes.byref(nitems),
            ctypes.byref(after), ctypes.byref(data))
        if rc != 0 or not data:
            return None, 0, 0
        width = {8: 1, 16: 2, 32: ctypes.sizeof(ctypes.c_long)}.get(fmt.value, 0)
        n = nitems.value
        raw = ctypes.string_at(data, n * width) if width else b""
        self.lib.XFree(data)
        return raw, n, fmt.value

    def pid(self, win):
        """The process that owns the window, if it says so."""
        raw, n, fmt = self.prop(win, "_NET_WM_PID", _XA_CARDINAL)
        if not raw or not n:
            return 0
        step = ctypes.sizeof(ctypes.c_long) if fmt == 32 else 4
        return int.from_bytes(raw[:step], "little")

    def title(self, win):
        raw, n, _ = self.prop(win, "_NET_WM_NAME", 0)
        if raw:
            return raw.decode("utf-8", "replace")
        raw, n, _ = self.prop(win, "WM_NAME", _XA_STRING)
        return raw.decode("latin-1", "replace") if raw else ""

    def _window_list(self, name):
        root = self.lib.XDefaultRootWindow(self.dpy)
        raw, n, _ = self.prop(root, name, _XA_WINDOW)
        if not raw or not n:
            return None
        step = ctypes.sizeof(ctypes.c_long)
        return [int.from_bytes(raw[i * step:(i + 1) * step], "little")
                for i in range(n)]

    def stacking(self):
        """Top-level windows from the bottom of the pile upwards, or []."""
        return self._window_list("_NET_CLIENT_LIST_STACKING") or []

    def clients(self):
        """Every window currently on screen, however the desktop says so."""
        root = self.lib.XDefaultRootWindow(self.dpy)
        for name in ("_NET_CLIENT_LIST", "_NET_CLIENT_LIST_STACKING"):
            wins = self._window_list(name)
            if wins:
                # Minimised windows stay in the list; on screen they are not.
                return [w for w in wins if self.viewable(w)]
        # No window manager, or one that keeps no list: every child of the
        # root is a candidate, but only the mapped ones are on screen.
        return [w for w in self.children(root) if self.viewable(w)]

    def viewable(self, win):
        a = _Attrs()
        if not self.lib.XGetWindowAttributes(self.dpy, win, ctypes.byref(a)):
            return False
        return a.map_state == _IS_VIEWABLE

    def children(self, win):
        r, parent = Window(), Window()
        kids = ctypes.POINTER(Window)()
        n = ctypes.c_uint()
        if not self.lib.XQueryTree(self.dpy, win, ctypes.byref(r),
                                   ctypes.byref(parent), ctypes.byref(kids),
                                   ctypes.byref(n)):
            return []
        out = [kids[i] for i in range(n.value)] if kids else []
        if kids:
            self.lib.XFree(kids)
        return out

    def framed(self, win):
        """The window the manager wrapped around this one, or the window.

        The client's own origin sits inside the decoration, so "directly
        below the launcher" has to mean below the frame.  Walking up to the
        child of the root finds it; an undecorated window - which is what the
        launcher is, since it draws its own close button - is its own frame.
        """
        root = self.lib.XDefaultRootWindow(self.dpy)
        cur = win
        for _ in range(16):
            r, parent = Window(), Window()
            kids = ctypes.POINTER(Window)()
            n = ctypes.c_uint()
            if not self.lib.XQueryTree(self.dpy, cur, ctypes.byref(r),
                                       ctypes.byref(parent), ctypes.byref(kids),
                                       ctypes.byref(n)):
                return cur
            if kids:
                self.lib.XFree(kids)
            if parent.value in (0, root):
                return cur
            cur = parent.value
        return win

    def geometry(self, win):
        """(x, y, w, h) on the screen, frame included, or None."""
        root = Window()
        x, y = ctypes.c_int(), ctypes.c_int()
        w, h = ctypes.c_uint(), ctypes.c_uint()
        bw, depth = ctypes.c_uint(), ctypes.c_uint()
        if not self.lib.XGetGeometry(self.dpy, win, ctypes.byref(root),
                                     ctypes.byref(x), ctypes.byref(y),
                                     ctypes.byref(w), ctypes.byref(h),
                                     ctypes.byref(bw), ctypes.byref(depth)):
            return None
        ax, ay, child = ctypes.c_int(), ctypes.c_int(), Window()
        if not self.lib.XTranslateCoordinates(self.dpy, win, root.value, 0, 0,
                                              ctypes.byref(ax), ctypes.byref(ay),
                                              ctypes.byref(child)):
            return None
        return ax.value, ay.value, w.value, h.value


_x = None


def _display():
    global _x
    if _x is None:
        _x = _X()
    return _x if _x.ok else None


def available():
    return _display() is not None


def stacking():
    x = _display()
    return x.stacking() if x is not None else []


def keep_above(win, parent):
    """Tie one window to another, so the desktop keeps it just above.

    This is what a dialog does to the window it belongs to, and it is the
    behaviour wanted here: above the launcher, below everything else, and
    gone from the screen when the launcher is.
    """
    x = _display()
    if x is None:
        return False
    try:
        x.lib.XSetTransientForHint(x.dpy, Window(win), Window(parent))
        x.lib.XFlush(x.dpy)
        return True
    except Exception:
        return False


def find_window_id(pattern):
    """The window id whose title matches, or 0."""
    x = _display()
    if x is None:
        return 0
    rx = re.compile(pattern, re.I)
    for win in x.clients():
        try:
            if rx.search(x.title(win)):
                return win
        except Exception:
            continue
    return 0


def process_name(pid):
    """What the process is called, as far as /proc will say.

    Under Proton this is the Windows executable's own name: the launcher
    reports "ClientLauncherG", which is what identifies its window past any
    doubt - its title is only "CnCRemastered", which the game itself may
    equally use.
    """
    if not pid:
        return ""
    try:
        with open("/proc/%d/comm" % pid) as f:
            name = f.read().strip()
    except OSError:
        return ""
    return os.path.splitext(name)[0]


def windows():
    """[(win, title, pid, (x, y, w, h))] for every window now on screen."""
    x = _display()
    if x is None:
        return []
    out = []
    for win in x.clients():
        try:
            geo = x.geometry(x.framed(win))
            if geo and geo[2] > 1 and geo[3] > 1:
                out.append((win, x.title(win), x.pid(win), geo))
        except Exception:
            continue
    return out


def find_window(pattern):
    """(x, y, w, h) of the first mapped window whose title matches, or None."""
    rx = re.compile(pattern, re.I)
    for _win, title, _pid, geo in windows():
        if rx.search(title):
            return geo
    return None
