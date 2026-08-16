"""
Reads the two T.16000M joysticks and (optionally) drives a virtual Xbox 360
pad from them. Used by both the CLI (main.py) and the GUI (gui.py).

StickManager owns a single background thread that polls pygame at
config["poll_hz"] and, while a gamepad is active, feeds a virtual controller
from the same reads - the GUI's debug view and its "activate controller"
toggle are just two consumers of that one loop, not two separate pollers.
"""

import ctypes
import json
import sys
import threading
import time

import pygame

import config_store

STICK_NAME_HINT = "T.16000M"


class Ticker:
    """Sleeps to hold a constant poll rate, compensating for time spent each iteration."""

    def __init__(self, hz):
        self.period = 1 / hz
        self.next_tick = time.perf_counter() + self.period

    def wait(self):
        now = time.perf_counter()
        delay = self.next_tick - now
        if delay > 0:
            time.sleep(delay)
        else:
            self.next_tick = now
        self.next_tick += self.period


def set_high_res_timer(enable):
    if sys.platform == "win32":
        (ctypes.windll.winmm.timeBeginPeriod if enable else ctypes.windll.winmm.timeEndPeriod)(1)


def apply_deadzone(value, deadzone):
    magnitude = abs(value)
    if magnitude < deadzone:
        return 0.0
    sign = 1.0 if value > 0 else -1.0
    scaled = (magnitude - deadzone) / (1.0 - deadzone)
    return sign * min(scaled, 1.0)


def discover_joysticks():
    pygame.joystick.quit()
    pygame.joystick.init()
    all_joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
    return [j for j in all_joysticks if STICK_NAME_HINT in j.get_name()], all_joysticks


def load_cached_left_index():
    path = config_store.calibration_path()
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            return json.load(f).get("left_index")
    except (json.JSONDecodeError, OSError):
        return None


def save_cached_left_index(left_index):
    with open(config_store.calibration_path(), "w") as f:
        json.dump({"left_index": left_index}, f)


def wait_for_active_stick(joysticks, threshold=0.5, timeout=15, axes=(0, 1), progress_cb=None, should_abort=None):
    """Blocks until one of joysticks moves past threshold on axes, or timeout.

    Returns the moved joystick, or None on timeout/abort. Intended to be run
    off the calling thread's UI loop when used from the GUI.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        if should_abort and should_abort():
            return None
        pygame.event.pump()
        for joy in joysticks:
            if any(abs(joy.get_axis(a)) > threshold for a in axes):
                return joy
        if progress_cb:
            progress_cb(max(0, deadline - time.time()))
        time.sleep(0.02)
    return None


def identify_sticks(joysticks, recalibrate=False, status_cb=None, progress_cb=None, should_abort=None):
    """Returns (left, right, used_cache). Caches the winning slot so future
    calls (new process, or GUI recalibrate=False) skip the movement wait."""
    status_cb = status_cb or (lambda msg: None)

    if not recalibrate:
        cached_index = load_cached_left_index()
        if cached_index is not None and 0 <= cached_index < len(joysticks):
            left = joysticks[cached_index]
            right = next(j for j in joysticks if j is not left)
            status_cb(f"Using cached assignment -> Left: {left.get_name()}, Right: {right.get_name()}")
            return left, right, True

    status_cb("Move the LEFT stick now (just the left one)...")
    left = wait_for_active_stick(joysticks, progress_cb=progress_cb, should_abort=should_abort)
    if left is None:
        status_cb("Calibration cancelled or timed out; defaulting to enumeration order.")
        left = joysticks[0]
    right = next(j for j in joysticks if j is not left)
    save_cached_left_index(joysticks.index(left))
    status_cb(f"Left  -> {left.get_name()}\nRight -> {right.get_name()}")
    return left, right, False


def read_raw_state(joy):
    return {
        "axes": [joy.get_axis(i) for i in range(joy.get_numaxes())],
        "buttons": [joy.get_button(i) for i in range(joy.get_numbuttons())],
        "hat": joy.get_hat(0) if joy.get_numhats() > 0 else (0, 0),
    }


def safe_axis(axes, index):
    return axes[index] if 0 <= index < len(axes) else 0.0


def safe_button(buttons, index):
    return bool(buttons[index]) if 0 <= index < len(buttons) else False


class GamepadController:
    """Wraps a vgamepad VX360Gamepad, mapping raw stick state to it per a
    config dict. Import of vgamepad is deferred so modules that only need
    read access (e.g. the debug view) work without ViGEmBus installed."""

    def __init__(self, config):
        import vgamepad as vg

        self._vg = vg
        self.gamepad = vg.VX360Gamepad()
        self.set_config(config)

    def set_config(self, config):
        self.config = config
        self.left_button_map = self._build_button_map(config["left_buttons"])
        self.right_button_map = self._build_button_map(config["right_buttons"])
        self.left_hat_map = self._build_hat_map(config["left_hat"])
        self.right_hat_map = self._build_hat_map(config["right_hat"])
        self.all_buttons = (
            set(self.left_button_map.values())
            | set(self.right_button_map.values())
            | set(self.left_hat_map.values())
            | set(self.right_hat_map.values())
        )

    def _build_button_map(self, mapping):
        return {
            int(index): getattr(self._vg.XUSB_BUTTON, config_store.BUTTON_NAME_MAP[name])
            for index, name in mapping.items()
        }

    def _build_hat_map(self, mapping):
        result = {}
        for direction, name in mapping.items():
            x_str, y_str = direction.split(",")
            result[(int(x_str), int(y_str))] = getattr(self._vg.XUSB_BUTTON, config_store.BUTTON_NAME_MAP[name])
        return result

    def update(self, left_state, right_state):
        lx = apply_deadzone(safe_axis(left_state["axes"], self.config["stick_x_axis"]), self.config["stick_deadzone"])
        ly = apply_deadzone(safe_axis(left_state["axes"], self.config["stick_y_axis"]), self.config["stick_deadzone"])
        rx = apply_deadzone(safe_axis(right_state["axes"], self.config["stick_x_axis"]), self.config["stick_deadzone"])
        ry = apply_deadzone(safe_axis(right_state["axes"], self.config["stick_y_axis"]), self.config["stick_deadzone"])
        if self.config["invert_y_left"]:
            ly = -ly
        if self.config["invert_y_right"]:
            ry = -ry

        self.gamepad.left_joystick_float(x_value_float=lx, y_value_float=ly)
        self.gamepad.right_joystick_float(x_value_float=rx, y_value_float=ry)

        trig_index = self.config["trigger_button"]
        self.gamepad.left_trigger_float(value_float=1.0 if safe_button(left_state["buttons"], trig_index) else 0.0)
        self.gamepad.right_trigger_float(value_float=1.0 if safe_button(right_state["buttons"], trig_index) else 0.0)

        active = set()
        self._active_buttons(left_state, self.left_button_map, self.left_hat_map, active)
        self._active_buttons(right_state, self.right_button_map, self.right_hat_map, active)
        for vg_button in self.all_buttons:
            if vg_button in active:
                self.gamepad.press_button(button=vg_button)
            else:
                self.gamepad.release_button(button=vg_button)

        self.gamepad.update()

    @staticmethod
    def _active_buttons(state, button_map, hat_map, active):
        for index, vg_button in button_map.items():
            if safe_button(state["buttons"], index):
                active.add(vg_button)
        for direction, vg_button in hat_map.items():
            if direction == state["hat"]:
                active.add(vg_button)

    def close(self):
        self.gamepad.reset()
        self.gamepad.update()


class StickManager:
    """Owns the two joystick handles and a background polling thread.

    Call connect() once sticks are found, then start_polling(). GUI code
    reads get_snapshot() from the Tk main loop via after(); it must not
    touch pygame directly from another thread.
    """

    def __init__(self):
        self.left = None
        self.right = None
        self.config = dict(config_store.DEFAULT_CONFIG)
        self._lock = threading.Lock()
        self._state = {"left": None, "right": None}
        self._thread = None
        self._running = False
        self._gamepad = None
        self._gamepad_lock = threading.Lock()
        self.gamepad_active = False
        self.last_error = None

    # -- connection -------------------------------------------------
    def find_sticks(self):
        sticks, all_joysticks = discover_joysticks()
        return sticks, all_joysticks

    def assign(self, sticks, recalibrate=False, status_cb=None, progress_cb=None, should_abort=None):
        left, right, used_cache = identify_sticks(
            sticks, recalibrate=recalibrate, status_cb=status_cb, progress_cb=progress_cb, should_abort=should_abort
        )
        self.left, self.right = left, right
        return used_cache

    def is_connected(self):
        return self.left is not None and self.right is not None

    def set_config(self, config):
        with self._lock:
            self.config = config
        with self._gamepad_lock:
            if self._gamepad is not None:
                self._gamepad.set_config(config)

    # -- polling ------------------------------------------------------
    def start_polling(self):
        if self._running:
            return
        self._running = True
        set_high_res_timer(True)
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop_polling(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        self.stop_gamepad()
        set_high_res_timer(False)

    def _poll_loop(self):
        ticker = Ticker(self.config.get("poll_hz", 125))
        while self._running:
            try:
                pygame.event.pump()
                left_raw = read_raw_state(self.left)
                right_raw = read_raw_state(self.right)
                with self._lock:
                    config = self.config
                    self._state = {
                        "left": {"name": self.left.get_name(), **left_raw},
                        "right": {"name": self.right.get_name(), **right_raw},
                    }
                with self._gamepad_lock:
                    if self.gamepad_active and self._gamepad is not None:
                        self._gamepad.update(left_raw, right_raw)
            except Exception as exc:  # keep the loop alive; surface the error to the GUI
                self.last_error = str(exc)
            ticker.wait()

    def get_snapshot(self):
        with self._lock:
            return dict(self._state)

    # -- virtual controller -------------------------------------------
    def start_gamepad(self):
        with self._gamepad_lock:
            if self._gamepad is None:
                self._gamepad = GamepadController(self.config)
            self.gamepad_active = True

    def stop_gamepad(self):
        with self._gamepad_lock:
            self.gamepad_active = False
            if self._gamepad is not None:
                self._gamepad.close()
                self._gamepad = None
