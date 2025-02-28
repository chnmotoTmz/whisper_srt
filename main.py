import os
import sys

def process_files(edl_file, srt_file):
    """EDLファイルとSRTファイルを処理して結合する"""
    # EDLファイルを読み込む
    with open(edl_file, 'r', encoding='utf-8') as f:
        edl_content = f.read()
    
    # SRTファイルを読み込む
    with open(srt_file, 'r', encoding='utf-8') as f:
        srt_content = f.read()
    
    # 結合した内容を出力ファイルに書き込む
    output_file = os.path.splitext(edl_file)[0] + '_combined.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(edl_content + '\n\n' + srt_content)
    
    return output_file

def main():
    # コマンドライン引数からファイルパスを取得
    if len(sys.argv) != 3:
        print("使用方法: python main.py <EDLファイル> <SRTファイル>")
        sys.exit(1)
    
    edl_file = sys.argv[1]
    srt_file = sys.argv[2]
    
    # ファイルの存在確認
    if not os.path.exists(edl_file):
        print(f"エラー: EDLファイル '{edl_file}' が見つかりません。")
        sys.exit(1)
    if not os.path.exists(srt_file):
        print(f"エラー: SRTファイル '{srt_file}' が見つかりません。")
        sys.exit(1)
    
    # ファイルを処理
    output_file = process_files(edl_file, srt_file)
    print(f"結合されたファイルを保存しました: {output_file}")

if __name__ == "__main__":
    main() 