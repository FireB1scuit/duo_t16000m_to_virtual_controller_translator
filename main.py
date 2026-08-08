"""
Combines two Thrustmaster T.16000M joysticks into a single virtual Xbox 360
controller: left stick -> left stick, right stick -> right stick, and each
stick's trigger button -> that side's analog trigger (LT/RT).

Setup:
    1. Install ViGEmBus driver: https://github.com/ViGEm/ViGEmBus/releases
    2. pip install pygame vgamepad

Run with --test to print raw axis/button values instead of creating a
virtual controller, useful for confirming the axis/button indices in
config.json match your hardware.
"""

import ctypes
import json
import sys
import time
from pathlib import Path

import pygame

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

DEFAULT_CONFIG = {
    "stick_x_axis": 0,
    "stick_y_axis": 1,
    "invert_y_left": True,     # pygame: stick forward = -1; gamepads report forward = +1
    "invert_y_right": True,
    "trigger_button": 0,        # T.16000M trigger is button index 0
    "stick_deadzone": 0.08,     # below this, axis reports 0; above it, movement scales smoothly to full deflection
    "poll_hz": 125,
    "left_buttons": {},         # pygame button index (str) -> XUSB_BUTTON name, see BUTTON_NAME_MAP
    "right_buttons": {},
    "left_hat": {},             # "x,y" hat direction (str) -> XUSB_BUTTON name
    "right_hat": {},
}

# Maps the button names used in config.json to vgamepad's XUSB_BUTTON enum.
BUTTON_NAME_MAP = {
    "A": "XUSB_GAMEPAD_A",
    "B": "XUSB_GAMEPAD_B",
    "X": "XUSB_GAMEPAD_X",
    "Y": "XUSB_GAMEPAD_Y",
    "LEFT_SHOULDER": "XUSB_GAMEPAD_LEFT_SHOULDER",
    "RIGHT_SHOULDER": "XUSB_GAMEPAD_RIGHT_SHOULDER",
    "DPAD_UP": "XUSB_GAMEPAD_DPAD_UP",
    "DPAD_DOWN": "XUSB_GAMEPAD_DPAD_DOWN",
    "DPAD_LEFT": "XUSB_GAMEPAD_DPAD_LEFT",
    "DPAD_RIGHT": "XUSB_GAMEPAD_DPAD_RIGHT",
    "LEFT_THUMB": "XUSB_GAMEPAD_LEFT_THUMB",
    "RIGHT_THUMB": "XUSB_GAMEPAD_RIGHT_THUMB",
    "BACK": "XUSB_GAMEPAD_BACK",
    "START": "XUSB_GAMEPAD_START",
    "GUIDE": "XUSB_GAMEPAD_GUIDE",
}


def load_config(path=CONFIG_PATH):
    if not path.exists():
        sys.exit(f"Config file not found: {path}")
    with open(path, "r") as f:
        user_config = json.load(f)
    config = {**DEFAULT_CONFIG, **user_config}
    missing = [key for key in DEFAULT_CONFIG if key not in config]
    if missing:
        sys.exit(f"Config file {path} is missing keys: {', '.join(missing)}")
    return config


CONFIG = load_config()


class Ticker:
    """Sleeps to hold a constant poll rate, compensating for time spent each iteration.

    A plain time.sleep(1/hz) after variable-cost work drifts and, on Windows,
    also gets rounded up to the ~15.6ms system timer tick unless a finer
    resolution is requested (see set_high_res_timer), both of which add
    jittery input latency on top of the nominal period.
    """

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


def apply_deadzone(value, deadzone=None):
    if deadzone is None:
        deadzone = CONFIG["stick_deadzone"]
    magnitude = abs(value)
    if magnitude < deadzone:
        return 0.0
    sign = 1.0 if value > 0 else -1.0
    scaled = (magnitude - deadzone) / (1.0 - deadzone)
    return sign * min(scaled, 1.0)


def identify_sticks(joysticks):
    print("Calibration: move the LEFT stick now (just the left one)...")
    left = wait_for_active_stick(joysticks)
    right = next(j for j in joysticks if j is not left)
    print(f"Left  -> {left.get_name()} (instance {left.get_instance_id()})")
    print(f"Right -> {right.get_name()} (instance {right.get_instance_id()})")
    return left, right


def wait_for_active_stick(joysticks, threshold=0.5, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        pygame.event.pump()
        for joy in joysticks:
            if abs(joy.get_axis(CONFIG["stick_x_axis"])) > threshold or abs(joy.get_axis(CONFIG["stick_y_axis"])) > threshold:
                return joy
        time.sleep(0.02)
    print("No movement detected in time, defaulting to enumeration order.")
    return joysticks[0]


def read_stick(joy, invert_y):
    x = apply_deadzone(joy.get_axis(CONFIG["stick_x_axis"]))
    y = apply_deadzone(joy.get_axis(CONFIG["stick_y_axis"]))
    if invert_y:
        y = -y
    return x, y


def run_test_mode(left, right):
    print("Test mode: printing values, Ctrl+C to stop.")
    ticker = Ticker(CONFIG["poll_hz"])
    while True:
        pygame.event.pump()
        lx, ly = read_stick(left, CONFIG["invert_y_left"])
        rx, ry = read_stick(right, CONFIG["invert_y_right"])
        lt = left.get_button(CONFIG["trigger_button"])
        rt = right.get_button(CONFIG["trigger_button"])
        print(f"L=({lx:+.2f},{ly:+.2f}) trig={lt}   R=({rx:+.2f},{ry:+.2f}) trig={rt}", end="\r")
        ticker.wait()


def read_raw_state(joy):
    return {
        "axes": [joy.get_axis(i) for i in range(joy.get_numaxes())],
        "buttons": [joy.get_button(i) for i in range(joy.get_numbuttons())],
        "hats": [joy.get_hat(i) for i in range(joy.get_numhats())],
    }


def run_debug_mode(left, right):
    print("Debug mode: printing every changing raw axis/button/hat, Ctrl+C to stop.")
    sticks = {"Left": left, "Right": right}
    prev = {name: read_raw_state(joy) for name, joy in sticks.items()}
    ticker = Ticker(CONFIG["poll_hz"])
    while True:
        pygame.event.pump()
        for name, joy in sticks.items():
            state = read_raw_state(joy)
            for i, (old, new) in enumerate(zip(prev[name]["axes"], state["axes"])):
                if abs(new - old) > 0.01:
                    print(f"{name} axis {i}: {old:+.3f} -> {new:+.3f}")
            for i, (old, new) in enumerate(zip(prev[name]["buttons"], state["buttons"])):
                if new != old:
                    print(f"{name} button {i}: {old} -> {new}")
            for i, (old, new) in enumerate(zip(prev[name]["hats"], state["hats"])):
                if new != old:
                    print(f"{name} hat {i}: {old} -> {new}")
            prev[name] = state
        ticker.wait()


def build_button_map(vg, mapping):
    return {
        int(button_index): getattr(vg.XUSB_BUTTON, BUTTON_NAME_MAP[name])
        for button_index, name in mapping.items()
    }


def build_hat_map(vg, mapping):
    result = {}
    for direction, name in mapping.items():
        x_str, y_str = direction.split(",")
        result[(int(x_str), int(y_str))] = getattr(vg.XUSB_BUTTON, BUTTON_NAME_MAP[name])
    return result


def active_buttons(joy, button_map, hat_map, active):
    for index, vg_button in button_map.items():
        if joy.get_button(index):
            active.add(vg_button)
    hat_value = joy.get_hat(0)
    for direction, vg_button in hat_map.items():
        if direction == hat_value:
            active.add(vg_button)


def apply_buttons(gamepad, active, all_buttons):
    for vg_button in all_buttons:
        if vg_button in active:
            gamepad.press_button(button=vg_button)
        else:
            gamepad.release_button(button=vg_button)


def run_gamepad_mode(left, right):
    import vgamepad as vg

    left_button_map = build_button_map(vg, CONFIG["left_buttons"])
    right_button_map = build_button_map(vg, CONFIG["right_buttons"])
    left_hat_map = build_hat_map(vg, CONFIG["left_hat"])
    right_hat_map = build_hat_map(vg, CONFIG["right_hat"])
    all_buttons = (
        set(left_button_map.values())
        | set(right_button_map.values())
        | set(left_hat_map.values())
        | set(right_hat_map.values())
    )

    gamepad = vg.VX360Gamepad()
    print("Virtual controller active. Ctrl+C to stop.")
    ticker = Ticker(CONFIG["poll_hz"])
    try:
        while True:
            pygame.event.pump()

            lx, ly = read_stick(left, CONFIG["invert_y_left"])
            rx, ry = read_stick(right, CONFIG["invert_y_right"])
            gamepad.left_joystick_float(x_value_float=lx, y_value_float=ly)
            gamepad.right_joystick_float(x_value_float=rx, y_value_float=ry)

            gamepad.left_trigger_float(value_float=1.0 if left.get_button(CONFIG["trigger_button"]) else 0.0)
            gamepad.right_trigger_float(value_float=1.0 if right.get_button(CONFIG["trigger_button"]) else 0.0)

            active = set()
            active_buttons(left, left_button_map, left_hat_map, active)
            active_buttons(right, right_button_map, right_hat_map, active)
            apply_buttons(gamepad, active, all_buttons)

            gamepad.update()
            ticker.wait()
    except KeyboardInterrupt:
        gamepad.reset()
        gamepad.update()
        print("\nStopped, virtual controller reset.")
    except Exception:
        import traceback
        traceback.print_exc()
        gamepad.reset()
        gamepad.update()
        sys.exit(1)


def main():
    pygame.init()
    pygame.joystick.init()

    all_joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
    joysticks = [j for j in all_joysticks if "T.16000M" in j.get_name()]
    if len(joysticks) != 2:
        names = ", ".join(j.get_name() for j in all_joysticks) or "none"
        sys.exit(f"Expected 2 T.16000M sticks, found {len(joysticks)}. Detected devices: {names}")

    left, right = identify_sticks(joysticks)

    set_high_res_timer(True)
    try:
        if "--debug" in sys.argv:
            run_debug_mode(left, right)
        elif "--test" in sys.argv:
            run_test_mode(left, right)
        else:
            run_gamepad_mode(left, right)
    finally:
        set_high_res_timer(False)


if __name__ == "__main__":
    main()

