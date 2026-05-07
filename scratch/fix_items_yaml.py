import re

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

with open("components/data/master/items.yml", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    m = re.match(r'^(\s+)rank:\s*([A-Z]+)', line)
    if m:
        indent = m.group(1)
        rank_val = m.group(2)
        rarity_val = mapping.get(rank_val, 1)
        new_lines.append(f'{indent}min_rank: "{rank_val}"\n')
        new_lines.append(f"{indent}rarity: {rarity_val}\n")
    else:
        new_lines.append(line)

with open("components/data/master/items.yml", "w") as f:
    f.writelines(new_lines)

print("done")
