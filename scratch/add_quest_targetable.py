import os
import re

files_to_process = [
    "components/data/master/items.yml",
    "components/data/master/enemies.yml",
    "components/data/master/obstacles.yml",
    "components/data/master/equipments/weapons.yml",
    "components/data/master/equipments/armors.yml",
    "components/data/master/equipments/shields.yml",
    "components/data/master/equipments/accessories.yml"
]

base_dir = "/Users/tj/Desktop/2DGame"

test_keys = ["test_all_bonus_weapon", "test_all_bonus_armor", "test_all_bonus_shield", "table", "magic_barrier"]

for rel_path in files_to_process:
    path = os.path.join(base_dir, rel_path)
    if not os.path.exists(path):
        print(f"Skipping {rel_path} (not found)")
        continue

    print(f"Processing {rel_path}...")
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    i = 0
    in_data_block = True
    if "equipments/" in rel_path:
        in_data_block = False

    # obstacles.yml は大元ブロックがなく、インデント0のキーがオブジェクト定義
    # それ以外は、DATAブロック配下のインデント2のキーがアイテム定義
    is_flat_yaml = (rel_path == "components/data/master/obstacles.yml")

    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        stripped = line.strip()
        if not is_flat_yaml:
            if stripped.endswith("_CATEGORIES:"):
                in_data_block = False
            elif stripped.endswith("_DATA:") or stripped == "ACCESSORY_DATA:":
                in_data_block = True
        
        if stripped.startswith("#") or not stripped:
            i += 1
            continue

        # アイテム定義の検出
        is_item_def = False
        key = None
        
        if is_flat_yaml:
            # インデント0のキーが定義 (例: "wood_barrel:")
            m = re.match(r"^([a-zA-Z0-9_]+):$", line.rstrip())
            if m:
                # _DATA や CATEGORIES などは除外（obstacles.ymlにはないが一応）
                key = m.group(1)
                is_item_def = True
        else:
            # インデント2のキーが定義 (例: "  broken_shield:")
            m = re.match(r"^ {2}([a-zA-Z0-9_]+):$", line.rstrip())
            if m and in_data_block:
                key = m.group(1)
                is_item_def = True
                
        if is_item_def and key:
            # 既に quest_targetable が定義されているかチェック
            already_exists = False
            j = i + 1
            expected_indent = 2 if is_flat_yaml else 4
            
            while j < len(lines) and j < i + 10:
                next_line = lines[j]
                # 次の定義が始まったらチェック終了
                if is_flat_yaml:
                    if re.match(r"^([a-zA-Z0-9_]+):$", next_line.rstrip()):
                        break
                else:
                    if re.match(r"^ {2}([a-zA-Z0-9_]+):$", next_line.rstrip()):
                        break
                        
                if "quest_targetable" in next_line:
                    already_exists = True
                    break
                j += 1
            
            if not already_exists:
                is_test = key in test_keys or key.startswith("test_")
                val = "false" if is_test else "true"
                
                # インデントを追加する
                if is_flat_yaml:
                    added_line = f"  quest_targetable: {val}\n"
                else:
                    added_line = f"    quest_targetable: {val}\n"
                    
                new_lines.append(added_line)
        
        i += 1

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

print("Done!")
