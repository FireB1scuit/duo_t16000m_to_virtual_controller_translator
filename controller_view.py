"""
Renders the labeled Xbox 360 controller schematic (assets/xbox 360
scematic.png) on a Tkinter Canvas, with live press/highlight indicators
drawn on top for the Debug tab. The debug-tab copy
(assets/xbox_360_schematic_debug.png) is a pre-shrunk, LANCZOS-resampled
copy of the source image sized to fit the app window - resized once at dev
time so no image library is needed at runtime, and PyInstaller just needs
to bundle the PNG (see build.ps1).
"""

import sys
import tkinter as tk
from pathlib import Path

# PyInstaller's --onefile bundle extracts data files under sys._MEIPASS at
# runtime instead of next to this script, so the asset has to be looked up
# relative to that when frozen (see build.ps1's --add-data for this file).
_BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
ASSET_PATH = _BASE_DIR / "assets" / "xbox_360_schematic_debug.png"

# The asset above is the source schematic scaled to this fraction; button
# geometry below is measured on the native 1024x559 source image and scaled
# by this factor at draw time, so re-deriving positions is a matter of
# reading pixel coordinates off the full-res original.
SCALE = 760 / 1024
WIDTH, HEIGHT = round(1024 * SCALE), round(559 * SCALE)

FACE_COLORS = {
    "A": "#4CAF50",
    "B": "#E5433C",
    "X": "#2F86D6",
    "Y": "#E8B923",
}
ACCENT_COLOR = "#22D3EE"
IDLE_OUTLINE = "#C7C9CC"  # faint ring, stays quiet on the white schematic until lit
CANVAS_BG = "#FFFFFF"

# (shape, x1, y1, x2, y2) read off the native 1024x559 source image.
_NATIVE_GEOMETRY = {
    "LT": ("rect", 290, 55, 345, 115),
    "RT": ("rect", 660, 55, 715, 115),
    "LEFT_SHOULDER": ("rect", 250, 115, 390, 150),
    "RIGHT_SHOULDER": ("rect", 630, 115, 770, 150),
    "Y": ("oval", 661, 160, 721, 220),
    "X": ("oval", 605, 210, 665, 270),
    "B": ("oval", 717, 210, 777, 270),
    "A": ("oval", 661, 260, 721, 320),
    "GUIDE": ("oval", 471, 194, 551, 274),
    "BACK": ("oval", 410, 213, 450, 253),
    "START": ("oval", 562, 215, 602, 255),
    "DPAD_UP": ("oval", 395, 294, 427, 326),
    "DPAD_DOWN": ("oval", 395, 368, 427, 400),
    "DPAD_LEFT": ("oval", 361, 331, 393, 363),
    "DPAD_RIGHT": ("oval", 429, 331, 461, 363),
}

# (cx, cy, radius) read off the same native image.
_STICKS_NATIVE = {
    "left": (331, 248, 49),
    "right": (590, 355, 50),
}


class ControllerSchematic(tk.Canvas):
    """set_active(active_buttons, lt, rt, lx, ly, rx, ry) redraws in place -
    call it on every debug refresh tick."""

    def __init__(self, parent):
        super().__init__(parent, width=WIDTH, height=HEIGHT, bg=CANVAS_BG, highlightthickness=0)
        self._shapes = {}
        self._sticks = {}
        self._image = tk.PhotoImage(file=str(ASSET_PATH))
        self._draw_static()

    def _s(self, v):
        return v * SCALE

    def _draw_static(self):
        self.create_image(0, 0, image=self._image, anchor="nw")

        for key, (shape, x1, y1, x2, y2) in _NATIVE_GEOMETRY.items():
            x1, y1, x2, y2 = self._s(x1), self._s(y1), self._s(x2), self._s(y2)
            if shape == "oval":
                item = self.create_oval(x1, y1, x2, y2, outline=IDLE_OUTLINE, width=2)
            else:
                item = self.create_rectangle(x1, y1, x2, y2, outline=IDLE_OUTLINE, width=2)
            self._shapes[key] = item

        for side, (cx, cy, r) in _STICKS_NATIVE.items():
            self._sticks[side] = self._make_stick(self._s(cx), self._s(cy), self._s(r))

    def _make_stick(self, cx, cy, radius):
        dot_r = radius * 0.28
        dot = self.create_oval(cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r,
                                fill=CANVAS_BG, outline=IDLE_OUTLINE, width=2)
        return {"dot": dot, "center": (cx, cy), "travel": radius - dot_r - 4, "dot_r": dot_r}

    # ------------------------------------------------------------ update --
    def set_active(self, active_buttons, lt, rt, lx, ly, rx, ry):
        for key in ("LEFT_SHOULDER", "RIGHT_SHOULDER", "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT",
                    "BACK", "START", "GUIDE"):
            self._set_pressed(key, key in active_buttons, ACCENT_COLOR)

        for key in ("A", "B", "X", "Y"):
            self._set_pressed(key, key in active_buttons, FACE_COLORS[key])

        self._set_pressed("LT", lt > 0.5, ACCENT_COLOR)
        self._set_pressed("RT", rt > 0.5, ACCENT_COLOR)

        self._set_stick("left", lx, ly, "LEFT_THUMB" in active_buttons)
        self._set_stick("right", rx, ry, "RIGHT_THUMB" in active_buttons)

    def _set_pressed(self, key, pressed, color):
        self.itemconfig(self._shapes[key], outline=color if pressed else IDLE_OUTLINE,
                         width=4 if pressed else 2)

    def _set_stick(self, side, x, y, clicked):
        stick = self._sticks[side]
        cx, cy = stick["center"]
        travel = stick["travel"]
        r = stick["dot_r"]
        nx = cx + max(-1.0, min(1.0, x)) * travel
        ny = cy - max(-1.0, min(1.0, y)) * travel
        self.coords(stick["dot"], nx - r, ny - r, nx + r, ny + r)
        self.itemconfig(stick["dot"], fill=ACCENT_COLOR if clicked else CANVAS_BG,
                         outline=ACCENT_COLOR if clicked else IDLE_OUTLINE)
