"""
CLI entry point: combines two Thrustmaster T.16000M joysticks into a single
virtual Xbox 360 controller: left stick -> left stick, right stick -> right
stick, and each stick's trigger button -> that side's analog trigger (LT/RT).

Setup:
    1. Install ViGEmBus driver: https://github.com/ViGEm/ViGEmBus/releases
    2. pip install -r requirements.txt

Run with --test to print processed axis/trigger values, or --debug to print
raw axis/button/hat changes, instead of creating a virtual controller -
useful for confirming the axis/button indices in a config match your
hardware. Add --recalibrate to redo the left/right identification, or
--config NAME to use a saved custom mapping instead of the Default one.

See gui.py for the Windows GUI version built on the same engine
(config_store.py / stick_engine.py).
"""

import sys
import time

import pygame

import config_store
from stick_engine import StickManager, Ticker, apply_deadzone, safe_axis, safe_button


def parse_args(argv):
    config_name = config_store.DEFAULT_CONFIG_NAME
    if "--config" in argv:
        idx = argv.index("--config")
        try:
            config_name = argv[idx + 1]
        except IndexError:
            sys.exit("--config requires a config name")
    return {
        "test": "--test" in argv,
        "debug": "--debug" in argv,
        "recalibrate": "--recalibrate" in argv,
        "config_name": config_name,
    }


def run_test_mode(manager):
    print("Test mode: printing values, Ctrl+C to stop.")
    ticker = Ticker(manager.config["poll_hz"])
    while True:
        snap = manager.get_snapshot()
        left, right = snap["left"], snap["right"]
        cfg = manager.config
        lx = apply_deadzone(safe_axis(left["axes"], cfg["stick_x_axis"]), cfg["stick_deadzone"])
        ly = apply_deadzone(safe_axis(left["axes"], cfg["stick_y_axis"]), cfg["stick_deadzone"])
        rx = apply_deadzone(safe_axis(right["axes"], cfg["stick_x_axis"]), cfg["stick_deadzone"])
        ry = apply_deadzone(safe_axis(right["axes"], cfg["stick_y_axis"]), cfg["stick_deadzone"])
        if cfg["invert_y_left"]:
            ly = -ly
        if cfg["invert_y_right"]:
            ry = -ry
        lt = safe_button(left["buttons"], cfg["trigger_button"])
        rt = safe_button(right["buttons"], cfg["trigger_button"])
        print(f"L=({lx:+.2f},{ly:+.2f}) trig={lt}   R=({rx:+.2f},{ry:+.2f}) trig={rt}", end="\r")
        ticker.wait()


def run_debug_mode(manager):
    print("Debug mode: printing every changing raw axis/button/hat, Ctrl+C to stop.")
    ticker = Ticker(manager.config["poll_hz"])
    prev = manager.get_snapshot()
    while True:
        state = manager.get_snapshot()
        for name in ("left", "right"):
            old, new = prev[name], state[name]
            for i, (o, n) in enumerate(zip(old["axes"], new["axes"])):
                if abs(n - o) > 0.01:
                    print(f"{name} axis {i}: {o:+.3f} -> {n:+.3f}")
            for i, (o, n) in enumerate(zip(old["buttons"], new["buttons"])):
                if n != o:
                    print(f"{name} button {i}: {o} -> {n}")
            if old["hat"] != new["hat"]:
                print(f"{name} hat: {old['hat']} -> {new['hat']}")
        prev = state
        ticker.wait()


def run_gamepad_mode(manager):
    manager.start_gamepad()
    print("Virtual controller active. Ctrl+C to stop.")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopped, virtual controller reset.")
    finally:
        manager.stop_gamepad()


def main():
    args = parse_args(sys.argv[1:])

    pygame.init()

    manager = StickManager()
    sticks, all_joysticks = manager.find_sticks()
    if len(sticks) != 2:
        names = ", ".join(j.get_name() for j in all_joysticks) or "none"
        sys.exit(f"Expected 2 T.16000M sticks, found {len(sticks)}. Detected devices: {names}")

    try:
        config = config_store.load_config(args["config_name"])
    except FileNotFoundError:
        sys.exit(f"No config named {args['config_name']!r}. Run the GUI to create one, or omit --config.")
    manager.set_config(config)
    manager.assign(sticks, recalibrate=args["recalibrate"], status_cb=print)

    manager.start_polling()
    try:
        if args["debug"]:
            run_debug_mode(manager)
        elif args["test"]:
            run_test_mode(manager)
        else:
            run_gamepad_mode(manager)
    except KeyboardInterrupt:
        pass
    finally:
        manager.stop_polling()


if __name__ == "__main__":
    main()
