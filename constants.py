"""
constants.py — ゲーム全体で使うキー設定やパラメータを一箇所にまとめた定数ファイル
このファイルはシステム設定に特化し、ゲームバランスやデータは JSON から読み込むように整理されました。
"""
import pygame
from wordings import Text
from systems.data_loader import (
    load_master_data, MASTER_DATA_DIR,
    generate_rank_floor_map, get_normalized_enemy_data,
    get_normalized_equipment_data, get_normalized_item_data
)

# ==============================================================================
# 🎮 1. システム・操作設定 (System & Input)
# ==============================================================================

GAME_TITLE = "ギルドとダンジョン"
GAME_SUBTITLE = "〜父の軌跡〜"
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 900
TILE_SIZE = 64

# --- デバッグ・ログ設定 ---
ENABLE_DEBUG_LOGGING = True  # Falseにすると全print出力がミュートされ、パフォーマンスが向上します

# --- 戦闘バランス設定 ---
MIN_HIT_RATE = 0.10  # 最低命中率（0.0で完全回避可能、0.10で最低10%命中）

# --- BGM設定 ---
BGM_TITLE   = "components/sounds/bgm/winding_adventure.mp3"
BGM_OPENING = "components/sounds/bgm/winding_adventure.mp3"
BGM_VILLAGE  = "components/sounds/bgm/village_theme.mp3"
BGM_DEFEAT   = "components/sounds/bgm/gameover.mp3"
BGM_OVERFLOW = "components/sounds/bgm/beyond_the_suffer.mp3"
BGM_BOSS     = "components/sounds/bgm/get_hornor.mp3"
SOUND_QUEST_COMPLETE = "components/sounds/sfx/quest_complete.wav"
SOUND_BOSS_VICTORY   = "components/sounds/sfx/killed_boss.wav"  # ボス撃破時の専用SE
SOUND_RANK_UP        = "components/sounds/sfx/quest_complete.wav"  # ランクアップ時の効果音
SOUND_INN_REST       = "components/sounds/sfx/recharge.wav"        # 宿屋宿泊時の効果音
SOUND_CURSOR_MOVE    = "components/sounds/sfx/cursor.wav"          # カーソル移動音
SOUND_SELECT         = "components/sounds/sfx/select_new.wav"      # 決定音
SOUND_CANCEL         = "components/sounds/sfx/cancel_new.wav"      # キャンセル音
SOUND_STAIRS_UP      = "components/sounds/sfx/stairs.wav"          # 階段移動音
SOUND_STAIRS_DOWN    = "components/sounds/sfx/stairs.wav"          # 階段移動音
SOUND_AREA_MESSAGE   = "components/sounds/sfx/floor_description.mp3" # エリア名演出SE
SOUND_HAMMER         = "components/sounds/sfx/attack_1.wav"       # 鍛冶屋の叩く音
SOUND_BLACKSMITH_FINISH = "components/sounds/sfx/buy.wav"        # 鍛冶完了音


# --- 操作キー設定 ---
KEY_MOVE_UP    = pygame.K_UP
KEY_MOVE_DOWN  = pygame.K_DOWN
KEY_MOVE_LEFT  = pygame.K_LEFT
KEY_MOVE_RIGHT = pygame.K_RIGHT

KEY_ATTACK     = pygame.K_SPACE
KEY_TURN_ONLY  = pygame.K_LSHIFT

KEY_CONFIRM     = pygame.K_SPACE
KEY_CANCEL      = pygame.K_x
KEY_INVENTORY   = pygame.K_i
KEY_STATUS      = pygame.K_s
KEY_MENU        = pygame.K_m
KEY_MAP         = pygame.K_TAB
KEY_DEBUG       = pygame.K_F12

# --- 基本アニメーション ---
WALK_ANIMATION_SPEED = 10
BREATHING_SCALE = 0.97

# --- UI Aesthetics ---
# Data Source: components/data/master/ui.yml
UI_SETTINGS = load_master_data("ui.yml")

# ==============================================================================
# ⚖️ 2. ゲームバランス設定 (Game Balance)
# ==============================================================================
# Data Source: components/data/master/balance.yml
_balance = load_master_data("balance.yml")

# ------------------------------------------------------------------------------
# 👤 PLAYER (プレイヤー)
# ------------------------------------------------------------------------------
# Data Source: balance.yml (PLAYER)
_p = _balance.get("PLAYER", {})

PLAYER_HP           = _p.get("max_hp", 100)
PLAYER_ATTACK       = _p.get("attack", 5)
PLAYER_DEFENSE      = _p.get("defense", 5)
PLAYER_MOVE_SPEED   = 300 # 1秒あたりの移動ピクセル数（フレームレートに依存しなくなりました）
PLAYER_COIN         = _p.get("initial_coin", 100)
PLAYER_ORE          = _p.get("initial_ore", 0)
MAX_ITEM_SLOTS      = _p.get("max_item_slots", 20)
MAX_EQUIP_SLOTS     = _p.get("max_equip_slots", 10)
MAX_STAVE_SLOTS     = _p.get("max_stave_slots", 10)
MAX_WAREHOUSE_SLOTS = _p.get("max_warehouse_slots", 20)
PLAYER_ACCURACY_CLOSE = _p.get("accuracy_close", 100)
PLAYER_ACCURACY_RANGED = _p.get("accuracy_ranged", 100)
PLAYER_EVASION      = _p.get("evasion", 1)
PLAYER_REGEN_BASE   = _p.get("regen_base", 0.1)
PLAYER_REGEN_MULTIPLIER = _p.get("regen_multiplier", 0.05)

# --- 呪いシステム設定 (Curse System) ---
_curse = _balance.get("CURSE_SYSTEM", {})
CURSE_REDUCTION_RATE = _curse.get("reduction_rate", 0.10)
CURSE_RECOVERY_COST_GP_PER_LEVEL = _curse.get("recovery_cost_gp_per_level", 50)
CURSE_RECOVERY_COST_GOLD_MULTIPLIER = _curse.get("recovery_cost_gold_multiplier", 10)

# --- 強化済み装備ドロップ設定 (Enhanced Drop) ---
_enh_drop = _balance.get("ENHANCED_DROP_CONFIG", {})
ENHANCED_DROP_MIN_FLOOR = _enh_drop.get("min_floor", 21)
ENHANCED_DROP_CHANCE = _enh_drop.get("occurrence_chance", 0.10)
ENHANCED_DROP_STAT_ALLOCATION = _enh_drop.get("stat_allocation", "random")
ENHANCED_DROP_RANK_RANGE = _enh_drop.get("rank_enhance_range", {
    "F": [0, 0], "E": [0, 0], "D": [0, 0],
    "C": [1, 5], "B": [3, 7], "A": [4, 8], "S": [5, 9], "SS": [5, 12]
})

PLAYER_WEAPON   = "old_sword"
PLAYER_ARMOR    = "adventurers_clothes"
PLAYER_SHIELD   = None

# ------------------------------------------------------------------------------
# 🏰 DUNGEON (ダンジョン生成・外観)
# ------------------------------------------------------------------------------
# Data Source: balance.yml (DUNGEON)
_d = _balance.get("DUNGEON", {})
DUNGEON_MIN_ROOMS              = _d.get("DUNGEON_MIN_ROOMS", 5)
DUNGEON_MAX_ROOMS              = _d.get("DUNGEON_MAX_ROOMS", 60)
DUNGEON_ROOM_MAX_CAP           = _d.get("DUNGEON_ROOM_MAX_CAP", 30)
DUNGEON_ROOM_MIN_CAP           = _d.get("DUNGEON_ROOM_MIN_CAP", 10)
DUNGEON_ROOM_GROWTH_LIMIT_FLOOR = _d.get("DUNGEON_ROOM_GROWTH_LIMIT_FLOOR", 50)
DUNGEON_ROOM_INCREASE_INTERVAL = _d.get("DUNGEON_ROOM_INCREASE_INTERVAL", 3) # 何階ごとに部屋を増やすか
DUNGEON_MIN_ROOM_DISTANCE      = _d.get("DUNGEON_MIN_ROOM_DISTANCE", 5)      # 部屋同士の最小間隔
DUNGEON_ROOM_DISTANCE_GROWTH   = _d.get("DUNGEON_ROOM_DISTANCE_GROWTH", 0.5)
DUNGEON_CORRIDOR_W2_CHANCE     = _d.get("DUNGEON_CORRIDOR_W2_CHANCE", 0.2)     # 通路が2マス幅になる確率
DUNGEON_STAIRS_FLOOR_RADIUS    = _d.get("DUNGEON_STAIRS_FLOOR_RADIUS", 1)
DUNGEON_MIN_ROOM_SIZE          = _d.get("DUNGEON_MIN_ROOM_SIZE", 5)
DUNGEON_MAX_ROOM_SIZE          = _d.get("DUNGEON_MAX_ROOM_SIZE", 25)
DUNGEON_ROOM_SIZE_GROWTH       = _d.get("DUNGEON_ROOM_SIZE_GROWTH", 0.05)
DUNGEON_ROOM_MIN_SIZE_CAP      = _d.get("DUNGEON_ROOM_MIN_SIZE_CAP", 10)
DUNGEON_ROOM_MAX_SIZE_CAP      = _d.get("DUNGEON_ROOM_MAX_SIZE_CAP", 30)

DUNGEON_VOID_COLOR = (10, 10, 15)
WALL_TOP_SHADOW_HEIGHT_RATIO = 0.10  # 影の高さ（タイルサイズに対する比率）
WALL_TOP_SHADOW_ALPHA = 190           # 影の濃さ (0-255)

# ------------------------------------------------------------------------------
# 👹 ENEMY (敵AI・スポーン・戦闘)
# ------------------------------------------------------------------------------
# Data Source: balance.yml (ENEMY_AI)
_ai = _balance.get("ENEMY_AI", {})
ENEMY_AGGRO_RADIUS         = _ai.get("ENEMY_AGGRO_RADIUS", 7)   # 索敵範囲
ENEMY_WANDER_CHANCE        = _ai.get("ENEMY_WANDER_CHANCE", 0.5) # うろつき確率
ENEMY_SPAWN_MIN            = _ai.get("ENEMY_SPAWN_MIN", 1)
ENEMY_SPAWN_MAX            = _ai.get("ENEMY_SPAWN_MAX", 2)
ENEMY_TOTAL_MAX            = _ai.get("ENEMY_TOTAL_MAX", 10)     # フロア全体の合計上限
ENEMY_RESPAWN_INTERVAL     = _ai.get("ENEMY_RESPAWN_INTERVAL", 50.0) # リスポーン間隔
ENEMY_RESPAWN_MIN_INTERVAL = _ai.get("ENEMY_RESPAWN_MIN_INTERVAL", 20.0)
ENEMY_RESPAWN_SCALE_SUB    = _ai.get("ENEMY_RESPAWN_SCALE_SUB", 0.5)  # 1階ごとに短縮する秒数

# スケーリング
ENEMY_SPAWN_SCALE_EVERY = _ai.get("ENEMY_SPAWN_SCALE_EVERY", 10)
ENEMY_SPAWN_SCALE_ADD   = _ai.get("ENEMY_SPAWN_SCALE_ADD", 1)
ENEMY_TOTAL_SCALE_EVERY = _ai.get("ENEMY_TOTAL_SCALE_EVERY", 5)
ENEMY_TOTAL_SCALE_ADD   = _ai.get("ENEMY_TOTAL_SCALE_ADD", 2)

# 位置制御
ENEMY_SPAWN_SAFE_RADIUS = _ai.get("ENEMY_SPAWN_SAFE_RADIUS", 5)
ENEMY_SPAWN_ATTEMPTS    = _ai.get("ENEMY_SPAWN_ATTEMPTS", 10)
ENEMY_SPAWN_SCATTER     = _ai.get("ENEMY_SPAWN_SCATTER", 5)

# 特殊スポーン
ENEMY_SPAWN_NEAR_RANDOM_FLOOR = _ai.get("ENEMY_SPAWN_NEAR_RANDOM_FLOOR", 20)
ENEMY_SPAWN_NEAR_CHANCE       = _ai.get("ENEMY_SPAWN_NEAR_CHANCE", 1)
ENEMY_SPAWN_NEAR_FLOOR        = _ai.get("ENEMY_SPAWN_NEAR_FLOOR", 50)

# 困惑度ごとのぼーっと確率テーブル (stupidity_level -> 0.0〜1.0)
# balance.yml の STUPIDITY_WANDER_RATES を読み込む。キーを int に変換して使用。
_default_wander = {0:0.00, 1:0.10, 2:0.20, 3:0.30, 4:0.40,
                   5:0.50, 6:0.60, 7:0.70, 8:0.80, 9:0.90, 10:1.00}
STUPIDITY_WANDER_RATES = {int(k): float(v)
                           for k, v in _ai.get("STUPIDITY_WANDER_RATES", _default_wander).items()}

# 逃げ道封鎖AI 有効フラグ (balance.yml ENEMY_ESCAPE_BLOCK_ENABLED)
ENEMY_ESCAPE_BLOCK_ENABLED: bool = _ai.get("ENEMY_ESCAPE_BLOCK_ENABLED", True)
BOSS_NO_QUEST_SPAWN_CHANCE = _ai.get("BOSS_NO_QUEST_SPAWN_CHANCE", 0.05)

# ------------------------------------------------------------------------------
# ⚔️ COMBAT (戦闘システム・演出)
# ------------------------------------------------------------------------------
# Data Source: balance.yml (COMBAT)
_cb = _balance.get("COMBAT", {})
CRITICAL_RATE_MAX           = _cb.get("CRITICAL_RATE_MAX", 0.7)
CRITICAL_DAMAGE_MULTIPLIER  = _cb.get("CRITICAL_DAMAGE_MULTIPLIER", 2.0)
BACKSTAB_CRITICAL_DAMAGE_MULTIPLIER = _cb.get("BACKSTAB_CRITICAL_DAMAGE_MULTIPLIER", 2.5)
BACKSTAB_CRIT_BONUS         = _cb.get("BACKSTAB_CRIT_BONUS", 0.25)
ENEMY_THINK_LIMIT_PER_FRAME = _cb.get("ENEMY_THINK_LIMIT_PER_FRAME", 10)

ATTACK_TAME_DURATION    = _cb.get("ATTACK_TAME_DURATION", 0)
ATTACK_STRIKE_DURATION  = _cb.get("ATTACK_STRIKE_DURATION", 16)
ATTACK_ANIMATION_FRAMES = ATTACK_TAME_DURATION + ATTACK_STRIKE_DURATION
ATTACK_PRE_DELAY_FRAMES = _cb.get("ATTACK_PRE_DELAY_FRAMES", 30)
HIT_STUN_DURATION       = _cb.get("HIT_STUN_DURATION", 12)
DAMAGE_FLASH_FRAMES     = _cb.get("DAMAGE_FLASH_FRAMES", 6)
COMBAT_LOG_WAIT_FRAMES  = _cb.get("COMBAT_LOG_WAIT_FRAMES", 60)
INTER_ACTION_BREATHER   = _cb.get("INTER_ACTION_BREATHER", 1)

# ------------------------------------------------------------------------------
# 💎 ITEMS (アイテム・ドロップ)
# ------------------------------------------------------------------------------
# Data Source: balance.yml (ITEMS)
_i = _balance.get("ITEMS", {})
FLOOR_ITEM_SPAWN_MIN   = _i.get("FLOOR_ITEM_SPAWN_MIN", 1)
FLOOR_ITEM_SPAWN_MAX   = _i.get("FLOOR_ITEM_SPAWN_MAX", 4)
FLOOR_ITEM_ROOM_RATIO   = _i.get("FLOOR_ITEM_ROOM_RATIO", 0.7)
FLOOR_ITEM_SCALE_LIMIT = _i.get("FLOOR_ITEM_SCALE_LIMIT", 30)
FLOOR_ITEM_SCALE_EVERY = _i.get("FLOOR_ITEM_SCALE_EVERY", 10)
FLOOR_ITEM_SCALE_ADD   = _i.get("FLOOR_ITEM_SCALE_ADD", 1) 

DROP_RATE_MULTIPLIER    = _i.get("DROP_RATE_MULTIPLIER", 1.0)
ITEM_DROP_RATES = {
    1: 0.25, 2: 0.15, 3: 0.10, 4: 0.05, 5: 0.05, 6: 0.03, 7: 0.01, 8: 0.005
}
RANK_TO_RARITY = {
    "F": 1, "E": 2, "D": 3, "C": 4, "B": 5, "A": 6, "S": 7, "SS": 8
}

# ------------------------------------------------------------------------------
# 🕸️ TRAPS (罠)
# ------------------------------------------------------------------------------
# Data Source: balance.yml (TRAPS)
_t = _balance.get("TRAPS", {})
TRAP_SPAWN_MIN         = _t.get("TRAP_SPAWN_MIN", 1)
TRAP_SPAWN_MAX         = _t.get("TRAP_SPAWN_MAX", 10)
TRAP_SPAWN_SCALE_LIMIT = _t.get("TRAP_SPAWN_SCALE_LIMIT", 15)
TRAP_SPAWN_SCALE_EVERY = _t.get("TRAP_SPAWN_SCALE_EVERY", 10)
TRAP_SPAWN_SCALE_ADD   = _t.get("TRAP_SPAWN_SCALE_ADD", 1)

# ------------------------------------------------------------------------------
# 🧱 OBSTACLES (障害物)
# ------------------------------------------------------------------------------
# Data Source: balance.yml (OBSTACLES)
_o = _balance.get("OBSTACLES", {})
OBSTACLE_SPAWN_MIN         = _o.get("OBSTACLE_SPAWN_MIN", 1)
OBSTACLE_SPAWN_MAX         = _o.get("OBSTACLE_SPAWN_MAX", 10)
OBSTACLE_TOTAL_MAX         = float(_o.get("OBSTACLE_TOTAL_MAX", 3))
OBSTACLE_SPAWN_LIMIT       = _o.get("OBSTACLE_SPAWN_LIMIT", 30)
OBSTACLE_SPAWN_SCALE_EVERY = _o.get("OBSTACLE_SPAWN_SCALE_EVERY", 10)
OBSTACLE_SPAWN_SCALE_ADD   = _o.get("OBSTACLE_SPAWN_SCALE_ADD", 1)
OBSTACLE_TOTAL_SCALE_EVERY = _o.get("OBSTACLE_TOTAL_SCALE_EVERY", 10)
OBSTACLE_TOTAL_SCALE_ADD   = _o.get("OBSTACLE_TOTAL_SCALE_ADD", 2)

# ------------------------------------------------------------------------------
# 💜 STATUS_EFFECTS (状態異常)
# ------------------------------------------------------------------------------
# Data Source: balance.yml (STATUS_EFFECTS)
STATUS_EFFECTS = _balance.get("STATUS_EFFECTS", {})
POISON_CURE_FEE = STATUS_EFFECTS.get("poison", {}).get("cure_fee", 100)

# 🏠 VILLAGE_SERVICES (村の施設・サービス料金)
# ------------------------------------------------------------------------------
# Data Source: balance.yml (VILLAGE_SERVICES)
_vs = _balance.get("VILLAGE_SERVICES", {})
INN_FEE       = _vs.get("INN_FEE", 60)
DOCTOR_FEE    = _vs.get("DOCTOR_FEE", 50)
WAREHOUSE_FEE = _vs.get("WAREHOUSE_FEE", 10)

# 🧙 MAGIC_SHOP (魔法屋)
_ms = _vs.get("MAGIC_SHOP", {})
RECHARGE_COST_PER_CHARGE = _ms.get("RECHARGE_COST_PER_CHARGE", 15)
STAVE_PRICE_MULTIPLIER   = _ms.get("STAVE_PRICE_MULTIPLIER", 1.5)

# 🤝 GUILD_QUEST (ギルド依頼)
# ------------------------------------------------------------------------------
# Data Source: balance.yml (GUILD_QUEST)
_gq = _balance.get("GUILD_QUEST", {})
GUILD_QUEST_GP_DIVISOR = _gq.get("GUILD_QUEST_GP_DIVISOR", 10)
GP_RANK_DIFF_MULTIPLIERS = _gq.get("GP_RANK_DIFF_MULTIPLIERS", {
    "CHALLENGE": 2.0, "MATCH": 1.5, "EASY": 0.5
})

# ------------------------------------------------------------------------------

# ==============================================================================
# 👹 3. マスターデータ (Master Data - Loaded from JSON)
# ==============================================================================

# --- ギルドランク & 階層マップ ---
# Data Source: components/data/master/guild.json
_guild = load_master_data("guild.json")
GUILD_RANKS = _guild.get("GUILD_RANKS", [])
RANK_ORDER  = _guild.get("RANK_ORDER", [])
RANKUP_GIFTS = _guild.get("RANKUP_GIFTS", [])
RANK_FLOOR_MAP = generate_rank_floor_map(GUILD_RANKS)

# --- 各種データの正規化読み込み ---
# Data Source: components/data/master/ (enemies.json, obstacles.yml, equipment.json, items.json)
ENEMY_DATA = get_normalized_enemy_data(RANK_FLOOR_MAP)
WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, ACCESSORY_DATA, WEAPON_CATEGORIES, ARMOR_CATEGORIES, SHIELD_CATEGORIES, ACCESSORY_CATEGORIES = get_normalized_equipment_data(RANK_FLOOR_MAP)
WEAPON_TYPES = WEAPON_CATEGORIES # 後方互換性
CONSUMABLE_DATA, STAVE_DATA = get_normalized_item_data(RANK_FLOOR_MAP)

# --- パーセント系ステータスのキー（強化ボーナス計算・UI表示で使用） ---
PCT_STAT_KEYS = frozenset([
    "crit_bonus",
    "block_chance_close",
    "block_chance_ranged",
    "armor_penetration",
])
LANTERN_DATA = {}  # 後方互換性のための空の定義

# --- 装備ステータスの全体レンジ（バー表示用） ---
# 全装備品から各ステータスの min/max を自動算出する
def _compute_stat_ranges():
    """全装備データを走査してステータスごとのmin/maxを算出"""
    stat_keys = [
        "attack_bonus", "defense_bonus", "hp_bonus",
        "crit_rate", "block_chance_close", "block_chance_ranged",
        "armor_penetration", "aggro_mod", "stupidity",
        "accuracy_bonus_close", "regen_bonus",
        "backstab_crit_bonus", "flank_backstab",
        "stupidity_proc_chance", "stupidity_proc_amount",
        "stun_proc_chance", "stun_duration",
        "counter_proc_chance", "counter_damage_ratio",
        "lifesteal_chance", "lifesteal_ratio",
    ]
    # パーセント系のキー（UI表示時に100倍するので、レンジも100倍で格納）
    pct_keys = {
        "crit_rate", "block_chance_close", "block_chance_ranged", "armor_penetration",
        "stupidity_proc_chance", "stun_proc_chance", "counter_proc_chance",
        "lifesteal_chance", "lifesteal_ratio", "counter_damage_ratio",
    }
    all_equips = list(WEAPON_DATA.values()) + list(ARMOR_DATA.values()) + list(SHIELD_DATA.values()) + list(ACCESSORY_DATA.values())
    ranges = {}
    for key in stat_keys:
        values = [e.get("stats", {}).get(key, 0) for e in all_equips if isinstance(e.get("stats"), dict)]
        # stats が dict でない場合もトップレベルから取得
        values += [e.get(key, 0) for e in all_equips if not isinstance(e.get("stats"), dict) and key in e]
        values = [v for v in values if v != 0]
        if key in pct_keys:
            values = [v * 100 for v in values]
        if values:
            ranges[key] = {"min": min(values), "max": max(values)}
        else:
            ranges[key] = {"min": 0, "max": 1}
    return ranges

STAT_RANGES = _compute_stat_ranges()

def get_stat_max(stat_key):
    """指定ステータスの全装備中の最大値を返す（バーのMAX基準）"""
    r = STAT_RANGES.get(stat_key, {"min": 0, "max": 1})
    return r["max"]

# プレイヤーの最終ステータス用レンジ（ステータス画面バー表示用）
# min=基礎値、max=基礎値+全装備中最大ボーナス（複数スロット分加算）
PLAYER_STAT_RANGES = {
    "total_attack": {"min": PLAYER_ATTACK, "max": PLAYER_ATTACK + get_stat_max("attack_bonus")},
    "total_defense": {"min": PLAYER_DEFENSE, "max": PLAYER_DEFENSE + get_stat_max("defense_bonus") * 2},
    "max_hp": {"min": PLAYER_HP, "max": PLAYER_HP + get_stat_max("hp_bonus") * 2},
    "block_close": {"min": 0, "max": get_stat_max("block_chance_close") * 2},
    "block_ranged": {"min": 0, "max": get_stat_max("block_chance_ranged") * 2},
}
# PLAYER_STAT_RANGESもSTAT_RANGESに統合してget_stat_rankで使えるようにする
STAT_RANGES.update(PLAYER_STAT_RANGES)

# ランク判定用の閾値（F〜S の6段階）
STAT_RANK_COLORS = {
    "F": (150, 150, 150),   # 灰
    "E": (255, 255, 255),   # 白
    "D": (100, 220, 100),   # 緑
    "C": (100, 150, 255),   # 青
    "B": (180, 100, 255),   # 紫
    "A": (255, 200, 50),    # 金
    "S": (255, 80, 80),     # 赤
}
STAT_RANK_ORDER = ["F", "E", "D", "C", "B", "A", "S"]

def get_stat_rank(value, stat_key):
    """ステータス値からランク(F〜S)を判定する"""
    r = STAT_RANGES.get(stat_key, {"min": 0, "max": 1})
    if r["max"] == r["min"]:
        return "S" if value >= r["max"] else "F"
    ratio = (value - r["min"]) / (r["max"] - r["min"])
    ratio = max(0.0, min(1.0, ratio))
    # 6段階に分割
    idx = min(int(ratio * len(STAT_RANK_ORDER)), len(STAT_RANK_ORDER) - 1)
    return STAT_RANK_ORDER[idx]

def get_next_rank_threshold(value, stat_key):
    """次のランクに上がるために必要な値を返す。既にSランクならNoneを返す"""
    r = STAT_RANGES.get(stat_key, {"min": 0, "max": 1})
    if r["max"] == r["min"]:
        return None
    ratio = (value - r["min"]) / (r["max"] - r["min"])
    ratio = max(0.0, min(1.0, ratio))
    current_idx = min(int(ratio * len(STAT_RANK_ORDER)), len(STAT_RANK_ORDER) - 1)
    if current_idx >= len(STAT_RANK_ORDER) - 1:
        return None  # 既にSランク
    # 次のランクの境界ratio
    next_ratio = (current_idx + 1) / len(STAT_RANK_ORDER)
    # ratioを値に戻す
    next_value = r["min"] + next_ratio * (r["max"] - r["min"])
    return next_value

def get_upgrades_to_next_rank(equip_inst, stat_key):
    """強化限界（+10または+10%）までの残り回数を返す。
    既に限界に達している場合は0、強化不可ならNoneを返す。
    """
    import math
    
    # 現在の強化回数とボーナスを取得
    stat_enhance = equip_inst.stats.get(stat_key, 0)
    current_bonus = equip_inst.get_enhance_bonus(stat_key)
    
    # %系か整数系か判定
    is_pct_stat = current_bonus < 0.1 or isinstance(current_bonus, float) and current_bonus < 0.1
    
    # 限界値（固定+10または+10%）
    if is_pct_stat:
        growth_room = 0.10  # +10%
    else:
        growth_room = 10    # +10
    
    # 既に限界に達しているか
    if current_bonus >= growth_room * 0.999:  # 誤差許容
        return 0
    
    # 残りのボーナス必要量
    remaining_bonus = growth_room - current_bonus
    
    # 減衰カーブに基づいて残り回数を計算
    # 1-10回: +0.5, 11-20回: +0.3, 21-30回: +0.2
    remaining_steps = 0
    temp_enhance = stat_enhance
    temp_bonus = remaining_bonus
    
    while temp_bonus > 0.001 and temp_enhance < 30:
        temp_enhance += 1
        if temp_enhance <= 10:
            step_bonus = growth_room * 0.05  # 0.5
        elif temp_enhance <= 20:
            step_bonus = growth_room * 0.03  # 0.3
        else:
            step_bonus = growth_room * 0.02  # 0.2
        temp_bonus -= step_bonus
        remaining_steps += 1
    
    return max(0, remaining_steps)

# --- その他のマスタデータ ---
# Data Source: components/data/master/ (dungeon.json, npcs.json, enemy_attack_effects.json, quests.json)
_dungeon       = load_master_data("dungeon.json")
TRAP_DATA      = _dungeon.get("TRAP_DATA", {})
DUNGEON_IMAGES = _dungeon.get("DUNGEON_IMAGES", {})

NPC_DATA           = load_master_data("npcs.json")
ATTACK_EFFECT_DATA = load_master_data("enemy_attack_effects.json")

_quests          = load_master_data("quests.json")
FIXED_QUEST_DATA = _quests.get("FIXED_QUESTS", [])

# --- アウトブレイク（魔物の氾濫）イベント ---
_outbreak = _balance.get("OUTBREAK_CONFIG", {})
OUTBREAK_MIN_FLOOR   = _outbreak.get("min_floor", 2)
OUTBREAK_MAX_FLOOR   = _outbreak.get("max_floor", 99)
OUTBREAK_CHANCE      = _outbreak.get("occurrence_chance", 0.08)
OUTBREAK_ENEMY_MULT  = _outbreak.get("enemy_multiplier", 3.0)
OUTBREAK_ITEM_MULT   = _outbreak.get("item_multiplier", 3.0)
OUTBREAK_GP_MULT     = _outbreak.get("reward_gp_multiplier", 2.0)
OUTBREAK_FLASH_COLOR = _outbreak.get("flash_color", [255, 0, 0])
BGM_OVERFLOW         = _outbreak.get("bgm", "components/sounds/bgm/beyond_the_suffer.mp3")
SOUND_OUTBREAK_ALERT = "components/sounds/sfx/explosion.wav"

# ==============================================================================
# 🛠️ 4. その他・システム固定データ
# ==============================================================================

# --- テレポート（転移屋）設定 ---
_teleport = _balance.get("TELEPORT_CONFIG", {})
TELEPORT_MONEY_PER_FLOOR = _teleport.get("money_per_floor", 1000)
TELEPORT_REQUIRED_ITEM   = _teleport.get("required_item_id", "teleport_stone")
TELEPORT_RETURN_VILLAGE_COST = _teleport.get("return_village_money", 10000)

# --- 初期装備 ---
PLAYER_WEAPON   = "old_sword"
PLAYER_ARMOR    = "adventurers_clothes"
PLAYER_SHIELD   = None
SOUND_PURCHASE  = "components/sounds/sfx/buy.wav"
SOUND_PROJECTILE_HIT = "components/sounds/sfx/get_damage.wav"
SOUND_ATTACK_HIT = "components/sounds/sfx/damage.wav"
SOUND_ATTACK_MISS = "components/sounds/sfx/attack_miss.wav" 

# --- サービス料金 ---
# Data Source: balance.yml (VILLAGE_SERVICES)
_svc = _balance.get("VILLAGE_SERVICES", {})
INN_FEE           = _svc.get("INN_FEE", 100)
DOCTOR_FEE        = _svc.get("DOCTOR_FEE", 50)
WAREHOUSE_FEE     = _svc.get("WAREHOUSE_FEE", 10)

# --- アイテムアイコン ---
COMMON_ITEM_IMAGES = {
    "weapon": "components/pictures/icon/weapon.png",
    "shield": "components/pictures/icon/shield.png",
    "armor":  "components/pictures/icon/armor.png",
    "stave":  "components/pictures/icon/stave.png",
    "consumable": "components/pictures/icon/item.png",
}

# --- 武器描画設定 ---
# WEAPON_TYPES は JSON から読み込まれます。

# --- 杖の描画 ---
STAVE_IMAGE_PATH = "components/pictures/items/stave.png"
STAVE_GLOW_COLOR = (255, 255, 100)

# --- 色設定（素材がない場合の予備） ---
ARMOR_COLORS = {
    "leather_armor": (120, 70, 30),
    "chain_mail": (140, 145, 155),
    "plate_armor": (90, 115, 175),
}
SHIELD_COLORS = {
    "wooden_shield": (139, 90, 43),
    "iron_shield": (150, 160, 175),
    "tower_shield": (80, 100, 180),
}

SOUND_OVERFLOW = "components/sounds/sfx/explosion.wav"
# --- タイルID定義 ---
TILE_WALL    = 0
TILE_FLOOR   = 1
TILE_STAIRS_UP = 2
TILE_STAIRS_DOWN = 3
TILE_CORRIDOR = 4
TILE_GATE    = 9  # すり抜け可能な頭上レイヤータイル
