import pygame
import sys
import os
import random
import traceback

# [NEW] セーブファイルの分離などを有効化（他のモジュールが読み込まれる前に設定）
os.environ["DEBUG_MODE"] = "1"

# プロジェクトのルートをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from constants import *
from components.sprites.player import Player, EquipInstance
from components.sprites.enemy import Enemy
from systems.dungeon import warp_to_floor
from systems.scene_handler import handle_game, handle_ending, handle_opening
from systems.session_handler import init_ui_elements, setup_ui_relations
from systems.resources import font_small, font_medium
from systems.events import handle_events, active_direction_keys

# show_menu is removed. Starting main directly.

def setup_gungeon_mode(dungeon, player):
    """テクスチャ・アイテム確認用の特殊フロア設定"""
    theme_name = dungeon.floor_info.get("image", "unknown")
    print(f"[Debug] Gungeon Mode: Floor {dungeon.current_floor}, Theme: {theme_name}")
    
    try:
        # 正方形の部屋(12x12)に作り変える
        w, h = 12, 12
        dungeon.map_width = w + 4
        dungeon.map_height = h + 4
        dungeon.map_data = [[0 for _ in range(dungeon.map_width)] for _ in range(dungeon.map_height)]
        # [FIX] 探索フラグを新しいサイズに合わせて再構築
        dungeon.revealed_tiles = [[False for _ in range(dungeon.map_width)] for _ in range(dungeon.map_height)]
        
        # 中央に部屋を作成
        for y in range(2, h + 2):
            for x in range(2, w + 2):
                dungeon.map_data[y][x] = 1 # 床
        
        # テクスチャが存在しないバリアントを除去
        def get_valid_variants(variants):
            return [v for v in variants if v in dungeon.textures]

        floor_vars = get_valid_variants(dungeon.available_floor_variants)
        if not floor_vars: floor_vars = ["floor"]
        top_vars = get_valid_variants(dungeon.available_wall_top_variants)
        if not top_vars: top_vars = ["wall_top"]
        none_vars = get_valid_variants(dungeon.available_wall_none_variants)
        if not none_vars: none_vars = ["wall_none"]

        dungeon.floor_variants = [[random.choice(floor_vars) for _ in range(dungeon.map_width)] for _ in range(dungeon.map_height)]
        dungeon.base_floor_variants = [[random.choice(floor_vars) for _ in range(dungeon.map_width)] for _ in range(dungeon.map_height)]
        dungeon.wall_top_variants = [[random.choice(top_vars) for _ in range(dungeon.map_width)] for _ in range(dungeon.map_height)]
        dungeon.wall_variants = [[random.choice(top_vars) for _ in range(dungeon.map_width)] for _ in range(dungeon.map_height)]
        dungeon.wall_none_variants = [[random.choice(none_vars) for _ in range(dungeon.map_width)] for _ in range(dungeon.map_height)]
        dungeon.wall_decoration_variants = [["" for _ in range(dungeon.map_width)] for _ in range(dungeon.map_height)]

        # 階段(上りと下り)
        dungeon.map_data[2][2] = 2 
        dungeon.map_data[2][3] = 3 
        
        ts = getattr(dungeon, 'tile_size', TILE_SIZE)
        player.x = (w // 2 + 2) * ts
        player.y = (h // 2 + 2) * ts
        player.prev_x, player.prev_y = player.x, player.y
        player.target_x, player.target_y = player.x, player.y
        
        dungeon.enemies = []
        dungeon.dropped_items = [] # Dungeon.draw が見ているのは dropped_items
        
        from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, CONSUMABLE_DATA, STAVE_DATA
        from components.sprites.item import DroppedWeapon, DroppedConsumable, DroppedArmor, DroppedShield, DroppedStave
        
        floor_tiles = [(c, r) for r in range(3, h + 2) for c in range(2, w + 2) if dungeon.map_data[r][c] == 1]
        random.shuffle(floor_tiles)

        # [NEW] 出現可能なアイテムをリストアップ
        candidates = []
        # アイテムカタログをスキャン
        for ctype, catalog in [("weapon", WEAPON_DATA), ("armor", ARMOR_DATA), 
                               ("shield", SHIELD_DATA), ("item", CONSUMABLE_DATA), ("stave", STAVE_DATA)]:
            for k, it in catalog.items():
                # 階層チェックを優先 (Floor制限があるアイテムのみ)
                min_f = it.get("min_floor", 1)
                max_f = it.get("max_floor", 999)
                if not (min_f <= dungeon.current_floor <= max_f):
                    continue
                
                # ランクチェック
                from constants import RANK_ORDER
                p_rank_idx = RANK_ORDER.index(player.guild_rank) if player.guild_rank in RANK_ORDER else 0
                
                item_rank = it.get("min_rank", "F")
                if item_rank in RANK_ORDER:
                    i_rank_idx = RANK_ORDER.index(item_rank)
                else:
                    i_rank_idx = 0 # 未知のランク（Gなど）はFランク扱いにする
                
                # デバッグモードでは、現在のランクより少し上のものまでテストで見れるようにする
                if i_rank_idx > p_rank_idx + 1: 
                    continue

                # 価格設定なし or shop_buyable: false でも、ドロップ品なら出す
                candidates.append((ctype, k))
        
        print(f"[Debug] Found {len(candidates)} spawnable items for Floor {dungeon.current_floor}")

        # アイテムの配置
        dungeon.dropped_items = []
        for i, cand in enumerate(candidates):
            if i >= len(floor_tiles): break
            tx, ty = floor_tiles[i]
            ctype, ckey = cand
            try:
                if ctype == "weapon": it = DroppedWeapon(tx * ts, ty * ts, ckey, WEAPON_DATA[ckey])
                elif ctype == "armor": it = DroppedArmor(tx * ts, ty * ts, ckey, ARMOR_DATA[ckey])
                elif ctype == "shield": it = DroppedShield(tx * ts, ty * ts, ckey, SHIELD_DATA[ckey])
                elif ctype == "item": it = DroppedConsumable(tx * ts, ty * ts, ckey, CONSUMABLE_DATA[ckey])
                elif ctype == "stave": it = DroppedStave(tx * ts, ty * ts, ckey, STAVE_DATA[ckey])
                dungeon.dropped_items.append(it)
            except Exception as e:
                print(f"[Debug Error] Failed to spawn {ckey}: {e}")
        
        # トラップの配置 (全種類)
        from components.sprites.trap import Trap
        dungeon.traps = []
        trap_start_idx = len(candidates)
        trap_keys = [k for k in TRAP_DATA.keys() if k != "flood_switch"]
        for i, trap_key in enumerate(trap_keys):
            if trap_start_idx + i >= len(floor_tiles): break
            tx, ty = floor_tiles[trap_start_idx + i]
            trap = Trap(tx, ty, trap_key)
            trap.is_revealed = True
            dungeon.traps.append(trap)
        
        # モンスターの配置 (現在のフロアに出現可能な全種類を最低1体ずつ)
        from components.sprites.enemy import Enemy
        from constants import ENEMY_DATA
        floor = dungeon.current_floor
        valid_enemy_types = []
        
        for e_type, e_data in ENEMY_DATA.items():
            min_f = e_data.get("min_floor", 1)
            max_f = e_data.get("max_floor", 999)
            # ボスフラグがある場合は、その指定階層にのみ出す
            if e_data.get("is_boss") and floor != min_f:
                continue
            if min_f <= floor <= max_f:
                valid_enemy_types.append(e_type)
        
        dungeon.enemies = []
        # アイテム・トラップの後ろに並べる
        current_tile_idx = trap_start_idx + len(trap_keys)
        for e_type in valid_enemy_types:
            spawn_count = 1
            # クエスト対象なら必要数分出す
            if getattr(dungeon, "is_quest_qa", False):
                for q in player.active_quests:
                    if q.get("type") == "hunt" and q.get("target_key") == e_type:
                        spawn_count = max(spawn_count, q.get("amount", 1))
            
            for _ in range(spawn_count):
                if current_tile_idx >= len(floor_tiles): break
                tx, ty = floor_tiles[current_tile_idx]
                en = Enemy(tx * ts, ty * ts, e_type)
                en.target_x, en.target_y = en.x, en.y
                dungeon.enemies.append(en)
                current_tile_idx += 1
            
            if current_tile_idx >= len(floor_tiles): break
            
        dungeon._add_floor_edges()
        dungeon.reveal_floor()
        dungeon.is_lighted = True
        
        # [NEW] ギルドNPCの配置（Quest QAをさらに快適に）
        from components.sprites.npc import NPC
        dungeon.npcs = [
            NPC("ギルド受付", 2 * ts, 2 * ts, sprite_type="guild_receptionist", image_path="components/pictures/npc/girl_town_v")
        ]
        
        print(f"[Debug] Gungeon Mode Ready. MapSize:{dungeon.map_width}x{dungeon.map_height}")
        return dungeon
    except Exception as e:
        print(f"[Error] setup_gungeon_mode: {e}")
        traceback.print_exc()
        return dungeon

def draw_debug_overlay(screen, dungeon, player):
    info_lines = [
        f"ULTIMATE DEBUG MODE - Floor: {dungeon.current_floor}",
        f"Rank: {player.guild_rank} (GP: {player.guild_point})",
        "[N/B] : Warp Next/Prev Floor | [Shift]+ : Jump 10F",
        "[G] : God Mode (Invincibility + Atk x100)",
        "[H] : Heal HP | [K] : Kill All Enemies",
        "[PageUp/Dn] : Adjust GP (+/-100)",
        "[. / ,] : Rank UP / DOWN"
    ]
    
    # 受注中クエストの表示
    if player.active_quests:
        info_lines.append("Active Quests:")
        for q in player.active_quests:
            info_lines.append(f" - {q['title']} ({q['type']})")

    # 表示位置の計算
    y_offset = SCREEN_HEIGHT - (len(info_lines) * 30 + 30)
    for line in info_lines:
        c = (255, 255, 255)
        if "[ACTIVE]" in line: c = (255, 255, 100)
        
        text_surf = font_small.render(line, True, c)
        bg_rect = text_surf.get_rect(topleft=(20, y_offset))
        
        # 半透明の背景を作成
        bg_surf = pygame.Surface((bg_rect.width + 10, bg_rect.height + 4), pygame.SRCALPHA)
        bg_surf.fill((0, 0, 0, 160))
        screen.blit(bg_surf, (bg_rect.x - 5, bg_rect.y - 2))
        
        screen.blit(text_surf, (20, y_offset))
        y_offset += 30

def main():
    """最強デバッグツール：メニューを廃止し、最初から全機能を有効にして起動する"""
    try:
        pygame.init()
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("ULTIMATE DEBUG TOOL")

        # 1. プレイヤーの初期化
        player = Player()
        player.is_debug = True
        player.attack = 50
        player.hp = 200
        player.max_hp = 200
        player.guild_point = 1000
        player.guild_rank = "F"

        # 2. ダンジョンの初期化 (1階から開始)
        dungeon = warp_to_floor(1, player)
        
        # デバッグ用設定の強制有効化
        dungeon.is_combat_qa = True
        dungeon.is_quest_qa = True
        dungeon = setup_gungeon_mode(dungeon, player)
        
        ui_elements = init_ui_elements(SCREEN_WIDTH, SCREEN_HEIGHT)
        from systems.game_state import game_state
        game_state.update({"dialog_modal": False, "current_scene": "game", "is_debug_mode": True})
        setup_ui_relations(ui_elements, player, dungeon, game_state)

        clock = pygame.time.Clock()
        running = True

        while running:
            dt = clock.tick(60) / 1000.0 # [NEW] Delta Time calculation
            success, events = handle_events()
            if not success: running = False
            
            # --- デバッグ用チートキー ---
            for event in events:
                if event.type == pygame.KEYDOWN:
                    mods = pygame.key.get_mods()
                    # 階層ワープ
                    change = 0
                    if event.key == pygame.K_n: change = 10 if (mods & pygame.KMOD_SHIFT) else 1
                    elif event.key == pygame.K_b: change = -(10 if (mods & pygame.KMOD_SHIFT) else 1)
                    
                    if change != 0:
                        new_floor = max(0, dungeon.current_floor + change)
                        dungeon = warp_to_floor(new_floor, player, spawn_reason="debug")
                        dungeon.is_combat_qa = True
                        dungeon.is_quest_qa = True
                        dungeon = setup_gungeon_mode(dungeon, player)
                        setup_ui_relations(ui_elements, player, dungeon, game_state)
                        print(f"[DEBUG] Warp to Floor {new_floor}")
                    
                    # 各種チート
                    elif event.key == pygame.K_h: # Heal
                        player.hp = player.max_hp
                        print("[DEBUG] Player Healed!")
                    elif event.key == pygame.K_g: # God Mode
                        player.is_god = not getattr(player, "is_god", False)
                        if player.is_god: player.attack *= 100
                        else: player.attack //= 100
                        print(f"[DEBUG] God Mode: {'ON' if player.is_god else 'OFF'}")
                    elif event.key == pygame.K_k: # Kill All
                        count = len(dungeon.enemies)
                        dungeon.enemies = []
                        print(f"[DEBUG] Annihilated {count} enemies!")
                    
                    # 進捗調整
                    elif event.key == pygame.K_PAGEUP:
                        player.guild_point += 100
                        print(f"[DEBUG] GP increased to {player.guild_point}")
                    elif event.key == pygame.K_PAGEDOWN:
                        player.guild_point = max(0, player.guild_point - 100)
                        print(f"[DEBUG] GP decreased to {player.guild_point}")
                    elif event.key == pygame.K_PERIOD:
                        ranks = ["F", "E", "D", "C", "B", "A", "S"]
                        idx = ranks.index(player.guild_rank) if player.guild_rank in ranks else 0
                        if idx < len(ranks) - 1:
                            player.guild_rank = ranks[idx + 1]
                            print(f"[DEBUG] Rank UP: {player.guild_rank}")
                            dungeon = setup_gungeon_mode(dungeon, player) # クエスト候補更新のため
                    elif event.key == pygame.K_COMMA:
                        ranks = ["F", "E", "D", "C", "B", "A", "S"]
                        idx = ranks.index(player.guild_rank) if player.guild_rank in ranks else 0
                        if idx > 0:
                            player.guild_rank = ranks[idx - 1]
                        print(f"[DEBUG] Rank DOWN: {player.guild_rank}")
                        dungeon = setup_gungeon_mode(dungeon, player)
                    elif event.key == pygame.K_o:
                        dungeon.debug_overflow = True
                        print(f"[DEBUG] Outbreak Reserved for Next Floor. Go to the stairs!")

            # 常に全表示
            dungeon.is_lighted = True
            
            scene = game_state.get("current_scene", "game")
            
            if scene == "game":
                guild_was_active = ui_elements["guild_dialog"].is_active
                dungeon = handle_game(screen, events, player, dungeon, ui_elements, game_state, dt=dt)
                
                # ギルドメニューが閉じられたらマップを最新化（クエスト対象反映のため）
                if guild_was_active and not ui_elements["guild_dialog"].is_active:
                    dungeon = setup_gungeon_mode(dungeon, player)
                
                draw_debug_overlay(screen, dungeon, player)
            elif scene == "ending":
                from systems.resources import ending_imgs, story_data
                handle_ending(screen, events, game_state, ending_imgs, ui_elements, story_data)
            elif scene == "opening":
                from systems.resources import opening_imgs, story_data
                def dummy_start(): pass
                handle_opening(screen, events, game_state, opening_imgs, dummy_start, ui_elements, story_data)

            pygame.display.flip()
            # clock.tick(60) is moved to the top of the loop to calculate dt

    except Exception as e:
        print(f"[Fatal Error] {e}")
        traceback.print_exc()
        input("Press Enter to exit...")
    pygame.quit()

if __name__ == "__main__":
    main()
