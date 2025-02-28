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
            self.cancel_flag = False
            directory = path if os.path.isdir(path) else os.path.dirname(path)
            
            # 結合ファイルのパスを設定
            combined_edl = os.path.join(directory, 'combined.edl')
            combined_srt = os.path.join(directory, 'combined.srt')
            
            # 既存のSRTファイルがない動画のみ文字起こしを実行
            video_files = []
            # 単一ファイルか確認
            if os.path.isfile(path):
                video_files = [Path(path)]
                log_callback(f"単一ファイルモード: {path}")
            else:
                video_files = list(Path(directory).glob('*.mp4')) + list(Path(directory).glob('*.mov')) + list(Path(directory).glob('*.avi'))
                log_callback(f"フォルダモード: {directory} ({len(video_files)}ファイル)")
            
            videos_needing_transcription = [
                video for video in video_files 
                if not video.with_suffix('.srt').exists() or options.get('force_transcribe', False)
            ]
            
            if videos_needing_transcription:
                total_files = len(videos_needing_transcription)
                for i, video_file in enumerate(videos_needing_transcription):
                    if self.cancel_flag:
                        log_callback("処理がキャンセルされました")
                        break
                    
                    progress = (i / total_files) * 50
                    progress_callback(progress)
                    
                    log_callback(f"文字起こし中 ({i+1}/{total_files}): {video_file.name}")
                    
                    try:
                        result = self.transcriber.process_video(
                            str(video_file),
                            generate_edl=options['generate_edl'],
                            generate_srt=options['generate_srt'],
                            generate_mlt=False
                        )
                    except Exception as e:
                        log_callback(f"エラー: {video_file.name} - {str(e)}")
                        continue
            else:
                log_callback("全ての動画にSRTファイルが存在します。文字起こしをスキップします。")
                progress_callback(50)
            
            if not self.cancel_flag:
                # EDLファイルの結合
                log_callback("EDLファイルを結合中...")
                progress_callback(75)
                if self.combine_files_by_extension(directory, 'edl', combined_edl):
                    log_callback(f"EDLファイルを結合: {combined_edl}")
                else:
                    log_callback("警告: 結合可能なEDLファイルが見つかりませんでした")
                
                # SRTファイルの結合
                log_callback("SRTファイルを結合中...")
                progress_callback(90)
                if self.combine_files_by_extension(directory, 'srt', combined_srt):
                    log_callback(f"SRTファイルを結合: {combined_srt}")
                else:
                    log_callback("警告: 結合可能なSRTファイルが見つかりませんでした")
                
                progress_callback(100)
                log_callback("すべての処理が完了しました")
            
            self.processing = False
            
        except Exception as e:
            log_callback(f"エラーが発生しました: {str(e)}")
            self.processing = False
            raise
            
    def combine_files_by_extension(self, directory, extension, output_path):
        """指定された拡張子のファイルを結合"""
        import os
        
        files = list(Path(directory).glob(f'*.{extension}'))
        if not files:
            return False
            
        with open(output_path, 'w', encoding='utf-8') as outfile:
            for file in files:
                if file.name != os.path.basename(output_path):  # 結合先ファイルを除外
                    with open(file, 'r', encoding='utf-8') as infile:
                        outfile.write(f"# {file.name}\n")
                        outfile.write(infile.read())
                        outfile.write("\n\n")
        return True
            
    def cancel(self):
        self.cancel_flag = True
        self.processing = False 