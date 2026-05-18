import re

with open("components/data/master/village.yml", "r") as f:
    content = f.read()

# For each NPC and obstacle, add base_image_path if it doesn't exist
# We will just parse it manually:

lines = content.split('\n')
new_lines = []

outdoor_npcs = ['villager', 'apprentice', 'dungeon_expert']

in_npc = False
in_obstacle = False
current_entity = None

for line in lines:
    new_lines.append(line)
    
    if "category: 'npc'" in line:
        in_npc = True
        in_obstacle = False
    elif "category: 'obstacle'" in line:
        in_obstacle = True
        in_npc = False
        
    match = re.search(r"id: '([^']+)'", line)
    if match:
        entity_id = match.group(1)
        if in_npc:
            bg = 'floor_0.png' if entity_id in outdoor_npcs else 'floor_1.png'
            new_lines.append(f"    base_image_path: 'components/pictures/dungeon/home/{bg}'")
        elif in_obstacle:
            new_lines.append(f"    base_image_path: 'components/pictures/dungeon/home/floor_0.png'")

with open("components/data/master/village.yml", "w") as f:
    f.write('\n'.join(new_lines))
