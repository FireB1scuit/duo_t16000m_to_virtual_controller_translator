# duo_t16000m_to_virtual_controller_translator

- [x] read out joystick values
- [x] virtual controller
- [x] left joystick xy to wasd
- [x] right joystick xy to mouse xy
- [x] triggers to LT and RT
- [x] map joystick buttons
- [x] map joystick hat to arrows and XABY
- [ ] map throttle button (slider left = mouse sensitivity, slider right = volume)
- [ ] map extra button on base
- [ ] map horizontal X rotation for X joystick acceleration

## Setup guide

1. Install the [ViGEmBus driver](https://github.com/ViGEm/ViGEmBus/releases) — this lets `vgamepad` create a virtual Xbox 360 controller on Windows.
2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Plug in both T.16000M joysticks.
4. Run `python main.py --test` to print raw axis/button/hat values for each stick. Use this to confirm the indices reported by your hardware match the ones in [config.json](config.json) — adjust `stick_x_axis`, `stick_y_axis`, `trigger_button`, and the button/hat maps if they don't.
5. Run `python main.py` to start the translator. The two joysticks are combined into a single virtual Xbox 360 controller, which any game or app that reads XInput controllers will pick up.

## Button mapping

Mapping is defined in [config.json](config.json); `BUTTON_NAME_MAP` in [main.py](main.py) lists the supported target names.

![Button mapping diagram](button_mapping.svg)

| T.16000M input | Left stick → | Right stick → |
| --- | --- | --- |
| Trigger (button 0) | LT | RT |
| Button 1 | B | A |
| Button 2 | Y | RB |
| Button 3 | LB | X |
| Hat up | D-Pad up | Y |
| Hat down | D-Pad down | A |
| Hat left | D-Pad left | X |
| Hat right | D-Pad right | B |
| Hat diagonal (↖) | Left stick click (L3) | Right stick click (R3) |
| Button 5 | Y | Y |
| Button 6 | Guide (Xbox button) | Guide (Xbox button) |
| Button 7 | X | X |
| Button 8 | A | A |
| Button 9 | B | B |
| Button 10 | Back | Back |
| Button 11 | D-Pad up | D-Pad up |
| Button 12 | Start | Start |
| Button 13 | D-Pad right | D-Pad right |
| Button 14 | D-Pad down | D-Pad down |
| Button 15 | D-Pad left | D-Pad left |
| Button 4, 16–19 | unmapped | unmapped |

Button 4 (screenshot/share) has no Xbox 360 equivalent — `VX360Gamepad` emulates a 360 pad, which predates that button.

![Reference image](reference.png)