import re
import os

files = [
    "components/data/master/equipment.yml",
    "components/data/master/items.yml",
    "components/data/master/README_EQUIPMENT.md"
]

mapping = {
    '"F"': "1",
    '"E"': "2",
    '"D"': "3",
    '"C"': "4",
    '"B"': "5",
    '"A"': "6",
    '"S"': "7",
    '"SS"': "8"
}

for file in files:
    if not os.path.exists(file):
        continue
    with open(file, "r") as f:
        content = f.read()
    
    for k, v in mapping.items():
        content = content.replace(f"rarity: {k}", f"rarity: {v}")
    
    with open(file, "w") as f:
        f.write(content)

print("Done YAML replacements.")
