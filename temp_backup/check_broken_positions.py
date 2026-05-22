import yaml

def check_positions():
    with open("temp_backup/village_broken.yml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        
    mappings = data.get("TILE_MAPPINGS", {})
    print("=== Tiles with positions defined in village_broken.yml ===")
    for tile_id, tile_val in mappings.items():
        if not isinstance(tile_val, dict):
            continue
        positions = tile_val.get("positions")
        if positions:
            print(f"{tile_id} (category: {tile_val.get('category')}): {len(positions)} positions defined.")
            if len(positions) < 10:
                print(f"  Positions: {positions}")
            else:
                print(f"  Positions (truncated): {positions[:5]} ... and {len(positions)-5} more")

if __name__ == "__main__":
    check_positions()
