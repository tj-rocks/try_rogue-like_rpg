import os
import json

def load_data_file(filepath, default=None):
    """
    指定されたパスのファイルを読み込む。
    拡張子が .json でも .yml/.yaml があればそちらを優先する。
    """
    if default is None:
        default = {}
        
    base, ext = os.path.splitext(filepath)
    
    # 探す順番: .yml -> .yaml -> 元のパス
    search_paths = []
    if ext == ".json":
        search_paths = [base + ".yml", base + ".yaml", filepath]
    else:
        search_paths = [filepath]
    
    for path in search_paths:
        if os.path.exists(path):
            current_ext = os.path.splitext(path)[1].lower()
            try:
                with open(path, "r", encoding="utf-8") as f:
                    if current_ext in ['.yml', '.yaml']:
                        import yaml
                        return yaml.safe_load(f)
                    else:
                        return json.load(f)
            except Exception as e:
                print(f"Error loading {path}: {e}")
                continue
    return default

# パス設定
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVE_OFFICIAL_PATH = os.path.join(_ROOT, "components/data/savefile/save_official.json")
SAVE_SUSPEND_PATH = os.path.join(_ROOT, "components/data/savefile/save_suspend.json")
SAVE_DATA_PATH = SAVE_OFFICIAL_PATH # 後方互換性のため
MASTER_DATA_DIR = os.path.join(_ROOT, "components/data/master")

def load_master_data(filename, default=None):
    """
    マスターデータを読み込む。MASTER_DATA_DIR 内を探す。
    """
    if default is None:
        default = {}
    return load_data_file(os.path.join(MASTER_DATA_DIR, filename), default)

def generate_rank_floor_map(guild_ranks):
    """ギルドランクの設定から、各ランクに対応する階層範囲(min/max)を算出する"""
    floor_map = {}
    prev_limit = 0
    for r_info in guild_ranks:
        rk = r_info.get("rank")
        if not rk: continue
        limit = r_info.get("limit_floor", prev_limit + 5)
        floor_map[rk] = {
            "min": prev_limit + 1,
            "max": limit + 2, # 少しオーバーラップさせる
            "limit": limit,
            "prev_limit": prev_limit,
            "rank_up_item": r_info.get("rank_up_item")
        }
        prev_limit = limit
    return floor_map

def apply_rank_floor_logic(data_dict, floor_map):
    """データ内の各項目に対し、ランクに基づいた階層設定(min_floor/max_floor)を自動適用する"""
    if not data_dict or not floor_map:
        return
        
    rank_up_items_map = {}
    for rk, f_data in floor_map.items():
        if f_data.get("rank_up_item"):
            spawn_floor = max(1, f_data["prev_limit"])
            rank_up_items_map[f_data["rank_up_item"]] = spawn_floor

    for key, v in data_dict.items():
        if not isinstance(v, dict): continue
        
        if key in rank_up_items_map:
            if v.get("min_floor") is None:
                v["min_floor"] = rank_up_items_map[key]
            if v.get("max_floor") is None:
                v["max_floor"] = rank_up_items_map[key]
            continue
            
        rank = v.get("rank") or v.get("min_rank") or "F"
        if rank not in floor_map:
            rank = "F"
        
        f_range = floor_map[rank]
        if v.get("min_floor") is None:
            v["min_floor"] = f_range["min"]
        if v.get("max_floor") is None:
            v["max_floor"] = f_range["max"]

import math
from systems.math_utils import hardcore_round

def get_normalized_enemy_data(floor_map):
    """モンスターデータを読み込み、カテゴリベースの継承を適用して返す（自動スケーリング無効化版）"""
    raw_enemies = load_master_data("enemies.yml")
    categories = raw_enemies.get("ENEMY_CATEGORIES", {})
    enemies_dict = raw_enemies.get("ENEMY_DATA", {})
    
    normalized_enemies = {}
    
    for key, v in enemies_dict.items():
        if not isinstance(v, dict): continue
        
        # カテゴリデータの継承
        cat_key = v.get("category")
        merged = categories.get(cat_key, {}).copy() if cat_key else {}
        
        # 個体データのマージ（YAMLの値が最終値）
        for k, val in v.items():
            merged[k] = val
        
        normalized_enemies[key] = merged

    # 障害物を統合
    obstacles = load_master_data("obstacles.yml")
    for k, v in obstacles.items():
        if not isinstance(v, dict): continue
        v["is_static"] = True
        normalized_enemies[k] = v
    
    apply_rank_floor_logic(normalized_enemies, floor_map)
    return normalized_enemies

def get_normalized_equipment_data(floor_map):
    """武器・防具・盾のデータを読み込み、カテゴリベースの継承を適用して返す（自動スケーリング無効化版）"""
    raw_equip = load_master_data("equipment.yml")
    weapon_categories = raw_equip.get("WEAPON_CATEGORIES", {})
    armor_categories = raw_equip.get("ARMOR_CATEGORIES", {})
    
    weapons = raw_equip.get("WEAPON_DATA", {})
    armor = raw_equip.get("ARMOR_DATA", {})
    shields = raw_equip.get("SHIELD_DATA", {})
    
    def normalize_no_scaling(data_dict, category_map):
        normalized = {}
        for key, v in data_dict.items():
            if not isinstance(v, dict): continue
            cat_key = v.get("category")
            merged = category_map.get(cat_key, {}).copy() if cat_key else {}
            for k, val in v.items():
                merged[k] = val
            normalized[key] = merged
        return normalized

    normalized_weapons = normalize_no_scaling(weapons, weapon_categories)
    normalized_armor = normalize_no_scaling(armor, armor_categories)
    
    shield_categories = raw_equip.get("SHIELD_CATEGORIES", {})
    normalized_shields = normalize_no_scaling(shields, shield_categories)
    
    apply_rank_floor_logic(normalized_weapons, floor_map)
    apply_rank_floor_logic(normalized_armor, floor_map)
    apply_rank_floor_logic(normalized_shields, floor_map)
    
    return normalized_weapons, normalized_armor, normalized_shields, raw_equip.get("WEAPON_TYPES", {})

def get_normalized_item_data(floor_map):
    """消費アイテム・杖などのデータを読み込み、階層設定を適用して返す"""
    items = load_master_data("items.json")
    consumables = items.get("CONSUMABLE_DATA", {})
    staves = items.get("STAVE_DATA", {})
    lanterns = items.get("LANTERN_DATA", {})
    
    for d in [consumables, staves, lanterns]:
        apply_rank_floor_logic(d, floor_map)
        
    return consumables, staves, lanterns
