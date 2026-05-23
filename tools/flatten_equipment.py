import yaml

files = [
    ('components/data/master/weapons.yml', 'WEAPON_CATEGORIES', 'WEAPON_DATA'),
    ('components/data/master/armors.yml', 'ARMOR_CATEGORIES', 'ARMOR_DATA'),
    ('components/data/master/shields.yml', 'SHIELD_CATEGORIES', 'SHIELD_DATA')
]

for filepath, cat_key, data_key in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    categories = data.pop(cat_key, {})
    item_data = data.get(data_key, {})

    for item_k, item_v in item_data.items():
        cat = item_v.pop('category', None)
        if cat and cat in categories:
            merged = categories[cat].copy()
            merged.update(item_v)
            item_data[item_k] = merged
        
        # Keep name at top
        if 'name' in item_data[item_k]:
            sorted_item = {'name': item_data[item_k].pop('name')}
            sorted_item.update(item_data[item_k])
            item_data[item_k] = sorted_item

    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump({data_key: item_data}, f, allow_unicode=True, sort_keys=False)

print("Flattened equipment YAMLs.")
