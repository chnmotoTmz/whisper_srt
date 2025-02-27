# Whisper 文字起こしツール

動画ファイルから音声を抽出し、Whisperを使用して自動で文字起こしを行うGUIツールです。

## 機能

- 動画ファイルからの音声抽出
- Whisperによる音声認識
- EDLファイル生成（動画編集用）
- SRTファイル生成（字幕用）
- GPUサポート
- 進捗表示とログ出力

## 必要条件

- Python 3.8以上
- FFmpeg
- CUDA対応GPU（推奨）

## インストール

1. リポジトリをクローン：
```bash
git clone https://github.com/yourusername/video-transcriber.git
cd video-transcriber
```

2. 仮想環境を作成して有効化：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 依存パッケージをインストール：
```bash
pip install -r requirements.txt
```

## 使用方法

1. GUIアプリケーションを起動：
```bash
python gui_app.py
```

2. 「フォルダを選択」ボタンをクリックして、処理したい動画ファイルが含まれるフォルダを選択

3. 「処理開始」ボタンをクリックして文字起こしを開始

## 出力ファイル

- `.edl`: 動画編集ソフト用のタイムライン情報
- `.srt`: 字幕ファイル

## 注意事項

- 大きなファイルの処理には時間がかかる場合があります
- GPUメモリの使用量に注意してください
- 音声品質により認識精度が変わる場合があります

## ライセンス

MITライセンス