import yaml

def diff_yml():
    with open("components/data/master/village.yml", "r", encoding="utf-8") as f:
        orig = yaml.safe_load(f) or {}
    with open("temp_backup/village_broken.yml", "r", encoding="utf-8") as f:
        brok = yaml.safe_load(f) or {}
        
    orig_mappings = orig.get("TILE_MAPPINGS", {})
    brok_mappings = brok.get("TILE_MAPPINGS", {})
    
    orig_keys = set(orig_mappings.keys())
    brok_keys = set(brok_mappings.keys())
    
    print("=== Keys in original but NOT in broken ===")
    print(orig_keys - brok_keys)
    
    print("\n=== Keys in broken but NOT in original ===")
    print(brok_keys - orig_keys)
    
    print("\n=== Differing chars ===")
    for k in orig_keys & brok_keys:
        o_char = orig_mappings[k].get("char")
        b_char = brok_mappings[k].get("char")
        if o_char != b_char:
            print(f"{k}: original_char={repr(o_char)}, broken_char={repr(b_char)}")

if __name__ == "__main__":
    diff_yml()
