import os
import whisper
import torch
import tempfile
import ffmpeg
import logging
from utils.formatters import EDLFormatter, SRTFormatter, MLTFormatter

class WhisperTranscriber:
    def __init__(self, model_name="small", use_gpu=True, logger=None):
        self.device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        self.logger = logger
        if self.device == "cuda":
            torch.cuda.empty_cache()
        self._log(f"デバイス: {self.device}")
        self._log(f"選択モデル: {model_name}")
        self._log("モデルをロード中...")
        self.model = None
        self.model_name = model_name
        self.model_loaded = False
        self._load_model()
        self._log("モデルのロードが完了しました")

    def _log(self, message, level=logging.INFO):
        """ログメッセージをGUIとコンソールの両方に出力"""
        if self.logger:
            self.logger.log(level, message)
        else:
            print(message)

    def _load_model(self):
        try:
            if self.device == "cuda":
                self._log(f"GPUメモリ使用量（ロード前）: {torch.cuda.memory_allocated() / 1024**2:.2f}MB")
            self.model = whisper.load_model(self.model_name).to(self.device)
            self.model_loaded = True
            if self.device == "cuda":
                self._log(f"GPUメモリ使用量（ロード後）: {torch.cuda.memory_allocated() / 1024**2:.2f}MB")
        except Exception as e:
            self._log(f"モデルのロードに失敗しました: {str(e)}", level=logging.ERROR)
            self.model_loaded = False
            raise

    def is_model_ready(self):
        return self.model_loaded and self.model is not None

    def wait_for_model(self):
        if not self.is_model_ready():
            self._load_model()

    def extract_audio(self, video_path, output_path=None):
        """音声を抽出し、Whisper用に適切なフォーマットに変換します"""
        if output_path is None:
            # デバッグ用に一時ファイルを固定パスに保存
            temp_dir = os.path.dirname(video_path)
            output_path = os.path.join(temp_dir, f"debug_{os.path.basename(video_path)}.wav")
        
        try:
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"動画ファイルが見つかりません: {video_path}")

            # 入力ファイルの情報を取得
            probe = ffmpeg.probe(video_path)
            self._log(f"\n入力ファイル情報 - {video_path}:")
            for stream in probe['streams']:
                self._log(f"ストリーム: {stream['codec_type']}, コーデック: {stream.get('codec_name', 'N/A')}")

            audio_streams = [stream for stream in probe['streams'] if stream['codec_type'] == 'audio']
            if not audio_streams:
                raise ValueError(f"動画に音声ストリームが含まれていません: {video_path}")

            self._log(f"\n音声ストリーム情報:")
            self._log(f"サンプルレート: {audio_streams[0].get('sample_rate', 'N/A')}")
            self._log(f"チャンネル数: {audio_streams[0].get('channels', 'N/A')}")
            self._log(f"コーデック: {audio_streams[0].get('codec_name', 'N/A')}")

            # 音声抽出とフォーマット変換
            stream = ffmpeg.input(video_path)
            stream = ffmpeg.output(stream, output_path,
                                acodec='pcm_s16le',  # 16ビットPCM
                                ac=1,                # モノラル
                                ar='16k',           # 16kHz
                                loglevel='error',   # エラーのみ表示
                                threads=0)          # 自動スレッド数
            
            self._log(f"\n音声抽出開始: {output_path}")
            ffmpeg.run(stream, capture_stdout=True, capture_stderr=True, overwrite_output=True)

            # 出力ファイルの検証
            if not os.path.exists(output_path):
                raise FileNotFoundError(f"音声ファイルの生成に失敗しました: {output_path}")
            
            file_size = os.path.getsize(output_path)
            if file_size < 1024:  # 1KB未満は異常と判断
                raise ValueError(f"生成された音声ファイルが不正です（サイズ: {file_size}バイト）: {output_path}")

            # 出力ファイルの情報を確認
            output_probe = ffmpeg.probe(output_path)
            self._log(f"\n出力音声ファイル情報:")
            self._log(f"サイズ: {file_size / 1024:.2f}KB")
            self._log(f"フォーマット: {output_probe['format']['format_name']}")
            self._log(f"デュレーション: {output_probe['format']['duration']}秒")
            self._log(f"ビットレート: {output_probe['format'].get('bit_rate', 'N/A')}bps")

            # デバッグ用に音声ファイルを保持
            self._log(f"音声ファイルを保存: {output_path}（手動確認用）")
            return output_path

        except ffmpeg.Error as e:
            error_message = e.stderr.decode() if e.stderr else str(e)
            self._log(f"FFmpeg エラー: {error_message}", level=logging.ERROR)
            if os.path.exists(output_path):
                os.remove(output_path)
            raise
        except Exception as e:
            self._log(f"音声抽出エラー: {str(e)}", level=logging.ERROR)
            if os.path.exists(output_path):
                os.remove(output_path)
            raise

    def process_video(self, video_path, output_dir=None, generate_edl=True, generate_srt=True, generate_mlt=False):
        """動画を処理し、EDL、SRT、MLTファイルを生成します"""
        if not self.is_model_ready():
            self.wait_for_model()

        if output_dir is None:
            output_dir = os.path.dirname(video_path)
            
        audio_path = None
        try:
            # GPUメモリをクリア
            if self.device == "cuda":
                torch.cuda.empty_cache()
                self._log(f"\nGPUメモリ使用量（処理前）: {torch.cuda.memory_allocated() / 1024**2:.2f}MB")

            # 音声抽出
            audio_path = self.extract_audio(video_path)
            
            self._log("\nWhisper処理開始...")
            try:
                # Whisperで音声認識
                result = self.model.transcribe(
                    audio_path,
                    language="ja",
                    task="transcribe",
                    verbose=True,
                    initial_prompt=None,
                    condition_on_previous_text=False,
                    temperature=0.0,
                    best_of=1,
                    beam_size=1,
                    word_timestamps=True,
                    fp16=True
                )
            except Exception as e:
                self._log(f"Whisper処理エラー: {str(e)}", level=logging.ERROR)
                if self.device == "cuda":
                    self._log(f"GPUメモリ使用量（エラー時）: {torch.cuda.memory_allocated() / 1024**2:.2f}MB")
                raise
            
            if self.device == "cuda":
                self._log(f"GPUメモリ使用量（Whisper処理後）: {torch.cuda.memory_allocated() / 1024**2:.2f}MB")
            
            # デバッグ用にセグメント情報を出力
            self._log(f"\n認識結果 - {video_path}:")
            for seg in result.get("segments", []):
                self._log(f"Start: {seg['start']:.2f}, End: {seg['end']:.2f}, Text: {seg['text']}")
            
            if not result or 'segments' not in result:
                raise ValueError(f"音声認識結果が不正です: {video_path}")

            # セグメントの前処理
            valid_segments = []
            file_name = os.path.basename(video_path)
            for segment in result["segments"]:
                if segment["end"] > segment["start"] and segment["text"].strip():
                    segment["file_name"] = file_name
                    valid_segments.append(segment)

            self._log(f"\n有効なセグメント数: {len(valid_segments)}/{len(result['segments'])}")

            base_name = os.path.splitext(os.path.basename(video_path))[0]
            edl_path = None
            srt_path = None
            mlt_path = None
            
            # EDLファイルの生成
            if generate_edl:
                edl_path = os.path.join(output_dir, f"{base_name}.edl")
                edl_content = EDLFormatter.generate(valid_segments, title=f"Transcription - {base_name}")
                with open(edl_path, "w", encoding="utf-8") as f:
                    f.write(edl_content)
                self._log(f"EDLファイル生成完了: {edl_path}")
                
            # SRTファイルの生成
            if generate_srt:
                srt_path = os.path.join(output_dir, f"{base_name}.srt")
                srt_content = SRTFormatter.generate(valid_segments, include_filename=True)
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write(srt_content)
                self._log(f"SRTファイル生成完了: {srt_path}")
                
            # MLTファイルの生成（単一ファイルの場合）
            if generate_mlt:
                mlt_path = os.path.join(output_dir, f"{base_name}.mlt")
                mlt_content = MLTFormatter.generate({video_path: valid_segments})
                with open(mlt_path, "w", encoding="utf-8") as f:
                    f.write(mlt_content)
                self._log(f"MLTファイル生成完了: {mlt_path}")
                
            return {
                "edl_path": edl_path,
                "srt_path": srt_path,
                "mlt_path": mlt_path,
                "segments": valid_segments,
                "text": result["text"],
                "file_path": video_path
            }
            
        except Exception as e:
            self._log(f"処理エラー - {video_path}: {str(e)}", level=logging.ERROR)
            raise
            
        finally:
            if self.device == "cuda":
                torch.cuda.empty_cache()
                self._log(f"GPUメモリ使用量（終了時）: {torch.cuda.memory_allocated() / 1024**2:.2f}MB")

# インスタンス生成（GPUモードをデフォルトに）
transcriber = WhisperTranscriber(model_name="medium", use_gpu=True) 