import re
import sys

def migrate_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    out_lines = []
    aggro_val = None
    
    # We will process line by line.
    # If we see `    aggro_mod: X`, we capture X and skip the line.
    # If we see `      common:`, we output it, and immediately after we output `        aggro_mod: X` (if we captured one for this item).
    # Since `aggro_mod` might appear before or after `common:`, we need a two-pass or block-based approach.
    
    # Actually, the simplest approach: 
    # Just read the whole file, identify blocks for each item, and move the line.
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Find all items. Items are at indentation level 2 (e.g., "  hard_leather_armor:")
    
    # Let's just use Python's re module.
    # Match `    aggro_mod: <val>\n`
    # And we need to place it under `      common:\n`
    
    # To do this safely line by line:
    new_lines = []
    current_aggro = None
    
    for line in lines:
        match = re.match(r'^    aggro_mod:\s*(-?\d+)\n?', line)
        if match:
            current_aggro = match.group(1)
            continue # skip this line
            
        new_lines.append(line)
        
        if line.startswith("      common:"):
            if current_aggro is not None:
                new_lines.append(f"        aggro_mod: {current_aggro}\n")
                current_aggro = None
                
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
        
    print(f"Migrated {filepath}")

migrate_file('components/data/master/armors.yml')
migrate_file('components/data/master/weapons.yml')
migrate_file('components/data/master/shields.yml')
