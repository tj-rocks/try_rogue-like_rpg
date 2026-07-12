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
from components.sprites.player import Player, EquipInstance, StaveInstance
from components.sprites.enemy import Enemy
from systems.dungeon import warp_to_floor
from systems.scene_handler import handle_game, handle_ending, handle_opening
from systems.session_handler import init_ui_elements, setup_ui_relations
from systems.resources import font_small, font_medium
from systems.events import handle_events, active_direction_keys
from systems.tactical_profile import TacticalProfile

# ===== デバッグ起動時のセットアップ画面 =====

def _build_equip_presets():
    from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, ACCESSORY_DATA
    presets = []
    for key, d in WEAPON_DATA.items():
        if d.get("category") == "event": continue
        presets.append(("weapon", key, d.get("name", key)))
    for key, d in ARMOR_DATA.items():
        if d.get("category") == "event": continue
        presets.append(("armor", key, d.get("name", key)))
    for key, d in SHIELD_DATA.items():
        if d.get("category") == "event": continue
        presets.append(("shield", key, d.get("name", key)))
    for key, d in ACCESSORY_DATA.items():
        if d.get("category") == "event": continue
        presets.append(("accessory", key, d.get("name", key)))
    return presets


def run_setup_screen(screen, font_s, font_m):
    """起動時のセットアップ画面。セーブ読み込み・開始階層・持ち物を選択する。
    戻り値: (player, start_floor) または None（キャンセル）"""
    from systems.data_loader import SAVE_DATA_PATH
    import os

    EQUIP_PRESETS = _build_equip_presets()

    SW, SH = screen.get_width(), screen.get_height()
    clock = pygame.time.Clock()
    ROW_H = 26
    VISIBLE_ROWS = (SH - 130) // ROW_H

    # --- 状態 ---
    has_save = os.path.exists(SAVE_DATA_PATH)
    use_save = False  # デフォルトはフレッシュスタート（セーブ汚染防止）
    start_floor = 1
    # シリーズ装備プリセット
    ASSASSIN_KEYS = {"assassin_dagger", "assassin_light_armor", "assassin_buckler"}
    HOLY_KEYS = {"holy_sword", "holy_armor", "holy_shield"}
    BRAVE_FIGHTER_KEYS = {"brave_fighter_sword", "brave_fighter_armor", "brave_fighter_shield"}
    MASTERS_KEYS = {"masters_rapier", "masters_armor", "masters_buckler"}
    SENIOR_KNIGHT_KEYS = {"senior_knight_hummer", "senior_knight_armor", "senior_knight_shield"}
    SERIES_PRESETS = {
        "アサシン": ASSASSIN_KEYS,
        "神聖": HOLY_KEYS,
        "勇敢戦士": BRAVE_FIGHTER_KEYS,
        "マスター": MASTERS_KEYS,
        "上級騎士": SENIOR_KNIGHT_KEYS,
    }
    # デフォルトでは何も選択しない
    selected_equips = set()
    section = 0  # 0:基本設定 1:装備
    cursor = 0
    scroll = 0

    BG      = (18, 22, 35)
    PANEL   = (30, 36, 55)
    ACCENT  = (80, 160, 255)
    WHITE   = (230, 230, 230)
    GRAY    = (130, 130, 150)
    YELLOW  = (255, 230, 80)
    GREEN   = (80, 220, 120)
    RED     = (220, 80, 80)

    def draw_checkbox(surf, x, y, checked, color):
        pygame.draw.rect(surf, (60, 70, 100), (x, y, 18, 18), border_radius=3)
        if checked:
            pygame.draw.rect(surf, color, (x+3, y+3, 12, 12), border_radius=2)
        else:
            pygame.draw.rect(surf, GRAY, (x, y, 18, 18), 1, border_radius=3)

    def draw_btn(surf, x, y, w, h, label, active=False):
        col = ACCENT if active else (55, 65, 90)
        pygame.draw.rect(surf, col, (x, y, w, h), border_radius=6)
        pygame.draw.rect(surf, (100, 130, 200) if active else GRAY, (x, y, w, h), 1, border_radius=6)
        txt = font_s.render(label, True, WHITE if active else GRAY)
        surf.blit(txt, (x + w//2 - txt.get_width()//2, y + h//2 - txt.get_height()//2))

    TABS = ["基本設定", f"装備選択 ({len(EQUIP_PRESETS)})"]

    running = True
    while running:
        clock.tick(60)
        screen.fill(BG)

        # --- タブ ---
        for i, tab in enumerate(TABS):
            col = ACCENT if i == section else (50, 60, 85)
            pygame.draw.rect(screen, col, (20 + i * 220, 15, 210, 38), border_radius=5)
            t = font_m.render(tab, True, WHITE)
            screen.blit(t, (20 + i * 220 + 105 - t.get_width()//2, 15 + 19 - t.get_height()//2))

        # --- セクション内容 ---
        y = 80
        if section == 0:
            # セーブ使用
            save_label = f"セーブデータを読み込む  ({'あり' if has_save else 'なし'})"
            draw_checkbox(screen, 30, y, use_save, GREEN)
            txt = font_s.render(save_label, True, WHITE if has_save else GRAY)
            screen.blit(txt, (58, y))
            if not has_save:
                warn = font_s.render("  ← セーブファイルが見つかりません", True, RED)
                screen.blit(warn, (58 + txt.get_width(), y))
            y += 44

            # 開始フロア
            floor_label = font_m.render(f"開始フロア:  {start_floor} F", True, WHITE)
            screen.blit(floor_label, (30, y))
            y += 36
            draw_btn(screen, 30,  y, 60, 30, "- 10", False)
            draw_btn(screen, 100, y, 60, 30, "- 1",  False)
            draw_btn(screen, 180, y, 60, 30, "+ 1",  False)
            draw_btn(screen, 250, y, 60, 30, "+10",  False)
            hint = font_s.render("← → または +/- ボタンで変更", True, GRAY)
            screen.blit(hint, (330, y + 6))
            y += 56

            info = font_s.render("※ セーブデータ読み込み時: セーブ時点の所持品・装備が引き継がれます", True, GRAY)
            screen.blit(info, (30, y))

        elif section == 1:
            header = font_s.render(f"チェックした装備を追加で持たせます  ↑↓スクロール  選択中: {len(selected_equips)}/{len(EQUIP_PRESETS)}", True, GRAY)
            screen.blit(header, (30, y - 20))
            # シリーズプリセットボタン
            btn_x = 30
            btn_y = y - 48
            for label, keys in SERIES_PRESETS.items():
                indices = {i for i, (_, ekey, _) in enumerate(EQUIP_PRESETS) if ekey in keys}
                active = bool(indices) and indices.issubset(selected_equips)
                bw = 100
                draw_btn(screen, btn_x, btn_y, bw, 30, label, active)
                btn_x += bw + 10
            all_selected = len(selected_equips) == len(EQUIP_PRESETS)
            draw_btn(screen, btn_x, btn_y, 90, 30, "全選択" if not all_selected else "全解除", False)
            for ri in range(VISIBLE_ROWS):
                i = scroll + ri
                if i >= len(EQUIP_PRESETS): break
                etype, ekey, ename = EQUIP_PRESETS[i]
                checked = i in selected_equips
                hl = i == cursor
                ry = y + ri * ROW_H
                if hl:
                    pygame.draw.rect(screen, (40, 50, 80), (25, ry - 2, SW - 50, ROW_H - 2), border_radius=4)
                draw_checkbox(screen, 30, ry, checked, GREEN)
                type_col = {"weapon": (255,180,80), "armor": (100,180,255),
                            "shield": (180,255,130), "accessory": (255,130,255)}.get(etype, WHITE)
                screen.blit(font_s.render(f"[{etype[:3].upper()}]", True, type_col), (58, ry))
                screen.blit(font_s.render(ename, True, YELLOW if hl else WHITE), (120, ry))
            # スクロールバー
            total = len(EQUIP_PRESETS)
            if total > VISIBLE_ROWS:
                bar_h = max(20, int(VISIBLE_ROWS / total * (SH - 130)))
                bar_y = y + int(scroll / total * (SH - 130))
                pygame.draw.rect(screen, GRAY, (SW - 12, y, 8, SH - 130 - 60), border_radius=4)
                pygame.draw.rect(screen, ACCENT, (SW - 12, bar_y, 8, bar_h), border_radius=4)

        # --- 下部ボタン ---
        draw_btn(screen, SW - 220, SH - 60, 190, 44, "▶ この設定で開始", True)
        hint_keys = font_s.render("Tab: タブ切替 | ↑↓: 移動 | Space/Enter: ON/OFF | ←→: フロア変更", True, GRAY)
        screen.blit(hint_keys, (20, SH - 28))

        pygame.display.flip()

        # --- イベント処理 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                k = event.key
                if k == pygame.K_ESCAPE:
                    return None
                elif k == pygame.K_TAB:
                    section = (section + 1) % 2
                    cursor = 0
                    scroll = 0
                elif k in (pygame.K_UP, pygame.K_w):
                    if section == 1:
                        cursor = (cursor - 1) % len(EQUIP_PRESETS)
                        scroll = max(0, min(scroll, cursor))
                        if cursor < scroll: scroll = cursor
                elif k in (pygame.K_DOWN, pygame.K_s):
                    if section == 1:
                        cursor = (cursor + 1) % len(EQUIP_PRESETS)
                        if cursor >= scroll + VISIBLE_ROWS: scroll = cursor - VISIBLE_ROWS + 1
                        if cursor == 0: scroll = 0
                elif k in (pygame.K_SPACE, pygame.K_RETURN):
                    if section == 0:
                        if has_save: use_save = not use_save
                    elif section == 1:
                        if cursor in selected_equips: selected_equips.remove(cursor)
                        else: selected_equips.add(cursor)
                elif k in (pygame.K_LEFT, pygame.K_MINUS):
                    mods = pygame.key.get_mods()
                    start_floor = max(0, start_floor - (10 if mods & pygame.KMOD_SHIFT else 1))
                elif k in (pygame.K_RIGHT, pygame.K_EQUALS, pygame.K_PLUS):
                    mods = pygame.key.get_mods()
                    start_floor = min(99, start_floor + (10 if mods & pygame.KMOD_SHIFT else 1))
                elif k == pygame.K_F5:
                    running = False
            if event.type == pygame.MOUSEWHEEL:
                if section == 1:
                    scroll = max(0, min(len(EQUIP_PRESETS) - VISIBLE_ROWS, scroll - event.y))
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if section == 0:
                    btn_y_base = 80 + 44 + 36
                    if btn_y_base <= my <= btn_y_base + 30:
                        if 30 <= mx <= 90:   start_floor = max(0,  start_floor - 10)
                        elif 100 <= mx <= 160: start_floor = max(0,  start_floor - 1)
                        elif 180 <= mx <= 240: start_floor = min(99, start_floor + 1)
                        elif 250 <= mx <= 310: start_floor = min(99, start_floor + 10)
                    if 30 <= mx <= 50 and 80 <= my <= 98 and has_save:
                        use_save = not use_save
                elif section == 1:
                    # シリーズプリセットボタンクリック
                    btn_x = 30
                    btn_y = 80 - 48
                    series_clicked = False
                    for label, keys in SERIES_PRESETS.items():
                        indices = {i for i, (_, ekey, _) in enumerate(EQUIP_PRESETS) if ekey in keys}
                        if btn_x <= mx <= btn_x + 100 and btn_y <= my <= btn_y + 30:
                            if indices.issubset(selected_equips):
                                selected_equips.difference_update(indices)
                            else:
                                selected_equips.update(indices)
                            series_clicked = True
                            break
                        btn_x += 110
                    if not series_clicked:
                        all_selected = len(selected_equips) == len(EQUIP_PRESETS)
                        if btn_x <= mx <= btn_x + 90 and btn_y <= my <= btn_y + 30:
                            if all_selected:
                                selected_equips.clear()
                            else:
                                selected_equips = set(range(len(EQUIP_PRESETS)))
                        else:
                            for ri in range(VISIBLE_ROWS):
                                ry = 80 + ri * ROW_H
                                if ry - 2 <= my <= ry + ROW_H - 4:
                                    i = scroll + ri
                                    if i < len(EQUIP_PRESETS):
                                        cursor = i
                                        if i in selected_equips: selected_equips.remove(i)
                                        else: selected_equips.add(i)
                # 開始ボタン
                if SW - 220 <= mx <= SW - 30 and SH - 60 <= my <= SH - 16:
                    running = False

    # --- プレイヤー構築 ---
    player = Player()
    player.is_debug = True
    player.max_reached_floor = 99

    if use_save and has_save:
        player.load_from_file()
        print(f"[Setup] セーブデータを読み込みました (Floor {player.current_floor}, Rank {player.guild_rank})")
        # 装備をクリアして選択した装備のみを持たせる
        player.weapon_inventory.clear()
        player.armor_inventory.clear()
        player.shield_inventory.clear()
        player.accessory_inventory.clear()
        player.equipped_weapon = None
        player.equipped_armor = None
        player.equipped_shield = None
        player.equipped_accessory = None
    else:
        # 本番バランスに近い値でスタート（backstab/stupidity 動作確認用）
        from constants import PLAYER_ATTACK, PLAYER_HP, PLAYER_DEFENSE
        player.attack = PLAYER_ATTACK
        player.hp = PLAYER_HP
        player.max_hp = PLAYER_HP
        player.defense = PLAYER_DEFENSE
        player.guild_point = 1000
        player.guild_rank = "F"
        player.coin = 100000
        print(f"[Setup] 本番バランスで開始 (attack={PLAYER_ATTACK}, hp={PLAYER_HP})")

    # 追加装備
    last_selected = {}
    for idx in sorted(selected_equips):
        etype, ekey, _ = EQUIP_PRESETS[idx]
        inst = EquipInstance(etype, ekey)
        if etype == "weapon":
            player.weapon_inventory.append(inst)
            last_selected["weapon"] = inst
        elif etype == "armor":
            player.armor_inventory.append(inst)
            last_selected["armor"] = inst
        elif etype == "shield":
            player.shield_inventory.append(inst)
            last_selected["shield"] = inst
        elif etype == "accessory":
            player.accessory_inventory.append(inst)
            last_selected["accessory"] = inst

    # 選択した装備を自動装備（最後に選択したものが各部位に反映される）
    if "weapon" in last_selected:
        player.change_weapon(last_selected["weapon"].iid)
    if "armor" in last_selected:
        player.change_armor(last_selected["armor"].iid)
    if "shield" in last_selected:
        player.change_shield(last_selected["shield"].iid)
    if "accessory" in last_selected:
        player.change_accessory(last_selected["accessory"].iid)

    print(f"[Setup] 開始フロア: {start_floor}F")
    return player, start_floor

def setup_gungeon_mode(dungeon, player):
    """テクスチャ・アイテム確認用の特殊フロア設定"""
    if dungeon.floor_info.get("map"):
        print(f"[Debug] Skipping Gungeon Mode for Fixed Map on Floor {dungeon.current_floor}")
        return dungeon

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
        
        from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, CONSUMABLE_DATA, STAVE_DATA, ACCESSORY_DATA
        from components.sprites.item import DroppedWeapon, DroppedConsumable, DroppedArmor, DroppedShield, DroppedStave, DroppedAccessory
        
        floor_tiles = [(c, r) for r in range(3, h + 2) for c in range(2, w + 2) if dungeon.map_data[r][c] == 1]
        random.shuffle(floor_tiles)

        # [NEW] 出現可能なアイテムをリストアップ
        candidates = []
        
        # 進行中のクエストアイテムは確定で追加する（ただし出現階層条件を満たす場合のみ）
        for q in player.active_quests:
            tk = q.get("target_key")
            if tk:
                # アイテムデータから階層制限を取得してチェック
                item_data = (WEAPON_DATA.get(tk) or ARMOR_DATA.get(tk) or 
                             SHIELD_DATA.get(tk) or CONSUMABLE_DATA.get(tk) or 
                             STAVE_DATA.get(tk) or ACCESSORY_DATA.get(tk))
                if item_data:
                    min_f = item_data.get("min_floor", 1)
                    max_f = item_data.get("max_floor", 999)
                    if not (min_f <= dungeon.current_floor <= max_f):
                        continue
                
                if tk in WEAPON_DATA: candidates.append(("weapon", tk))
                elif tk in ARMOR_DATA: candidates.append(("armor", tk))
                elif tk in SHIELD_DATA: candidates.append(("shield", tk))
                elif tk in CONSUMABLE_DATA: candidates.append(("item", tk))
                elif tk in STAVE_DATA: candidates.append(("stave", tk))
                elif tk in ACCESSORY_DATA: candidates.append(("accessory", tk))
                
        # アイテムカタログをスキャン
        for ctype, catalog in [("weapon", WEAPON_DATA), ("armor", ARMOR_DATA), 
                               ("shield", SHIELD_DATA), ("item", CONSUMABLE_DATA), ("stave", STAVE_DATA),
                               ("accessory", ACCESSORY_DATA)]:
            for k, it in catalog.items():
                if it.get("category") == "event":
                    continue
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

        dungeon.dropped_items = []
        
        for i, cand in enumerate(candidates):
            if i >= len(floor_tiles): break
            tx, ty = floor_tiles[i]
            ctype, ckey = cand
            try:
                it = None
                enhance, stats = dungeon._generate_enhanced_drop(player)
                
                if ctype == "weapon": it = DroppedWeapon(tx * ts, ty * ts, ckey, WEAPON_DATA[ckey], enhance=enhance, stats=stats)
                elif ctype == "armor": it = DroppedArmor(tx * ts, ty * ts, ckey, ARMOR_DATA[ckey], enhance=enhance, stats=stats)
                elif ctype == "shield": it = DroppedShield(tx * ts, ty * ts, ckey, SHIELD_DATA[ckey], enhance=enhance, stats=stats)
                elif ctype == "item": it = DroppedConsumable(tx * ts, ty * ts, ckey, CONSUMABLE_DATA[ckey])
                elif ctype == "stave": it = DroppedStave(tx * ts, ty * ts, ckey, STAVE_DATA[ckey])
                elif ctype == "accessory": it = DroppedAccessory(tx * ts, ty * ts, ckey, ACCESSORY_DATA[ckey], enhance=enhance, stats=stats)
                if it:
                    dungeon.dropped_items.append(it)
                    print(f"  [Debug Spawn] Item {i+1}: {it.name} ({ckey}) at ({tx}, {ty})")
            except Exception as e:
                print(f"[Debug Error] Failed to spawn {ckey}: {e}")
        
        # トラップの配置 (全種類)
        from components.sprites.trap import Trap
        dungeon.traps = []
        trap_start_idx = len(candidates)
        trap_keys = list(TRAP_DATA.keys())
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
            NPC("ギルド受付", (w + 1) * ts, 2 * ts, sprite_type="guild_receptionist", role="guild_receptionist", image_path="components/pictures/npc/girl_town_v")
        ]
        
        print(f"[Debug] Gungeon Mode Ready. MapSize:{dungeon.map_width}x{dungeon.map_height}")
        return dungeon
    except Exception as e:
        print(f"[Error] setup_gungeon_mode: {e}")
        traceback.print_exc()
        return dungeon


def setup_last_boss_mode(dungeon, player):
    try:
        print("[Debug] Setting up Last Boss Mode...")
        try:
            if os.path.exists("duel_ai.log"):
                os.remove("duel_ai.log")
        except:
            pass
        apply_last_boss_mock_player(player)
        dungeon = setup_gungeon_mode(dungeon, player)
        ts = dungeon.tile_size
        dungeon.dropped_items = []
        dungeon.traps = []
        dungeon.npcs = []
        dungeon.enemies = []
        dungeon.spawn_counts = {}
        dungeon.is_combat_qa = False
        dungeon.is_quest_qa = False

        center_x = max(2, dungeon.map_width // 2)
        center_y = max(2, dungeon.map_height // 2)
        player.x = center_x * ts
        player.y = min(dungeon.map_height - 3, center_y + 4) * ts
        player.target_x = player.x
        player.target_y = player.y
        player.set_current_floor(99)

        boss = Enemy(center_x * ts, center_y * ts, "dungeon_core", player=player)
        boss.target_x, boss.target_y = boss.x, boss.y
        boss.current_dungeon = dungeon
        dungeon.enemies.append(boss)
        dungeon.spawn_counts[boss.type] = 1
        dungeon.current_floor = 99
        dungeon.is_lighted = True
        dungeon.reveal_floor()
        print("[Debug] Last Boss Mode Ready.")
        return dungeon
    except Exception as e:
        print(f"[Error] setup_last_boss_mode: {e}")
        traceback.print_exc()
        return dungeon

def apply_last_boss_mock_player(player):
    mock_weapon = player._find_equip_inst(player.weapon_inventory, player.equipped_weapon)
    mock_armor = player._find_equip_inst(player.armor_inventory, player.equipped_armor)
    mock_shield = player._find_equip_inst(player.shield_inventory, player.equipped_shield)
    mock_accessory = player._find_equip_inst(player.accessory_inventory, player.equipped_accessory)

    def clone_equip(inst):
        if not inst:
            return None
        cloned = EquipInstance(inst.equip_type, inst.key)
        cloned.enhance = getattr(inst, "enhance", 0)
        cloned.stats = dict(getattr(inst, "stats", {}) or {})
        return cloned

    preserved = {
        "weapon": clone_equip(mock_weapon),
        "armor": clone_equip(mock_armor),
        "shield": clone_equip(mock_shield),
        "accessory": clone_equip(mock_accessory),
    }

    from constants import PLAYER_ATTACK, PLAYER_HP, PLAYER_DEFENSE
    player.attack = PLAYER_ATTACK
    player.hp = PLAYER_HP
    player.max_hp = PLAYER_HP
    player.defense = PLAYER_DEFENSE
    player.coin = 5000
    player.bank_coin = 0
    player.guild_point = 9999
    player.guild_rank = "A"
    player.current_floor = 99
    player.max_reached_floor = 99
    player.items = [
        {"key": "heal_potion", "count": 3},
        {"key": "antidote", "count": 2},
    ]
    player.active_quests = []
    player.quest_tokens = {}
    player.completed_fixed_quests = []
    player.defeated_once_only = []
    player.warehouse_items = []
    player.event_items = [{"key": "fathers_charm", "count": 1}]
    player.regen_pool = 0
    player.condition = "normal"
    player.invincible_turns = 0
    player.attack_buff_turns = 0
    player.attack_buff_val = 0
    player.attack_buff_crit = 0
    player.attack_buff_armor_pen = 0.0
    player.regen_buff_turns = 0
    player.regen_buff_val = 0
    player.regen_buff_heal_boost = 0.0
    player.magic_buff_turns = 0
    player.magic_buff_val = 0
    player.stealth_buff_turns = 0
    player.stealth_buff_max_turns = 0
    player.stealth_buff_lantern = 0
    player.stealth_buff_aggro = 0
    player.stealth_buff_stupidity = 0
    player.enemy_turn_pending = False
    player.is_god = False
    player.weapon_inventory = []
    player.armor_inventory = []
    player.shield_inventory = []
    player.accessory_inventory = []
    player.stave_inventory = [
        StaveInstance("fire_stave", charges=5),
        StaveInstance("knockback_stave", charges=5),
        StaveInstance("heal_stave", charges=3),
    ]
    player.unequip_weapon()
    player.unequip_armor()
    player.unequip_shield()
    player.unequip_accessory()

    if preserved["weapon"]:
        player.weapon_inventory.append(preserved["weapon"])
        player.change_weapon(preserved["weapon"].iid)
    if preserved["armor"]:
        player.armor_inventory.append(preserved["armor"])
        player.change_armor(preserved["armor"].iid)
    if preserved["shield"]:
        player.shield_inventory.append(preserved["shield"])
        player.change_shield(preserved["shield"].iid)
    if preserved["accessory"]:
        player.accessory_inventory.append(preserved["accessory"])
        player.change_accessory(preserved["accessory"].iid)

    # ラスボスの読み筋を即確認できるよう、軽く傾向を仕込んでおく
    player.tactical_profile = TacticalProfile({
        "front|1|melee": 4,
        "front|1|magic_knockback": 3,
        "front|2|move": 3,
        "diagonal|1|move": 4,
        "far|3plus|magic_fire": 5,
        "far|3plus|move": 2,
    })
    print("[Debug] Applied mocked player profile for Last Boss Mode.")

def _build_last_boss_debug_lines(dungeon, player):
    boss = None
    for enemy in getattr(dungeon, "enemies", []):
        if getattr(enemy, "type", "") == "dungeon_core" and not getattr(enemy, "is_dead", False):
            boss = enemy
            break
    if not boss:
        return []

    try:
        from systems.tactical_profile import get_relation_and_distance
        relation, distance = get_relation_and_distance(player, boss, dungeon.tile_size)
        profile = getattr(player, "tactical_profile", None)
        preferred = profile.get_preferred_action(relation, distance) if profile else None
        fire_local = profile.get_action_total("magic_fire", relation=relation, distance=distance) if profile else 0
        knockback_local = profile.get_action_total("magic_knockback", relation=relation, distance=distance) if profile else 0
        fire_total = profile.get_action_total("magic_fire") if profile else 0
        knockback_total = profile.get_action_total("magic_knockback") if profile else 0
        magic_read = boss._read_player_magic_habit(player, relation, distance)
        current_mode = getattr(boss, "current_attack_mode", None) or "-"
        counter_ready = getattr(boss, "counter_ready_turns", 0)
        return [
            "--- LAST BOSS READ ---",
            f"Pos: relation={relation} distance={distance} preferred={preferred or '-'}",
            f"Magic habit: read={magic_read or '-'} fire={fire_local}/{fire_total} knockback={knockback_local}/{knockback_total}",
            f"Boss state: mode={current_mode} counter={counter_ready}",
        ]
    except Exception as e:
        return [f"Last Boss Debug Error: {e}"]

def draw_debug_overlay(screen, dungeon, player):
    # 会心率の計算
    crit_rate = getattr(player, "crit_rate", 0.01)
    weapon = getattr(player, "weapon", None)
    if weapon:
        crit_rate = weapon.data.get("crit_rate", 0.01)
    crit_bonus = getattr(player, "crit_bonus", 0)                   
    crit_rate += crit_bonus
    from constants import CRITICAL_RATE_MAX
    crit_rate = min(CRITICAL_RATE_MAX, crit_rate)
    crit_percent = int(crit_rate * 100)

    info_lines = [
        f"ULTIMATE DEBUG MODE - Floor: {dungeon.current_floor}",
        f"Rank: {player.guild_rank} (GP: {player.guild_point})",
        f"Crit Rate: {crit_percent}% (Base: {int(getattr(player, 'crit_rate', 0.01)*100)}% + Weapon: {int(weapon.data.get('crit_rate', 0.01)*100) if weapon else 0}% + Bonus: {int(crit_bonus*100)}%)",
        "[N/B] : Warp Next/Prev Floor | [Shift]+ : Jump 10F",
        "[G] : God Mode (Invincibility + Atk x100)",
        "[H] : Heal HP | [K] : Kill All Enemies",
        "[Y] : Trigger Shop Sale",
        "[PageUp/Dn] : Adjust GP (+/-100)",
        "[. / ,] : Rank UP / DOWN",
        "[J] : Last Boss Mode",
    ]
    
    # 受注中クエストの表示
    if player.active_quests:
        info_lines.append("Active Quests:")
        for q in player.active_quests:
            info_lines.append(f" - {q['title']} ({q['type']})")

    info_lines.extend(_build_last_boss_debug_lines(dungeon, player))

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
    """最強デバッグツール：セットアップ画面でセーブ・装備・フロアを選んで起動する"""
    try:
        pygame.init()
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("ULTIMATE DEBUG TOOL")

        # 1. セットアップ画面
        result = run_setup_screen(screen, font_small, font_medium)
        if result is None:
            pygame.quit()
            return
        player, start_floor = result

        # 2. ダンジョンの初期化
        dungeon = warp_to_floor(max(0, start_floor), player)
        
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
                        player.max_reached_floor = max(player.max_reached_floor, new_floor) # デバッグワープでも到達階を更新
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
                    elif event.key == pygame.K_y: # Trigger shop sale refresh
                        player.shop_bonus_refresh = True
                        dungeon.refresh_shop_stock(player_rank=player.guild_rank)
                        print(f"[DEBUG] Shop Sale Triggered! Rank={player.guild_rank}")
                    
                    # 進捗調整
                    elif event.key == pygame.K_PAGEUP:
                        player.guild_point += 100
                        print(f"[DEBUG] GP increased to {player.guild_point}")
                    elif event.key == pygame.K_PAGEDOWN:
                        player.guild_point = max(0, player.guild_point - 100)
                        print(f"[DEBUG] GP decreased to {player.guild_point}")
                    elif event.key == pygame.K_PERIOD:
                        from constants import RANK_ORDER
                        ranks = list(RANK_ORDER) if RANK_ORDER else ["F", "E", "D", "C", "B", "A", "S", "SS"]
                        idx = ranks.index(player.guild_rank) if player.guild_rank in ranks else 0
                        if idx < len(ranks) - 1:
                            player.guild_rank = ranks[idx + 1]
                            print(f"[DEBUG] Rank UP: {player.guild_rank}")
                            dungeon = setup_gungeon_mode(dungeon, player) # クエスト候補更新のため
                    elif event.key == pygame.K_COMMA:
                        from constants import RANK_ORDER
                        ranks = list(RANK_ORDER) if RANK_ORDER else ["F", "E", "D", "C", "B", "A", "S", "SS"]
                        idx = ranks.index(player.guild_rank) if player.guild_rank in ranks else 0
                        if idx > 0:
                            player.guild_rank = ranks[idx - 1]
                        print(f"[DEBUG] Rank DOWN: {player.guild_rank}")
                        dungeon = setup_gungeon_mode(dungeon, player)
                    elif event.key == pygame.K_o:
                        dungeon.debug_overflow = True
                        print(f"[DEBUG] Outbreak Reserved for Next Floor. Go to the stairs!")
                    elif event.key == pygame.K_l:
                        dungeon.is_lighted = not dungeon.is_lighted
                        print(f"[DEBUG] Light Mode: {'ON' if dungeon.is_lighted else 'OFF'}")
                    elif event.key == pygame.K_j:
                        dungeon = warp_to_floor(99, player, spawn_reason="debug")
                        dungeon.is_combat_qa = True
                        dungeon.is_quest_qa = True
                        dungeon = setup_last_boss_mode(dungeon, player)
                        setup_ui_relations(ui_elements, player, dungeon, game_state)
                        print("[DEBUG] Last Boss Mode engaged")

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
                handle_ending(screen, events, game_state, ending_imgs, ui_elements, story_data, player=player)
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
