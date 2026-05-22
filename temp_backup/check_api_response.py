import sys
import os
import json

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from systems.data_loader import load_master_data

village_data = load_master_data("../temp_backup/village_broken.yml") or {}
tile_mappings = {}
tile_mappings_raw = village_data.get("TILE_MAPPINGS", {})
for k, v in tile_mappings_raw.items():
    if isinstance(v, dict):
        tile_mappings[k] = dict(v)

# tiles の中で、char が設定されているもの一覧を表示
print("=== Tiles with char defined ===")
for ch, val in tile_mappings.items():
    c = val.get("char")
    if c is not None:
        print(f"{ch}: {repr(c)} (type: {type(c)})")
