import re

# 1. Update tests/test_equipment_offsets.py
with open("tests/test_equipment_offsets.py", "r") as f:
    code = f.read()

code = re.sub(
    r'cat_data = constants\.SHIELD_CATEGORIES\.get\(data\.get\("category"\), \{\}\)',
    r'cat_data = data',
    code
)
code = re.sub(
    r'cat_key = constants\.SHIELD_DATA\["wooden_round_shield"\]\["category"\]\n\s*original_offsets = constants\.SHIELD_CATEGORIES\[cat_key\]\["position"\]\["offsets"\]\["down"\]\n\s*constants\.SHIELD_CATEGORIES\[cat_key\]\["position"\]\["offsets"\]\["down"\] = \[ox1 \+ 10, oy1 \+ 20\]',
    r'original_offsets = constants.SHIELD_DATA["wooden_round_shield"]["position"]["offsets"]["down"]\n    constants.SHIELD_DATA["wooden_round_shield"]["position"]["offsets"]["down"] = [ox1 + 10, oy1 + 20]',
    code
)
code = re.sub(
    r'constants\.SHIELD_CATEGORIES\[cat_key\]\["position"\]\["offsets"\]\["down"\] = original_offsets',
    r'constants.SHIELD_DATA["wooden_round_shield"]["position"]["offsets"]["down"] = original_offsets',
    code
)

code = re.sub(
    r'cat_data = constants\.ARMOR_CATEGORIES\.get\(data\.get\("category"\), \{\}\)',
    r'cat_data = data',
    code
)
code = re.sub(
    r'cat_key = constants\.ARMOR_DATA\["adventurers_clothes"\]\["category"\]\n\s*constants\.ARMOR_CATEGORIES\[cat_key\]\["position"\]\["offsets"\]\["left"\] = \[ax1 - 5, ay1 \+ 15\]',
    r'constants.ARMOR_DATA["adventurers_clothes"]["position"]["offsets"]["left"] = [ax1 - 5, ay1 + 15]',
    code
)

code = re.sub(
    r'cat_key = constants\.WEAPON_DATA\[weapon\.key\]\["category"\]\n\s*constants\.WEAPON_CATEGORIES\[cat_key\]\["position"\]\["hand_offsets"\]\["right"\]\[0\] = \[wx1 \+ 30, wy1 - 10\]',
    r'constants.WEAPON_DATA[weapon.key]["position"]["hand_offsets"]["right"][0] = [wx1 + 30, wy1 - 10]',
    code
)
with open("tests/test_equipment_offsets.py", "w") as f:
    f.write(code)

# 2. Update components/sprites/weapon.py
with open("components/sprites/weapon.py", "r") as f:
    weapon_code = f.read()
weapon_code = weapon_code.replace('from constants import WEAPON_DATA, WEAPON_TYPES', 'from constants import WEAPON_DATA, WEAPON_TYPES')
weapon_code = weapon_code.replace('cat_data = WEAPON_TYPES.get(data.get("type", "onehanded_sword"), {})', 'cat_data = data')
with open("components/sprites/weapon.py", "w") as f:
    f.write(weapon_code)

# 3. Update tools/戦闘バランス調整.py
with open("tools/戦闘バランス調整.py", "r") as f:
    balance = f.read()

balance = balance.replace('for section in ["ENEMY_DATA", "ENEMY_CATEGORIES"]:', 'for section in ["ENEMY_DATA"]:')
balance = balance.replace('for section in ["WEAPON_DATA", "WEAPON_CATEGORIES", "ARMOR_DATA", "ARMOR_CATEGORIES", "SHIELD_DATA", "SHIELD_CATEGORIES"]:', 'for section in ["WEAPON_DATA", "ARMOR_DATA", "SHIELD_DATA"]:')
with open("tools/戦闘バランス調整.py", "w") as f:
    f.write(balance)

print("Patching complete.")
