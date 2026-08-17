"""
A top-down Xbox 360 controller schematic drawn on a Tkinter Canvas, used by
the Debug tab to show at a glance what's currently pressed/held. No image
assets - everything is drawn with canvas primitives so it stays crisp and
keeps the packaged .exe self-contained.
"""

import tkinter as tk

WIDTH, HEIGHT = 560, 400
CX = WIDTH // 2  # controller body is left/right symmetric around this column

# Standard-ish Xbox face button colors.
FACE_COLORS = {
    "A": "#4CAF50",
    "B": "#E5433C",
    "X": "#2F86D6",
    "Y": "#E8B923",
}
ACCENT_COLOR = "#22D3EE"  # highlight used for every non-face-button element
IDLE_FILL = "#3A3D45"
IDLE_OUTLINE = "#54585F"
IDLE_TEXT = "#B8BCC4"
PRESSED_TEXT = "#111318"
BODY_FILL = "#232529"
BODY_OUTLINE = "#141517"
BODY_RIM = "#2C2F35"
CANVAS_BG = "#F4F5F7"


def _rounded_rect_points(x1, y1, x2, y2, r):
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    return [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1, x1 + r, y1,
    ]


class ControllerSchematic(tk.Canvas):
    """set_active(active_buttons, lt, rt, lx, ly, rx, ry) redraws in place -
    call it on every debug refresh tick."""

    def __init__(self, parent):
        super().__init__(parent, width=WIDTH, height=HEIGHT, bg=CANVAS_BG, highlightthickness=0)
        self._shapes = {}
        self._texts = {}
        self._sticks = {}
        self._draw_static()

    # ------------------------------------------------------------- build --
    def _button(self, key, x1, y1, x2, y2, label, shape="rect", radius=8, font_size=8):
        if shape == "oval":
            item = self.create_oval(x1, y1, x2, y2, fill=IDLE_FILL, outline=IDLE_OUTLINE, width=2)
        else:
            item = self.create_polygon(_rounded_rect_points(x1, y1, x2, y2, radius), smooth=True,
                                        fill=IDLE_FILL, outline=IDLE_OUTLINE, width=2)
        self._shapes[key] = item
        if label:
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            self._texts[key] = self.create_text(
                cx, cy, text=label, fill=IDLE_TEXT, font=("Segoe UI", font_size, "bold")
            )

    # The body silhouette is a union of five overlapping primitives: two
    # shoulder bulges (which house the left stick/d-pad and face buttons,
    # like the real controller's rounded "wings"), two lower grip lobes,
    # and a narrower waist connecting them. Drawing an oversized copy of
    # the whole union first in the outline color, then the true-sized copy
    # on top in the body color, fakes a clean single silhouette + rim
    # without needing exact polygon boolean ops.
    _SHOULDER_R = 95
    _GRIP_R = 88
    _SHOULDER_CENTER_Y = 150
    _GRIP_CENTER_Y = 300

    def _body_primitives(self, grow=0):
        sr, gr = self._SHOULDER_R + grow, self._GRIP_R + grow
        sy, gy = self._SHOULDER_CENTER_Y, self._GRIP_CENTER_Y
        return [
            ("oval", CX - 145 - sr, sy - sr, CX - 145 + sr, sy + sr),
            ("oval", CX + 145 - sr, sy - sr, CX + 145 + sr, sy + sr),
            ("oval", CX - 140 - gr, gy - gr, CX - 140 + gr, gy + gr),
            ("oval", CX + 140 - gr, gy - gr, CX + 140 + gr, gy + gr),
            ("rrect", CX - 118 - grow, 132 - grow, CX + 118 + grow, 318 + grow, 56 + grow),
        ]

    def _draw_body_layer(self, grow, color):
        for kind, x1, y1, x2, y2, *rest in self._body_primitives(grow):
            if kind == "oval":
                self.create_oval(x1, y1, x2, y2, fill=color, outline="")
            else:
                self.create_polygon(_rounded_rect_points(x1, y1, x2, y2, rest[0]), smooth=True, fill=color, outline="")

    def _draw_static(self):
        # Soft ground shadow, peeking out from under the body's lower edge.
        self.create_oval(CX - 220, 130, CX + 220, 400, fill="#000000", outline="", stipple="gray25")

        self._draw_body_layer(4, BODY_OUTLINE)
        self._draw_body_layer(0, BODY_FILL)
        # Glossy highlight arcs on the two shoulder bulges for a moulded look.
        self.create_arc(CX - 145 - 80, self._SHOULDER_CENTER_Y - 80, CX - 145 + 80, self._SHOULDER_CENTER_Y + 80,
                         start=70, extent=110, style="arc", outline=BODY_RIM, width=2)
        self.create_arc(CX + 145 - 80, self._SHOULDER_CENTER_Y - 80, CX + 145 + 80, self._SHOULDER_CENTER_Y + 80,
                         start=70, extent=110, style="arc", outline=BODY_RIM, width=2)

        # Triggers - poke above the body's top edge like real trigger caps.
        self._button("LT", CX - 178, 14, CX - 100, 50, "LT", radius=10)
        self._button("RT", CX + 100, 14, CX + 178, 50, "RT", radius=10)
        # Shoulder buttons, set into the top corners of the body.
        self._button("LEFT_SHOULDER", CX - 185, 62, CX - 100, 90, "LB", radius=8)
        self._button("RIGHT_SHOULDER", CX + 100, 62, CX + 185, 90, "RB", radius=8)

        # Sticks (ring is static context, dot moves + recolors on click).
        self._sticks["left"] = self._make_stick(CX - 140, 138, 36)
        self._sticks["right"] = self._make_stick(CX + 65, 268, 36)

        # D-pad - four flush arms forming a plus, plus a static pivot cap.
        self._draw_dpad(CX - 140, 280)

        # Face buttons, diamond-arranged to match the real layout.
        fbx, fby = CX + 150, 155
        self._button("Y", fbx - 19, fby - 61, fbx + 19, fby - 23, "Y", shape="oval")
        self._button("X", fbx - 57, fby - 19, fbx - 19, fby + 19, "X", shape="oval")
        self._button("B", fbx + 19, fby - 19, fbx + 57, fby + 19, "B", shape="oval")
        self._button("A", fbx - 19, fby + 23, fbx + 19, fby + 61, "A", shape="oval")
        for key in ("Y", "X", "B", "A"):
            self.itemconfig(self._shapes[key], fill=IDLE_FILL)

        # Back / Guide / Start, centered on the body between stick and pad.
        self._button("BACK", CX - 55, 200, CX - 32, 218, "BK", shape="oval", font_size=6)
        self._button("GUIDE", CX - 22, 190, CX + 22, 230, "GD", shape="oval")
        self._button("START", CX + 32, 200, CX + 55, 218, "ST", shape="oval", font_size=6)

    def _draw_dpad(self, cx, cy):
        half_thick, extent = 11, 33
        arms = {
            "DPAD_UP": (cx - half_thick, cy - extent, cx + half_thick, cy - half_thick, "▲"),
            "DPAD_DOWN": (cx - half_thick, cy + half_thick, cx + half_thick, cy + extent, "▼"),
            "DPAD_LEFT": (cx - extent, cy - half_thick, cx - half_thick, cy + half_thick, "◀"),
            "DPAD_RIGHT": (cx + half_thick, cy - half_thick, cx + extent, cy + half_thick, "▶"),
        }
        for key, (x1, y1, x2, y2, label) in arms.items():
            item = self.create_rectangle(x1, y1, x2, y2, fill=IDLE_FILL, outline=IDLE_OUTLINE, width=2)
            self._shapes[key] = item
            lx = cx + (14 if "RIGHT" in key else -14 if "LEFT" in key else 0)
            ly = cy + (14 if "DOWN" in key else -14 if "UP" in key else 0)
            self._texts[key] = self.create_text(lx, ly, text=label, fill=IDLE_TEXT, font=("Segoe UI", 8, "bold"))
        # Static pivot cap covering the shared center of the cross.
        self.create_rectangle(cx - half_thick, cy - half_thick, cx + half_thick, cy + half_thick,
                               fill=IDLE_OUTLINE, outline="")

    def _make_stick(self, cx, cy, radius):
        socket = self.create_oval(cx - radius - 4, cy - radius - 4, cx + radius + 4, cy + radius + 4,
                                   fill=BODY_OUTLINE, outline="")
        ring = self.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                                 fill="#2A2D33", outline=IDLE_OUTLINE, width=2)
        dot_r = 15
        dot = self.create_oval(cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r,
                                fill=IDLE_FILL, outline=IDLE_OUTLINE, width=2)
        highlight = self.create_oval(cx - dot_r + 4, cy - dot_r + 4, cx - dot_r + 10, cy - dot_r + 10,
                                      fill="#585C66", outline="")
        return {
            "socket": socket, "ring": ring, "dot": dot, "highlight": highlight,
            "center": (cx, cy), "travel": radius - dot_r, "dot_r": dot_r,
        }

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
            self.itemconfig(text, fill=PRESSED_TEXT if pressed else IDLE_TEXT)

    def _set_stick(self, side, x, y, clicked):
        stick = self._sticks[side]
        cx, cy = stick["center"]
        travel = stick["travel"]
        r = stick["dot_r"]
        nx = cx + max(-1.0, min(1.0, x)) * travel
        ny = cy - max(-1.0, min(1.0, y)) * travel
        self.coords(stick["dot"], nx - r, ny - r, nx + r, ny + r)
        self.coords(stick["highlight"], nx - r + 4, ny - r + 4, nx - r + 10, ny - r + 10)
        self.itemconfig(stick["dot"], fill=ACCENT_COLOR if clicked else IDLE_FILL)
