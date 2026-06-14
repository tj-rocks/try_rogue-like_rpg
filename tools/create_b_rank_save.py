#!/usr/bin/env python3
"""
Bランクテストデータ作成スクリプト
スカウト+狩人装備、杖全種類、ハイポーション多め、赤い石8個、転移の石3個
"""

import json
import os
import sys

# プロジェクトルートをパスに追加
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# 保存先
SAVE_DIR = os.path.join(ROOT, "components/data/savefile")
SAVE_PATH = os.path.join(SAVE_DIR, "save_scout_hunter_b.json")

# アイテムIDカウンター
_item_id = 0
def new_item_id():
    global _item_id
    _item_id += 1
    return _item_id

_equip_id = 0
def new_equip_id():
    global _equip_id
    _equip_id += 1
    return _equip_id

# データ作成
data = {
    "x": 704,
    "y": 320,
    "hp": 150,
    "max_hp": 150,
    "coin": 50000,
    "bank_coin": 10000,
    "attack": 15,
    "defense": 10,
    "gp": 800,  # Bランク相当
    "rank": "B",
    "floor": 0,  # 村
    "guild_rank_up_item_collected": True,
    "tutorial_completed": True,
    "tutorial_skipped": False,
    "visited_rest_points": ["0", "1"],  # チュートリアルと1st_rest_pointを訪問済み
    
    # インベントリアイテム
    "items": [],
    
    # 武器インベントリ
    "weapon_inventory": [
        {
            "iid": new_equip_id(),
            "type": "weapon",
            "key": "scount_small_knife",
            "enhance": 0,
            "stats": {}
        },
        {
            "iid": new_equip_id(),
            "type": "weapon", 
            "key": "hunter_bow",
            "enhance": 0,
            "stats": {}
        }
    ],
    "equipped_weapon": 1,  # スカウトの小刀を装備
    
    # 防具インベントリ
    "armor_inventory": [
        {
            "iid": new_equip_id(),
            "type": "armor",
            "key": "scount_clothes",
            "enhance": 0,
            "stats": {}
        },
        {
            "iid": new_equip_id(),
            "type": "armor",
            "key": "hunter_vest",
            "enhance": 0,
            "stats": {}
        }
    ],
    "equipped_armor": 3,  # スカウトの服を装備
    
    # 盾インベントリ
    "shield_inventory": [
        {
            "iid": new_equip_id(),
            "type": "shield",
            "key": "scount_buckler",
            "enhance": 0,
            "stats": {}
        },
        {
            "iid": new_equip_id(),
            "type": "shield",
            "key": "hunter_shield",
            "enhance": 0,
            "stats": {}
        }
    ],
    "equipped_shield": 5,  # スカウトバックラー装備
    
    # 杖インベントリ（全種類）
    "stave_inventory": [
        {"iid": new_item_id(), "key": "fire_stave", "charges": 5},
        {"iid": new_item_id(), "key": "ice_stave", "charges": 5},
        {"iid": new_item_id(), "key": "heal_stave", "charges": 5},
        {"iid": new_item_id(), "key": "light_stave", "charges": 5},
        {"iid": new_item_id(), "key": "wind_stave", "charges": 5},
        {"iid": new_item_id(), "key": "holy_stave", "charges": 5},
        {"iid": new_item_id(), "key": "dark_stave", "charges": 5},
    ],
    
    # アクセサリインベントリ
    "accessory_inventory": [
        {
            "iid": new_equip_id(),
            "type": "accessory",
            "key": "lantern_basic",  # カンテラ
            "enhance": 5,  # 少し鍛えてある
            "stats": {"lantern_bonus": 5}
        },
        {
            "iid": new_equip_id(),
            "type": "accessory",
            "key": "scount_ring",  # スカウトの指輪
            "enhance": 0,
            "stats": {}
        },
        {
            "iid": new_equip_id(),
            "type": "accessory",
            "key": "hunter_amulet",  # 狩人のお守り
            "enhance": 0,
            "stats": {}
        }
    ],
    "equipped_accessory": 12,  # カンテラ装備
    
    # 消費アイテムをインベントリに追加
    "invincible_turns": 0,
    "attack_buff_turns": 0,
    "attack_buff_val": 0,
    "defense_buff_turns": 0,
    "defense_buff_val": 0,
    "active_quests": [],
    "completed_quests": [],
    "completed_fixed_quests": [],
    "warehouse_items": [],
    "cursed_stats": []
}

# 消費アイテムの追加
# ハイポーション x20
for _ in range(20):
    data["items"].append({"type": "consumable", "key": "high_potion", "id": new_item_id()})

# 赤い石（鍛冶用）x8
for _ in range(8):
    data["items"].append({"type": "consumable", "key": "red_stone", "id": new_item_id()})

# 転移の石 x3
for _ in range(3):
    data["items"].append({"type": "consumable", "key": "warp_stone", "id": new_item_id()})

# 保存（既存ファイルは上書きしない）
os.makedirs(SAVE_DIR, exist_ok=True)

if os.path.exists(SAVE_PATH):
    print(f"⚠️  {SAVE_PATH} は既に存在します")
    response = input("上書きしますか？ (y/N): ").strip().lower()
    if response != 'y':
        print("キャンセルしました。既存データは保持されています。")
        sys.exit(0)

with open(SAVE_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✅ Bランクテストデータを作成しました: {SAVE_PATH}")
print(f"   武器: スカウトの小刀 + 狩人の弓")
print(f"   防具: スカウトの服")
print(f"   杖: {len(data['stave_inventory'])}種類")
print(f"   ハイポーション: 20個")
print(f"   赤い石: 8個")
print(f"   転移の石: 3個")
print(f"   所持金: {data['coin']}G")
print(f"   GP: {data['gp']}")
print(f"   ランク: {data['rank']}")
