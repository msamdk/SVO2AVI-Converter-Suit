import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, font
import os
import subprocess
import threading
import queue
import re
from PIL import Image, ImageTk
import datetime
import webbrowser

# ZED SDK specific imports
try:
    import pyzed.sl as sl
    import cv2 # OpenCV is used for fast color conversion
except ImportError:
    print("Error: ZED SDK (pyzed) or OpenCV (cv2) not found.")
    print("Please install the ZED SDK, its Python wrapper, and opencv-python.")
    exit()

# --- Style Constants ---
BG_COLOR = "#282c34"
CONTENT_BG = "#3c4049"
FIELD_BG = "#2c313a"
BORDER_COLOR = "#202328"
TEXT_COLOR = "#EAEAEA"
ACCENT_COLOR = "#2e8fde"
TEAL_COLOR = "#007596"
TEAL_ACTIVE_COLOR = "#007596"
STOP_COLOR = "#d9534f"
STOP_ACTIVE_COLOR = "#c9302c"
FRAME_ENTRY_BG = "#01839a"
TIME_DISPLAY_BG = "#c08619"

class RoundedLabelFrame(tk.Frame):
    """A custom frame with a label and rounded corners, styled for a modern look."""
    def __init__(self, parent, text="", pad=15, radius=15,
                 color_bg=BG_COLOR, color_fill=CONTENT_BG, color_border=BORDER_COLOR):
        super().__init__(parent, bg=color_bg)
        self._radius = radius
        self._color_fill = color_fill
        self._color_border = color_border

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.label = ttk.Label(self, text=text, style='FrameTitle.TLabel')
        self.label.grid(row=0, column=0, sticky='w', padx=pad, pady=(0, 5))

        self._canvas = tk.Canvas(self, bg=color_bg, highlightthickness=0)
        self._canvas.grid(row=1, column=0, sticky='nsew', padx=5, pady=(0, 5))

        self.content_frame = ttk.Frame(self, style='Content.TFrame', padding=(pad, 10))
        self._canvas.bind("<Configure>", self._draw_frame)

    def _draw_frame(self, event):
        width, height = self._canvas.winfo_width(), self._canvas.winfo_height()
        if width < 2 or height < 2: return
        self._canvas.delete("all")
        self._canvas.create_rectangle(1, 1, width-1, height-1, fill=self._color_fill, outline=self._color_border, width=2, tags="frame")
        self.content_frame.place(in_=self._canvas, x=2, y=2, relwidth=1, relheight=1, width=-4, height=-4)

class SVOConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SVO Converter Suite")
        self.root.geometry("1050x900")
        self.root.configure(bg=BG_COLOR)
        
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1) 

        self.batch_input_dir, self.batch_output_dir = tk.StringVar(), tk.StringVar()
        self.trim_input_file, self.trim_output_dir = tk.StringVar(), tk.StringVar()
        
        self.start_frame_var, self.end_frame_var = tk.StringVar(), tk.StringVar()
        
        self.log_queue, self.progress_queue = queue.Queue(), queue.Queue()
        self.stop_event, self.running_process = threading.Event(), None
        self.trim_video_capture = None
        self.trim_total_frames = 0
        self.trim_fps = 30
        self.trim_start_frame, self.trim_end_frame = 0, 0
        self.is_playing = False
        
        self.play_pause_button = None

        self._create_styles()
        
        self.notebook = ttk.Notebook(root, style='TNotebook')
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.batch_tab = ttk.Frame(self.notebook, style='TFrame', padding=0)
        self.trim_tab = ttk.Frame(self.notebook, style='TFrame', padding=0)
        self.doc_tab = ttk.Frame(self.notebook, style='TFrame', padding=10)
        self.notebook.add(self.batch_tab, text='Batch Conversion')
        self.notebook.add(self.trim_tab, text='Trim Settings')
        self.notebook.add(self.doc_tab, text='Documentation')
        
        self.batch_log_text = None
        self.trim_log_text = None

        self._create_batch_tab()
        self._create_trim_tab()
        self._create_doc_tab()
        
        self.root.after(100, self.process_queues)

    

    def _create_styles(self):
        self.style = ttk.Style(self.root)
        self.style.theme_use('clam')

        self.style.configure('.', background=BG_COLOR, foreground=TEXT_COLOR, borderwidth=0, lightcolor=BORDER_COLOR, darkcolor=BORDER_COLOR)
        self.style.configure('TFrame', background=BG_COLOR)
        self.style.configure('Content.TFrame', background=CONTENT_BG)

        self.style.configure('TLabel', background=CONTENT_BG, foreground=TEXT_COLOR, font=('Segoe UI', 12))
        self.style.configure('FrameTitle.TLabel', background=BG_COLOR, foreground=ACCENT_COLOR, font=('Segoe UI', 12, 'bold'))
        
        self.style.configure('TEntry', fieldbackground=FIELD_BG, foreground=TEXT_COLOR, insertbackground=TEXT_COLOR, relief='flat', borderwidth=2, bordercolor=FIELD_BG)
        self.style.map('TEntry', bordercolor=[('focus', ACCENT_COLOR)])
        
        
        self.style.configure('Frame.TEntry', 
            fieldbackground=FRAME_ENTRY_BG, 
            foreground='white',
            padding=(5, 8, 5, 8) # Left, Top, Right, Bottom
        )
        self.style.configure('Time.TLabel', background=TIME_DISPLAY_BG, foreground='white', padding=6, anchor='center', font=('Consolas', 12))
        
        self.style.configure('ProgressPercent.TLabel', background=CONTENT_BG, foreground=TEXT_COLOR, font=('Segoe UI', 30, 'bold'), anchor='center')

        self.style.configure('TButton', background=TEAL_COLOR, foreground='white', font=('Segoe UI', 12, 'bold'), borderwidth=0, padding=(15, 8), relief='flat')
        self.style.map('TButton', background=[('active', TEAL_ACTIVE_COLOR)])
        self.style.configure('Stop.TButton', background=STOP_COLOR)
        self.style.map('Stop.TButton', background=[('active', STOP_ACTIVE_COLOR)])
        
        self.style.configure('spectrum.Horizontal.TProgressbar', troughcolor=FIELD_BG, background=ACCENT_COLOR, borderwidth=0, thickness=12)

        self.style.configure('TNotebook', background=BG_COLOR, borderwidth=0)
        self.style.configure('TNotebook.Tab', background=CONTENT_BG, foreground=TEXT_COLOR, padding=[12, 6], font=('Segoe UI', 12, 'bold'), borderwidth=0)
        self.style.map('TNotebook.Tab', background=[('selected', ACCENT_COLOR)], foreground=[('selected', 'white')])
        
        self.style.configure('Timeline.Horizontal.TScale', troughcolor=FIELD_BG, background=ACCENT_COLOR, troughrelief='flat', sliderrelief='flat')
        self.style.map('Timeline.Horizontal.TScale', background=[('active', TEAL_ACTIVE_COLOR)])

    def _create_batch_tab(self):
       
        self.batch_tab.grid_columnconfigure(0, weight=1)
        self.batch_tab.grid_rowconfigure(0, weight=45) 
        self.batch_tab.grid_rowconfigure(1, weight=55) 

        controls_container = ttk.Frame(self.batch_tab, style='TFrame', padding=(5, 10, 5, 0))
        controls_container.grid(row=0, column=0, sticky='nsew')
        controls_container.grid_columnconfigure(0, weight=1)

        io_frame = RoundedLabelFrame(controls_container, text="Select Folders")
        io_frame.grid(row=0, column=0, sticky='ew')
        io_content = io_frame.content_frame
        io_content.grid_columnconfigure(1, weight=1)
        ttk.Label(io_content, text="Input Directory (.svo/.svo2 files):").grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 2))
        ttk.Entry(io_content, textvariable=self.batch_input_dir, font=('Segoe UI', 12)).grid(row=1, column=1, sticky=tk.EW, ipady=4, padx=(0,10))
        ttk.Button(io_content, text="Browse", command=self.select_batch_input_dir).grid(row=1, column=2)
        ttk.Label(io_content, text="Output Directory (.avi files):").grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(10, 2))
        ttk.Entry(io_content, textvariable=self.batch_output_dir, font=('Segoe UI', 12)).grid(row=3, column=1, sticky=tk.EW, ipady=4, padx=(0,10))
        ttk.Button(io_content, text="Browse", command=self.select_batch_output_dir).grid(row=3, column=2)
        
        control_frame = RoundedLabelFrame(controls_container, text="Conversion Control")
        control_frame.grid(row=1, column=0, sticky='ew', pady=(15,0))
        control_content = control_frame.content_frame
        control_content.grid_columnconfigure(0, weight=1)
        button_frame = ttk.Frame(control_content, style='Content.TFrame')
        button_frame.grid(row=0, column=0, columnspan=2, pady=5)
        self.start_button = ttk.Button(button_frame, text="Start Conversion", command=self.start_batch_conversion)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(button_frame, text="Stop Conversion", command=self.stop_conversion, style='Stop.TButton', state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)
        self.current_file_label = ttk.Label(control_content, text="Waiting to start...", font=('Segoe UI', 12, 'italic'), foreground="#cccccc")
        self.current_file_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(10, 2), padx=5)
        progress_frame = ttk.Frame(control_content, style='Content.TFrame')
        progress_frame.grid(row=2, column=0, sticky=tk.EW, pady=2, padx=5)
        progress_frame.grid_columnconfigure(0, weight=1)
        self.current_progress = ttk.Progressbar(progress_frame, orient='horizontal', mode='determinate', style='spectrum.Horizontal.TProgressbar')
        self.current_progress.grid(row=0, column=0, sticky=tk.EW)
        self.current_percent_label = ttk.Label(progress_frame, text="0%", font=('Segoe UI', 12, 'bold'), width=4, anchor='e')
        self.current_percent_label.grid(row=0, column=1, padx=(10,0))
        ttk.Label(control_content, text="Overall Progress:").grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 2), padx=5)
        self.overall_progress = ttk.Progressbar(control_content, orient='horizontal', mode='determinate', style='spectrum.Horizontal.TProgressbar')
        self.overall_progress.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=2, padx=5)

        log_frame = RoundedLabelFrame(self.batch_tab, text="Conversion Log")
        log_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=(15, 10))
        self.batch_log_text = scrolledtext.ScrolledText(log_frame.content_frame, state='disabled', wrap=tk.WORD, bg=FIELD_BG, fg=TEXT_COLOR, relief=tk.FLAT, bd=0, font=('Consolas', 12), height=1, insertbackground=TEXT_COLOR)
        self.batch_log_text.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

    def _create_trim_tab(self):
        
        self.trim_tab.grid_columnconfigure(0, weight=1)
        self.trim_tab.grid_rowconfigure(0, weight=75) 
        self.trim_tab.grid_rowconfigure(1, weight=25)
        
        main_frame = ttk.Frame(self.trim_tab, style='TFrame', padding=(5, 10, 5, 0))
        main_frame.grid(row=0, column=0, sticky='nsew')
        main_frame.grid_columnconfigure(0, weight=3)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        
        player_container = ttk.Frame(main_frame, style='TFrame')
        player_container.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        player_container.grid_rowconfigure(0, weight=1)
        player_container.grid_columnconfigure(0, weight=1)
        self.trim_video_label = tk.Label(player_container, text="Select an SVO file to preview", bg='black', fg='white', font=('Segoe UI', 16))
        self.trim_video_label.grid(row=0, column=0, sticky='nsew')
        
        timeline_frame = ttk.Frame(player_container, style= 'TFrame')
        timeline_frame.grid(row=1, column=0, sticky='ew')
        timeline_frame.grid_columnconfigure(0, weight=1)
        self.timeline_var = tk.DoubleVar()
        self.timeline = ttk.Scale(timeline_frame, from_=0, to=100, orient='horizontal', variable=self.timeline_var, style='Timeline.Horizontal.TScale', command=self._on_timeline_seek, state='disabled')
        self.timeline.grid(row=0, column=0, sticky='ew', padx=(5,10))
        self.current_time_label = ttk.Label(timeline_frame, text="00:00:00 / 00:00:00", font=('Consolas', 12), background=BG_COLOR, foreground="#cccccc")
        self.current_time_label.grid(row=0, column=1, sticky='e', padx=(0,5))

        player_controls_frame = tk.Frame(player_container, bg=BG_COLOR)
        player_controls_frame.grid(row=2, column=0, sticky='ew')
        buttons_defs = {'✂ In': self._set_trim_start, '✂ Out': self._set_trim_end, '⏪': None, 'TOGGLE': self._toggle_playback, '⏩': None}
        for i, (text, cmd) in enumerate(buttons_defs.items()):
            player_controls_frame.grid_columnconfigure(i, weight=1)
            if text == 'TOGGLE':
                self.play_pause_button = tk.Button(player_controls_frame, text='▶', bg=TEAL_COLOR, fg='white', activebackground=TEAL_ACTIVE_COLOR, font=('Segoe UI', 12, 'bold'), relief='flat', borderwidth=0, command=cmd)
                self.play_pause_button.grid(row=0, column=i, sticky='ew', padx=2, pady=(5,0))
            else:
                btn = tk.Button(player_controls_frame, text=text, bg=TEAL_COLOR, fg='white', activebackground=TEAL_ACTIVE_COLOR, font=('Segoe UI', 12, 'bold'), relief='flat', borderwidth=0, command=cmd)
                btn.grid(row=0, column=i, sticky='ew', padx=2, pady=(5,0))

        trim_details_frame = ttk.Frame(player_container, style='TFrame', padding=(0, 10))
        trim_details_frame.grid(row=3, column=0, sticky='ew')
        trim_details_frame.grid_columnconfigure((0,1), weight=1)

        start_frame_ui = ttk.Frame(trim_details_frame, style='TFrame')
        start_frame_ui.grid(row=0, column=0, sticky='ew', padx=(0, 5))
        ttk.Label(start_frame_ui, text="Start Frame", style='TLabel', background=BG_COLOR).pack(anchor='w')
        
        
        start_entry_font = ('Segoe UI', 22, 'bold')
        start_entry = ttk.Entry(start_frame_ui, textvariable=self.start_frame_var, style='Frame.TEntry', justify='center', font=start_entry_font)
        start_entry.pack(fill='x') 
        start_entry.bind("<Return>", self._on_start_frame_entry)
        
        self.start_time_label = ttk.Label(start_frame_ui, text="00:00:00", style='Time.TLabel')
        self.start_time_label.pack(fill='x', pady=(5,0))

        end_frame_ui = ttk.Frame(trim_details_frame, style='TFrame')
        end_frame_ui.grid(row=0, column=1, sticky='ew', padx=(5, 0))
        ttk.Label(end_frame_ui, text="End Frame", background=BG_COLOR).pack(anchor='w')
        
        
        end_entry_font = ('Segoe UI', 22, 'bold')
        end_entry = ttk.Entry(end_frame_ui, textvariable=self.end_frame_var, style='Frame.TEntry', justify='center', font=end_entry_font)
        end_entry.pack(fill='x') 
        end_entry.bind("<Return>", self._on_end_frame_entry)
        
        self.end_time_label = ttk.Label(end_frame_ui, text="00:00:00", style='Time.TLabel')
        self.end_time_label.pack(fill='x', pady=(5,0))
        
        
        controls_container = ttk.Frame(main_frame, style='TFrame')
        controls_container.grid(row=0, column=1, sticky='nsew')
        controls_container.grid_columnconfigure(0, weight=1)

        trim_io_frame = RoundedLabelFrame(controls_container, text="Select Files & Convert")
        trim_io_frame.grid(row=0, column=0, sticky='ew')
        trim_io_content = trim_io_frame.content_frame
        trim_io_content.grid_columnconfigure(0, weight=1)
        ttk.Label(trim_io_content, text="Input Video File:").grid(row=0, column=0, sticky=tk.W, pady=(0, 2), columnspan=2)
        ttk.Entry(trim_io_content, textvariable=self.trim_input_file).grid(row=1, column=0, sticky=tk.EW, ipady=4, padx=(0,10))
        ttk.Button(trim_io_content, text="Browse", command=self._select_trim_input_file).grid(row=1, column=1)
        ttk.Label(trim_io_content, text="Output Directory:").grid(row=2, column=0, sticky=tk.W, pady=(10, 2), columnspan=2)
        ttk.Entry(trim_io_content, textvariable=self.trim_output_dir).grid(row=3, column=0, sticky=tk.EW, ipady=4, padx=(0,10))
        ttk.Button(trim_io_content, text="Browse", command=self._select_trim_output_dir).grid(row=3, column=1)
        trim_btn_frame = ttk.Frame(trim_io_content, style='Content.TFrame')
        trim_btn_frame.grid(row=4, column=0, columnspan=2, pady=(15, 5))
        trim_btn_frame.grid_columnconfigure(0, weight=1)
        self.trim_start_button = ttk.Button(trim_btn_frame, text="Start Conversion", command=self._start_trim_conversion)
        self.trim_start_button.pack(side=tk.LEFT, padx=5, expand=True)
        self.trim_stop_button = ttk.Button(trim_btn_frame, text="Stop", style='Stop.TButton', command=self.stop_conversion, state='disabled')
        self.trim_stop_button.pack(side=tk.LEFT, padx=5, expand=True)

        conversion_prog_frame = RoundedLabelFrame(controls_container, text="Progress")
        conversion_prog_frame.grid(row=1, column=0, sticky='nsew', pady=(15,0))
        prog_content = conversion_prog_frame.content_frame
        prog_content.grid_columnconfigure(0, weight=1)
        self.trim_progress = ttk.Progressbar(prog_content, orient='horizontal', mode='determinate', style='spectrum.Horizontal.TProgressbar')
        self.trim_progress.grid(row=0, column=0, sticky='ew', padx=10, pady=(10, 5))
        self.trim_percent_label = ttk.Label(prog_content, text="0%", style='ProgressPercent.TLabel')
        self.trim_percent_label.grid(row=1, column=0, sticky='nsew', pady=(5, 10))
        
        log_frame = RoundedLabelFrame(self.trim_tab, text="Conversion Log")
        log_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=(15, 10))
        self.trim_log_text = scrolledtext.ScrolledText(log_frame.content_frame, state='disabled', wrap=tk.WORD, bg=FIELD_BG, fg=TEXT_COLOR, relief=tk.FLAT, bd=0, font=('Consolas', 12), height=1, insertbackground=TEXT_COLOR)
        self.trim_log_text.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)


    def _create_doc_tab(self):
        
        self.doc_tab.grid_columnconfigure(0, weight=1)
        self.doc_tab.grid_rowconfigure(0, weight=1)
        doc_frame = RoundedLabelFrame(self.doc_tab, text="Documentation")
        doc_frame.grid(row=0, column=0, sticky='nsew', padx=5, pady=(10,5))
        doc_text = scrolledtext.ScrolledText(doc_frame.content_frame, state='normal', wrap=tk.WORD,bg=CONTENT_BG, fg=TEXT_COLOR, relief=tk.FLAT, bd=0,font=('Segoe UI', 12), padx=10, pady=10)
        doc_text.pack(fill=tk.BOTH, expand=True)
        doc_text.insert(tk.END, "Welcome to the SVO Converter Suite!\n\n", ('h1',))
        doc_text.insert(tk.END, "Batch Conversion Tab\n", ('h2',))
        doc_text.insert(tk.END, "1.  Input Directory: Select the folder containing your SVO files.\n2.  Output Directory: Choose where the converted AVI files will be saved.\n3.  Start Conversion: Begins processing all SVO files in the input folder.\n\n")
        doc_text.insert(tk.END, "Trim Settings Tab\n", ('h2',))
        doc_text.insert(tk.END, "1.  Input Video File: Select a single SVO file to preview and trim.\n2.  Video Timeline: Click or drag the slider to scrub through the video.\n3.  Set Trim Points: Use the '✂ In' and '✂ Out' buttons to mark the start and end of your desired clip.\n4.  Manual Entry: For precise control, type frame numbers into the 'Start/End Frame' boxes and press Enter.\n\n")
        doc_text.insert(tk.END, "Important notes\n", ('h2',))
        # --- Hyperlink Text Insertion ---
        doc_text.insert(tk.END, "The SVO converter suit is designed to work on the original script provided by the ZED stereolabs. It was slightly modified to suit the specific needs of the application such as trimming. The guide to install the necessary dependancies are fully documented in the github repository of ")
        doc_text.insert(tk.END, "Samitha Thilakarathna", ('link',)) # The clickable text
        doc_text.insert(tk.END, ", a PhD student of DTU Aqua, Section of Fisheries Technology, Technical University of Denmark.")
        
        doc_text.tag_config('h1', font=('Segoe UI', 18, 'bold'), foreground=TEAL_COLOR, spacing3=10)
        doc_text.tag_config('h2', font=('Segoe UI', 14, 'bold'), foreground=ACCENT_COLOR, spacing3=8)

        # --- Hyperlink Tag and Event Bindings ---
        doc_text.tag_config('link', foreground="#87CEFA", underline=True) # Light sky blue
        doc_text.tag_bind('link', '<Enter>', lambda e: doc_text.config(cursor="hand2"))
        doc_text.tag_bind('link', '<Leave>', lambda e: doc_text.config(cursor=""))
        doc_text.tag_bind('link', '<Button-1>', self._open_link)
        
        doc_text.config(state='disabled')

    def _open_link(self, evemt):
        webbrowser.open_new(r"https://github.com/msamdk/SVO_converter_app/blob/main/README.md")
    
    def _toggle_playback(self):
        
        if self.is_playing:
            self._pause_video()
        else:
            self._play_video()

    def _play_video(self):
        
        if self.is_playing or not self.trim_video_capture: return
        self.is_playing = True
        if self.play_pause_button:
            self.play_pause_button.config(text='⏸')
        delay = int(1000 / self.trim_fps) if self.trim_fps > 0 else 33
        self._playback_loop(delay)

    def _playback_loop(self, delay):
        
        if self.is_playing:
            current_frame = int(self.timeline_var.get())
            next_frame = current_frame + 1
            if next_frame < self.trim_total_frames:
                self.timeline_var.set(next_frame)
                self._on_timeline_seek(next_frame)
                self.root.after(delay, lambda: self._playback_loop(delay))
            else:
                self._pause_video()
    
    def _pause_video(self):
        
        self.is_playing = False
        if self.play_pause_button:
            self.play_pause_button.config(text='▶')
        
    def _format_time(self, frame_num):
        
        if self.trim_fps > 0:
            secs = frame_num / self.trim_fps
            return str(datetime.timedelta(seconds=int(secs)))
        return "00:00:00"

    def _on_timeline_seek(self, value):
        
        frame_num = int(float(value))
        self._show_frame(frame_num)
        total_time_str = self._format_time(self.trim_total_frames)
        current_time_str = self._format_time(frame_num)
        self.current_time_label.config(text=f"{current_time_str} / {total_time_str}")

    def _show_frame(self, frame_num):
        
        if isinstance(self.trim_video_capture, sl.Camera) and self.trim_video_capture.is_opened():
            self.trim_video_capture.set_svo_position(frame_num)
            zed_image = sl.Mat()
            if self.trim_video_capture.grab() == sl.ERROR_CODE.SUCCESS:
                self.trim_video_capture.retrieve_image(zed_image, sl.VIEW.LEFT)
                frame_data = zed_image.get_data()
                frame_rgb = cv2.cvtColor(frame_data, cv2.COLOR_BGRA2RGB)

                overlay_text = f"Frame: {frame_num}"
                font_scale = 0.8
                font_face = cv2.FONT_HERSHEY_SIMPLEX
                text_color = (0, 255, 0)
                cv2.putText(frame_rgb, overlay_text, (15, 35), font_face, font_scale, (0,0,0), 4, cv2.LINE_AA)
                cv2.putText(frame_rgb, overlay_text, (15, 35), font_face, font_scale, text_color, 2, cv2.LINE_AA)

                img = Image.fromarray(frame_rgb)
                label_w, label_h = self.trim_video_label.winfo_width(), self.trim_video_label.winfo_height()
                if label_w > 1 and label_h > 1:
                    img.thumbnail((label_w, label_h), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image=img)
                self.trim_video_label.config(image=photo)
                self.trim_video_label.image = photo

    def _set_trim_start(self):
        
        if not self.trim_video_capture: return
        self._pause_video()
        self.trim_start_frame = int(self.timeline.get())
        time_str = self._format_time(self.trim_start_frame)
        self.start_time_label.config(text=time_str)
        self.start_frame_var.set(str(self.trim_start_frame)) 
        if self.trim_end_frame < self.trim_start_frame:
            self._set_trim_end(self.trim_start_frame)

    def _set_trim_end(self, frame_num=None):
        
        if not self.trim_video_capture: return
        self._pause_video()
        self.trim_end_frame = int(self.timeline.get()) if frame_num is None else frame_num
        time_str = self._format_time(self.trim_end_frame)
        self.end_time_label.config(text=time_str)
        self.end_frame_var.set(str(self.trim_end_frame)) 

    def _on_start_frame_entry(self, event=None):
        
        if not self.trim_video_capture: return
        try:
            frame_num = int(self.start_frame_var.get())
            if 0 <= frame_num < self.trim_total_frames:
                self._pause_video()
                self.timeline_var.set(frame_num)
                self._on_timeline_seek(frame_num)
                self._set_trim_start()
            else:
                self.start_frame_var.set(str(self.trim_start_frame))
        except (ValueError, TypeError):
            self.start_frame_var.set(str(self.trim_start_frame))
            
    def _on_end_frame_entry(self, event=None):
        
        if not self.trim_video_capture: return
        try:
            frame_num = int(self.end_frame_var.get())
            if self.trim_start_frame <= frame_num < self.trim_total_frames:
                self._pause_video()
                self.timeline_var.set(frame_num)
                self._on_timeline_seek(frame_num)
                self._set_trim_end()
            else:
                self.end_frame_var.set(str(self.trim_end_frame))
        except (ValueError, TypeError):
            self.end_frame_var.set(str(self.trim_end_frame))

    def _select_trim_input_file(self):
        
        self._pause_video()
        file_path = filedialog.askopenfilename(
            title="Select Input SVO File",
            filetypes=(("SVO Files", "*.svo *.svo2"), ("All files", "*.*"))
        )
        if not file_path: return
        self.trim_input_file.set(file_path)

        if isinstance(self.trim_video_capture, sl.Camera) and self.trim_video_capture.is_opened():
            self.trim_video_capture.close()

        zed = sl.Camera()
        init_params = sl.InitParameters()
        init_params.set_from_svo_file(file_path)
        init_params.svo_real_time_mode = False

        err = zed.open(init_params)
        if err != sl.ERROR_CODE.SUCCESS:
            self.trim_video_label.config(text=f"Error: Could not open SVO.\n{err}", image='')
            self.timeline.config(state='disabled')
            self.trim_video_capture = None
            return

        self.trim_video_capture = zed
        self.trim_total_frames = self.trim_video_capture.get_svo_number_of_frames()
        self.trim_fps = self.trim_video_capture.get_camera_information().camera_configuration.fps
        if self.trim_fps == 0: self.trim_fps = 30

        self.timeline.config(state='normal', to=self.trim_total_frames - 1)
        self.timeline_var.set(0)
        
        self._on_timeline_seek(0)
        self._set_trim_start()
        self._set_trim_end(self.trim_total_frames - 1)
    
    def _select_trim_output_dir(self):
        
        dir_path = filedialog.askdirectory(title="Select Output Directory for Trimmed File")
        if dir_path: self.trim_output_dir.set(dir_path)

    def select_batch_input_dir(self):
        
        dir_path = filedialog.askdirectory(title="Select Input Directory")
        if dir_path: self.batch_input_dir.set(dir_path)

    def select_batch_output_dir(self):
        
        dir_path = filedialog.askdirectory(title="Select Output Directory")
        if dir_path: self.batch_output_dir.set(dir_path)

    def log(self, message): self.log_queue.put(message)
    def update_progress(self, target, percent): self.progress_queue.put((target, percent))
    
    def process_queues(self):
        
        try:
            while not self.log_queue.empty():
                message = self.log_queue.get_nowait()
                for log_widget in [self.batch_log_text, self.trim_log_text]:
                    if log_widget:
                        log_widget.config(state='normal')
                        log_widget.insert(tk.END, message)
                        log_widget.see(tk.END)
                        log_widget.config(state='disabled')
        except queue.Empty: pass
        
        try:
            while not self.progress_queue.empty():
                target, percent = self.progress_queue.get_nowait()
                if target == 'batch':
                    self.current_progress['value'] = percent
                    self.current_percent_label.config(text=f"{int(percent)}%")
                elif target == 'trim':
                    self.trim_progress['value'] = percent
                    self.trim_percent_label.config(text=f"{int(percent)}%")
        except queue.Empty: pass
        finally: self.root.after(100, self.process_queues)

    def _clear_logs(self):
        
        for log_widget in [self.batch_log_text, self.trim_log_text]:
            if log_widget:
                log_widget.config(state='normal')
                log_widget.delete('1.0', tk.END)
                log_widget.config(state='disabled')

    def start_batch_conversion(self):
        
        input_dir = self.batch_input_dir.get()
        output_dir = self.batch_output_dir.get()
        if not os.path.isdir(input_dir) or not os.path.isdir(output_dir):
            self.log("Error: Please select valid input and output directories.\n")
            return
        self.set_gui_state(is_running=True, mode='batch')
        self._clear_logs()
        self.stop_event.clear()
        threading.Thread(target=self.run_batch_conversion_thread, args=(input_dir, output_dir), daemon=True).start()

    def _start_trim_conversion(self):
        
        input_file = self.trim_input_file.get()
        output_dir = self.trim_output_dir.get()
        if not os.path.isfile(input_file) or not os.path.isdir(output_dir):
            self.log("Error: Please select a valid input file and output directory.\n")
            return
        self.set_gui_state(is_running=True, mode='trim')
        self._clear_logs()
        self.stop_event.clear()
        threading.Thread(target=self._run_trim_conversion_thread, args=(input_file, output_dir), daemon=True).start()

    def stop_conversion(self):
        
        self._pause_video()
        self.log("Stopping conversion...\n")
        self.stop_event.set()
        if self.running_process:
            self.running_process.terminate()

    def set_gui_state(self, is_running, mode):
        
        if is_running:
            self.start_button.config(state='disabled')
            self.trim_start_button.config(state='disabled')
        else:
            self.start_button.config(state='normal')
            self.trim_start_button.config(state='normal')

        if mode == 'batch':
            self.stop_button.config(state='normal' if is_running else 'disabled')
            self.trim_stop_button.config(state='disabled')
        elif mode == 'trim':
            self.trim_stop_button.config(state='normal' if is_running else 'disabled')
            self.stop_button.config(state='disabled')

    def run_batch_conversion_thread(self, input_path, output_path):
        # Unchanged
        svo_files = sorted([f for f in os.listdir(input_path) if f.lower().endswith(('.svo', '.svo2'))])
        if not svo_files:
            self.log("No .svo or .svo2 files found.\n")
            self.root.after(0, lambda: self.set_gui_state(False, 'batch'))
            return
        self.log(f"Found {len(svo_files)} files to convert.\n{'='*50}\n")
        self.overall_progress['maximum'] = len(svo_files)
        for i, svo_file in enumerate(svo_files):
            if self.stop_event.is_set():
                self.log("Conversion stopped by user.\n")
                break
            self.overall_progress['value'] = i
            self.update_progress('batch', 0)
            self.root.after(0, lambda f=svo_file: self.current_file_label.config(text=f"Processing: {f}"))
            self.log(f"[{i+1}/{len(svo_files)}] Converting: {svo_file}\n")
            output_filename = os.path.join(output_path, f"{os.path.splitext(svo_file)[0]}.avi")
            command = ["python", "-u", "svo_export.py", "--mode", "0", "--input_svo_file", os.path.join(input_path, svo_file), "--output_avi_file", output_filename]
            try:
                creationflags = 0
                if os.name == 'nt': creationflags = subprocess.CREATE_NO_WINDOW
                self.running_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', creationflags=creationflags)
                for line in iter(self.running_process.stdout.readline, ''):
                    if self.stop_event.is_set(): break
                    match = re.search(r'(\d+)%', line)
                    if match: self.update_progress('batch', int(match.group(1)))
                    elif "Converting SVO..." not in line.strip(): self.log(line)
                self.running_process.wait()
            except Exception as e:
                self.log(f"FATAL ERROR: {e}\n")
                break
            finally:
                self.running_process = None
            if not self.stop_event.is_set():
                self.update_progress('batch', 100)
                self.log(f"SUCCESS: Converted {svo_file}\n{'='*50}\n")
        self.root.after(0, lambda: self.current_file_label.config(text="Finished!"))
        if not self.stop_event.is_set():
            self.overall_progress['value'] = len(svo_files)
        self.root.after(0, lambda: self.set_gui_state(False, 'batch'))
        
    def _run_trim_conversion_thread(self, input_file, output_dir):
        # Unchanged
        self.log(f"Starting trim conversion for: {os.path.basename(input_file)}\n")
        self.update_progress('trim', 0)
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        
        output_filename = os.path.join(output_dir, f"{base_name}_trimmed_{self.trim_start_frame}_{self.trim_end_frame}.avi")
        
        command = [
            "python", "-u", "svo_export.py", "--mode", "0", 
            "--input_svo_file", input_file, 
            "--output_avi_file", output_filename,
            "--start_frame", str(self.trim_start_frame),
            "--end_frame", str(self.trim_end_frame)
        ]
        
        try:
            creationflags = 0
            if os.name == 'nt': creationflags = subprocess.CREATE_NO_WINDOW
            self.running_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', creationflags=creationflags)
            for line in iter(self.running_process.stdout.readline, ''):
                if self.stop_event.is_set(): break
                match = re.search(r'(\d+)%', line)
                if match:
                    self.update_progress('trim', int(match.group(1)))
                elif "Converting SVO..." not in line.strip():
                    self.log(line)
            return_code = self.running_process.wait()
        except Exception as e:
            self.log(f"FATAL ERROR: {e}\n")
            return_code = -1
        finally:
            self.running_process = None

        if not self.stop_event.is_set() and return_code == 0:
            self.update_progress('trim', 100)
            self.log(f"SUCCESS: Trimmed video saved to {output_filename}\n{'='*50}\n")
        elif return_code != 0:
            self.log(f"ERROR: Conversion script failed with exit code {return_code}.\n{'='*50}\n")
        
        self.root.after(0, lambda: self.set_gui_state(False, 'trim'))

if __name__ == "__main__":
    root = tk.Tk()
    app = SVOConverterApp(root)
    root.mainloop()