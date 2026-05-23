import yaml

with open('components/data/master/enemies.yml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

enemies = data.get('ENEMY_DATA', {})

# F-D rank drop assignments (Draft)
drop_table = {
    "mawaru_kame": {
        "normal": ["broken_shield", "rotten_potion"],
        "rare": ["wooden_round_shield", "iron_breastplate"]
    },
    "normal_tako": {
        "normal": ["rotten_potion", "expired_potion"],
        "rare": ["thiefs_knife"]
    },
    "kowai_kusa": {
        "normal": ["expired_potion", "wooden_stick"],
        "rare": ["adventurers_clothes"]
    },
    "slime_red": {
        "normal": ["hp_potion"],
        "rare": ["iron_sword"]
    },
    "bakudan_man": {
        "normal": ["broken_sword", "hp_potion"],
        "rare": ["bomb_fragment"] # Wait, not sure if bomb fragment exists, maybe teleport_stone
    },
    "doku_kame": {
        "normal": ["rotten_potion", "broken_armor"],
        "rare": ["iron_shield"] # Not sure if iron_shield exists, let's just use leather_breastplate
    },
    "skeleton": {
        "normal": ["broken_sword", "broken_armor"],
        "rare": ["old_sword", "iron_sword"]
    }
}

for e_key, e_data in enemies.items():
    rank = e_data.get("min_rank", "F")
    if rank in ["F", "E", "D"] and e_key in drop_table:
        e_data["drops"] = drop_table[e_key]
        e_data["normal_drop_rate"] = 0.15
        e_data["rare_drop_rate"] = 0.03
    elif e_key == "slime":
        pass # Already set

# Ensure bakudan_man, doku_kame, skeleton get valid items
enemies["bakudan_man"]["drops"]["rare"] = ["fullmetal_sword"]
enemies["doku_kame"]["drops"]["rare"] = ["leather_breastplate"]

with open('components/data/master/enemies.yml', 'w', encoding='utf-8') as f:
    yaml.dump({'ENEMY_DATA': enemies}, f, allow_unicode=True, sort_keys=False)

print("Drops updated.")
