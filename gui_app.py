import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
from whisper_integration import WhisperTranscriber
import threading
from pathlib import Path
import logging
from gui.components import LogFrame, ProgressFrame, OptionFrame
from gui.processor import VideoProcessor

class WhisperGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Whisper 文字起こしツール')
        self.root.geometry('1200x800')
        
        self.transcriber = WhisperTranscriber()
        self.processor = VideoProcessor(self.transcriber)
        self.setup_logger()
        self.create_widgets()
        
    def setup_logger(self):
        self.logger = logging.getLogger('WhisperGUI')
        self.logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(console_handler)
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # タイトル
        title_label = ttk.Label(main_frame, text='Whisper 文字起こしツール', font=('Helvetica', 16))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)
        
        # パス選択
        self.path_var = tk.StringVar()
        path_frame = ttk.LabelFrame(main_frame, text='ファイル/フォルダ選択', padding="5")
        path_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=60)
        path_entry.grid(row=0, column=0, padx=5)
        
        ttk.Button(path_frame, text='フォルダ選択', command=self.select_folder).grid(row=0, column=1, padx=5)
        ttk.Button(path_frame, text='ファイル選択', command=self.select_file).grid(row=0, column=2, padx=5)
        
        # オプション
        self.option_frame = OptionFrame(main_frame)
        self.option_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # 進捗
        self.progress_frame = ProgressFrame(main_frame)
        self.progress_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # ログ
        self.log_frame = LogFrame(main_frame)
        self.log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=10)
        
        self.start_button = ttk.Button(button_frame, text='処理開始', command=self.start_processing)
        self.start_button.grid(row=0, column=0, padx=10)
        
        self.cancel_button = ttk.Button(button_frame, text='キャンセル', command=self.cancel_processing, state='disabled')
        self.cancel_button.grid(row=0, column=1, padx=10)
        
        ttk.Button(button_frame, text='終了', command=self.root.quit).grid(row=0, column=2, padx=10)
        
    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.path_var.set(folder_path)
            
    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[('動画ファイル', '*.mp4 *.mov *.avi')])
        if file_path:
            self.path_var.set(file_path)
            
    def start_processing(self):
        path = self.path_var.get()
        if not path:
            messagebox.showerror('エラー', 'ファイルまたはフォルダを選択してください。')
            return
            
        self.start_button.config(state='disabled')
        self.cancel_button.config(state='normal')
        
        thread = threading.Thread(
            target=self.processor.process_files,
            args=(
                path,
                self.option_frame.get_options(),
                self.progress_frame.update_progress,
                self.log_frame.log
            )
        )
        thread.start()
        
    def cancel_processing(self):
        self.processor.cancel()
        self.start_button.config(state='normal')
        self.cancel_button.config(state='disabled')
        
    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    app = WhisperGUI()
    app.run() 