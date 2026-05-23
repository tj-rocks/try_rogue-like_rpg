import yaml

with open('components/data/master/enemies.yml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

categories = data.pop('ENEMY_CATEGORIES', {})
enemy_data = data.get('ENEMY_DATA', {})

for enemy_key, enemy in enemy_data.items():
    cat = enemy.pop('category', None)
    if cat and cat in categories:
        merged = categories[cat].copy()
        merged.update(enemy)
        enemy_data[enemy_key] = merged
    
    # Sort keys for consistent output: name first, then everything else
    sorted_enemy = {'name': enemy_data[enemy_key].pop('name')}
    sorted_enemy.update(enemy_data[enemy_key])
    enemy_data[enemy_key] = sorted_enemy

with open('components/data/master/enemies.yml', 'w', encoding='utf-8') as f:
    yaml.dump({'ENEMY_DATA': enemy_data}, f, allow_unicode=True, sort_keys=False)

print("Done removing enemy categories.")
