import os
import re

PROJECT_ROOT = "/Users/tj/Desktop/2DGame"
YAML_FILES = [
    "components/data/master/equipments/weapons.yml",
    "components/data/master/equipments/armors.yml",
    "components/data/master/equipments/shields.yml",
    "components/data/master/equipments/accessories.yml"
]

def invert_aggro_match(match):
    val_str = match.group(1)
    if '.' in val_str:
        val = float(val_str)
        # 0.0 の場合はそのままにする
        new_val = -val if val != 0.0 else 0.0
        # 小数点以下の桁数を合わせる
        return f"aggro_mod: {new_val}"
    else:
        val = int(val_str)
        new_val = -val
        return f"aggro_mod: {new_val}"

def process_files():
    print("--- Inverting aggro_mod values in YAMLs ---")
    for rel_path in YAML_FILES:
        file_path = os.path.join(PROJECT_ROOT, rel_path)
        if not os.path.exists(file_path):
            print(f"Warning: File not found: {file_path}")
            continue
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        pattern = r"aggro_mod:\s*(-?[\d.]+)"
        new_content = re.sub(pattern, invert_aggro_match, content)
        
        if new_content != content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Successfully inverted aggro_mod in {rel_path}")
        else:
            print(f"No changes in {rel_path}")

if __name__ == "__main__":
    process_files()
