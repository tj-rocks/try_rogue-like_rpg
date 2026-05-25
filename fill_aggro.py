import re
import sys
import yaml

def fill_missing_aggro_mod(filepath):
    # First, let's read the YAML to see which items are missing aggro_mod in bonus.common
    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        
    keys_to_fix = set()
    for root_key, items in data.items():
        if root_key.endswith('_DATA'):
            for key, item in items.items():
                if not isinstance(item, dict): continue
                common = item.get('bonus', {}).get('common', {})
                if 'aggro_mod' not in common:
                    keys_to_fix.add(key)
                    
    if not keys_to_fix:
        print(f"No missing aggro_mod in {filepath}")
        return

    # Now, parse line by line and insert `        aggro_mod: 0\n` where appropriate.
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    out_lines = []
    current_key = None
    
    for line in lines:
        # Check if line defines a new item key
        match = re.match(r'^  ([a-zA-Z0-9_]+):', line)
        if match:
            current_key = match.group(1)
            
        out_lines.append(line)
        
        # If we hit `      common:` and the current item needs a fix, append `        aggro_mod: 0`
        if line.startswith("      common:"):
            if current_key in keys_to_fix:
                out_lines.append("        aggro_mod: 0\n")
                
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)
        
    print(f"Fixed {len(keys_to_fix)} items in {filepath}")

def main():
    fill_missing_aggro_mod('components/data/master/armors.yml')
    fill_missing_aggro_mod('components/data/master/weapons.yml')
    fill_missing_aggro_mod('components/data/master/shields.yml')
    
if __name__ == "__main__":
    main()
