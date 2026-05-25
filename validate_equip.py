import yaml
import sys

def check_file(filepath, data_key):
    print(f"--- Checking {filepath} ---")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"Failed to load {filepath}: {e}")
        return False
        
    items = data.get(data_key, {})
    all_ok = True
    for key, item in items.items():
        if not isinstance(item, dict):
            continue
            
        # Check root
        if 'aggro_mod' in item:
            print(f"❌ [{key}] still has aggro_mod at the root level!")
            all_ok = False
            
        # Check bonus.common
        bonus = item.get('bonus', {})
        common = bonus.get('common', {})
        if 'aggro_mod' not in common:
            print(f"❌ [{key}] is missing aggro_mod in bonus.common!")
            all_ok = False
            
    if all_ok:
        print(f"✅ All items in {filepath} are perfectly structured.")
        
    return all_ok

def main():
    ok1 = check_file('components/data/master/armors.yml', 'ARMOR_DATA')
    ok2 = check_file('components/data/master/weapons.yml', 'WEAPON_DATA')
    ok3 = check_file('components/data/master/shields.yml', 'SHIELD_DATA')
    
    if ok1 and ok2 and ok3:
        print("\nAll checks passed successfully!")
    else:
        print("\nSome checks failed!")
        
if __name__ == "__main__":
    main()
