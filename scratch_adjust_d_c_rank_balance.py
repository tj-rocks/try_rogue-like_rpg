import re

def adjust_weapons():
    filepath = '/Users/tj/Desktop/2DGame/components/data/master/weapons.yml'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. fighters_sword
    # Change attack to 18, accuracy_close to 10, add defense: 2 and hp: 5 under common:
    content = re.sub(
        r'(fighters_sword:.*?\n\s+common:\n\s+aggro_mod: 0\n\s+attack:) 17(\n\s+accuracy_close:) 5',
        r'\1 18\2 10\n        hp: 5\n        defense: 2',
        content,
        flags=re.DOTALL
    )

    # 2. knight_heavy_axe
    # Change max_rank to B, attack to 28, hp to 10, defense to 4, eva to -0.08
    content = re.sub(
        r'(knight_heavy_axe:.*?\n\s+max_rank:) b',
        r'\1 B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(knight_heavy_axe:.*?\n\s+common:\n\s+aggro_mod: 3\n\s+attack:) 20(\n\s+accuracy_close: -5\n\s+accuracy_range: -10\n\s+crit_rate: -0.05\n\s+hp:) 5(\n\s+defense:) 0(\n\s+eva:) -0.05',
        r'\1 28\2 10\3 4\4 -0.08',
        content,
        flags=re.DOTALL
    )

    # 3. mages_staff
    # Change attack to 8, aggro_mod to -1, lantern_bonus to 1, fire_damage to 0.25, heal_ratio to 0.15, knockback_damage to 0.15, stave_bonus to 15
    content = re.sub(
        r'(mages_staff:.*?\n\s+common:\n\s+aggro_mod:) -2(\n\s+attack:) 10(.*?lantern_bonus:) 10(.*?magic:\n\s+fire_damage:) 0.15(.*?heal_ratio:) 0.1(.*?knockback_damage:) 0.1(.*?stave_bonus:) 0',
        r'\1 -1\2 8\3 1\4 0.25\5 0.15\6 0.15\7 15',
        content,
        flags=re.DOTALL
    )

    # 4. pilgrims_sword
    # Change attack to 16, hp to 15, regen to 15, heal_ratio to 0.20, stave_bonus to 5
    content = re.sub(
        r'(pilgrims_sword:.*?\n\s+common:\n\s+aggro_mod: 0\n\s+attack:) 15(.*?hp:) 10(.*?regen:) 10(.*?magic:.*?heal_ratio:) 0.1(.*?stave_bonus:) 0',
        r'\1 16\2 15\3 15\4 0.20\5 5',
        content,
        flags=re.DOTALL
    )

    # 5. scount_small_knife
    # Change aggro_mod to -3, attack to 12, crit_rate to 0.25, eva to 0.12, armor_penetration to 0.35
    content = re.sub(
        r'(scount_small_knife:.*?\n\s+common:\n\s+aggro_mod:) -1(\n\s+attack:) 13(.*?crit_rate:) 0.1(.*?eva:) 0.1(.*?armor_penetration:) 0.25',
        r'\1 -3\2 12\3 0.25\4 0.12\5 0.35',
        content,
        flags=re.DOTALL
    )

    # 6. hunters_rapier
    # Change attack to 14, accuracy_range to 15, crit_rate to 0.18, eva to 0.06, armor_penetration to 0.20
    content = re.sub(
        r'(hunters_rapier:.*?\n\s+common:\n\s+aggro_mod: -2\n\s+attack:) 11(.*?accuracy_range:) 20(.*?crit_rate:) 0.15(.*?eva:) 0.05(.*?armor_penetration:) 0',
        r'\1 14\2 15\3 0.18\4 0.06\5 0.20',
        content,
        flags=re.DOTALL
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Adjusted weapons.yml successfully.")

def adjust_armors():
    filepath = '/Users/tj/Desktop/2DGame/components/data/master/armors.yml'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. fighters_armor
    # Change defense to 22, hp to 15, aggro_mod to 1
    content = re.sub(
        r'(fighters_armor:.*?\n\s+common:\n\s+aggro_mod:) 0(.*?hp:) 0(.*?defense:) 18',
        r'\1 1\2 15\3 22',
        content,
        flags=re.DOTALL
    )

    # 2. knight_heavy_armor
    # Change defense to 35, hp to 25, aggro_mod to 4, accuracy_close to -8, accuracy_range to -12, eva to -0.12
    content = re.sub(
        r'(knight_heavy_armor:.*?\n\s+common:\n\s+aggro_mod:) 3(.*?accuracy_close:) -5(\n\s+accuracy_range:) -10(.*?hp:) 5(.*?defense:) 20(.*?eva:) -0.11',
        r'\1 4\2 -8\3 -12\4 25\5 35\6 -0.12',
        content,
        flags=re.DOTALL
    )

    # 3. mages_robe
    # Change defense to 8, hp to 5, fire_damage to 0.3, knockback_damage to 0.2, stave_bonus to 20
    content = re.sub(
        r'(mages_robe:.*?\n\s+common:\n\s+aggro_mod: 0\n\s+attack: 0\n\s+accuracy_close: 0\n\s+accuracy_range: 0\n\s+crit_rate: 0\n\s+hp:) 0(.*?defense:) 10(.*?magic:\n\s+fire_damage:) 0.2(.*?knockback_damage:) 0.2(.*?stave_bonus:) 0',
        r'\1 5\2 8\3 0.3\4 0.2\5 20',
        content,
        flags=re.DOTALL
    )

    # 4. pilgrims_armor
    # Change regen to 15, stave_bonus to 15
    content = re.sub(
        r'(pilgrims_armor:.*?\n\s+common:.*?regen:) 1(.*?magic:.*?stave_bonus:) 10',
        r'\1 15\2 15',
        content,
        flags=re.DOTALL
    )

    # 5. scount_armor
    # Fix the double max_rank line to min_rank: D and max_rank: B
    # Also change defense to 12, crit_rate to 0.15, eva to 0.10, aggro_mod to -2, armor_penetration to 0.15
    content = re.sub(
        r'(scount_armor:.*?\n\s+)max_rank: D\n\s+max_rank: B',
        r'\1min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(scount_armor:.*?\n\s+common:\n\s+attack: 0\n\s+accuracy_close: 0\n\s+accuracy_range: 0\n\s+crit_rate:) 0.1(.*?defense:) 14(.*?eva:) 0.05(.*?aggro_mod:) -1(.*?armor_penetration:) 0.1(\n)',
        r'\1 0.15\2 12\3 0.10\4 -2\5 0.15\6',
        content,
        flags=re.DOTALL
    )

    # 6. hunters_armor
    # Fix the double min_rank line to min_rank: D and max_rank: B
    content = re.sub(
        r'(hunters_armor:.*?\n\s+)min_rank: D\n\s+min_rank: B',
        r'\1min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )

    # 7. pilgrim_robe
    # Ensure max_rank is B
    content = re.sub(
        r'(pilgrim_robe:.*?\n\s+category: robe\n\s+min_rank: D\n\s+max_rank:) B',
        r'\1 B',
        content,
        flags=re.DOTALL
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Adjusted armors.yml successfully.")

def adjust_shields():
    filepath = '/Users/tj/Desktop/2DGame/components/data/master/shields.yml'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. fighters_sheld
    # Change max_rank to B, defense to 2, hp to 10, block_chance_close to 0.18, block_chance_ranged to 0.12
    content = re.sub(
        r'(fighters_sheld:.*?\n\s+max_rank:) A',
        r'\1 B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(fighters_sheld:.*?\n\s+common:\n\s+aggro_mod: 0\n\s+attack: 0\n\s+accuracy_close: 0\n\s+accuracy_range: 0\n\s+crit_rate: 0.05\n\s+hp:) 5(\n\s+defense:) 0(.*?block_chance_close:) 0.15(\n\s+block_chance_ranged:) 0.1',
        r'\1 10\2 2\3 0.18\4 0.12',
        content,
        flags=re.DOTALL
    )

    # 2. knight_heavy_sheld
    # Change max_rank to B, defense to 8, hp to 20, block_chance_close to 0.28, block_chance_ranged to 0.28
    content = re.sub(
        r'(knight_heavy_sheld:.*?\n\s+max_rank:) A',
        r'\1 B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(knight_heavy_sheld:.*?\n\s+common:\n\s+aggro_mod: 4\n\s+attack: 2\n\s+accuracy_close: -5\n\s+accuracy_range: 0\n\s+crit_rate: 0\n\s+hp:) -10(\n\s+defense:) 2(.*?block_chance_close:) 0.1(\n\s+block_chance_ranged:) 0.1',
        r'\1 20\2 8\3 0.28\4 0.28',
        content,
        flags=re.DOTALL
    )

    # 3. mages_sheld
    # Change max_rank to B, block_chance_close to 0.10, block_chance_ranged to 0.10, fire_damage to 0.20, knockback_damage to 0.20, stave_bonus to 15
    content = re.sub(
        r'(mages_sheld:.*?\n\s+max_rank:) A',
        r'\1 B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(mages_sheld:.*?\n\s+common:.*?block_chance_close:) 0.2(\n\s+block_chance_ranged:) 0.2(.*?magic:\n\s+fire_damage:) 0.15(.*?knockback_damage:) 0.15(.*?stave_bonus:) 2',
        r'\1 0.10\2 0.10\3 0.20\4 0.20\5 15',
        content,
        flags=re.DOTALL
    )

    # 4. pilgrimss_round_sheld
    # Change max_rank to B, hp to 15, regen to 10, heal_ratio to 0.15
    content = re.sub(
        r'(pilgrimss_round_sheld:.*?\n\s+max_rank:) A',
        r'\1 B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(pilgrimss_round_sheld:.*?\n\s+common:.*?hp:) 20(.*?regen:) 1(.*?magic:.*?heal_ratio:) 0.1',
        r'\1 15\2 10\3 0.15',
        content,
        flags=re.DOTALL
    )

    # 5. scount_blackleather_sheld
    # Change max_rank to B, crit_rate to 0.12, eva to 0.08, aggro_mod to -2
    content = re.sub(
        r'(scount_blackleather_sheld:.*?\n\s+max_rank:) A',
        r'\1 B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(scount_blackleather_sheld:.*?\n\s+common:\n\s+aggro_mod:) -1(.*?crit_rate:) 0.1(.*?eva:) 0.05',
        r'\1 -2\2 0.12\3 0.08',
        content,
        flags=re.DOTALL
    )

    # 6. hunters_wood_sheild
    # Change max_rank to B
    content = re.sub(
        r'(hunters_wood_sheild:.*?\n\s+max_rank:) A',
        r'\1 B',
        content,
        flags=re.DOTALL
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Adjusted shields.yml successfully.")

if __name__ == '__main__':
    adjust_weapons()
    adjust_armors()
    adjust_shields()
