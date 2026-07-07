import os
import sys
import time
import math
import json
import threading
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from pynput import mouse as pynput_mouse
from pynput import keyboard as pynput_keyboard
import darkdetect
import ctypes
from ctypes import Structure, c_ushort, c_ubyte, c_short, c_ulong, POINTER, byref, sizeof, c_uint, c_wchar

# Define XInput structures for Xbox Controller support
class XINPUT_GAMEPAD(Structure):
    _fields_ = [
        ("wButtons", c_ushort),
        ("bLeftTrigger", c_ubyte),
        ("bRightTrigger", c_ubyte),
        ("sThumbLX", c_short),
        ("sThumbLY", c_short),
        ("sThumbRX", c_short),
        ("sThumbRY", c_short)
    ]

class XINPUT_STATE(Structure):
    _fields_ = [
        ("dwPacketNumber", c_ulong),
        ("Gamepad", XINPUT_GAMEPAD)
    ]

# Try loading xinput DLL
xinput_dll = None
for dll_name in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
    try:
        xinput_dll = ctypes.windll.LoadLibrary(dll_name)
        break
    except OSError:
        continue

# If dll loaded, get the state function
if xinput_dll:
    XInputGetState = xinput_dll.XInputGetState
    XInputGetState.argtypes = [c_ulong, POINTER(XINPUT_STATE)]
    XInputGetState.restype = c_ulong
else:
    XInputGetState = None

# Controller Buttons Map
XINPUT_BUTTONS = {
    0x0001: "Controller_Dpad_Up",
    0x0002: "Controller_Dpad_Down",
    0x0004: "Controller_Dpad_Left",
    0x0008: "Controller_Dpad_Right",
    0x0010: "Controller_Start",
    0x0020: "Controller_Back",
    0x0040: "Controller_LStick_Click",
    0x0080: "Controller_RStick_Click",
    0x0100: "Controller_LB",
    0x0200: "Controller_RB",
    0x1000: "Controller_A",
    0x2000: "Controller_B",
    0x4000: "Controller_X",
    0x8000: "Controller_Y",
}

# Define WinMM structures for generic/PlayStation controllers
MAXPNAMELEN = 32

class JOYCAPS(Structure):
    _fields_ = [
        ("wMid", c_ushort),
        ("wPid", c_ushort),
        ("szPname", c_wchar * MAXPNAMELEN),
        ("wXmin", c_uint),
        ("wXmax", c_uint),
        ("wYmin", c_uint),
        ("wYmax", c_uint),
        ("wZmin", c_uint),
        ("wZmax", c_uint),
        ("wNumButtons", c_uint),
        ("wPeriodMin", c_uint),
        ("wPeriodMax", c_uint),
        ("wRmin", c_uint),
        ("wRmax", c_uint),
        ("wSmin", c_uint),
        ("wSmax", c_uint),
        ("wMaxAxes", c_uint),
        ("wNumAxes", c_uint),
        ("wMaxButtons", c_uint),
        ("szRegKey", c_wchar * 32),
        ("szOEMVxD", c_wchar * 266)
    ]

class JOYINFOEX(Structure):
    _fields_ = [
        ("dwSize", c_ulong),
        ("dwFlags", c_ulong),
        ("dwXpos", c_ulong),
        ("dwYpos", c_ulong),
        ("dwZpos", c_ulong),
        ("dwRpos", c_ulong),
        ("dwUpos", c_ulong),
        ("dwVpos", c_ulong),
        ("dwButtons", c_ulong),
        ("dwButtonNumber", c_ulong),
        ("dwPOV", c_ulong),
        ("dwReserved1", c_ulong),
        ("dwReserved2", c_ulong)
    ]

# Image Recognition imports
try:
    import cv2
    import numpy as np
    from PIL import ImageGrab, ImageEnhance, ImageTk, Image
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

# Win32 Drag and Drop imports & setup (Migrated to TkinterDnD2)
from tkinterdnd2 import TkinterDnD, DND_FILES


# Set default appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Global mapping for keyboard keystrokes
SPECIAL_KEYS_MAP = {
    'Ctrl': pynput_keyboard.Key.ctrl,
    'Alt': pynput_keyboard.Key.alt,
    'Shift': pynput_keyboard.Key.shift,
    'Win': pynput_keyboard.Key.cmd,
    'Space': pynput_keyboard.Key.space,
    'Enter': pynput_keyboard.Key.enter,
    'Tab': pynput_keyboard.Key.tab,
    'CapsLock': pynput_keyboard.Key.caps_lock,
    'Backspace': pynput_keyboard.Key.backspace,
    'Delete': pynput_keyboard.Key.delete,
    'Insert': pynput_keyboard.Key.insert,
    'Home': pynput_keyboard.Key.home,
    'End': pynput_keyboard.Key.end,
    'PgUp': pynput_keyboard.Key.page_up,
    'PgDn': pynput_keyboard.Key.page_down,
    'Up': pynput_keyboard.Key.up,
    'Down': pynput_keyboard.Key.down,
    'Left': pynput_keyboard.Key.left,
    'Right': pynput_keyboard.Key.right,
    'Esc': pynput_keyboard.Key.esc,
    'F1': pynput_keyboard.Key.f1,
    'F2': pynput_keyboard.Key.f2,
    'F3': pynput_keyboard.Key.f3,
    'F4': pynput_keyboard.Key.f4,
    'F5': pynput_keyboard.Key.f5,
    'F6': pynput_keyboard.Key.f6,
    'F7': pynput_keyboard.Key.f7,
    'F8': pynput_keyboard.Key.f8,
    'F9': pynput_keyboard.Key.f9,
    'F10': pynput_keyboard.Key.f10,
    'F11': pynput_keyboard.Key.f11,
    'F12': pynput_keyboard.Key.f12,
}

class CoordinatePicker:
    """Creates a full-screen semi-transparent overlay to capture coordinates visually."""
    def __init__(self, parent_app, on_select_callback):
        self.parent = parent_app
        self.callback = on_select_callback
        
        self.parent.withdraw()
        
        self.window = tk.Toplevel()
        self.window.title("ClickPulse - Coordinate Picker")
        self.window.attributes("-fullscreen", True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-alpha", 0.45)
        self.window.configure(cursor="crosshair")
        self.window.configure(bg="#05070a")
        
        self.canvas = tk.Canvas(self.window, bg="#05070a", highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.window.bind("<Motion>", self.on_mouse_move)
        self.window.bind("<Button-1>", self.on_click)
        self.window.bind("<space>", self.on_space)
        self.window.bind("<Escape>", self.on_cancel)
        
        self.current_x = 0
        self.current_y = 0
        self.width = self.window.winfo_screenwidth()
        self.height = self.window.winfo_screenheight()
        
        self.canvas.create_text(
            self.width // 2, 50, 
            text="COORDINATE PICKER MODE", fill="#00f0ff", font=("Helvetica", 18, "bold")
        )
        self.canvas.create_text(
            self.width // 2, 85, 
            text="Move cursor to target • Left-Click or Press SPACE to capture • Press ESC to cancel", 
            fill="#ffffff", font=("Helvetica", 12)
        )

    def on_mouse_move(self, event):
        self.current_x, self.current_y = event.x_root, event.y_root
        self.draw_overlay()

    def draw_overlay(self):
        self.canvas.delete("crosshair")
        self.canvas.create_line(0, self.current_y, self.width, self.current_y, fill="#00f0ff", width=1, tags="crosshair", dash=(4, 4))
        self.canvas.create_line(self.current_x, 0, self.current_x, self.height, fill="#00f0ff", width=1, tags="crosshair", dash=(4, 4))
        
        self.canvas.create_oval(self.current_x - 12, self.current_y - 12, self.current_x + 12, self.current_y + 12, outline="#00ff88", width=2, tags="crosshair")
        self.canvas.create_oval(self.current_x - 3, self.current_y - 3, self.current_x + 3, self.current_y + 3, fill="#00ff88", outline="#00ff88", tags="crosshair")
        
        badge_text = f" X: {self.current_x}  Y: {self.current_y} "
        text_w, text_h = 130, 24
        badge_x, badge_y = self.current_x + 18, self.current_y + 18
        
        if badge_x + text_w > self.width:
            badge_x = self.current_x - text_w - 18
        if badge_y + text_h > self.height:
            badge_y = self.current_y - text_h - 18
            
        self.canvas.create_rectangle(badge_x, badge_y, badge_x + text_w, badge_y + text_h, fill="#161b22", outline="#00f0ff", width=1, tags="crosshair")
        self.canvas.create_text(badge_x + text_w // 2, badge_y + text_h // 2, text=badge_text, fill="#ffffff", font=("Consolas", 11, "bold"), tags="crosshair")

    def on_click(self, event):
        self.capture()

    def on_space(self, event):
        self.capture()

    def capture(self):
        self.window.destroy()
        self.parent.deiconify()
        self.callback(self.current_x, self.current_y)

    def on_cancel(self, event):
        self.window.destroy()
        self.parent.deiconify()
        self.callback(None, None)


class ScreenSnipper:
    """Creates a full-screen overlay to snip a region of the screen and save it as an image."""
    def __init__(self, parent_app, on_select_callback):
        self.parent = parent_app
        self.callback = on_select_callback
        
        self.parent.withdraw()
        self.parent.update_idletasks()
        time.sleep(0.35)  # Wait for window to fade out
        
        try:
            self.screenshot = ImageGrab.grab(all_screens=True)
            self.width, self.height = self.screenshot.size
        except Exception as e:
            self.parent.deiconify()
            self.callback(None)
            self.parent.log(f"Snipping capture failed: {str(e)}", "#ff453a")
            return

        self.window = tk.Toplevel()
        self.window.title("ClickPulse - Image Snipper")
        self.window.attributes("-fullscreen", True)
        self.window.attributes("-topmost", True)
        
        self.canvas = tk.Canvas(self.window, bg="black", highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        
        from PIL import ImageTk, ImageEnhance
        
        self.bg_image_original = self.screenshot
        enhancer = ImageEnhance.Brightness(self.bg_image_original)
        self.bg_image_dimmed = enhancer.enhance(0.40)
        
        self.tk_bg_image = ImageTk.PhotoImage(self.bg_image_dimmed)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_bg_image)
        
        self.window.bind("<ButtonPress-1>", self.on_button_press)
        self.window.bind("<B1-Motion>", self.on_move_press)
        self.window.bind("<ButtonRelease-1>", self.on_button_release)
        self.window.bind("<Escape>", self.on_cancel)
        
        self.start_x = None
        self.start_y = None
        self.cur_x = None
        self.cur_y = None
        
        self.canvas.create_text(
            self.width // 2, 50,
            text="SCREEN SNIPPER MODE", fill="#ff9500", font=("Helvetica", 18, "bold")
        )
        self.canvas.create_text(
            self.width // 2, 85,
            text="Left-Click and drag a box around the target image • Release to capture • Press ESC to cancel",
            fill="#ffffff", font=("Helvetica", 12)
        )

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y

    def on_move_press(self, event):
        self.cur_x = event.x
        self.cur_y = event.y
        
        self.canvas.delete("snipping_rect")
        
        x1 = min(self.start_x, self.cur_x)
        y1 = min(self.start_y, self.cur_y)
        x2 = max(self.start_x, self.cur_x)
        y2 = max(self.start_y, self.cur_y)
        
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="#ff9500", width=2, tags="snipping_rect")
        self.canvas.create_rectangle(x1+1, y1+1, x2-1, y2-1, outline="#ffffff", width=1, dash=(2, 2), tags="snipping_rect")

    def on_button_release(self, event):
        self.cur_x = event.x
        self.cur_y = event.y
        
        self.window.destroy()
        self.parent.deiconify()
        
        if self.start_x is None or self.cur_x is None:
            self.callback(None)
            return
            
        x1 = min(self.start_x, self.cur_x)
        y1 = min(self.start_y, self.cur_y)
        x2 = max(self.start_x, self.cur_x)
        y2 = max(self.start_y, self.cur_y)
        
        if x2 - x1 < 5 or y2 - y1 < 5:
            self.callback(None)
            return
            
        cropped = self.bg_image_original.crop((x1, y1, x2, y2))
        self.callback(cropped)

    def on_cancel(self, event):
        self.window.destroy()
        self.parent.deiconify()
        self.callback(None)


class ClickPulseApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)
        
        # Configure Main Window
        self.title("ClickPulse - Virtual Control Deck")
        self.geometry("1020x860")
        self.resizable(False, False)
        
        # Style Constants
        self.bg_color = "#0a0c10"
        self.frame_bg = "#12161f"
        self.accent_cyan = "#00f0ff"
        self.accent_green = "#00ff88"
        self.accent_purple = "#bf5af2"
        self.accent_orange = "#ff9500"
        self.accent_pink = "#ff5efb"
        self.accent_gold = "#ffd60a"
        self.text_white = "#ffffff"
        self.text_gray = "#8b949e"
        
        self.button_to_pos = {}
        
        self.configure(fg_color=self.bg_color)
        
        # Selected slot coordinates
        self.selected_row = 0
        self.selected_col = 0
        
        # Global states
        self.is_recording_slot = False
        self.recorded_keys_temp = set()
        self.pressed_keys_global = set()
        self.recording_card_idx = None
        self.sequence_actions = []            # Temp container for timeline widgets
        self.last_triggered_time = 0.0
        
        # Loop execution control state
        self.current_running_slot = None         # (page_idx, row, col) when running
        self.running_slot_start_time = 0.0
        self.stop_current_loop = False
        
        # File paths
        exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        self.board_file = os.path.join(exe_dir, "board.json")
        
        # Load board structures
        self.load_board_data()
        
        # Input controllers
        self.mouse_controller = pynput_mouse.Controller()
        self.keyboard_controller = pynput_keyboard.Controller()
        self.sequence_lock = threading.Lock()

        # AutoClicker & MouseJiggler state
        self.autoclicker_active = False
        self.jiggler_active = False
        self._autoclicker_thread = None
        self._jiggler_thread = None
        self.autoclicker_hotkey = set()          # Recorded hotkey combo
        self.is_recording_ac_hotkey = False      # Recording mode flag
        
        # Build UI layout
        self.setup_ui()
        
        # Select first button by default
        self.on_grid_button_clicked(0, 0)
        
        # Bind keyboard listeners
        self.keyboard_listener = pynput_keyboard.Listener(
            on_press=self.global_on_press,
            on_release=self.global_on_release
        )
        self.keyboard_listener.start()

        # Start Controller polling thread (unless disabled by build type)
        exe_name = os.path.basename(sys.executable).lower()
        self.disable_controller = "nocontroller" in exe_name
        self.pressed_controller_buttons = set()
        
        if self.disable_controller:
            self.log("Controller support disabled for this build.", self.accent_purple)
        else:
            self.controller_thread = threading.Thread(target=self._poll_controller, daemon=True)
            self.controller_thread.start()
        
        self.log("Virtual Control Deck ready.")
        self.after(100, self.enable_drag_and_drop)

    def load_board_data(self):
        self.board_pages = []
        loaded = False
        if os.path.exists(self.board_file):
            try:
                with open(self.board_file, "r") as f:
                    data = json.load(f)
                    
                    # Check if data is version 2 format (dict with pages)
                    if isinstance(data, dict) and "pages" in data:
                        pages_data = data["pages"]
                        for page_data in pages_data:
                            page_slots = []
                            for r in range(4):
                                row_data = []
                                for c in range(8):
                                    slot = page_data[r][c]
                                    slot['hotkey'] = set(slot['hotkey'])
                                    if 'steps' not in slot:
                                        slot['steps'] = []
                                    row_data.append(slot)
                                page_slots.append(row_data)
                            self.board_pages.append(page_slots)
                        loaded = True
                    # If it's a version 1 format (just a list of list of slots - a single page)
                    elif isinstance(data, list):
                        page_slots = []
                        for r in range(4):
                            row_data = []
                            for c in range(8):
                                slot = data[r][c]
                                slot['hotkey'] = set(slot['hotkey'])
                                if 'steps' not in slot:
                                    slot['steps'] = []
                                row_data.append(slot)
                            page_slots.append(row_data)
                        self.board_pages.append(page_slots)
                        # Add 4 more empty pages
                        for _ in range(4):
                            self.board_pages.append(self.create_empty_page_slots())
                        loaded = True
            except Exception as e:
                pass
                
        if not loaded:
            # Create 5 empty pages
            for _ in range(5):
                self.board_pages.append(self.create_empty_page_slots())
            self.save_board_data()
            
        self.current_page = 0
        self.board_slots = self.board_pages[self.current_page]

    def create_empty_page_slots(self):
        page_slots = []
        for r in range(4):
            row_data = []
            for c in range(8):
                row_data.append({
                    'type': 'empty',
                    'title': '',
                    'hotkey': set(),
                    'app_path': '',
                    'web_url': '',
                    'mouse_x': 1000,
                    'mouse_y': 850,
                    'click_type': 'Left Click',
                    'glide_enabled': True,
                    'glide_duration': 0.1,
                    'steps': [],
                    'loop_enabled': False,
                    'loop_count': 0
                })
            page_slots.append(row_data)
        return page_slots

    def save_board_data(self):
        pages_serializable = []
        for page in self.board_pages:
            page_serializable = []
            for r in range(4):
                row_data = []
                for c in range(8):
                    slot = page[r][c]
                    slot_copy = slot.copy()
                    slot_copy['hotkey'] = list(slot['hotkey'])
                    row_data.append(slot_copy)
                page_serializable.append(row_data)
            pages_serializable.append(page_serializable)
            
        data = {
            "version": 2,
            "pages": pages_serializable
        }
        
        try:
            with open(self.board_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            self.log(f"Error saving board settings: {str(e)}", "#ff453a")

    def setup_ui(self):
        # 1. Main Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=30, pady=(20, 10))
        
        title_lbl = ctk.CTkLabel(header_frame, text="VIRTUAL DECK CONSOLE", text_color=self.accent_cyan, font=("Helvetica", 20, "bold"))
        title_lbl.pack(side="left")
        
        profile_lbl = ctk.CTkLabel(header_frame, text="Default Profile v", text_color=self.text_gray, font=("Helvetica", 12))
        profile_lbl.pack(side="left", padx=15)

        # Page Controls
        self.page_controls_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        self.page_controls_frame.pack(side="right")
        
        self.btn_prev_page = ctk.CTkButton(
            self.page_controls_frame, text="◀", fg_color="#1c212e", hover_color="#2b3240", border_color="#30363d", border_width=1,
            text_color=self.accent_cyan, font=("Helvetica", 12, "bold"), width=30, height=26, corner_radius=6,
            command=self.prev_page
        )
        self.btn_prev_page.pack(side="left", padx=5)
        
        self.page_lbl = ctk.CTkLabel(self.page_controls_frame, text="PAGE 1 / 5", text_color=self.text_white, font=("Helvetica", 11, "bold"))
        self.page_lbl.pack(side="left", padx=10)
        
        self.btn_next_page = ctk.CTkButton(
            self.page_controls_frame, text="▶", fg_color="#1c212e", hover_color="#2b3240", border_color="#30363d", border_width=1,
            text_color=self.accent_cyan, font=("Helvetica", 12, "bold"), width=30, height=26, corner_radius=6,
            command=self.next_page
        )
        self.btn_next_page.pack(side="left", padx=5)

        # 2. Main Middle Split
        middle_split = ctk.CTkFrame(self, fg_color="transparent")
        middle_split.pack(fill="both", expand=True, padx=25, pady=(0, 10))

        # 2A. Left Layout: Grid panel + Inspector Panel
        left_panel = ctk.CTkFrame(middle_split, fg_color="transparent")
        left_panel.pack(side="left", fill="both", expand=True)

        # 8x4 Button Grid (Stream Deck Layout)
        self.grid_buttons = []
        grid_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        grid_frame.pack(pady=10)
        
        for r in range(4):
            row_btns = []
            for c in range(8):
                slot = self.board_slots[r][c]
                border_c = self.get_slot_border_color(slot['type'])
                
                btn = ctk.CTkButton(
                    grid_frame,
                    text=slot['title'] if slot['title'] else (slot['type'].upper() if slot['type'] != 'empty' else ""),
                    width=74,
                    height=74,
                    corner_radius=14,
                    fg_color="#181c24",
                    hover_color="#242b36",
                    border_color=border_c,
                    border_width=2,
                    text_color="#ffffff",
                    font=("Helvetica", 9, "bold"),
                    command=lambda row=r, col=c: self.on_grid_button_clicked(row, col)
                )
                btn.grid(row=r, column=c, padx=6, pady=6)
                
                self.button_to_pos[btn] = (r, c)
                canvas = btn._canvas
                self.button_to_pos[canvas] = (r, c)
                canvas.bind("<Button-1>", lambda event, row=r, col=c: self.start_grid_drag(event, row, col), add="+")
                canvas.bind("<B1-Motion>", self.grid_drag_motion, add="+")
                canvas.bind("<ButtonRelease-1>", self.end_grid_drag, add="+")
                
                row_btns.append(btn)
            self.grid_buttons.append(row_btns)

        # Bottom Inspector Panel
        self.inspector_panel = ctk.CTkFrame(left_panel, fg_color=self.frame_bg, corner_radius=12, border_color="#21262d", border_width=1, height=380)
        self.inspector_panel.pack(fill="both", expand=True, pady=(5, 0))
        self.inspector_panel.pack_propagate(False)

        # Inspector Title, Type Selection and Hotkeys Config Row
        self.build_inspector_header()

        # Build Parameter Sub-frames inside Inspector
        self.build_inspector_param_frames()

        # 2B. Right Layout: Action Toolbox Sidebar
        self.toolbox_panel = ctk.CTkFrame(middle_split, fg_color=self.frame_bg, width=220, corner_radius=12, border_color="#21262d", border_width=1)
        self.toolbox_panel.pack(side="right", fill="y", padx=(10, 0))
        self.toolbox_panel.pack_propagate(False)

        tb_title = ctk.CTkLabel(self.toolbox_panel, text="Toolbox Actions", text_color=self.accent_cyan, font=("Helvetica", 14, "bold"))
        tb_title.pack(anchor="w", padx=15, pady=(15, 10))

        tb_desc = ctk.CTkLabel(self.toolbox_panel, text="Select a grid slot and click an action type below to assign it:", text_color=self.text_gray, font=("Helvetica", 11), wraplength=190, justify="left")
        tb_desc.pack(anchor="w", padx=15, pady=(0, 15))

        # Toolbox Assignment Triggers
        self.btn_tb_app = ctk.CTkButton(self.toolbox_panel, text="Launch Application", fg_color="#182d24", hover_color="#224033", text_color=self.accent_green, font=("Helvetica", 12, "bold"), height=34, command=lambda: self.assign_action_to_selected("app"))
        self.btn_tb_app.pack(fill="x", padx=15, pady=6)

        self.btn_tb_web = ctk.CTkButton(self.toolbox_panel, text="Launch Website", fg_color="#2c1a30", hover_color="#3d2442", text_color=self.accent_pink, font=("Helvetica", 12, "bold"), height=34, command=lambda: self.assign_action_to_selected("web"))
        self.btn_tb_web.pack(fill="x", padx=15, pady=6)

        self.btn_tb_click = ctk.CTkButton(self.toolbox_panel, text="Mouse Clicker", fg_color="#1a2536", hover_color="#24344d", text_color=self.accent_cyan, font=("Helvetica", 12, "bold"), height=34, command=lambda: self.assign_action_to_selected("mouse"))
        self.btn_tb_click.pack(fill="x", padx=15, pady=6)

        self.btn_tb_image = ctk.CTkButton(self.toolbox_panel, text="Click at Image", fg_color="#2c271c", hover_color="#3d3727", text_color=self.accent_orange, font=("Helvetica", 12, "bold"), height=34, command=lambda: self.assign_action_to_selected("image"))
        self.btn_tb_image.pack(fill="x", padx=15, pady=6)

        self.btn_tb_macro = ctk.CTkButton(self.toolbox_panel, text="Macro Sequence", fg_color="#241e33", hover_color="#332a4a", text_color=self.accent_purple, font=("Helvetica", 12, "bold"), height=34, command=lambda: self.assign_action_to_selected("macro"))
        self.btn_tb_macro.pack(fill="x", padx=15, pady=6)

        self.btn_tb_clear = ctk.CTkButton(self.toolbox_panel, text="Clear Selected Slot", fg_color="transparent", hover_color="#2b3240", border_color="#30363d", border_width=1, text_color=self.text_gray, font=("Helvetica", 12, "bold"), height=34, command=lambda: self.assign_action_to_selected("empty"))
        self.btn_tb_clear.pack(fill="x", padx=15, pady=(25, 6))

        # ══════════════════════════════════════
        # ⚡ Utility Tools Panel
        # ══════════════════════════════════════
        util_outer = ctk.CTkScrollableFrame(
            self.toolbox_panel, fg_color="transparent",
            scrollbar_button_color="#2b3240", scrollbar_button_hover_color="#3a4255"
        )
        util_outer.pack(fill="both", expand=True, padx=6, pady=(10, 6))

        util_title = ctk.CTkLabel(util_outer, text="⚡  Utility Tools", font=("Helvetica", 11, "bold"), text_color=self.accent_cyan)
        util_title.pack(anchor="w", padx=4, pady=(4, 8))

        # ── AutoClicker Section ──────────────
        ac_frame = ctk.CTkFrame(util_outer, fg_color="#0f1a12", corner_radius=8, border_color="#1a4025", border_width=1)
        ac_frame.pack(fill="x", padx=2, pady=(0, 10))

        ctk.CTkLabel(ac_frame, text="🖱  AutoClicker", font=("Helvetica", 10, "bold"), text_color=self.accent_green).pack(anchor="w", padx=8, pady=(6, 4))

        # Interval slider
        ac_int_row = ctk.CTkFrame(ac_frame, fg_color="transparent")
        ac_int_row.pack(fill="x", padx=8, pady=(0, 2))
        self.ac_interval_lbl = ctk.CTkLabel(ac_int_row, text="Interval: 1.00s", font=("Helvetica", 9), text_color=self.text_gray)
        self.ac_interval_lbl.pack(side="left")
        self.ac_interval_slider = ctk.CTkSlider(
            ac_frame, from_=0.05, to=5.0, number_of_steps=99,
            progress_color=self.accent_green, button_color=self.accent_green, button_hover_color="#00cc6a",
            height=12, command=lambda v: self.ac_interval_lbl.configure(text=f"Interval: {v:.2f}s")
        )
        self.ac_interval_slider.set(1.0)
        self.ac_interval_slider.pack(fill="x", padx=8, pady=(0, 6))

        # Duration entry
        ac_dur_row = ctk.CTkFrame(ac_frame, fg_color="transparent")
        ac_dur_row.pack(fill="x", padx=8, pady=(0, 6))
        ctk.CTkLabel(ac_dur_row, text="Duration (0=∞):", font=("Helvetica", 9), text_color=self.text_gray).pack(side="left", padx=(0, 4))
        self.ac_duration_entry = ctk.CTkEntry(
            ac_dur_row, width=52, height=20, placeholder_text="sec",
            fg_color="#0a0c10", border_color="#1a4025", text_color=self.text_white,
            font=("Helvetica", 10)
        )
        self.ac_duration_entry.insert(0, "0")
        self.ac_duration_entry.pack(side="left")
        ctk.CTkLabel(ac_dur_row, text="sec", font=("Helvetica", 9), text_color="#4a5568").pack(side="left", padx=(3, 0))

        # Hotkey row
        ac_hk_row = ctk.CTkFrame(ac_frame, fg_color="transparent")
        ac_hk_row.pack(fill="x", padx=8, pady=(0, 4))
        ctk.CTkLabel(ac_hk_row, text="Hotkey:", font=("Helvetica", 9), text_color=self.text_gray).pack(side="left", padx=(0, 4))
        self.ac_hotkey_display = ctk.CTkLabel(
            ac_hk_row, text="None", font=("Helvetica", 9, "bold"),
            text_color=self.accent_green, width=70, anchor="w"
        )
        self.ac_hotkey_display.pack(side="left", padx=(0, 4))
        self.ac_hotkey_rec_btn = ctk.CTkButton(
            ac_hk_row, text="Record", width=50, height=18,
            fg_color="#1a4025", hover_color="#224a30",
            text_color=self.accent_green, font=("Helvetica", 9, "bold"),
            corner_radius=4, command=self.start_record_ac_hotkey
        )
        self.ac_hotkey_rec_btn.pack(side="left", padx=(0, 3))
        ctk.CTkButton(
            ac_hk_row, text="✕", width=18, height=18,
            fg_color="#2a1010", hover_color="#3d1515",
            text_color="#ff453a", font=("Helvetica", 9, "bold"),
            corner_radius=4, command=self.clear_ac_hotkey
        ).pack(side="left")

        # Toggle button
        self.btn_autoclicker = ctk.CTkButton(
            ac_frame, text="🖱  AutoClicker  OFF",
            fg_color="#1c212e", hover_color="#2b3240",
            border_color="#1a4025", border_width=1,
            text_color=self.text_gray,
            font=("Helvetica", 11, "bold"), height=28,
            command=self.toggle_autoclicker
        )
        self.btn_autoclicker.pack(fill="x", padx=8, pady=(0, 8))

        # ── MouseJiggler Section ─────────────
        jg_frame = ctk.CTkFrame(util_outer, fg_color="#0a1520", corner_radius=8, border_color="#1a3050", border_width=1)
        jg_frame.pack(fill="x", padx=2, pady=(0, 6))

        ctk.CTkLabel(jg_frame, text="🐭  MouseJiggler", font=("Helvetica", 10, "bold"), text_color=self.accent_cyan).pack(anchor="w", padx=8, pady=(6, 4))

        # Jiggle interval slider
        jg_int_row = ctk.CTkFrame(jg_frame, fg_color="transparent")
        jg_int_row.pack(fill="x", padx=8, pady=(0, 2))
        self.jg_interval_lbl = ctk.CTkLabel(jg_int_row, text="Interval: 1.00s", font=("Helvetica", 9), text_color=self.text_gray)
        self.jg_interval_lbl.pack(side="left")
        self.jg_interval_slider = ctk.CTkSlider(
            jg_frame, from_=0.05, to=10.0, number_of_steps=199,
            progress_color=self.accent_cyan, button_color=self.accent_cyan, button_hover_color="#00b8cc",
            height=12, command=lambda v: self.jg_interval_lbl.configure(text=f"Interval: {v:.2f}s")
        )
        self.jg_interval_slider.set(1.0)
        self.jg_interval_slider.pack(fill="x", padx=8, pady=(0, 6))

        # Jiggle range slider
        jg_rng_row = ctk.CTkFrame(jg_frame, fg_color="transparent")
        jg_rng_row.pack(fill="x", padx=8, pady=(0, 2))
        self.jg_range_lbl = ctk.CTkLabel(jg_rng_row, text="Range: 80px", font=("Helvetica", 9), text_color=self.text_gray)
        self.jg_range_lbl.pack(side="left")
        self.jg_range_slider = ctk.CTkSlider(
            jg_frame, from_=5, to=400, number_of_steps=79,
            progress_color="#00c8ff", button_color="#00c8ff", button_hover_color="#0099cc",
            height=12, command=lambda v: self.jg_range_lbl.configure(text=f"Range: {int(v)}px")
        )
        self.jg_range_slider.set(80)
        self.jg_range_slider.pack(fill="x", padx=8, pady=(0, 6))

        # Toggle button
        self.btn_jiggler = ctk.CTkButton(
            jg_frame, text="🐭  MouseJiggler  OFF",
            fg_color="#1c212e", hover_color="#2b3240",
            border_color="#1a3050", border_width=1,
            text_color=self.text_gray,
            font=("Helvetica", 11, "bold"), height=28,
            command=self.toggle_mousejiggler
        )
        self.btn_jiggler.pack(fill="x", padx=8, pady=(0, 8))

        # Keep legacy references for backward compat
        self.util_interval_slider = self.ac_interval_slider
        self.util_interval_lbl = self.ac_interval_lbl

        # 3. Visual Log Panel at the absolute bottom
        self.log_container = ctk.CTkFrame(self, fg_color="transparent")
        self.log_container.pack(fill="x", side="bottom", padx=25, pady=(0, 15))

        log_head = ctk.CTkFrame(self.log_container, fg_color="transparent")
        log_head.pack(fill="x")
        
        ctk.CTkLabel(log_head, text="Visual Event Logs", text_color=self.text_white, font=("Helvetica", 12, "bold")).pack(side="left")
        ctk.CTkButton(log_head, text="Clear Logs", fg_color="transparent", hover_color="#1a1e26", text_color=self.text_gray, font=("Helvetica", 10, "underline"), width=60, height=20, command=self.clear_logs).pack(side="right")
        
        self.log_text = ctk.CTkTextbox(self.log_container, fg_color="#06080b", border_color="#1f242e", border_width=1, text_color="#00ff88", font=("Consolas", 11), corner_radius=8, height=100)
        self.log_text.pack(fill="both", expand=True, pady=(5, 0))
        self.log_text.configure(state="disabled")

    # --- Utility Tools: AutoClicker & MouseJiggler ---

    def _update_utility_interval_label(self, val=None):
        interval = self.ac_interval_slider.get()
        self.ac_interval_lbl.configure(text=f"Interval: {interval:.2f}s")

    # ── AutoClicker Hotkey Recording ──────────────────────
    def start_record_ac_hotkey(self):
        self.is_recording_ac_hotkey = True
        self.autoclicker_hotkey = set()
        self.ac_hotkey_rec_btn.configure(text="● Stop", fg_color="#2a1010", text_color="#ff453a")
        self.ac_hotkey_display.configure(text="Press keys...", text_color="#ff9500")
        self.log("Recording AutoClicker hotkey — press your combo, then release all keys.", "#ff9500")

    def clear_ac_hotkey(self):
        self.autoclicker_hotkey = set()
        self.is_recording_ac_hotkey = False
        self.ac_hotkey_display.configure(text="None", text_color=self.accent_green)
        self.ac_hotkey_rec_btn.configure(text="Record", fg_color="#1a4025", text_color=self.accent_green)
        self.log("AutoClicker hotkey cleared.", self.text_gray)

    # ── AutoClicker ───────────────────────────────────────
    def toggle_autoclicker(self):
        self.autoclicker_active = not self.autoclicker_active
        if self.autoclicker_active:
            self.btn_autoclicker.configure(
                text="🖱  AutoClicker  ON",
                fg_color="#0a2a1a", border_color=self.accent_green,
                text_color=self.accent_green
            )
            try:
                dur = float(self.ac_duration_entry.get().strip())
            except ValueError:
                dur = 0.0
            dur_str = f" for {dur:.1f}s" if dur > 0 else " (∞)"
            self.log(f"AutoClicker started{dur_str}. Click again or press hotkey to stop.", self.accent_green)
            self._autoclicker_thread = threading.Thread(target=self._run_autoclicker, daemon=True)
            self._autoclicker_thread.start()
        else:
            self.btn_autoclicker.configure(
                text="🖱  AutoClicker  OFF",
                fg_color="#1c212e", border_color="#1a4025",
                text_color=self.text_gray
            )
            self.log("AutoClicker stopped.", self.text_gray)

    def _run_autoclicker(self):
        import time as _time
        try:
            dur = float(self.ac_duration_entry.get().strip())
        except ValueError:
            dur = 0.0
        start = _time.time()
        while self.autoclicker_active:
            interval = self.ac_interval_slider.get()
            self.mouse_controller.click(pynput_mouse.Button.left, 1)
            _time.sleep(interval)
            if dur > 0 and (_time.time() - start) >= dur:
                # Auto-stop after duration
                self.autoclicker_active = False
                self.after(0, lambda: self.btn_autoclicker.configure(
                    text="🖱  AutoClicker  OFF",
                    fg_color="#1c212e", border_color="#1a4025",
                    text_color=self.text_gray
                ))
                self.after(0, lambda: self.log("AutoClicker: duration reached, auto-stopped.", self.accent_green))
                break

    # ── MouseJiggler ──────────────────────────────────────
    def toggle_mousejiggler(self):
        self.jiggler_active = not self.jiggler_active
        if self.jiggler_active:
            self.btn_jiggler.configure(
                text="🐭  MouseJiggler  ON",
                fg_color="#0a1a2a", border_color=self.accent_cyan,
                text_color=self.accent_cyan
            )
            self.log("MouseJiggler started. Click the button again to stop.", self.accent_cyan)
            self._jiggler_thread = threading.Thread(target=self._run_jiggler, daemon=True)
            self._jiggler_thread.start()
        else:
            self.btn_jiggler.configure(
                text="🐭  MouseJiggler  OFF",
                fg_color="#1c212e", border_color="#1a3050",
                text_color=self.text_gray
            )
            self.log("MouseJiggler stopped.", self.text_gray)

    def _run_jiggler(self):
        import time as _time
        import random as _random
        while self.jiggler_active:
            interval = self.jg_interval_slider.get()
            jiggle_range = int(self.jg_range_slider.get())
            cx, cy = self.mouse_controller.position
            dx = _random.randint(-jiggle_range, jiggle_range)
            dy = _random.randint(-jiggle_range, jiggle_range)
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            nx = max(0, min(sw - 1, cx + dx))
            ny = max(0, min(sh - 1, cy + dy))
            self.mouse_controller.position = (nx, ny)
            _time.sleep(interval)

    # --- Grid Drag-and-Drop Methods ---


    def start_grid_drag(self, event, row, col):
        self.drag_src_row = row
        self.drag_src_col = col
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        self.is_dragging_grid = False

    def grid_drag_motion(self, event):
        if not hasattr(self, 'drag_start_x'):
            return
        dx = abs(event.x_root - self.drag_start_x)
        dy = abs(event.y_root - self.drag_start_y)
        # 8-pixel threshold to start drag
        if dx > 8 or dy > 8:
            if not getattr(self, 'is_dragging_grid', False):
                self.is_dragging_grid = True
                self.config(cursor="hand2")
                self.log(f"Dragging grid slot: Row {self.drag_src_row + 1} Col {self.drag_src_col + 1}...")

    def end_grid_drag(self, event):
        self.config(cursor="")
        if not getattr(self, 'is_dragging_grid', False):
            # Regular click selection
            self.on_grid_button_clicked(self.drag_src_row, self.drag_src_col)
            return

        self.is_dragging_grid = False
        target_widget = self.winfo_containing(event.x_root, event.y_root)
        if not target_widget:
            return

        target_pos = self.find_grid_button_from_widget(target_widget)
        if target_pos:
            tr, tc = target_pos
            if tr == self.drag_src_row and tc == self.drag_src_col:
                return # Dropped on self
            self.move_or_swap_slots(self.drag_src_row, self.drag_src_col, tr, tc)

    def find_grid_button_from_widget(self, widget):
        curr = widget
        while curr:
            if curr in self.button_to_pos:
                return self.button_to_pos[curr]
            curr = curr.master if hasattr(curr, "master") else None
        return None

    def move_or_swap_slots(self, src_r, src_c, tgt_r, tgt_c):
        # Swap configuration in current page
        src_slot = self.board_slots[src_r][src_c]
        tgt_slot = self.board_slots[tgt_r][tgt_c]

        self.board_slots[src_r][src_c] = tgt_slot
        self.board_slots[tgt_r][tgt_c] = src_slot

        # Refresh UI
        self.refresh_grid_buttons()

        # Focus inspector on the target slot
        self.on_grid_button_clicked(tgt_r, tgt_c)

        # Save to database
        self.save_board_data()

        self.log(f"Grid Move: Swapped Row {src_r + 1} Col {src_c + 1} with Row {tgt_r + 1} Col {tgt_c + 1}", self.accent_cyan)

    # --- Win32 Drag & Drop Methods (TkinterDnD2) ---

    def enable_drag_and_drop(self):
        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self.on_drop_event)
            self.log("Drag-and-Drop enabled for files & folders.")
        except Exception as e:
            self.log(f"Drag-and-Drop initialization failed: {e}", "#ff9500")

    def on_drop_event(self, event):
        try:
            if not event.data:
                return
            # Use self.tk.splitlist to correctly parse paths, handling spaces and braces
            files = self.tk.splitlist(event.data)
            if files:
                self.on_files_dropped(files)
        except Exception as e:
            self.log(f"Error handling dropped files: {e}", "#ff453a")

    def on_files_dropped(self, files):
        r, c = self.selected_row, self.selected_col
        if r is None or c is None:
            r, c = 0, 0
            self.on_grid_button_clicked(0, 0)
            
        if not files:
            return
            
        # Parse first dropped file/folder path and normalize
        path = os.path.normpath(files[0])
        basename = os.path.basename(path)
        title, ext = os.path.splitext(basename)
        if not title:
            title = basename
            
        title = title.capitalize()
        
        slot = self.board_slots[r][c]
        slot['type'] = 'app'
        slot['title'] = title
        slot['app_path'] = path
        
        # Refresh grid button text and border
        self.grid_buttons[r][c].configure(text=title, border_color=self.accent_green)
        
        # Reload current slot to inspector and save settings
        self.load_slot_to_inspector(r, c)
        self.save_board_data()
        
        self.log(f"Dropped File: Assigned Launch App -> {title} ({path})", self.accent_green)

    def create_bat_file_for_selected_slot(self):
        r, c = self.selected_row, self.selected_col
        if r is None or c is None:
            return
            
        slot = self.board_slots[r][c]
        slot_type = slot['type']
        
        if slot_type == 'empty':
            self.log("Cannot export .bat file for an empty slot.", "#ff9500")
            return
            
        default_name = f"{slot['title'] or slot_type}.bat"
        # Sanitize filename
        import re
        default_name = re.sub(r'[\/*?:"<>|]', '', default_name)
        
        save_path = filedialog.asksaveasfilename(
            initialfile=default_name,
            filetypes=[("Batch Files", "*.bat")],
            title="Save Exported Batch File"
        )
        
        if not save_path:
            return
            
        project_dir = os.path.dirname(self.board_file)
        
        content = ""
        if slot_type == 'app':
            app_path = slot.get('app_path', '')
            content = f'@echo off\n:: ClickPulse Export - Launch Application\nstart "" "{app_path}"\n'
            
        elif slot_type == 'web':
            web_url = slot.get('web_url', '')
            content = f'@echo off\n:: ClickPulse Export - Launch Website\nstart "" "{web_url}"\n'
            
        elif slot_type == 'mouse':
            x = slot.get('mouse_x', 1000)
            y = slot.get('mouse_y', 850)
            click_type = slot.get('click_type', 'Left Click')
            
            click_cmd = ""
            if click_type == "Left Click":
                click_cmd = "$sys::mouse_event(0x0002, 0, 0, 0, 0); Start-Sleep -m 50; $sys::mouse_event(0x0004, 0, 0, 0, 0);"
            elif click_type == "Double Left Click":
                click_cmd = "$sys::mouse_event(0x0002, 0, 0, 0, 0); Start-Sleep -m 50; $sys::mouse_event(0x0004, 0, 0, 0, 0); Start-Sleep -m 100; $sys::mouse_event(0x0002, 0, 0, 0, 0); Start-Sleep -m 50; $sys::mouse_event(0x0004, 0, 0, 0, 0);"
            elif click_type == "Right Click":
                click_cmd = "$sys::mouse_event(0x0008, 0, 0, 0, 0); Start-Sleep -m 50; $sys::mouse_event(0x0010, 0, 0, 0, 0);"
            elif click_type == "Middle Click":
                click_cmd = "$sys::mouse_event(0x0020, 0, 0, 0, 0); Start-Sleep -m 50; $sys::mouse_event(0x0040, 0, 0, 0, 0);"
                
            content = (
                f'@echo off\n'
                f':: ClickPulse Export - Mouse Clicker\n'
                f'powershell -NoProfile -ExecutionPolicy Bypass -Command ^\n'
                f'  "[void][System.Reflection.Assembly]::LoadWithPartialName(\'System.Windows.Forms\');" ^\n'
                f'  "[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point({x}, {y});" ^\n'
                f'  "$api = \'[DllImport(\\"user32.dll\\")] public static extern void mouse_event(int flags, int dx, int dy, int data, int extraInfo);\';" ^\n'
                f'  "$sys = Add-Type -MemberDefinition $api -Name \'Win32Mouse\' -Namespace \'Win32\' -PassThru;" ^\n'
                f'  "{click_cmd}"\n'
            )
            
        else: # macro or image
            content = (
                f'@echo off\n'
                f':: ClickPulse Export - Trigger Headless CLI\n'
                f'cd /d "{project_dir}"\n'
                f'if exist "ClickPulse.exe" (\n'
                f'    start "" "ClickPulse.exe" --run-slot P{self.current_page+1}_R{r+1}_C{c+1}\n'
                f') else if exist "dist\\ClickPulse.exe" (\n'
                f'    start "" "dist\\ClickPulse.exe" --run-slot P{self.current_page+1}_R{r+1}_C{c+1}\n'
                f') else (\n'
                f'    start "" ".venv\\Scripts\\pythonw.exe" "main.py" --run-slot P{self.current_page+1}_R{r+1}_C{c+1}\n'
                f')\n'
            )
            
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.log(f"Successfully exported .bat file to: {save_path}", self.accent_green)
        except Exception as e:
            self.log(f"Failed to export .bat file: {str(e)}", "#ff453a")

    def build_inspector_header(self):
        """Creates the shared configuration headers inside property inspector."""
        header = ctk.CTkFrame(self.inspector_panel, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(12, 8))
        
        # Title Entry
        title_lbl = ctk.CTkLabel(header, text="Title:", text_color=self.text_gray, font=("Helvetica", 11))
        title_lbl.pack(side="left", padx=(0, 4))
        self.inspector_title_entry = ctk.CTkEntry(header, width=120, height=26, fg_color="#0a0c10", border_color="#30363d", text_color=self.text_white)
        self.inspector_title_entry.pack(side="left", padx=(0, 15))
        self.inspector_title_entry.bind("<KeyRelease>", lambda event: self.save_current_inspector_data())

        # Type Selector Dropdown
        type_lbl = ctk.CTkLabel(header, text="Type:", text_color=self.text_gray, font=("Helvetica", 11))
        type_lbl.pack(side="left", padx=(0, 4))
        self.inspector_type_combo = ctk.CTkOptionMenu(
            header,
            values=["Empty", "Launch App", "Launch Website", "Mouse Click", "Click at Image", "Macro Sequence"],
            fg_color="#0a0c10", button_color="#1f242e", button_hover_color="#282f3d", text_color=self.text_white,
            dropdown_fg_color="#12161f", font=("Helvetica", 11), width=130, height=26,
            command=self.on_inspector_type_changed
        )
        self.inspector_type_combo.pack(side="left", padx=(0, 15))

        # Hotkey binder
        hk_lbl = ctk.CTkLabel(header, text="Hotkey:", text_color=self.text_gray, font=("Helvetica", 11))
        hk_lbl.pack(side="left", padx=(0, 4))
        self.inspector_hotkey_display = ctk.CTkLabel(header, text="None", text_color=self.accent_purple, font=("Consolas", 12, "bold"))
        self.inspector_hotkey_display.pack(side="left", padx=(0, 8))
        
        self.inspector_rec_btn = ctk.CTkButton(
            header, text="Record", fg_color="#1c212e", hover_color="#2b3240", border_color="#30363d", border_width=1,
            text_color=self.text_white, font=("Helvetica", 11, "bold"), width=70, height=26, corner_radius=6,
            command=self.start_slot_hotkey_recording
        )
        self.inspector_rec_btn.pack(side="left", padx=(0, 10))

        # Loop Config
        self.inspector_loop_switch = ctk.CTkSwitch(
            header, text="Loop", text_color=self.text_gray, font=("Helvetica", 11), progress_color=self.accent_cyan,
            command=self.on_inspector_loop_switch_toggled, width=70
        )
        self.inspector_loop_switch.pack(side="left", padx=(10, 5))

        self.loop_count_lbl = ctk.CTkLabel(header, text="Times:", text_color=self.text_gray, font=("Helvetica", 11))
        self.loop_count_lbl.pack(side="left", padx=(0, 4))
        self.inspector_loop_count_entry = ctk.CTkEntry(header, width=45, height=26, fg_color="#0a0c10", border_color="#30363d", text_color=self.text_white)
        self.inspector_loop_count_entry.pack(side="left", padx=(0, 5))
        self.inspector_loop_count_entry.bind("<KeyRelease>", lambda event: self.save_current_inspector_data())

        # Test trigger button
        self.inspector_test_btn = ctk.CTkButton(
            header, text="Test Key", fg_color="#1f242e", hover_color="#2b3240", border_color=self.accent_purple, border_width=1,
            text_color=self.accent_purple, font=("Helvetica", 11, "bold"), width=75, height=26, corner_radius=6,
            command=self.trigger_selected_slot_async
        )
        self.inspector_test_btn.pack(side="right")

        # Export BAT button
        self.inspector_bat_btn = ctk.CTkButton(
            header, text="Export BAT", fg_color="#1f242e", hover_color="#2b3240", border_color=self.accent_green, border_width=1,
            text_color=self.accent_green, font=("Helvetica", 11, "bold"), width=75, height=26, corner_radius=6,
            command=self.create_bat_file_for_selected_slot
        )
        self.inspector_bat_btn.pack(side="right", padx=(0, 10))

    def build_inspector_param_frames(self):
        """Creates individual configuration frames for each action type."""
        # 1. Empty Frame
        self.param_empty_frame = ctk.CTkFrame(self.inspector_panel, fg_color="transparent")
        self.empty_lbl = ctk.CTkLabel(self.param_empty_frame, text="Select an action type to configure settings.", text_color=self.text_gray, font=("Helvetica", 12))
        self.empty_lbl.pack(expand=True, pady=60)
        
        # 2. App Frame
        self.param_app_frame = ctk.CTkFrame(self.inspector_panel, fg_color="transparent")
        app_row = ctk.CTkFrame(self.param_app_frame, fg_color="transparent")
        app_row.pack(fill="x", padx=15, pady=10)
        
        app_lbl = ctk.CTkLabel(app_row, text="Application Path:", text_color=self.text_gray, font=("Helvetica", 11))
        app_lbl.pack(side="left", padx=(0, 5))
        
        self.app_path_entry = ctk.CTkEntry(app_row, fg_color="#0a0c10", border_color="#30363d", text_color=self.text_white)
        self.app_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.app_path_entry.bind("<KeyRelease>", lambda event: self.save_current_inspector_data())
        
        browse_btn = ctk.CTkButton(
            app_row, text="Browse", fg_color=self.accent_purple, hover_color="#a841e0",
            text_color=self.text_white, font=("Helvetica", 11, "bold"), width=80, height=26,
            command=self.browse_app_path
        )
        browse_btn.pack(side="right")

        # 2C. Website Frame
        self.param_web_frame = ctk.CTkFrame(self.inspector_panel, fg_color="transparent")
        web_row = ctk.CTkFrame(self.param_web_frame, fg_color="transparent")
        web_row.pack(fill="x", padx=15, pady=10)

        web_lbl = ctk.CTkLabel(web_row, text="Website URL:", text_color=self.text_gray, font=("Helvetica", 11))
        web_lbl.pack(side="left", padx=(0, 5))

        self.web_url_entry = ctk.CTkEntry(web_row, fg_color="#0a0c10", border_color="#30363d", text_color=self.text_white)
        self.web_url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.web_url_entry.bind("<KeyRelease>", lambda event: self.save_current_inspector_data())

        launch_web_btn = ctk.CTkButton(
            web_row, text="Launch Test", fg_color=self.accent_pink, hover_color="#e04bb3",
            text_color=self.text_white, font=("Helvetica", 11, "bold"), width=80, height=26,
            command=self.test_launch_website
        )
        launch_web_btn.pack(side="right")

        # 3. Mouse Frame
        self.param_mouse_frame = ctk.CTkFrame(self.inspector_panel, fg_color="transparent")
        
        m_row1 = ctk.CTkFrame(self.param_mouse_frame, fg_color="transparent")
        m_row1.pack(fill="x", padx=15, pady=8)
        
        m_x_lbl = ctk.CTkLabel(m_row1, text="X Coord:", text_color=self.text_gray, font=("Helvetica", 11))
        m_x_lbl.pack(side="left", padx=(0, 4))
        self.mouse_x_entry = ctk.CTkEntry(m_row1, width=70, height=24, fg_color="#0a0c10", border_color="#30363d", text_color=self.text_white)
        self.mouse_x_entry.pack(side="left", padx=(0, 15))
        self.mouse_x_entry.bind("<KeyRelease>", lambda event: self.save_current_inspector_data())
        
        m_y_lbl = ctk.CTkLabel(m_row1, text="Y Coord:", text_color=self.text_gray, font=("Helvetica", 11))
        m_y_lbl.pack(side="left", padx=(0, 4))
        self.mouse_y_entry = ctk.CTkEntry(m_row1, width=70, height=24, fg_color="#0a0c10", border_color="#30363d", text_color=self.text_white)
        self.mouse_y_entry.pack(side="left", padx=(0, 15))
        self.mouse_y_entry.bind("<KeyRelease>", lambda event: self.save_current_inspector_data())

        m_pick_btn = ctk.CTkButton(
            m_row1, text="Pick Position", fg_color=self.accent_purple, hover_color="#a841e0",
            text_color=self.text_white, font=("Helvetica", 11, "bold"), width=100, height=24,
            command=self.start_slot_coordinate_picking
        )
        m_pick_btn.pack(side="left", padx=(0, 20))

        m_type_lbl = ctk.CTkLabel(m_row1, text="Click Type:", text_color=self.text_gray, font=("Helvetica", 11))
        m_type_lbl.pack(side="left", padx=(0, 4))
        self.mouse_click_combo = ctk.CTkOptionMenu(
            m_row1, values=["Left Click", "Double Left Click", "Right Click", "Middle Click", "Only Move"],
            fg_color="#0a0c10", button_color="#1f242e", button_hover_color="#282f3d", text_color=self.text_white,
            dropdown_fg_color="#12161f", font=("Helvetica", 11), width=120, height=24,
            command=lambda val: self.save_current_inspector_data()
        )
        self.mouse_click_combo.pack(side="left")

        m_row2 = ctk.CTkFrame(self.param_mouse_frame, fg_color="transparent")
        m_row2.pack(fill="x", padx=15, pady=8)

        self.mouse_glide_switch = ctk.CTkSwitch(
            m_row2, text="Enable Smooth Glide", text_color=self.text_gray, font=("Helvetica", 11), progress_color=self.accent_cyan,
            command=self.on_mouse_glide_switch_toggled
        )
        self.mouse_glide_switch.pack(side="left", padx=(0, 20))
        
        self.mouse_glide_lbl = ctk.CTkLabel(m_row2, text="Duration: 0.1s", text_color=self.accent_cyan, font=("Consolas", 11, "bold"))
        self.mouse_glide_lbl.pack(side="right", padx=(5, 0))

        self.mouse_glide_slider = ctk.CTkSlider(
            m_row2, from_=0.1, to=2.0, number_of_steps=19, progress_color=self.accent_cyan, button_color=self.accent_cyan,
            command=self.on_mouse_glide_slider_changed
        )
        self.mouse_glide_slider.pack(side="right", fill="x", expand=True, padx=10)

        # 3B. Image Recognition Frame
        self.param_image_frame = ctk.CTkFrame(self.inspector_panel, fg_color="transparent")
        
        img_row1 = ctk.CTkFrame(self.param_image_frame, fg_color="transparent")
        img_row1.pack(fill="x", padx=15, pady=8)
        
        img_lbl = ctk.CTkLabel(img_row1, text="Target Image:", text_color=self.text_gray, font=("Helvetica", 11))
        img_lbl.pack(side="left", padx=(0, 5))
        
        self.image_path_entry = ctk.CTkEntry(img_row1, fg_color="#0a0c10", border_color="#30363d", text_color=self.text_white)
        self.image_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.image_path_entry.bind("<KeyRelease>", lambda event: self.save_current_inspector_data())
        
        img_browse_btn = ctk.CTkButton(
            img_row1, text="Browse", fg_color=self.accent_purple, hover_color="#a841e0",
            text_color=self.text_white, font=("Helvetica", 11, "bold"), width=80, height=26,
            command=self.browse_image_path
        )
        img_browse_btn.pack(side="right", padx=(0, 8))
        
        img_snip_btn = ctk.CTkButton(
            img_row1, text="Snip Image", fg_color="#2c271c", hover_color="#3d3727",
            text_color="#ff9500", font=("Helvetica", 11, "bold"), width=90, height=26,
            command=self.start_slot_image_snipping
        )
        img_snip_btn.pack(side="right")
        
        img_row2 = ctk.CTkFrame(self.param_image_frame, fg_color="transparent")
        img_row2.pack(fill="x", padx=15, pady=8)
        
        img_type_lbl = ctk.CTkLabel(img_row2, text="Click Type:", text_color=self.text_gray, font=("Helvetica", 11))
        img_type_lbl.pack(side="left", padx=(0, 4))
        
        self.image_click_combo = ctk.CTkOptionMenu(
            img_row2, values=["Left Click", "Double Left Click", "Right Click", "Middle Click", "Only Move"],
            fg_color="#0a0c10", button_color="#1f242e", button_hover_color="#282f3d", text_color=self.text_white,
            dropdown_fg_color="#12161f", font=("Helvetica", 11), width=120, height=24,
            command=lambda val: self.save_current_inspector_data()
        )
        self.image_click_combo.pack(side="left", padx=(0, 20))
        
        self.image_confidence_lbl = ctk.CTkLabel(img_row2, text="Confidence: 0.80", text_color="#ff9500", font=("Consolas", 11, "bold"))
        self.image_confidence_lbl.pack(side="left", padx=(0, 8))
        
        self.image_confidence_slider = ctk.CTkSlider(
            img_row2, from_=0.5, to=1.0, number_of_steps=50, progress_color="#ff9500", button_color="#ff9500",
            width=100, command=self.on_image_confidence_slider_changed
        )
        self.image_confidence_slider.pack(side="left", padx=(0, 25))
        
        self.image_glide_switch = ctk.CTkSwitch(
            img_row2, text="Glide", text_color=self.text_gray, font=("Helvetica", 11), progress_color=self.accent_cyan,
            command=self.on_image_glide_switch_toggled
        )
        self.image_glide_switch.pack(side="left", padx=(0, 15))
        
        self.image_glide_lbl = ctk.CTkLabel(img_row2, text="Duration: 0.1s", text_color=self.accent_cyan, font=("Consolas", 11, "bold"))
        self.image_glide_lbl.pack(side="right", padx=(5, 0))
        
        self.image_glide_slider = ctk.CTkSlider(
            img_row2, from_=0.1, to=2.0, number_of_steps=19, progress_color=self.accent_cyan, button_color=self.accent_cyan,
            command=self.on_image_glide_slider_changed
        )
        self.image_glide_slider.pack(side="right", fill="x", expand=True, padx=10)

        # 4. Macro Frame
        self.param_macro_frame = ctk.CTkFrame(self.inspector_panel, fg_color="transparent")
        
        macro_split = ctk.CTkFrame(self.param_macro_frame, fg_color="transparent")
        macro_split.pack(fill="both", expand=True, padx=15, pady=5)
        
        # Macro Timeline Scrollable
        self.macro_timeline_frame = ctk.CTkScrollableFrame(
            macro_split, fg_color="#06080b", border_color="#1f242e", border_width=1, corner_radius=8,
            label_text="Steps Timeline"
        )
        self.macro_timeline_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Macro Timeline Empty Placeholder
        self.macro_placeholder = ctk.CTkLabel(self.macro_timeline_frame, text="Macro timeline is empty. Add steps on the right.", text_color=self.text_gray, font=("Helvetica", 11))
        self.macro_placeholder.pack(pady=40)

        # Macro Timeline Toolbox
        macro_tb = ctk.CTkFrame(macro_split, fg_color="transparent", width=130)
        macro_tb.pack(side="right", fill="y")
        macro_tb.pack_propagate(False)
        
        ctk.CTkButton(macro_tb, text="+ Mouse Click", fg_color="#1a2536", text_color=self.accent_cyan, font=("Helvetica", 10, "bold"), height=24, command=lambda: self.add_sequence_card("mouse")).pack(fill="x", pady=2)
        ctk.CTkButton(macro_tb, text="+ Wait Delay", fg_color="#241e33", text_color=self.accent_purple, font=("Helvetica", 10, "bold"), height=24, command=lambda: self.add_sequence_card("delay")).pack(fill="x", pady=2)
        ctk.CTkButton(macro_tb, text="+ Press Key", fg_color="#182d24", text_color=self.accent_green, font=("Helvetica", 10, "bold"), height=24, command=lambda: self.add_sequence_card("key")).pack(fill="x", pady=2)
        ctk.CTkButton(macro_tb, text="+ Write Text", fg_color="#2c271c", text_color="#ff9500", font=("Helvetica", 10, "bold"), height=24, command=lambda: self.add_sequence_card("text")).pack(fill="x", pady=2)
        ctk.CTkButton(macro_tb, text="+ Launch App", fg_color="#182d24", text_color=self.accent_green, font=("Helvetica", 10, "bold"), height=24, command=lambda: self.add_sequence_card("app")).pack(fill="x", pady=2)
        ctk.CTkButton(macro_tb, text="+ Launch Web", fg_color="#2c1a30", text_color=self.accent_pink, font=("Helvetica", 10, "bold"), height=24, command=lambda: self.add_sequence_card("web")).pack(fill="x", pady=2)
        ctk.CTkButton(macro_tb, text="+ Click Image", fg_color="#2c271c", text_color=self.accent_orange, font=("Helvetica", 10, "bold"), height=24, command=lambda: self.add_sequence_card("image")).pack(fill="x", pady=2)
        ctk.CTkButton(macro_tb, text="● Record Activity", fg_color="#2d1d1f", hover_color="#3d2729", text_color="#ff453a", font=("Helvetica", 10, "bold"), height=24, command=self.record_macro_activity).pack(fill="x", pady=2)
        ctk.CTkButton(macro_tb, text="Clear Steps", fg_color="transparent", border_color="#30363d", border_width=1, text_color=self.text_gray, font=("Helvetica", 10, "bold"), height=24, command=self.clear_inspector_macro_timeline).pack(fill="x", pady=(10, 2))

    # --- Property Inspector Actions ---

    # --- Page Switching Methods ---

    def prev_page(self):
        if self.current_page > 0:
            self.switch_page(self.current_page - 1)

    def next_page(self):
        if self.current_page < 4:
            self.switch_page(self.current_page + 1)

    def switch_page(self, page_idx):
        self.current_page = page_idx
        self.board_slots = self.board_pages[self.current_page]
        self.page_lbl.configure(text=f"PAGE {self.current_page + 1} / 5")
        
        # Deselect old highlight coords and highlight (0, 0)
        self.selected_row = 0
        self.selected_col = 0
        
        self.refresh_grid_buttons()
        self.on_grid_button_clicked(0, 0)
        
    def refresh_grid_buttons(self):
        for r in range(4):
            for c in range(8):
                slot = self.board_slots[r][c]
                border_c = self.get_slot_border_color(slot['type'])
                if r == self.selected_row and c == self.selected_col:
                    border_c = self.accent_cyan
                
                text_val = slot['title'] if slot['title'] else (slot['type'].upper() if slot['type'] != 'empty' else "")
                self.grid_buttons[r][c].configure(text=text_val, border_color=border_c)

    def on_grid_button_clicked(self, r, c):
        old_r, old_c = self.selected_row, self.selected_col
        self.selected_row = r
        self.selected_col = c
        
        # Deselect old button highlights
        if old_r is not None and old_c is not None:
            old_slot = self.board_slots[old_r][old_c]
            old_border = self.get_slot_border_color(old_slot['type'])
            self.grid_buttons[old_r][old_c].configure(border_color=old_border)
            
        # Highlight new button border
        self.grid_buttons[r][c].configure(border_color=self.accent_cyan)
        self.load_slot_to_inspector(r, c)

    def get_slot_border_color(self, slot_type):
        if slot_type == "app":
            return self.accent_green
        elif slot_type == "web":
            return self.accent_pink
        elif slot_type == "mouse":
            return self.accent_cyan
        elif slot_type == "image":
            return self.accent_orange
        elif slot_type == "macro":
            return self.accent_purple
        return "#2b3240"

    def assign_action_to_selected(self, action_type):
        r, c = self.selected_row, self.selected_col
        if r is None or c is None:
            return
            
        slot = self.board_slots[r][c]
        slot['type'] = action_type
        
        if action_type == "empty":
            slot['title'] = ""
            slot['hotkey'] = set()
            
        self.inspector_type_combo.set(self.format_type_name(action_type))
        self.on_inspector_type_changed(self.format_type_name(action_type))
        self.save_current_inspector_data()
        
    def format_type_name(self, action_type):
        if action_type == "app": return "Launch App"
        elif action_type == "web": return "Launch Website"
        elif action_type == "mouse": return "Mouse Click"
        elif action_type == "image": return "Click at Image"
        elif action_type == "macro": return "Macro Sequence"
        return "Empty"

    def parse_type_name(self, combo_name):
        if combo_name == "Launch App": return "app"
        elif combo_name == "Launch Website": return "web"
        elif combo_name == "Mouse Click": return "mouse"
        elif combo_name == "Click at Image": return "image"
        elif combo_name == "Macro Sequence": return "macro"
        return "empty"

    def load_slot_to_inspector(self, r, c):
        slot = self.board_slots[r][c]
        
        # Set Header fields
        self.inspector_title_entry.delete(0, "end")
        self.inspector_title_entry.insert(0, slot['title'])
        self.inspector_type_combo.set(self.format_type_name(slot['type']))
        
        hk_combo = " + ".join(sorted(list(slot['hotkey']))) if slot['hotkey'] else "None"
        self.inspector_hotkey_display.configure(text=hk_combo)

        # Load loop settings
        loop_enabled = slot.get('loop_enabled', False)
        loop_count = slot.get('loop_count', 0)
        
        if loop_enabled:
            self.inspector_loop_switch.select()
            self.inspector_loop_count_entry.configure(state="normal")
        else:
            self.inspector_loop_switch.deselect()
            self.inspector_loop_count_entry.configure(state="disabled")
            
        self.inspector_loop_count_entry.delete(0, "end")
        self.inspector_loop_count_entry.insert(0, str(loop_count))

        # Hide all inspector sub-frames
        self.param_empty_frame.pack_forget()
        self.param_app_frame.pack_forget()
        self.param_web_frame.pack_forget()
        self.param_mouse_frame.pack_forget()
        self.param_image_frame.pack_forget()
        self.param_macro_frame.pack_forget()

        # Load values into matching parameters sub-frame
        slot_type = slot['type']
        if slot_type == "empty":
            self.param_empty_frame.pack(fill="both", expand=True)
            
        elif slot_type == "app":
            self.app_path_entry.delete(0, "end")
            self.app_path_entry.insert(0, slot.get('app_path', ''))
            self.param_app_frame.pack(fill="both", expand=True)
            
        elif slot_type == "web":
            self.web_url_entry.delete(0, "end")
            self.web_url_entry.insert(0, slot.get('web_url', ''))
            self.param_web_frame.pack(fill="both", expand=True)
            
        elif slot_type == "mouse":
            self.mouse_x_entry.delete(0, "end")
            self.mouse_x_entry.insert(0, str(slot.get('mouse_x', 1000)))
            
            self.mouse_y_entry.delete(0, "end")
            self.mouse_y_entry.insert(0, str(slot.get('mouse_y', 850)))
            
            self.mouse_click_combo.set(slot.get('click_type', 'Left Click'))
            
            glide_enabled = slot.get('glide_enabled', True)
            if glide_enabled:
                self.mouse_glide_switch.select()
                self.mouse_glide_slider.configure(state="normal")
            else:
                self.mouse_glide_switch.deselect()
                self.mouse_glide_slider.configure(state="disabled")
                
            glide_dur = slot.get('glide_duration', 0.1)
            self.mouse_glide_slider.set(glide_dur)
            self.mouse_glide_lbl.configure(text=f"Duration: {glide_dur:.1f}s")
            self.param_mouse_frame.pack(fill="both", expand=True)
            
        elif slot_type == "image":
            self.image_path_entry.delete(0, "end")
            self.image_path_entry.insert(0, slot.get('image_path', ''))
            
            self.image_click_combo.set(slot.get('click_type', 'Left Click'))
            
            conf_val = slot.get('confidence', 0.8)
            self.image_confidence_slider.set(conf_val)
            self.image_confidence_lbl.configure(text=f"Confidence: {conf_val:.2f}")
            
            glide_enabled = slot.get('glide_enabled', True)
            if glide_enabled:
                self.image_glide_switch.select()
                self.image_glide_slider.configure(state="normal")
            else:
                self.image_glide_switch.deselect()
                self.image_glide_slider.configure(state="disabled")
                
            glide_dur = slot.get('glide_duration', 0.1)
            self.image_glide_slider.set(glide_dur)
            self.image_glide_lbl.configure(text=f"Duration: {glide_dur:.1f}s")
            self.param_image_frame.pack(fill="both", expand=True)
            
        elif slot_type == "macro":
            # Recreate timeline card widgets from steps dictionary data
            self.clear_timeline_widgets_only()
            steps = slot.get('steps', [])
            for step in steps:
                self.add_sequence_card(step['type'], step)
            self.param_macro_frame.pack(fill="both", expand=True)

    def on_inspector_type_changed(self, val):
        r, c = self.selected_row, self.selected_col
        if r is None or c is None:
            return
            
        slot_type = self.parse_type_name(val)
        self.board_slots[r][c]['type'] = slot_type
        
        # Dynamically switch inspector panels
        self.load_slot_to_inspector(r, c)
        self.save_current_inspector_data()

    def on_inspector_loop_switch_toggled(self):
        if self.inspector_loop_switch.get() == 1:
            self.inspector_loop_count_entry.configure(state="normal")
        else:
            self.inspector_loop_count_entry.configure(state="disabled")
        self.save_current_inspector_data()

    def save_current_inspector_data(self):
        r, c = self.selected_row, self.selected_col
        if r is None or c is None:
            return
            
        slot = self.board_slots[r][c]
        
        # Header properties
        slot['title'] = self.inspector_title_entry.get().strip()
        slot['type'] = self.parse_type_name(self.inspector_type_combo.get())
        slot['loop_enabled'] = self.inspector_loop_switch.get() == 1
        try:
            slot['loop_count'] = int(self.inspector_loop_count_entry.get().strip())
        except ValueError:
            slot['loop_count'] = 0
        
        # Grid button label updates
        grid_text = slot['title'] if slot['title'] else (slot['type'].upper() if slot['type'] != 'empty' else "")
        self.grid_buttons[r][c].configure(text=grid_text)
        self.grid_buttons[r][c].configure(border_color=self.get_slot_border_color(slot['type']) if (r != self.selected_row or c != self.selected_col) else self.accent_cyan)

        # Config properties
        if slot['type'] == 'app':
            slot['app_path'] = self.app_path_entry.get().strip()
            
        elif slot['type'] == 'web':
            slot['web_url'] = self.web_url_entry.get().strip()
            
        elif slot['type'] == 'mouse':
            try:
                slot['mouse_x'] = int(self.mouse_x_entry.get().strip())
                slot['mouse_y'] = int(self.mouse_y_entry.get().strip())
            except ValueError:
                pass
            slot['click_type'] = self.mouse_click_combo.get()
            slot['glide_enabled'] = self.mouse_glide_switch.get() == 1
            slot['glide_duration'] = self.mouse_glide_slider.get()
            
        elif slot['type'] == 'image':
            slot['image_path'] = self.image_path_entry.get().strip()
            slot['confidence'] = self.image_confidence_slider.get()
            slot['click_type'] = self.image_click_combo.get()
            slot['glide_enabled'] = self.image_glide_switch.get() == 1
            slot['glide_duration'] = self.image_glide_slider.get()
            
        elif slot['type'] == 'macro':
            # Compile current scrollable widgets configuration into slot data steps
            steps_data = []
            for action in self.sequence_actions:
                atype = action['type']
                step = {'type': atype}
                
                if atype == 'mouse':
                    try:
                        step['x'] = int(action['x_entry'].get().strip())
                        step['y'] = int(action['y_entry'].get().strip())
                    except ValueError:
                        step['x'], step['y'] = 1000, 850
                    step['click_type'] = action['click_type_combo'].get()
                    step['glide_enabled'] = action['glide_switch'].get() == 1
                    step['glide_duration'] = action['glide_slider'].get()
                    
                elif atype == 'delay':
                    try:
                        step['value'] = float(action['delay_entry'].get().strip())
                    except ValueError:
                        step['value'] = 500.0
                    step['unit'] = action['unit_combo'].get()
                    
                elif atype == 'key':
                    step['key'] = action['key_entry'].get().strip()
                    
                elif atype == 'text':
                    step['text'] = action['text_entry'].get()
                elif atype == 'app':
                    step['app_path'] = action['app_entry'].get().strip()
                elif atype == 'web':
                    step['web_url'] = action['web_entry'].get().strip()
                elif atype == 'image':
                    step['image_path'] = action['image_entry'].get().strip()
                    step['confidence'] = action['confidence_slider'].get()
                    step['click_type'] = action['click_type_combo'].get()
                    step['glide_enabled'] = action['glide_switch'].get() == 1
                    step['glide_duration'] = action['glide_slider'].get()
                    
                elif atype == 'recorded':
                    step['events'] = action.get('events', [])
                    step['skip_mouse_move'] = action.get('skip_var', ctk.StringVar(value='off')).get() == 'on'
                    
                steps_data.append(step)
            slot['steps'] = steps_data

        # Save to local disk
        self.save_board_data()

    # --- Property Inspector Callback Triggers ---

    def test_launch_website(self):
        url = self.web_url_entry.get().strip()
        if url:
            try:
                import webbrowser
                webbrowser.open(url)
                self.log(f"Launching website: {url}", self.accent_green)
            except Exception as e:
                self.log(f"Failed to launch website: {str(e)}", "#ff453a")
        else:
            self.log("Website URL is blank.", "#ff9500")

    def browse_app_path(self):
        path = filedialog.askopenfilename(
            filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")],
            title="Select Application to Open"
        )
        if path:
            self.app_path_entry.delete(0, "end")
            self.app_path_entry.insert(0, path)
            self.save_current_inspector_data()

    def browse_image_path(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp"), ("All Files", "*.*")],
            title="Select Target Image"
        )
        if path:
            proj_dir = os.path.dirname(self.board_file)
            try:
                rel = os.path.relpath(path, proj_dir)
                if not rel.startswith(".."):
                    path = rel
            except ValueError:
                pass
            
            self.image_path_entry.delete(0, "end")
            self.image_path_entry.insert(0, path)
            self.save_current_inspector_data()

    def start_slot_image_snipping(self):
        r, c = self.selected_row, self.selected_col
        if r is None or c is None:
            return
        self.log(f"Entering Screen Snipper for Grid Slot ({r+1}, {c+1}).", self.accent_purple)
        ScreenSnipper(self, self.on_slot_image_snipped)

    def on_slot_image_snipped(self, cropped_image):
        if cropped_image is None:
            self.log("Snipping cancelled.", "#ff453a")
            return
            
        r, c = self.selected_row, self.selected_col
        if r is None or c is None:
            return
            
        templates_dir = os.path.join(os.path.dirname(self.board_file), "templates")
        os.makedirs(templates_dir, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"snip_{r+1}_{c+1}_{timestamp}.png"
        full_path = os.path.join(templates_dir, filename)
        
        try:
            cropped_image.save(full_path, "PNG")
            rel_path = os.path.join("templates", filename)
            
            self.image_path_entry.delete(0, "end")
            self.image_path_entry.insert(0, rel_path)
            self.save_current_inspector_data()
            self.log(f"Image captured and saved to: {rel_path}", self.accent_green)
        except Exception as e:
            self.log(f"Failed to save snipped image: {str(e)}", "#ff453a")

    def on_image_glide_switch_toggled(self):
        if self.image_glide_switch.get():
            self.image_glide_slider.configure(state="normal")
        else:
            self.image_glide_slider.configure(state="disabled")
        self.save_current_inspector_data()

    def on_image_glide_slider_changed(self, val):
        self.image_glide_lbl.configure(text=f"Duration: {val:.1f}s")
        self.save_current_inspector_data()

    def on_image_confidence_slider_changed(self, val):
        self.image_confidence_lbl.configure(text=f"Confidence: {val:.2f}")
        self.save_current_inspector_data()

    def on_mouse_glide_switch_toggled(self):
        if self.mouse_glide_switch.get():
            self.mouse_glide_slider.configure(state="normal")
        else:
            self.mouse_glide_slider.configure(state="disabled")
        self.save_current_inspector_data()

    def on_mouse_glide_slider_changed(self, val):
        self.mouse_glide_lbl.configure(text=f"Duration: {val:.1f}s")
        self.save_current_inspector_data()

    # --- Hotkey Recording for Slots ---

    def start_slot_hotkey_recording(self):
        if self.is_recording_slot:
            return
            
        r, c = self.selected_row, self.selected_col
        if r is None or c is None:
            return
            
        self.is_recording_slot = True
        self.recorded_keys_temp.clear()
        self.pressed_keys_global.clear()
        
        self.inspector_rec_btn.configure(text="Press...", fg_color="#ff453a", hover_color="#e03b31")
        self.inspector_hotkey_display.configure(text="Waiting...", text_color="#ff453a")
        self.log(f"Recording global hotkey for Grid Slot ({r+1}, {c+1}). Press combo and release all keys.", self.accent_purple)

    def start_slot_coordinate_picking(self):
        r, c = self.selected_row, self.selected_col
        self.log(f"Entering Coordinate Pick Mode for Grid Slot ({r+1}, {c+1}).", self.accent_purple)
        CoordinatePicker(self, self.on_slot_coordinate_picked)

    def on_slot_coordinate_picked(self, x, y):
        if x is not None and y is not None:
            self.mouse_x_entry.delete(0, "end")
            self.mouse_x_entry.insert(0, str(x))
            self.mouse_y_entry.delete(0, "end")
            self.mouse_y_entry.insert(0, str(y))
            self.save_current_inspector_data()
            self.log(f"Captured coordinate (X: {x}, Y: {y}) successfully.", self.accent_green)
        else:
            self.log("Coordinate picking cancelled.", "#ff453a")

    # --- Inline Macro Timeline Card Managers ---

    def serialize_key(self, key):
        if isinstance(key, pynput_keyboard.Key):
            return f"special:{key.name}"
        elif hasattr(key, 'char') and key.char is not None:
            return f"char:{key.char}"
        elif hasattr(key, 'vk') and key.vk is not None:
            return f"vk:{key.vk}"
        else:
            return f"str:{str(key)}"

    def deserialize_key(self, key_str):
        if not key_str or not isinstance(key_str, str):
            return None
        if key_str.startswith("special:"):
            name = key_str.split(":", 1)[1]
            if hasattr(pynput_keyboard.Key, name):
                return getattr(pynput_keyboard.Key, name)
        elif key_str.startswith("char:"):
            char = key_str.split(":", 1)[1]
            return pynput_keyboard.KeyCode.from_char(char)
        elif key_str.startswith("vk:"):
            try:
                vk = int(key_str.split(":", 1)[1])
                return pynput_keyboard.KeyCode(vk=vk)
            except ValueError:
                pass
        elif key_str.startswith("str:"):
            val = key_str.split(":", 1)[1]
            if val.startswith("Key."):
                name = val.split(".", 1)[1]
                if hasattr(pynput_keyboard.Key, name):
                    return getattr(pynput_keyboard.Key, name)
            return pynput_keyboard.KeyCode.from_char(val)
        return None

    def record_macro_activity(self):
        # Stop global keyboard hotkey listener to prevent hook conflicts/crashes
        if hasattr(self, 'keyboard_listener') and self.keyboard_listener:
            try:
                self.keyboard_listener.stop()
            except:
                pass
            self.keyboard_listener = None
            self.log("Suspended global hotkey listener for recording safety.", self.accent_purple)

        # Create overlay window
        overlay = tk.Toplevel(self)
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True)
        
        # Center at top of screen
        screen_width = self.winfo_screenwidth()
        x_pos = (screen_width - 340) // 2
        overlay.geometry(f"340x35+{x_pos}+5")
        
        overlay.configure(bg="#0c0e12")
        frame = tk.Frame(overlay, bg="#ffd60a", bd=1)  # Yellow border initially
        frame.pack(fill="both", expand=True)
        
        lbl = tk.Label(frame, text="Preparing to record...", fg="#ffd60a", bg="#0c0e12", font=("Helvetica", 11, "bold"))
        lbl.pack(fill="both", expand=True)
        
        def start_listening():
            # 3 Seconds countdown
            for i in range(3, 0, -1):
                self.after(0, lambda val=i: lbl.configure(text=f"Recording starts in {val}..."))
                time.sleep(1.0)
            
            # Hide main app window
            self.after(0, self.withdraw)
            
            # Change overlay style to active recording (Red)
            self.after(0, lambda: [
                frame.configure(bg="#ff453a"),
                lbl.configure(text="🔴 Recording... Press [ESC] to Stop & Save", fg="#ff453a")
            ])
            
            self.recorded_events = []
            self.currently_pressed_keys = set()
            self.last_move_time = time.time()
            self.is_recording_macro = True
            
            def on_move(x, y):
                now = time.time()
                # Sample at ~30Hz
                if now - self.last_move_time >= 0.033:
                    self.recorded_events.append({
                        'time': now,
                        'type': 'mouse_move',
                        'x': x,
                        'y': y
                    })
                    self.last_move_time = now
                    
            def on_click(x, y, button, pressed):
                self.recorded_events.append({
                    'time': time.time(),
                    'type': 'mouse_down' if pressed else 'mouse_up',
                    'x': x,
                    'y': y,
                    'button': button.name
                })
                
            def on_press(key):
                if key == pynput_keyboard.Key.esc:
                    self.is_recording_macro = False
                    return False  # stops keyboard listener
                if key not in self.currently_pressed_keys:
                    self.currently_pressed_keys.add(key)
                    self.recorded_events.append({
                        'time': time.time(),
                        'type': 'key_down',
                        'key': self.serialize_key(key)
                    })
                    
            def on_release(key):
                if key == pynput_keyboard.Key.esc:
                    return
                if key in self.currently_pressed_keys:
                    self.currently_pressed_keys.remove(key)
                    self.recorded_events.append({
                        'time': time.time(),
                        'type': 'key_up',
                        'key': self.serialize_key(key)
                    })
            
            self.macro_mouse_listener = pynput_mouse.Listener(on_move=on_move, on_click=on_click)
            self.macro_keyboard_listener = pynput_keyboard.Listener(on_press=on_press, on_release=on_release)
            
            self.macro_mouse_listener.start()
            self.macro_keyboard_listener.start()
            
            # Block background thread until keyboard listener stops
            self.macro_keyboard_listener.join()
            
            # Stop mouse listener
            self.macro_mouse_listener.stop()
            
            # Destroy overlay and restore window on main thread
            self.after(0, overlay.destroy)
            self.after(0, self.deiconify)
            
            # Restart global keyboard hotkey listener
            self.after(0, self.restart_global_hotkey_listener)
            
            # Remove trailing ESC key press from events
            while self.recorded_events and self.recorded_events[-1].get('type') in ('key_down', 'key_up') and self.recorded_events[-1].get('key') == "special:esc":
                self.recorded_events.pop()
                
            if self.recorded_events:
                self.after(0, lambda: self.add_sequence_card("recorded", {'events': self.recorded_events}, save=True))
                self.after(0, lambda: self.log(f"Recording completed! Added Recorded Session card ({len(self.recorded_events)} events).", self.accent_green))
            else:
                self.after(0, lambda: self.log("Recording cancelled: No events captured.", "#ff9500"))

        threading.Thread(target=start_listening, daemon=True).start()

    def restart_global_hotkey_listener(self):
        if hasattr(self, 'keyboard_listener') and self.keyboard_listener:
            try:
                self.keyboard_listener.stop()
            except:
                pass
        self.keyboard_listener = pynput_keyboard.Listener(
            on_press=self.global_on_press,
            on_release=self.global_on_release
        )
        self.keyboard_listener.start()
        self.log("Restored global hotkey listener.", self.accent_green)

    def clear_inspector_macro_timeline(self):
        self.clear_timeline_widgets_only()
        self.save_current_inspector_data()
        self.log("Macro sequence timeline cleared.")

    def clear_timeline_widgets_only(self):
        for action in self.sequence_actions:
            action['widget'].destroy()
        self.sequence_actions.clear()
        if self.macro_placeholder:
            self.macro_placeholder.pack(pady=40)

    def add_sequence_card(self, action_type, step_data=None, save=False):
        """Creates and appends a card widget into the inspector's macro timeline scrollable panel."""
        if self.macro_placeholder:
            self.macro_placeholder.pack_forget()
            
        card = ctk.CTkFrame(self.macro_timeline_frame, fg_color="#181c24", corner_radius=8, border_color="#2b3240", border_width=1)
        
        # Header Row
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=(4, 2))
        
        index_lbl = ctk.CTkLabel(header, text="#0", font=("Helvetica", 10, "bold"), text_color=self.text_gray)
        index_lbl.pack(side="left", padx=(0, 6))
        
        title_colors = {"mouse": self.accent_cyan, "delay": self.accent_purple, "key": self.accent_green, "text": "#ff9500", "app": self.accent_green, "image": self.accent_orange, "web": self.accent_pink, "recorded": self.accent_gold}
        title_text = {"mouse": "MOUSE", "delay": "DELAY", "key": "KEYPRESS", "text": "TEXT", "app": "LAUNCH APP", "image": "CLICK IMAGE", "web": "LAUNCH WEB", "recorded": "RECORDED SESSION"}
        
        type_lbl = ctk.CTkLabel(header, text=title_text[action_type], font=("Helvetica", 10, "bold"), text_color=title_colors[action_type])
        type_lbl.pack(side="left")

        # Reorder / Delete controllers
        ctrls = ctk.CTkFrame(header, fg_color="transparent")
        ctrls.pack(side="right")
        
        up_btn = ctk.CTkButton(ctrls, text="▲", width=18, height=18, fg_color="#0a0c10", hover_color="#2b3240", font=("Arial", 8), corner_radius=3)
        up_btn.pack(side="left", padx=1)
        
        down_btn = ctk.CTkButton(ctrls, text="▼", width=18, height=18, fg_color="#0a0c10", hover_color="#2b3240", font=("Arial", 8), corner_radius=3)
        down_btn.pack(side="left", padx=1)
        
        del_btn = ctk.CTkButton(ctrls, text="X", width=18, height=18, fg_color="#ff453a", hover_color="#e03b31", font=("Arial", 8, "bold"), corner_radius=3)
        del_btn.pack(side="left", padx=(4, 0))

        # Config Parameter row
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=8, pady=(1, 6))
        
        action_data = {
            'type': action_type, 'widget': card, 'index_lbl': index_lbl, 'up_btn': up_btn, 'down_btn': down_btn, 'del_btn': del_btn
        }

        if action_type == "mouse":
            # Compact inputs on one row
            x_val = str(step_data.get('x', 1000)) if step_data else "1000"
            y_val = str(step_data.get('y', 850)) if step_data else "850"
            
            x_lbl = ctk.CTkLabel(body, text="X:", text_color=self.text_gray, font=("Helvetica", 10))
            x_lbl.pack(side="left", padx=(0, 1))
            x_entry = ctk.CTkEntry(body, width=44, height=20, fg_color="#0a0c10", border_color="#30363d", text_color=self.text_white, font=("Helvetica", 10))
            x_entry.insert(0, x_val)
            x_entry.pack(side="left", padx=(0, 4))
            x_entry.bind("<KeyRelease>", lambda event: self.save_current_inspector_data())
            
            y_lbl = ctk.CTkLabel(body, text="Y:", text_color=self.text_gray, font=("Helvetica", 10))
            y_lbl.pack(side="left", padx=(0, 1))
            y_entry = ctk.CTkEntry(body, width=44, height=20, fg_color="#0a0c10", border_color="#30363d", text_color=self.text_white, font=("Helvetica", 10))
            y_entry.insert(0, y_val)
            y_entry.pack(side="left", padx=(0, 4))
            y_entry.bind("<KeyRelease>", lambda event: self.save_current_inspector_data())
            
            pick_btn = ctk.CTkButton(body, text="Pick", width=34, height=20, fg_color=self.accent_purple, hover_color="#a841e0", font=("Helvetica", 10, "bold"), corner_radius=3)
            pick_btn.pack(side="left", padx=(0, 6))
            
            click_type_combo = ctk.CTkOptionMenu(
                body, values=["Left Click", "Double Left Click", "Right Click", "Middle Click", "Only Move"],
                fg_color="#0a0c10", button_color="#1c212e", button_hover_color="#2b3240", text_color=self.text_white,
                dropdown_fg_color="#12161f", font=("Helvetica", 10), width=90, height=20,
                command=lambda val: self.save_current_inspector_data()
            )
            click_type_combo.set(step_data.get('click_type', 'Left Click') if step_data else "Left Click")
            click_type_combo.pack(side="left", padx=(0, 6))
            
            glide_switch = ctk.CTkSwitch(body, text="Glide", text_color=self.text_gray, font=("Helvetica", 9), progress_color=self.accent_cyan, height=16, command=self.save_current_inspector_data)
            glide_switch.pack(side="left", padx=(0, 4))
            if step_data is None or step_data.get('glide_enabled', True):
                glide_switch.select()
            else:
                glide_switch.deselect()
                
            glide_slider = ctk.CTkSlider(body, from_=0.1, to=2.0, number_of_steps=19, progress_color=self.accent_cyan, button_color=self.accent_cyan, width=50, height=10, command=lambda val: self.save_current_inspector_data())
            glide_slider.set(step_data.get('glide_duration', 0.1) if step_data else 0.1)
            glide_slider.pack(side="left")

            action_data.update({
                'x_entry': x_entry, 'y_entry': y_entry, 'pick_btn': pick_btn, 'click_type_combo': click_type_combo,
                'glide_switch': glide_switch, 'glide_slider': glide_slider
            })
            
        elif action_type == "delay":
            delay_val = str(step_data.get('value', 500)) if step_data else "500"
            
            delay_lbl = ctk.CTkLabel(body, text="Delay:", text_color=self.text_gray, font=("Helvetica", 10))
            delay_lbl.pack(side="left", padx=(0, 4))
            
            delay_entry = ctk.CTkEntry(body, width=60, height=20, fg_color="#0a0c10", border_color="#30363d", text_color=self.text_white, font=("Helvetica", 10))
            delay_entry.insert(0, delay_val)
            delay_entry.pack(side="left", padx=(0, 6))
            delay_entry.bind("<KeyRelease>", lambda event: self.save_current_inspector_data())
            
            unit_combo = ctk.CTkOptionMenu(
                body, values=["ms", "seconds"], fg_color="#0a0c10", button_color="#1c212e", button_hover_color="#2b3240",
                text_color=self.text_white, dropdown_fg_color="#12161f", font=("Helvetica", 10), width=70, height=20,
                command=lambda val: self.save_current_inspector_data()
            )
            unit_combo.set(step_data.get('unit', 'ms') if step_data else "ms")
            unit_combo.pack(side="left")
            
            action_data.update({
                'delay_entry': delay_entry, 'unit_combo': unit_combo
            })
            
        elif action_type == "key":
            key_val = step_data.get('key', 'F') if step_data else "F"
            
            key_lbl = ctk.CTkLabel(body, text="Key:", text_color=self.text_gray, font=("Helvetica", 10))
            key_lbl.pack(side="left", padx=(0, 4))
            
            key_entry = ctk.CTkEntry(body, width=80, height=20, fg_color="#0a0c10", border_color="#30363d", text_color=self.text_white, font=("Helvetica", 10))
            key_entry.insert(0, key_val)
            key_entry.pack(side="left", padx=(0, 10))
            key_entry.bind("<KeyRelease>", lambda event: self.save_current_inspector_data())
            
            rec_btn = ctk.CTkButton(body, text="Record", width=60, height=20, fg_color="#0a0c10", hover_color="#2b3240", border_color="#30363d", border_width=1, text_color=self.text_white, font=("Helvetica", 10, "bold"), corner_radius=4)
            rec_btn.pack(side="left")
            
            action_data.update({
                'key_entry': key_entry, 'rec_btn': rec_btn
            })
            
        elif action_type == "text":
            text_val = step_data.get('text', 'Hello ClickPulse') if step_data else "Hello ClickPulse"
            
            text_lbl = ctk.CTkLabel(body, text="Type:", text_color=self.text_gray, font=("Helvetica", 10))
            text_lbl.pack(side="left", padx=(0, 4))
            
            text_entry = ctk.CTkEntry(body, height=20, fg_color="#0a0c10", border_color="#30363d", text_color=self.text_white, font=("Helvetica", 10))
            text_entry.insert(0, text_val)
            text_entry.pack(side="left", fill="x", expand=True)
            text_entry.bind("<KeyRelease>", lambda event: self.save_current_inspector_data())
            
            action_data.update({
                'text_entry': text_entry
            })
            
        elif action_type == "app":
            app_val = step_data.get('app_path', '') if step_data else ""
            
            app_lbl = ctk.CTkLabel(body, text="Path:", text_color=self.text_gray, font=("Helvetica", 10))
            app_lbl.pack(side="left", padx=(0, 4))
            
            app_entry = ctk.CTkEntry(body, height=20, fg_color="#0a0c10", border_color="#30363d", text_color=self.text_white, font=("Helvetica", 10))
            app_entry.insert(0, app_val)
            app_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
            app_entry.bind("<KeyRelease>", lambda event: self.save_current_inspector_data())
            
            browse_btn = ctk.CTkButton(body, text="Browse", width=50, height=20, fg_color=self.accent_purple, hover_color="#a841e0", font=("Helvetica", 10, "bold"), corner_radius=3)
            browse_btn.pack(side="right")
            
            action_data.update({
                'app_entry': app_entry, 'browse_btn': browse_btn
            })

        elif action_type == "web":
            web_val = step_data.get('web_url', '') if step_data else ""
            
            web_lbl = ctk.CTkLabel(body, text="URL:", text_color=self.text_gray, font=("Helvetica", 10))
            web_lbl.pack(side="left", padx=(0, 4))
            
            web_entry = ctk.CTkEntry(body, height=20, fg_color="#0a0c10", border_color="#30363d", text_color=self.text_white, font=("Helvetica", 10))
            web_entry.insert(0, web_val)
            web_entry.pack(side="left", fill="x", expand=True)
            web_entry.bind("<KeyRelease>", lambda event: self.save_current_inspector_data())
            
            action_data.update({
                'web_entry': web_entry
            })

        elif action_type == "image":
            image_val = step_data.get('image_path', '') if step_data else ""
            conf_val = step_data.get('confidence', 0.8) if step_data else 0.8
            click_type_val = step_data.get('click_type', 'Left Click') if step_data else "Left Click"
            glide_enabled = step_data.get('glide_enabled', True) if step_data else True
            glide_duration = step_data.get('glide_duration', 0.1) if step_data else 0.1
            
            row1 = ctk.CTkFrame(body, fg_color="transparent")
            row1.pack(fill="x", pady=(0, 2))
            
            img_lbl = ctk.CTkLabel(row1, text="Img:", text_color=self.text_gray, font=("Helvetica", 10))
            img_lbl.pack(side="left", padx=(0, 4))
            
            image_entry = ctk.CTkEntry(row1, height=20, fg_color="#0a0c10", border_color="#30363d", text_color=self.text_white, font=("Helvetica", 10))
            image_entry.insert(0, image_val)
            image_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
            image_entry.bind("<KeyRelease>", lambda event: self.save_current_inspector_data())
            
            browse_btn = ctk.CTkButton(row1, text="Browse", width=44, height=20, fg_color="#1a2536", hover_color="#24344d", text_color=self.accent_cyan, font=("Helvetica", 9, "bold"), corner_radius=3)
            browse_btn.pack(side="left", padx=(0, 2))
            
            snip_btn = ctk.CTkButton(row1, text="Snip", width=36, height=20, fg_color="#2c271c", hover_color="#3d3727", text_color="#ff9500", font=("Helvetica", 9, "bold"), corner_radius=3)
            snip_btn.pack(side="left")
            
            row2 = ctk.CTkFrame(body, fg_color="transparent")
            row2.pack(fill="x", pady=(2, 0))
            
            click_type_combo = ctk.CTkOptionMenu(
                row2, values=["Left Click", "Double Left Click", "Right Click", "Middle Click", "Only Move"],
                fg_color="#0a0c10", button_color="#1c212e", button_hover_color="#2b3240", text_color=self.text_white,
                dropdown_fg_color="#12161f", font=("Helvetica", 10), width=90, height=20,
                command=lambda val: self.save_current_inspector_data()
            )
            click_type_combo.set(click_type_val)
            click_type_combo.pack(side="left", padx=(0, 6))
            
            conf_lbl = ctk.CTkLabel(row2, text=f"Conf: {conf_val:.2f}", text_color=self.text_gray, font=("Helvetica", 9))
            conf_lbl.pack(side="left", padx=(0, 2))
            
            confidence_slider = ctk.CTkSlider(row2, from_=0.5, to=1.0, number_of_steps=50, progress_color="#ff9500", button_color="#ff9500", width=45, height=10)
            confidence_slider.set(conf_val)
            confidence_slider.pack(side="left", padx=(0, 6))
            confidence_slider.configure(command=lambda val, lbl=conf_lbl: [lbl.configure(text=f"Conf: {val:.2f}"), self.save_current_inspector_data()])
            
            glide_switch = ctk.CTkSwitch(row2, text="Glide", text_color=self.text_gray, font=("Helvetica", 9), progress_color=self.accent_cyan, height=16, command=self.save_current_inspector_data)
            glide_switch.pack(side="left", padx=(0, 2))
            if glide_enabled:
                glide_switch.select()
            else:
                glide_switch.deselect()
                
            glide_slider = ctk.CTkSlider(row2, from_=0.1, to=2.0, number_of_steps=19, progress_color=self.accent_cyan, button_color=self.accent_cyan, width=40, height=10, command=lambda val: self.save_current_inspector_data())
            glide_slider.set(glide_duration)
            glide_slider.pack(side="left")

            action_data.update({
                'image_entry': image_entry, 'browse_btn': browse_btn, 'snip_btn': snip_btn,
                'click_type_combo': click_type_combo, 'confidence_slider': confidence_slider,
                'glide_switch': glide_switch, 'glide_slider': glide_slider, 'conf_lbl': conf_lbl
            })

        elif action_type == "recorded":
            events = step_data.get('events', []) if step_data else []
            events_count = len(events)
            skip_mouse_move_val = step_data.get('skip_mouse_move', False) if step_data else False
            
            # Calculate duration
            if events:
                duration = events[-1]['time'] - events[0]['time']
            else:
                duration = 0.0
                
            # Row 1: Stats
            lbl_text = f"Recorded: {events_count} events, Duration: {duration:.2f}s"
            info_lbl = ctk.CTkLabel(body, text=lbl_text, text_color=self.accent_gold, font=("Helvetica", 11, "bold"))
            info_lbl.pack(side="left", padx=(0, 10))

            # Row 2: WARP option (separate row below)
            warp_row = ctk.CTkFrame(card, fg_color="#10131a", corner_radius=6)
            warp_row.pack(fill="x", padx=8, pady=(0, 6))

            warp_divider = ctk.CTkLabel(warp_row, text="MOUSE OPTIONS", font=("Helvetica", 9, "bold"), text_color="#4a5568")
            warp_divider.pack(anchor="center", pady=(4, 2))

            warp_inner = ctk.CTkFrame(warp_row, fg_color="transparent")
            warp_inner.pack(fill="x", padx=8, pady=(0, 4))

            warp_badge = ctk.CTkLabel(warp_inner, text="«WARP» Motion", font=("Helvetica", 10, "bold"), text_color="#7c3aed")
            warp_badge.pack(side="left", padx=(0, 8))

            skip_var = ctk.StringVar(value="on" if skip_mouse_move_val else "off")
            skip_cb = ctk.CTkCheckBox(
                warp_inner, text="🚀 Skip Mouse Movement",
                variable=skip_var, onvalue="on", offvalue="off",
                font=("Helvetica", 10, "bold"), text_color="#a78bfa",
                checkmark_color="#7c3aed", fg_color="#7c3aed", hover_color="#5b21b6",
                command=self.save_current_inspector_data
            )
            skip_cb.pack(side="left")

            warp_hint = ctk.CTkLabel(warp_row, text="Only Start and Stop Mouse-Position within a Section are executed (Affects the Process Time)",
                                     font=("Helvetica", 9), text_color="#4a5568", wraplength=320, justify="left")
            warp_hint.pack(anchor="w", padx=8, pady=(0, 4))

            action_data.update({
                'info_lbl': info_lbl,
                'events': events,
                'skip_var': skip_var,
                'skip_cb': skip_cb
            })

        self.sequence_actions.append(action_data)
        self.repack_inspector_timeline()
        if step_data is None or save:
            self.save_current_inspector_data()
            if step_data is None:
                self.log(f"Added sequence {action_type.upper()} card.")

    def repack_inspector_timeline(self):
        """Sorts and repacks all timeline widgets inside property inspector scrollable panel."""
        for action in self.sequence_actions:
            action['widget'].pack_forget()
            
        if self.macro_placeholder:
            self.macro_placeholder.pack_forget()
            
        if len(self.sequence_actions) == 0:
            self.macro_placeholder.pack(pady=40)
            return
            
        for idx, action in enumerate(self.sequence_actions):
            action['index_lbl'].configure(text=f"#{idx+1}")
            
            # Rebind indices in callbacks
            action['up_btn'].configure(command=lambda i=idx: self.move_card_up(i))
            action['down_btn'].configure(command=lambda i=idx: self.move_card_down(i))
            action['del_btn'].configure(command=lambda i=idx: self.delete_card(i))
            
            if action['type'] == 'mouse':
                action['pick_btn'].configure(command=lambda i=idx: self.start_card_coordinate_picking(i))
            elif action['type'] == 'key':
                action['rec_btn'].configure(command=lambda i=idx: self.start_card_key_recording(i))
            elif action['type'] == 'app':
                action['browse_btn'].configure(command=lambda i=idx: self.start_card_app_browsing(i))
            elif action['type'] == 'image':
                action['browse_btn'].configure(command=lambda i=idx: self.start_card_image_browsing(i))
                action['snip_btn'].configure(command=lambda i=idx: self.start_card_image_snipping(i))
                
            action['widget'].pack(fill="x", padx=5, pady=4)

    def move_card_up(self, idx):
        if idx <= 0 or idx >= len(self.sequence_actions):
            return
        self.sequence_actions[idx], self.sequence_actions[idx-1] = self.sequence_actions[idx-1], self.sequence_actions[idx]
        self.repack_inspector_timeline()
        self.save_current_inspector_data()

    def move_card_down(self, idx):
        if idx < 0 or idx >= len(self.sequence_actions) - 1:
            return
        self.sequence_actions[idx], self.sequence_actions[idx+1] = self.sequence_actions[idx+1], self.sequence_actions[idx]
        self.repack_inspector_timeline()
        self.save_current_inspector_data()

    def delete_card(self, idx):
        if idx < 0 or idx >= len(self.sequence_actions):
            return
        action = self.sequence_actions.pop(idx)
        action['widget'].destroy()
        self.repack_inspector_timeline()
        self.save_current_inspector_data()

    def start_card_coordinate_picking(self, card_idx):
        self.log(f"Entering Coordinate Pick Mode for macro step #{card_idx + 1}.", self.accent_purple)
        CoordinatePicker(self, lambda x, y: self.on_card_coordinate_picked(card_idx, x, y))

    def on_card_coordinate_picked(self, card_idx, x, y):
        if x is not None and y is not None:
            if card_idx < len(self.sequence_actions):
                action = self.sequence_actions[card_idx]
                action['x_entry'].delete(0, "end")
                action['x_entry'].insert(0, str(x))
                action['y_entry'].delete(0, "end")
                action['y_entry'].insert(0, str(y))
                self.save_current_inspector_data()
                self.log(f"Captured coordinate for step #{card_idx+1}: ({x}, {y})", self.accent_green)
        else:
            self.log(f"Coordinate picker for step #{card_idx+1} cancelled.", "#ff453a")

    def start_card_app_browsing(self, card_idx):
        path = filedialog.askopenfilename(
            filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")],
            title=f"Select App for Step #{card_idx + 1}"
        )
        if path:
            if card_idx < len(self.sequence_actions):
                action = self.sequence_actions[card_idx]
                action['app_entry'].delete(0, "end")
                action['app_entry'].insert(0, path)
                self.save_current_inspector_data()
                self.log(f"Selected application path for step #{card_idx+1}: {path}", self.accent_green)

    def start_card_image_browsing(self, card_idx):
        path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp"), ("All Files", "*.*")],
            title=f"Select Image for Step #{card_idx + 1}"
        )
        if path:
            proj_dir = os.path.dirname(self.board_file)
            try:
                rel = os.path.relpath(path, proj_dir)
                if not rel.startswith(".."):
                    path = rel
            except ValueError:
                pass
            if card_idx < len(self.sequence_actions):
                action = self.sequence_actions[card_idx]
                action['image_entry'].delete(0, "end")
                action['image_entry'].insert(0, path)
                self.save_current_inspector_data()
                self.log(f"Selected image path for step #{card_idx+1}: {path}", self.accent_green)

    def start_card_image_snipping(self, card_idx):
        if card_idx < len(self.sequence_actions):
            self.log(f"Entering Screen Snipper for Step #{card_idx+1}.", self.accent_purple)
            ScreenSnipper(self, lambda img: self.on_card_image_snipped(card_idx, img))

    def on_card_image_snipped(self, card_idx, cropped_image):
        if cropped_image is None:
            self.log(f"Snipping for Step #{card_idx+1} cancelled.", "#ff453a")
            return
            
        r, c = self.selected_row, self.selected_col
        if r is None or c is None:
            return
            
        templates_dir = os.path.join(os.path.dirname(self.board_file), "templates")
        os.makedirs(templates_dir, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"snip_{r+1}_{c+1}_step{card_idx+1}_{timestamp}.png"
        full_path = os.path.join(templates_dir, filename)
        
        try:
            cropped_image.save(full_path, "PNG")
            rel_path = os.path.join("templates", filename)
            
            if card_idx < len(self.sequence_actions):
                action = self.sequence_actions[card_idx]
                action['image_entry'].delete(0, "end")
                action['image_entry'].insert(0, rel_path)
                self.save_current_inspector_data()
                self.log(f"Step #{card_idx+1}: Image captured and saved to: {rel_path}", self.accent_green)
        except Exception as e:
            self.log(f"Failed to save snipped image: {str(e)}", "#ff453a")

    def start_card_key_recording(self, card_idx):
        if self.recording_card_idx is not None:
            return
        self.recording_card_idx = card_idx
        action = self.sequence_actions[card_idx]
        action['rec_btn'].configure(text="Press...", fg_color="#ff453a", hover_color="#e03b31")
        self.log(f"Recording keystroke for Step #{card_idx+1}. Press any standard key or F1-F12 globally.", self.accent_purple)

    # --- Trigger Routines ---

    def trigger_selected_slot_async(self):
        r, c = self.selected_row, self.selected_col
        if r is None or c is None:
            return
        self.execute_slot_action_async(r, c, self.current_page)

    def execute_slot_action_async(self, r, c, page_idx=None):
        threading.Thread(target=self.run_slot_action, args=(r, c, page_idx), daemon=True).start()

    def run_slot_action(self, r, c, page_idx=None):
        if page_idx is None:
            page_idx = self.current_page
        slot = self.board_pages[page_idx][r][c]
        slot_type = slot['type']
        
        if slot_type == 'empty':
            return
            
        self.log(f"Executing Grid Slot P{page_idx+1} ({r+1}, {c+1}): '{slot['title'] or slot_type.upper()}'")
        
        # Prevent concurrent triggers
        if not self.sequence_lock.acquire(blocking=False):
            self.log("Another deck automation is currently executing. Denied.", "#ff9500")
            return
            
        try:
            self.current_running_slot = (page_idx, r, c)
            self.running_slot_start_time = time.time()
            self.stop_current_loop = False

            loop_enabled = slot.get('loop_enabled', False)
            loop_count = slot.get('loop_count', 0)
            
            max_iterations = loop_count if (loop_enabled and loop_count > 0) else (1 if not loop_enabled else float('inf'))
            iteration = 0
            
            while iteration < max_iterations:
                if self.stop_current_loop:
                    self.log("Loop execution stopped by user.", "#ff9500")
                    break
                    
                if iteration > 0:
                    self.log(f"Looping Slot P{page_idx+1} ({r+1}, {c+1}): Iteration {iteration+1}")

                if slot_type == 'app':
                    path = slot.get('app_path', '').strip()
                    if not path:
                        self.log("Application path is blank.", "#ff453a")
                        break
                    try:
                        os.startfile(path)
                        self.log(f"Successfully launched: {path}", self.accent_green)
                    except Exception as ex:
                        self.log(f"Failed launching app: {str(ex)}", "#ff453a")
                        break
                        
                elif slot_type == 'web':
                    url = slot.get('web_url', '').strip()
                    if not url:
                        self.log("Website URL is blank.", "#ff453a")
                        break
                    try:
                        import webbrowser
                        webbrowser.open(url)
                        self.log(f"Successfully launched website: {url}", self.accent_green)
                    except Exception as ex:
                        self.log(f"Failed launching website: {str(ex)}", "#ff453a")
                        break
                        
                elif slot_type == 'mouse':
                    x = slot.get('mouse_x', 1000)
                    y = slot.get('mouse_y', 850)
                    click_type = slot.get('click_type', 'Left Click')
                    glide_enabled = slot.get('glide_enabled', True)
                    glide_duration = slot.get('glide_duration', 0.1) if glide_enabled else 0.0
                    
                    # Glide execution
                    start_x, start_y = self.mouse_controller.position
                    if glide_duration > 0:
                        steps = int(glide_duration * 120)
                        if steps == 0: steps = 1
                        dt = glide_duration / steps
                        for step in range(1, steps + 1):
                            if self.stop_current_loop:
                                break
                            t = step / steps
                            if t < 0.5:
                                ease_t = 4 * t * t * t
                            else:
                                ease_t = 1 - ((-2 * t + 2) ** 3) / 2
                            curr_x = start_x + (x - start_x) * ease_t
                            curr_y = start_y + (y - start_y) * ease_t
                            self.mouse_controller.position = (int(curr_x), int(curr_y))
                            time.sleep(dt)
                    else:
                        self.mouse_controller.position = (x, y)
                    
                    if self.stop_current_loop:
                        break
                        
                    time.sleep(0.03)  # Synchronization
                    
                    if self.stop_current_loop:
                        break
                        
                    if click_type == "Left Click":
                        self.mouse_controller.click(pynput_mouse.Button.left, 1)
                    elif click_type == "Double Left Click":
                        self.mouse_controller.click(pynput_mouse.Button.left, 2)
                    elif click_type == "Right Click":
                        self.mouse_controller.click(pynput_mouse.Button.right, 1)
                    elif click_type == "Middle Click":
                        self.mouse_controller.click(pynput_mouse.Button.middle, 1)
                    
                    self.log(f"Cursor clicked successfully at ({x}, {y}).", self.accent_green)
                    
                elif slot_type == 'image':
                    image_path = slot.get('image_path', '').strip()
                    confidence = slot.get('confidence', 0.8)
                    click_type = slot.get('click_type', 'Left Click')
                    glide_enabled = slot.get('glide_enabled', True)
                    glide_duration = slot.get('glide_duration', 0.1) if glide_enabled else 0.0
                    
                    coords = self.locate_image_on_screen(image_path, confidence)
                    if coords is None:
                        self.log(f"Failed to locate image on screen: {image_path}", "#ff453a")
                        break
                    else:
                        x, y = coords
                        # Glide execution
                        start_x, start_y = self.mouse_controller.position
                        if glide_duration > 0:
                            steps = int(glide_duration * 120)
                            if steps == 0: steps = 1
                            dt = glide_duration / steps
                            for step in range(1, steps + 1):
                                if self.stop_current_loop:
                                    break
                                t = step / steps
                                if t < 0.5:
                                    ease_t = 4 * t * t * t
                                else:
                                    ease_t = 1 - ((-2 * t + 2) ** 3) / 2
                                curr_x = start_x + (x - start_x) * ease_t
                                curr_y = start_y + (y - start_y) * ease_t
                                self.mouse_controller.position = (int(curr_x), int(curr_y))
                                time.sleep(dt)
                        else:
                            self.mouse_controller.position = (x, y)
                        
                        if self.stop_current_loop:
                            break
                            
                        time.sleep(0.03) # Synchronization
                        
                        if self.stop_current_loop:
                            break
                            
                        if click_type == "Left Click":
                            self.mouse_controller.click(pynput_mouse.Button.left, 1)
                        elif click_type == "Double Left Click":
                            self.mouse_controller.click(pynput_mouse.Button.left, 2)
                        elif click_type == "Right Click":
                            self.mouse_controller.click(pynput_mouse.Button.right, 1)
                        elif click_type == "Middle Click":
                            self.mouse_controller.click(pynput_mouse.Button.middle, 1)
                        
                        self.log(f"Located image and clicked successfully at ({x}, {y}).", self.accent_green)
                        
                elif slot_type == 'macro':
                    steps = slot.get('steps', [])
                    if not steps:
                        self.log("Macro sequence timeline is empty.", "#ff9500")
                        break
                    
                    self.log("Starting macro sequence...", self.accent_purple)
                    macro_stopped = False
                    for step_idx, step in enumerate(steps):
                        if self.stop_current_loop:
                            macro_stopped = True
                            break
                        stype = step.get('type')
                        
                        if stype == 'mouse':
                            x = step.get('x', 1000)
                            y = step.get('y', 850)
                            click_type = step.get('click_type', 'Left Click')
                            glide_enabled = step.get('glide_enabled', True)
                            glide_duration = step.get('glide_duration', 0.1) if glide_enabled else 0.0
                            
                            start_x, start_y = self.mouse_controller.position
                            if glide_duration > 0:
                                steps_count = int(glide_duration * 120)
                                if steps_count == 0: steps_count = 1
                                dt = glide_duration / steps_count
                                for step_s in range(1, steps_count + 1):
                                    if self.stop_current_loop:
                                        break
                                    t = step_s / steps_count
                                    if t < 0.5:
                                        ease_t = 4 * t * t * t
                                    else:
                                        ease_t = 1 - ((-2 * t + 2) ** 3) / 2
                                    curr_x = start_x + (x - start_x) * ease_t
                                    curr_y = start_y + (y - start_y) * ease_t
                                    self.mouse_controller.position = (int(curr_x), int(curr_y))
                                    time.sleep(dt)
                            else:
                                self.mouse_controller.position = (x, y)
                                
                            if self.stop_current_loop:
                                macro_stopped = True
                                break
                                
                            time.sleep(0.03)
                            
                            if self.stop_current_loop:
                                macro_stopped = True
                                break
                            
                            if click_type == "Left Click":
                                self.mouse_controller.click(pynput_mouse.Button.left, 1)
                            elif click_type == "Double Left Click":
                                self.mouse_controller.click(pynput_mouse.Button.left, 2)
                            elif click_type == "Right Click":
                                self.mouse_controller.click(pynput_mouse.Button.right, 1)
                            elif click_type == "Middle Click":
                                self.mouse_controller.click(pynput_mouse.Button.middle, 1)
                                
                        elif stype == 'delay':
                            val = step.get('value', 500)
                            unit = step.get('unit', 'ms')
                            sleep_time = val / 1000.0 if unit == 'ms' else val
                            
                            # Interruptible sleep
                            sleep_end = time.time() + sleep_time
                            while time.time() < sleep_end:
                                if self.stop_current_loop:
                                    break
                                time.sleep(0.01)
                            
                            if self.stop_current_loop:
                                macro_stopped = True
                                break
                            
                        elif stype == 'key':
                            key_val = step.get('key', 'F')
                            if key_val:
                                if key_val in SPECIAL_KEYS_MAP:
                                    key_obj = SPECIAL_KEYS_MAP[key_val]
                                else:
                                    key_obj = pynput_keyboard.KeyCode.from_char(key_val.lower())
                                self.keyboard_controller.press(key_obj)
                                time.sleep(0.05)
                                self.keyboard_controller.release(key_obj)
                                
                        elif stype == 'text':
                            text_val = step.get('text', '')
                            if text_val:
                                self.keyboard_controller.type(text_val)
                                
                        elif stype == 'app':
                            app_path = step.get('app_path', '').strip()
                            if app_path:
                                try:
                                    os.startfile(app_path)
                                except Exception as ex:
                                    self.log(f"Failed to launch app in sequence: {str(ex)}", "#ff453a")
                                    
                        elif stype == 'web':
                            web_url = step.get('web_url', '').strip()
                            if web_url:
                                try:
                                    import webbrowser
                                    webbrowser.open(web_url)
                                except Exception as ex:
                                    self.log(f"Failed to launch website in sequence: {str(ex)}", "#ff453a")
    
                        elif stype == 'image':
                            image_path = step.get('image_path', '').strip()
                            confidence = step.get('confidence', 0.8)
                            click_type = step.get('click_type', 'Left Click')
                            glide_enabled = step.get('glide_enabled', True)
                            glide_duration = step.get('glide_duration', 0.1) if glide_enabled else 0.0
                            
                            coords = self.locate_image_on_screen(image_path, confidence)
                            if coords is None:
                                self.log(f"Macro step: failed to locate image: {image_path}", "#ff453a")
                            else:
                                x, y = coords
                                start_x, start_y = self.mouse_controller.position
                                if glide_duration > 0:
                                    steps_count = int(glide_duration * 120)
                                    if steps_count == 0: steps_count = 1
                                    dt = glide_duration / steps_count
                                    for step_s in range(1, steps_count + 1):
                                        if self.stop_current_loop:
                                            break
                                        t = step_s / steps_count
                                        if t < 0.5:
                                            ease_t = 4 * t * t * t
                                        else:
                                            ease_t = 1 - ((-2 * t + 2) ** 3) / 2
                                        curr_x = start_x + (x - start_x) * ease_t
                                        curr_y = start_y + (y - start_y) * ease_t
                                        self.mouse_controller.position = (int(curr_x), int(curr_y))
                                        time.sleep(dt)
                                else:
                                    self.mouse_controller.position = (x, y)
                                    
                                if self.stop_current_loop:
                                    macro_stopped = True
                                    break
                                    
                                time.sleep(0.03)
                                
                                if self.stop_current_loop:
                                    macro_stopped = True
                                    break
                                
                                if click_type == "Left Click":
                                    self.mouse_controller.click(pynput_mouse.Button.left, 1)
                                elif click_type == "Double Left Click":
                                    self.mouse_controller.click(pynput_mouse.Button.left, 2)
                                elif click_type == "Right Click":
                                    self.mouse_controller.click(pynput_mouse.Button.right, 1)
                                elif click_type == "Middle Click":
                                    self.mouse_controller.click(pynput_mouse.Button.middle, 1)
                                
                                self.log(f"Macro step: located image and clicked successfully at ({x}, {y}).", self.accent_green)
                                
                        elif stype == 'recorded':
                            events = step.get('events', [])
                            skip_mouse_move = step.get('skip_mouse_move', False)
                            if events:
                                mode_str = " (WARP: mouse moves skipped)" if skip_mouse_move else ""
                                self.log(f"Replaying recorded session: {len(events)} events{mode_str}...", self.accent_purple)
                                start_time = time.time()
                                base_offset = events[0].get('time', 0.0)
                                
                                for ev in events:
                                    if self.stop_current_loop:
                                        macro_stopped = True
                                        break
                                    target_time = start_time + (ev.get('time', 0.0) - base_offset)
                                    while time.time() < target_time:
                                        if self.stop_current_loop:
                                            break
                                        time.sleep(0.01)
                                        
                                    if self.stop_current_loop:
                                        macro_stopped = True
                                        break
                                        
                                    etype = ev.get('type')
                                    if etype == 'mouse_move':
                                        if skip_mouse_move:
                                            continue
                                        self.mouse_controller.position = (ev['x'], ev['y'])
                                    elif etype == 'mouse_down':
                                        self.mouse_controller.position = (ev['x'], ev['y'])
                                        btn_name = ev.get('button', 'left')
                                        btn = pynput_mouse.Button.left if btn_name == 'left' else (pynput_mouse.Button.right if btn_name == 'right' else pynput_mouse.Button.middle)
                                        self.mouse_controller.press(btn)
                                    elif etype == 'mouse_up':
                                        self.mouse_controller.position = (ev['x'], ev['y'])
                                        btn_name = ev.get('button', 'left')
                                        btn = pynput_mouse.Button.left if btn_name == 'left' else (pynput_mouse.Button.right if btn_name == 'right' else pynput_mouse.Button.middle)
                                        self.mouse_controller.release(btn)
                                    elif etype == 'key_down':
                                        k_val = ev.get('key')
                                        k_obj = self.deserialize_key(k_val)
                                        if k_obj:
                                            try:
                                                self.keyboard_controller.press(k_obj)
                                            except:
                                                pass
                                    elif etype == 'key_up':
                                        k_val = ev.get('key')
                                        k_obj = self.deserialize_key(k_val)
                                        if k_obj:
                                            try:
                                                self.keyboard_controller.release(k_obj)
                                            except:
                                                pass
                                                
                        time.sleep(0.02)
                        
                    if macro_stopped:
                        break
                    self.log("Macro sequence completed successfully.", self.accent_green)
                
                iteration += 1
                if iteration < max_iterations:
                    # Brief sleep between iterations, checking for stop requests
                    for _ in range(10):
                        if self.stop_current_loop:
                            break
                        time.sleep(0.01)
                        
        except Exception as e:
            self.log(f"Sequence macro exception: {str(e)}", "#ff453a")
        finally:
            self.current_running_slot = None
            self.stop_current_loop = False
            self.sequence_lock.release()

    # --- Keyboard listener inputs routing ---

    def global_on_press(self, key):
        if isinstance(key, str):
            key_name = key
        else:
            key_name = self.normalize_key_name(key)
        
        # 1. Macro Timeline step recording
        if self.recording_card_idx is not None:
            if key_name in ["Ctrl", "Alt", "Shift", "Win"]:
                return
            card_idx = self.recording_card_idx
            self.recording_card_idx = None
            
            if card_idx < len(self.sequence_actions):
                action = self.sequence_actions[card_idx]
                action['key_entry'].delete(0, "end")
                action['key_entry'].insert(0, key_name)
                
                self.after(0, lambda: action['rec_btn'].configure(text="Record", fg_color="#0a0c10", hover_color="#2b3240"))
                self.save_current_inspector_data()
                self.log(f"Step #{card_idx + 1}: Recorded key '{key_name}'", self.accent_green)
            return

        # 2. Main Slot Hotkey recording
        if self.is_recording_slot:
            self.pressed_keys_global.add(key_name)
            self.recorded_keys_temp.add(key_name)
            
            combo_str = " + ".join(sorted(list(self.recorded_keys_temp)))
            self.after(0, lambda: self.inspector_hotkey_display.configure(text=combo_str))
            return

        # 2b. AutoClicker Hotkey recording
        if self.is_recording_ac_hotkey:
            self.pressed_keys_global.add(key_name)
            self.autoclicker_hotkey.add(key_name)
            combo_str = " + ".join(sorted(list(self.autoclicker_hotkey)))
            self.after(0, lambda s=combo_str: self.ac_hotkey_display.configure(text=s, text_color="#ff9500"))
            return

        # 3. Global hotkey trigger monitoring
        self.pressed_keys_global.add(key_name)
        
        # Check if we should stop the currently running loop
        if self.current_running_slot is not None:
            curr_p, curr_r, curr_c = self.current_running_slot
            running_slot = self.board_pages[curr_p][curr_r][curr_c]
            
            is_hotkey_pressed = False
            if running_slot.get('hotkey') and running_slot['hotkey'].issubset(self.pressed_keys_global):
                if time.time() - self.running_slot_start_time > 0.5:
                    is_hotkey_pressed = True
                    
            if key_name == 'Esc' or is_hotkey_pressed:
                self.stop_current_loop = True
                self.log("Loop execution stop requested by hotkey.", "#ff9500")
                return
                
        current_time = time.time()
        # Iterate over all pages and all 32 buttons per page
        for p_idx, page in enumerate(self.board_pages):
            for r in range(4):
                for c in range(8):
                    slot = page[r][c]
                    if slot['type'] != 'empty' and slot['hotkey']:
                        if slot['hotkey'].issubset(self.pressed_keys_global):
                            # Debounce 400ms per trigger event
                            if current_time - self.last_triggered_time > 0.4:
                                self.last_triggered_time = current_time
                                self.log(f"Global Hotkey Triggered for Slot P{p_idx+1} ({r+1}, {c+1}): {' + '.join(sorted(list(slot['hotkey'])))}", self.accent_purple)
                                self.execute_slot_action_async(r, c, p_idx)

        # AutoClicker global hotkey check
        if self.autoclicker_hotkey and self.autoclicker_hotkey.issubset(self.pressed_keys_global):
            if current_time - self.last_triggered_time > 0.4:
                self.last_triggered_time = current_time
                self.after(0, self.toggle_autoclicker)

    def global_on_release(self, key):
        if isinstance(key, str):
            key_name = key
        else:
            key_name = self.normalize_key_name(key)
        
        if key_name in self.pressed_keys_global:
            self.pressed_keys_global.remove(key_name)
            
        # AutoClicker hotkey finalize (on full release)
        if self.is_recording_ac_hotkey:
            if len(self.pressed_keys_global) == 0:
                self.is_recording_ac_hotkey = False
                if self.autoclicker_hotkey:
                    combo_str = " + ".join(sorted(list(self.autoclicker_hotkey)))
                    self.after(0, lambda s=combo_str: [
                        self.ac_hotkey_display.configure(text=s, text_color=self.accent_green),
                        self.ac_hotkey_rec_btn.configure(text="Record", fg_color="#1a4025", text_color=self.accent_green)
                    ])
                    self.log(f"AutoClicker hotkey registered: {combo_str}", self.accent_green)
                return

        if self.is_recording_slot:
            if len(self.pressed_keys_global) == 0:
                self.is_recording_slot = False
                
                r, c = self.selected_row, self.selected_col
                if r is not None and c is not None:
                    slot = self.board_slots[r][c]
                    if len(self.recorded_keys_temp) > 0:
                        slot['hotkey'] = set(self.recorded_keys_temp)
                        combo_str = " + ".join(sorted(list(slot['hotkey'])))
                        self.after(0, lambda: self.inspector_hotkey_display.configure(text=combo_str, text_color=self.accent_purple))
                        self.log(f"Registered hotkey for Grid Slot ({r+1}, {c+1}): {combo_str}", self.accent_green)
                    else:
                        slot['hotkey'] = set()
                        self.after(0, lambda: self.inspector_hotkey_display.configure(text="None", text_color=self.accent_purple))
                        self.log("Hotkey cleared.", "#ff453a")
                        
                    self.save_board_data()
                
                self.after(0, lambda: self.inspector_rec_btn.configure(text="Record", fg_color="#1c212e", hover_color="#2b3240"))

    def normalize_key_name(self, key):
        if hasattr(key, 'char') and key.char is not None:
            if 32 <= ord(key.char) < 127:
                return key.char.upper()
                
        if hasattr(key, 'name') and key.name is not None:
            name = key.name.lower()
            if name.startswith('ctrl'):
                return 'Ctrl'
            elif name.startswith('alt'):
                return 'Alt'
            elif name.startswith('shift'):
                return 'Shift'
            elif name.startswith('cmd') or name.startswith('win'):
                return 'Win'
            elif name == 'space':
                return 'Space'
            elif name == 'enter':
                return 'Enter'
            elif name == 'esc':
                return 'Esc'
            else:
                if name.startswith('f') and len(name) > 1:
                    return name.upper()
                return name.capitalize()
                
        vk = getattr(key, 'vk', None)
        if vk is not None:
            if 65 <= vk <= 90:
                return chr(vk)
            elif 48 <= vk <= 57:
                return chr(vk)
            elif 96 <= vk <= 105:
                return f"Num_{vk - 96}"
            return f"Key_{vk}"
            
        return str(key)

    def log(self, message, color_tag=None):
        """Thread-safe method to append timestamps and logs to the textbox."""
        timestamp = time.strftime("[%H:%M:%S]")
        log_line = f"{timestamp} {message}\n"
        
        def do_log():
            if not hasattr(self, 'log_text') or self.log_text is None:
                # Fallback to standard console print if UI is not fully created yet
                print(log_line.strip())
                return
                
            self.log_text.configure(state="normal")
            
            text_content = self.log_text.get("1.0", "end-1c")
            if len(text_content.split('\n')) > 200:
                self.log_text.delete("1.0", "30.0")
                
            self.log_text.insert("end", log_line)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
            
        self.after(0, do_log)

    def locate_image_on_screen(self, image_path, confidence_threshold=0.8):
        """Searches the screen for the target image using OpenCV template matching.
        Returns (x, y) center coordinates if found, else None.
        """
        if not OPENCV_AVAILABLE:
            self.log("Error: OpenCV and Pillow (PIL) are required for image recognition. Install them first.", "#ff453a")
            return None
            
        try:
            # Check if relative to app folder or check if filename only in a templates/ subdir
            possible_paths = [
                image_path,
                os.path.join(os.path.dirname(self.board_file), image_path),
                os.path.join(os.path.dirname(self.board_file), "templates", image_path)
            ]
            actual_path = None
            for p in possible_paths:
                if os.path.exists(p):
                    actual_path = p
                    break
            if not actual_path:
                self.log(f"Image file not found: {image_path}", "#ff453a")
                return None
            image_path = actual_path

            # Take screenshot of all screens
            screenshot = ImageGrab.grab(all_screens=True)
            screenshot_np = np.array(screenshot)
            screenshot_cv = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
            
            # Read template image via PIL to support unicode paths and clean format conversion
            from PIL import Image
            template_img = Image.open(image_path)
            template_np = np.array(template_img)
            
            # Convert template to OpenCV format
            if len(template_np.shape) == 3:
                if template_np.shape[2] == 4:
                    template_cv = cv2.cvtColor(template_np, cv2.COLOR_RGBA2BGR)
                else:
                    template_cv = cv2.cvtColor(template_np, cv2.COLOR_RGB2BGR)
            else:
                template_cv = cv2.cvtColor(template_np, cv2.COLOR_GRAY2BGR)
                
            if template_cv is None:
                self.log(f"Error: Could not read template image from: {image_path}", "#ff453a")
                return None
                
            h_scr, w_scr = screenshot_cv.shape[:2]
            h_tpl, w_tpl = template_cv.shape[:2]
            
            if h_tpl > h_scr or w_tpl > w_scr:
                self.log("Error: Target image is larger than the screen size.", "#ff453a")
                return None
                
            # Perform template matching
            res = cv2.matchTemplate(screenshot_cv, template_cv, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            
            if max_val >= confidence_threshold:
                match_x = max_loc[0] + w_tpl // 2
                match_y = max_loc[1] + h_tpl // 2
                return (match_x, match_y)
            else:
                self.log(f"Image match confidence too low: max={max_val:.2f}, req={confidence_threshold:.2f}", "#ff9500")
                return None
        except Exception as e:
            self.log(f"Image recognition error: {str(e)}", "#ff453a")
            return None

    def clear_logs(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self.log("Logs cleared.")

    def _poll_controller(self):
        if getattr(self, "disable_controller", False):
            return
        import time
        winmm = ctypes.windll.winmm
        
        # Track D-pad (POV) state per joystick
        dpad_states = {}
        
        while True:
            time.sleep(0.015)
            current_pressed_all = set()
            
            # 1. Poll XInput (Xbox Controllers)
            if XInputGetState:
                for user_idx in range(4):
                    state = XINPUT_STATE()
                    res = XInputGetState(user_idx, byref(state))
                    if res == 0:
                        wButtons = state.Gamepad.wButtons
                        for mask, name in XINPUT_BUTTONS.items():
                            if wButtons & mask:
                                current_pressed_all.add(name)
                        if state.Gamepad.bLeftTrigger > 120:
                            current_pressed_all.add("Controller_LT")
                        if state.Gamepad.bRightTrigger > 120:
                            current_pressed_all.add("Controller_RT")
            
            # 2. Poll WinMM (PlayStation and generic controllers)
            num_devs = winmm.joyGetNumDevs()
            for i in range(min(num_devs, 8)):
                info = JOYINFOEX()
                info.dwSize = sizeof(JOYINFOEX)
                info.dwFlags = 0xFF # JOY_RETURNALL
                
                res = winmm.joyGetPosEx(i, byref(info))
                if res == 0:
                    caps = JOYCAPS()
                    winmm.joyGetDevCapsW(i, byref(caps), sizeof(JOYCAPS))
                    
                    # Skip Microsoft / Xbox devices to let XInput handle them
                    if caps.wMid == 1118:
                        continue
                        
                    joy_name = caps.szPname if caps.szPname else "Wireless Controller"
                    
                    # Read buttons
                    num_buttons = caps.wNumButtons if caps.wNumButtons > 0 else 32
                    for btn_idx in range(min(num_buttons, 32)):
                        if info.dwButtons & (1 << btn_idx):
                            btn_label = self._get_winmm_button_label(joy_name, btn_idx)
                            current_pressed_all.add(btn_label)
                            
                    # Read D-pad (POV)
                    pov = info.dwPOV
                    dpad_key = i
                    old_dpads = dpad_states.get(dpad_key, set())
                    new_dpads = set()
                    
                    if pov != 65535:
                        if pov == 0 or pov == 31500 or pov == 4500:
                            new_dpads.add("Dpad_Up")
                        if pov == 18000 or pov == 13500 or pov == 22500:
                            new_dpads.add("Dpad_Down")
                        if pov == 27000 or pov == 22500 or pov == 31500:
                            new_dpads.add("Dpad_Left")
                        if pov == 9000 or pov == 4500 or pov == 13500:
                            new_dpads.add("Dpad_Right")
                            
                    dpad_states[dpad_key] = new_dpads
                    for dpad_dir in new_dpads:
                        current_pressed_all.add(f"Controller_{dpad_dir}")
            
            # 3. Calculate transitions for ALL buttons globally
            newly_pressed = current_pressed_all - self.pressed_controller_buttons
            newly_released = self.pressed_controller_buttons - current_pressed_all
            
            self.pressed_controller_buttons = current_pressed_all
            
            for btn in newly_pressed:
                self.after(0, lambda b=btn: self.global_on_press(b))
            for btn in newly_released:
                self.after(0, lambda b=btn: self.global_on_release(b))

    def _get_winmm_button_label(self, joy_name, btn_idx):
        name_lower = joy_name.lower()
        if "sony" in name_lower or "dualshock" in name_lower or "playstation" in name_lower or "wireless controller" in name_lower:
            ps_map = {
                0: "Square",
                1: "Cross",
                2: "Circle",
                3: "Triangle",
                4: "L1",
                5: "R1",
                6: "L2",
                7: "R2",
                8: "Share",
                9: "Options",
                10: "LStick_Click",
                11: "RStick_Click",
                12: "PS",
                13: "Touchpad"
            }
            name = ps_map.get(btn_idx, f"Button_{btn_idx+1}")
            return f"Controller_{name}"
        else:
            xbox_map = {
                0: "A",
                1: "B",
                2: "X",
                3: "Y",
                4: "LB",
                5: "RB",
                6: "Back",
                7: "Start",
                8: "LStick_Click",
                9: "RStick_Click",
                10: "Home"
            }
            name = xbox_map.get(btn_idx, f"Button_{btn_idx+1}")
            return f"Controller_{name}"

if __name__ == "__main__":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass
            
    # CLI Mode check
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == "--run-slot":
        app = ClickPulseApp()
        app.withdraw() # Hide GUI
        try:
            target = sys.argv[2] # e.g. P1_R1_C1
            parts = target.split("_")
            p_idx = int(parts[0][1:]) - 1
            r_idx = int(parts[1][1:]) - 1
            c_idx = int(parts[2][1:]) - 1
            app.run_slot_action(r_idx, c_idx, p_idx)
        except Exception as e:
            print(f"CLI Error: {e}")
        finally:
            sys.exit(0)
            
    app = ClickPulseApp()
    app.mainloop()
