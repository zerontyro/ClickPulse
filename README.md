# ClickPulse V4

ClickPulse is a premium automation utility for macro sequencing, hotkey mapping, image recognition triggers, and input emulation on Windows.

## Key Features
- **Control Deck & Pages:** 3 pages of action grids to trigger recorded workflows.
- **Sequence Timeline Editor:** Build sequences of mouse clicks, drags, keyboard hotkeys, and delays.
- **Interactive Drag & Drop:** Easily re-order steps in the timeline editor.
- **Resizable & Fullscreen Modes [NEW in V4]:** The window is now resizable and starts in a maximized state. Press **`F11`** to toggle borderless fullscreen mode.
- **Master Hotkey Switch [NEW in V4]:** Added an **`All Hotkeys Active`** switch to the top header. Toggle it off to temporarily disable all global hotkeys from triggering macros.
- **High-Speed AutoClicker [NEW in V4]:** The autoclicker speed range has been boosted down to **`0.001s`** (1 millisecond) with millisecond-precision slider labels.
- **Live Drag-and-Drop Feedback:** Dragging a grid slot shows a semi-transparent replica of the macro button tracking the mouse cursor in real-time, matching its title, type, and status.
- **Macro Active Switch:** Toggle each macro on or off instantly using the "Active" toggle switch in the Property Inspector. Disabled macros dim on the grid (displaying `[OFF]`) and will not trigger via hotkeys.
- **Advanced Loop Control:** Repeat sequences infinitely or for a set number of loops. Interrupt loops instantly by holding the trigger hotkey.
- **Image Recognition:** Set slots to only execute when a matching image appears on the screen (configurable confidence levels).
- **Universal Gamepad Hotkey Support:** Bind game controller buttons to trigger any slot.
  - **Xbox Wireless Controllers:** Full integration with native XInput.
  - **PS4 DualShock 4 Controllers:** Native support with mapped labels (`Cross`, `Circle`, `Square`, `Triangle`, `L1`, `R1`, `L2`, `R2`, `Share`, `Options`, `PS`, `Touchpad`).

---

## Executable Versions Available (in `dist/`)

1. **`ClickpulseV4.exe`:**
   - The full build including active background controller polling (Xbox & PS4).
2. **`ClickpulseV4_NoController.exe`:**
   - A lightweight version that bypasses gamepad polling loops entirely, saving CPU cycles if you only use keyboard & mouse.

---

## How to Run
Double-click either executable in the `dist` folder. To launch the program automatically when Windows starts:
1. Press `Win + R`, type `shell:startup`, and press Enter.
2. Place a shortcut of your preferred ClickPulse executable in that folder.
