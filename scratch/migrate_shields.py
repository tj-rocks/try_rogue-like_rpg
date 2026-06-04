import os
import re
import shutil

PROJECT_ROOT = "/Users/tj/Desktop/2DGame"
SHIELDS_YML = os.path.join(PROJECT_ROOT, "components/data/master/equipments/shields.yml")
SHIELD_IMG_DIR = os.path.join(PROJECT_ROOT, "components/pictures/shield")

keys = [
    "broken_shield",
    "wooden_round_shield",
    "leather_round_shield",
    "iron_round_shield",
    "fullmetal_round_shield",
    "fighters_sheld",
    "hunters_wood_sheild",
    "knight_heavy_sheld",
    "mages_sheld",
    "pilgrimss_round_sheld",
    "scount_blackleather_sheld",
    "test_all_bonus_shield"
]

def migrate_images():
    print("--- Migrating Shield Images ---")
    for key in keys:
        src_file = os.path.join(SHIELD_IMG_DIR, f"{key}.png")
        dest_dir = os.path.join(SHIELD_IMG_DIR, key)
        dest_file = os.path.join(dest_dir, "shield.png")
        
        if os.path.exists(src_file):
            os.makedirs(dest_dir, exist_ok=True)
            print(f"Moving {src_file} -> {dest_file}")
            shutil.move(src_file, dest_file)
        else:
            if os.path.exists(dest_file):
                print(f"Already migrated: {dest_file}")
            else:
                print(f"Warning: Source image not found for key: {key}")

def update_yml():
    print("--- Updating shields.yml ---")
    with open(SHIELDS_YML, "r", encoding="utf-8") as f:
        content = f.read()

    modified_content = content
    for key in keys:
        # キー定義の後に続く image_dir: components/pictures/shield を正規表現で置換
        # \s{2}key:\n から始まり、次のインデント2の定義またはファイル末尾までの範囲で、image_dir を置換する
        pattern = rf"(  {key}:\n(?:.*\n)*?\s+image_dir:\s*)components/pictures/shield(\s*\n)"
        match = re.search(pattern, modified_content)
        if match:
            replacement = rf"\1components/pictures/shield/{key}\2"
            modified_content = re.sub(pattern, replacement, modified_content)
            print(f"Updated image_dir for {key} in shields.yml")
        else:
            print(f"Warning: Could not find image_dir pattern for key: {key}")

    if modified_content != content:
        with open(SHIELDS_YML, "w", encoding="utf-8") as f:
            f.write(modified_content)
        print("shields.yml written successfully.")
    else:
        print("No changes needed or made to shields.yml.")

if __name__ == "__main__":
    migrate_images()
    update_yml()
