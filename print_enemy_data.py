import sys
sys.path.append('.')
from constants import ENEMY_DATA
for k, v in ENEMY_DATA.items():
    if v.get("min_floor") is None or v.get("max_floor") is None:
        print(f"Enemy {k} has None: min_floor={v.get('min_floor')}, max_floor={v.get('max_floor')}")
print("Done.")
