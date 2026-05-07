import pygame
import sys
import os
import random
import traceback

# プロジェクトのルートをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from constants import *
from components.sprites.player import Player, EquipInstance
from components.sprites.enemy import Enemy
from systems.dungeon import warp_to_floor
from systems.scene_handler import handle_game
from systems.session_handler import init_ui_elements, setup_ui_relations
from systems.resources import font_small, font_medium
from systems.events import handle_events, active_direction_keys

def show_menu(screen):
    print("[Debug] Showing Menu...")
    running = True
    selected = 0
    options = [
        "1. Monster Overflow Test (Start 1F, Forced 5F)",
        "2. Enemy Equipment / Combat Test (Spawn + Equip)",
        "3. Dungeon Texture / Item Drop Test (Gungeon 4F)",
        "4. Guild / Quest Debug (High GP)",
        "5. Combat QA Mode (Normal Stats)",
        "6. Quest QA Mode (Rank/GP Control)",
        "EXIT (ESC)"
    ]
    
    while running:
        screen.fill((30, 30, 30))
        for i, option in enumerate(options):
            color = (255, 255, 255) if i == selected else (100, 100, 100)
            text = font_medium.render(option, True, color)
            screen.blit(text, (100, 150 + i * 50))
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return None, False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP: selected = (selected - 1) % len(options)
                elif event.key == pygame.K_DOWN: selected = (selected + 1) % len(options)
                elif event.key == pygame.K_ESCAPE: return None, False
                elif event.key in [pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE]:
                    if selected == 0: return 1, False
                    if selected == 1: return 1, False
                    if selected == 2: return 4, True
                    if selected == 3: return 0, False
                    if selected == 4: return 1, "COMBAT_QA"
                    if selected == 5: return 1, "QUEST_QA"
                    if selected == 6: return None, False
    return None, False

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

        # 階段(目印)
        dungeon.map_data[3][3] = 2 
        dungeon.map_data[3][4] = 3 
        
        dungeon.edges = []
        ts = getattr(dungeon, 'tile_size', TILE_SIZE)
        player.x = (w // 2 + 2) * ts
        player.y = (h // 2 + 2) * ts
        player.prev_x, player.prev_y = player.x, player.y
        player.target_x, player.target_y = player.x, player.y
        
        dungeon.enemies = []
        dungeon.dropped_items = [] # Dungeon.draw が見ているのは dropped_items
        
        from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, CONSUMABLE_DATA, STAVE_DATA
        from components.sprites.item import DroppedWeapon, DroppedConsumable, DroppedArmor, DroppedShield, DroppedStave
        
        candidates = []
        # [NEW] 全アイテムをテスト用にリストアップ
        for catalog, itype in [(CONSUMABLE_DATA, "consumable"), (WEAPON_DATA, "weapon"), 
                               (ARMOR_DATA, "armor"), (SHIELD_DATA, "shield"), (STAVE_DATA, "stave")]:
            for tkey, tdata in catalog.items():
                if tdata.get("min_rank") != "S": # Sランク(特殊)以外を全て並べる
                    candidates.append((tkey, itype, tdata))

        # [NEW] クエスト対象の強制追加 (Quest QAモード時)
        if getattr(dungeon, "is_quest_qa", False):
            for q in player.active_quests:
                tkey = q.get("target_key")
                qtype = q.get("type")
                if qtype == "hunt":
                    # モンスター配置が必要なことをフラグで持っておく（後述のモンスター配置ブロックで利用）
                    pass
                elif qtype == "delivery":
                    # アイテムを candidates の先頭に追加
                    for catalog, itype in [(CONSUMABLE_DATA, "consumable"), (WEAPON_DATA, "weapon"), 
                                           (ARMOR_DATA, "armor"), (SHIELD_DATA, "shield"), (STAVE_DATA, "stave")]:
                        if tkey in catalog:
                            candidates.insert(0, (tkey, itype, catalog[tkey]))
                            break

        floor_tiles = [(c, r) for r in range(2, h + 2) for c in range(2, w + 2) if dungeon.map_data[r][c] == 1]
        random.shuffle(floor_tiles)
        
        # アイテムの配置
        for i, (key, itype, data) in enumerate(candidates):
            if i >= len(floor_tiles): break
            tx, ty = floor_tiles[i]
            px, py = tx * ts, ty * ts
            if itype == "weapon": item = DroppedWeapon(px, py, key, data)
            elif itype == "armor": item = DroppedArmor(px, py, key, data)
            elif itype == "shield": item = DroppedShield(px, py, key, data)
            elif itype == "stave": item = DroppedStave(px, py, key, data)
            else: item = DroppedConsumable(px, py, key, data)
            dungeon.dropped_items.append(item)
            
        # 罠の配置
        from constants import TRAP_DATA
        from components.sprites.trap import Trap
        dungeon.traps = []
        # アイテムの後ろに並べる
        trap_start_idx = len(candidates)
        trap_keys = [k for k in TRAP_DATA.keys() if k != "flood_switch"]
        for i, trap_key in enumerate(trap_keys):
            if trap_start_idx + i >= len(floor_tiles): break
            tx, ty = floor_tiles[trap_start_idx + i]
            trap = Trap(tx, ty, trap_key)
            trap.is_revealed = True # デバッグ時は最初から見えるように
            dungeon.traps.append(trap)
        
        # モンスターの配置 (COMBAT_QA または QUEST_QA モード時)
        if getattr(dungeon, "is_combat_qa", False) or getattr(dungeon, "is_quest_qa", False):
            from components.sprites.enemy import Enemy
            from constants import ENEMY_DATA
            floor = dungeon.current_floor
            valid_enemy_types = []
            
            # クエスト討伐対象を優先追加
            if getattr(dungeon, "is_quest_qa", False):
                for q in player.active_quests:
                    if q.get("type") == "hunt":
                        tkey = q.get("target_key")
                        if tkey in ENEMY_DATA and tkey not in valid_enemy_types:
                            valid_enemy_types.append(tkey)

            for e_type, e_data in ENEMY_DATA.items():
                min_f = e_data.get("min_floor", 1)
                max_f = e_data.get("max_floor", 999)
                if min_f <= floor <= max_f:
                    if e_type not in valid_enemy_types:
                        valid_enemy_types.append(e_type)
            
            dungeon.enemies = []
            # アイテムがない分、最初から並べる
            current_tile_idx = 0
            for e_type in valid_enemy_types:
                # クエスト対象なら必要数分出す
                spawn_count = 1
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
            print(f"[Debug] Spawned {len(dungeon.enemies)} types of enemies for Floor {floor}")

        dungeon._add_floor_edges() # 影を再生成
        dungeon.reveal_floor()
        dungeon.is_lighted = True
        
        # [NEW] ギルドNPCの配置（Quest QAをさらに快適に）
        from components.sprites.npc import NPC
        dungeon.npcs = [
            NPC("ギルドマスター", 2 * ts, 2 * ts, sprite_type="guild_master", image_path="components/pictures/npc/guild_master")
        ]
        
        print(f"[Debug] Gungeon Mode Ready. MapSize:{dungeon.map_width}x{dungeon.map_height}")
        return dungeon
    except Exception as e:
        print(f"[Error] {e}")
        traceback.print_exc()
        return dungeon

def setup_god_mode(player):
    """クエストQA用などの最強プレイヤー設定（死なないようにするため）"""
    player.attack = 999
    player.defense = 999
    player.hp = 999
    player.max_hp = 999
    type(player).eva_bonus = property(lambda self: 0)

def setup_combat_qa_mode(player, dungeon):
    """戦闘QA用のフラグ設定（ステータスは通常通り）"""
    dungeon.is_combat_qa = True
    print("[Debug] Combat QA Mode: Normal player stats for real combat testing.")

def draw_debug_overlay(screen, dungeon, player):
    """デバッグ用の操作ガイドを画面に表示"""
    mode_str = "NORMAL"
    if getattr(dungeon, "is_quest_qa", False): mode_str = "QUEST QA"
    elif getattr(dungeon, "is_combat_qa", False): mode_str = "COMBAT QA"
    
    info_lines = [
        f"DEBUG MODE: {mode_str} - Floor: {dungeon.current_floor}",
        f"Rank: {player.guild_rank} (GP: {player.guild_point})",
        "[N] or [+/-] : Floor (1F) | [Shift] N/+/- : Jump 10F",
        "[/] or [.] : Rank Up | [,] : Rank Down",
        "[PgUp/Dn] : Adjust GP (+/-50)",
        "[K] : Cycle Quest Catalog | [L] : Accept/Cancel Quest"
    ]
    
    # クエストプレビュー（カタログ選択）の表示
    if getattr(dungeon, "is_quest_qa", False):
        from constants import load_master_data
        quests_data = load_master_data("quests.yml")
        fixed_quests = quests_data.get("FIXED_QUESTS", [])
        q_idx = getattr(player, "debug_quest_idx", 0)
        if fixed_quests:
            q = fixed_quests[q_idx % len(fixed_quests)]
            # 受注条件チェック
            from constants import RANK_ORDER
            try:
                rank_val = RANK_ORDER.index(player.guild_rank)
                min_rank_val = RANK_ORDER.index(q.get("min_rank", "F"))
                max_rank_val = RANK_ORDER.index(q.get("max_rank", "SS"))
                can_accept = (min_rank_val <= rank_val <= max_rank_val)
            except ValueError:
                can_accept = False
            
            status = "AVAILABLE" if can_accept else "RANK LOCKED"
            
            is_active = any(aq["id"] == q["id"] for aq in player.active_quests)
            active_mark = "[ACTIVE] " if is_active else ""
            
            info_lines.append(f"Catalog: {active_mark}{q['title']}")
            info_lines.append(f" -> {status} (Min:{q['min_rank']} Max:{q['max_rank']})")

    # 受注中クエストの表示
    if player.active_quests:
        info_lines.append("Active Quests:")
        for q in player.active_quests:
            info_lines.append(f" - {q['title']} ({q['type']})")

    # 表示位置の計算 (行数に合わせて上にずらす)
    y_offset = SCREEN_HEIGHT - (len(info_lines) * 30 + 30)
    for line in info_lines:
        # カラー判定（簡易的）
        c = (255, 255, 255)
        if "AVAILABLE" in line: c = (100, 255, 100)
        elif "LOCKED" in line: c = (255, 100, 100)
        elif "[ACTIVE]" in line: c = (255, 255, 100)
        
        text_surf = font_small.render(line, True, c)
        bg_rect = text_surf.get_rect(topleft=(20, y_offset))
        
        # 半透明の背景を作成
        bg_surf = pygame.Surface((bg_rect.width + 10, bg_rect.height + 4), pygame.SRCALPHA)
        bg_surf.fill((0, 0, 0, 160)) # Alpha 160 (視認性向上のため少し濃く)
        screen.blit(bg_surf, (bg_rect.x - 5, bg_rect.y - 2))
        
        screen.blit(text_surf, (20, y_offset))
        y_offset += 30 # 行間を広げて重なりを解消

def main():
    try:
        pygame.init()
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Debug Master")
        
        start_floor, is_gungeon_mode = show_menu(screen)
        if start_floor is None:
            pygame.quit()
            return

        player = Player()
        player.is_debug = True
        player.hp = player.max_hp
        
        dungeon = warp_to_floor(start_floor, player)
        
        if is_gungeon_mode == "COMBAT_QA":
            dungeon.is_combat_qa = True
            dungeon = setup_gungeon_mode(dungeon, player)
            setup_combat_qa_mode(player, dungeon)
            is_gungeon_mode = True # 特殊マップ生成フラグとして維持
        elif is_gungeon_mode == "QUEST_QA":
            dungeon.is_quest_qa = True
            dungeon = setup_gungeon_mode(dungeon, player)
            setup_god_mode(player)
            is_gungeon_mode = True
        elif is_gungeon_mode:
            dungeon = setup_gungeon_mode(dungeon, player)
        
        ui_elements = init_ui_elements(SCREEN_WIDTH, SCREEN_HEIGHT)
        game_state = {"dialog_modal": False, "current_scene": "game"}
        setup_ui_relations(ui_elements, player, dungeon, game_state)

        clock = pygame.time.Clock()
        running = True

        while running:
            success, events = handle_events()
            if not success: running = False
            
            if is_gungeon_mode:
                dungeon.is_lighted = True
                for event in events:
                    if event.type == pygame.KEYDOWN:
                        # 階層移動 (1階刻み / Shift押下で10階刻み)
                        mods = pygame.key.get_mods()
                        step = 10 if (mods & pygame.KMOD_SHIFT) else 1
                        
                        change = 0
                        if event.key in (pygame.K_PLUS, pygame.K_SEMICOLON, pygame.K_EQUALS, pygame.K_KP_PLUS, pygame.K_n):
                            change = step
                        elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                            change = -step
                        
                        if change != 0:
                            new_floor = max(0, dungeon.current_floor + change)
                            if new_floor != dungeon.current_floor:
                                # モードを判定
                                is_combat_qa = getattr(dungeon, "is_combat_qa", False)
                                is_quest_qa = getattr(dungeon, "is_quest_qa", False)
                                is_gungeon = is_gungeon_mode # main内のフラグ
                                
                                dungeon.current_floor = new_floor
                                dungeon = warp_to_floor(dungeon.current_floor, player)
                                
                                if is_combat_qa:
                                    dungeon.is_combat_qa = True
                                    dungeon = setup_gungeon_mode(dungeon, player)
                                    setup_combat_qa_mode(player, dungeon)
                                elif is_quest_qa:
                                    dungeon.is_quest_qa = True
                                    dungeon = setup_gungeon_mode(dungeon, player)
                                    setup_god_mode(player)
                                elif is_gungeon:
                                    dungeon = setup_gungeon_mode(dungeon, player)
                                    
                                setup_ui_relations(ui_elements, player, dungeon, game_state)
                                print(f"[Debug] Switched to Floor {dungeon.current_floor} (Step: {change})")

                        # [NEW] ランク・GP操作
                        from constants import RANK_ORDER
                        if event.key in (pygame.K_RIGHTBRACKET, pygame.K_SLASH, pygame.K_PERIOD): # ] or / or . : Rank Up
                            idx = RANK_ORDER.index(player.guild_rank)
                            if idx < len(RANK_ORDER) - 1:
                                player.guild_rank = RANK_ORDER[idx + 1]
                                print(f"[Debug] Rank UP: {player.guild_rank}")
                                # マップ再生成（クエスト出現テスト用）
                                dungeon = setup_gungeon_mode(dungeon, player)
                        elif event.key in (pygame.K_LEFTBRACKET, pygame.K_COMMA): # [ or , : Rank Down
                            idx = RANK_ORDER.index(player.guild_rank)
                            if idx > 0:
                                player.guild_rank = RANK_ORDER[idx - 1]
                                print(f"[Debug] Rank DOWN: {player.guild_rank}")
                                dungeon = setup_gungeon_mode(dungeon, player)
                        elif event.key == pygame.K_PAGEUP: # GP +50
                            player.guild_point += 50
                            print(f"[Debug] GP +50: {player.guild_point}")
                            dungeon = setup_gungeon_mode(dungeon, player)
                        elif event.key == pygame.K_PAGEDOWN: # GP -50
                            player.guild_point = max(0, player.guild_point - 50)
                            print(f"[Debug] GP -50: {player.guild_point}")
                            dungeon = setup_gungeon_mode(dungeon, player)
                        
                        # [NEW] クエスト選択・受注操作
                        elif event.key == pygame.K_k: # K: Cycle Quest
                            player.debug_quest_idx = getattr(player, "debug_quest_idx", 0) + 1
                        elif event.key == pygame.K_l: # L: Toggle Accept
                            from constants import load_master_data
                            quests_data = load_master_data("quests.yml")
                            fixed_quests = quests_data.get("FIXED_QUESTS", [])
                            if fixed_quests:
                                q_idx = getattr(player, "debug_quest_idx", 0)
                                q = fixed_quests[q_idx % len(fixed_quests)]
                                # 既に受けているかチェック
                                existing = next((aq for aq in player.active_quests if aq["id"] == q["id"]), None)
                                if existing:
                                    player.remove_quest(existing)
                                    print(f"[Debug] Quest Removed & Tokens Reset: {q['title']}")
                                else:
                                    # [NEW] 1つ制限
                                    if len(player.active_quests) >= 1:
                                        print("[Debug] Quest limit reached (1). Remove existing quest first.")
                                    else:
                                        player.accept_quest(q)
                                        print(f"[Debug] Quest Accepted: {q['title']}")
                                # ターゲット出現のためにマップ再生成
                                dungeon = setup_gungeon_mode(dungeon, player)

            # ギルドメニューを閉じた瞬間を検知
            guild_was_active = ui_elements["guild_dialog"].is_active
            
            new_d = handle_game(screen, events, player, dungeon, ui_elements, game_state)
            
            # ギルドメニューが閉じられたらマップを最新化
            if guild_was_active and not ui_elements["guild_dialog"].is_active and is_gungeon_mode:
                print(f"[Debug] Guild Menu closed. Refreshing map for potential quest changes...")
                dungeon = setup_gungeon_mode(dungeon, player)
                new_d = dungeon
                # 他のUI要素にも新しい参照を渡す
                if ui_elements.get("shop_dialog"):
                    ui_elements["shop_dialog"].dungeon_ref = dungeon
            
            if not is_gungeon_mode:
                dungeon = new_d
            else:
                if new_d != dungeon:
                    dungeon = new_d
            
            draw_debug_overlay(screen, dungeon, player)
            
            pygame.display.flip()
            clock.tick(60)

    except Exception as e:
        print(f"[Fatal Error] {e}")
        traceback.print_exc()
        input("Press Enter to exit...")
    pygame.quit()

if __name__ == "__main__":
    main()
