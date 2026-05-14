
import os
import subprocess
import glob

def convert_mp3_to_wav_in_dir(target_dir, delete_original=False):
    """
    指定したディレクトリ内のすべての .mp3 ファイルを .wav (PCM16) に変換する
    """
    if not os.path.exists(target_dir):
        print(f"[Error] Directory not found: {target_dir}")
        return

    # カレントディレクトリをプロジェクトルートに合わせる
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    mp3_files = glob.glob(os.path.join(target_dir, "*.mp3"))
    
    if not mp3_files:
        print(f"[Info] No .mp3 files found in {target_dir}")
        return

    print(f"--- Starting conversion in {target_dir} ---")
    success_count = 0
    
    for mp3_path in mp3_files:
        filename = os.path.basename(mp3_path)
        name_no_ext = os.path.splitext(filename)[0]
        wav_path = os.path.join(target_dir, name_no_ext + ".wav")
        
        print(f"Converting: {filename} ...", end="", flush=True)
        
        # afconvert: macOS標準のオーディオ変換ツール
        # -f WAVE: WAVE形式
        # -d LEI16: Little Endian Integer 16bit (pygameで最も推奨される形式)
        try:
            subprocess.run([
                "afconvert", 
                "-f", "WAVE", 
                "-d", "LEI16", 
                mp3_path, 
                wav_path
            ], check=True, capture_output=True)
            
            print(" [DONE]")
            success_count += 1
            
            if delete_original:
                os.remove(mp3_path)
                print(f"  (Deleted original: {filename})")
                
        except subprocess.CalledProcessError as e:
            print(" [FAILED]")
            print(f"Error detail: {e.stderr.decode()}")
        except Exception as e:
            print(" [ERROR]")
            print(f"Error: {e}")

    print(f"--- Finished! Successfully converted {success_count} files. ---")

if __name__ == "__main__":
    # デフォルトでは効果音フォルダを対象にする
    sfx_dir = "components/sounds/sfx"
    
    print("MP3 to WAV Converter for macOS")
    print(f"Target directory: {sfx_dir}")
    print("Press Enter to start, or type a different path:")
    
    user_input = input("> ").strip()
    if user_input:
        sfx_dir = user_input
        
    convert_mp3_to_wav_in_dir(sfx_dir)
