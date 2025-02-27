from datetime import timedelta

class EDLFormatter:
    HEADER_TEMPLATE = """TITLE: {title}
FCM: NON-DROP FRAME

"""
    
    ENTRY_TEMPLATE = """{number:03d}  AX       AA/V  C        {start_tc} {end_tc}
* FROM CLIP NAME: {clip_name}
* TEXT: {clip_name}

"""
    
    @staticmethod
    def format_timecode(seconds):
        """秒数をEDLタイムコード形式（HH:MM:SS:FF）に変換"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        frames = min(int((seconds % 1) * 24), 23)  # 24fps想定、23フレームまで
        return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"
        
    @classmethod
    def generate(cls, segments, title="Audio Transcription"):
        """EDLファイルの内容を生成"""
        content = cls.HEADER_TEMPLATE.format(title=title)
        
        for i, segment in enumerate(segments, 1):
            if not cls.is_valid_segment(segment):
                continue
                
            content += cls.ENTRY_TEMPLATE.format(
                number=i,
                start_tc=cls.format_timecode(segment["start"]),
                end_tc=cls.format_timecode(segment["end"]),
                clip_name=segment.get("file_name", ""),
                text=segment["text"].strip()
            )
            
        return content
        
    @staticmethod
    def is_valid_segment(segment):
        """セグメントの妥当性をチェック"""
        return (isinstance(segment, dict) and
                "start" in segment and
                "end" in segment and
                segment["end"] > segment["start"] and
                segment.get("text", "").strip())

class SRTFormatter:
    ENTRY_TEMPLATE = """{number}
{start_time} --> {end_time}
{text}

"""
    
    @staticmethod
    def format_timestamp(seconds):
        """秒数をSRT形式のタイムスタンプ（HH:MM:SS,mmm）に変換"""
        time = timedelta(seconds=seconds)
        hours = int(time.total_seconds() // 3600)
        minutes = int((time.total_seconds() % 3600) // 60)
        seconds = time.total_seconds() % 60
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{int((seconds % 1) * 1000):03d}"
        
    @classmethod
    def generate(cls, segments, include_filename=False):
        """SRTファイルの内容を生成"""
        content = ""
        
        for i, segment in enumerate(segments, 1):
            if not cls.is_valid_segment(segment):
                continue
                
            text = segment["text"].strip()
            if include_filename and "file_name" in segment:
                text = f"[{segment['file_name']}] {text}"
                
            content += cls.ENTRY_TEMPLATE.format(
                number=i,
                start_time=cls.format_timestamp(segment["start"]),
                end_time=cls.format_timestamp(segment["end"]),
                text=text
            )
            
        return content
        
    @staticmethod
    def is_valid_segment(segment):
        """セグメントの妥当性をチェック"""
        return (isinstance(segment, dict) and
                "start" in segment and
                "end" in segment and
                segment["end"] > segment["start"] and
                segment.get("text", "").strip())

class MLTFormatter:
    MLT_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<mlt>
{producers}
  <playlist id="playlist0">
{entries}
  </playlist>
  <tractor id="tractor0">
    <track producer="playlist0"/>
  </tractor>
</mlt>
"""

    PRODUCER_TEMPLATE = """  <producer id="producer{id}" resource="{video_path}"/>
"""

    ENTRY_TEMPLATE = """    <entry producer="producer{id}" in="{start_sec:.3f}" out="{end_sec:.3f}">
      <property name="shotcut:caption">{text}</property>
    </entry>
"""

    @classmethod
    def generate(cls, video_segments_dict):
        """複数動画のセグメントからMLTを生成
        video_segments_dict: {video_path: [segments]} の辞書
        """
        producers = ""
        entries = ""
        producer_ids = {}  # video_path と producer ID のマッピング
        
        # 各動画ファイルに一意の producer ID を割り当て
        for i, video_path in enumerate(video_segments_dict.keys()):
            producer_id = f"{i}"
            producer_ids[video_path] = producer_id
            producers += cls.PRODUCER_TEMPLATE.format(id=producer_id, video_path=video_path)
        
        # すべてのセグメントを1つのプレイリストに追加
        for video_path, segments in video_segments_dict.items():
            producer_id = producer_ids[video_path]
            for segment in segments:
                if not cls.is_valid_segment(segment):
                    continue
                entries += cls.ENTRY_TEMPLATE.format(
                    id=producer_id,
                    start_sec=segment["start"],
                    end_sec=segment["end"],
                    text=segment["text"].strip()
                )
        
        return cls.MLT_TEMPLATE.format(producers=producers, entries=entries)

    @staticmethod
    def is_valid_segment(segment):
        """セグメントの妥当性をチェック"""
        return (isinstance(segment, dict) and
                "start" in segment and
                "end" in segment and
                segment["end"] > segment["start"] and
                segment.get("text", "").strip()) 