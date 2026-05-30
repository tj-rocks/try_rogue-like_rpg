import re
import os

def update_item_block(block, spec):
    # Update simple fields at the top level of the item block (4 spaces indentation)
    for field, val in spec.get('fields', {}).items():
        # Match "    field: value"
        pattern = re.compile(rf'^    {field}:.*$', re.MULTILINE)
        if pattern.search(block):
            block = pattern.sub(f'    {field}: {val}', block)
        else:
            # If not found, insert it before 'rarity' or 'price' or 'describe'
            insert_pattern = re.compile(rf'^    (rarity|price|describe|image_path|image_dir):', re.MULTILINE)
            match = insert_pattern.search(block)
            if match:
                idx = match.start()
                block = block[:idx] + f'    {field}: {val}\n' + block[idx:]
            else:
                # Fallback: append at the beginning after the first newline
                idx = block.find('\n') + 1
                block = block[:idx] + f'    {field}: {val}\n' + block[idx:]

    # Helper function to update fields under a sub-block like 'common:' or 'magic:'
    def update_sub_block(block_str, sub_name, sub_spec):
        # Locate the sub-block (e.g. "      common:\n")
        sub_pattern = re.compile(rf'^      {sub_name}:\s*$', re.MULTILINE)
        match = sub_pattern.search(block_str)
        if not match:
            return block_str
        
        start_idx = match.end()
        # Find where this sub-block ends: next line that has <= 6 spaces of indentation and is not empty/comment
        # Or just search line by line from start_idx
        lines = block_str[start_idx:].split('\n')
        modified_lines = []
        updated_fields = set()
        
        for line in lines:
            if not line.strip():
                modified_lines.append(line)
                continue
            # Check indentation of non-empty line
            indent = len(line) - len(line.lstrip())
            if indent <= 6 and line.strip() and not line.strip().startswith('#'):
                # We reached the end of the sub-block
                break
            
            # Check if this line defines a field in the sub_spec
            field_match = re.match(r'^        ([a-zA-Z_0-9]+):\s*(.*)$', line)
            if field_match:
                f_name = field_match.group(1)
                if f_name in sub_spec:
                    val = sub_spec[f_name]
                    modified_lines.append(f'        {f_name}: {val}')
                    updated_fields.add(f_name)
                    continue
            modified_lines.append(line)
            
        # Add any fields that were in spec but not in the sub-block yet
        for f_name, val in sub_spec.items():
            if f_name not in updated_fields:
                modified_lines.insert(0, f'        {f_name}: {val}')
                
        # Reconstruct the block
        end_idx = start_idx + len('\n'.join(lines[:len(modified_lines) - len(updated_fields)])) # rough estimate, let's be more precise
        # Better: just replace the sub-block section in block_str
        # Let's find the exact end index on block_str
        current_idx = start_idx
        for line in lines:
            if not line.strip():
                current_idx += len(line) + 1
                continue
            indent = len(line) - len(line.lstrip())
            if indent <= 6 and line.strip() and not line.strip().startswith('#'):
                break
            current_idx += len(line) + 1
            
        sub_block_content = block_str[start_idx:current_idx]
        # Now rebuild sub_block_content line by line
        sub_lines = sub_block_content.split('\n')
        new_sub_lines = []
        updated_fields = set()
        for s_line in sub_lines:
            if not s_line.strip():
                new_sub_lines.append(s_line)
                continue
            indent = len(s_line) - len(s_line.lstrip())
            if indent > 6:
                f_match = re.match(r'^(\s+)([a-zA-Z_0-9]+):\s*(.*)$', s_line)
                if f_match:
                    indentation = f_match.group(1)
                    f_name = f_match.group(2)
                    if f_name in sub_spec:
                        val = sub_spec[f_name]
                        new_sub_lines.append(f'{indentation}{f_name}: {val}')
                        updated_fields.add(f_name)
                        continue
            new_sub_lines.append(s_line)
            
        # Add missing fields
        for f_name, val in sub_spec.items():
            if f_name not in updated_fields:
                # Find the first line after common:
                new_sub_lines.insert(0, f'        {f_name}: {val}')
                
        new_sub_block_content = '\n'.join(new_sub_lines)
        block_str = block_str[:start_idx] + new_sub_block_content + block_str[current_idx:]
        return block_str

    if 'common' in spec:
        block = update_sub_block(block, 'common', spec['common'])
    if 'magic' in spec:
        block = update_sub_block(block, 'magic', spec['magic'])

    # Clean up duplicate key typos if any (like double min_rank or double max_rank)
    lines = block.split('\n')
    cleaned_lines = []
    seen_keys = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and ':' in stripped:
            indent = len(line) - len(line.lstrip())
            if indent == 4: # top level fields of the item
                k = stripped.split(':')[0].strip()
                if k in seen_keys:
                    print(f"Removing duplicate key {k} in block")
                    continue
                seen_keys.add(k)
        cleaned_lines.append(line)
    block = '\n'.join(cleaned_lines)

    return block

def modify_file(filepath, specs):
    print(f"Modifying {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the data header line (e.g. "WEAPON_DATA:" or "ARMOR_DATA:" or "SHIELD_DATA:")
    header_match = re.search(r'^[A-Z_]+:\s*$', content, re.MULTILINE)
    if not header_match:
        print("Header not found!")
        return
    
    header_end = header_match.end()
    header_part = content[:header_end]
    items_part = content[header_end:]

    # Split the items part by item keys: "  key:\n"
    # To keep the separators, we use re.split with capturing parentheses
    parts = re.split(r'(\n  [a-zA-Z_0-9]+:\s*\n)', items_part)
    
    # parts[0] is the text before the first item key
    # parts[1] is the first item key
    # parts[2] is the first item block content
    # ...
    new_parts = [parts[0]]
    for i in range(1, len(parts), 2):
        key_line = parts[i]
        block = parts[i+1]
        
        # Extract item key
        key = key_line.replace('\n', '').replace(' ', '').replace(':', '')
        
        if key in specs:
            spec = specs[key]
            block = update_item_block(block, spec)
            
        new_parts.append(key_line)
        new_parts.append(block)

    new_content = header_part + ''.join(new_parts)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Successfully updated {filepath}")

def main():
    weapon_specs = {
        'fighters_sword': {
            'fields': {'min_rank': 'D', 'max_rank': 'B'},
            'common': {'attack': 17}
        },
        'hunters_rapier': {
            'fields': {'min_rank': 'D', 'max_rank': 'B'},
            'common': {'attack': 11}
        },
        'knight_heavy_axe': {
            'fields': {'min_rank': 'D', 'max_rank': 'B'},
            'common': {
                'aggro_mod': 3,
                'attack': 20,
                'accuracy_close': -5,
                'crit_rate': -0.05,
                'hp': 5
            }
        },
        'mages_staff': {
            'fields': {'min_rank': 'D', 'max_rank': 'B'},
            'common': {
                'aggro_mod': -2
            },
            'magic': {
                'fire_damage': 0.15,
                'fire_range': 1,
                'heal_ratio': 0.1,
                'knockback_damage': 0.1,
                'invincible_turns': 2,
                'stave_bonus': 0
            }
        },
        'pilgrims_sword': {
            'fields': {'min_rank': 'D', 'max_rank': 'B'},
            'common': {
                'attack': 15,
                'hp': 10,
                'regen': 10
            },
            'magic': {
                'heal_ratio': 0.1,
                'stave_bonus': 0
            }
        },
        'scount_small_knife': {
            'fields': {
                'name': 'スカウトの小刀',
                'min_rank': 'D',
                'max_rank': 'B'
            },
            'common': {
                'aggro_mod': -1,
                'attack': 13,
                'crit_rate': 0.1,
                'eva': 0.1,
                'block_chance_close': 0.1,
                'armor_penetration': 0.25
            }
        }
    }

    armor_specs = {
        'leather_breastplate': {
            'common': {'regen': 1}
        },
        'pilgrim_robe': {
            'fields': {'min_rank': 'D', 'max_rank': 'B'},
            'common': {
                'hp': 5,
                'regen': 15
            }
        },
        'hunters_armor': {
            'fields': {'min_rank': 'D', 'max_rank': 'B'},
            'common': {
                'accuracy_close': 20,
                'crit_rate': 0.15,
                'defense': 17
            }
        },
        'fighters_armor': {
            'fields': {'min_rank': 'D', 'max_rank': 'B'},
            'common': {
                'defense': 18
            }
        },
        'knight_heavy_armor': {
            'fields': {'min_rank': 'D', 'max_rank': 'B'},
            'common': {
                'aggro_mod': 3,
                'attack': 2,
                'accuracy_close': -5,
                'hp': 5,
                'defense': 20,
                'eva': -0.11
            }
        },
        'pilgrims_armor': {
            'fields': {'min_rank': 'D', 'max_rank': 'B'}
        },
        'scount_armor': {
            'fields': {'min_rank': 'D', 'max_rank': 'B'},
            'common': {
                'crit_rate': 0.1,
                'aggro_mod': -1,
                'armor_penetration': 0.1
            }
        },
        'mages_robe': {
            'fields': {'min_rank': 'D', 'max_rank': 'B'},
            'common': {
                'defense': 10
            },
            'magic': {
                'stave_bonus': 0
            }
        }
    }

    shield_specs = {
        'fighters_sheld': {
            'fields': {'min_rank': 'D', 'max_rank': 'B'},
            'common': {
                'crit_rate': 0.05,
                'hp': 5,
                'block_chance_close': 0.15,
                'block_chance_ranged': 0.1
            }
        },
        'hunters_wood_sheild': {
            'fields': {'min_rank': 'D', 'max_rank': 'B'},
            'common': {
                'crit_rate': 0.15,
                'accuracy_close': 20
            }
        },
        'knight_heavy_sheld': {
            'fields': {'min_rank': 'D', 'max_rank': 'B'},
            'common': {
                'attack': 2,
                'accuracy_close': -5,
                'hp': -10,
                'defense': 2,
                'block_chance_close': 0.1,
                'block_chance_ranged': 0.1
            }
        },
        'mages_sheld': {
            'fields': {'min_rank': 'D', 'max_rank': 'B'},
            'common': {
                'block_chance_close': 0.2,
                'block_chance_ranged': 0.2
            },
            'magic': {
                'stave_bonus': 2
            }
        },
        'pilgrimss_round_sheld': {
            'fields': {'min_rank': 'D', 'max_rank': 'B'},
            'common': {
                'block_chance_close': 0.1,
                'block_chance_ranged': 0.1
            },
            'magic': {
                'stave_bonus': 0
            }
        },
        'scount_blackleather_sheld': {
            'fields': {'min_rank': 'D', 'max_rank': 'B'},
            'common': {
                'aggro_mod': -1,
                'crit_rate': 0.1,
                'armor_penetration': 0.1
            }
        }
    }

    modify_file('/Users/tj/Desktop/2DGame/components/data/master/weapons.yml', weapon_specs)
    modify_file('/Users/tj/Desktop/2DGame/components/data/master/armors.yml', armor_specs)
    modify_file('/Users/tj/Desktop/2DGame/components/data/master/shields.yml', shield_specs)

if __name__ == '__main__':
    main()
