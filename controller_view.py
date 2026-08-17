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


# Right-half body profile as (dx from CX, y) pairs, traced from the shallow
# dip at top-center, out across the shoulder, down through a gentle waist,
# and out again into the lower grip lobe. Mirroring this across CX and
# closing through BOTTOM_CENTER gives the whole silhouette as one smoothed
# polygon - this is what actually reads as "Xbox 360 controller" instead of
# a blob, so keep the widen/narrow/widen rhythm if these ever get tuned.
BODY_RIGHT_HALF = [
    (18, 45), (95, 50), (160, 78), (210, 135),
    (198, 195), (168, 235), (178, 262), (213, 305),
    (190, 345), (108, 368), (40, 360),
]
BODY_BOTTOM_CENTER = (0, 345)


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

    def _body_outline_points(self):
        left_half = [(-dx, y) for dx, y in reversed(BODY_RIGHT_HALF)]
        points = []
        for dx, y in BODY_RIGHT_HALF:
            points += [CX + dx, y]
        points += [CX + BODY_BOTTOM_CENTER[0], BODY_BOTTOM_CENTER[1]]
        for dx, y in left_half:
            points += [CX + dx, y]
        return points

    def _draw_static(self):
        body_pts = self._body_outline_points()

        # Soft ground shadow, peeking out from under the body's lower edge.
        self.create_oval(CX - 220, 140, CX + 220, 400, fill="#000000", outline="", stipple="gray25")

        self.create_polygon(body_pts, smooth=True, splinesteps=24, fill=BODY_OUTLINE, outline="")
        inset_pts = self._offset_polygon(body_pts, -4)
        self.create_polygon(inset_pts, smooth=True, splinesteps=24, fill=BODY_FILL, outline="")
        self.create_line(inset_pts + inset_pts[:2], smooth=True, splinesteps=24, fill=BODY_RIM, width=1)

        # Shoulder bumpers, set flush into the top-left/top-right curve.
        self._button("LEFT_SHOULDER", CX - 178, 55, CX - 96, 82, "LB", radius=10)
        self._button("RIGHT_SHOULDER", CX + 96, 55, CX + 178, 82, "RB", radius=10)
        # Triggers - separate caps that poke above the body's top edge.
        self._button("LT", CX - 150, 12, CX - 80, 44, "LT", radius=10)
        self._button("RT", CX + 80, 12, CX + 150, 44, "RT", radius=10)

        # Sticks (ring is static context, dot moves + recolors on click).
        self._sticks["left"] = self._make_stick(CX - 160, 150, 34)
        self._sticks["right"] = self._make_stick(CX + 65, 270, 34)

        # D-pad - four flush arms forming a plus, plus a static pivot cap.
        self._draw_dpad(CX - 150, 275)

        # Face buttons, diamond-arranged to match the real layout.
        fbx, fby = CX + 145, 140
        self._button("Y", fbx - 18, fby - 58, fbx + 18, fby - 22, "Y", shape="oval")
        self._button("X", fbx - 54, fby - 18, fbx - 18, fby + 18, "X", shape="oval")
        self._button("B", fbx + 18, fby - 18, fbx + 54, fby + 18, "B", shape="oval")
        self._button("A", fbx - 18, fby + 22, fbx + 18, fby + 58, "A", shape="oval")

        # Back / Guide / Start, centered on the body's waist. The guide
        # button is the big one, flanked by two small pill-shaped buttons.
        self._button("GUIDE", CX - 27, 205, CX + 27, 259, "XBOX", shape="oval", font_size=7)
        self._button("BACK", CX - 62, 212, CX - 36, 228, "◁", shape="oval", font_size=7)
        self._button("START", CX + 36, 212, CX + 62, 228, "▷", shape="oval", font_size=7)

    @staticmethod
    def _offset_polygon(points, amount):
        """Nudge every (x, y) pair toward the shape's centroid by `amount`
        px (negative shrinks), used to draw a slightly-smaller rim shape
        for a beveled look."""
        xs = points[0::2]
        ys = points[1::2]
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        out = []
        for x, y in zip(xs, ys):
            dx, dy = x - cx, y - cy
            dist = max((dx * dx + dy * dy) ** 0.5, 1e-6)
            out += [x + dx / dist * amount, y + dy / dist * amount]
        return out

    def _draw_dpad(self, cx, cy):
        half_thick, extent = 11, 33
        self.create_oval(cx - extent - 8, cy - extent - 8, cx + extent + 8, cy + extent + 8,
                          fill="#2A2D33", outline=IDLE_OUTLINE, width=2)
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
        socket = self.create_oval(cx - radius - 6, cy - radius - 6, cx + radius + 6, cy + radius + 6,
                                   fill="#2A2D33", outline=IDLE_OUTLINE, width=2)
        dot_r = 15
        dot = self.create_oval(cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r,
                                fill=IDLE_FILL, outline=IDLE_OUTLINE, width=2)
        highlight = self.create_oval(cx - dot_r + 4, cy - dot_r + 4, cx - dot_r + 10, cy - dot_r + 10,
                                      fill="#585C66", outline="")
        return {
            "socket": socket, "dot": dot, "highlight": highlight,
            "center": (cx, cy), "travel": radius - dot_r + 6, "dot_r": dot_r,
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
