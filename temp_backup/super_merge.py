import os
import sys
from ruamel.yaml import YAML

def super_merge():
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    
    # 1. village.txtを読み込み
    with open("components/data/dungeon/village.txt", "r", encoding="utf-8") as f:
        map_lines = [line.replace("\n", "").replace("\r", "") for line in f.readlines()]
    
    # コメント行や空行を除外して純粋なマップデータを抽出
    map_grid = []
    for line in map_lines:
        if line.startswith("//") or line.strip() == "":
            continue
        map_grid.append(line)
        
    # 2. 現在の village.yml 読み込み
    with open("components/data/master/village.yml", "r", encoding="utf-8") as f:
        current_data = yaml.load(f)
        
    # 3. 退避された village_broken.yml 読み込み
    with open("temp_backup/village_broken.yml", "r", encoding="utf-8") as f:
        broken_data = yaml.load(f)
        
    current_mappings = current_data.get("TILE_MAPPINGS", {})
    broken_mappings = broken_data.get("TILE_MAPPINGS", {})
    
    # 各文字の座標を village.txt からスキャンする関数
    def scan_positions_from_map(char):
        if not char:
            return []
        positions = []
        for y, row in enumerate(map_grid):
            for x, ch in enumerate(row):
                if ch == char:
                    positions.append({
                        "x": x,
                        "y": y,
                        "flip": False,
                        "min_rank": "F",
                        "max_rank": "SS"
                    })
        return positions

    # 全体マージ処理
    for tile_id, tile_val in current_mappings.items():
        if not isinstance(tile_val, dict):
            continue
            
        category = tile_val.get("category")
        is_entity = category in ["npc", "obstacle", "wall_decoration", "wall_pass"]
        
        # 1. village_broken.yml に定義があり、且つ positions が存在する場合
        broken_val = broken_mappings.get(tile_id)
        broken_positions = None
        if isinstance(broken_val, dict):
            broken_positions = broken_val.get("positions")
            
        if broken_positions is not None:
            # broken_positions をコピーして使う
            positions_to_set = []
            for pos in broken_positions:
                new_pos = {
                    "x": pos.get("x"),
                    "y": pos.get("y"),
                    "flip": pos.get("flip", False)
                }
                # min_rank / max_rank がなければデフォルト F / SS を設定
                new_pos["min_rank"] = pos.get("min_rank") or "F"
                new_pos["max_rank"] = pos.get("max_rank") or "SS"
                positions_to_set.append(new_pos)
            
            tile_val["positions"] = positions_to_set
            print(f"🔄 {tile_id}: Restored {len(positions_to_set)} positions from broken.yml with min/max rank.")
            
        # 2. broken.yml に positions が存在しないが、現在の yml で Entity カテゴリの場合
        elif is_entity:
            # village.txt 内から char を自動検出して positions を補完
            char = tile_val.get("char")
            positions_to_set = scan_positions_from_map(char)
            if positions_to_set:
                tile_val["positions"] = positions_to_set
                print(f"✨ {tile_id}: Scanned and added {len(positions_to_set)} positions from village.txt (char: '{char}') with min/max rank.")
            else:
                # 配置座標が見つからなかった場合、positionsフィールドを削除または空にする
                if "positions" in tile_val:
                    del tile_val["positions"]
                print(f"🗑️ {tile_id}: No positions found on map. Cleaned up positions.")

    # 4. village.yml に書き戻し
    with open("components/data/master/village.yml", "w", encoding="utf-8") as f:
        yaml.dump(current_data, f)
        
    print("🎉 Super Merge Completed successfully!")

if __name__ == "__main__":
    super_merge()
