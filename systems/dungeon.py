import pygame
import random
import os
import math
from constants import *
from components.sprites.npc import NPC
from components.sprites.enemy import Enemy
from components.sprites.item import DroppedWeapon, DroppedConsumable, DroppedArmor, DroppedShield, DroppedStave, DroppedAccessory
from systems.ui import Dialog, ConfirmDialog, InventoryDialog, StatusBar, StatusDialog, EnhanceDialog, ItemActionDialog, OreSelectionDialog, ShopDialog, StaveSelectionDialog, GuildDialog, WarehouseDialog
from systems.guild import GuildSystem
# from systems.dungeon_settings import dungeon_settings
from systems.game_state import is_paused
from wordings import Text


def warp_to_floor(floor_level, player, is_death=False, debug_overflow=False, spawn_reason="normal", old_dungeon=None):
    """指定した階層へ移動するための新しいダンジョンオブジェクトを生成する"""
    # --- [MEMORY OPTIMIZATION] 階層移動時にキャッシュをクリーンアップ ---
    import gc
    from components.sprites.enemy import Enemy
    from components.sprites.player import Player
    from components.sprites.npc import NPC
    from systems.sound_handler import sound_manager
    from constants import SOUND_STAIRS_UP, SOUND_STAIRS_DOWN
    
    # Dungeonのキャッシュは消去せず、一度読み込んだテーマの画像を全階層で使い回す（爆速化）
    Enemy.clear_cache()
    Player.clear_cache()
    NPC.clear_cache()
    if old_dungeon:
        old_dungeon.cleanup_instance()
    gc.collect() # 未使用メモリを強制解放
    
    # 階層移動音の再生
    if hasattr(player, "current_floor"):
        if floor_level > player.current_floor:
            sound_manager.play_sfx(SOUND_STAIRS_DOWN)
        elif floor_level < player.current_floor:
            sound_manager.play_sfx(SOUND_STAIRS_UP)
            
    # 読み込み中画面を表示 (重い処理の前に強制描画)
    screen = pygame.display.get_surface()
    if screen:
        from systems.ui import show_loading_screen
        show_loading_screen(screen)
            
    is_first_visit = floor_level > getattr(player, "max_reached_floor", 0)
    player.set_current_floor(floor_level)
    new_dungeon = Dungeon(level=floor_level, player=player, debug_overflow=debug_overflow)
    
    # エリア到達メッセージ（下り方向のみ表示）
    area_msg = new_dungeon.floor_info.get("area_message")
    is_descending = floor_level > getattr(player, "prev_floor", -1)
    if area_msg and is_descending:
        from systems.game_state import game_state
        game_state["pending_area_message"] = area_msg
    
    # 専用メソッドでスポーン位置を決定
    new_dungeon.set_spawn_position(player, spawn_reason, is_death)
    
    old_floor = getattr(player, "prev_floor", -1)
    player.prev_floor = floor_level
    player.reset_status()
    player.boss_message_shown = False # 階層移動時に表示済みフラグをリセット
    player._shown_boss_messages = set() # ボスごとの遭遇メッセージ表示済みセットをリセット
    
    # ボス戦状態をリセット（次の階でBGMが正しく再生されるように）
    from systems.game_state import game_state
    game_state["is_boss_battle"] = False
    game_state["boss_battle_persistent"] = False
    
    # 敵・アイテムを初期配置（村や固定マップ階層以外）
    if floor_level > 0 and not new_dungeon.floor_info.get("map"):
        new_dungeon.enemies = Enemy.spawn_enemies(new_dungeon, player, is_outbreak=new_dungeon.is_outbreak)
        new_dungeon.spawn_floor_items(player)
        new_dungeon.spawn_traps(player)
        
    new_dungeon.turns_since_last_respawn = 0
    # 階層に応じたBGMを再生
    new_dungeon.play_floor_bgm()
    
    # --- [AUTO-SAVE] 階層移動時に自動セーブ ---
    # 「続きから(continue)」や「死亡時(is_death)」はセーブ不要
    if floor_level != old_floor and spawn_reason != "continue" and not is_death:
        from systems.data_loader import SAVE_DATA_PATH
        print(f"[AUTO-SAVE] Floor transition ({old_floor} -> {floor_level}). Saving to persistent file: {SAVE_DATA_PATH}")
        player.save_to_file()

    return new_dungeon

def warp_with_pitfall(floor_level, player, spawn_reason="teleport"):
    """落とし穴の演出付きで指定階層へ移動予約を行う (共通化用)"""
    from systems.game_state import game_state
    from systems.sound_handler import sound_manager
    
    # 1. プレイヤーを落下状態にする
    player.is_falling = True
    player.falling_timer = 40 # 約0.7秒 (通常の階段より少し溜めを作る)
    
    # 2. 落下SE再生
    # 既存の stairs SE とは別に、落とし穴感のある音があれば再生
    sound_manager.play_sfx("components/sounds/sfx/fall.wav") 
    
    # 3. game_state に移動先を予約
    game_state["pending_warp"] = {
        "floor": floor_level,
        "spawn_reason": spawn_reason
    }
    print(f"[WARP] Pitfall animation started. Target floor: {floor_level}")

class Dungeon:
    # --- [NEW] クラスレベルのキャッシュ ---
    _texture_cache = {} # {theme_folder: {key: surface}}
    _variant_lists = {} # {theme_folder: {category: [keys]}}

    @classmethod
    def preload_all_themes(cls, screen=None):
        """起動時に全テーマ画像をキャッシュに一括ロードする。
        以降の階層移動では常にキャッシュヒットするため、プレイ中のロードが消える。
        """
        from constants import DUNGEON_IMAGES, TILE_SIZE
        main_path = DUNGEON_IMAGES.get("path", "components/pictures/dungeon")
        folders = set()
        for k, v in DUNGEON_IMAGES.items():
            if k in ("path",): continue
            if isinstance(v, dict):
                img = v.get("image")
                if img: folders.add(img)
            elif isinstance(v, str):
                folders.add(v)

        loaded = 0
        total = len(folders)
        for folder in sorted(folders):
            if folder in cls._texture_cache:
                continue
            img_dir = f"{main_path}/{folder}"
            if not os.path.exists(img_dir):
                continue

            if screen:
                from systems.ui import show_loading_screen
                show_loading_screen(screen, f"Now Loading... ({loaded+1}/{total})")
                pygame.display.flip()

            textures = {}
            available_floor_variants = []
            available_wall_variants = []
            available_wall_top_variants = []
            available_wall_none_variants = []
            available_wall_decoration_variants = []
            overhead_base_map = {}
            short_to_full_key = {}

            def load_and_scale(path):
                img = pygame.image.load(path).convert_alpha()
                if img.get_size() != (TILE_SIZE, TILE_SIZE):
                    return pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
                return img

            keys_to_load = ["floor", "wall_top", "wall_bottom", "wall_side", "wall_none",
                            "wall_corner", "corridor", "wall_single", "wall_base", "wall_pass"]
            for key in keys_to_load:
                p = f"{img_dir}/{key}.png"
                if os.path.exists(p):
                    textures[key] = load_and_scale(p)

            for f in os.listdir(img_dir):
                if not f.endswith(".png"): continue
                key = f[:-4]
                path = f"{img_dir}/{f}"
                if f.startswith("floor"):
                    textures[key] = load_and_scale(path)
                    available_floor_variants.append(key)
                elif f.startswith("wall_single"):
                    textures[key] = load_and_scale(path)
                    available_wall_variants.append(key)
                elif f.startswith("wall_top"):
                    textures[key] = load_and_scale(path)
                    available_wall_top_variants.append(key)
                elif f.startswith("wall_none"):
                    textures[key] = load_and_scale(path)
                    available_wall_none_variants.append(key)
                elif f.startswith("corridor"):
                    textures[key] = load_and_scale(path)
                elif f.startswith("wall_decoration"):
                    textures[key] = load_and_scale(path)
                    available_wall_decoration_variants.append(key)
                elif f.startswith("wall_pass"):
                    textures[key] = load_and_scale(path)
                    available_wall_top_variants.append(key)

            for base_key, variant_list in [("floor", available_floor_variants),
                                           ("wall_top", available_wall_top_variants),
                                           ("wall_none", available_wall_none_variants)]:
                has_real = os.path.exists(f"{img_dir}/{base_key}.png")
                if not has_real and variant_list:
                    textures[base_key] = textures[variant_list[0]]
                    if base_key not in variant_list: variant_list.append(base_key)
                elif has_real and base_key not in variant_list:
                    variant_list.append(base_key)

            stairs_dir = f"{main_path}/stairs"
            for key in ["stairs_up", "stairs_down"]:
                p = f"{stairs_dir}/{key}.png"
                if os.path.exists(p):
                    textures[key] = load_and_scale(p)

            if "corridor" in textures:
                textures["corridor_h"] = pygame.transform.rotate(textures["corridor"], -90)

            for k in textures.keys():
                if "-" in k:
                    parts = k.split("-")
                    if len(parts) >= 2:
                        short = parts[0]
                        overhead_base_map[short] = parts[1]
                        short_to_full_key[short] = k
                else:
                    short_to_full_key[k] = k

            cls._texture_cache[folder] = textures
            cls._variant_lists[folder] = {
                "floor": available_floor_variants,
                "wall": available_wall_variants,
                "wall_top": available_wall_top_variants,
                "wall_none": available_wall_none_variants,
                "wall_decoration": available_wall_decoration_variants,
            }
            cls._overhead_base_map_cache = getattr(cls, "_overhead_base_map_cache", {})
            cls._overhead_base_map_cache[folder] = overhead_base_map
            cls._short_to_full_key_cache = getattr(cls, "_short_to_full_key_cache", {})
            cls._short_to_full_key_cache[folder] = short_to_full_key

            loaded += 1
            print(f"[PRELOAD] Theme '{folder}' cached. ({loaded}/{total})")

        print(f"[PRELOAD] All themes preloaded. ({loaded} themes)")

    @classmethod
    def clear_cache(cls):
        """蓄積されたダンジョンテクスチャのキャッシュを解放する"""
        count = len(cls._texture_cache)
        cls._texture_cache = {}
        cls._variant_lists = {}
        if count > 0:
            print(f"[MEMORY] Dungeon texture cache cleared ({count} themes)")

    def cleanup_instance(self):
        """インスタンスに紐付く巨大なデータ配列の参照を明示的に断ち切り、GCを促進する"""
        self.map_data = None
        self.rooms = []
        self.room_info = []
        self.room_rects = []
        self.enemies = []
        self.npcs = []
        self.dropped_items = []
        self.traps = []
        self.magic_effects = []
        self.weapon_shop_stock = []
        self.item_shop_stock = []
        self.magic_shop_stock = []
        self.dedicated_weapon_shop_stock = []
        self.dedicated_armor_shop_stock = []
        self.dedicated_accessory_shop_stock = []
        if self.player:
            self.player = None

    def __init__(self, level=1, player=None, debug_overflow=False):
        from constants import (
            DUNGEON_MIN_ROOMS, DUNGEON_MAX_ROOMS, DUNGEON_ROOM_INCREASE_INTERVAL,
            DUNGEON_ROOM_MAX_CAP, DUNGEON_ROOM_MIN_CAP, DUNGEON_ROOM_GROWTH_LIMIT_FLOOR,
            DUNGEON_MIN_ROOM_SIZE, DUNGEON_MAX_ROOM_SIZE, DUNGEON_ROOM_SIZE_GROWTH,
            DUNGEON_ROOM_MIN_SIZE_CAP, DUNGEON_ROOM_MAX_SIZE_CAP,
            TILE_SIZE, DUNGEON_IMAGES
        )
        self.current_floor = level
        self.player = player
        self.debug_overflow = debug_overflow
        self.turns_since_last_respawn = 0
        self.tile_size = TILE_SIZE
        
        # --- 部屋数の決定 (指数成長ロジック) ---
        # 成長の上限階層を取得
        limit_floor = DUNGEON_ROOM_GROWTH_LIMIT_FLOOR
        interval = DUNGEON_ROOM_INCREASE_INTERVAL
        
        # 上限階層で成長をストップさせつつ、段階的な増加(3階ごと等)を適用
        capped_level = min(limit_floor, level)
        effective_level = ((capped_level - 1) // interval) * interval + 1
        
        # 進捗率を計算 (0.0 〜 1.0)
        progress = (effective_level - 1) / (limit_floor - 1) if limit_floor > 1 else 1.0
        
        # 指数関数的な成長: start * (end/start)^progress
        def calc_exponential_growth(start, end, p):
            if start <= 0 or end <= 0: return start
            return start * ((end / start) ** p)

        self.min_rooms = int(calc_exponential_growth(DUNGEON_MIN_ROOMS, DUNGEON_ROOM_MIN_CAP, progress))
        self.max_rooms = int(calc_exponential_growth(DUNGEON_MAX_ROOMS, DUNGEON_ROOM_MAX_CAP, progress))
        
        # 下限/上限の最終ガード
        self.min_rooms = max(DUNGEON_MIN_ROOMS, min(DUNGEON_ROOM_MIN_CAP, self.min_rooms))
        self.max_rooms = max(DUNGEON_MAX_ROOMS, min(DUNGEON_ROOM_MAX_CAP, self.max_rooms))
        
        room_growth = 1.0 + (effective_level - 1) * DUNGEON_ROOM_SIZE_GROWTH # 部屋サイズは緩やかに大きくする
        self.min_room_size = min(DUNGEON_ROOM_MIN_SIZE_CAP, int(DUNGEON_MIN_ROOM_SIZE * room_growth))
        self.max_room_size = min(DUNGEON_ROOM_MAX_SIZE_CAP, int(DUNGEON_MAX_ROOM_SIZE * room_growth))
        
        from constants import DUNGEON_MIN_ROOM_DISTANCE, DUNGEON_ROOM_DISTANCE_GROWTH
        
        # 階層に応じた「部屋間の必要距離」を計算（生成ロジックと合わせる）
        required_dist = int(DUNGEON_MIN_ROOM_DISTANCE + (level - 1) * DUNGEON_ROOM_DISTANCE_GROWTH)
        
        avg_room_size = (self.min_room_size + self.max_room_size) / 2.0
        
        # 修正: 余裕を持って「最大部屋数」が入る広さを確保する
        effective_room_side = avg_room_size + required_dist
        target_total_area = (effective_room_side ** 2) * self.max_rooms * 2.0
        
        calculated_side = int(math.sqrt(target_total_area))
        
        # 最小サイズ(30x30)を保証しつつ、動的に決定
        self.map_width = max(30, calculated_side)
        self.map_height = max(30, calculated_side)

        # --- 各種データコンテナの初期化 (他のメソッドから参照されるため、ロジック実行前に初期化) ---
        self.rooms = []
        self.room_info = []
        self.room_rects = []
        self.enemies = []
        self.npcs = []
        self.dropped_items = []
        self.traps = []
        self.magic_effects = []
        self.spawn_counts = {}
        self.spawn_pos = (0, 0)
        self.start_pos = (0, 0)
        self.inn_pos = (0, 0)
        self.dungeon_pos = (0, 0)
        self.clinic_pos = None
        
        self.guild_system = GuildSystem()
        
        self.weapon_shop_stock = []
        self.item_shop_stock = []
        self.magic_shop_stock = []
        self.dedicated_weapon_shop_stock = []
        self.dedicated_armor_shop_stock = []
        self.dedicated_accessory_shop_stock = []
        
        self.shake_amount = 0
        self.shake_timer = 0
        self.shake_offset = (0, 0)
        self.flash_timer = 0
        

        # [DEBUG] 5Fはテスト用フラグがあれば部屋数を3つに固定し、氾濫を発生しやすくする
        if self.debug_overflow and level == 5:
            self.min_rooms = 3
            self.max_rooms = 3

        # --- 探索システム (ミニマップ用) ---
        self.show_map = True
        
        
        self.textures = self._create_placeholder_textures()
        
        current_level = self.get_current_floor_level()
        main_path = DUNGEON_IMAGES.get("path", "components/pictures/dungeon")
        info = DUNGEON_IMAGES.get(str(current_level))
        
        if info is None and current_level > 0:
            valid_keys = [k for k in DUNGEON_IMAGES.keys() if k.isdigit() and k != "0"]
            if valid_keys:
                chosen_info = DUNGEON_IMAGES.get(random.choice(valid_keys))
                if isinstance(chosen_info, dict):
                    info = chosen_info.copy()
                    info["map"] = None
                else:
                    info = chosen_info
        
        if info is None:
            info = {"image": "normal"}
            
        self.floor_info = info
        folder = info["image"] if isinstance(info, dict) else info
        is_fixed_map = isinstance(info, dict) and info.get("map") is not None
        
        # --- アウトブレイク（魔物の氾濫）イベント ---
        self.is_outbreak = False
        self.outbreak_intro_done = False
        self.outbreak_cleared = False
        self.outbreak_clear_rewarded = False
        self.outbreak_monster_initial_count = 0
        self.entry_stairs = None
        
        # 発生判定（設定された階層範囲内、かつ村や固定マップ階層以外）
        if current_level > 0 and not is_fixed_map:
            from constants import OUTBREAK_CHANCE, OUTBREAK_MIN_FLOOR, OUTBREAK_MAX_FLOOR
            in_range = OUTBREAK_MIN_FLOOR <= current_level <= OUTBREAK_MAX_FLOOR
            if (in_range and random.random() < OUTBREAK_CHANCE) or self.debug_overflow:
                self.is_outbreak = True
        
        # --- 設定値のバリデーション ---
        if isinstance(info, dict):
            brightness = info.get("brightness")
            if brightness is not None and not isinstance(brightness, int):
                print(f"[\033[93mWARNING\033[0m] Invalid 'brightness' in floor {current_level}: {brightness} (Expected int)")
            
            ratio = info.get("wall_decoration_ratio")
            if ratio is not None and not isinstance(ratio, (int, float)):
                print(f"[\033[93mWARNING\033[0m] Invalid 'wall_decoration_ratio' in floor {current_level}: {ratio} (Expected number)")

        print(f"Floor {current_level} theme: {folder}")
        def load_and_scale(path):
            img = pygame.image.load(path).convert_alpha()
            if img.get_size() != (self.tile_size, self.tile_size):
                return pygame.transform.scale(img, (self.tile_size, self.tile_size))
            return img

        # --- [NEW] キャッシュチェック ---
        if folder in Dungeon._texture_cache:
            self.textures = Dungeon._texture_cache[folder].copy()
            v_data = Dungeon._variant_lists[folder]
            self.available_floor_variants = v_data["floor"].copy()
            self.available_wall_variants = v_data["wall"].copy()
            self.available_wall_top_variants = v_data["wall_top"].copy()
            self.available_wall_none_variants = v_data["wall_none"].copy()
            self.available_wall_decoration_variants = v_data["wall_decoration"].copy()
            print(f"[DUNGEON] Theme '{folder}' loaded from cache.")
        else:
            img_dir = main_path + "/" + folder
            keys_to_load = ["floor", "wall_top", "wall_bottom", "wall_side", "wall_none", 
                            "wall_corner", "corridor", "wall_single", "wall_base", "wall_pass"]

            for key in keys_to_load:
                p = f"{img_dir}/{key}.png"
                if os.path.exists(p):
                    self.textures[key] = load_and_scale(p)
            
            self.available_floor_variants = []
            self.available_wall_variants = []
            self.available_wall_top_variants = []
            self.available_wall_none_variants = []
            self.available_wall_decoration_variants = []
            if os.path.exists(img_dir):
                for f in os.listdir(img_dir):
                    if f.endswith(".png"):
                        key = f[:-4]
                        path = f"{img_dir}/{f}"
                        if f.startswith("floor"):
                            self.textures[key] = load_and_scale(path)
                            self.available_floor_variants.append(key)
                        elif f.startswith("wall_single"):
                            self.textures[key] = load_and_scale(path)
                            self.available_wall_variants.append(key)
                        elif f.startswith("wall_top"):
                            self.textures[key] = load_and_scale(path)
                            self.available_wall_top_variants.append(key)
                        elif f.startswith("wall_none"):
                            self.textures[key] = load_and_scale(path)
                            self.available_wall_none_variants.append(key)
                        elif f.startswith("corridor"):
                            self.textures[key] = load_and_scale(path)
                        elif f.startswith("wall_decoration"):
                            self.textures[key] = load_and_scale(path)
                            self.available_wall_decoration_variants.append(key)
                        elif f.startswith("wall_pass"):
                            self.textures[key] = load_and_scale(path)
                            # wall_top_variants に含めることでゲートとして選ばれるようにする
                            self.available_wall_top_variants.append(key)

            # バリデーションとベースキーの補完
            for base_key, variant_list in [("floor", self.available_floor_variants), 
                                           ("wall_top", self.available_wall_top_variants),
                                           ("wall_none", self.available_wall_none_variants)]:
                has_real = os.path.exists(f"{img_dir}/{base_key}.png")
                if not has_real and variant_list:
                    self.textures[base_key] = self.textures[variant_list[0]]
                    if base_key not in variant_list: variant_list.append(base_key)
                elif has_real and base_key not in variant_list:
                    variant_list.append(base_key)

            # 階段の読み込みもキャッシュに含める
            stairs_dir = main_path + "/stairs"
            for key in ["stairs_up", "stairs_down"]:
                if os.path.exists(f"{stairs_dir}/{key}.png"):
                    self.textures[key] = load_and_scale(f"{stairs_dir}/{key}.png")

            # キャッシュに保存
            Dungeon._texture_cache[folder] = self.textures.copy()
            Dungeon._variant_lists[folder] = {
                "floor": self.available_floor_variants.copy(),
                "wall": self.available_wall_variants.copy(),
                "wall_top": self.available_wall_top_variants.copy(),
                "wall_none": self.available_wall_none_variants.copy(),
                "wall_decoration": self.available_wall_decoration_variants.copy()
            }
            
            # --- [NEW] 命名規則による地面指定の解析 (wall_pass-floor_0.png 等) ---
            self.overhead_base_map = {}
            self.short_to_full_key = {} # 短縮名からフルキーへのマッピング
            for k in self.textures.keys():
                if "-" in k:
                    parts = k.split("-")
                    if len(parts) >= 2:
                        # 例: "wall_pass_0-floor_1" -> {"wall_pass_0": "floor_1"}
                        short = parts[0]
                        self.overhead_base_map[short] = parts[1]
                        self.short_to_full_key[short] = k
                else:
                    self.short_to_full_key[k] = k # 通常のキーはそのまま
            
            Dungeon._overhead_base_map_cache = getattr(Dungeon, "_overhead_base_map_cache", {})
            Dungeon._overhead_base_map_cache[folder] = self.overhead_base_map.copy()
            Dungeon._short_to_full_key_cache = getattr(Dungeon, "_short_to_full_key_cache", {})
            Dungeon._short_to_full_key_cache[folder] = self.short_to_full_key.copy()
            
            print(f"[DUNGEON] Theme '{folder}' cached.")
        
        # キャッシュからの復元時にも map を取得
        if folder in Dungeon._texture_cache and not hasattr(self, "overhead_base_map"):
            self.overhead_base_map = Dungeon._overhead_base_map_cache.get(folder, {}).copy()
            self.short_to_full_key = Dungeon._short_to_full_key_cache.get(folder, {}).copy()

        self.map_data = [[0 for _ in range(self.map_width)] for _ in range(self.map_height)]
        
        import re
        def build_weight_list(variants, uniform=False):
            if not variants: return []
            if uniform:
                return [1.0] * len(variants)
            weights = []
            for v in variants:
                m = re.search(r'(\d+)$', v)
                weights.append(0.5 ** int(m.group(1)) if m else 1.0)
            return weights

        self._floor_weights = build_weight_list(self.available_floor_variants, uniform=True)
        self._wall_weights = build_weight_list(self.available_wall_variants)
        self._top_weights = build_weight_list(self.available_wall_top_variants)
        self._none_weights = build_weight_list(self.available_wall_none_variants)
        # 決定論的なバリアント選択用シード（フロアごとに固定）
        self._variant_seed = random.randint(0, 0xFFFF)

        # wall_variants: 障害物として配置されたマスのみ保持するdict {(x,y): variant_key}
        self.wall_variants = {}
        self.wall_decoration_variants = [["" for _ in range(self.map_width)] for _ in range(self.map_height)]
        self.wall_decoration_flips = [[False for _ in range(self.map_width)] for _ in range(self.map_height)]
        
        if "corridor" in self.textures:
            self.textures["corridor_h"] = pygame.transform.rotate(self.textures["corridor"], -90)
            
        if "wall_single" not in self.textures and "wall_side" in self.textures:
            surface = pygame.Surface((self.tile_size, self.tile_size), pygame.SRCALPHA)
            side = self.textures["wall_side"]
            side_flip = pygame.transform.flip(side, True, False)
            surface.blit(side, (0, 0), (0, 0, self.tile_size//2, self.tile_size))
            surface.blit(side_flip, (self.tile_size//2, 0), (self.tile_size//2, 0, self.tile_size//2, self.tile_size))
            self.textures["wall_single"] = surface
        
        # stairs_dir 処理は上に移動済み
            
        # [NEW] 固定マップの読み込み判定
        map_file = self.floor_info.get("map")
        if map_file:
            self.generate_fixed_map(map_file)
        else:
            self.generate_dungeon()
            self._clean_map_single_pass()
        
        # 壁の装飾を配置 (ランダムダンジョンのみ)
        if not map_file:
            self._add_wall_decorations()
        
        self._add_floor_edges()
        
        self.next_dungeon = None
        self.brightness = self.floor_info.get("brightness", 1)
        self.darkness_type = self.floor_info.get("darkness_type", "dark")
        self.is_lighted = (self.current_floor == 0 or self.brightness == 5)

        # --- 探索システム (ミニマップ用) ---
        # 最終的な map_width, map_height を使用して初期化
        self.revealed_tiles = [[False for _ in range(self.map_width)] for _ in range(self.map_height)]
        
        # プレイヤーの初期位置（または階段の出現位置）を探索済みにする
        if self.player:
            self.reveal_area(int(self.player.x // TILE_SIZE), int(self.player.y // TILE_SIZE))
        elif hasattr(self, "start_pos"):
            self.reveal_area(self.start_pos[0], self.start_pos[1])

    def set_spawn_position(self, player, spawn_reason, is_death=False):
        """プレイヤーのスポーン位置を状況（New Game, Continue, Return）に応じて設定する"""
        ts = self.tile_size
        
        if self.current_floor == 0: # 村
            # デフォルトは開始地点(P)。CONFIG指定があればそちらを優先
            tx, ty = getattr(self, "fixed_spawn_pos", None) or self.start_pos
            
            # 死亡時は診療所(R)の右隣にスポーン
            if is_death and self.clinic_pos:
                tx, ty = self.clinic_pos[0] + 1, self.clinic_pos[1]
            # 宿屋(H)（後方互換/フォールバック用）
            elif is_death and self.inn_pos != (0, 0):
                tx, ty = self.inn_pos[0] + 1, self.inn_pos[1]
                
            # ダンジョンからの帰還
            elif spawn_reason == "return" and self.dungeon_pos != (0, 0):
                # ダンジョン入口(D)の右隣にスポーン
                tx, ty = self.dungeon_pos[0] + 1, self.dungeon_pos[1]
            
            # 座標を適用 (再開時でも死亡時は強制的に座標を設定する)
            if spawn_reason != "continue" or is_death:
                player.x = tx * ts
                player.y = ty * ts
            self.spawn_pos = (int(player.x // ts), int(player.y // ts))
            
        else: # ダンジョン
            # 登り階段(2)か下り階段(3)を探す
            if spawn_reason == "continue":
                target_tile = 2 # 再開時はその階の入口(上り階段)から
            else:
                target_tile = 2 if self.current_floor > getattr(player, "prev_floor", 0) else 3
            found = False
            for y in range(self.map_height):
                for x in range(self.map_width):
                    if self.map_data[y][x] == target_tile:
                        player.x = x * ts
                        player.y = y * ts
                        self.spawn_pos = (x, y)
                        found = True
                        break
                if found: break
            
            # 階段が見つからない場合のフォールバック
            if not found and self.rooms:
                rx, ry = self.rooms[0]
                player.x = rx * ts
                player.y = ry * ts
                self.spawn_pos = (rx, ry)

            self.entry_stairs = target_tile

    def reveal_floor(self):
        self.is_lighted = True
        self.reveal_all_tiles() # マップをすべて探索済みにする
        from systems.magic_handler import FlashEffect
        for trap in self.traps:
            if not trap.is_revealed:
                trap.is_revealed = True
        self.magic_effects.append(FlashEffect(color=(255, 255, 200), duration=20))
    
    def generate_dungeon(self):
        from constants import DUNGEON_MIN_ROOM_DISTANCE, DUNGEON_ROOM_DISTANCE_GROWTH, DUNGEON_CORRIDOR_W2_CHANCE, DUNGEON_STAIRS_FLOOR_RADIUS
        
        # 最小部屋数を確保するためのリトライループ
        for dungeon_attempt in range(10):
            # マップと部屋リストをリセット
            self.map_data = [[0 for _ in range(self.map_width)] for _ in range(self.map_height)]
            self.rooms = []
            self.room_rects = []
            self.valid_floor_coords = set()
            pending_rooms = []
            
            num_rooms = random.randint(self.min_rooms, self.max_rooms)
            required_dist = int(DUNGEON_MIN_ROOM_DISTANCE + (self.current_floor - 1) * DUNGEON_ROOM_DISTANCE_GROWTH)
            
            for _ in range(num_rooms):
                placed = False
                for attempt in range(50):
                    w = random.randint(self.min_room_size, self.max_room_size)
                    h = random.randint(self.min_room_size, self.max_room_size)
                    x = random.randint(1, self.map_width - w - 1)
                    y = random.randint(1, self.map_height - h - 1)
                    
                    conflict = False
                    for (rx, ry, rw, rh) in self.room_rects:
                        if (x < rx + rw + required_dist and x + w + required_dist > rx and
                            y < ry + rh + required_dist and y + h + required_dist > ry):
                            conflict = True
                            break
                            
                    if not conflict:
                        center_x, center_y = x + w // 2, y + h // 2
                        
                        if self.rooms:
                            min_dist = float('inf')
                            closest_center = None
                            for (rx, ry) in self.rooms:
                                dist = abs(rx - center_x) + abs(ry - center_y)
                                if dist < min_dist:
                                    min_dist = dist
                                    closest_center = (rx, ry)
                            prev_cx, prev_cy = closest_center
                            
                            # 氾濫判定は最後に行うので、ここでは通常の通路生成
                            c_width = 2 if random.random() < DUNGEON_CORRIDOR_W2_CHANCE else 1
                            self.create_corridor(prev_cx, center_x, prev_cy, prev_cy, width=c_width)
                            self.create_corridor(center_x, center_x, prev_cy, center_y, width=c_width)
                            
                        self.room_rects.append((x, y, w, h))
                        self.rooms.append((center_x, center_y))
                        pending_rooms.append((x, y, w, h))
                        placed = True
                        break
            # 最小部屋数を確保できたかチェック
            if len(self.rooms) >= self.min_rooms:
                if dungeon_attempt > 0:
                    print(f"[DUNGEON] Guaranteed min rooms ({len(self.rooms)}) after {dungeon_attempt} retries.")
                
                # 床タイルの書き込み
                for (x, y, w, h) in pending_rooms:
                    for row in range(y, y + h):
                        for col in range(x, x + w):
                            self.map_data[row][col] = 1
                            self.valid_floor_coords.add((col, row))
                break
        
        start_room_idx = 0
        self.map_data[self.rooms[start_room_idx][1]][self.rooms[start_room_idx][0]] = 2
        
        # 階段の配置: デバッグモードなら同じ部屋、通常なら最も遠い部屋
        if self.debug_overflow:
            target_room_idx = start_room_idx
            # 上り階段の右隣を下り階段にする
            tx, ty = self.rooms[target_room_idx][0] + 1, self.rooms[target_room_idx][1]
            self.map_data[ty][tx] = 3
        else:
            # 階段の配置: スタート部屋以外からランダムに選ぶ（ただし遠いほど確率が高い）
            room_indices = []
            weights = []
            for i in range(len(self.rooms)):
                if i == start_room_idx: continue
                r = self.rooms[i]
                dist = abs(r[0] - self.rooms[start_room_idx][0]) + abs(r[1] - self.rooms[start_room_idx][1])
                room_indices.append(i)
                weights.append(dist ** 2) # 距離の2乗を重みにして遠くを選びやすくする
            
            if room_indices:
                target_room_idx = random.choices(room_indices, weights=weights, k=1)[0]
            else:
                target_room_idx = start_room_idx
            
            self.map_data[self.rooms[target_room_idx][1]][self.rooms[target_room_idx][0]] = 3

        self.start_room_idx = start_room_idx
        self.target_room_idx = target_room_idx


        r_stairs = DUNGEON_STAIRS_FLOOR_RADIUS
        for sx, sy in [self.rooms[start_room_idx], self.rooms[target_room_idx]]:
            for dy in range(-r_stairs, r_stairs + 1):
                for dx in range(-r_stairs, r_stairs + 1):
                    nx, ny = sx + dx, sy + dy
                    if 0 <= nx < self.map_width and 0 <= ny < self.map_height:
                        if nx == sx and ny == sy: continue
                        if self.map_data[ny][nx] == 0:
                            self.map_data[ny][nx] = 1
                            self.valid_floor_coords.add((nx, ny))
        
        # 最後に有効エリア以外を削る
        self._trim_to_valid_areas()
        
    def check_outbreak_start(self, dialog):
        """フロア開始時のアウトブレイク演出"""
        if self.is_outbreak and not self.outbreak_intro_done:
            if dialog:
                from constants import SOUND_OUTBREAK_ALERT, OUTBREAK_FLASH_COLOR
                from systems.sound_handler import sound_manager
                from systems.magic_handler import FlashEffect
                self.magic_effects.append(FlashEffect(color=OUTBREAK_FLASH_COLOR, duration=60))
                from constants import BGM_OVERFLOW
                from systems.audio_manager import play_sfx, play_bgm
                
                play_sfx(SOUND_OUTBREAK_ALERT)
                self.shake_amount = 15
                self.shake_timer = 60
                
                dialog.text = "＜警告＞\n魔物の気配が濃すぎます！\n逃げ場のない『魔物の氾濫』が発生した！"
                dialog.is_active = True
                play_bgm(BGM_OVERFLOW)
                
                self.outbreak_intro_done = True

    def update_outbreak_status(self, player, dialog):
        """アウトブレイクのクリア判定"""
        if not self.is_outbreak or self.outbreak_cleared:
            return
            
        # 生きている敵をカウント
        alive_enemies = [e for e in self.enemies if not getattr(e, "is_dead", False) and not e.is_static]
        
        if len(alive_enemies) == 0:
            self.outbreak_cleared = True
            
            # BGMを元に戻すか、無音にする
            from systems.audio_manager import stop_bgm
            stop_bgm()

    def _resolve_theme_texture_key(self, category, tile_id=0):
        """現在ロードされているテーマのテクスチャから、カテゴリ/IDに対応する有効なキーを返す。
        該当IDのテクスチャが存在しない場合は基本キー、それもなければ最初のバリアントを返す。
        """
        if category == "floor":
            candidates = [f"floor_{tile_id}", "floor"]
            if getattr(self, "available_floor_variants", None):
                candidates.append(self.available_floor_variants[0])
        elif category == "wall_top":
            candidates = [f"wall_top_{tile_id}", "wall_top"]
            if getattr(self, "available_wall_top_variants", None):
                candidates.append(self.available_wall_top_variants[0])
        elif category == "wall_none":
            candidates = [f"wall_none_{tile_id}", "wall_none"]
            if getattr(self, "available_wall_none_variants", None):
                candidates.append(self.available_wall_none_variants[0])
        elif category == "corridor":
            candidates = ["corridor"]
            if getattr(self, "available_floor_variants", None):
                candidates.append(self.available_floor_variants[0])
        elif category == "wall_pass":
            candidates = [f"wall_pass_{tile_id}", "wall_pass"]
            if getattr(self, "available_wall_top_variants", None):
                candidates.append(self.available_wall_top_variants[0])
            elif "wall_top" in self.textures:
                candidates.append("wall_top")
        else:
            return "wall_none"
        for k in candidates:
            if k in self.textures:
                return k
        return candidates[-1] if candidates else "wall_none"

    def generate_fixed_map(self, map_name):
        """テキストファイルから固定マップを生成する（村や休憩ポイント用）"""
        # 読み込みパスの優先順位: 1. components/data/dungeon/  2. ルート
        paths = [f"components/data/dungeon/{map_name}", map_name]
        lines = None
        
        for p in paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        lines = [line.rstrip("\n") for line in f.readlines() if line.strip() and not line.strip().startswith("//") and not line.strip().startswith("#")]
                    if lines: break
                except Exception as e:
                    print(f"[Dungeon] Error reading map file {p}: {e}")

        if lines:
            try:
                self.map_height = len(lines)
                self.map_width = max(len(line) for line in lines)
                self.map_data = [[0 for _ in range(self.map_width)] for _ in range(self.map_height)]
                # 固定マップ用: タイル別のバリアント上書き dict {(x,y): key}
                self._floor_override = {}
                self._wall_top_override = {}
                self._wall_none_override = {}
                self.wall_decoration_variants = [["" for _ in range(self.map_width)] for _ in range(self.map_height)]
                self.wall_decoration_flips = [[False for _ in range(self.map_width)] for _ in range(self.map_height)]
                self.npcs = []
                self.rooms = []
                ts = self.tile_size
                # Load dynamic tile mappings. Base definitions are always from village.yml.
                base_name = os.path.splitext(os.path.basename(map_name))[0]
                from systems.data_loader import load_master_data, MASTER_DATA_DIR
                
                village_data = load_master_data("village.yml") or {}
                base_config = village_data.get("CONFIG", {}) or {}
                base_mappings = village_data.get("TILE_MAPPINGS", {})
                
                # Check for map-specific custom yml config
                custom_file = None
                candidate = f"restpoint/{base_name}.yml"
                if os.path.exists(os.path.join(MASTER_DATA_DIR, candidate)):
                    custom_file = candidate
                elif os.path.exists(os.path.join(MASTER_DATA_DIR, f"{base_name}.yml")):
                    custom_file = f"{base_name}.yml"
                
                # Build tile_mappings_raw by copying base definitions, and mapping positions only if allowed
                tile_mappings_raw = {}
                is_village_map = (base_name == "village")
                
                map_config = base_config
                if custom_file:
                    custom_data = load_master_data(custom_file) or {}
                    map_config = custom_data.get("CONFIG", {}) or base_config
                    custom_mappings = custom_data.get("TILE_MAPPINGS", {})
                    for k, v in base_mappings.items():
                        if isinstance(v, dict):
                            tile_mappings_raw[k] = dict(v)
                            if k in custom_mappings and isinstance(custom_mappings[k], dict):
                                # Apply map-specific positions if defined, else clear them
                                if "positions" in custom_mappings[k]:
                                    tile_mappings_raw[k]["positions"] = custom_mappings[k]["positions"]
                                else:
                                    tile_mappings_raw[k].pop("positions", None)
                            else:
                                tile_mappings_raw[k].pop("positions", None)
                    # Load any additional map-specific custom mappings not present in base
                    for k, v in custom_mappings.items():
                        if isinstance(v, dict) and k not in tile_mappings_raw:
                            tile_mappings_raw[k] = dict(v)
                else:
                    for k, v in base_mappings.items():
                        if isinstance(v, dict):
                            tile_mappings_raw[k] = dict(v)
                            # Clear positions for rest points / custom maps if no custom yml exists
                            if not is_village_map:
                                tile_mappings_raw[k].pop("positions", None)
                
                self.fixed_spawn_pos = None
                cfg_spawn_x = map_config.get("player_start_x")
                cfg_spawn_y = map_config.get("player_start_y")
                if cfg_spawn_x is not None and cfg_spawn_y is not None:
                    try:
                        self.fixed_spawn_pos = (int(cfg_spawn_x), int(cfg_spawn_y))
                    except (TypeError, ValueError):
                        self.fixed_spawn_pos = None

                # 非村の固定マップ（rest point等）では village.yml の具体的な home 画像パスを使わず、
                # その階層のテーマテクスチャを使うため image_path を削除する
                # （wall_decoration 等のカスタム画像は保持）
                if not is_village_map:
                    for v in tile_mappings_raw.values():
                        if isinstance(v, dict) and v.get("category") in (
                            "floor", "wall_top", "wall_none", "corridor", "wall_pass"
                        ):
                            v.pop("image_path", None)
                
                # 地形文字マッピング（village.txtのパース用）
                tile_mappings = {}
                for k, v in tile_mappings_raw.items():
                    if isinstance(v, dict):
                        ch = v.get("char")
                        if ch:
                            tile_mappings[ch] = v

                # --- [NEW] カスタムタイルのテクスチャ動的ロード ---
                for ent_id, tile_info in tile_mappings_raw.items():
                    if isinstance(tile_info, dict):
                        img_path = tile_info.get("image_path")
                        if img_path and os.path.exists(img_path):
                            fk = os.path.splitext(os.path.basename(img_path))[0]
                            if fk not in self.textures:
                                try:
                                    img = pygame.image.load(img_path).convert_alpha()
                                    if img.get_size() != (ts, ts):
                                        img = pygame.transform.scale(img, (ts, ts))
                                    self.textures[fk] = img
                                    print(f"[DEBUG-TEXTURE] Dynamically loaded custom tile texture: {fk} from {img_path}")
                                except Exception as tex_ex:
                                    print(f"[DEBUG-TEXTURE] Failed to load custom tile texture '{img_path}': {tex_ex}")

                for r, line in enumerate(lines):
                    for c, char in enumerate(line):
                        if c >= self.map_width: break
                        # デフォルトは壁(0)
                        self.map_data[r][c] = 0
                        
                        # --- [NEW] 完全動的マッピング・システム ---
                        
                        # 1. ゲート（すり抜け可能扉・ゲート）
                        if char in tile_mappings and tile_mappings[char].get("category") == "wall_pass":
                            self.map_data[r][c] = TILE_GATE
                            img_path = tile_mappings[char].get("image_path", "")
                            if img_path:
                                import os as _os
                                fk = _os.path.splitext(_os.path.basename(img_path))[0]
                            else:
                                fk = self._resolve_theme_texture_key("wall_pass", tile_mappings[char].get("tile_id", 0))
                            self._wall_top_override[(c, r)] = fk
                            self._floor_override[(c, r)] = self._resolve_theme_texture_key("floor", 0)
                            
                        # 2. 壁・天井
                        elif char in tile_mappings and tile_mappings[char].get("category") == "wall_top":
                            self.map_data[r][c] = 0
                            img_path = tile_mappings[char].get("image_path", "")
                            if img_path:
                                import os as _os
                                fk = _os.path.splitext(_os.path.basename(img_path))[0]
                            else:
                                fk = self._resolve_theme_texture_key("wall_top", tile_mappings[char].get("tile_id", 0))
                            self._wall_top_override[(c, r)] = fk
                            
                        # 4. 背景・虚無
                        elif char in tile_mappings and tile_mappings[char].get("category") == "wall_none":
                            self.map_data[r][c] = 0
                            img_path = tile_mappings[char].get("image_path", "")
                            if img_path:
                                import os as _os
                                fk = _os.path.splitext(_os.path.basename(img_path))[0]
                            else:
                                fk = self._resolve_theme_texture_key("wall_none", tile_mappings[char].get("tile_id", 0))
                            self._wall_none_override[(c, r)] = fk
                            
                        # 5. 床・地面
                        elif char in tile_mappings and tile_mappings[char].get("category") == "floor":
                            self.map_data[r][c] = 1
                            img_path = tile_mappings[char].get("image_path", "")
                            if img_path:
                                import os as _os
                                fk = _os.path.splitext(_os.path.basename(img_path))[0]
                            else:
                                fk = self._resolve_theme_texture_key("floor", tile_mappings[char].get("tile_id", 0))
                            self._floor_override[(c, r)] = fk

                        # 6. 通路
                        elif char in tile_mappings and tile_mappings[char].get("category") == "corridor":
                            self.map_data[r][c] = 4
                            img_path = tile_mappings[char].get("image_path", "")
                            if img_path:
                                import os as _os
                                fk = _os.path.splitext(_os.path.basename(img_path))[0]
                            else:
                                fk = self._resolve_theme_texture_key("corridor")
                            self._floor_override[(c, r)] = fk
                        # 6. 特別・特殊タイル (P, D, U)
                        elif char == "P":
                            self.start_pos = (c, r)
                            self.map_data[r][c] = 1
                            self._floor_override[(c, r)] = self._resolve_theme_texture_key("floor", 0)

                        elif char == "D":
                            self.map_data[r][c] = 3
                            self.dungeon_pos = (c, r)
                        elif char == "U": 
                            self.map_data[r][c] = 2
                            
                        # 7. 互換性のためのフォールバック
                        elif char == "X":
                            self.map_data[r][c] = 0
                            self.wall_variants[(c, r)] = "wall_single_1"
                        elif char == "Y":
                            self.map_data[r][c] = 0
                            self.wall_variants[(c, r)] = "wall_single_2"
                        elif char == "Z":
                            self.map_data[r][c] = 0
                            self.wall_variants[(c, r)] = "wall_single_3"
                        elif char == "O":
                            self.map_data[r][c] = 0
                            self.wall_variants[(c, r)] = "wall_single"
                        elif char in "KLkl": # 通路
                            self.map_data[r][c] = 4
                        else: 
                            self.map_data[r][c] = 0
                if not self.rooms: self.rooms = [self.start_pos]
                else: self.rooms = [self.start_pos] # 固定マップでは開始地点を優先
                # 村(0F)はプレイヤーランク、休憩所はフロアに対応するランクで在庫決定
                if self.current_floor == 0:
                    shop_rank = getattr(self.player, "guild_rank", "-")
                else:
                    shop_rank = self.guild_system.get_required_rank_for_floor(self.current_floor) if self.guild_system else "F"
                self.refresh_shop_stock(player_rank=shop_rank)
                self.enemies = [e for e in self.enemies if getattr(e, "is_static", False)]
                
                # --- [NEW] 外部化されたエンティティ座標データ (positions) からキャラ/障害物を配置 ---
                source_yml = custom_file if custom_file else "village.yml"
                print(f"[DEBUG-NPC] Loading entities from TILE_MAPPINGS in {source_yml}. Total entries: {len(tile_mappings_raw)}")
                for ent_id, tile_info in tile_mappings_raw.items():
                    if not isinstance(tile_info, dict): continue
                    positions = tile_info.get("positions", [])
                    cat = tile_info.get("category")
                    
                    if not positions:
                        if cat in ("npc", "obstacle", "enemy"):
                            print(f"[DEBUG-NPC] Entity '{ent_id}' has NO positions listed in {source_yml}!")
                        continue
                    
                    print(f"[DEBUG-NPC] Found entity '{ent_id}' ({cat}) with {len(positions)} positions.")
                    for pos in positions:
                        c, r = pos.get("x"), pos.get("y")
                        if c is None or r is None:
                            print(f"[DEBUG-NPC]   Position is missing x or y for '{ent_id}'!")
                            continue
                        if c < 0 or c >= self.map_width or r < 0 or r >= self.map_height:
                            print(f"[DEBUG-NPC]   Position ({c}, {r}) is out of bounds for '{ent_id}' (map size: {self.map_width}x{self.map_height})!")
                            continue
                        
                        # --- ランクフィルタ ---
                        min_rank = pos.get("min_rank")
                        if ent_id in ("dedicated_weapon_shop", "dedicated_armor_shop", "dedicated_accessory_shop") and not min_rank:
                            min_rank = "D"
                        max_rank = pos.get("max_rank")
                        if min_rank or max_rank:
                            from constants import RANK_ORDER
                            player_rank = getattr(self.player, "guild_rank", "-") if self.player else "-"
                            p_idx = RANK_ORDER.index(player_rank) if player_rank in RANK_ORDER else 0
                            
                            # ランク "-" (0) の時は F (1) ランクの位置も表示可能にするための仮想インデックス
                            virtual_p_idx = 1 if p_idx == 0 else p_idx
                            
                            if min_rank and min_rank in RANK_ORDER:
                                if virtual_p_idx < RANK_ORDER.index(min_rank):
                                    continue
                            if max_rank and max_rank in RANK_ORDER:
                                if virtual_p_idx > RANK_ORDER.index(max_rank):
                                    continue

                        
                        if cat == "obstacle":
                            self.map_data[r][c] = 1 # 地面の上に配置
                            from components.sprites.enemy import Enemy
                            ox, oy = c * ts, r * ts
                            obstacle = Enemy(ox, oy, ent_id, player=self.player)
                            obstacle.x = c * ts + (ts - obstacle.width)//2
                            obstacle.y = r * ts + (ts - obstacle.height)//2
                            obstacle.target_x, obstacle.target_y = obstacle.x, obstacle.y
                            obstacle.flip = pos.get("flip", False)
                            self.enemies.append(obstacle)
                            print(f"[DEBUG-NPC]   Successfully spawned obstacle '{ent_id}' at grid coordinate ({c}, {r})")

                        elif cat == "enemy":
                            self.map_data[r][c] = 1
                            from components.sprites.enemy import Enemy
                            if ent_id in ENEMY_DATA and not ENEMY_DATA[ent_id].get("is_static", False):
                                ex, ey = c * ts, r * ts
                                enemy = Enemy(ex, ey, ent_id, player=self.player)
                                enemy.x = c * ts + (ts - enemy.width)//2
                                enemy.y = r * ts + (ts - enemy.height)//2
                                enemy.target_x, enemy.target_y = enemy.x, enemy.y
                                enemy.flip = pos.get("flip", False)
                                self.enemies.append(enemy)
                                print(f"[DEBUG-NPC]   Successfully spawned enemy '{ent_id}' at grid coordinate ({c}, {r})")
                            else:
                                print(f"[DEBUG-NPC]   Enemy '{ent_id}' not found in ENEMY_DATA or is static-only")
                            
                        elif cat == "npc":
                            self.map_data[r][c] = 1
                            from constants import NPC_DATA
                            if ent_id in NPC_DATA:
                                data = NPC_DATA[ent_id]
                                px, py = c * ts, r * ts
                                
                                role = data.get("role")
                                if not role:
                                    name = data.get("name", "")
                                    if "宿屋" in name: role = "inn"
                                    elif "鍛冶屋" in name: role = "blacksmith"
                                    elif "武器屋" in name: role = "weapon_shop"
                                    elif "道具屋" in name: role = "item_shop"
                                    elif "大魔導士" in name or "魔法屋" in name: role = "magic_shop"
                                    elif "商人" in name: role = "merchant"
                                    elif "ギルドマスター" in name or "ギルド受付" in name: role = "guild_receptionist"
                                    elif "預かり屋" in name: role = "storage"
                                    elif "銀行員" in name: role = "bank"
                                    elif "医者" in name: role = "doctor"
                                    elif "テレポート屋" in name: role = "teleport"
                                
                                npc = NPC(data["name"], px, py, 
                                          dialogue=data["dialogue"], 
                                          image_path=data["image_path"],
                                          base_image_path=tile_info.get("base_image_path", data.get("base_image_path")),
                                          role=role,
                                          flip=pos.get("flip", False),
                                          alpha=data.get("alpha"))
                                self.npcs.append(npc)
                                if role == "inn": self.inn_pos = (c, r)
                                if role == "doctor": self.clinic_pos = (c, r)
                                print(f"[DEBUG-NPC]   Successfully spawned NPC '{ent_id}' ('{data['name']}') at grid coordinate ({c}, {r})")
                            else:
                                print(f"[DEBUG-NPC]   NPC '{ent_id}' not found in NPC_DATA! Check npcs.yml")
                                
                        elif cat == "wall_decoration":
                            deco_id = tile_info.get("id", ent_id)
                            self.wall_decoration_variants[r][c] = deco_id
                            self.wall_decoration_flips[r][c] = pos.get("flip", False)
                            
                            # Dynamically load custom wall_decoration image paths (e.g. components/pictures/icon/stave.png)
                            if deco_id not in self.textures:
                                img_path = tile_info.get("image_path")
                                if img_path and os.path.exists(img_path):
                                    try:
                                        img = pygame.image.load(img_path).convert_alpha()
                                        if img.get_size() != (ts, ts):
                                            img = pygame.transform.scale(img, (ts, ts))
                                        self.textures[deco_id] = img
                                        print(f"[DEBUG-NPC]   Dynamically loaded custom wall_decoration image '{img_path}' for '{deco_id}'")
                                    except Exception as ex:
                                        print(f"[DEBUG-NPC]   Failed to load custom wall_decoration image '{img_path}': {ex}")
                            
                            print(f"[DEBUG-NPC]   Successfully placed wall_decoration '{deco_id}' at grid coordinate ({c}, {r}) (in textures: {deco_id in self.textures}) (flip: {pos.get('flip', False)})")
                        
                        elif cat == "wall_pass":
                            self.map_data[r][c] = TILE_GATE
                            img_path = tile_info.get("image_path", "")
                            if img_path:
                                import os as _os
                                fk = _os.path.splitext(_os.path.basename(img_path))[0]
                            else:
                                tile_id = tile_info.get("tile_id", 0)
                                fk = self._resolve_theme_texture_key("wall_pass", tile_id)
                            self._wall_top_override[(c, r)] = fk
                            print(f"[DEBUG-NPC]   Successfully placed wall_pass '{ent_id}' (fk={fk}) at grid coordinate ({c}, {r})")
                
                # --- [NEW] 固定マップでも障害物を配置可能にする (no_attack フロアは除く) ---
                _no_attack = self.floor_info.get("no_attack", False) if isinstance(self.floor_info, dict) else False
                if self.player and self.current_floor > 0 and not _no_attack:
                    self._spawn_wall_obstacles(self.player)
                    
                return
            except Exception as e:
                import traceback
                print(f"[Dungeon] Error parsing fixed map {map_name}: {e}")
                traceback.print_exc()

        # フォールバック（ファイルがない場合）
        print(f"[Dungeon] Warning: Fixed map {map_name} not found. Using fallback layout.")
        self.map_width, self.map_height = 25, 20
        self.map_data = [[0 for _ in range(self.map_width)] for _ in range(self.map_height)]
        
        # 属性マップ（バリエーション）も新しいサイズで初期化し直す
        f_list = self.available_floor_variants
        w_list = self.available_wall_variants
        wt_list = self.available_wall_top_variants
        wn_list = self.available_wall_none_variants
        self.floor_variants = [[(random.choice(f_list) if f_list else "floor") for _ in range(self.map_width)] for _ in range(self.map_height)]
        self.wall_variants = [[(random.choice(w_list) if w_list else "wall_single") for _ in range(self.map_width)] for _ in range(self.map_height)]
        self.wall_top_variants = [[(random.choice(wt_list) if wt_list else "wall_top") for _ in range(self.map_width)] for _ in range(self.map_height)]
        self.wall_none_variants = [[(random.choice(wn_list) if wn_list else "wall_none") for _ in range(self.map_width)] for _ in range(self.map_height)]
        for row in range(5, 15):
            for col in range(5, 20): self.map_data[row][col] = 1
        self.rooms = [(12, 10)]
        self.map_data[10][19] = 3
        self.enemies = []
        self.play_floor_bgm()

    def play_floor_bgm(self):
        """現在の階層設定に基づいたBGMを再生する"""
        from systems.audio_manager import play_bgm
        from constants import DUNGEON_IMAGES
        bgm_folder = DUNGEON_IMAGES.get("bgm_path", "components/sounds/bgm")
        sound_file = self.floor_info.get("sound")
        if sound_file:
            if "/" in sound_file or "\\" in sound_file:
                play_bgm(sound_file)
            else:
                play_bgm(bgm_folder + "/" + sound_file)

    def spawn_floor_items(self, player):
        from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, CONSUMABLE_DATA, STAVE_DATA, ACCESSORY_DATA, ITEM_DROP_RATES
        from constants import FLOOR_ITEM_SPAWN_MIN, FLOOR_ITEM_SPAWN_MAX, FLOOR_ITEM_ROOM_RATIO, FLOOR_ITEM_SCALE_EVERY, FLOOR_ITEM_SCALE_ADD
        from components.sprites.item import DroppedWeapon, DroppedConsumable, DroppedArmor, DroppedShield, DroppedStave, DroppedAccessory
        
        floor = self.current_floor
        rooms = len(self.rooms)
        
        # 部屋数に対する比率でアイテム数を決定 (例: 4部屋 * 0.7 = 2.8 -> 2個)
        # 階層が進むとさらに微増させるスケーリングも加味
        scale_add = (floor // FLOOR_ITEM_SCALE_EVERY) * FLOOR_ITEM_SCALE_ADD
        base_count = int(rooms * FLOOR_ITEM_ROOM_RATIO) + scale_add
        
        # 最終的な個数を Min/Max の範囲内に収める
        count = max(FLOOR_ITEM_SPAWN_MIN, min(FLOOR_ITEM_SPAWN_MAX + scale_add, base_count))
        
        # アウトブレイク時はアイテム数を増やす
        if self.is_outbreak:
            from constants import OUTBREAK_ITEM_MULT
            count = int(count * OUTBREAK_ITEM_MULT)
            
        # フロア設定によるアイテム出現比率の適用 (例: 0.5で半減)
        ratio_mult = self.floor_info.get("item_ratio", 1.0)
        count = max(0, int(count * ratio_mult))
        
        # ランクアップアイテムのチェック
        cert_to_spawn = None
        for q in player.active_quests:
            if q.get("is_rank_up"):
                # 現在のランクの最大階層なら証を出現させる
                max_f = self.guild_system.get_max_floor(player.guild_rank)
                if floor == max_f:
                    cert_to_spawn = q["target_key"]
                    break
        
        candidates = []
        # Consumable
        for key, data in CONSUMABLE_DATA.items():
            if data.get("category") != "event" and data.get("floor_spawnable", True):
                if data.get("min_floor", 1) <= floor <= data.get("max_floor", 999):
                    candidates.append((key, "consumable", data, ITEM_DROP_RATES.get(data.get("rarity", 1), 0.1)))
        # Weapon, Armor, Shield, Stave (default to common)
        for key, data in WEAPON_DATA.items():
            if data.get("category") != "event" and data.get("floor_spawnable", True):
                if data.get("min_floor", 1) <= floor <= data.get("max_floor", 999):
                    candidates.append((key, "weapon", data, ITEM_DROP_RATES.get(data.get("rarity", 1), 0.1)))
        for key, data in ARMOR_DATA.items():
            if data.get("category") != "event" and data.get("floor_spawnable", True):
                if data.get("min_floor", 1) <= floor <= data.get("max_floor", 999):
                    candidates.append((key, "armor", data, ITEM_DROP_RATES.get(data.get("rarity", 1), 0.1)))
        for key, data in SHIELD_DATA.items():
            if data.get("category") != "event" and data.get("floor_spawnable", True):
                if data.get("min_floor", 1) <= floor <= data.get("max_floor", 999):
                    candidates.append((key, "shield", data, ITEM_DROP_RATES.get(data.get("rarity", 1), 0.1)))
        for key, data in STAVE_DATA.items():
            if data.get("category") != "event" and data.get("floor_spawnable", True):
                if data.get("min_floor", 1) <= floor <= data.get("max_floor", 999):
                    candidates.append((key, "stave", data, ITEM_DROP_RATES.get(data.get("rarity", 1), 0.1)))
        for key, data in ACCESSORY_DATA.items():
            if data.get("category") != "event" and data.get("floor_spawnable", True):
                if data.get("min_floor", 1) <= floor <= data.get("max_floor", 999):
                    candidates.append((key, "accessory", data, ITEM_DROP_RATES.get(data.get("rarity", 1), 0.1)))
        if not candidates:
            print(f"[Dungeon] WARNING: No item candidates for Floor {floor}!")
            return
        
        try:
            print(f"[Dungeon] Floor {floor} | Item Candidates: {len(candidates)} | Spawning: {count}")
            player_gx, player_gy = int((player.x + self.tile_size / 2) // self.tile_size), int((player.y + self.tile_size / 2) // self.tile_size)
            if hasattr(self, 'valid_floor_coords') and self.valid_floor_coords:
                floor_tiles = [(c, r) for (c, r) in self.valid_floor_coords if self.map_data[r][c] == 1 and (abs(c - player_gx) > 1 or abs(r - player_gy) > 1)]
            else:
                floor_tiles = [(c, r) for r in range(self.map_height) for c in range(self.map_width) if self.map_data[r][c] == 1 and (abs(c - player_gx) > 1 or abs(r - player_gy) > 1)]
            random.shuffle(floor_tiles)
            placed = 0
            
            print(f"[Dungeon] Floor {floor} | Potential Tiles: {len(floor_tiles)}")
            for tile_pos in floor_tiles:
                if placed >= count: break
                weights = [c[3] for c in candidates]
                chosen_key, chosen_type, chosen_data, _ = random.choices(candidates, weights=weights, k=1)[0]
                gx, gy = tile_pos
                px, py = gx * self.tile_size, gy * self.tile_size
                
                item = None
                # 強化済み装備ドロップの判定（全装備タイプに適用）
                enhance, stats = self._generate_enhanced_drop(player)
                
                if chosen_type == "weapon":
                    item = DroppedWeapon(px, py, chosen_key, chosen_data, enhance=enhance, stats=stats)
                elif chosen_type == "consumable": item = DroppedConsumable(px, py, chosen_key, chosen_data)
                elif chosen_type == "armor": item = DroppedArmor(px, py, chosen_key, chosen_data, enhance=enhance, stats=stats)
                elif chosen_type == "shield": item = DroppedShield(px, py, chosen_key, chosen_data, enhance=enhance, stats=stats)
                elif chosen_type == "stave": item = DroppedStave(px, py, chosen_key, chosen_data)
                elif chosen_type == "accessory": item = DroppedAccessory(px, py, chosen_key, chosen_data, enhance=enhance, stats=stats)
                else: continue
                
                self.dropped_items.append(item)
                placed += 1
                print(f"  - Item {placed}: {item.name} at ({gx}, {gy})")
                
            print(f"[Dungeon] Floor {floor} | Total Items Placed: {placed}/{count}")
        except Exception as e:
            print(f"[Dungeon] Error in spawn_floor_items: {e}")
            import traceback
            traceback.print_exc()
            
        # 2. イベントアイテムの強制配置（カテゴリ: event かつ条件合致）
        event_candidates = []
        from constants import GUILD_RANKS, RANK_ORDER
        # ランクアップアイテムと対応ランクのマップ作成
        rank_item_map = {r.get("rank_up_item"): r.get("rank") for r in GUILD_RANKS if r.get("rank_up_item")}
        
        for key, data in CONSUMABLE_DATA.items():
            if data.get("category") == "event":
                # 階層条件
                if data.get("min_floor", 1) <= floor <= data.get("max_floor", 999):
                    # ランクアップ用アイテム（冒険者の証や各ランク証）の特殊判定
                    target_rank = rank_item_map.get(key)
                    if target_rank:
                        # 1. すでにそのランクに到達している場合はドロップしない
                        try:
                            if RANK_ORDER.index(player.guild_rank) >= RANK_ORDER.index(target_rank):
                                continue
                        except: pass
                        
                        # 2. 昇級クエストを受注している場合のみドロップする
                        is_needed = any(q.get("is_rank_up") and q.get("target_key") == key for q in player.active_quests)
                        if not is_needed: continue
                    
                    # 重複チェック（所持品：通常+貴重品、床の上）
                    if not any(i["key"] == key for i in player.items) and \
                       not any(i["key"] == key for i in player.event_items) and \
                       not any(isinstance(di, DroppedConsumable) and di.item_key == key for di in self.dropped_items):
                        event_candidates.append((key, data))
                        
        if event_candidates:
            # 上り階段（開始地点）の位置を探す
            up_stairs = None
            for r in range(self.map_height):
                for c in range(self.map_width):
                    if self.map_data[r][c] == 2:  # 2: 上り階段
                        up_stairs = (c, r)
                        break
                if up_stairs: break
            
            # 階段が見つからない場合はプレイヤーの開始位置
            if not up_stairs:
                up_stairs = (player_gx, player_gy)

            # 上り階段から一番遠い部屋（中心座標）を探す
            target_pos = up_stairs
            if hasattr(self, "rooms") and self.rooms:
                max_dist = -1
                for rx, ry in self.rooms:
                    dist = (rx - up_stairs[0])**2 + (ry - up_stairs[1])**2
                    if dist > max_dist:
                        max_dist = dist
                        target_pos = (rx, ry)

            for e_key, e_data in event_candidates:
                # ターゲット位置（最も遠い部屋の中心）の周囲3x3から空いている床を探す
                spawn_pos = None
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        cx, cy = target_pos[0] + dx, target_pos[1] + dy
                        if 0 <= cx < self.map_width and 0 <= cy < self.map_height:
                            if self.map_data[cy][cx] in (1, 3):  # 床(1)か下り階段(3)
                                # 既にアイテムがあるかチェック
                                if not any(int(di.x//self.tile_size) == cx and int(di.y//self.tile_size) == cy for di in self.dropped_items):
                                    spawn_pos = (cx, cy)
                                    break
                    if spawn_pos: break
                
                # それでも空きがなければ元の tile_pos の最初の空き場所
                if not spawn_pos and floor_tiles:
                    for tile_pos in floor_tiles:
                        if not any(int(di.x//self.tile_size) == tile_pos[0] and int(di.y//self.tile_size) == tile_pos[1] for di in self.dropped_items):
                            spawn_pos = tile_pos
                            break

                if spawn_pos:
                    px, py = spawn_pos[0] * self.tile_size, spawn_pos[1] * self.tile_size
                    item = DroppedConsumable(px, py, e_key, e_data)
                    self.dropped_items.append(item)
                    print(f"[Dungeon] Forced spawn of event item: {e_key} at {spawn_pos} (furthest room)")

    def _generate_enhanced_drop(self, player):
        """強化済み装備ドロップの判定とステータス生成（ギルドランク別強化範囲対応）
        
        Returns:
            tuple: (enhance_count, stats_dict) - 強化回数とステータス辞書
        """
        import random
        from constants import ENHANCED_DROP_CHANCE, ENHANCED_DROP_RANK_RANGE
        
        if random.random() > ENHANCED_DROP_CHANCE:
            return 0, {}
        
        # プレイヤーのギルドランクで判定
        rank = getattr(player, "guild_rank", "F")
        
        # ランク別の強化範囲を取得
        enh_range = ENHANCED_DROP_RANK_RANGE.get(rank, [0, 0])
        min_e, max_e = enh_range[0], enh_range[1]
        if max_e == 0:
            return 0, {}
        
        enhance = random.randint(min_e, max_e)
        
        stats = {}
        upgradeable_stats = [
            "attack_bonus", "accuracy_bonus_close", "accuracy_bonus_range", "crit_rate",
            "hp_bonus", "defense_bonus", "block_chance_close", "block_chance_ranged",
            "regen_bonus", "armor_penetration"
        ]
        for _ in range(enhance):
            stat = random.choice(upgradeable_stats)
            stats[stat] = stats.get(stat, 0) + 1
        
        return enhance, stats

    def create_corridor(self, x1, x2, y1, y2, width=1):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for dw in range(width):
                    tx, ty = (x + dw, y) if x1 == x2 else (x, y + dw)
                    if 0 <= ty < self.map_height and 0 <= tx < self.map_width:
                        if self.map_data[ty][tx] == 0: self.map_data[ty][tx] = 4
                        if hasattr(self, "valid_floor_coords"):
                            self.valid_floor_coords.add((tx, ty))

    def _trim_to_valid_areas(self):
        """有効な床エリア(valid_floor_coords)に含まれない床・通路タイルを削除します。"""
        if not hasattr(self, "valid_floor_coords"): return
        removed = 0
        for y in range(self.map_height):
            for x in range(self.map_width):
                # 床(1)や通路(4,5,6)で、かつ有効エリアに含まれないものを壁(0)に戻す
                if self.map_data[y][x] in [1, 4, 5, 6] and (x, y) not in self.valid_floor_coords:
                    self.map_data[y][x] = 0
                    removed += 1
        if removed > 0:
            print(f"[Dungeon] Trimmed {removed} artifact floor tiles.")

    def _is_room(self, x, y):
        if not (0 <= x < self.map_width and 0 <= y < self.map_height): return False
        t = self.map_data[y][x]
        return 1 <= t <= 3

    def _is_corridor(self, x, y):
        if not (0 <= x < self.map_width and 0 <= y < self.map_height): return False
        t = self.map_data[y][x]
        return 4 <= t <= 6
    
    def _convert_sandwiched_walls(self):
        """上下を床に挟まれた壁（0）を床（1）に変換します。"""
        to_floor = []
        for y in range(1, self.map_height - 1):
            for x in range(self.map_width):
                if self.map_data[y][x] == 0:
                    # 上下ともに床（ID > 0）なら、それは挟まれた壁
                    if self.map_data[y-1][x] > 0 and self.map_data[y+1][x] > 0:
                        to_floor.append((x, y))
        
        for x, y in to_floor:
            self.map_data[y][x] = 1
            if hasattr(self, "valid_floor_coords"):
                self.valid_floor_coords.add((x, y))
        
        if to_floor:
            print(f"[Dungeon] Converted {len(to_floor)} sandwiched walls to floor.")

    def is_nw(self, x, y):
        """指定した座標が「南側に床がある北壁」かどうかを判定します。"""
        if not (0 <= x < self.map_width and 0 <= y < self.map_height): return False
        return self.map_data[y][x] == 0 and y < self.map_height - 1 and self.map_data[y+1][x] > 0

    def _get_wall_texture_key(self, x, y):
        # 南側が床（ID > 0）である壁のみを「表示される壁」とする
        if not self.is_nw(x, y):
            return "wall_none"
            
        # 左右に壁があるかに関わらず wall_top を返す（wall_singleは廃止）
        return "wall_top"
    def export_debug_map(self, player):
        """現在のマップの状態をテキストファイルとして書き出します（デバッグ用）。"""
        px, py = int(player.x // self.tile_size), int(player.y // self.tile_size)
        lines = []
        for y in range(self.map_height):
            row_chars = []
            for x in range(self.map_width):
                char = "?"
                tile = self.map_data[y][x]
                
                # プレイヤーの位置を最優先で表示
                if x == px and y == py:
                    char = "P"
                elif tile == 1: char = "." # 床
                elif tile == 2: char = "U" # 階段上
                elif tile == 3: char = "D" # 階段下
                elif tile in [4, 5, 6]: char = "C" # 通路
                elif tile == 0:
                    if self.is_nw(x, y): char = "@" # 許可された壁（縁）
                    else: char = "#" # 許可されていない壁（背景）
                
                row_chars.append(char)
            lines.append(" ".join(row_chars))
        
        try:
            with open("debug_map.txt", "w", encoding="utf-8") as f:
                f.write(f"Floor: {self.current_floor}\n")
                f.write(f"Player Pos: ({px}, {py})\n")
                f.write("-" * (self.map_width * 2) + "\n")
                f.write("\n".join(lines))
            print(f"[Debug] Map exported to debug_map.txt (Player at {px}, {py})")
        except Exception as e:
            print(f"[Debug] Failed to export map: {e}")

    def _spawn_wall_obstacles(self, player):
        """床の上にランダムに障害物（独立壁）を配置する。"""
        from constants import (OBSTACLE_SPAWN_MIN, OBSTACLE_SPAWN_MAX, 
                               OBSTACLE_SPAWN_SCALE_EVERY, OBSTACLE_SPAWN_SCALE_ADD, OBSTACLE_SPAWN_LIMIT)
        scale = (self.current_floor - 1) // OBSTACLE_SPAWN_SCALE_EVERY * OBSTACLE_SPAWN_SCALE_ADD
        count = random.randint(OBSTACLE_SPAWN_MIN, OBSTACLE_SPAWN_MAX) + scale
        count = min(count, OBSTACLE_SPAWN_LIMIT)
        floor_tiles = []
        for y in range(1, self.map_height - 1):
            for x in range(1, self.map_width - 1):
                tile = self.map_data[y][x]
                # 床タイル（ID 1）を対象にする
                if tile == 1:
                    # 階段(2,3)や通路(4,5,6)の隣には置かない（入り口を塞がない）
                    neighbors = [self.map_data[y+dy][x+dx] for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]]
                    if all(t not in [2, 3, 4, 5, 6] for t in neighbors):
                        floor_tiles.append((x, y))
        random.shuffle(floor_tiles)
        placed = 0
        px, py = int(player.x // self.tile_size), int(player.y // self.tile_size)
        for tx, ty in floor_tiles:
            if placed >= count: break
            if abs(tx - px) <= 1 and abs(ty - py) <= 1: continue
            self.map_data[ty][tx] = 0
            if self.available_wall_variants:
                self.wall_variants[(tx, ty)] = random.choice(self.available_wall_variants)
            placed += 1
        print(f"[Dungeon] Spawned {placed} wall obstacles (Floor {self.current_floor})")

    def _clean_map_single_pass(self):
        """ランダムダンジョン生成後のクリーニングを1収束ループで行う。
        旧: _remove_lone_walls + _convert_inner_walls_to_floors + _remove_thin_walls
            + _convert_sandwiched_walls + _adjust_wall_rendering_logic + _remove_lone_walls(2回目)
        を統合して全マスループを最小化する。
        """
        def is_vis(tx, ty):
            if not (0 <= tx < self.map_width and 0 <= ty < self.map_height): return False
            return self.map_data[ty][tx] > 0 or self.is_nw(tx, ty)

        def is_void(tx, ty):
            if not (0 <= tx < self.map_width and 0 <= ty < self.map_height): return True
            return self.map_data[ty][tx] == 0 and not self.is_nw(tx, ty)

        changed = True
        while changed:
            changed = False
            for y in range(1, self.map_height - 1):
                for x in range(1, self.map_width - 1):
                    if self.map_data[y][x] != 0:
                        continue
                    n = self.map_data[y-1][x]
                    s = self.map_data[y+1][x]
                    w = self.map_data[y][x-1]
                    e = self.map_data[y][x+1]
                    f_u, f_d, f_l, f_r = n > 0, s > 0, w > 0, e > 0

                    # 孤立壁（4方向すべて床）→ 床
                    if f_u and f_d and f_l and f_r:
                        self.map_data[y][x] = 1
                        if hasattr(self, 'valid_floor_coords'):
                            self.valid_floor_coords.add((x, y))
                        changed = True
                        continue

                    # 挟まれた壁（上下が床）→ 床
                    if f_u and f_d:
                        self.map_data[y][x] = 1
                        if hasattr(self, 'valid_floor_coords'):
                            self.valid_floor_coords.add((x, y))
                        changed = True
                        continue

                    # 内側壁（4方向すべて可視）→ 床
                    if all(is_vis(x+dx, y+dy) for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]):
                        self.map_data[y][x] = 1
                        if hasattr(self, 'valid_floor_coords'):
                            self.valid_floor_coords.add((x, y))
                        changed = True
                        continue

                    # 細い壁（3方向以上がVoid）→ 床
                    if self.is_nw(x, y):
                        void_count = sum(1 for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)] if is_void(x+dx, y+dy))
                        if void_count >= 3:
                            self.map_data[y][x] = 1
                            if hasattr(self, 'valid_floor_coords'):
                                self.valid_floor_coords.add((x, y))
                            changed = True
                            continue

                    # 3方向が床の壁 → 床（ただし上だけ壁・他3方向床はwall_topなので残す）
                    if self.current_floor != 0:
                        floor_count = sum([f_u, f_d, f_l, f_r])
                        if floor_count == 3 and not (not f_u and f_d and f_l and f_r):
                            self.map_data[y][x] = 1
                            if hasattr(self, 'valid_floor_coords'):
                                self.valid_floor_coords.add((x, y))
                            changed = True

    def _remove_lone_walls(self):
        """上下左右がすべて床（または通路）である孤立した壁を床に置き換える。"""
        for y in range(1, self.map_height - 1):
            for x in range(1, self.map_width - 1):
                if self.map_data[y][x] == 0:
                    is_lone = True
                    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        if self.map_data[y+dy][x+dx] == 0:
                            is_lone = False
                            break
                    if is_lone:
                        self.map_data[y][x] = 1

    def _convert_inner_walls_to_floors(self):
        """上下左右がすべて可視領域（＝縁が出ない場所）である壁を床に置き換える。"""
        def is_vis(tx, ty):
            if not (0 <= tx < self.map_width and 0 <= ty < self.map_height): return False
            return self.map_data[ty][tx] > 0 or self.is_nw(tx, ty)
        
        while True:
            to_floor = []
            for y in range(1, self.map_height - 1):
                for x in range(1, self.map_width - 1):
                    if self.map_data[y][x] == 0:
                        if all(is_vis(x+dx, y+dy) for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]):
                            to_floor.append((x, y))
            if not to_floor: break
            for x, y in to_floor:
                self.map_data[y][x] = 1

    def _remove_thin_walls(self):
        """周囲が空白（Void）に囲まれすぎている不自然な壁を床に変換する。"""
        def is_void(tx, ty):
            if not (0 <= tx < self.map_width and 0 <= ty < self.map_height): True
            return self.map_data[ty][tx] == 0 and not self.is_nw(tx, ty)

        while True:
            to_floor = []
            for y in range(1, self.map_height - 1):
                for x in range(1, self.map_width - 1):
                    if self.is_nw(x, y):
                        # 上下左右の空白（Void）の数を数える
                        void_neighbors = 0
                        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            if is_void(x+dx, y+dy):
                                void_neighbors += 1
                        
                        # 3方向以上が空白（行き止まりのような突起）なら床にする
                        if void_neighbors >= 3:
                            to_floor.append((x, y))
            if not to_floor: break
            for x, y in to_floor:
                self.map_data[y][x] = 1

    def _add_floor_edges(self):
        """床と壁の境界に縁を配置します。"""
        self.edges = []
        edge_size = max(1, self.tile_size // 4)
        base_tex = self.textures.get("wall_base")
        if not base_tex:
            base_tex = pygame.Surface((self.tile_size, self.tile_size), pygame.SRCALPHA)
            base_tex.fill((120, 100, 80, 200))

        # 縁のテクスチャ切り出し
        h_tex_base = base_tex.subsurface((0, 0, self.tile_size, edge_size)).copy()
        corner_tex_base = base_tex.subsurface((0, 0, edge_size, edge_size)).copy()
        side_tex = base_tex.subsurface((0, 0, edge_size, self.tile_size)).copy()

        def is_vis(tx, ty):
            if not (0 <= tx < self.map_width and 0 <= ty < self.map_height): return False
            return self.map_data[ty][tx] > 0 or self.is_nw(tx, ty)

        for y in range(self.map_height):
            for x in range(self.map_width):
                # 1. 横方向の判定 (最優先)
                if y < self.map_height - 1:
                    # 下隣のタイル情報をチェック
                    is_floor_below = (self.map_data[y+1][x] > 0)
                    
                    # [FIX] 壁の下部には影を描かない
                    pass

                # 上隣 (x, y-1) が表示対象の場合 (Void cell (x, y) の上端に描画)
                if y > 0 and not is_vis(x, y) and is_vis(x, y-1):
                    self.edges.append({"x": x, "y": y, "img": pygame.transform.flip(h_tex_base, False, True), "ox": 0, "oy": 0})
                
                # [NEW] 自分が表示対象で上が不可視（Void）の場合 (上のタイルの下端に縁を描画)
                if y > 0 and is_vis(x, y) and not is_vis(x, y-1):
                    self.edges.append({"x": x, "y": y-1, "img": h_tex_base, "ox": 0, "oy": self.tile_size - edge_size})

                # 2. 縦方向・角の判定 (Voidセルの内側のみ)
                if not is_vis(x, y):
                    # 縦方向 (影なしの基本テクスチャを強制)
                    if x < self.map_width - 1 and is_vis(x+1, y):
                        self.edges.append({"x": x, "y": y, "img": side_tex, "ox": self.tile_size - edge_size, "oy": 0})
                    if x > 0 and is_vis(x-1, y):
                        self.edges.append({"x": x, "y": y, "img": pygame.transform.flip(side_tex, True, False), "ox": 0, "oy": 0})
                    
                    # 角の処理
                    for dx, dy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
                        tx, ty = x + dx, y + dy
                        if not (0 <= tx < self.map_width and 0 <= ty < self.map_height): continue
                        if not is_vis(tx, ty): continue
                        
                        # 通常の角（両隣がVoid）
                        is_normal_corner = not is_vis(x+dx, y) and not is_vis(x, y+dy)
                        # 壁との接合部（床にも触れている場合）
                        is_wall_junction = False
                        below_key = self._get_wall_texture_key(tx, ty)
                        is_wall_diag = (below_key in ["wall_top", "wall_single"])
                        
                        if is_wall_diag:
                            # 斜めが壁 かつ 隣接タイルのどちらかが床（map_data > 0）ならジャンクション
                            adj_x_is_floor = (0 <= x+dx < self.map_width) and self.map_data[y][x+dx] > 0
                            adj_y_is_floor = (0 <= y+dy < self.map_height) and self.map_data[y+dy][x] > 0
                            if adj_x_is_floor or adj_y_is_floor:
                                is_wall_junction = True
                        
                        if is_normal_corner or is_wall_junction:
                            # 影なし: 全角でベーステクスチャ
                            ox = self.tile_size - edge_size if dx > 0 else 0
                            oy = self.tile_size - edge_size if dy > 0 else 0
                            self.edges.append({"x": x, "y": y, "img": corner_tex_base, "ox": ox, "oy": oy})

    def _create_placeholder_textures(self):
        size = self.tile_size
        textures = {}
        floor = pygame.Surface((size, size))
        floor.fill((139, 115, 85))
        pygame.draw.line(floor, (100, 80, 60), (0, size//2), (size, size//2), 2)
        pygame.draw.line(floor, (100, 80, 60), (size//2, 0), (size//2, size//2), 2)
        pygame.draw.line(floor, (100, 80, 60), (size//4, size//2), (size//4, size), 2)
        pygame.draw.line(floor, (100, 80, 60), (size*3//4, size//2), (size*3//4, size), 2)
        textures["floor"] = floor
        corridor = pygame.Surface((size, size))
        corridor.fill((120, 100, 75))
        pygame.draw.line(corridor, (90, 70, 50), (size//2, 0), (size//2, size), 2)
        textures["corridor"] = corridor
        wall_top = pygame.Surface((size, size))
        wall_top.fill((180, 80, 80))
        pygame.draw.rect(wall_top, (120, 50, 50), (0, 0, size, size), 4)
        textures["wall_top"] = wall_top
        from constants import DUNGEON_VOID_COLOR
        wall_none = pygame.Surface((size, size))
        wall_none.fill(DUNGEON_VOID_COLOR)
        textures["wall_none"] = wall_none
        stairs_up = pygame.Surface((size, size))
        stairs_up.fill((139, 115, 85))
        pygame.draw.rect(stairs_up, (180, 100, 255), (size//6, size//6, size*2//3, size*2//3))
        textures["stairs_up"] = stairs_up
        stairs_down = pygame.Surface((size, size))
        stairs_down.fill((139, 115, 85))
        pygame.draw.rect(stairs_down, (100, 0, 150), (size//6, size//6, size*2//3, size*2//3))
        textures["stairs_down"] = stairs_down
        wall_base = pygame.Surface((size, size), pygame.SRCALPHA)
        wall_base.fill((100, 80, 60, 200))
        textures["wall_base"] = wall_base
        return textures

    def refresh_shop_stock(self, player_rank="-"):
        from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, ACCESSORY_DATA, CONSUMABLE_DATA, STAVE_DATA, ITEM_DROP_RATES, RANK_ORDER

        # ミッション達成ボーナスフラグ
        bonus_mode = getattr(self.player, "shop_bonus_refresh", False) if self.player else False
        if bonus_mode and self.player:
            self.player.shop_bonus_refresh = False

        SHOP_LIMIT_NORMAL = 10
        SHOP_LIMIT_BONUS = 30
        BONUS_LIMIT_WEAPON_SHOP = 8
        BONUS_LIMIT_DEDICATED_WEAPON = 4
        BONUS_LIMIT_DEDICATED_ARMOR = 4
        BONUS_LIMIT_DEDICATED_ACCESSORY = 4

        # 出現率をレアリティから算出（ドロップ率の5倍をショップ出現率とする）
        def get_shop_rate(v):
            rarity = v.get("rarity", 1)
            return ITEM_DROP_RATES.get(rarity, 0.1) * 5

        # ランク制限チェック
        def is_rank_ok(v):
            if not self.guild_system: return True
            req_rank = v.get("min_rank") or v.get("rank") or "F"
            return self.guild_system.is_rank_at_least(player_rank, req_rank)

        def is_bonus_rank_visible(v):
            req_rank = v.get("min_rank") or v.get("rank") or "F"
            if player_rank == "A":
                return req_rank in ("A", "B")
            return True

        # 通常時: usually_buyable かつ min_rank がプレイヤーランク以下で最も高いもの
        def get_fixed_items(data_dict, item_type):
            """通常時: usually_buyable品のうち、min_rankがプレイヤーランク以下で最も高いものを返す"""
            p_idx = RANK_ORDER.index(player_rank) if player_rank in RANK_ORDER else 0
            best_rank_idx = -1
            items = []
            for k, v in data_dict.items():
                shop = v.get("shop", {})
                if not shop.get("usually_buyable", False): continue
                min_rank = v.get("min_rank", "F")
                if min_rank not in RANK_ORDER: continue
                f_idx = RANK_ORDER.index(min_rank)
                if f_idx <= p_idx:
                    if f_idx > best_rank_idx:
                        best_rank_idx = f_idx
                        items = [(k, v)]
                    elif f_idx == best_rank_idx:
                        items.append((k, v))
            return [{"key": k, "type": item_type, "name": v["name"], "price": v["price"], "count": 1} for k, v in items]

        # ボーナスモード: special_buyable かつランクOKの全品
        def get_bonus_items(data_dict, item_type):
            """ミッション後: special_buyable品をランク条件内で全部並べる"""
            result = []
            for k, v in data_dict.items():
                shop = v.get("shop", {})
                if not shop.get("special_buyable", False): continue
                if not is_rank_ok(v): continue
                if not is_bonus_rank_visible(v): continue
                result.append({"key": k, "type": item_type, "name": v["name"], "price": v["price"], "count": 1})
            return result

        def pick_bonus_items_with_cycle(items, category_key, limit):
            if not items:
                return []
            player = getattr(self, "player", None)
            if not player:
                return items[:limit]
            seen_map = getattr(player, "shop_seen_special", None)
            if not isinstance(seen_map, dict):
                seen_map = {}
                player.shop_seen_special = seen_map

            def item_token(entry):
                return f"{entry['type']}:{entry['key']}"

            all_tokens = {item_token(it) for it in items}
            seen_tokens = set(seen_map.get(category_key, []))
            fresh_items = [it for it in items if item_token(it) not in seen_tokens]
            if not fresh_items:
                seen_tokens = set()
                fresh_items = items[:]

            random.shuffle(fresh_items)
            picked = fresh_items[:limit]
            seen_tokens.update(item_token(it) for it in picked)

            if all_tokens and seen_tokens.issuperset(all_tokens):
                seen_map[category_key] = []
            else:
                seen_map[category_key] = sorted(seen_tokens)
            return picked

        # --- 1. 武器屋 (武器・防具・盾) ---
        if bonus_mode:
            weapon_cands = get_bonus_items(WEAPON_DATA, "weapon") + get_bonus_items(ARMOR_DATA, "armor") + get_bonus_items(SHIELD_DATA, "shield")
            weapon_cands = pick_bonus_items_with_cycle(weapon_cands, "weapon_shop", BONUS_LIMIT_WEAPON_SHOP)
        else:
            weapon_cands = get_fixed_items(WEAPON_DATA, "weapon") + get_fixed_items(ARMOR_DATA, "armor") + get_fixed_items(SHIELD_DATA, "shield")
        self.weapon_shop_stock = weapon_cands[:]

        # --- 1.2 武器専用屋 (武器のみ) ---
        if bonus_mode:
            d_weapon_cands = get_bonus_items(WEAPON_DATA, "weapon")
            d_weapon_cands = pick_bonus_items_with_cycle(d_weapon_cands, "dedicated_weapon_shop", BONUS_LIMIT_DEDICATED_WEAPON)
        else:
            d_weapon_cands = get_fixed_items(WEAPON_DATA, "weapon")
        self.dedicated_weapon_shop_stock = d_weapon_cands[:]

        # --- 1.3 防具専用屋 (防具・盾のみ) ---
        if bonus_mode:
            d_armor_cands = get_bonus_items(ARMOR_DATA, "armor") + get_bonus_items(SHIELD_DATA, "shield")
            d_armor_cands = pick_bonus_items_with_cycle(d_armor_cands, "dedicated_armor_shop", BONUS_LIMIT_DEDICATED_ARMOR)
        else:
            d_armor_cands = get_fixed_items(ARMOR_DATA, "armor") + get_fixed_items(SHIELD_DATA, "shield")
        self.dedicated_armor_shop_stock = d_armor_cands[:]

        # --- 1.4 アクセサリ専用屋 (アクセサリのみ) ---
        if bonus_mode:
            d_acc_cands = get_bonus_items(ACCESSORY_DATA, "accessory")
            d_acc_cands = pick_bonus_items_with_cycle(d_acc_cands, "dedicated_accessory_shop", BONUS_LIMIT_DEDICATED_ACCESSORY)
        else:
            d_acc_cands = get_fixed_items(ACCESSORY_DATA, "accessory")
            # アクセサリにfixed品がない場合、ランダムで補充
            if not d_acc_cands:
                for k, v in ACCESSORY_DATA.items():
                    shop = v.get("shop", {})
                    if shop.get("special_buyable", False) and is_rank_ok(v) and random.random() < get_shop_rate(v):
                        d_acc_cands.append({"key": k, "type": "accessory", "name": v["name"], "price": v["price"], "count": 1})
                if not d_acc_cands:
                    all_accs = [(k, v) for k, v in ACCESSORY_DATA.items() if v.get("shop", {}).get("special_buyable", False) and is_rank_ok(v)]
                    if all_accs:
                        while len(d_acc_cands) < 3:
                            k, v = random.choice(all_accs)
                            d_acc_cands.append({"key": k, "type": "accessory", "name": v["name"], "price": v["price"], "count": 1})
        self.dedicated_accessory_shop_stock = d_acc_cands[:SHOP_LIMIT_BONUS if bonus_mode else SHOP_LIMIT_NORMAL]

        # --- 2. 道具屋 (消耗品) --- ※従来通りランダム
        item_cands = []
        for k, v in CONSUMABLE_DATA.items():
            if v.get("shop_buyable", True) and is_rank_ok(v) and random.random() < get_shop_rate(v):
                item_cands.append({"key": k, "type": "consumable", "name": v["name"], "price": v["price"], "count": random.randint(1, 5)})
        
        # 最低在庫保証 (道具 3枠)
        if len(item_cands) < 3:
            all_items = [(k, v) for k, v in CONSUMABLE_DATA.items() if v.get("shop_buyable", True) and is_rank_ok(v)]
            if all_items:
                while len(item_cands) < 3:
                    k, v = random.choice(all_items)
                    item_cands.append({"key": k, "type": "consumable", "name": v["name"], "price": v["price"], "count": random.randint(1, 5)})
        self.item_shop_stock = item_cands[:SHOP_LIMIT_NORMAL]

        # --- 3. 魔法屋 (杖) --- ※従来通りランダム
        magic_cands = []
        for k, v in STAVE_DATA.items():
            if v.get("shop_buyable", True) and is_rank_ok(v) and random.random() < get_shop_rate(v):
                magic_cands.append({"key": k, "type": "stave", "name": v["name"], "price": v["price"], "count": 1})
        
        # 最低在庫保証 (杖 2枠)
        if len(magic_cands) < 2:
            all_staves = [(k, v) for k, v in STAVE_DATA.items() if v.get("shop_buyable", True) and is_rank_ok(v)]
            if all_staves:
                while len(magic_cands) < 2:
                    k, v = random.choice(all_staves)
                    magic_cands.append({"key": k, "type": "stave", "name": v["name"], "price": v["price"], "count": 1})
        self.magic_shop_stock = magic_cands[:SHOP_LIMIT_NORMAL]

    def spawn_traps(self, player):
        from constants import TRAP_SPAWN_MIN, TRAP_SPAWN_MAX, TRAP_SPAWN_SCALE_EVERY, TRAP_SPAWN_SCALE_ADD, TRAP_SPAWN_SCALE_LIMIT, TRAP_DATA
        from components.sprites.trap import Trap
        scale = (self.current_floor - 1) // TRAP_SPAWN_SCALE_EVERY * TRAP_SPAWN_SCALE_ADD
        max_traps = min(TRAP_SPAWN_SCALE_LIMIT, TRAP_SPAWN_MAX + scale)
        target_count = random.randint(TRAP_SPAWN_MIN, max_traps)
        px, py = int((player.x + player.width / 2) // self.tile_size), int((player.y + player.height / 2) // self.tile_size)
        trap_types = list(TRAP_DATA.keys())
        weights = [data["weight"] for data in TRAP_DATA.values()]
        placed_count = 0
        attempts = 0
        while placed_count < target_count and attempts < 100:
            attempts += 1
            if not self.room_rects: break
            rx, ry, rw, rh = random.choice(self.room_rects)
            tx, ty = random.randint(rx, rx + rw - 1), random.randint(ry, ry + rh - 1)
            if not (0 <= tx < self.map_width and 0 <= ty < self.map_height): continue
            if self.map_data[ty][tx] != 1 and self.map_data[ty][tx] not in [4, 5, 6]: continue
            if abs(tx - px) <= 2 and abs(ty - py) <= 2: continue
            if any(t.x == tx and t.y == ty for t in self.traps): continue
            t_type = random.choices(trap_types, weights=weights, k=1)[0]
            self.traps.append(Trap(tx, ty, t_type))
            placed_count += 1

    def trigger_shake(self, amount, duration):
        self.shake_amount = amount
        self.shake_timer = duration

    def update(self, dialog=None):
        """ダンジョン全体の更新（タイマーや演出）"""
        # アウトブレイク演出は check_outbreak_start で完結

        # 画面揺らしの更新
        if self.shake_timer > 0:
            self.shake_timer -= 1
            self.shake_offset = (random.randint(-self.shake_amount, self.shake_amount), random.randint(-self.shake_amount, self.shake_amount))
            if self.shake_timer <= 0:
                self.shake_amount = 0
                self.shake_offset = (0, 0)
        
        # --- [Logic Update Phase] ---
        
        # [NEW] フラッシュタイマーの更新
        if self.flash_timer > 0:
            self.flash_timer -= 1

        for effect in self.magic_effects[:]:
            effect.update()
            if effect.is_done():
                self.magic_effects.remove(effect)
        
        # [NEW] NPCのアニメーション更新
        for npc in self.npcs:
            npc.update_animation()

    def check_traps(self, player, dialog):
        if getattr(player, "is_moving", False): return self
        from systems.game_state import game_state, is_paused
        if is_paused() or game_state.get("dialog_just_closed"): return self
        
        px, py = int((player.x + player.width / 2) // self.tile_size), int((player.y + player.height / 2) // self.tile_size)
        for trap in self.traps[:]:
            if trap.x == px and trap.y == py and not trap.is_triggered:
                # ランクチェック (落とし穴の場合)
                if trap.type == "pitfall":
                    target_floor = self.current_floor + 1
                    guild = GuildSystem()
                    max_f = guild.get_max_floor(player.guild_rank)
                    
                    # 進行中の昇格クエストがあれば、その目標ランクの制限まで緩和する
                    # ※ただし、フライング防止のため、この緩和は最初のギルド加入試験（ランク "-" から F への昇格）のときのみ適用する。
                    for q in player.active_quests:
                        if q.get("is_rank_up"):
                            target_rank = q.get("next_rank")
                            if target_rank and player.guild_rank == "-":
                                exam_limit = guild.get_max_floor(target_rank)
                                max_f = max(max_f, exam_limit)

                    if target_floor > max_f:
                        req_rank = guild.get_required_rank_for_floor(target_floor)
                        if dialog:
                            dialog.text = Text.UI.RANK_LIMIT_REACHED.format(rank=req_rank)
                            dialog.is_active = True
                        
                        # 階段と同様に、一歩押し戻してメッセージがループするのを防ぐ
                        player.x, player.y = player.prev_x, player.prev_y
                        player.target_x, player.target_y = player.x, player.y
                        player.is_moving = False
                        return self

                msg = trap.trigger(player, self, dialog)
                print(f"[DUNGEON] Trap Triggered: type={trap.type}, msg={msg.split('\\n')[0]}")
                if dialog:
                    # すでにメッセージがある場合は改行して追加
                    if dialog.is_active:
                        dialog.text += "\n" + msg
                    else:
                        dialog.text = msg
                        dialog.is_active = True
                if trap.type == "mine":
                    self.traps.remove(trap)
                    self.trigger_shake(15, 30)
                elif trap.type == "pitfall":
                    self.trigger_shake(8, 20)
                    # 以前はここで即座に warp_to_floor していたが、
                    # Trap.trigger -> player.start_falling が呼ばれるので、
                    # Dungeon.update 側でタイマー終了を待ってから遷移するように変更
                    pass 
        return self

    def _pick_variant(self, variants, weights, x, y, seed_offset=0):
        """(x, y)座標と固定シードから決定論的にバリアントを選ぶ（2D配列不要）"""
        if not variants:
            return None
        if len(variants) == 1:
            return variants[0]
        h = self._variant_seed ^ (seed_offset * 0x9E3779B9) ^ (x * 0x6C62272E) ^ (y * 0xC2B2AE35)
        h = (h ^ (h >> 16)) * 0x45D9F3B
        h = (h ^ (h >> 16)) & 0xFFFFFFFF
        total = sum(weights)
        r = (h / 0xFFFFFFFF) * total
        cumulative = 0.0
        for v, w in zip(variants, weights):
            cumulative += w
            if r <= cumulative:
                return v
        return variants[-1]

    def draw(self, screen, camera_x, camera_y, player=None):
        # [SAFETY] クリーンアップ済みのダンジョンの場合は描画をスキップ
        if self.map_data is None:
            screen.fill((0, 0, 0))
            return

        sw, sh = screen.get_size()
        sx, ex = max(0, int(camera_x // self.tile_size)), min(self.map_width, int((camera_x + sw) // self.tile_size) + 1)
        sy, ey = max(0, int(camera_y // self.tile_size)), min(self.map_height, int((camera_y + sh) // self.tile_size) + 1)
        for y in range(sy, ey):
            for x in range(sx, ex):
                dx, dy = (x * self.tile_size) - camera_x, (y * self.tile_size) - camera_y
                tile = self.map_data[y][x]
                
                # [NEW] ゲート（頭上）はここでは地面だけ描画する
                if tile == TILE_GATE:
                    ov_key = getattr(self, '_wall_top_override', {}).get((x, y)) or self._pick_variant(self.available_wall_top_variants, self._top_weights, x, y, 2)
                    # 短縮名（wall_pass_0）を使って地面を取得
                    if ov_key in self.overhead_base_map:
                        fk = self.overhead_base_map[ov_key]
                    else:
                        fk = getattr(self, '_floor_override', {}).get((x, y)) or self._pick_variant(self.available_floor_variants, self._floor_weights, x, y, 0) or "floor"
                else:
                    fk = "wall_none"
                
                if tile > 0:
                    # 床、階段、通路
                    if tile == 2: fk = "stairs_up"
                    elif tile == 3: fk = "stairs_down"
                    elif 4 <= tile <= 6: fk = "corridor"
                    elif tile == TILE_GATE:
                        # すでに fk が設定されている（命名規則によるもの）場合はそのまま
                        pass
                    else: 
                        fk = getattr(self, '_floor_override', {}).get((x, y)) or self._pick_variant(self.available_floor_variants, self._floor_weights, x, y, 0) or "floor"
                else:
                    # 壁(ID 0)
                    wall_type = self._get_wall_texture_key(x, y)
                    if wall_type == "wall_top":
                        fk = getattr(self, '_wall_top_override', {}).get((x, y)) or self._pick_variant(self.available_wall_top_variants, self._top_weights, x, y, 2) or "wall_top"
                    elif wall_type == "wall_single":
                        fk = self.wall_variants.get((x, y)) or self._pick_variant(self.available_wall_variants, self._wall_weights, x, y, 4) or "wall_single"
                    else:
                        fk = getattr(self, '_wall_none_override', {}).get((x, y)) or self._pick_variant(self.available_wall_none_variants, self._none_weights, x, y, 3) or "wall_none"
                
                img = self.textures.get(fk, self.textures.get("wall_none"))
                if img:
                    # [NEW] 床系、または1マスの壁（壺や樽などの障害物）の場合はベースレイヤーを描画する
                    is_floor_type = (tile > 0)
                    is_obstacle = (tile == 0 and wall_type == "wall_single")
                    
                    if is_floor_type or is_obstacle:
                        # ベース床: overrideがあればそれを、なければハッシュから取得
                        base_fk = getattr(self, '_floor_override', {}).get((x, y)) or self._pick_variant(self.available_floor_variants, self._floor_weights, x, y, 1) or "floor"
                        base_img = self.textures.get(base_fk)
                        # 今描画しようとしているタイル自体が「床系(available_floor_variants)」でない場合のみ、
                        # 背景としてベース床を敷く（これで模様の混ざりを防ぐ）
                        if base_img and base_fk != fk and fk not in self.available_floor_variants:
                             screen.blit(base_img, (dx, dy))
                    
                    screen.blit(img, (dx, dy))
                    
                    # [NEW] 壁の装飾を描画
                    dec_key = self.wall_decoration_variants[y][x]
                    if dec_key and dec_key in self.textures:
                        dec_img = self.textures[dec_key]
                        if self.wall_decoration_flips[y][x]:
                            dec_img = pygame.transform.flip(dec_img, True, False)
                        screen.blit(dec_img, (dx, dy))
        for e in self.edges:
            dx, dy = (e["x"] * self.tile_size) + e["ox"] - camera_x, (e["y"] * self.tile_size) + e["oy"] - camera_y
            if -self.tile_size <= dx <= sw and -self.tile_size <= dy <= sh: screen.blit(e["img"], (dx, dy))
        for t in self.traps: t.draw(screen, camera_x, camera_y, self.tile_size, player=player, dungeon=self)
        for i in self.dropped_items: i.draw(screen, camera_x, camera_y)
        for n in self.npcs:
            if camera_x - n.width <= n.x <= camera_x + sw and camera_y - n.height <= n.y <= camera_y + sh: n.draw(screen, camera_x, camera_y, player)
        
        # マジックエフェクトを最前面（UI除く）に描画
        for f in self.magic_effects: f.draw(screen, camera_x, camera_y)
        
        # デバッグ: 氾濫トリガー位置の可視化（スイッチが配置されるので不要）
        pass

        # [NEW] フラッシュ（クリティカル演出）の描画
        if self.flash_timer > 0:
            # 最初の数フレームは真っ白、徐々に透明にする
            alpha = min(255, self.flash_timer * 30)
            flash_surf = pygame.Surface((sw, sh))
            flash_surf.fill((255, 255, 255))
            flash_surf.set_alpha(alpha)
            screen.blit(flash_surf, (0, 0))
        for e in self.enemies:
            e.current_dungeon = self
            if camera_x - e.width <= e.x <= camera_x + sw and camera_y - e.height <= e.y <= camera_y + sh: e.draw(screen, camera_x, camera_y)

    def get_current_floor_level(self): return self.current_floor

    def handle_respawn_turn(self, player):
        """1ターン経過時のリスポーン判定（ターン制ベース）"""
        if self.current_floor == 0: return
        
        import math
        self.turns_since_last_respawn += 1
        
        # 1階層ごとに SCALE_SUB 分だけ短縮
        scale = (self.current_floor - 1) * ENEMY_RESPAWN_SCALE_SUB
        
        # インターバルを計算（最短下限値を考慮しつつ、小数点以下切り上げ）
        interval = math.ceil(max(ENEMY_RESPAWN_MIN_INTERVAL, ENEMY_RESPAWN_INTERVAL - scale))
        
        if self.turns_since_last_respawn >= interval:
            self.turns_since_last_respawn = 0
            # フロア全体の敵上限チェック
            total_cap = len(self.rooms) * ENEMY_TOTAL_MAX
            if len(self.enemies) < total_cap:
                Enemy.spawn_one(self, player)

    def reveal_area(self, center_x, center_y, radius=2):
        """指定された座標の周囲を探索済みにする"""
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx, ny = center_x + dx, center_y + dy
                if 0 <= nx < self.map_width and 0 <= ny < self.map_height:
                    self.revealed_tiles[ny][nx] = True

        # もし部屋の中にいるなら、その部屋全体を探索済みにする
        for rx, ry, rw, rh in self.room_rects:
            if rx <= center_x < rx + rw and ry <= center_y < ry + rh:
                for row in range(ry, min(ry + rh, self.map_height)):
                    for col in range(rx, min(rx + rw, self.map_width)):
                        self.revealed_tiles[row][col] = True

    def reveal_all_tiles(self):
        """フロア全体のタイルをすべて探索済みにする（燈の杖などの効果用）"""
        for y in range(self.map_height):
            for x in range(self.map_width):
                self.revealed_tiles[y][x] = True

    def check_stairs(self, player, confirm_dialog, dialog=None):
        if self.next_dungeon: return self.next_dungeon
        from systems.game_state import game_state
        if is_paused() or game_state.get("dialog_just_closed"): return self

        def _block_stair(message):
            if dialog and not dialog.is_active:
                dialog.text = message
                dialog.is_active = True
            player.x, player.y = player.prev_x, player.prev_y
            player.target_x, player.target_y = player.x, player.y
            player.is_moving = False
            self.spawn_pos = (tx, ty)
            return self

        tx, ty = int((player.x + player.width / 2) // self.tile_size), int((player.y + player.height / 2) // self.tile_size)
        
        # ワープ直後の地点にいる場合は、そのタイルから完全に出るまで反応させない
        if hasattr(self, "spawn_pos") and self.spawn_pos == (tx, ty):
            return self
        else:
            # 一度でもそのタイルから出たら制限解除
            self.spawn_pos = (-1, -1)

        if not (0 <= tx < self.map_width and 0 <= ty < self.map_height): return self
        ct = self.map_data[ty][tx]

        # ラスボス戦中は、階段タイルに触れた時だけ封鎖する。
        if ct in (2, 3):
            if getattr(player, "guild_rank", None) == "SS":
                return _block_stair("SSランク中は 階段を 使えない！")
            boss_in_battle = any(
                getattr(enemy, "type", None) == "dungeon_core" and not getattr(enemy, "is_dead", False)
                for enemy in getattr(self, "enemies", [])
            )
            if boss_in_battle and (game_state.get("is_boss_battle", False) or game_state.get("boss_encounter_pending", False)):
                return _block_stair("ラスボス戦中は 階段を 使えない！")

        # --- モンスターブレイクアウト時の進入元階段の封鎖 ---
        if ct in (2, 3):
            if self.is_outbreak and not self.outbreak_cleared and self.entry_stairs == ct:
                return _block_stair(Text.System.OUTBREAK_BLOCKED)

        if ct == 3:
            # --- ランク制限チェック ---
            target_floor = self.current_floor + 1
            guild = GuildSystem()
            max_f = guild.get_max_floor(player.guild_rank)
            
            # 進行中の昇格クエストがあれば、その目標ランクの制限まで緩和する
            # ※ただし、フライング防止のため、この緩和は最初のギルド加入試験（ランク "-" から F への昇格）のときのみ適用する。
            for q in player.active_quests:
                if q.get("is_rank_up"):
                    target_rank = q.get("next_rank")
                    if target_rank and player.guild_rank == "-":
                        exam_limit = guild.get_max_floor(target_rank)
                        max_f = max(max_f, exam_limit)
            
            # [SPECIAL] ギルド未加入(-)かつ昇格試験も受けていない場合、B1Fへの進入を拒否する
            if player.guild_rank == "-" and max_f == 0 and target_floor == 1:
                if dialog:
                    dialog.text = Text.UI.GUILD_NO_ENTRY
                    dialog.is_active = True
                player.x, player.y = player.prev_x, player.prev_y
                player.target_x, player.target_y = player.x, player.y
                return self
                
            if target_floor > max_f:
                if dialog and not dialog.is_active:
                    req_rank = guild.get_required_rank_for_floor(target_floor)
                    dialog.text = Text.UI.RANK_LIMIT_REACHED.format(rank=req_rank)
                    dialog.is_active = True
                
                # 階段の上で止まらないように一歩押し戻す
                player.x, player.y = player.prev_x, player.prev_y
                player.target_x, player.target_y = player.x, player.y
                return self

            confirm_dialog.text = Text.UI.CONFIRM_DUNGEON_START if self.current_floor == 0 else Text.UI.CONFIRM_GO_DEEPER
            confirm_dialog.on_yes = lambda: setattr(self, "next_dungeon", warp_to_floor(self.current_floor + 1, player, debug_overflow=self.debug_overflow, old_dungeon=self))
            def on_no():
                # 元の仕様通り、一歩押し戻す
                player.x, player.y = player.prev_x, player.prev_y
                player.target_x, player.target_y = player.x, player.y
                player.is_moving = False
                # かつ、そのマスから出るまで再判定しない
                self.spawn_pos = (tx, ty)
            confirm_dialog.on_no = on_no
            confirm_dialog.is_active = True
        elif ct == 2 and self.current_floor >= 1:
            confirm_dialog.text = Text.UI.CONFIRM_RETURN_VILLAGE if self.current_floor == 1 else Text.UI.CONFIRM_GO_UPPER
            confirm_dialog.on_yes = lambda: setattr(self, "next_dungeon", warp_to_floor(self.current_floor - 1, player, debug_overflow=self.debug_overflow, spawn_reason="return" if self.current_floor == 1 else "normal", old_dungeon=self))
            def on_no_upper():
                player.x, player.y = player.prev_x, player.prev_y
                player.target_x, player.target_y = player.x, player.y
                player.is_moving = False
                self.spawn_pos = (tx, ty)
            confirm_dialog.on_no = on_no_upper
            confirm_dialog.is_active = True
        return self

    def _adjust_wall_rendering_logic(self):
        """描画直前にマップデータを微調整します（既存の描画ロジックは弄らない）。"""
        for y in range(1, self.map_height - 1):
            for x in range(1, self.map_width - 1):
                if self.map_data[y][x] == 0:
                    # 周囲4方向の状態を確認
                    f_u = (self.map_data[y-1][x] > 0)
                    f_d = (self.map_data[y+1][x] > 0)
                    f_l = (self.map_data[y][x-1] > 0)
                    f_r = (self.map_data[y][x+1] > 0)
                    
                    floor_count = sum([f_u, f_d, f_l, f_r])
                    
                    if floor_count == 3:
                        # 例外：上が壁で、他の3方向が床の場合のみ「壁」として残す
                        # （_get_wall_texture_key が統合されたため、そのまま wall_top として描画される）
                        if not f_u and f_d and f_l and f_r:
                            continue
                        # それ以外の「3方向が床」の壁は床に置換
                        if self.current_floor != 0:
                            self.map_data[y][x] = 1

    def _add_wall_decorations(self):
        """北側の壁にランダムに装飾を配置します。"""
        if not self.available_wall_decoration_variants: return
        
        ratio = self.floor_info.get("wall_decoration_ratio", 0.3)
        
        for y in range(self.map_height - 1):
            for x in range(self.map_width):
                # 北側の壁（＝下が床）にのみ配置
                if self.is_nw(x, y):
                    if random.random() < ratio:
                        self.wall_decoration_variants[y][x] = random.choice(self.available_wall_decoration_variants)
    def draw_overhead(self, screen, camera_x, camera_y):
        """プレイヤーの上に重なるタイル（ゲートなど）を描画する"""
        sw, sh = screen.get_size()
        sx, ex = max(0, int(camera_x // self.tile_size)), min(self.map_width, int((camera_x + sw) // self.tile_size) + 1)
        sy, ey = max(0, int(camera_y // self.tile_size)), min(self.map_height, int((camera_y + sh) // self.tile_size) + 1)
        
        for y in range(sy, ey):
            for x in range(sx, ex):
                if self.map_data[y][x] == TILE_GATE:
                    dx, dy = (x * self.tile_size) - camera_x, (y * self.tile_size) - camera_y
                    ov_key = getattr(self, '_wall_top_override', {}).get((x, y)) or self._pick_variant(self.available_wall_top_variants, self._top_weights, x, y, 2) or "wall_top"
                    # フルキーを取得して描画
                    full_key = self.short_to_full_key.get(ov_key, ov_key)
                    if full_key in self.textures:
                        screen.blit(self.textures[full_key], (dx, dy))
