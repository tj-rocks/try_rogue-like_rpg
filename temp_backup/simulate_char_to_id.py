import sys
import os
import json
import yaml

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from systems.data_loader import load_master_data

def simulate(yml_path):
    print(f"\n--- Simulating for {yml_path} ---")
    
    # サーバー側API /api/tile_definitions の再現
    with open(yml_path, "r", encoding="utf-8") as f:
        village_data = yaml.safe_load(f) or {}
    tile_mappings = {}
    tile_mappings_raw = village_data.get("TILE_MAPPINGS", {})
    for k, v in tile_mappings_raw.items():
        if isinstance(v, dict):
            tile_mappings[k] = dict(v)
                
    # フロントエンド JavaScript ロジックの再現
    charToId = {}
    for ch, val in tile_mappings.items():
        if val.get("char"):
            charToId[val["char"]] = ch
            
    # charToId の中身をソートして表示
    print("charToId mappings count:", len(charToId))
    for char in sorted(charToId.keys()):
        print(f"  {repr(char)} -> {charToId[char]}")

if __name__ == "__main__":
    simulate("components/data/master/village.yml")
    simulate("temp_backup/village_broken.yml")
