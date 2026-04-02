#############################################################################################

#   THIS APPLICATION IS MADE AS A SOLUTION TO THE RESEARCH WORKS CONDUCTED IN DTU AQUA,
#   SECTION OF FISHERIES TECHNOLOGY, TECHNICAL UNIVERSITY OF DENMARK. THE APPLICATION IS
#   BUILD ON THE ORIGINAL SVO TO AVI FORMAT CONVERTER SCRIPT GIVEN BY THE STEREOLABS.
#   THE GUI IS MADE TO CONDUCT IN-HOUSE BATCH CONVERSION OF VIDEO CLIPS AND ALSO INDIVIDUAL
#   CONVERSION WITH A TRIMMING FEATURE. THE APPLICATION WILL BE DEVELOPED AND UPDATED
#   CONTINUOUSLY TO MEET THE ONGOING RESEARCH NEEDS.

#   DEVELOPED BY SAMITHA N. THILARATHNA, PhD STUDENT, DTU AQUA
#   email: msam@aqua.dtu.dk
#   last updated on 2nd April 2026

#############################################################################################

import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
import os
import subprocess
import threading
import queue
import re
import time
from PIL import Image, ImageTk
import datetime
import webbrowser

# OpenCV is always required
try:
    import cv2
except ImportError:
    print("Error: OpenCV (cv2) not found. Please install opencv-python.")
    exit()

# ZED SDK
try:
    import pyzed.sl as sl
    ZED_AVAILABLE = True
except ImportError:
    ZED_AVAILABLE = False
    print("Warning: ZED SDK (pyzed) not found. SVO-based tabs will be disabled.")


# ──────────────────────────────────────────────────────────────────────────────
#  MAC-STYLE DARK THEME CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────
BG_COLOR          = "#0d0f12"  # Deep dark background
SIDEBAR_BG        = "#000000"
PANEL_BG          = "#15181c"
ENTRY_BG          = "#1e2227"
BORDER_COLOR      = "#2a2f38"
TEXT_COLOR        = "#FFFFFF"
DIM_TEXT          = "#888888"
BLUE_ACCENT       = "#0A84FF"  # Apple Blue
BLUE_HOVER        = "#0060C0"
STOP_BTN          = "#c0392b"
STOP_HOVER        = "#e74c3c"

# Frame Entry Colors
FRAME_ENTRY_BG    = "#005f6b"  # Teal
TIME_ENTRY_BG     = "#7a5200"  # Brownish/Yellow

# Gradients for graphs
GRAPH_PURPLE      = "#7B2CBF"
GRAPH_PINK        = "#FF007F"
GRAPH_GREEN_DARK  = "#2E8B57"
GRAPH_GREEN_LIGHT = "#ADFF2F"
GRAPH_ERROR       = "#FF3B30"


# ──────────────────────────────────────────────────────────────────────────────
#  HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────────
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % (int(rgb[0]), int(rgb[1]), int(rgb[2]))

def interpolate_color(c1, c2, factor):
    """Interpolates between two hex colors based on a factor (0.0 to 1.0)"""
    rgb1 = hex_to_rgb(c1)
    rgb2 = hex_to_rgb(c2)
    new_rgb = [rgb1[i] + (rgb2[i] - rgb1[i]) * factor for i in range(3)]
    return rgb_to_hex(new_rgb)


# ──────────────────────────────────────────────────────────────────────────────
#  CUSTOM WIDGETS (Vector Drawn, Mac Style)
# ──────────────────────────────────────────────────────────────────────────────
class CanvasRadio(tk.Canvas):
    """A custom vector-drawn radio button for modern styling."""
    def __init__(self, parent, text, variable, value, command=None, w=100, h=28, bg=BG_COLOR, fg=TEXT_COLOR, accent=BLUE_ACCENT):
        super().__init__(parent, width=w, height=h, bg=bg, highlightthickness=0, cursor='hand2')
        self.variable = variable
        self.value = value
        self.text = text
        self.command = command
        self.fg = fg
        self.accent = accent

        self.bind('<Button-1>', self._on_click)
        self.variable.trace_add('write', self._on_var_change)
        self._draw()

    def _draw(self):
        self.delete('all')
        is_selected = (self.variable.get() == self.value)
        ring_color = self.accent if is_selected else DIM_TEXT
        
        # Outer ring
        self.create_oval(4, 6, 20, 22, outline=ring_color, width=2)
        
        if is_selected:
            # Inner filled dot
            self.create_oval(8, 10, 16, 18, fill=self.accent, outline='')
            
        # Text (bright if selected, dim if not)
        text_color = self.fg if is_selected else DIM_TEXT
        self.create_text(28, 14, text=self.text, fill=text_color, font=('Segoe UI', 11), anchor='w')

    def _on_click(self, event):
        self.variable.set(self.value)
        if self.command:
            self.command()

    def _on_var_change(self, *args):
        self._draw()


class PillButton(tk.Canvas):
    """A pill-shaped text button."""
    def __init__(self, parent, text='', command=None, w=120, h=32, bg=BLUE_ACCENT, hover_bg=BLUE_HOVER, fg=TEXT_COLOR):
        super().__init__(parent, width=w, height=h, highlightthickness=0, bg=BG_COLOR, cursor='hand2')
        self.btn_w, self.btn_h = w, h
        self._text = text
        self._command = command
        self._bg_normal = bg
        self._bg_hover = hover_bg
        self._bg_disabled = "#333333"
        self._bg_current = bg
        self._fg = fg
        self._enabled = True

        self.bind('<Button-1>', self._on_press)
        self.bind('<ButtonRelease-1>', self._on_release)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self._draw(self._bg_normal)

    def _draw(self, fill):
        self.delete('all')
        r = self.btn_h // 2
        w, h = self.btn_w, self.btn_h
        pts = [r, 0, w-r, 0, w, 0, w, r, w, h-r, w, h, w-r, h, r, h, 0, h, 0, h-r, 0, r, 0, 0]
        self.create_polygon(pts, smooth=True, fill=fill, outline='')
        
        fg = self._fg if self._enabled else DIM_TEXT
        self.create_text(w//2, h//2, text=self._text, fill=fg, font=('Segoe UI', 11, 'bold'))

    def _on_press(self, _e):
        if self._enabled: self._draw(self._bg_hover)

    def _on_release(self, _e):
        if self._enabled:
            self._draw(self._bg_hover)
            if self._command: self._command()

    def _on_enter(self, _e):
        if self._enabled: self._draw(self._bg_hover)

    def _on_leave(self, _e):
        self._draw(self._bg_current)

    def set_state(self, state):
        self._enabled = (state != 'disabled')
        self._bg_current = self._bg_normal if self._enabled else self._bg_disabled
        self.config(cursor='hand2' if self._enabled else 'arrow')
        self._draw(self._bg_current)


class IconButton(tk.Canvas):
    """Vector drawn icon button for media controls."""
    def __init__(self, parent, icon, command=None, w=40, h=40, fg=BLUE_ACCENT, hover_fg=BLUE_HOVER):
        super().__init__(parent, width=w, height=h, highlightthickness=0, bg=BG_COLOR, cursor='hand2')
        self.btn_w, self.btn_h = w, h
        self._icon = icon
        self._command = command
        self._fg_normal = fg
        self._fg_hover = hover_fg
        self._fg_current = fg
        self._enabled = True

        self.bind('<Button-1>', self._on_press)
        self.bind('<ButtonRelease-1>', self._on_release)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self._draw(self._fg_normal)

    def _draw(self, fg):
        self.delete('all')
        cx, cy = self.btn_w // 2, self.btn_h // 2
        r = min(self.btn_h, self.btn_w) // 2 - 6

        if self._icon == 'play':
            pts = [cx - r + 4, cy - r + 2, cx + r - 2, cy, cx - r + 4, cy + r - 2]
            self.create_polygon(pts, fill=fg, outline='')
        elif self._icon == 'pause':
            bw, gap = max(3, r//2 - 2), max(3, r//3)
            self.create_rectangle(cx - gap - bw, cy - r + 2, cx - gap, cy + r - 2, fill=fg, outline='')
            self.create_rectangle(cx + gap, cy - r + 2, cx + gap + bw, cy + r - 2, fill=fg, outline='')
        elif self._icon == 'mark_in':
            bx = cx - r + 2
            self.create_rectangle(bx, cy - r + 2, bx + 3, cy + r - 2, fill=fg, outline='')
            pts = [bx + 6, cy - r + 4, cx + r - 2, cy, bx + 6, cy + r - 4]
            self.create_polygon(pts, fill=fg, outline='')
        elif self._icon == 'mark_out':
            bx = cx + r - 2
            self.create_rectangle(bx - 3, cy - r + 2, bx, cy + r - 2, fill=fg, outline='')
            pts = [bx - 6, cy - r + 4, cx - r + 2, cy, bx - 6, cy + r - 4]
            self.create_polygon(pts, fill=fg, outline='')
        elif self._icon == 'capture':
            br = r - 1
            self.create_rectangle(cx - br, cy - br + 4, cx + br, cy + br, outline=fg, width=2, fill='')
            self.create_oval(cx - br//2, cy - br//2 + 4, cx + br//2, cy + br//2 + 4, outline=fg, width=2, fill='')
            self.create_rectangle(cx - br//3 + 1, cy - br + 2, cx + br//3 - 1, cy - br + 5, fill=fg, outline='')

    def _on_press(self, _e):
        if self._enabled: self._draw(self._fg_hover)
    def _on_release(self, _e):
        if self._enabled:
            self._draw(self._fg_hover)
            if self._command: self._command()
    def _on_enter(self, _e):
        if self._enabled: self._draw(self._fg_hover)
    def _on_leave(self, _e):
        self._draw(self._fg_current)

    def set_icon(self, icon):
        self._icon = icon
        self._draw(self._fg_current)


class RoundedEntry(tk.Frame):
    """A mac-style rounded entry box."""
    def __init__(self, parent, width=300, textvariable=None):
        super().__init__(parent, bg=BG_COLOR)
        self.canvas = tk.Canvas(self, width=width, height=32, bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack(fill='x', expand=True)
        
        w, h, r = width, 32, 16
        pts = [r, 0, w-r, 0, w, 0, w, r, w, h-r, w, h, w-r, h, r, h, 0, h, 0, h-r, 0, r, 0, 0]
        self.border = self.canvas.create_polygon(pts, smooth=True, fill=ENTRY_BG, outline=BORDER_COLOR, width=2)

        self.entry = tk.Entry(self, textvariable=textvariable, bg=ENTRY_BG, fg=TEXT_COLOR, 
                              insertbackground=TEXT_COLOR, relief='flat', font=('Segoe UI', 11))
        self.entry.place(x=12, y=6, width=width-24, height=20)
        
        self.entry.bind('<FocusIn>', lambda e: self.canvas.itemconfig(self.border, outline=BLUE_ACCENT))
        self.entry.bind('<FocusOut>', lambda e: self.canvas.itemconfig(self.border, outline=BORDER_COLOR))
        self.canvas.bind('<Configure>', self._on_resize)

    def _on_resize(self, event):
        w, h, r = event.width, event.height, 16
        if w < 20: return
        pts = [r, 0, w-r, 0, w, 0, w, r, w, h-r, w, h, w-r, h, r, h, 0, h, 0, h-r, 0, r, 0, 0]
        self.canvas.coords(self.border, *pts)
        self.entry.place(x=12, y=6, width=w-24, height=20)


class ProgressGraph(tk.Canvas):
    """Animated gradient speed graph with error marking."""
    def __init__(self, parent, c1, c2, title="", height=80):
        super().__init__(parent, height=height, bg=BG_COLOR, highlightthickness=1, highlightbackground=BORDER_COLOR)
        self.c1 = c1
        self.c2 = c2
        self.title = title
        self.history = []  
        self.errors = []   
        self.max_speed = 0.001
        self.draw_ui()

    def draw_ui(self):
        self.delete('all')
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10: return

        self.create_rectangle(0, 0, w, h, fill=BG_COLOR, outline=BORDER_COLOR, width=1)

        if not self.history: return

        prev_x, prev_y = None, None
        speeds = [s for p, s in self.history]
        self.max_speed = max(max(speeds) if speeds else 0.001, self.max_speed)
        
        for i in range(len(self.history)):
            pct, speed = self.history[i]
            x = (pct / 100.0) * w
            normalized_h = (speed / self.max_speed) * (h - 20)
            y = h - normalized_h - 2

            if prev_x is not None:
                factor = (prev_x + x) / (2 * w)
                color = interpolate_color(self.c1, self.c2, factor)
                self.create_line(prev_x, prev_y, x, y, fill=color, width=4, capstyle='round', smooth=True)

            prev_x, prev_y = x, y

        for err_pct in self.errors:
            err_x = (err_pct / 100.0) * w
            self.create_line(err_x, 0, err_x, h, fill=GRAPH_ERROR, width=2, dash=(4, 4))

    def update_graph(self, pct, speed):
        self.history.append((pct, speed))
        self.draw_ui()

    def mark_error(self, pct):
        self.errors.append(pct)
        self.draw_ui()

    def clear(self):
        self.history = []
        self.errors = []
        self.max_speed = 0.001
        self.draw_ui()


# ──────────────────────────────────────────────────────────────────────────────
#  MAIN APPLICATION
# ──────────────────────────────────────────────────────────────────────────────
class SVOConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SVO Converter Suit")
        self.root.geometry("1500x900")
        self.root.configure(bg=BG_COLOR)

        # File Variables
        self.batch_input_dir  = tk.StringVar()
        self.batch_output_dir = tk.StringVar()
        self.trim_input_file  = tk.StringVar()
        self.trim_output_dir  = tk.StringVar()
        self.avi_input_file   = tk.StringVar()
        self.avi_output_dir   = tk.StringVar()
        
        # Frame Entry Variables
        self.start_frame_var  = tk.StringVar(value="0")
        self.end_frame_var    = tk.StringVar(value="0")
        self.avi_start_frame_var = tk.StringVar(value="0")
        self.avi_end_frame_var   = tk.StringVar(value="0")

        self.log_queue       = queue.Queue()
        self.progress_queue  = queue.Queue()
        self.stop_event      = threading.Event()
        self.running_process = None

        # SVO Player States
        self.trim_video_capture = None
        self.trim_total_frames  = 0
        self.trim_fps           = 30
        self.trim_start_frame   = 0
        self.trim_end_frame     = 0
        self.is_playing         = False
        self.svo_export_side    = tk.StringVar(value='left')
        self.svo_preview_side   = tk.StringVar(value='left')

        # AVI Player States
        self.avi_video_capture    = None
        self.avi_total_frames     = 0
        self.avi_fps              = 30
        self.avi_start_frame      = 0
        self.avi_end_frame        = 0
        self.avi_is_playing       = False
        self.avi_export_side      = tk.StringVar(value='left')
        self.avi_preview_side     = tk.StringVar(value='left')

        # Layout Setup
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self._create_sidebar()
        self.main_container = tk.Frame(self.root, bg=BG_COLOR)
        self.main_container.grid(row=0, column=1, sticky='nsew', padx=20, pady=20)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.frames = {}
        for F in (self._create_batch_tab, self._create_trim_tab, self._create_avi_tab, self._create_doc_tab):
            frame_name, frame_obj = F(self.main_container)
            self.frames[frame_name] = frame_obj
            frame_obj.grid(row=0, column=0, sticky="nsew")

        self.show_frame("SVO Trim and Export")
        self.root.after(100, self.process_queues)
        self.root.bind("<Configure>", lambda e: self._redraw_graphs())

    def _redraw_graphs(self):
        if hasattr(self, 'batch_single_graph'): self.batch_single_graph.draw_ui()
        if hasattr(self, 'batch_overall_graph'): self.batch_overall_graph.draw_ui()
        if hasattr(self, 'trim_overall_graph'): self.trim_overall_graph.draw_ui()
        if hasattr(self, 'avi_overall_graph'): self.avi_overall_graph.draw_ui()

    # ── Sidebar Navigation ─────────────────────────────────────────────────
    def _create_sidebar(self):
        self.sidebar = tk.Frame(self.root, bg=SIDEBAR_BG, width=250)
        self.sidebar.grid(row=0, column=0, sticky='ns')
        
        tk.Frame(self.root, bg=BORDER_COLOR, width=2).grid(row=0, column=0, sticky='nse', pady=30)
        tk.Label(self.sidebar, text="SVO Converter Suit", bg=SIDEBAR_BG, fg=TEXT_COLOR, 
                 font=('Segoe UI', 16, 'bold')).pack(anchor='w', padx=20, pady=(30, 40))

        self.nav_buttons = {}
        
        # Order: SVO Trim -> AVI Trim -> Batch Conversion
        nav_items = ["SVO Trim and Export", "AVI Trim and Export", "Batch Conversion"]
        
        for item in nav_items:
            lbl = tk.Label(self.sidebar, text=item, bg=SIDEBAR_BG, fg=TEXT_COLOR, font=('Segoe UI', 12), cursor='hand2')
            lbl.pack(anchor='w', padx=20, pady=10)
            lbl.bind("<Button-1>", lambda e, name=item: self.show_frame(name))
            self.nav_buttons[item] = lbl

        tk.Frame(self.sidebar, bg=BORDER_COLOR, height=1).pack(fill='x', padx=20, pady=20)

        doc_lbl = tk.Label(self.sidebar, text="Documentation", bg=SIDEBAR_BG, fg=TEXT_COLOR, font=('Segoe UI', 12), cursor='hand2')
        doc_lbl.pack(anchor='sw', side='bottom', padx=20, pady=30)
        doc_lbl.bind("<Button-1>", lambda e: self.show_frame("Documentation"))
        self.nav_buttons["Documentation"] = doc_lbl

    def show_frame(self, name):
        for frame in self.frames.values(): frame.grid_remove()
        self.frames[name].grid()

        for btn_name, lbl in self.nav_buttons.items():
            if btn_name == name: lbl.config(fg=BLUE_ACCENT)
            else: lbl.config(fg=TEXT_COLOR)

    # ── Views ──────────────────────────────────────────────────────────────
    def _create_batch_tab(self, parent):
        frame = tk.Frame(parent, bg=BG_COLOR)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        tl = tk.Frame(frame, bg=BG_COLOR)
        tl.grid(row=0, column=0, sticky='nw', padx=(0, 20))
        
        tk.Label(tl, text="Input Directory (.SVO/.SVO2)", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 5))
        row1 = tk.Frame(tl, bg=BG_COLOR)
        row1.pack(fill='x', pady=(0, 20))
        RoundedEntry(row1, width=400, textvariable=self.batch_input_dir).pack(side='left', padx=(0, 10))
        PillButton(row1, text="Browse", w=90, command=self.select_batch_input).pack(side='left')

        tk.Label(tl, text="Output Directory (.AVI)", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 5))
        row2 = tk.Frame(tl, bg=BG_COLOR)
        row2.pack(fill='x', pady=(0, 30))
        RoundedEntry(row2, width=400, textvariable=self.batch_output_dir).pack(side='left', padx=(0, 10))
        PillButton(row2, text="Browse", w=90, command=self.select_batch_output).pack(side='left')

        row3 = tk.Frame(tl, bg=BG_COLOR)
        row3.pack(anchor='w')
        self.batch_start_btn = PillButton(row3, text="Start", w=100, command=self.start_batch_conversion)
        self.batch_start_btn.pack(side='left', padx=(0, 15))
        self.batch_stop_btn = PillButton(row3, text="Stop", w=100, bg=STOP_BTN, hover_bg=STOP_HOVER, command=self.stop_conversion)
        self.batch_stop_btn.set_state('disabled')
        self.batch_stop_btn.pack(side='left')

        tr = tk.Frame(frame, bg=BG_COLOR)
        tr.grid(row=0, column=1, sticky='nsew', rowspan=2)
        tk.Label(tr, text="Log", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 5))
        
        log_container = tk.Frame(tr, bg=BG_COLOR, highlightthickness=1, highlightbackground=BORDER_COLOR)
        log_container.pack(fill='both', expand=True)
        self.batch_log_text = scrolledtext.ScrolledText(log_container, state='disabled', bg=PANEL_BG, fg=TEXT_COLOR, bd=0, font=('Consolas', 10))
        self.batch_log_text.pack(fill='both', expand=True, padx=5, pady=5)

        bot = tk.Frame(frame, bg=BG_COLOR)
        bot.grid(row=2, column=0, columnspan=2, sticky='sew', pady=(30, 0))
        
        # Single Graph Header with Percentage
        h1 = tk.Frame(bot, bg=BG_COLOR)
        h1.pack(fill='x', pady=(0, 5))
        tk.Label(h1, text="Single Conversion Progress", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold')).pack(side='left')
        self.batch_single_pct_lbl = tk.Label(h1, text="0%", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold'))
        self.batch_single_pct_lbl.pack(side='right')
        
        self.batch_single_graph = ProgressGraph(bot, GRAPH_PURPLE, GRAPH_PINK, title="")
        self.batch_single_graph.pack(fill='x', pady=(0, 20))

        # Overall Graph Header with Percentage
        h2 = tk.Frame(bot, bg=BG_COLOR)
        h2.pack(fill='x', pady=(0, 5))
        tk.Label(h2, text="Overall Conversion Progress", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold')).pack(side='left')
        self.batch_overall_pct_lbl = tk.Label(h2, text="0%", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold'))
        self.batch_overall_pct_lbl.pack(side='right')

        self.batch_overall_graph = ProgressGraph(bot, GRAPH_GREEN_DARK, GRAPH_GREEN_LIGHT, title="")
        self.batch_overall_graph.pack(fill='x')

        return "Batch Conversion", frame

    def _create_trim_tab(self, parent):
        frame = tk.Frame(parent, bg=BG_COLOR)
        frame.grid_columnconfigure(0, weight=3)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        # Left: Player & Entry Boxes
        left = tk.Frame(frame, bg=BG_COLOR)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 30))

        self.trim_video_label = tk.Label(left, text='Select an SVO file to preview', bg=PANEL_BG, fg=DIM_TEXT, font=('Segoe UI', 14),
                                         highlightthickness=1, highlightbackground=BORDER_COLOR)
        self.trim_video_label.pack(fill='both', expand=True)

        tl_frame = tk.Frame(left, bg=BG_COLOR)
        tl_frame.pack(fill='x', pady=(10, 5))
        self.trim_timeline_var = tk.DoubleVar()
        self.trim_timeline = ttk.Scale(tl_frame, from_=0, to=100, variable=self.trim_timeline_var, command=self._on_trim_seek)
        self.trim_timeline.pack(side='left', fill='x', expand=True)
        self.trim_time_lbl = tk.Label(tl_frame, text="00:00:00 / 00:00:00", bg=BG_COLOR, fg=DIM_TEXT, font=('Consolas', 10))
        self.trim_time_lbl.pack(side='right', padx=(10, 0))

        # Media Controls
        ctrls = tk.Frame(left, bg=BG_COLOR)
        ctrls.pack(pady=5)
        IconButton(ctrls, icon='mark_in', command=self._set_trim_start).pack(side='left', padx=10)
        self.trim_play_btn = IconButton(ctrls, icon='play', command=self._toggle_trim_playback)
        self.trim_play_btn.pack(side='left', padx=10)
        IconButton(ctrls, icon='capture', command=self._capture_trim_frame).pack(side='left', padx=10)
        IconButton(ctrls, icon='mark_out', command=self._set_trim_end).pack(side='left', padx=10)

        # Start/End Frame Editable Boxes
        entry_f = tk.Frame(left, bg=BG_COLOR)
        entry_f.pack(fill='x', pady=(10, 20))
        entry_f.grid_columnconfigure(0, weight=1)
        entry_f.grid_columnconfigure(1, weight=1)

        # Start Frame Box
        sf_container = tk.Frame(entry_f, bg=BG_COLOR)
        sf_container.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        tk.Label(sf_container, text="Start Frame", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10)).pack(anchor='w')
        sf_box = tk.Entry(sf_container, textvariable=self.start_frame_var, bg=FRAME_ENTRY_BG, fg="white", font=('Segoe UI', 24, 'bold'), 
                          justify='center', relief='flat', highlightthickness=1, highlightbackground=BORDER_COLOR)
        sf_box.pack(fill='x', ipady=12)
        sf_box.bind('<Return>', self._on_trim_start_entry)
        self.trim_start_time_lbl = tk.Label(sf_container, text="00:00:00", bg=TIME_ENTRY_BG, fg="white", font=('Consolas', 10, 'bold'), anchor='w', padx=5, pady=4)
        self.trim_start_time_lbl.pack(fill='x')

        # End Frame Box
        ef_container = tk.Frame(entry_f, bg=BG_COLOR)
        ef_container.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        tk.Label(ef_container, text="End Frame", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10)).pack(anchor='w')
        ef_box = tk.Entry(ef_container, textvariable=self.end_frame_var, bg=FRAME_ENTRY_BG, fg="white", font=('Segoe UI', 24, 'bold'), 
                          justify='center', relief='flat', highlightthickness=1, highlightbackground=BORDER_COLOR)
        ef_box.pack(fill='x', ipady=12)
        ef_box.bind('<Return>', self._on_trim_end_entry)
        self.trim_end_time_lbl = tk.Label(ef_container, text="00:00:00", bg=TIME_ENTRY_BG, fg="white", font=('Consolas', 10, 'bold'), anchor='w', padx=5, pady=4)
        self.trim_end_time_lbl.pack(fill='x')


        # Bottom Graph with Percentage
        bot = tk.Frame(left, bg=BG_COLOR)
        bot.pack(fill='x', side='bottom')
        
        h_trim = tk.Frame(bot, bg=BG_COLOR)
        h_trim.pack(fill='x', pady=(0, 5))
        tk.Label(h_trim, text="Overall Conversion Progress", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold')).pack(side='left')
        self.trim_overall_pct_lbl = tk.Label(h_trim, text="0%", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold'))
        self.trim_overall_pct_lbl.pack(side='right')
        
        self.trim_overall_graph = ProgressGraph(bot, GRAPH_GREEN_DARK, GRAPH_GREEN_LIGHT, title="", height=60)
        self.trim_overall_graph.pack(fill='x')


        # Right: Output Options
        right = tk.Frame(frame, bg=BG_COLOR)
        right.grid(row=0, column=1, sticky='nsew')

        tk.Label(right, text="Input SVO File", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 5))
        r1 = tk.Frame(right, bg=BG_COLOR)
        r1.pack(fill='x', pady=(0, 20))
        RoundedEntry(r1, width=250, textvariable=self.trim_input_file).pack(side='left', fill='x', expand=True, padx=(0, 10))
        PillButton(r1, text="Browse", w=80, command=self._select_trim_input).pack(side='left')

        tk.Label(right, text="Output Directory", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 5))
        r2 = tk.Frame(right, bg=BG_COLOR)
        r2.pack(fill='x', pady=(0, 30))
        RoundedEntry(r2, width=250, textvariable=self.trim_output_dir).pack(side='left', fill='x', expand=True, padx=(0, 10))
        PillButton(r2, text="Browse", w=80, command=self._select_trim_output).pack(side='left')

        # Side selector for SVO Export
        tk.Label(right, text="Export Side:", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 5))
        sf = tk.Frame(right, bg=BG_COLOR)
        sf.pack(anchor='w', pady=(0, 10))
        CanvasRadio(sf, text='Left', variable=self.svo_export_side, value='left', w=70).pack(side='left')
        CanvasRadio(sf, text='Right', variable=self.svo_export_side, value='right', w=80).pack(side='left')
        CanvasRadio(sf, text='Both (full)', variable=self.svo_export_side, value='both', w=100).pack(side='left')

        # Side selector for SVO Preview
        tk.Label(right, text="Preview Side:", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 5))
        pf = tk.Frame(right, bg=BG_COLOR)
        pf.pack(anchor='w', pady=(0, 20))
        CanvasRadio(pf, text='Left', variable=self.svo_preview_side, value='left', w=70, command=self._refresh_trim_preview).pack(side='left')
        CanvasRadio(pf, text='Right', variable=self.svo_preview_side, value='right', w=80, command=self._refresh_trim_preview).pack(side='left')
        CanvasRadio(pf, text='Full SBS', variable=self.svo_preview_side, value='full', w=100, command=self._refresh_trim_preview).pack(side='left')

        r3 = tk.Frame(right, bg=BG_COLOR)
        r3.pack(anchor='w', fill='x', pady=(0, 20))
        self.trim_start_btn = PillButton(r3, text="Convert to AVI", w=130, command=self._start_trim_conversion)
        self.trim_start_btn.pack(side='left', padx=(0, 10))
        self.trim_export_btn = PillButton(r3, text="Export Images", w=130, command=self._start_trim_export)
        self.trim_export_btn.pack(side='left', padx=(0, 10))
        
        self.trim_stop_btn = PillButton(right, text="Stop", w=100, bg=STOP_BTN, hover_bg=STOP_HOVER, command=self.stop_conversion)
        self.trim_stop_btn.set_state('disabled')
        self.trim_stop_btn.pack(anchor='w', pady=(0, 30))

        # Log
        tk.Label(right, text="Log", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 5))
        log_c = tk.Frame(right, bg=BG_COLOR, highlightthickness=1, highlightbackground=BORDER_COLOR)
        log_c.pack(fill='both', expand=True)
        self.trim_log_text = scrolledtext.ScrolledText(log_c, state='disabled', bg=PANEL_BG, fg=TEXT_COLOR, bd=0, font=('Consolas', 10))
        self.trim_log_text.pack(fill='both', expand=True, padx=5, pady=5)

        return "SVO Trim and Export", frame

    def _create_avi_tab(self, parent):
        frame = tk.Frame(parent, bg=BG_COLOR)
        frame.grid_columnconfigure(0, weight=3)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        left = tk.Frame(frame, bg=BG_COLOR)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 30))

        self.avi_video_label = tk.Label(left, text='Select an AVI file to preview', bg=PANEL_BG, fg=DIM_TEXT, font=('Segoe UI', 14),
                                        highlightthickness=1, highlightbackground=BORDER_COLOR)
        self.avi_video_label.pack(fill='both', expand=True)

        tl_frame = tk.Frame(left, bg=BG_COLOR)
        tl_frame.pack(fill='x', pady=(10, 5))
        self.avi_timeline_var = tk.DoubleVar()
        self.avi_timeline = ttk.Scale(tl_frame, from_=0, to=100, variable=self.avi_timeline_var, command=self._on_avi_seek)
        self.avi_timeline.pack(side='left', fill='x', expand=True)
        self.avi_time_lbl = tk.Label(tl_frame, text="00:00:00 / 00:00:00", bg=BG_COLOR, fg=DIM_TEXT, font=('Consolas', 10))
        self.avi_time_lbl.pack(side='right', padx=(10, 0))

        # Media Controls
        ctrls = tk.Frame(left, bg=BG_COLOR)
        ctrls.pack(pady=5)
        IconButton(ctrls, icon='mark_in', command=self._set_avi_start).pack(side='left', padx=10)
        self.avi_play_btn = IconButton(ctrls, icon='play', command=self._toggle_avi_playback)
        self.avi_play_btn.pack(side='left', padx=10)
        IconButton(ctrls, icon='capture', command=self._capture_avi_frame).pack(side='left', padx=10)
        IconButton(ctrls, icon='mark_out', command=self._set_avi_end).pack(side='left', padx=10)

        # Start/End Frame Editable Boxes
        entry_f = tk.Frame(left, bg=BG_COLOR)
        entry_f.pack(fill='x', pady=(10, 20))
        entry_f.grid_columnconfigure(0, weight=1)
        entry_f.grid_columnconfigure(1, weight=1)

        sf_container = tk.Frame(entry_f, bg=BG_COLOR)
        sf_container.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        tk.Label(sf_container, text="Start Frame", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10)).pack(anchor='w')
        sf_box = tk.Entry(sf_container, textvariable=self.avi_start_frame_var, bg=FRAME_ENTRY_BG, fg="white", font=('Segoe UI', 24, 'bold'), 
                          justify='center', relief='flat', highlightthickness=1, highlightbackground=BORDER_COLOR)
        sf_box.pack(fill='x', ipady=12)
        sf_box.bind('<Return>', self._on_avi_start_entry)
        self.avi_start_time_lbl = tk.Label(sf_container, text="00:00:00", bg=TIME_ENTRY_BG, fg="white", font=('Consolas', 10, 'bold'), anchor='w', padx=5, pady=4)
        self.avi_start_time_lbl.pack(fill='x')

        ef_container = tk.Frame(entry_f, bg=BG_COLOR)
        ef_container.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        tk.Label(ef_container, text="End Frame", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10)).pack(anchor='w')
        ef_box = tk.Entry(ef_container, textvariable=self.avi_end_frame_var, bg=FRAME_ENTRY_BG, fg="white", font=('Segoe UI', 24, 'bold'), 
                          justify='center', relief='flat', highlightthickness=1, highlightbackground=BORDER_COLOR)
        ef_box.pack(fill='x', ipady=12)
        ef_box.bind('<Return>', self._on_avi_end_entry)
        self.avi_end_time_lbl = tk.Label(ef_container, text="00:00:00", bg=TIME_ENTRY_BG, fg="white", font=('Consolas', 10, 'bold'), anchor='w', padx=5, pady=4)
        self.avi_end_time_lbl.pack(fill='x')


        # Bottom Graph with Percentage
        bot = tk.Frame(left, bg=BG_COLOR)
        bot.pack(fill='x', side='bottom')
        
        h_avi = tk.Frame(bot, bg=BG_COLOR)
        h_avi.pack(fill='x', pady=(0, 5))
        tk.Label(h_avi, text="Overall Conversion Progress", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold')).pack(side='left')
        self.avi_overall_pct_lbl = tk.Label(h_avi, text="0%", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold'))
        self.avi_overall_pct_lbl.pack(side='right')
        
        self.avi_overall_graph = ProgressGraph(bot, GRAPH_GREEN_DARK, GRAPH_GREEN_LIGHT, title="", height=60)
        self.avi_overall_graph.pack(fill='x')


        # Right: Output Options
        right = tk.Frame(frame, bg=BG_COLOR)
        right.grid(row=0, column=1, sticky='nsew')

        tk.Label(right, text="Input AVI File", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 5))
        r1 = tk.Frame(right, bg=BG_COLOR)
        r1.pack(fill='x', pady=(0, 20))
        RoundedEntry(r1, width=250, textvariable=self.avi_input_file).pack(side='left', fill='x', expand=True, padx=(0, 10))
        PillButton(r1, text="Browse", w=80, command=self._select_avi_input).pack(side='left')

        tk.Label(right, text="Output Directory", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 5))
        r2 = tk.Frame(right, bg=BG_COLOR)
        r2.pack(fill='x', pady=(0, 20))
        RoundedEntry(r2, width=250, textvariable=self.avi_output_dir).pack(side='left', fill='x', expand=True, padx=(0, 10))
        PillButton(r2, text="Browse", w=80, command=self._select_avi_output).pack(side='left')

        # Side selector for AVI Export
        tk.Label(right, text="Export Side:", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 5))
        sf = tk.Frame(right, bg=BG_COLOR)
        sf.pack(anchor='w', pady=(0, 10))
        CanvasRadio(sf, text='Left', variable=self.avi_export_side, value='left', w=70).pack(side='left')
        CanvasRadio(sf, text='Right', variable=self.avi_export_side, value='right', w=80).pack(side='left')
        CanvasRadio(sf, text='Both (full)', variable=self.avi_export_side, value='both', w=100).pack(side='left')

        # Side selector for AVI Preview
        tk.Label(right, text="Preview Side:", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 5))
        pf = tk.Frame(right, bg=BG_COLOR)
        pf.pack(anchor='w', pady=(0, 20))
        CanvasRadio(pf, text='Left', variable=self.avi_preview_side, value='left', w=70, command=self._refresh_avi_preview).pack(side='left')
        CanvasRadio(pf, text='Right', variable=self.avi_preview_side, value='right', w=80, command=self._refresh_avi_preview).pack(side='left')
        CanvasRadio(pf, text='Full SBS', variable=self.avi_preview_side, value='full', w=100, command=self._refresh_avi_preview).pack(side='left')

        r3 = tk.Frame(right, bg=BG_COLOR)
        r3.pack(anchor='w', fill='x', pady=(0, 20))
        self.avi_start_btn = PillButton(r3, text="Export Images", w=130, command=self._start_avi_export)
        self.avi_start_btn.pack(side='left', padx=(0, 10))
        self.avi_stop_btn = PillButton(r3, text="Stop", w=100, bg=STOP_BTN, hover_bg=STOP_HOVER, command=self.stop_conversion)
        self.avi_stop_btn.set_state('disabled')
        self.avi_stop_btn.pack(side='left')

        # Log
        tk.Label(right, text="Log", bg=BG_COLOR, fg=TEXT_COLOR, font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 5))
        log_c = tk.Frame(right, bg=BG_COLOR, highlightthickness=1, highlightbackground=BORDER_COLOR)
        log_c.pack(fill='both', expand=True)
        self.avi_log_text = scrolledtext.ScrolledText(log_c, state='disabled', bg=PANEL_BG, fg=TEXT_COLOR, bd=0, font=('Consolas', 10))
        self.avi_log_text.pack(fill='both', expand=True, padx=5, pady=5)

        return "AVI Trim and Export", frame

    def _create_doc_tab(self, parent):
        frame = tk.Frame(parent, bg=BG_COLOR)
        dt = scrolledtext.ScrolledText(frame, state='normal', wrap='word', bg=PANEL_BG, fg=TEXT_COLOR, relief='flat', bd=0, font=('Segoe UI', 12))
        dt.pack(fill='both', expand=True, padx=20, pady=20)

        dt.insert('end', 'SVO Converter Suit - Documentation\n\n', ('h1',))
        dt.insert('end', 'Welcome to the modernized SVO Converter. This tool allows for batch processing of SVO/SVO2 files to AVI format, as well as specific trimming and image extraction from both SVO and previously generated AVI files.\n\n')
        dt.insert('end', 'Use the left sidebar to navigate between modules. The real-time progress graphs map the speed and consistency of the conversion process. Any errors encountered will be marked with a vertical red line in the graphs.\n')
        dt.insert('end', 'Complete documentation is available at the SVO converter suit GitHub repository linked below. This tool was developed as a part of the PhD programme of Samitha Thilakarathna, DTU Aqua. The main script of converting SVO to AVI is sourced from Stereolabs github repository lined below..\n\n')
        
        dt.tag_config('h1', font=('Segoe UI', 20, 'bold'), foreground=BLUE_ACCENT, spacing3=10)
        dt.config(state='disabled')
        return "Documentation", frame


    # ── Media Helpers ──────────────────────────────────────────────────────
    def _format_time(self, frame, fps):
        if fps and fps > 0:
            return str(datetime.timedelta(seconds=int(frame / fps)))
        return "00:00:00"

    def _overlay_frame_num(self, rgb_array, frame_num):
        text = f'Frame: {frame_num}'
        cv2.putText(rgb_array, text, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(rgb_array, text, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (80, 220, 80), 2, cv2.LINE_AA)


    # ── Logic Integration ──────────────────────────────────────────────────
    def select_batch_input(self):
        d = filedialog.askdirectory()
        if d: self.batch_input_dir.set(d)
    def select_batch_output(self):
        d = filedialog.askdirectory()
        if d: self.batch_output_dir.set(d)
    def _select_trim_input(self):
        p = filedialog.askopenfilename(filetypes=[('SVO', '*.svo *.svo2')])
        if p: self.trim_input_file.set(p); self._load_trim_video(p)
    def _select_trim_output(self):
        d = filedialog.askdirectory()
        if d: self.trim_output_dir.set(d)
    def _select_avi_input(self):
        p = filedialog.askopenfilename(filetypes=[('AVI', '*.avi')])
        if p: self.avi_input_file.set(p); self._load_avi_video(p)
    def _select_avi_output(self):
        d = filedialog.askdirectory()
        if d: self.avi_output_dir.set(d)

    def log(self, message, target='batch'):
        self.log_queue.put((message, target))

    def log_error(self, target, pct):
        self.progress_queue.put((target, pct, 0.0, True))

    def process_queues(self):
        try:
            while not self.log_queue.empty():
                msg, target = self.log_queue.get_nowait()
                w = self.batch_log_text if target == 'batch' else (self.trim_log_text if target == 'trim' else self.avi_log_text)
                w.config(state='normal')
                w.insert('end', msg)
                w.see('end')
                w.config(state='disabled')
        except queue.Empty: pass

        try:
            while not self.progress_queue.empty():
                target, pct, speed, is_err = self.progress_queue.get_nowait()
                if target == 'batch_single':
                    if is_err: 
                        self.batch_single_graph.mark_error(pct)
                    else: 
                        self.batch_single_graph.update_graph(pct, speed)
                        self.batch_single_pct_lbl.config(text=f"{int(pct)}%")
                elif target == 'batch_overall':
                    if is_err: 
                        self.batch_overall_graph.mark_error(pct)
                    else: 
                        self.batch_overall_graph.update_graph(pct, speed)
                        self.batch_overall_pct_lbl.config(text=f"{int(pct)}%")
                elif target == 'trim':
                    if is_err: 
                        self.trim_overall_graph.mark_error(pct)
                    else: 
                        self.trim_overall_graph.update_graph(pct, speed)
                        self.trim_overall_pct_lbl.config(text=f"{int(pct)}%")
                elif target == 'avi':
                    if is_err: 
                        self.avi_overall_graph.mark_error(pct)
                    else: 
                        self.avi_overall_graph.update_graph(pct, speed)
                        self.avi_overall_pct_lbl.config(text=f"{int(pct)}%")
        except queue.Empty: pass
        finally:
            self.root.after(50, self.process_queues)

    def stop_conversion(self):
        self.log("Stopping process...\n", "batch")
        self.log("Stopping process...\n", "trim")
        self.log("Stopping process...\n", "avi")
        self.stop_event.set()
        if self.running_process: self.running_process.terminate()

    # ── Speed tracker ──────────────────────────────────────────────────────
    class Tracker:
        def __init__(self):
            self.last_time = time.time()
            self.last_pct = 0.0
            self.speed = 0.0
        def update(self, current_pct):
            now = time.time()
            dt = now - self.last_time
            dp = current_pct - self.last_pct
            if dt > 0:
                raw_s = dp / dt
                self.speed = 0.2 * raw_s + 0.8 * self.speed 
            self.last_time = now
            self.last_pct = current_pct
            return self.speed

    # ── Batch Threading ────────────────────────────────────────────────────
    def start_batch_conversion(self):
        self.batch_start_btn.set_state('disabled')
        self.batch_stop_btn.set_state('normal')
        self.stop_event.clear()
        
        self.batch_single_graph.clear()
        self.batch_overall_graph.clear()
        self.batch_single_pct_lbl.config(text="0%")
        self.batch_overall_pct_lbl.config(text="0%")
        
        threading.Thread(target=self._run_batch, daemon=True).start()

    def _run_batch(self):
        in_d = self.batch_input_dir.get()
        out_d = self.batch_output_dir.get()
        if not os.path.isdir(in_d) or not os.path.isdir(out_d):
            self.log("Invalid directories.\n", "batch")
            self.root.after(0, lambda: self._reset_batch_btns())
            return

        files = [f for f in os.listdir(in_d) if f.endswith(('.svo', '.svo2'))]
        total_f = len(files)
        if total_f == 0:
            self.log("No SVO files found.\n", "batch")
            self.root.after(0, lambda: self._reset_batch_btns())
            return

        overall_trk = self.Tracker()
        for i, f in enumerate(files):
            if self.stop_event.is_set(): break
            self.log(f"Processing {f}...\n", "batch")
            
            self.batch_single_graph.clear()
            self.root.after(0, lambda: self.batch_single_pct_lbl.config(text="0%"))
            single_trk = self.Tracker()
            
            base_name = os.path.splitext(f)[0]
            out_file = os.path.join(out_d, f'{base_name}.avi')
            
            cmd = ['python', '-u', 'svo_export.py', '--mode', '0', 
                   '--input_svo_file', os.path.join(in_d, f), 
                   '--output_avi_file', out_file]
            try:
                cf = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                self.running_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=cf)
                for line in iter(self.running_process.stdout.readline, ''):
                    if self.stop_event.is_set(): break
                    m = re.search(r'(\d+)%', line)
                    if m:
                        pct = int(m.group(1))
                        self.progress_queue.put(('batch_single', pct, single_trk.update(pct), False))
                        self.progress_queue.put(('batch_overall', ((i * 100) + pct) / total_f, overall_trk.update(((i * 100) + pct) / total_f), False))
                    elif 'Converting SVO' not in line.strip():
                        self.log(line, "batch")
                        if "Error" in line or "Exception" in line:
                            self.log_error('batch_single', single_trk.last_pct)
                            self.log_error('batch_overall', overall_trk.last_pct)
                rc = self.running_process.wait()
                if rc != 0 and not self.stop_event.is_set(): self.log_error('batch_single', single_trk.last_pct)
            except Exception as e:
                self.log(f"Fatal error: {e}\n", "batch")
                self.log_error('batch_single', single_trk.last_pct)
            finally:
                self.running_process = None

        self.log("Batch finished.\n", "batch")
        self.root.after(0, lambda: self._reset_batch_btns())

    def _reset_batch_btns(self):
        self.batch_start_btn.set_state('normal')
        self.batch_stop_btn.set_state('disabled')


    # ── SVO Trim & Export Player Logic ─────────────────────────────────────
    def _load_trim_video(self, path):
        if not ZED_AVAILABLE:
            self.log("ZED SDK not available.\n", "trim")
            return
        if self.trim_video_capture: self.trim_video_capture.close()
        
        zed = sl.Camera()
        ip = sl.InitParameters()
        ip.set_from_svo_file(path)
        ip.svo_real_time_mode = False
        if zed.open(ip) != sl.ERROR_CODE.SUCCESS:
            self.trim_video_label.config(text="Error loading SVO", image='')
            return
            
        self.trim_video_capture = zed
        self.trim_total_frames = zed.get_svo_number_of_frames()
        self.trim_fps = zed.get_camera_information().camera_configuration.fps or 30
        self.trim_timeline.config(to=self.trim_total_frames-1)
        
        self._on_trim_seek(0)
        self.trim_timeline_var.set(0)
        self._set_trim_start()
        
        self._on_trim_seek(self.trim_total_frames - 1)
        self.trim_timeline_var.set(self.trim_total_frames - 1)
        self._set_trim_end()
        self._on_trim_seek(0)

    def _refresh_trim_preview(self):
        if self.trim_video_capture:
            self._on_trim_seek(self.trim_timeline_var.get())

    def _on_trim_seek(self, val):
        n = int(float(val))
        if self.trim_video_capture:
            self.trim_video_capture.set_svo_position(n)
            z_img = sl.Mat()
            if self.trim_video_capture.grab() == sl.ERROR_CODE.SUCCESS:
                
                # Check preview side option
                side = self.svo_preview_side.get()
                if side == 'left':
                    self.trim_video_capture.retrieve_image(z_img, sl.VIEW.LEFT)
                elif side == 'right':
                    self.trim_video_capture.retrieve_image(z_img, sl.VIEW.RIGHT)
                else:
                    self.trim_video_capture.retrieve_image(z_img, sl.VIEW.SIDE_BY_SIDE)
                    
                rgb = cv2.cvtColor(z_img.get_data(), cv2.COLOR_BGRA2RGB)
                self._overlay_frame_num(rgb, n)
                self._show_frame_on_label(self.trim_video_label, rgb)
        
        t_cur = self._format_time(n, self.trim_fps)
        t_tot = self._format_time(self.trim_total_frames, self.trim_fps)
        self.trim_time_lbl.config(text=f"{t_cur} / {t_tot}")

    def _show_frame_on_label(self, lbl, rgb):
        img = Image.fromarray(rgb)
        w, h = lbl.winfo_width(), lbl.winfo_height()
        if w > 10 and h > 10:
            img.thumbnail((w, h), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        lbl.config(image=photo)
        lbl.image = photo

    def _toggle_trim_playback(self):
        if self.is_playing:
            self.is_playing = False
            self.trim_play_btn.set_icon('play')
        else:
            self.is_playing = True
            self.trim_play_btn.set_icon('pause')
            self._trim_play_loop()

    def _trim_play_loop(self):
        if not self.is_playing: return
        nxt = int(self.trim_timeline_var.get()) + 1
        if nxt < self.trim_total_frames:
            self.trim_timeline_var.set(nxt)
            self._on_trim_seek(nxt)
            delay = int(1000/self.trim_fps) if self.trim_fps else 33
            self.root.after(delay, self._trim_play_loop)
        else:
            self._toggle_trim_playback()

    def _set_trim_start(self):
        self.trim_start_frame = int(self.trim_timeline_var.get())
        self.start_frame_var.set(str(self.trim_start_frame))
        self.trim_start_time_lbl.config(text=self._format_time(self.trim_start_frame, self.trim_fps))
        self.log(f"Mark In: {self.trim_start_frame}\n", "trim")

    def _set_trim_end(self):
        self.trim_end_frame = int(self.trim_timeline_var.get())
        self.end_frame_var.set(str(self.trim_end_frame))
        self.trim_end_time_lbl.config(text=self._format_time(self.trim_end_frame, self.trim_fps))
        self.log(f"Mark Out: {self.trim_end_frame}\n", "trim")
        
    def _on_trim_start_entry(self, event=None):
        try:
            n = int(self.start_frame_var.get())
            if 0 <= n < self.trim_total_frames:
                self.trim_timeline_var.set(n)
                self._on_trim_seek(n)
                self._set_trim_start()
            else: self.start_frame_var.set(str(self.trim_start_frame))
        except ValueError: self.start_frame_var.set(str(self.trim_start_frame))

    def _on_trim_end_entry(self, event=None):
        try:
            n = int(self.end_frame_var.get())
            if self.trim_start_frame <= n < self.trim_total_frames:
                self.trim_timeline_var.set(n)
                self._on_trim_seek(n)
                self._set_trim_end()
            else: self.end_frame_var.set(str(self.trim_end_frame))
        except ValueError: self.end_frame_var.set(str(self.trim_end_frame))

    def _capture_trim_frame(self):
        n = int(self.trim_timeline_var.get())
        self.log(f"Captured frame {n}\n", "trim")

    def _start_trim_conversion(self):
        self.trim_start_btn.set_state('disabled')
        self.trim_export_btn.set_state('disabled')
        self.trim_stop_btn.set_state('normal')
        self.stop_event.clear()
        
        self.trim_overall_graph.clear()
        self.trim_overall_pct_lbl.config(text="0%")
        
        threading.Thread(target=self._run_trim_conv, daemon=True).start()

    def _run_trim_conv(self):
        self.log("Starting SVO Conversion to AVI...\n", "trim")
        in_file = self.trim_input_file.get()
        out_dir = self.trim_output_dir.get()
        
        if not os.path.isfile(in_file) or not os.path.isdir(out_dir):
            self.log("Error: Invalid paths.\n", "trim")
            self.root.after(0, lambda: self._reset_trim_btns())
            return

        base = os.path.splitext(os.path.basename(in_file))[0]
        out_file = os.path.join(out_dir, f'{base}_trimmed_{self.trim_start_frame}_{self.trim_end_frame}.avi')

        cmd = ['python', '-u', 'svo_export.py', '--mode', '0',
               '--input_svo_file', in_file,
               '--output_avi_file', out_file,
               '--start_frame', str(self.trim_start_frame),
               '--end_frame',   str(self.trim_end_frame)]

        trk = self.Tracker()
        try:
            cf = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            self.running_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=cf)
            for line in iter(self.running_process.stdout.readline, ''):
                if self.stop_event.is_set(): break
                m = re.search(r'(\d+)%', line)
                if m:
                    pct = int(m.group(1))
                    self.progress_queue.put(('trim', pct, trk.update(pct), False))
                elif 'Converting SVO' not in line.strip():
                    self.log(line, "trim")
            rc = self.running_process.wait()
            if rc == 0 and not self.stop_event.is_set():
                self.progress_queue.put(('trim', 100, 0, False))
                self.log(f'SUCCESS → {out_file}\n', "trim")
            elif rc != 0:
                self.log(f'ERROR: exit code {rc}.\n', "trim")
                self.log_error('trim', trk.last_pct)
        except Exception as e:
            self.log(f'FATAL ERROR: {e}\n', "trim")
            self.log_error('trim', trk.last_pct)
        finally:
            self.running_process = None
        
        self.root.after(0, lambda: self._reset_trim_btns())

    def _start_trim_export(self):
        in_file = self.trim_input_file.get()
        out_dir = self.trim_output_dir.get()
        if not os.path.isfile(in_file) or not os.path.isdir(out_dir):
            self.log('Error: Please select a valid input file and output directory.\n', "trim")
            return
            
        self.trim_start_btn.set_state('disabled')
        self.trim_export_btn.set_state('disabled')
        self.trim_stop_btn.set_state('normal')
        self.stop_event.clear()
        
        self.trim_overall_graph.clear()
        self.trim_overall_pct_lbl.config(text="0%")
        
        threading.Thread(target=self._run_image_export_thread, daemon=True).start()

    def _run_image_export_thread(self):
        in_file = self.trim_input_file.get()
        out_dir = self.trim_output_dir.get()
        side    = self.svo_export_side.get()
        
        base = os.path.splitext(os.path.basename(in_file))[0]
        image_folder = os.path.join(out_dir, f'{base}_frames_{side}_{self.trim_start_frame}_{self.trim_end_frame}')
        os.makedirs(image_folder, exist_ok=True)
        
        self.log(f'Exporting images from SVO (Side: {side})\nSaving to: {image_folder}\n', "trim")

        zed = sl.Camera()
        ip  = sl.InitParameters()
        ip.set_from_svo_file(in_file)
        ip.svo_real_time_mode = False
        if zed.open(ip) != sl.ERROR_CODE.SUCCESS:
            self.log('Error: Could not open SVO file.\n', "trim")
            self.root.after(0, lambda: self._reset_trim_btns())
            return

        zed_img = sl.Mat()
        total = max(1, self.trim_end_frame - self.trim_start_frame)
        trk = self.Tracker()
        
        view_mode = sl.VIEW.LEFT
        if side == 'right': view_mode = sl.VIEW.RIGHT
        elif side == 'both': view_mode = sl.VIEW.SIDE_BY_SIDE

        try:
            for i, fn in enumerate(range(self.trim_start_frame, self.trim_end_frame + 1)):
                if self.stop_event.is_set():
                    self.log('Stopped by user.\n', "trim")
                    break
                zed.set_svo_position(fn)
                if zed.grab() == sl.ERROR_CODE.SUCCESS:
                    zed.retrieve_image(zed_img, view_mode)
                    rgb = cv2.cvtColor(zed_img.get_data(), cv2.COLOR_BGRA2RGB)
                    Image.fromarray(rgb).save(os.path.join(image_folder, f'frame_{str(fn).zfill(6)}.png'))
                
                pct = (i / total) * 100
                self.progress_queue.put(('trim', pct, trk.update(pct), False))
                
        except Exception as e:
            self.log(f'Error during SVO export: {e}\n', "trim")
            self.log_error('trim', trk.last_pct)
        finally:
            zed.close()

        if not self.stop_event.is_set():
            self.progress_queue.put(('trim', 100, 0, False))
            self.log(f'SUCCESS: SVO image sequence exported.\n', "trim")
            
        self.root.after(0, lambda: self._reset_trim_btns())

    def _reset_trim_btns(self):
        self.trim_start_btn.set_state('normal')
        self.trim_export_btn.set_state('normal')
        self.trim_stop_btn.set_state('disabled')


    # ── AVI Player Logic ───────────────────────────────────────────────────
    def _load_avi_video(self, path):
        if self.avi_video_capture: self.avi_video_capture.release()
        cap = cv2.VideoCapture(path)
        if not cap.isOpened(): return
        self.avi_video_capture = cap
        self.avi_total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.avi_fps = cap.get(cv2.CAP_PROP_FPS) or 30
        self.avi_timeline.config(to=self.avi_total_frames-1)
        
        self._on_avi_seek(0)
        self.avi_timeline_var.set(0)
        self._set_avi_start()
        
        self._on_avi_seek(self.avi_total_frames - 1)
        self.avi_timeline_var.set(self.avi_total_frames - 1)
        self._set_avi_end()
        self._on_avi_seek(0)

    def _refresh_avi_preview(self):
        if self.avi_video_capture:
            self._on_avi_seek(self.avi_timeline_var.get())

    def _on_avi_seek(self, val):
        n = int(float(val))
        if self.avi_video_capture:
            self.avi_video_capture.set(cv2.CAP_PROP_POS_FRAMES, n)
            ret, frame = self.avi_video_capture.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Crop logic based on preview side
                side = self.avi_preview_side.get()
                w = frame.shape[1]
                if side == 'left': frame = frame[:, :w//2]
                elif side == 'right': frame = frame[:, w//2:]
                
                self._overlay_frame_num(frame, n)
                self._show_frame_on_label(self.avi_video_label, frame)
        
        t_cur = self._format_time(n, self.avi_fps)
        t_tot = self._format_time(self.avi_total_frames, self.avi_fps)
        self.avi_time_lbl.config(text=f"{t_cur} / {t_tot}")

    def _toggle_avi_playback(self):
        if self.avi_is_playing:
            self.avi_is_playing = False
            self.avi_play_btn.set_icon('play')
        else:
            self.avi_is_playing = True
            self.avi_play_btn.set_icon('pause')
            self._avi_play_loop()

    def _avi_play_loop(self):
        if not self.avi_is_playing: return
        nxt = int(self.avi_timeline_var.get()) + 1
        if nxt < self.avi_total_frames:
            self.avi_timeline_var.set(nxt)
            self._on_avi_seek(nxt)
            self.root.after(int(1000/self.avi_fps), self._avi_play_loop)
        else:
            self._toggle_avi_playback()

    def _set_avi_start(self): 
        self.avi_start_frame = int(self.avi_timeline_var.get())
        self.avi_start_frame_var.set(str(self.avi_start_frame))
        self.avi_start_time_lbl.config(text=self._format_time(self.avi_start_frame, self.avi_fps))
        self.log(f"Mark In: {self.avi_start_frame}\n", "avi")

    def _set_avi_end(self): 
        self.avi_end_frame = int(self.avi_timeline_var.get())
        self.avi_end_frame_var.set(str(self.avi_end_frame))
        self.avi_end_time_lbl.config(text=self._format_time(self.avi_end_frame, self.avi_fps))
        self.log(f"Mark Out: {self.avi_end_frame}\n", "avi")
        
    def _on_avi_start_entry(self, event=None):
        try:
            n = int(self.avi_start_frame_var.get())
            if 0 <= n < self.avi_total_frames:
                self.avi_timeline_var.set(n)
                self._on_avi_seek(n)
                self._set_avi_start()
            else: self.avi_start_frame_var.set(str(self.avi_start_frame))
        except ValueError: self.avi_start_frame_var.set(str(self.avi_start_frame))

    def _on_avi_end_entry(self, event=None):
        try:
            n = int(self.avi_end_frame_var.get())
            if self.avi_start_frame <= n < self.avi_total_frames:
                self.avi_timeline_var.set(n)
                self._on_avi_seek(n)
                self._set_avi_end()
            else: self.avi_end_frame_var.set(str(self.avi_end_frame))
        except ValueError: self.avi_end_frame_var.set(str(self.avi_end_frame))

    def _capture_avi_frame(self): 
        n = int(self.avi_timeline_var.get())
        self.log(f"Captured AVI frame {n}\n", "avi")

    def _start_avi_export(self):
        in_file = self.avi_input_file.get()
        out_dir = self.avi_output_dir.get()
        if not os.path.isfile(in_file) or not os.path.isdir(out_dir):
            self.log('Error: Please select a valid AVI file and output directory.\n', 'avi')
            return
            
        self.avi_start_btn.set_state('disabled')
        self.avi_stop_btn.set_state('normal')
        self.stop_event.clear()
        
        self.avi_overall_graph.clear()
        self.avi_overall_pct_lbl.config(text="0%")
        
        threading.Thread(target=self._run_avi_export, daemon=True).start()

    def _run_avi_export(self):
        in_file = self.avi_input_file.get()
        out_dir = self.avi_output_dir.get()
        side = self.avi_export_side.get()
        base = os.path.splitext(os.path.basename(in_file))[0]
        image_folder = os.path.join(out_dir, f'{base}_{side}_{self.avi_start_frame}_{self.avi_end_frame}')
        os.makedirs(image_folder, exist_ok=True)

        self.log(f"Starting AVI Image Export (Side: {side})...\nOutput: {image_folder}\n", "avi")
        
        cap = cv2.VideoCapture(in_file)
        if not cap.isOpened():
            self.log('Error: Could not open AVI file.\n', 'avi')
            self.root.after(0, lambda: self._reset_avi_btns())
            return

        total = max(1, self.avi_end_frame - self.avi_start_frame)
        trk = self.Tracker()
        errors = 0

        try:
            for i, fn in enumerate(range(self.avi_start_frame, self.avi_end_frame + 1)):
                if self.stop_event.is_set():
                    self.log('Stopped by user.\n', 'avi')
                    break

                cap.set(cv2.CAP_PROP_POS_FRAMES, fn)
                ret, frame = cap.read()
                if not ret:
                    errors += 1
                    if errors > 10:
                        self.log(f'Too many read errors, aborting at frame {fn}.\n', 'avi')
                        self.log_error('avi', trk.last_pct)
                        break
                    continue

                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                w = frame.shape[1]
                if side == 'left': frame = frame[:, :w // 2]
                elif side == 'right': frame = frame[:, w // 2:]

                out_path = os.path.join(image_folder, f'frame_{str(fn).zfill(6)}.png')
                Image.fromarray(frame).save(out_path)

                pct = (i / total) * 100
                self.progress_queue.put(('avi', pct, trk.update(pct), False))

        except Exception as e:
            self.log(f'Error during AVI export: {e}\n', 'avi')
            self.log_error('avi', trk.last_pct)
        finally:
            cap.release()

        if not self.stop_event.is_set():
            self.progress_queue.put(('avi', 100, 0, False))
            self.log(f"SUCCESS: {total - errors} frames exported.\n", "avi")
            
        self.root.after(0, lambda: self._reset_avi_btns())

    def _reset_avi_btns(self):
        self.avi_start_btn.set_state('normal')
        self.avi_stop_btn.set_state('disabled')


if __name__ == '__main__':
    root = tk.Tk()
    app = SVOConverterApp(root)
    root.mainloop()
