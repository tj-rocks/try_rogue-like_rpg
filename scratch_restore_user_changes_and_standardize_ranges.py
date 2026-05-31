import re

def restore_weapons():
    filepath = '/Users/tj/Desktop/2DGame/components/data/master/weapons.yml'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. damascus_sword range: E to D -> C to A
    content = re.sub(
        r'  damascus_sword:.*?min_rank: \w+.*?max_rank: \w+',
        '  damascus_sword:\n    name: ダマスカス鋼の剣\n    category: onehanded_sword\n    min_rank: C\n    max_rank: A',
        content,
        flags=re.DOTALL
    )

    # 2. fighters_sword max_rank: A -> B
    content = re.sub(
        r'  fighters_sword:.*?min_rank: D.*?max_rank: A',
        '  fighters_sword:\n    name: 戦士の剣\n    category: onehanded_sword\n    min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )

    # 3. hunters_rapier max_rank: A -> B
    content = re.sub(
        r'  hunters_rapier:.*?min_rank: D.*?max_rank: A',
        '  hunters_rapier:\n    name: 狩人のレイピア\n    category: onehanded_sword\n    min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )

    # 4. knight_heavy_axe max_rank: A -> B and stats
    # Stats: aggro_mod: 3, attack: 20, accuracy_close: -5, crit_rate: -0.05, hp: 5
    content = re.sub(
        r'  knight_heavy_axe:.*?min_rank: D.*?max_rank: \w+',
        '  knight_heavy_axe:\n    name: 騎士の重斧\n    category: axe\n    min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(knight_heavy_axe:.*?common:\n\s+aggro_mod:) \d+(\n\s+attack:) \d+(\n\s+accuracy_close:) -\d+(\n\s+accuracy_range: -10\n\s+crit_rate:) \d+\.\d+(\n\s+hp:) \d+',
        r'\1 3\2 20\3 -5\4 -0.05\5 5',
        content,
        flags=re.DOTALL
    )

    # 5. mages_staff max_rank: B and stats
    # Stats: aggro_mod: -2, lantern_bonus: 10, fire_damage: 0.15, heal_ratio: 0.1, knockback_damage: 0.1, invincible_turns: 2, stave_bonus: 0
    content = re.sub(
        r'  mages_staff:.*?min_rank: D.*?max_rank: \w+',
        '  mages_staff:\n    name: 魔術師のスタッフ\n    category: onehanded_sword\n    min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(mages_staff:.*?common:\n\s+aggro_mod:) \d+(\n\s+attack: 10\n\s+accuracy_close: 0\n\s+accuracy_range: 0\n\s+crit_rate: 0.0\n\s+hp: 0\n\s+defense: 0\n\s+eva: 0.0\n\s+block_chance: 0.0\n\s+block_chance_close: 0.0\n\s+block_chance_ranged: 0.0\n\s+lantern_bonus:) \d+(.*?magic:\n\s+fire_damage:) \d+\.\d+(.*?fire_range: 1\n\s+heal_ratio:) \d+\.\d+(.*?knockback_damage:) \d+\.\d+(\n\s+invincible_turns:) \d+(\n\s+stave_bonus:) \d+',
        r'\1 -2\2 10\3 0.15\4 0.1\5 0.1\6 2\7 0',
        content,
        flags=re.DOTALL
    )

    # 6. pilgrims_sword max_rank: B and stats
    # Stats: attack: 15, hp: 10, regen: 10, heal_ratio: 0.1, stave_bonus: 0
    content = re.sub(
        r'  pilgrims_sword:.*?min_rank: D.*?max_rank: \w+',
        '  pilgrims_sword:\n    name: 巡礼者の剣\n    category: onehanded_sword\n    min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(pilgrims_sword:.*?common:\n\s+aggro_mod: 0\n\s+attack:) \d+(.*?hp:) \d+(.*?regen:) \d+(.*?magic:.*?heal_ratio:) \d+\.\d+(.*?stave_bonus:) \d+',
        r'\1 15\2 10\3 10\4 0.1\5 0',
        content,
        flags=re.DOTALL
    )

    # 7. scount_small_knife: name to "スカウトの小刀", max_rank: B and stats
    # Stats: aggro_mod: -1, attack: 13, crit_rate: 0.1, eva: 0.1, block_chance_close: 0.1, armor_penetration: 0.25
    content = re.sub(
        r'  scount_small_knife:.*?name: [^\n]+',
        '  scount_small_knife:\n    name: スカウトの小刀',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'  scount_small_knife:.*?min_rank: D.*?max_rank: \w+',
        '  scount_small_knife:\n    name: スカウトの小刀\n    category: dagger\n    min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(scount_small_knife:.*?common:\n\s+aggro_mod:) -\d+(\n\s+attack:) \d+(.*?crit_rate:) \d+\.\d+(.*?eva:) \d+\.\d+(.*?block_chance_close:) \d+\.\d+(.*?armor_penetration:) \d+\.\d+',
        r'\1 -1\2 13\3 0.1\4 0.1\5 0.1\6 0.25',
        content,
        flags=re.DOTALL
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Restored and standardized weapons.yml successfully.")

def restore_armors():
    filepath = '/Users/tj/Desktop/2DGame/components/data/master/armors.yml'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. leather_breastplate (E-rank) regen: 1
    content = re.sub(
        r'(leather_breastplate:.*?common:.*?regen:) 0',
        r'\1 1',
        content,
        flags=re.DOTALL
    )

    # 2. pilgrim_robe: max_rank: B and stats: hp: 5, regen: 15
    content = re.sub(
        r'  pilgrim_robe:.*?min_rank: D.*?max_rank: \w+',
        '  pilgrim_robe:\n    name: 巡礼者のローブ\n    category: robe\n    min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(pilgrim_robe:.*?common:.*?hp:) 0(.*?regen:) 0',
        r'\1 5\2 15',
        content,
        flags=re.DOTALL
    )

    # 3. hunters_armor: fix min_rank typo to min_rank: D and max_rank: B, stats: accuracy_close: 20, crit_rate: 0.15, defense: 17
    content = re.sub(
        r'  hunters_armor:.*?min_rank: D.*?min_rank: \w+',
        '  hunters_armor:\n    name: 狩人の鎧\n    category: light\n    min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(hunters_armor:.*?common:.*?accuracy_close:) \d+(.*?crit_rate:) \d+\.\d+(.*?defense:) \d+',
        r'\1 20\2 0.15\3 17',
        content,
        flags=re.DOTALL
    )

    # 4. fighters_armor: min_rank: D, max_rank: B, stats: defense: 18, hp: 0, aggro_mod: 0
    content = re.sub(
        r'  fighters_armor:.*?min_rank: \w+.*?max_rank: \w+',
        '  fighters_armor:\n    name: 戦士の鎧\n    category: medium\n    min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(fighters_armor:.*?common:\n\s+aggro_mod:) \d+(.*?hp:) \d+(.*?defense:) \d+',
        r'\1 0\2 0\3 18',
        content,
        flags=re.DOTALL
    )

    # 5. knight_heavy_armor: min_rank: D, max_rank: B, stats: aggro_mod: 3, attack: 2, accuracy_close: -5, hp: 5, defense: 20, eva: -0.11
    content = re.sub(
        r'  knight_heavy_armor:.*?min_rank: \w+.*?max_rank: \w+',
        '  knight_heavy_armor:\n    name: 騎士の重鎧\n    category: heavy\n    min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(knight_heavy_armor:.*?common:\n\s+aggro_mod:) \d+(\n\s+attack:) \d+(\n\s+accuracy_close:) -\d+(.*?hp:) \d+(.*?defense:) \d+(.*?eva:) -0.1\d',
        r'\1 3\2 2\3 -5\4 5\5 20\6 -0.11',
        content,
        flags=re.DOTALL
    )

    # 6. pilgrims_armor: min_rank: D, max_rank: B
    content = re.sub(
        r'  pilgrims_armor:.*?min_rank: \w+.*?max_rank: \w+',
        '  pilgrims_armor:\n    name: 巡礼者の装衣\n    category: robe\n    min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )

    # 7. scount_armor: fix max_rank typo to min_rank: D and max_rank: B, stats: crit_rate: 0.1, aggro_mod: -1, armor_penetration: 0.1
    content = re.sub(
        r'  scount_armor:.*?max_rank: D.*?max_rank: \w+',
        '  scount_armor:\n    name: スカウトの鎧\n    category: light\n    min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(scount_armor:.*?common:.*?crit_rate:) \d+\.\d+(.*?aggro_mod:) -\d+(.*?armor_penetration:) \d+\.\d+',
        r'\1 0.1\2 -1\3 0.1',
        content,
        flags=re.DOTALL
    )

    # 8. mages_robe: min_rank: D, max_rank: B, stats: defense: 10, stave_bonus: 0
    content = re.sub(
        r'  mages_robe:.*?min_rank: \w+.*?max_rank: \w+',
        '  mages_robe:\n    name: 魔術師の魔導衣\n    category: robe\n    min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(mages_robe:.*?common:.*?defense:) \d+(.*?magic:.*?stave_bonus:) \d+',
        r'\1 10\2 0',
        content,
        flags=re.DOTALL
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Restored and standardized armors.yml successfully.")

def restore_shields():
    filepath = '/Users/tj/Desktop/2DGame/components/data/master/shields.yml'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. leather_round_shield (E-rank) stats: crit_rate: 0.1, armor_penetration: 0.05
    content = re.sub(
        r'(leather_round_shield:.*?common:.*?crit_rate:) 0.0(.*?armor_penetration:) 0.0',
        r'\1 0.1\2 0.05',
        content,
        flags=re.DOTALL
    )

    # 2. fighters_sheld: max_rank: B, stats: crit_rate: 0.05, hp: 5, block_chance_close: 0.15, block_chance_ranged: 0.1
    content = re.sub(
        r'  fighters_sheld:.*?min_rank: D.*?max_rank: \w+',
        '  fighters_sheld:\n    name: 戦士の盾\n    category: round_shield\n    min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(fighters_sheld:.*?common:.*?crit_rate:) 0.0(.*?hp:) 0(.*?block_chance_close:) 0.10(.*?block_chance_ranged:) 0.10',
        r'\1 0.05\2 5\3 0.15\4 0.1',
        content,
        flags=re.DOTALL
    )

    # 3. hunters_wood_sheild: max_rank: B, stats: crit_rate: 0.15, accuracy_close: 20
    content = re.sub(
        r'  hunters_wood_sheild:.*?min_rank: D.*?max_rank: \w+',
        '  hunters_wood_sheild:\n    name: 狩人の木盾\n    category: round_shield\n    min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(hunters_wood_sheild:.*?common:.*?accuracy_close:) \d+(.*?crit_rate:) \d+\.\d+',
        r'\1 20\2 0.15',
        content,
        flags=re.DOTALL
    )

    # 4. knight_heavy_sheld: max_rank: B, stats: attack: 2, accuracy_close: -5, hp: -10, defense: 2, block_chance_close: 0.1, block_chance_ranged: 0.1
    content = re.sub(
        r'  knight_heavy_sheld:.*?min_rank: D.*?max_rank: \w+',
        '  knight_heavy_sheld:\n    name: 騎士の重盾\n    category: large_shield\n    min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(knight_heavy_sheld:.*?common:.*?attack:) \d+(\n\s+accuracy_close:) -\d+(.*?hp:) 0(\n\s+defense:) 0(.*?block_chance_close:) 0.22(\n\s+block_chance_ranged:) 0.22',
        r'\1 2\2 -5\3 -10\4 2\5 0.1\6 0.1',
        content,
        flags=re.DOTALL
    )

    # 5. mages_sheld: max_rank: B, stats: block_chance_close: 0.2, block_chance_ranged: 0.2, stave_bonus: 2
    content = re.sub(
        r'  mages_sheld:.*?min_rank: D.*?max_rank: \w+',
        '  mages_sheld:\n    name: 魔術師の魔導盾\n    category: round_shield\n    min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(mages_sheld:.*?common:.*?block_chance_close:) 0.05(\n\s+block_chance_ranged:) 0.05(.*?magic:.*?stave_bonus:) 15',
        r'\1 0.2\2 0.2\3 2',
        content,
        flags=re.DOTALL
    )

    # 6. pilgrimss_round_sheld: max_rank: B, stats: block_chance_close: 0.1, block_chance_ranged: 0.1, stave_bonus: 0
    content = re.sub(
        r'  pilgrimss_round_sheld:.*?min_rank: D.*?max_rank: \w+',
        '  pilgrimss_round_sheld:\n    name: 巡礼者の丸盾\n    category: round_shield\n    min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(pilgrimss_round_sheld:.*?common:.*?block_chance_close:) 0.08(\n\s+block_chance_ranged:) 0.08(.*?magic:.*?stave_bonus:) 10',
        r'\1 0.1\2 0.1\3 0',
        content,
        flags=re.DOTALL
    )

    # 7. scount_blackleather_sheld: max_rank: B, stats: aggro_mod: -1, crit_rate: 0.1, armor_penetration: 0.1
    content = re.sub(
        r'  scount_blackleather_sheld:.*?min_rank: D.*?max_rank: \w+',
        '  scount_blackleather_sheld:\n    name: スカウトの黒革盾\n    category: round_shield\n    min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(scount_blackleather_sheld:.*?common:\n\s+aggro_mod:) -\d+(.*?crit_rate:) \d+\.\d+(.*?armor_penetration:) \d+\.\d+',
        r'\1 -1\2 0.1\3 0.1',
        content,
        flags=re.DOTALL
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Restored and standardized shields.yml successfully.")

if __name__ == '__main__':
    restore_weapons()
    restore_armors()
    restore_shields()
