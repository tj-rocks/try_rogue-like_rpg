import random
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, CONSUMABLE_DATA, STAVE_DATA, ITEM_DROP_RATES
from systems.data_loader import get_normalized_enemy_data
from constants import RANK_FLOOR_MAP

def get_item_rarity(item_key):
    if item_key in WEAPON_DATA: return WEAPON_DATA[item_key].get("rarity", 1)
    if item_key in ARMOR_DATA: return ARMOR_DATA[item_key].get("rarity", 1)
    if item_key in SHIELD_DATA: return SHIELD_DATA[item_key].get("rarity", 1)
    if item_key in CONSUMABLE_DATA: return CONSUMABLE_DATA[item_key].get("rarity", 1)
    if item_key in STAVE_DATA: return STAVE_DATA[item_key].get("rarity", 1)
    return 1

def pick_item(item_list):
    if not item_list: return None
    weights = []
    for item in item_list:
        rarity = get_item_rarity(item)
        weights.append(ITEM_DROP_RATES.get(rarity, 0.1))
    return random.choices(item_list, weights=weights, k=1)[0]

def simulate_drops(enemy_key, iterations=10000):
    enemy_data = get_normalized_enemy_data(RANK_FLOOR_MAP)
    enemy = enemy_data.get(enemy_key)
    if not enemy:
        print(f"Enemy {enemy_key} not found.")
        return

    normal_rate = enemy.get("normal_drop_rate", 0.0)
    rare_rate = enemy.get("rare_drop_rate", 0.0)
    drops = enemy.get("drops", {})
    normal_list = drops.get("normal", [])
    rare_list = drops.get("rare", [])

    results = {"None": 0}
    for _ in range(iterations):
        if rare_list and random.random() <= rare_rate:
            item = pick_item(rare_list)
            results[item] = results.get(item, 0) + 1
        elif normal_list and random.random() <= normal_rate:
            item = pick_item(normal_list)
            results[item] = results.get(item, 0) + 1
        else:
            results["None"] += 1

    print(f"--- Simulation for {enemy_key} ({iterations} kills) ---")
    print(f"Base rates -> Normal: {normal_rate*100}%, Rare: {rare_rate*100}%")
    print(f"Available Normal drops: {normal_list}")
    print(f"Available Rare drops:   {rare_list}")
    print("-" * 40)
    
    total_drops = sum(v for k, v in results.items() if k != "None")
    print(f"No Drop:   {results['None']} times ({results['None']/iterations*100:.2f}%)")
    print(f"Total Drops: {total_drops} times ({total_drops/iterations*100:.2f}%)\n")
    
    for item, count in sorted(results.items(), key=lambda x: x[1], reverse=True):
        if item == "None": continue
        rarity = get_item_rarity(item)
        print(f" - {item:<20} (Rarity {rarity}): {count:>5} times ({count/iterations*100:05.2f}%)")

if __name__ == "__main__":
    simulate_drops("skeleton", 10000)
    print("\n")
    simulate_drops("mawaru_kame", 10000)
