import pygame
import random
from components.sprites.item import DroppedWeapon, DroppedConsumable, DroppedArmor, DroppedShield, DroppedStave, DroppedToken, DroppedAccessory
from constants import WEAPON_DATA, CONSUMABLE_DATA, ARMOR_DATA, SHIELD_DATA, STAVE_DATA, ACCESSORY_DATA
from constants import ENEMY_DATA, ITEM_DROP_RATES
from systems.game_state import game_state

def update_dungeon_entities(dungeon, player, dt, dialog=None):
    """
    ダンジョン内の動的なエンティティ（敵・アイテム・NPC）の状態を更新する。
    main.py のメインループをスッキリさせるためのハンドラ関数。
    """
    # 1. 敵の状態更新（アニメーション進行と死亡処理）
    for enemy in dungeon.enemies[:]:
        if enemy.is_dead:
            # 敵が死んでも点滅中は少し待つ（痛そうな顔を見せるため）
            if enemy.damage_flash_timer > 0:
                enemy.update_animation(dt)
                continue

            # 敵の撃破処理
            # 経験値システムは廃止されたため、ドロップ判定のみ行います。
            
            # 各アイテムのカテゴリ、レアリティ、および設定されたドロップ率を取得
            drops = getattr(enemy, "drops", {})
            normal_drop_rate = getattr(enemy, "normal_drop_rate", 0.1)
            rare_drop_rate = getattr(enemy, "rare_drop_rate", 0.01)
            
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
                        
                    if item_key in WEAPON_DATA:
                        dungeon.dropped_items.append(DroppedWeapon(grid_x, grid_y, item_key, WEAPON_DATA[item_key]))
                    elif item_key in ARMOR_DATA:
                        dungeon.dropped_items.append(DroppedArmor(grid_x, grid_y, item_key, ARMOR_DATA[item_key]))
                    elif item_key in SHIELD_DATA:
                        dungeon.dropped_items.append(DroppedShield(grid_x, grid_y, item_key, SHIELD_DATA[item_key]))
                    elif item_key in CONSUMABLE_DATA:
                        dungeon.dropped_items.append(DroppedConsumable(grid_x, grid_y, item_key, CONSUMABLE_DATA[item_key]))
                    elif item_key in STAVE_DATA:
                        dungeon.dropped_items.append(DroppedStave(grid_x, grid_y, item_key, STAVE_DATA[item_key]))
                    elif item_key in ACCESSORY_DATA:
                        dungeon.dropped_items.append(DroppedAccessory(grid_x, grid_y, item_key, ACCESSORY_DATA[item_key]))
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
                from constants import SOUND_QUEST_COMPLETE, SOUND_BOSS_VICTORY
                import os
                
                # 勝利SEの再生 (自作の boss_victory.wav があれば優先)
                victory_se = SOUND_BOSS_VICTORY if os.path.exists(SOUND_BOSS_VICTORY) else SOUND_QUEST_COMPLETE
                
                if os.path.exists(victory_se):
                    pygame.mixer.Sound(victory_se).play()
                
                # 撃破メッセージを表示 (モーダル表示：入力を待つ)
                show_dialog(dialog, f"{enemy.name} を 討伐した！", modal=True, auto_close=0)

            dungeon.enemies.remove(enemy)
            reason = "Destroyed" if getattr(enemy, "is_static", False) else "Killed"
            enemy.__class__.log_population(dungeon, reason)
            continue

        
        # ★ 全ての敵のアニメーション（滑らかな移動や攻撃）を毎フレーム更新する
        moved = enemy.update(dungeon, dt)
        if moved:
            # 敵が移動を完了した瞬間に足元の罠をチェック
            egx = int((enemy.x + enemy.width / 2) // dungeon.tile_size)
            egy = int((enemy.y + enemy.height / 2) // dungeon.tile_size)
            for trap in dungeon.traps[:]:
                if trap.x == egx and trap.y == egy:
                    # 敵が罠を踏んだ！
                    # ダメージ床や地雷は敵にも効くようにする
                    if trap.type == "damage_floor":
                        dmg = trap.data.get("damage", 10)
                        enemy.hp -= dmg
                        trap.is_revealed = True
                        from systems.magic_handler import FlashEffect
                        dungeon.magic_effects.append(FlashEffect(color=(255, 0, 0), duration=8))
                    elif trap.type == "mine":
                        enemy.hp = enemy.hp // 2
                        trap.is_revealed = True
                        from systems.magic_handler import FireEffect
                        dungeon.magic_effects.append(FireEffect(enemy.x, enemy.y, size=80, color=(255, 150, 0)))
                        dungeon.traps.remove(trap)
                        dungeon.trigger_shake(10, 20)
                    elif trap.type == "pitfall":
                        enemy.hp = 0
                        enemy.is_dead = True
                        trap.is_revealed = True
                        dungeon.trigger_shake(5, 15)
                    
                    if enemy.hp <= 0:
                        enemy.is_dead = True
                        # 罠で死んだ場合も撃破演出（ボスなら）
                        if getattr(enemy, "is_boss", False):
                            from systems.ui import show_dialog
                            show_dialog(dialog, f"{enemy.name} を 討伐した！")

    # 2. 敵の「思考（行動決定）」を処理する
    from systems.game_state import game_state
    from constants import INTER_ACTION_BREATHER, ENEMY_THINK_LIMIT_PER_FRAME
    
    if game_state["turn_state"] == "enemies":
        enemies = dungeon.enemies
        all_entities = game_state.get("all_entities_cache", [player] + enemies)
        occupied_cells = game_state.get("occupied_cells", set())

        think_count = 0
        while game_state["current_enemy_idx"] < len(enemies):
            idx = game_state["current_enemy_idx"]
            enemy = enemies[idx]
            
            if getattr(enemy, "has_acted", False) or getattr(enemy, "is_dead", False):
                game_state["current_enemy_idx"] += 1
                continue
            
            if think_count >= ENEMY_THINK_LIMIT_PER_FRAME:
                break
            
            # 敵の思考と行動実行
            enemy.take_turn(player, dungeon, all_entities, dialog, occupied_cells)
            enemy.has_acted = True
            think_count += 1
            game_state["current_enemy_idx"] += 1
            
            if enemy.is_attacking:
                game_state["enemy_action_breather"] = INTER_ACTION_BREATHER
                break
        
        if game_state["current_enemy_idx"] >= len(enemies):
            if game_state.get("enemy_action_breather", 0) <= 0:
                # 全ての敵の行動決定が終わった
                pass 

        # 全ての敵が行動決定を終えたら、全員の移動アニメーション完了を待つ
        all_moving_done = True
        for e in enemies:
            if e.is_moving or e.is_attacking:
                all_moving_done = False
                break
        
        if all_moving_done and not (dialog and dialog.is_active):
            # --- プレイヤーにターンを戻す前の処理 ---
            player.apply_turn_effects(dungeon, dialog)
            
            # リスポーン判定（1ターンに1回実行）
            dungeon.handle_respawn_turn(player)
            
            game_state["turn_state"] = "player"
            game_state["current_enemy_idx"] = 0
            for e in enemies:
                e.has_acted = False # リセット
                if hasattr(e, "has_dealt_impact_damage"):
                    e.has_dealt_impact_damage = False

    # 2. 落ちているアイテムの取得判定
    px = int((player.x + dungeon.tile_size / 2) // dungeon.tile_size)
    py = int((player.y + dungeon.tile_size / 2) // dungeon.tile_size)
    
    for item in dungeon.dropped_items[:]:
        if not getattr(item, "is_collected", False):
            ix = int((item.x + dungeon.tile_size / 2) // dungeon.tile_size)
            iy = int((item.y + dungeon.tile_size / 2) // dungeon.tile_size)
            if px == ix and py == iy:
                if hasattr(item, "collect"):
                    try:
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
                        else:
                            # 拾えなかった場合、プレイヤーを一歩手前に押し戻す（アイテムを消さないため）
                            player.x = player.prev_x
                            player.y = player.prev_y
                            player.target_x = player.prev_x
                            player.target_y = player.prev_y
                            player.is_moving = False
                    except Exception as e:
                        print(f"[Error] Failed to collect item: {e}")

    # 3. 敵のリスポーン処理（ターン制へ移行したため、ここでは何もしない）
    # 4. ボスBGMの切り替え判定 [NEW]
    from constants import ENEMY_AGGRO_RADIUS, BGM_BOSS
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
            dist_x, dist_y = abs(egx - pgx), abs(egy - pgy)
            
            # 認識範囲（隠密補正込み）を取得
            aggro_mod = player.get_aggro_modifier() if hasattr(player, "get_aggro_modifier") else 0
            effective_radius = max(1, ENEMY_AGGRO_RADIUS + aggro_mod)
            
            if dist_x <= effective_radius and dist_y <= effective_radius:
                active_boss = enemy
                has_aggroed_boss = True
                break
    
    # BGMの切り替え実行
    if has_aggroed_boss:
        if not was_boss_battle:
            game_state["is_boss_battle"] = True
            # 個別BGM設定があればそれを使う。なければ定数 BGM_BOSS を使う
            target_bgm = getattr(active_boss, "bgm", None) or BGM_BOSS
            play_bgm(target_bgm)
            
            # [NEW] ボス遭遇メッセージ (モーダル表示：入力を待つ)
            if not getattr(player, "boss_message_shown", False):
                from systems.ui import show_dialog
                show_dialog(dialog, f"{active_boss.name} に 発見された！", modal=True, auto_close=0)
                player.boss_message_shown = True
            
            print(f"[SOUND] Boss encountered! Switching to: {target_bgm}")
    else:
        if was_boss_battle:
            game_state["is_boss_battle"] = False
            dungeon.play_floor_bgm()
            print("[SOUND] Boss battle ended. Reverting to floor BGM.")

    pass
