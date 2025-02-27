import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
from whisper_integration import WhisperTranscriber
import threading
from pathlib import Path
import time
import logging
import json
from datetime import timedelta
import concurrent.futures
import queue
import psutil
import torch

class WhisperGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Whisper 文字起こしツール')
        self.root.geometry('1200x800')  # ウィンドウサイズを大きくして、ログエリアを広げる
        
        # CPU数の取得（並列処理用）
        self.max_workers = min(psutil.cpu_count(logical=False) or 2, 4)  # 物理コア数を使用、最大4
        
        self.transcriber = WhisperTranscriber()
        self.processing = False
        self.temp_results = []  # 一時的な処理結果を保存
        self.result_queue = queue.Queue()  # 処理結果を保存するキュー
        
        # ロガーの設定
        self.setup_logger()
        
        self.create_widgets()
        
    def setup_logger(self):
        self.logger = logging.getLogger('WhisperGUI')
        self.logger.setLevel(logging.INFO)
        
        # コンソールハンドラ
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
    def create_widgets(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # タイトル
        title_label = ttk.Label(main_frame, text='Whisper 文字起こしツール', font=('Helvetica', 16))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)
        
        # パス入力フレーム
        path_frame = ttk.LabelFrame(main_frame, text='ファイル/フォルダ選択', padding="5")
        path_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=60)
        path_entry.grid(row=0, column=0, padx=5)
        
        folder_button = ttk.Button(path_frame, text='フォルダ選択', command=self.select_folder)
        folder_button.grid(row=0, column=1, padx=5)
        
        file_button = ttk.Button(path_frame, text='ファイル選択', command=self.select_file)
        file_button.grid(row=0, column=2, padx=5)
        
        # オプションフレーム
        option_frame = ttk.LabelFrame(main_frame, text='出力オプション', padding="5")
        option_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.edl_var = tk.BooleanVar(value=True)
        edl_check = ttk.Checkbutton(option_frame, text='EDLファイルを生成', variable=self.edl_var)
        edl_check.grid(row=0, column=0, padx=20)
        
        self.srt_var = tk.BooleanVar(value=True)
        srt_check = ttk.Checkbutton(option_frame, text='SRTファイルを生成', variable=self.srt_var)
        srt_check.grid(row=0, column=1, padx=20)
        
        # 進捗表示フレーム
        progress_frame = ttk.LabelFrame(main_frame, text='進捗状況', padding="5")
        progress_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # 進捗バー
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(progress_frame, length=700, mode='determinate', variable=self.progress_var)
        self.progress.grid(row=0, column=0, columnspan=3, pady=5)
        
        # 進捗ラベル
        self.progress_label = ttk.Label(progress_frame, text="0% 完了")
        self.progress_label.grid(row=1, column=0, columnspan=3, pady=5)
        
        # 処理時間ラベル
        self.time_label = ttk.Label(progress_frame, text="処理時間: 0.00秒")
        self.time_label.grid(row=2, column=0, columnspan=3, pady=5)
        
        # ログ表示エリア（2列に分割）
        log_frame = ttk.LabelFrame(main_frame, text='処理ログ', padding="5")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # GUIログ
        gui_log_frame = ttk.LabelFrame(log_frame, text='GUIログ', padding="5")
        gui_log_frame.grid(row=0, column=0, padx=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.log_area = scrolledtext.ScrolledText(gui_log_frame, width=50, height=15)
        self.log_area.grid(row=0, column=0, padx=5, pady=5)
        
        # コンソールログ
        console_log_frame = ttk.LabelFrame(log_frame, text='コンソールログ', padding="5")
        console_log_frame.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.console_area = scrolledtext.ScrolledText(console_log_frame, width=50, height=15)
        self.console_area.grid(row=0, column=0, padx=5, pady=5)
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=10)
        
        self.start_button = ttk.Button(button_frame, text='処理開始', command=self.start_processing)
        self.start_button.grid(row=0, column=0, padx=10)
        
        self.cancel_button = ttk.Button(button_frame, text='キャンセル', command=self.cancel_processing, state='disabled')
        self.cancel_button.grid(row=0, column=1, padx=10)
        
        quit_button = ttk.Button(button_frame, text='終了', command=self.root.quit)
        quit_button.grid(row=0, column=2, padx=10)
        
    def log(self, message, level=logging.INFO):
        # GUIログエリアに出力
        self.log_area.insert(tk.END, message + '\n')
        self.log_area.see(tk.END)
        
        # コンソールログエリアに出力
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        console_message = f'{timestamp} - {message}'
        self.console_area.insert(tk.END, console_message + '\n')
        self.console_area.see(tk.END)
        
        # 実際のコンソールにも出力
        self.logger.log(level, message)
        
    def update_progress(self, progress, current_time):
        self.progress_var.set(progress)
        self.progress_label.config(text=f"{progress:.1f}% 完了")
        self.time_label.config(text=f"処理時間: {current_time:.2f}秒")
        
    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.path_var.set(folder_path)
            
    def select_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[('動画ファイル', '*.mp4 *.mov *.avi')]
        )
        if file_path:
            self.path_var.set(file_path)
            
    def process_single_file(self, video_path, generate_edl, generate_srt):
        """単一ファイルの処理（エラーハンドリング強化版）"""
        try:
            # GPUメモリをクリア
            if hasattr(torch.cuda, 'empty_cache'):
                torch.cuda.empty_cache()

            result = self.transcriber.process_video(
                video_path,
                generate_edl=generate_edl,
                generate_srt=generate_srt
            )
            return {
                'success': True,
                'file_path': video_path,
                'result': result,
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'file_path': video_path,
                'result': None,
                'error': str(e)
            }
            
    def process_files(self, path, generate_edl, generate_srt):
        try:
            self.processing = True
            self.start_button.config(state='disabled')
            self.cancel_button.config(state='normal')
            
            if os.path.isfile(path):
                self.log(f'ファイル処理開始: {path}')
                self.progress_var.set(0)
                
                try:
                    result = self.transcriber.process_video(
                        path,
                        generate_edl=generate_edl,
                        generate_srt=generate_srt
                    )
                    self.progress_var.set(100)
                    self.log(f'処理完了: {os.path.basename(path)}')
                    if result['edl_path']:
                        self.log(f'EDLファイル生成: {result["edl_path"]}')
                    if result['srt_path']:
                        self.log(f'SRTファイル生成: {result["srt_path"]}')
                except Exception as e:
                    self.log(f'エラー - {os.path.basename(path)}: {str(e)}', level=logging.ERROR)
                    
            else:
                video_files = []
                for ext in ['.mp4', '.mov', '.avi']:
                    video_files.extend(Path(path).glob(f'*{ext}'))
                
                total_files = len(video_files)
                self.log(f'フォルダ内の動画ファイル数: {total_files}')
                
                # 並列処理数を制限（GPUメモリ対策）
                max_workers = min(self.max_workers, 2)
                processed_files = 0
                failed_files = []
                
                # ThreadPoolExecutorで並列処理
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_file = {
                        executor.submit(
                            self.process_single_file,
                            str(video_file),
                            generate_edl,
                            generate_srt
                        ): video_file
                        for video_file in video_files
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_file):
                        if not self.processing:
                            executor.shutdown(wait=False)
                            break
                            
                        video_file = future_to_file[future]
                        try:
                            result = future.result()
                            processed_files += 1
                            progress = (processed_files / total_files) * 100
                            
                            if result['success']:
                                self.log(f'処理完了 ({processed_files}/{total_files}): {video_file.name}')
                            else:
                                failed_files.append((video_file.name, result['error']))
                                self.log(f'エラー - {video_file.name}: {result["error"]}', level=logging.ERROR)
                                
                            self.progress_var.set(progress)
                            
                        except Exception as e:
                            processed_files += 1
                            failed_files.append((video_file.name, str(e)))
                            self.log(f'エラー - {video_file.name}: {str(e)}', level=logging.ERROR)
                            
                # エラー発生ファイルの一覧を表示
                if failed_files:
                    self.log("\n処理に失敗したファイル:", level=logging.WARNING)
                    for file_name, error in failed_files:
                        self.log(f"- {file_name}: {error}", level=logging.WARNING)
                        
        except Exception as e:
            self.log(f'エラーが発生しました: {str(e)}', level=logging.ERROR)
            messagebox.showerror('エラー', str(e))
            
        finally:
            self.processing = False
            self.start_button.config(state='normal')
            self.cancel_button.config(state='disabled')
            self.progress_var.set(0)
            self.log('処理が完了しました')
            
    def _generate_combined_edl(self, output_path):
        """複数の処理結果を統合してEDLファイルを生成"""
        # 全セグメントを1つのリストにまとめる
        all_segments = []
        for result in self.temp_results:
            file_name = os.path.basename(result['file_path'])
            segments = result.get('segments', [])
            for segment in segments:
                # セグメントの妥当性チェック
                if not isinstance(segment, dict) or 'start' not in segment or 'end' not in segment:
                    continue
                    
                # 極端に短いセグメントは除外
                if segment['end'] - segment['start'] < 0.5:
                    continue
                    
                all_segments.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text'].strip(),
                    'file_name': file_name
                })

        # 開始時間でソート
        all_segments.sort(key=lambda x: x['start'])

        # EDLファイルの生成
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("TITLE: Combined Audio Transcription\n")
            f.write("FCM: NON-DROP FRAME\n\n")

            for i, segment in enumerate(all_segments, 1):
                # EDLのタイムコードフォーマットに変換（HH:MM:SS:FF）
                start_tc = self._format_edl_timecode(segment['start'])
                end_tc = self._format_edl_timecode(segment['end'])
                
                # EDLエントリの生成
                f.write(f"{i:03d}  AX       AA/V  C        {start_tc} {end_tc}\n")
                f.write(f"* FROM CLIP NAME: {segment['file_name']}\n")
                f.write(f"* TEXT: {segment['text']}\n\n")

    def _format_edl_timecode(self, seconds):
        """秒数をEDLタイムコード形式（HH:MM:SS:FF）に変換"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        frames = int((seconds % 1) * 24)  # 24fpsを想定
        
        # フレーム数が24を超えないようにする
        frames = min(frames, 23)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"
        
    def _generate_combined_srt(self, output_path):
        """複数の処理結果を統合してSRTファイルを生成"""
        with open(output_path, "w", encoding="utf-8") as f:
            current_index = 1
            
            for result in self.temp_results:
                file_name = os.path.basename(result['file_path'])
                segments = result.get('segments', [])
                
                for segment in segments:
                    start_time = self._format_timestamp(segment["start"])
                    end_time = self._format_timestamp(segment["end"])
                    text = segment["text"].strip()
                    
                    f.write(f"{current_index}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"[{file_name}] {text}\n\n")
                    
                    current_index += 1
                    
    def _format_timestamp(self, seconds):
        """秒数をSRT形式のタイムスタンプに変換"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds % 1) * 1000)
        seconds = int(seconds)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
        
    def start_processing(self):
        path = self.path_var.get()
        if not path:
            messagebox.showwarning('警告', 'フォルダまたはファイルを選択してください')
            return
            
        if not os.path.exists(path):
            messagebox.showerror('エラー', '指定されたパスが存在しません')
            return
            
        # モデルの準備状態を確認
        try:
            if not self.transcriber.is_model_ready():
                self.log("モデルの準備中です。しばらくお待ちください...", level=logging.INFO)
                self.transcriber.wait_for_model()
        except Exception as e:
            self.log(f"モデルの準備に失敗しました: {str(e)}", level=logging.ERROR)
            messagebox.showerror('エラー', 'モデルの準備に失敗しました')
            return
            
        # 処理スレッドの開始
        thread = threading.Thread(
            target=self.process_files,
            args=(path, self.edl_var.get(), self.srt_var.get()),
            daemon=True
        )
        thread.start()
        
    def cancel_processing(self):
        self.processing = False
        self.log('処理をキャンセルしています...')
        
    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    app = WhisperGUI()
    app.run() 