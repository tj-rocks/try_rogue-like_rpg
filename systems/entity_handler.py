import pygame
import random
from collections.abc import Mapping
from components.sprites.item import DroppedWeapon, DroppedConsumable, DroppedArmor, DroppedShield, DroppedStave, DroppedToken, DroppedAccessory
from constants import WEAPON_DATA, CONSUMABLE_DATA, ARMOR_DATA, SHIELD_DATA, STAVE_DATA, ACCESSORY_DATA
from constants import ENEMY_DATA, ITEM_DROP_RATES
from systems.game_state import game_state, is_enemy_acting

def resolve_dynamic_drops(item_list, current_rank):
    """
    ドロップリスト内の '@' から始まる特別なキーワード（例: '@current_rank_weapons', '@current_rank_armors'）
    を、該当ランク（またはそれに最も近い下位ランク）の全ての対象アイテムキーのリストに動的に展開します。
    """
    if not isinstance(item_list, list):
        return item_list
        
    RANKS = ["F", "E", "D", "C", "B", "A", "S", "SS"]
    
    def get_query_rank(category_data):
        # 該当ランクのアイテムが直接存在する場合はそれを返す
        if any(item.get("min_rank") == current_rank for item in category_data.values()):
            return current_rank
        # 存在しない場合（例: Cランクの武器が存在しないなど）、存在する最も近い下位ランクを探す
        try:
            current_idx = RANKS.index(current_rank)
        except ValueError:
            current_idx = len(RANKS) - 1
            
        for i in range(current_idx - 1, -1, -1):
            r = RANKS[i]
            if any(item.get("min_rank") == r for item in category_data.values()):
                return r
        return "F"

    resolved = []
    for item in item_list:
        if isinstance(item, str) and item.startswith("@"):
            if item == "@current_rank_weapons":
                target_rank = get_query_rank(WEAPON_DATA)
                weapons = [k for k, v in WEAPON_DATA.items() if v.get("min_rank") == target_rank]
                resolved.extend(weapons)
            elif item == "@current_rank_armors":
                target_rank = get_query_rank(ARMOR_DATA)
                armors = [k for k, v in ARMOR_DATA.items() if v.get("min_rank") == target_rank]
                resolved.extend(armors)
            else:
                resolved.append(item)
        else:
            resolved.append(item)
    return resolved

def _normalize_dialog_text(value):
    if not value:
        return None
    if isinstance(value, list):
        return "\n".join(str(v) for v in value if v is not None)
    return str(value)

def _normalize_dialog_sequence(value):
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v is not None and str(v) != ""]
    text = str(value)
    return [text] if text else []

def _get_boss_encounter_config(boss_type):
    cfg = ENEMY_DATA.get(boss_type, {})
    select_cfg = cfg.get("select_dialog") or {}
    has_select_dialog = isinstance(select_cfg, Mapping) and bool(select_cfg)
    if not isinstance(select_cfg, Mapping):
        select_cfg = {}
    return {
        "encounter_message": _normalize_dialog_text(cfg.get("encounter_message")),
        "dialog_message": _normalize_dialog_text(cfg.get("dialog_message")),
        "dialog_sequence": _normalize_dialog_sequence(cfg.get("dialog_message")),
        "has_select_dialog": has_select_dialog,
        "prompt": _normalize_dialog_text(select_cfg.get("message")) or "戦いますか",
        "yes_text": str(select_cfg.get("yes_text") or "はい"),
        "no_text": str(select_cfg.get("no_text") or "いいえ"),
        "yes_action": select_cfg.get("yes_action") or "battle_start",
        "no_action": select_cfg.get("no_action") or "village_warp",
        "encounter_trigger_range": int(cfg.get("encounter_trigger_range", cfg.get("detect_range", 3) or 3)),
        "encounter_dialog_range": int(
            cfg.get(
                "encounter_dialog_range",
                cfg.get("encounter_trigger_range", cfg.get("detect_range", 3) or 3),
            )
        ),
    }

def _start_boss_battle(dungeon, player, boss):
    from systems.audio_manager import play_bgm
    from constants import BGM_BOSS
    game_state["is_boss_battle"] = True
    game_state["boss_battle_persistent"] = getattr(boss, "type", None) == "dungeon_core"
    game_state["boss_encounter_pending"] = False
    if boss:
        boss.battle_locked = False
        if hasattr(boss, "activate_battle_equipment"):
            boss.activate_battle_equipment()
    target_bgm = getattr(boss, "bgm", None) or BGM_BOSS
    play_bgm(target_bgm)
    print(f"[SOUND] Boss battle confirmed! Switching to: {target_bgm}")

def _warp_to_village_from_boss(dungeon, player):
    from systems.dungeon import warp_to_floor
    game_state["boss_encounter_pending"] = False
    dungeon.next_dungeon = warp_to_floor(0, player, spawn_reason="return", old_dungeon=dungeon)

def _open_boss_select_dialog(confirm_dialog, boss_cfg):
    if not confirm_dialog:
        return
    confirm_dialog.text = boss_cfg["prompt"]
    confirm_dialog.yes_text = boss_cfg["yes_text"]
    confirm_dialog.no_text = boss_cfg["no_text"]
    confirm_dialog.is_active = True

def update_dungeon_entities(dungeon, player, dt, dialog=None, confirm_dialog=None):
    """
    ダンジョン内の動的なエンティティ（敵・アイテム・NPC）の状態を更新する。
    main.py のメインループをスッキリさせるためのハンドラ関数。
    """
    from systems.game_state import game_state
    # 1. 敵の状態更新（アニメーション進行と死亡処理）
    for enemy in dungeon.enemies[:]:
        if enemy.is_dead:
            # 敵が死んでも点滅中は少し待つ（痛そうな顔を見せるため）
            if enemy.damage_flash_timer > 0:
                if not hasattr(enemy, "_death_logged"):
                    enemy._log_trace(dungeon, f"[DEATH-DEBUG] is_dead=True, damage_flash_timer={enemy.damage_flash_timer}, attack_pre_delay_timer={getattr(enemy, 'attack_pre_delay_timer', 0)}, peak_hold_timer={getattr(enemy, 'peak_hold_timer', 0)}")
                    enemy._death_logged = True
                enemy.update_animation(dt)
                continue

            # 敵の撃破処理
            # 経験値システムは廃止されたため、ドロップ判定のみ行います。
            
            # 各アイテムのカテゴリ、レアリティ、および設定されたドロップ率を取得
            drops = getattr(enemy, "drops", {})
            normal_drop_rate = getattr(enemy, "normal_drop_rate", 0.1)
            rare_drop_rate = getattr(enemy, "rare_drop_rate", 0.01)
            
            # 現在のフロアに応じたランクを計算
            floor = dungeon.current_floor
            if floor <= 11: current_rank = "F"
            elif floor <= 21: current_rank = "E"
            elif floor <= 30: current_rank = "D"
            elif floor <= 40: current_rank = "C"
            elif floor <= 55: current_rank = "B"
            elif floor <= 70: current_rank = "A"
            elif floor <= 99: current_rank = "S"
            else: current_rank = "SS"
            
            # 階層ランク別または共通ドロップ設定が含まれている場合の抽出・マージ処理
            if isinstance(drops, dict) and ("common" in drops or any(r in drops for r in ["F", "E", "D", "C", "B", "A", "S", "SS"])):
                common_cfg = drops.get("common", {})
                rank_cfg = drops.get(current_rank, {})
                
                if isinstance(common_cfg, dict):
                    merged = common_cfg.copy()
                    if isinstance(rank_cfg, dict):
                        merged.update(rank_cfg)
                    drops = merged
                else:
                    drops = rank_cfg if isinstance(rank_cfg, dict) else {}
                
                normal_drop_rate = drops.get("normal_drop_rate", normal_drop_rate)
                rare_drop_rate = drops.get("rare_drop_rate", rare_drop_rate)
                
            # 動的ドロップ設定（@表記）の解決
            if isinstance(drops, dict):
                if "normal" in drops:
                    drops["normal"] = resolve_dynamic_drops(drops["normal"], current_rank)
                if "rare" in drops:
                    drops["rare"] = resolve_dynamic_drops(drops["rare"], current_rank)
            
            # 1. 討伐の証（クエスト対象）の優先ドロップ判定
            dropped_token = False
            active_quests = getattr(player, "active_quests", [])
            for q in active_quests:
                if q.get("type") == "hunt" and q.get("target_key") == enemy.type:
                    grid_x = int((enemy.x + dungeon.tile_size / 2) // dungeon.tile_size) * dungeon.tile_size
                    grid_y = int((enemy.y + dungeon.tile_size / 2) // dungeon.tile_size) * dungeon.tile_size
                    dungeon.dropped_items.append(DroppedToken(grid_x, grid_y, enemy.type, ENEMY_DATA[enemy.type]["name"]))
                    dropped_token = True
                    break
            
            # 2. 通常のドロップ判定 (証を落とした場合は確実にスキップ)
            if not dropped_token and isinstance(drops, dict):
                from constants import DROP_RATE_MULTIPLIER
                from systems.game_state import game_state
                
                grid_x = int((enemy.x + dungeon.tile_size / 2) // dungeon.tile_size) * dungeon.tile_size
                grid_y = int((enemy.y + dungeon.tile_size / 2) // dungeon.tile_size) * dungeon.tile_size
                
                def try_spawn_item(item_list):
                    if not item_list:
                        return False
                        
                    # 重みリストの作成
                    weights = []
                    for d in item_list:
                        item_key = d.get("item") if isinstance(d, dict) else d
                        rarity = 1
                        if item_key in WEAPON_DATA: rarity = WEAPON_DATA[item_key].get("rarity", 1)
                        elif item_key in ARMOR_DATA: rarity = ARMOR_DATA[item_key].get("rarity", 1)
                        elif item_key in SHIELD_DATA: rarity = SHIELD_DATA[item_key].get("rarity", 1)
                        elif item_key in CONSUMABLE_DATA: rarity = CONSUMABLE_DATA[item_key].get("rarity", 1)
                        elif item_key in STAVE_DATA: rarity = STAVE_DATA[item_key].get("rarity", 1)
                        elif item_key in ACCESSORY_DATA: rarity = ACCESSORY_DATA[item_key].get("rarity", 1)
                        
                        weights.append(ITEM_DROP_RATES.get(rarity, 0.1))
                        
                    chosen = random.choices(item_list, weights=weights, k=1)[0]
                    item_key = chosen.get("item") if isinstance(chosen, dict) else chosen
                    
                    # グリッド重複チェック
                    occupied = any(
                        int((it.x + dungeon.tile_size / 2) // dungeon.tile_size) * dungeon.tile_size == grid_x and
                        int((it.y + dungeon.tile_size / 2) // dungeon.tile_size) * dungeon.tile_size == grid_y
                        for it in dungeon.dropped_items
                        if not getattr(it, "is_collected", False)
                    )
                    if occupied:
                        return False
                        
                    enhance, stats = dungeon._generate_enhanced_drop(player)
                    if item_key in WEAPON_DATA:
                        dungeon.dropped_items.append(DroppedWeapon(grid_x, grid_y, item_key, WEAPON_DATA[item_key], enhance=enhance, stats=stats))
                    elif item_key in ARMOR_DATA:
                        dungeon.dropped_items.append(DroppedArmor(grid_x, grid_y, item_key, ARMOR_DATA[item_key], enhance=enhance, stats=stats))
                    elif item_key in SHIELD_DATA:
                        dungeon.dropped_items.append(DroppedShield(grid_x, grid_y, item_key, SHIELD_DATA[item_key], enhance=enhance, stats=stats))
                    elif item_key in CONSUMABLE_DATA:
                        dungeon.dropped_items.append(DroppedConsumable(grid_x, grid_y, item_key, CONSUMABLE_DATA[item_key]))
                    elif item_key in STAVE_DATA:
                        dungeon.dropped_items.append(DroppedStave(grid_x, grid_y, item_key, STAVE_DATA[item_key]))
                    elif item_key in ACCESSORY_DATA:
                        dungeon.dropped_items.append(DroppedAccessory(grid_x, grid_y, item_key, ACCESSORY_DATA[item_key], enhance=enhance, stats=stats))
                    return True
                
                # A. レアドロップ判定
                rare_rolled = random.random() <= rare_drop_rate * DROP_RATE_MULTIPLIER or game_state.get("is_debug_mode")
                if rare_rolled and try_spawn_item(drops.get("rare", [])):
                    pass # ドロップ成功
                else:
                    # B. ノーマルドロップ判定 (レアが外れた、または出現しなかった場合)
                    normal_rolled = random.random() <= normal_drop_rate * DROP_RATE_MULTIPLIER or game_state.get("is_debug_mode")
                    if normal_rolled:
                        try_spawn_item(drops.get("normal", []))

            # 敵の撃破処理
            # ボスの場合、特別な演出
            if getattr(enemy, "is_boss", False):
                from systems.ui import show_dialog
                from systems.guild import GuildSystem
                from constants import SOUND_QUEST_COMPLETE, SOUND_BOSS_VICTORY
                from systems.magic_handler import FlashEffect, BossDefeatAuraEffect
                from systems.audio_manager import play_bgm
                import os
                enemy_type = getattr(enemy, "type", None)
                
                # 白フラッシュエフェクト（約1秒）
                dungeon.magic_effects.append(FlashEffect(color=(255, 255, 255), duration=60))
                dungeon.magic_effects.append(
                    BossDefeatAuraEffect(
                        enemy.x,
                        enemy.y,
                        duration=360,
                        color=(210, 240, 255) if enemy_type == "dungeon_core" else (235, 235, 255),
                        radius=max(enemy.width, enemy.height),
                    )
                )
                
                # 勝利SEの再生 (自作の boss_victory.wav があれば優先)
                victory_se = SOUND_BOSS_VICTORY if os.path.exists(SOUND_BOSS_VICTORY) else SOUND_QUEST_COMPLETE
                
                if os.path.exists(victory_se):
                    pygame.mixer.Sound(victory_se).play()

                # ボス撃破時点で戦闘BGMを解除し、専用曲があればそちらへ切り替える
                game_state["is_boss_battle"] = False
                game_state["boss_battle_persistent"] = False
                game_state["boss_encounter_pending"] = False
                defeat_bgm = ENEMY_DATA.get(enemy_type, {}).get("defeat_bgm")
                if defeat_bgm:
                    play_bgm(defeat_bgm)
                else:
                    dungeon.play_floor_bgm()
                
                # 撃破メッセージを表示 (モーダル表示：入力を待つ)
                # enemies.yml の defeat_message があれば順送りでそれを使う
                defeat_sequence = _normalize_dialog_sequence(
                    ENEMY_DATA.get(enemy_type, {}).get("defeat_message")
                )
                if defeat_sequence:
                    dialog.page_wait_frames = 60
                    show_dialog(dialog, defeat_sequence, modal=True, auto_close=0)
                    dialog.on_close_callback = lambda d=dialog: setattr(d, "page_wait_frames", 2)
                else:
                    show_dialog(dialog, f"{enemy.name} を 討伐した！", modal=True, auto_close=0)

                # ダンジョンコア討伐時は、ギルドクエストを挟まず直接SSランクへ昇格させる
                if enemy_type in ("undead_father", "dungeon_core"):
                    guild = GuildSystem()
                    ss_data = guild.get_current_rank("SS")
                    player.guild_rank = "SS"
                    player.guild_point = max(player.guild_point, ss_data.get("required_gp", player.guild_point))
                    from systems.game_state import game_state
                    game_state["post_boss_clear_pending"] = True
                    game_state["ending_route"] = "core" if enemy_type == "dungeon_core" else "father"
                
                # once_only 敵の撃破記録
                if enemy_type and ENEMY_DATA.get(enemy_type, {}).get("once_only"):
                    if not hasattr(player, "defeated_once_only"):
                        player.defeated_once_only = []
                    if enemy_type not in player.defeated_once_only:
                        player.defeated_once_only.append(enemy_type)

            enemy._log_trace(dungeon, f"[DEATH-DEBUG] removing enemy from dungeon.enemies (len before: {len(dungeon.enemies)})")
            dungeon.enemies.remove(enemy)
            reason = "Destroyed" if getattr(enemy, "is_static", False) else "Killed"
            enemy.__class__.log_population(dungeon, reason)
            continue

        
        # ★ 全ての敵のアニメーション（滑らかな移動や攻撃）を毎フレーム更新する
        enemy.update(dungeon, dt)

    # 2. 敵の「思考（行動決定）」を処理する
    from constants import INTER_ACTION_BREATHER, ENEMY_THINK_LIMIT_PER_FRAME

    if game_state.get("boss_encounter_pending", False):
        for enemy in dungeon.enemies:
            if getattr(enemy, "is_boss", False):
                enemy.battle_locked = True
                enemy.is_moving = False
                enemy.target_x, enemy.target_y = enemy.x, enemy.y
        return
    
    if game_state["turn_state"] == "enemies":
        enemies = dungeon.enemies
        all_entities = game_state.get("all_entities_cache", [player] + enemies)
        occupied_cells = game_state.get("occupied_cells", set())

        think_count = 0
        while game_state["current_enemy_idx"] < len(enemies):
            idx = game_state["current_enemy_idx"]
            enemy = enemies[idx]
            
            if getattr(enemy, "has_acted", False) or getattr(enemy, "is_dead", False) or getattr(enemy, "is_static", False):
                game_state["current_enemy_idx"] += 1
                continue
            
            if think_count >= ENEMY_THINK_LIMIT_PER_FRAME:
                break
            
            # 敵の思考と行動実行
            enemy.take_turn(player, dungeon, all_entities, dialog, occupied_cells)
            enemy.has_acted = True
            # 一時的 stupidity 上昇は敵ターン終了でリセット
            if hasattr(enemy, "stupidity_temp"):
                enemy.stupidity_temp = 0
            think_count += 1
            game_state["current_enemy_idx"] += 1
            
            if enemy.is_attacking:
                game_state["enemy_action_breather"] = INTER_ACTION_BREATHER
                break
        
        if game_state["current_enemy_idx"] >= len(enemies):
            if game_state.get("enemy_action_breather", 0) <= 0:
                # 全ての敵の行動決定が終わった
                pass 

        # 全ての敵が行動決定を終えており、且つ全員の移動アニメーションが完了している場合のみプレイヤーのターンに戻す
        all_thinking_done = (game_state["current_enemy_idx"] >= len(enemies))
        
        all_moving_done = True
        if is_enemy_acting(dungeon):
            all_moving_done = False
        if all_moving_done:
            for e in enemies:
                if e.is_moving:
                    all_moving_done = False
                    break
        
        if all_thinking_done and all_moving_done and not (dialog and dialog.is_active):
            # --- プレイヤーにターンを戻す前の処理 ---
            player.apply_turn_effects(dungeon, dialog)
            
            # リスポーン判定（1ターンに1回実行）
            dungeon.handle_respawn_turn(player)
            
            game_state["turn_state"] = "player"
            game_state["current_enemy_idx"] = 0
            
            # [DEBUG] ターン終了時に全エネミーのステータスをダンプ
            try:
                with open("enemy_ai.log", "a", encoding="utf-8") as f:
                    f.write(f"=== TURN END ENEMY DUMP (Floor {dungeon.current_floor}) ===\n")
                    for e in enemies:
                        f.write(f"  [{e.name}#{id(e)%10000}]: pos=({e.x},{e.y}), target=({e.target_x},{e.target_y}), is_dead={getattr(e, 'is_dead', False)}, has_acted={getattr(e, 'has_acted', False)}, is_moving={getattr(e, 'is_moving', False)}, is_attacking={getattr(e, 'is_attacking', False)}, flash={getattr(e, 'damage_flash_timer', 0)}, speed={getattr(e, 'move_speed', 0)}\n")
                    f.write("========================================================\n")
            except:
                pass

            for e in enemies:
                # 障害物（is_static）の寿命ターンの更新
                if getattr(e, "is_static", False) and hasattr(e, "lifetime_turns") and e.lifetime_turns is not None:
                    e.lifetime_turns -= 1
                    if e.lifetime_turns <= 0:
                        e.is_dead = True
                        if dialog:
                            from constants import COMBAT_LOG_WAIT_FRAMES
                            msg = f"{e.name} は 消滅した！"
                            if dialog.is_active:
                                dialog.text += "\n" + msg
                            else:
                                dialog.text = msg
                                dialog.is_active = True
                            dialog.auto_close_timer = COMBAT_LOG_WAIT_FRAMES

                e.has_acted = False # リセット
                if hasattr(e, "has_dealt_impact_damage"):
                    e.has_dealt_impact_damage = False

    # 2. 落ちているアイテムの取得判定
    px = int((player.x + dungeon.tile_size / 2) // dungeon.tile_size)
    py = int((player.y + dungeon.tile_size / 2) // dungeon.tile_size)
    
    has_uncollected_item_at_player = False
    for item in dungeon.dropped_items[:]:
        if not getattr(item, "is_collected", False):
            ix = int((item.x + dungeon.tile_size / 2) // dungeon.tile_size)
            iy = int((item.y + dungeon.tile_size / 2) // dungeon.tile_size)
            if px == ix and py == iy:
                has_uncollected_item_at_player = True
                
                # すでにこのマスで警告を表示済みの場合はスキップ
                last_warned = getattr(player, "last_item_warned_pos", None)
                if last_warned == (px, py):
                    continue
                
                if hasattr(item, "collect"):
                    try:
                        item_type = type(item).__name__
                        item_key = getattr(item, 'item_key', 'unknown')
                        print(f"[ITEM-PICKUP-START] type={item_type}, key={item_key}, pos=({px},{py})")

                        msg = item.collect(player)
                        print(f"[DUNGEON] Collected Item: {msg}")
                        if dialog:
                            from systems.game_state import game_state
                            dialog.text = msg
                            game_state["dialog_modal"] = True
                            dialog.is_active = True

                        # 実際に取得できた場合のみ、リストから削除する
                        if getattr(item, "is_collected", False):
                            dungeon.dropped_items.remove(item)
                            player.last_item_warned_pos = None
                            print(f"[ITEM-PICKUP-SUCCESS] Removed {item_key} from dropped_items")
                        else:
                            # 拾えなかった場合、位置を記録
                            player.last_item_warned_pos = (px, py)
                            print(f"[ITEM-PICKUP-FAILED] {item_key} not collected (inventory full?)")
                    except Exception as e:
                        import traceback
                        print(f"[ERROR] Failed to collect item: {e}")
                        print(f"[ERROR] Item type: {type(item).__name__}")
                        print(f"[ERROR] Item key: {getattr(item, 'item_key', 'unknown')}")
                        print(f"[ERROR] Traceback:\n{traceback.format_exc()}")
                        traceback.print_exc()
                break
                
    if not has_uncollected_item_at_player:
        player.last_item_warned_pos = None

    # 3. 敵のリスポーン処理（ターン制へ移行したため、ここでは何もしない）
    # 4. ボスBGMの切り替え判定 [NEW]
    from constants import BGM_BOSS
    from systems.game_state import game_state
    from systems.audio_manager import play_bgm
    
    was_boss_battle = game_state.get("is_boss_battle", False)
    has_aggroed_boss = False
    
    # 視界内にボスがいて、かつプレイヤーに気づいているかチェック
    active_boss = None
    for enemy in dungeon.enemies:
        if getattr(enemy, "is_boss", False) and not getattr(enemy, "is_dead", False):
            # グリッド距離で判定
            egx, egy = int(enemy.x // dungeon.tile_size), int(enemy.y // dungeon.tile_size)
            pgx, pgy = int(player.x // dungeon.tile_size), int(player.y // dungeon.tile_size)
            dist = max(abs(egx - pgx), abs(egy - pgy))
            boss_cfg = _get_boss_encounter_config(getattr(enemy, "type", None))
            trigger_range = max(1, boss_cfg["encounter_dialog_range"])

            if dist <= trigger_range:
                active_boss = enemy
                has_aggroed_boss = True
                break
    
    # BGMの切り替え実行
    if has_aggroed_boss:
        if not was_boss_battle:
            shown_bosses = getattr(player, "_shown_boss_messages", set())
            boss_type = getattr(active_boss, "type", None)
            boss_cfg = _get_boss_encounter_config(boss_type)
            encounter_msg = boss_cfg["encounter_message"] or f"{active_boss.name} に 発見された！"
            if boss_type not in shown_bosses and not game_state.get("confirm_active", False):
                from systems.game_state import game_state as gs
                shown_bosses.add(boss_type)
                player._shown_boss_messages = shown_bosses

                if confirm_dialog:
                    from systems.ui import show_dialog
                    dialog_msg = boss_cfg["dialog_message"]
                    dialog_sequence = boss_cfg["dialog_sequence"]
                    game_state["boss_encounter_pending"] = True
                    game_state["boss_battle_persistent"] = boss_type == "dungeon_core"
                    active_boss.battle_locked = True

                    def on_yes(boss=active_boss, dun=dungeon, pl=player):
                        _start_boss_battle(dun, pl, boss)

                    def on_no(boss=active_boss, dun=dungeon, pl=player):
                        from systems.game_state import game_state as gs
                        gs["post_boss_clear_pending"] = True
                        gs["ending_route"] = "core_refuse"
                        _warp_to_village_from_boss(dun, pl)

                    confirm_dialog.on_yes = on_yes if boss_cfg["yes_action"] == "battle_start" else None
                    confirm_dialog.on_no = on_no if boss_cfg["no_action"] == "village_warp" else None

                    def _finish_boss_dialog(
                        cd=confirm_dialog,
                        cfg=boss_cfg,
                        boss=active_boss,
                        dun=dungeon,
                        pl=player,
                        d=dialog,
                    ):
                        d.page_wait_frames = 2
                        if cfg["has_select_dialog"]:
                            _open_boss_select_dialog(cd, cfg)
                        else:
                            _start_boss_battle(dun, pl, boss)

                    if dialog_sequence:
                        dialog.page_wait_frames = 60
                        show_dialog(dialog, dialog_sequence, modal=True, auto_close=0)
                        dialog.on_close_callback = _finish_boss_dialog
                    else:
                        dialog.page_wait_frames = 60
                        show_dialog(dialog, dialog_msg or encounter_msg, modal=True, auto_close=0)
                        dialog.just_opened_timer = 60
                        dialog.on_close_callback = _finish_boss_dialog
                    gs["dialog_modal"] = True
            else:
                if boss_type not in shown_bosses:
                    shown_bosses.add(boss_type)
                    player._shown_boss_messages = shown_bosses
    else:
        if was_boss_battle and not game_state.get("boss_battle_persistent", False):
            game_state["is_boss_battle"] = False
            dungeon.play_floor_bgm()
            print("[SOUND] Boss battle ended. Reverting to floor BGM.")

    pass
