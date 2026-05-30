import re
import random

random.seed(42)  # For deterministic variety

input_path = '/Users/tj/Desktop/2DGame/components/data/master/enemies.yml'

with open(input_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

output_lines = []
current_block_lines = []
in_enemy_data = False

for line in lines:
    stripped = line.strip()
    # Check if we enter ENEMY_DATA
    if line.startswith('ENEMY_DATA:'):
        in_enemy_data = True
        output_lines.append(line)
        continue
    
    if not in_enemy_data:
        output_lines.append(line)
        continue

    # Check for enemy entry start (exactly 2 spaces indent, followed by key, colon)
    match_entry = re.match(r'^  ([a-zA-Z0-9_-]+):\s*(#.*)?$', line)
    
    if match_entry:
        # Flush previous block if any
        if current_block_lines:
            # Process previous block
            block_text = "".join(current_block_lines)
            if 'damaged_detect_range:' not in block_text:
                # Determine value
                is_boss = 'is_boss: true' in block_text
                enemy_id = current_block_lines[0].split(':')[0].strip()
                
                # Determine name
                name_match = re.search(r'name:\s*([^\n]+)', block_text)
                name = name_match.group(1).strip() if name_match else ""
                
                if is_boss:
                    val = 100
                elif "kame" in enemy_id or "カメ" in name:
                    val = 6
                elif "slime" in enemy_id or "スライム" in name:
                    val = 8
                elif "tako" in enemy_id or "たこ" in name:
                    val = 10
                elif "spider" in enemy_id or "クモ" in name:
                    val = 15
                elif "skeleton" in enemy_id or "骸骨" in name or "スケルトン" in name:
                    val = 25
                else:
                    val = random.choice([12, 15, 20])
                
                # Add before last empty line or insert at the end
                # Find the position of attack_priority: or similar, or just append at the end
                insert_idx = len(current_block_lines)
                # If the last line is empty, put it before the empty line
                if current_block_lines[-1].strip() == "":
                    insert_idx -= 1
                current_block_lines.insert(insert_idx, f"    damaged_detect_range: {val}\n")
            
            output_lines.extend(current_block_lines)
            current_block_lines = []
        
        current_block_lines.append(line)
    else:
        # If we hit an unindented comment or top level section outside ENEMY_DATA, we flush
        if (line.startswith('#') or (re.match(r'^[a-zA-Z0-9_-]+:', line) and not line.startswith('  '))) and current_block_lines:
            block_text = "".join(current_block_lines)
            if 'damaged_detect_range:' not in block_text:
                is_boss = 'is_boss: true' in block_text
                enemy_id = current_block_lines[0].split(':')[0].strip()
                name_match = re.search(r'name:\s*([^\n]+)', block_text)
                name = name_match.group(1).strip() if name_match else ""
                if is_boss:
                    val = 100
                elif "kame" in enemy_id or "カメ" in name:
                    val = 6
                elif "slime" in enemy_id or "スライム" in name:
                    val = 8
                elif "tako" in enemy_id or "たこ" in name:
                    val = 10
                elif "spider" in enemy_id or "クモ" in name:
                    val = 15
                elif "skeleton" in enemy_id or "骸骨" in name or "スケルトン" in name:
                    val = 25
                else:
                    val = random.choice([12, 15, 20])
                
                insert_idx = len(current_block_lines)
                if current_block_lines[-1].strip() == "":
                    insert_idx -= 1
                current_block_lines.insert(insert_idx, f"    damaged_detect_range: {val}\n")
            output_lines.extend(current_block_lines)
            current_block_lines = []
            output_lines.append(line)
        else:
            if current_block_lines:
                current_block_lines.append(line)
            else:
                output_lines.append(line)

# Flush final block
if current_block_lines:
    block_text = "".join(current_block_lines)
    if 'damaged_detect_range:' not in block_text:
        is_boss = 'is_boss: true' in block_text
        enemy_id = current_block_lines[0].split(':')[0].strip()
        name_match = re.search(r'name:\s*([^\n]+)', block_text)
        name = name_match.group(1).strip() if name_match else ""
        if is_boss:
            val = 100
        elif "kame" in enemy_id or "カメ" in name:
            val = 6
        elif "slime" in enemy_id or "スライム" in name:
            val = 8
        elif "tako" in enemy_id or "たこ" in name:
            val = 10
        elif "spider" in enemy_id or "クモ" in name:
            val = 15
        elif "skeleton" in enemy_id or "骸骨" in name or "スケルトン" in name:
            val = 25
        else:
            val = random.choice([12, 15, 20])
        
        insert_idx = len(current_block_lines)
        if current_block_lines[-1].strip() == "":
            insert_idx -= 1
        current_block_lines.insert(insert_idx, f"    damaged_detect_range: {val}\n")
    output_lines.extend(current_block_lines)

# Write back
with open(input_path, 'w', encoding='utf-8') as f:
    f.writelines(output_lines)

print("Done! Added damaged_detect_range to all enemies.")
