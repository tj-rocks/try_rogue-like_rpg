import re

def adjust_weapons():
    filepath = '/Users/tj/Desktop/2DGame/components/data/master/weapons.yml'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix knight_heavy_axe max_rank: b -> B
    content = re.sub(
        r'(knight_heavy_axe:.*?\n\s+max_rank:) b',
        r'\1 B',
        content,
        flags=re.DOTALL
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed weapons.yml typos.")

def adjust_armors():
    filepath = '/Users/tj/Desktop/2DGame/components/data/master/armors.yml'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. pilgrim_robe: max_rank: E -> B
    content = re.sub(
        r'(pilgrim_robe:.*?\n\s+category: robe\n\s+min_rank: D\n\s+max_rank:) E',
        r'\1 B',
        content,
        flags=re.DOTALL
    )

    # 2. hunters_armor: fix min_rank: D \n min_rank: B -> min_rank: D \n max_rank: B
    content = re.sub(
        r'(hunters_armor:.*?\n\s+)min_rank: D\n\s+min_rank: B',
        r'\1min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )

    # 3. scount_armor: fix max_rank: D \n max_rank: B -> min_rank: D \n max_rank: B
    content = re.sub(
        r'(scount_armor:.*?\n\s+)max_rank: D\n\s+max_rank: B',
        r'\1min_rank: D\n    max_rank: B',
        content,
        flags=re.DOTALL
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed armors.yml typos and ranges.")

def adjust_shields():
    filepath = '/Users/tj/Desktop/2DGame/components/data/master/shields.yml'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Change max_rank from A to B for D-rank shields:
    # fighters_sheld, hunters_wood_sheild, knight_heavy_sheld, mages_sheld, pilgrimss_round_sheld, scount_blackleather_sheld
    for shield_key in ['fighters_sheld', 'hunters_wood_sheild', 'knight_heavy_sheld', 'mages_sheld', 'pilgrimss_round_sheld', 'scount_blackleather_sheld']:
        content = re.sub(
            rf'({shield_key}:.*?\n\s+max_rank:) A',
            r'\1 B',
            content,
            flags=re.DOTALL
        )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed shields.yml ranges.")

if __name__ == '__main__':
    adjust_weapons()
    adjust_armors()
    adjust_shields()
