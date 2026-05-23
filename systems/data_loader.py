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
SAVE_DIR = os.path.join(_ROOT, "components/data/savefile")
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR, exist_ok=True)

SAVE_OFFICIAL_PATH = os.path.join(SAVE_DIR, "save_official.json")

# [NEW] テストモード時はさらに優先して別ファイルにする
if os.environ.get("TEST_MODE") == "1":
    SAVE_OFFICIAL_PATH = os.path.join(_ROOT, "components/data/savefile/save_data_test.json")
# [NEW] デバッグモード時はセーブファイルを分離する
elif os.environ.get("DEBUG_MODE") == "1":
    SAVE_OFFICIAL_PATH = os.path.join(_ROOT, "components/data/savefile/save_data_debug.json")

SAVE_SUSPEND_PATH = SAVE_OFFICIAL_PATH # 一本化
SAVE_DATA_PATH = SAVE_OFFICIAL_PATH # 後方互換性
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
        
        # チュートリアルランク(-)の場合は、便宜上 F ランク(1階〜)と同じ開始地点にする
        current_min = prev_limit + 1
        if rk == "-":
            current_min = 1
            
        floor_map[rk] = {
            "min": current_min,
            "max": limit + 2, # 少しオーバーラップさせる
            "limit": limit,
            "prev_limit": prev_limit,
            "rank_up_item": r_info.get("rank_up_item")
        }
        # ランク F 以降の計算のために prev_limit を更新
        # ただしランク - は limit 0 なので、実質 F の prev_limit は 0 のまま維持される
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
            
        min_rk = v.get("min_rank") or v.get("rank") or "F"
        max_rk = v.get("max_rank")
        
        # チュートリアルランク(-)の場合は F ランク相当として扱う
        if min_rk == "-" or min_rk not in floor_map:
            min_rk = "F"
        
        f_range_min = floor_map[min_rk]
        if v.get("min_floor") is None:
            v["min_floor"] = f_range_min["min"]
            
        if v.get("max_floor") is None:
            if max_rk and max_rk in floor_map:
                v["max_floor"] = floor_map[max_rk]["max"]
            else:
                v["max_floor"] = f_range_min["max"]

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
        
        normalized_enemies[key] = v.copy()

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
    raw_weapons = load_master_data("weapons.yml")
    raw_armors = load_master_data("armors.yml")
    raw_shields = load_master_data("shields.yml")
    
    weapons = raw_weapons.get("WEAPON_DATA", {})
    armor = raw_armors.get("ARMOR_DATA", {})
    shields = raw_shields.get("SHIELD_DATA", {})
    
    apply_rank_floor_logic(weapons, floor_map)
    apply_rank_floor_logic(armor, floor_map)
    apply_rank_floor_logic(shields, floor_map)
    
    return weapons, armor, shields

def get_normalized_item_data(floor_map):
    """消費アイテム・杖などのデータを読み込み、階層設定を適用して返す"""
    items = load_master_data("items.yml")
    consumables = items.get("CONSUMABLE_DATA", {})
    staves = items.get("STAVE_DATA", {})
    lanterns = items.get("LANTERN_DATA", {})
    
    # [DEBUG] 読み込み確認
    print(f"[DataLoader] Items loaded: Consumables={len(consumables)}, Staves={len(staves)}, Lanterns={len(lanterns)}")
    
    for d in [consumables, staves, lanterns]:
        apply_rank_floor_logic(d, floor_map)
        
    return consumables, staves, lanterns

def get_story_data():
    """オープニング・エンディングなどのストーリーテキストを読み込む"""
    return load_master_data("story.yml")
