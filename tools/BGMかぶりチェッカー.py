import hashlib
import os
import glob
import sys
import yaml

def calculate_md5(path):
    """ファイルのMD5ハッシュを計算する"""
    hasher = hashlib.md5()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return None

def load_dungeon_usage():
    """dungeon.yml から BGM の使用状況をロードする"""
    dungeon_yml_path = os.path.join(os.path.dirname(__file__), "..", "components", "data", "master", "dungeon.yml")
    usage_map = {} # filename -> list of keys
    
    if not os.path.exists(dungeon_yml_path):
        return usage_map

    try:
        with open(dungeon_yml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        dungeon_images = data.get("DUNGEON_IMAGES", {})
        for key, info in dungeon_images.items():
            if isinstance(info, dict) and "sound" in info:
                sound_val = info["sound"]
                if sound_val:
                    # パスが含まれている場合はファイル名のみ抽出
                    filename = os.path.basename(sound_val)
                    if filename not in usage_map:
                        usage_map[filename] = []
                    usage_map[filename].append(key)
    except Exception as e:
        print(f"Error loading dungeon.yml: {e}")
        
    return usage_map

def main():
    # パス設定
    default_dir = os.path.join(os.path.dirname(__file__), "..", "components", "sounds", "bgm")
    target_dir = sys.argv[1] if len(sys.argv) > 1 else default_dir
    target_dir = os.path.abspath(target_dir)

    if not os.path.exists(target_dir):
        print(f"Directory not found: {target_dir}")
        return

    # 使用状況のロード
    usage_map = load_dungeon_usage()

    print(f"--- Scanning for duplicates in: ---")
    print(f"    {target_dir}")
    print(f"--- Checking usage in dungeon.yml DUNGEON_IMAGES ---\n")
    
    mp3_files = glob.glob(os.path.join(target_dir, "*.mp3"))
    if not mp3_files:
        print("No .mp3 files found.")
        return

    hashes = {}
    for path in mp3_files:
        filename = os.path.basename(path)
        file_hash = calculate_md5(path)
        if file_hash:
            if file_hash in hashes:
                hashes[file_hash].append(filename)
            else:
                hashes[file_hash] = [filename]

    found_duplicates = False
    for h, filenames in hashes.items():
        if len(filenames) > 1:
            found_duplicates = True
            size = os.path.getsize(os.path.join(target_dir, filenames[0]))
            print(f"[Duplicate Found] MD5: {h} ({size / 1024 / 1024:.2f} MB)")
            
            for f in filenames:
                keys = usage_map.get(f, [])
                usage_str = f" -> Used in keys: {keys}" if keys else " (Not used in dungeon.yml)"
                print(f"  - {f}{usage_str}")
            print("-" * 60)

    if not found_duplicates:
        print("No identical files found.")
    else:
        print("\nScan complete.")

if __name__ == "__main__":
    main()
