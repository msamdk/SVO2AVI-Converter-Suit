import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
import os
import subprocess
import threading
import queue
import re

# --- Style Constants ---
BG_COLOR = "#121212"  
CONTENT_BG = "#1E1E1E" 
BORDER_COLOR = "#333333" 
TEXT_COLOR = "#EAEAEA"
TEAL_COLOR = "#008080"
TEAL_ACTIVE_COLOR = "#006666"
STOP_COLOR = "#B03A2E"
STOP_ACTIVE_COLOR = "#943126"
PROGRESS_RED = (220, 38, 38)
PROGRESS_BLUE = (59, 130, 246)

class RoundedLabelFrame(tk.Frame):
    
    def __init__(self, parent, text="", pad=10, radius=25,
                 color_bg=BG_COLOR, color_fill=CONTENT_BG, color_border=BORDER_COLOR):
        super().__init__(parent, bg=color_bg, padx=pad, pady=pad)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._text = text
        self._radius = radius
        self._color_bg = color_bg
        self._color_fill = color_fill
        self._color_border = color_border

        self._canvas = tk.Canvas(self, bg=color_bg, highlightthickness=0)
        self._canvas.grid(row=1, column=0, sticky='nsew')
        
        # The actual frame for content, placed on top of the canvas
        self.content_frame = ttk.Frame(self._canvas, style='Content.TFrame', padding=pad+5)
        self._canvas.create_window(0, 0, window=self.content_frame, anchor='nw')
        
        self.label = ttk.Label(self, text=text, style='FrameLabel.TLabel')
        self.label.grid(row=0, column=0, sticky='w', padx=pad+10, pady=(0, 5))

        self.bind("<Configure>", self._draw_frame)
        self.content_frame.bind("<Configure>", self._update_canvas)

    def _update_canvas(self, event=None):
        self._canvas.config(width=self.content_frame.winfo_reqwidth(),
                            height=self.content_frame.winfo_reqheight())
        self._draw_frame()

    def _draw_frame(self, event=None):
        width = self.winfo_width()
        height = self.winfo_height()
        r = self._radius

        self._canvas.delete("all")
        self._canvas.create_aa_rounded_rect(
            0, self.label.winfo_height()//2, width, height,
            radius=r, fill=self._color_fill, outline=self._color_border, width=2
        )
        self.content_frame.place(in_=self._canvas, x=2, y=self.label.winfo_height()//2 + 2,
                                 width=width-4, height=height-self.label.winfo_height()//2-4)

# Helper for anti-aliased rounded rectangle on canvas
def create_aa_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
    points = [
        x1 + radius, y1,
        x1 + radius, y1,
        x2 - radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1 + radius,
        x1, y1
    ]
    return self.create_polygon(points, **kwargs, smooth=True)

tk.Canvas.create_aa_rounded_rect = create_aa_rounded_rect

class SVOConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SVO Batch Converter")
        self.root.geometry("850x750")
        self.root.configure(bg=BG_COLOR)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.log_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.running_process = None

        # --- Configure ttk Styles ---
        self.style = ttk.Style(root)
        self.style.theme_use('clam')
        self.style.configure('.', background=CONTENT_BG, foreground=TEXT_COLOR, fieldbackground=CONTENT_BG, borderwidth=0)
        self.style.configure('TFrame', background=BG_COLOR)
        self.style.configure('Content.TFrame', background=CONTENT_BG)
        self.style.configure('TLabel', background=CONTENT_BG, foreground=TEXT_COLOR, font=('Arial', 10))
        self.style.configure('FrameLabel.TLabel', background=BG_COLOR, foreground=TEXT_COLOR, font=('Arial', 11, 'bold'))
        self.style.configure('TEntry', fieldbackground=CONTENT_BG, foreground=TEXT_COLOR, insertbackground=TEXT_COLOR, relief='flat')
        self.style.configure('TButton', background=TEAL_COLOR, foreground='white', font=('Arial', 10, 'bold'), borderwidth=0, focusthickness=0, padding=8)
        self.style.map('TButton', background=[('active', TEAL_ACTIVE_COLOR)])
        self.style.configure('Stop.TButton', background=STOP_COLOR)
        self.style.map('Stop.TButton', background=[('active', STOP_ACTIVE_COLOR)])
        self.style.configure('spectrum.Horizontal.TProgressbar', troughcolor=BG_COLOR, background=f'#{PROGRESS_RED[0]:02x}{PROGRESS_RED[1]:02x}{PROGRESS_RED[2]:02x}', relief='flat', borderwidth=0, thickness=15)
        
        # --- Main Layout Frame ---
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky='nsew')
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)

        # --- I/O Frame ---
        io_frame = RoundedLabelFrame(main_frame, text="1. Select Folders")
        io_frame.grid(row=0, column=0, sticky='ew', pady=5)
        io_content = io_frame.content_frame
        io_content.grid_columnconfigure(0, weight=1)
        
        ttk.Label(io_content, text="Input Directory (contains .svo/.svo2 files):").grid(row=0, column=0, sticky=tk.W, pady=(0, 2))
        ttk.Entry(io_content, textvariable=self.input_dir).grid(row=1, column=0, sticky=tk.EW, ipady=5, padx=(0,10))
        ttk.Button(io_content, text="Browse...", command=self.select_input_dir).grid(row=1, column=1)

        ttk.Label(io_content, text="Output Directory (to save .avi files):").grid(row=2, column=0, sticky=tk.W, pady=(10, 2))
        ttk.Entry(io_content, textvariable=self.output_dir).grid(row=3, column=0, sticky=tk.EW, ipady=5, padx=(0,10))
        ttk.Button(io_content, text="Browse...", command=self.select_output_dir).grid(row=3, column=1)

        # --- Control & Progress Frame ---
        control_frame = RoundedLabelFrame(main_frame, text="2. Conversion Control & Progress")
        control_frame.grid(row=1, column=0, sticky='ew', pady=15)
        control_content = control_frame.content_frame
        control_content.grid_columnconfigure(0, weight=1)

        button_frame = ttk.Frame(control_content, style='Content.TFrame')
        button_frame.grid(row=0, column=0, columnspan=2, pady=5)
        self.start_button = ttk.Button(button_frame, text="Start Conversion", command=self.start_conversion)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(button_frame, text="Stop Conversion", command=self.stop_conversion, style='Stop.TButton', state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.current_file_label = ttk.Label(control_content, text="Waiting to start...", font=('Arial', 10, 'italic'))
        self.current_file_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(10, 2))
        
        self.current_progress = ttk.Progressbar(control_content, orient='horizontal', mode='determinate', style='spectrum.Horizontal.TProgressbar')
        self.current_progress.grid(row=2, column=0, sticky=tk.EW, pady=2)
        self.current_percent_label = ttk.Label(control_content, text="0%", font=('Arial', 10, 'bold'))
        self.current_percent_label.grid(row=2, column=1, padx=(10,0))
        
        ttk.Label(control_content, text="Overall Progress:").grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 2))
        self.overall_progress = ttk.Progressbar(control_content, orient='horizontal', mode='determinate')
        self.overall_progress.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=2)

        # --- Log Output Frame ---
        log_frame = RoundedLabelFrame(main_frame, text="3. Conversion Log")
        log_frame.grid(row=2, column=0, sticky='nsew', pady=5)
        self.log_text = scrolledtext.ScrolledText(log_frame.content_frame, state='disabled', wrap=tk.WORD,
                                                 bg=CONTENT_BG, fg=TEXT_COLOR, relief=tk.FLAT, bd=0, insertbackground=TEXT_COLOR)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.root.after(100, self.process_queues)

    def select_input_dir(self):
        dir_path = filedialog.askdirectory(title="Select Input Directory")
        if dir_path: self.input_dir.set(dir_path)

    def select_output_dir(self):
        dir_path = filedialog.askdirectory(title="Select Output Directory")
        if dir_path: self.output_dir.set(dir_path)

    def log(self, message): self.log_queue.put(message)
    def update_progress(self, percent): self.progress_queue.put(percent)

    def get_color_for_progress(self, percent):
        r = int(PROGRESS_RED[0] + (PROGRESS_BLUE[0] - PROGRESS_RED[0]) * (percent / 100))
        g = int(PROGRESS_RED[1] + (PROGRESS_BLUE[1] - PROGRESS_RED[1]) * (percent / 100))
        b = int(PROGRESS_RED[2] + (PROGRESS_BLUE[2] - PROGRESS_RED[2]) * (percent / 100))
        return f'#{r:02x}{g:02x}{b:02x}'

    def process_queues(self):
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.config(state='normal')
                self.log_text.insert(tk.END, message)
                self.log_text.see(tk.END)
                self.log_text.config(state='disabled')
        except queue.Empty: pass
        try:
            while True:
                percent = self.progress_queue.get_nowait()
                self.current_progress['value'] = percent
                self.current_percent_label.config(text=f"{int(percent)}%")
                self.style.configure('spectrum.Horizontal.TProgressbar', background=self.get_color_for_progress(percent))
        except queue.Empty: pass
        finally: self.root.after(100, self.process_queues)

    def start_conversion(self):
        if not os.path.isdir(self.input_dir.get()) or not os.path.isdir(self.output_dir.get()):
            self.log("Error: Please select valid input and output directories.\n")
            return
        
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.log_text.config(state='normal'); self.log_text.delete('1.0', tk.END); self.log_text.config(state='disabled')
        self.stop_event.clear()
        
        threading.Thread(target=self.run_conversion_thread, args=(self.input_dir.get(), self.output_dir.get()), daemon=True).start()

    def stop_conversion(self):
        self.log("Stopping conversion...\n")
        self.stop_event.set()
        if self.running_process:
            self.running_process.terminate() # Forcefully stop the svo_export.py script

    def set_gui_state(self, is_running):
        self.start_button.config(state='disabled' if is_running else 'normal')
        self.stop_button.config(state='normal' if is_running else 'disabled')

    def run_conversion_thread(self, input_path, output_path):
        svo_files = sorted([f for f in os.listdir(input_path) if f.lower().endswith(('.svo', '.svo2'))])
        if not svo_files:
            self.log("No .svo or .svo2 files found.\n")
            self.set_gui_state(False)
            return

        self.log(f"Found {len(svo_files)} files to convert.\n{'='*50}\n")
        self.overall_progress['maximum'] = len(svo_files)
        
        for i, svo_file in enumerate(svo_files):
            if self.stop_event.is_set():
                self.log("Conversion stopped by user.\n")
                break
            
            self.overall_progress['value'] = i
            self.update_progress(0)
            
            self.root.after(0, lambda f=svo_file: self.current_file_label.config(text=f"Processing: {f}"))
            self.log(f"[{i+1}/{len(svo_files)}] Converting: {svo_file}\n")
            
            command = ["python", "-u", "svo_export.py", "--mode", "0", "--input_svo_file", os.path.join(input_path, svo_file), "--output_avi_file", os.path.join(output_path, f"{os.path.splitext(svo_file)[0]}.avi")]
            
            try:
                self.running_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
                for line in iter(self.running_process.stdout.readline, ''):
                    if self.stop_event.is_set(): break
                    match = re.search(r'(\d+)%', line)
                    if match: self.update_progress(int(match.group(1)))
                    elif "Converting SVO..." not in line.strip(): self.log(line)
                self.running_process.wait()
            except Exception as e:
                self.log(f"FATAL ERROR: {e}\n")
                break
            finally:
                self.running_process = None

            if not self.stop_event.is_set():
                self.update_progress(100)
                self.log(f"SUCCESS: Converted {svo_file}\n{'='*50}\n")
        
        self.root.after(0, lambda: self.current_file_label.config(text="Finished!"))
        if not self.stop_event.is_set():
             self.overall_progress['value'] = len(svo_files)
        self.set_gui_state(False)

if __name__ == "__main__":
    root = tk.Tk()
    app = SVOConverterApp(root)
    root.mainloop()
