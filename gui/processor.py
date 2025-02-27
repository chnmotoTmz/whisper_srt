import os
from pathlib import Path
import logging
import concurrent.futures
import psutil
import torch
from utils.formatters import MLTFormatter

class VideoProcessor:
    def __init__(self, transcriber):
        self.transcriber = transcriber
        self.processing = False
        self.max_workers = min(psutil.cpu_count(logical=False) or 2, 4)
        self.all_segments = {}  # {video_path: [segments]} の辞書
        
    def process_single_file(self, video_path, options):
        try:
            if hasattr(torch.cuda, 'empty_cache'):
                torch.cuda.empty_cache()
                
            result = self.transcriber.process_video(
                video_path,
                generate_edl=options['generate_edl'],
                generate_srt=options['generate_srt'],
                generate_mlt=False  # 単一ファイルでは個別MLT不要
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
            
    def process_files(self, path, options, progress_callback, log_callback):
        try:
            self.processing = True
            self.all_segments.clear()  # 初期化
            
            if os.path.isfile(path):
                log_callback(f'ファイル処理開始: {path}')
                try:
                    result = self.transcriber.process_video(
                        path,
                        generate_edl=options['generate_edl'],
                        generate_srt=options['generate_srt'],
                        generate_mlt=False  # 単一ファイルでは個別MLT不要
                    )
                    self.all_segments[path] = result["segments"]
                    progress_callback(100, 0)
                    log_callback(f'処理完了: {os.path.basename(path)}')
                    if result['edl_path']:
                        log_callback(f'EDLファイル生成: {result["edl_path"]}')
                    if result['srt_path']:
                        log_callback(f'SRTファイル生成: {result["srt_path"]}')
                except Exception as e:
                    log_callback(f'エラー - {os.path.basename(path)}: {str(e)}', level=logging.ERROR)
                    
            else:
                video_files = []
                for ext in ['.mp4', '.mov', '.avi']:
                    video_files.extend(Path(path).glob(f'*{ext}'))
                    
                total_files = len(video_files)
                log_callback(f'フォルダ内の動画ファイル数: {total_files}')
                
                max_workers = min(self.max_workers, 2)
                processed_files = 0
                failed_files = []
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_file = {
                        executor.submit(
                            self.process_single_file,
                            str(video_file),
                            options
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
                                log_callback(f'処理完了 ({processed_files}/{total_files}): {video_file.name}')
                                self.all_segments[str(video_file)] = result['result']['segments']
                                if result['result']['edl_path']:
                                    log_callback(f'EDLファイル生成: {result["result"]["edl_path"]}')
                                if result['result']['srt_path']:
                                    log_callback(f'SRTファイル生成: {result["result"]["srt_path"]}')
                            else:
                                failed_files.append((video_file.name, result['error']))
                                log_callback(f'エラー - {video_file.name}: {result["error"]}', level=logging.ERROR)
                                
                            progress_callback(progress, 0)
                            
                        except Exception as e:
                            processed_files += 1
                            failed_files.append((video_file.name, str(e)))
                            log_callback(f'エラー - {video_file.name}: {str(e)}', level=logging.ERROR)
                            
                if failed_files:
                    log_callback("\n処理に失敗したファイル:", level=logging.WARNING)
                    for file_name, error in failed_files:
                        log_callback(f"- {file_name}: {error}", level=logging.WARNING)
                
                # 全動画のMLT生成
                if options.get('generate_mlt', False) and self.all_segments:
                    output_dir = path
                    mlt_path = os.path.join(output_dir, "combined.mlt")
                    mlt_content = MLTFormatter.generate(self.all_segments)
                    with open(mlt_path, "w", encoding="utf-8") as f:
                        f.write(mlt_content)
                    log_callback(f"結合MLTファイル生成完了: {mlt_path}")
                        
        finally:
            self.processing = False
            progress_callback(0, 0)
            log_callback('処理が完了しました')
            
    def cancel(self):
        self.processing = False 