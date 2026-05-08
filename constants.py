"""
constants.py — ゲーム全体で使うキー設定やパラメータを一箇所にまとめた定数ファイル
このファイルはシステム設定に特化し、ゲームバランスやデータは JSON から読み込むように整理されました。
"""
import pygame
from wordings import Text
from systems.data_loader import (
    load_master_data, SAVE_DATA_PATH, MASTER_DATA_DIR,
    generate_rank_floor_map, get_normalized_enemy_data,
    get_normalized_equipment_data, get_normalized_item_data
)

# ==============================================================================
# 🎮 1. システム・操作設定 (System & Input)
# ==============================================================================

GAME_TITLE = "Rogue-like Expedition"
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 900
TILE_SIZE = 64

# --- BGM設定 ---
BGM_TITLE   = "components/sounds/bgm/winding_adventure.mp3"
BGM_OPENING = "components/sounds/bgm/winding_adventure.mp3"
BGM_VILLAGE  = "components/sounds/bgm/village_theme.mp3"
BGM_DEFEAT   = "components/sounds/bgm/gameover.mp3"
BGM_OVERFLOW = "components/sounds/bgm/beyond_the_suffer.mp3"
SOUND_QUEST_COMPLETE = "components/sounds/sfx/quest_complete.wav"
SOUND_RANK_UP        = "components/sounds/sfx/quest_complete.wav"  # ランクアップ時の効果音
SOUND_INN_REST       = "components/sounds/sfx/recharge.wav"        # 宿屋宿泊時の効果音
SOUND_CURSOR_MOVE    = "components/sounds/sfx/cursor.wav"          # カーソル移動音
SOUND_SELECT         = "components/sounds/sfx/select_new.wav"      # 決定音
SOUND_CANCEL         = "components/sounds/sfx/cancel_new.wav"      # キャンセル音
SOUND_STAIRS_UP      = "components/sounds/sfx/stairs.wav"          # 階段移動音
SOUND_STAIRS_DOWN    = "components/sounds/sfx/stairs.wav"          # 階段移動音
SOUND_HAMMER         = "components/sounds/sfx/attack_1.wav"       # 鍛冶屋の叩く音
SOUND_BLACKSMITH_FINISH = "components/sounds/sfx/buy.wav"        # 鍛冶完了音


# --- 操作キー設定 ---
KEY_MOVE_UP    = pygame.K_UP
KEY_MOVE_DOWN  = pygame.K_DOWN
KEY_MOVE_LEFT  = pygame.K_LEFT
KEY_MOVE_RIGHT = pygame.K_RIGHT

KEY_ATTACK     = pygame.K_SPACE
KEY_TURN_ONLY  = pygame.K_s

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
PLAYER_COIN         = _p.get("initial_coin", 100)
PLAYER_ORE          = _p.get("initial_ore", 0)
MAX_ITEM_SLOTS      = _p.get("max_item_slots", 20)
MAX_EQUIP_SLOTS     = _p.get("max_equip_slots", 10)
MAX_STAVE_SLOTS     = _p.get("max_stave_slots", 10)
PLAYER_ACCURACY_CLOSE = _p.get("accuracy_close", 100)
PLAYER_ACCURACY_RANGED = _p.get("accuracy_ranged", 100)
PLAYER_EVASION      = _p.get("evasion", 1)

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

# ------------------------------------------------------------------------------
# ⚔️ COMBAT (戦闘システム・演出)
# ------------------------------------------------------------------------------
# Data Source: balance.yml (COMBAT)
_cb = _balance.get("COMBAT", {})
CRITICAL_RATE_MAX           = _cb.get("CRITICAL_RATE_MAX", 0.7)
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

# ------------------------------------------------------------------------------

# ==============================================================================
# 👹 3. マスターデータ (Master Data - Loaded from JSON)
# ==============================================================================

# --- ギルドランク & 階層マップ ---
# Data Source: components/data/master/guild.json
_guild = load_master_data("guild.json")
GUILD_RANKS = _guild.get("GUILD_RANKS", [])
RANK_ORDER  = _guild.get("RANK_ORDER", [])
RANK_FLOOR_MAP = generate_rank_floor_map(GUILD_RANKS)

# --- 各種データの正規化読み込み ---
# Data Source: components/data/master/ (enemies.json, obstacles.yml, equipment.json, items.json)
ENEMY_DATA = get_normalized_enemy_data(RANK_FLOOR_MAP)
WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, WEAPON_TYPES = get_normalized_equipment_data(RANK_FLOOR_MAP)
CONSUMABLE_DATA, STAVE_DATA, LANTERN_DATA = get_normalized_item_data(RANK_FLOOR_MAP)

# --- その他のマスタデータ ---
# Data Source: components/data/master/ (dungeon.json, npcs.json, enemy_attack_effects.json, quests.json)
_dungeon       = load_master_data("dungeon.json")
TRAP_DATA      = _dungeon.get("TRAP_DATA", {})
DUNGEON_IMAGES = _dungeon.get("DUNGEON_IMAGES", {})

NPC_DATA           = load_master_data("npcs.json")
ATTACK_EFFECT_DATA = load_master_data("enemy_attack_effects.json")

_quests          = load_master_data("quests.json")
FIXED_QUEST_DATA = _quests.get("FIXED_QUESTS", [])

# --- 氾濫イベント（ランク連動） ---
# 移動済み（上部へ）
OVERFLOW_CHANCE = 0.1
# Bランクの開始階
OVERFLOW_MIN_FLOOR = RANK_FLOOR_MAP.get("B", {"min": 21})["min"]
# Bランクの次(Aランク)の開始階
OVERFLOW_CENTER_SWITCH_MIN_FLOOR = RANK_FLOOR_MAP.get("A", {"min": 26})["min"]
SOUND_OVERFLOW = "components/sounds/sfx/explosion.wav"

# ==============================================================================
# 🛠️ 4. その他・システム固定データ
# ==============================================================================

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
