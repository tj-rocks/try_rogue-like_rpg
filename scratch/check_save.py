import os
import sys

# プロジェクトルートを追加
_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(_ROOT)

from systems.data_loader import SAVE_OFFICIAL_PATH, SAVE_SUSPEND_PATH, SAVE_DATA_PATH

print(f"--- Save Path Check ---")
print(f"SAVE_OFFICIAL_PATH: {SAVE_OFFICIAL_PATH}")
print(f"Exists: {os.path.exists(SAVE_OFFICIAL_PATH)}")
print(f"SAVE_SUSPEND_PATH: {SAVE_SUSPEND_PATH}")
print(f"Exists: {os.path.exists(SAVE_SUSPEND_PATH)}")
print(f"SAVE_DATA_PATH: {SAVE_DATA_PATH}")
print(f"Exists: {os.path.exists(SAVE_DATA_PATH)}")

# ディレクトリの中身も念のため
save_dir = os.path.dirname(SAVE_OFFICIAL_PATH)
if os.path.exists(save_dir):
    print(f"\nFiles in {save_dir}:")
    for f in os.listdir(save_dir):
        print(f" - {f}")
else:
    print(f"\nSave directory NOT FOUND: {save_dir}")
