import tkinter as tk
from tkinter import ttk, scrolledtext
import time
import logging

class LogFrame(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text='処理ログ', padding="5")
        self.create_widgets()
        
    def create_widgets(self):
        # GUIログ
        gui_log_frame = ttk.LabelFrame(self, text='GUIログ', padding="5")
        gui_log_frame.grid(row=0, column=0, padx=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.log_area = scrolledtext.ScrolledText(gui_log_frame, width=50, height=15)
        self.log_area.grid(row=0, column=0, padx=5, pady=5)
        
        # コンソールログ
        console_log_frame = ttk.LabelFrame(self, text='コンソールログ', padding="5")
        console_log_frame.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.console_area = scrolledtext.ScrolledText(console_log_frame, width=50, height=15)
        self.console_area.grid(row=0, column=0, padx=5, pady=5)
        
    def log(self, message, level=logging.INFO):
        # GUIログ
        self.log_area.insert(tk.END, message + '\n')
        self.log_area.see(tk.END)
        
        # コンソールログ
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        console_message = f'{timestamp} - {message}'
        self.console_area.insert(tk.END, console_message + '\n')
        self.console_area.see(tk.END)

class ProgressFrame(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text='進捗状況', padding="5")
        self.create_widgets()
        
    def create_widgets(self):
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self, length=700, mode='determinate', variable=self.progress_var)
        self.progress.grid(row=0, column=0, columnspan=3, pady=5)
        
        self.progress_label = ttk.Label(self, text="0% 完了")
        self.progress_label.grid(row=1, column=0, columnspan=3, pady=5)
        
        self.time_label = ttk.Label(self, text="処理時間: 0.00秒")
        self.time_label.grid(row=2, column=0, columnspan=3, pady=5)
        
    def update_progress(self, progress, current_time):
        self.progress_var.set(progress)
        self.progress_label.config(text=f"{progress:.1f}% 完了")
        self.time_label.config(text=f"処理時間: {current_time:.2f}秒")

class OptionFrame(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text='出力オプション', padding="5")
        self.create_widgets()
        
    def create_widgets(self):
        self.edl_var = tk.BooleanVar(value=True)
        edl_check = ttk.Checkbutton(self, text='EDLファイルを生成', variable=self.edl_var)
        edl_check.grid(row=0, column=0, padx=20)
        
        self.srt_var = tk.BooleanVar(value=True)
        srt_check = ttk.Checkbutton(self, text='SRTファイルを生成', variable=self.srt_var)
        srt_check.grid(row=0, column=1, padx=20)
        
        self.mlt_var = tk.BooleanVar(value=True)
        mlt_check = ttk.Checkbutton(self, text='MLTファイルを生成', variable=self.mlt_var)
        mlt_check.grid(row=0, column=2, padx=20)
        
    def get_options(self):
        return {
            'generate_edl': self.edl_var.get(),
            'generate_srt': self.srt_var.get(),
            'generate_mlt': self.mlt_var.get()
        } 