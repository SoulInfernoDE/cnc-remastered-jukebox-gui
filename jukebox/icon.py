# -*- coding: utf-8 -*-
"""The application's own icon: a jukebox cabinet in a skin's colours.

The window is frameless, so this is all the task bar and the window switcher
have to go on.  It is drawn rather than shipped - the only part read from the
game is the faction emblem behind the cabinet's screen - and it is wanted in
two places, the window itself and the button beside the game's launcher, so it
lives here rather than in either of them.
"""

from PyQt5.QtCore import QPointF, QRect, QRectF, Qt
from PyQt5.QtGui import (QBrush, QColor, QIcon, QLinearGradient, QPainter,
                         QPainterPath, QPen, QPixmap, QRadialGradient)

SIZES = (32, 48, 64, 128, 256)


def pixmap(side, emblem, accent):
    """One size of the icon, on a transparent ground."""
    pm = QPixmap(side, side)
    pm.fill(QColor(0, 0, 0, 0))
    q = QPainter(pm)
    q.setRenderHint(QPainter.Antialiasing, True)
    q.setRenderHint(QPainter.SmoothPixmapTransform, True)
    u = side / 32.0
    body = QRectF(4.5 * u, 3.0 * u, 23 * u, 26.5 * u)

    shell = QLinearGradient(body.left(), 0, body.right(), 0)
    shell.setColorAt(0.0, QColor(52, 56, 60))
    shell.setColorAt(0.42, QColor(138, 143, 148))
    shell.setColorAt(1.0, QColor(58, 62, 66))
    q.setPen(QPen(QColor(20, 21, 23), max(1.0, 0.9 * u)))
    q.setBrush(QBrush(shell))
    # Arched top over a flat base: the shape a jukebox is known by.
    path = QPainterPath()
    radius = 3.0 * u
    path.moveTo(body.left(), body.bottom() - radius)
    path.lineTo(body.left(), body.top() + body.height() * 0.30)
    path.quadTo(body.center().x(), body.top() - body.height() * 0.10,
                body.right(), body.top() + body.height() * 0.30)
    path.lineTo(body.right(), body.bottom() - radius)
    path.quadTo(body.right(), body.bottom(), body.right() - radius, body.bottom())
    path.lineTo(body.left() + radius, body.bottom())
    path.quadTo(body.left(), body.bottom(), body.left(), body.bottom() - radius)
    q.drawPath(path)

    screen = QRectF(body.left() + 2.6 * u, body.top() + 6.4 * u,
                    body.width() - 5.2 * u, body.height() * 0.40)
    q.setBrush(QColor(12, 13, 15))
    q.setPen(QPen(QColor(10, 11, 12), max(1.0, 0.9 * u)))
    q.drawRoundedRect(screen, 1.8 * u, 1.8 * u)
    if emblem is not None and not emblem.isNull():
        e = int(min(screen.width(), screen.height()) * 0.98)
        q.drawImage(QRect(int(screen.center().x() - e / 2),
                          int(screen.center().y() - e / 2), e, e), emblem)

    # Round speakers, set inside the cabinet rather than under it.
    q.setPen(Qt.NoPen)
    r_sp = 2.7 * u
    cy = screen.bottom() + (body.bottom() - screen.bottom()) * 0.52
    for k in (-1, 1):
        cx = body.center().x() + k * 5.4 * u
        q.setBrush(QColor(20, 21, 23))
        q.drawEllipse(QPointF(cx, cy), r_sp * 1.16, r_sp * 1.16)
        cone = QRadialGradient(cx - r_sp * 0.32, cy - r_sp * 0.36, r_sp * 1.7)
        cone.setColorAt(0.0, accent.lighter(170))
        cone.setColorAt(0.55, accent)
        cone.setColorAt(1.0, accent.darker(210))
        q.setBrush(QBrush(cone))
        q.drawEllipse(QPointF(cx, cy), r_sp, r_sp)
        q.setBrush(QColor(16, 17, 19))
        q.drawEllipse(QPointF(cx, cy), r_sp * 0.30, r_sp * 0.30)
    q.end()
    return pm


def icon(emblem, accent):
    """Every size the desktop might ask for."""
    out = QIcon()
    for side in SIZES:
        out.addPixmap(pixmap(side, emblem, accent))
    return out
