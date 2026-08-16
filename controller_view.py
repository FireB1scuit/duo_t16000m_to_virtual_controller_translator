"""
A top-down Xbox 360 controller schematic drawn on a Tkinter Canvas, used by
the Debug tab to show at a glance what's currently pressed/held. No image
assets - everything is drawn with canvas primitives so it stays crisp and
keeps the packaged .exe self-contained.
"""

import tkinter as tk

WIDTH, HEIGHT = 460, 300

# Standard-ish Xbox face button colors.
FACE_COLORS = {
    "A": "#3AA43A",
    "B": "#D6423B",
    "X": "#2E7FCF",
    "Y": "#E0B426",
}
ACCENT_COLOR = "#3AA43A"  # highlight used for every non-face-button element
IDLE_FILL = "#f4f4f4"
IDLE_OUTLINE = "#9a9a9a"
IDLE_TEXT = "#555555"
BODY_FILL = "#dcdcdc"
BODY_OUTLINE = "#bcbcbc"


def _rounded_rect_points(x1, y1, x2, y2, r):
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    return [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
        x1 + r, y1,
    ]


class ControllerSchematic(tk.Canvas):
    """set_active(active_buttons, lt, rt, lx, ly, rx, ry) redraws in place -
    call it on every debug refresh tick."""

    def __init__(self, parent):
        super().__init__(parent, width=WIDTH, height=HEIGHT, bg="white", highlightthickness=0)
        self._shapes = {}
        self._texts = {}
        self._sticks = {}
        self._draw_static()

    # ------------------------------------------------------------- build --
    def _rounded_rect(self, x1, y1, x2, y2, r=8, **kwargs):
        return self.create_polygon(_rounded_rect_points(x1, y1, x2, y2, r), smooth=True, **kwargs)

    def _button(self, key, x1, y1, x2, y2, label, shape="rect", radius=8, font_size=8):
        if shape == "oval":
            item = self.create_oval(x1, y1, x2, y2, fill=IDLE_FILL, outline=IDLE_OUTLINE, width=2)
        else:
            item = self._rounded_rect(x1, y1, x2, y2, r=radius, fill=IDLE_FILL, outline=IDLE_OUTLINE, width=2)
        self._shapes[key] = item
        if label:
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            self._texts[key] = self.create_text(
                cx, cy, text=label, fill=IDLE_TEXT, font=("Segoe UI", font_size, "bold")
            )

    def _draw_static(self):
        self._rounded_rect(10, 38, 450, 292, r=44, fill=BODY_FILL, outline=BODY_OUTLINE, width=2)

        # Triggers / shoulders
        self._button("LT", 55, 18, 120, 40, "LT")
        self._button("RT", 340, 18, 405, 40, "RT")
        self._button("LEFT_SHOULDER", 55, 46, 120, 64, "LB")
        self._button("RIGHT_SHOULDER", 340, 46, 405, 64, "RB")

        # Sticks (ring is static context, dot moves + recolors on click)
        self._sticks["left"] = self._make_stick(95, 128, 36)
        self._sticks["right"] = self._make_stick(300, 222, 36)

        # D-pad
        self._button("DPAD_UP", 81, 188, 109, 212, "▲")
        self._button("DPAD_DOWN", 81, 232, 109, 256, "▼")
        self._button("DPAD_LEFT", 61, 208, 85, 232, "◀")
        self._button("DPAD_RIGHT", 105, 208, 129, 232, "▶")

        # Face buttons
        self._button("Y", 343, 71, 377, 105, "Y", shape="oval")
        self._button("X", 303, 111, 337, 145, "X", shape="oval")
        self._button("B", 383, 111, 417, 145, "B", shape="oval")
        self._button("A", 343, 151, 377, 185, "A", shape="oval")

        # Back / Guide / Start
        self._button("BACK", 165, 140, 185, 160, "BK", shape="oval", font_size=6)
        self._button("GUIDE", 200, 140, 240, 180, "GD", shape="oval")
        self._button("START", 255, 140, 275, 160, "ST", shape="oval", font_size=6)

    def _make_stick(self, cx, cy, radius):
        ring = self.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill="white", outline=IDLE_OUTLINE, width=2)
        dot_r = 12
        dot = self.create_oval(cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r, fill=IDLE_FILL, outline=IDLE_OUTLINE, width=2)
        return {"ring": ring, "dot": dot, "center": (cx, cy), "travel": radius - dot_r, "dot_r": dot_r}

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
        shape = self._shapes[key]
        self.itemconfig(shape, fill=color if pressed else IDLE_FILL)
        text = self._texts.get(key)
        if text is not None:
            self.itemconfig(text, fill="white" if pressed else IDLE_TEXT)

    def _set_stick(self, side, x, y, clicked):
        stick = self._sticks[side]
        cx, cy = stick["center"]
        travel = stick["travel"]
        r = stick["dot_r"]
        nx = cx + max(-1.0, min(1.0, x)) * travel
        ny = cy - max(-1.0, min(1.0, y)) * travel
        self.coords(stick["dot"], nx - r, ny - r, nx + r, ny + r)
        self.itemconfig(stick["dot"], fill=ACCENT_COLOR if clicked else IDLE_FILL)
