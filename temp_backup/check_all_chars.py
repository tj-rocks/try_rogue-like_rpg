import yaml

def check_all_chars():
    with open("temp_backup/village_broken.yml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    mappings = data.get("TILE_MAPPINGS", {})
    for tile_id, tile_val in mappings.items():
        if not isinstance(tile_val, dict):
            continue
        char = tile_val.get("char")
        if char is not None:
            print(f"{tile_id}: {repr(char)}")

if __name__ == "__main__":
    check_all_chars()
