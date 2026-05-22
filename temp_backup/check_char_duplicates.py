import yaml

def check_duplicates():
    with open("temp_backup/village_broken.yml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    mappings = data.get("TILE_MAPPINGS", {})
    char_to_ids = {}
    
    for tile_id, tile_val in mappings.items():
        if not isinstance(tile_val, dict):
            continue
        char = tile_val.get("char")
        if char is not None and char != "":
            char_to_ids.setdefault(char, []).append(tile_id)
            
    print("=== Duplicated Characters in village.yml ===")
    has_dup = False
    for char, ids in char_to_ids.items():
        if len(ids) > 1:
            print(f"Char: {repr(char)} is shared by IDs: {ids}")
            has_dup = True
    if not has_dup:
        print("No duplicated characters found!")

if __name__ == "__main__":
    check_duplicates()
