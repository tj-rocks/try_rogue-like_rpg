import re
import os

mapping = {
    'F': 1,
    'E': 2,
    'D': 3,
    'C': 4,
    'B': 5,
    'A': 6,
    'S': 7,
    'SS': 8
}

def fix_yaml(filepath):
    if not os.path.exists(filepath):
        print(f"Skipping {filepath}: Not found")
        return
    
    with open(filepath, "r") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        # Match "rank: [RANK]" but not "min_rank" or "max_rank"
        m = re.match(r'^(\s+)rank:\s*([A-Z]+)', line)
        if m:
            indent = m.group(1)
            rank_val = m.group(2)
            rarity_val = mapping.get(rank_val, 1)
            new_lines.append(f'{indent}min_rank: "{rank_val}"\n')
            new_lines.append(f"{indent}rarity: {rarity_val}\n")
        else:
            new_lines.append(line)

    with open(filepath, "w") as f:
        f.writelines(new_lines)
    print(f"Fixed {filepath}")

fix_yaml("components/data/master/obstacles.yml")
fix_yaml("components/data/master/enemies.yml")
