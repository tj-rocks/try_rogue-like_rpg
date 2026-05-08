import random
from components.sprites.item import DroppedWeapon, DroppedConsumable, DroppedArmor, DroppedShield, DroppedStave, DroppedToken
from constants import WEAPON_DATA, CONSUMABLE_DATA, ARMOR_DATA, SHIELD_DATA, STAVE_DATA
from constants import ENEMY_DATA, ITEM_DROP_RATES

def update_dungeon_entities(dungeon, player, dialog=None):
    """
    ダンジョン内の動的なエンティティ（敵・アイテム・NPC）の状態を更新する。
    main.py のメインループをスッキリさせるためのハンドラ関数。
    """
    # 1. 敵の状態更新（アニメーション進行と死亡処理）
    for enemy in dungeon.enemies[:]:
        if enemy.is_dead:
            # 敵が死んでも点滅中は少し待つ（痛そうな顔を見せるため）
            if enemy.damage_flash_timer > 0:
                enemy.update_animation()
                continue

            # 敵の撃破処理
            # 経験値システムは廃止されたため、ドロップ判定のみ行います。
            
            # 各アイテムのカテゴリ、レアリティ、および設定されたドロップ率を取得
            drops = getattr(enemy, "drops", [])
            drop_infos = []
            for drop in drops:
                item_key = drop.get("item")
                # YAML で設定された個別確率を優先的に取得
                specific_rate = drop.get("rate") 
                
                rarity = 1
                if item_key in WEAPON_DATA: rarity = WEAPON_DATA[item_key].get("rarity", 1)
                elif item_key in ARMOR_DATA: rarity = ARMOR_DATA[item_key].get("rarity", 1)
                elif item_key in SHIELD_DATA: rarity = SHIELD_DATA[item_key].get("rarity", 1)
                elif item_key in CONSUMABLE_DATA: rarity = CONSUMABLE_DATA[item_key].get("rarity", 1)
                elif item_key in STAVE_DATA: rarity = STAVE_DATA[item_key].get("rarity", 1)
                
                drop_infos.append({
                    "item": item_key, 
                    "rarity": rarity, 
                    "rank_val": rarity,
                    "rate": specific_rate
                })
            
            # 高レアリティ順（降順）にソート
            drop_infos.sort(key=lambda x: x["rank_val"], reverse=True)
            
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
            if not dropped_token:
                from constants import DROP_RATE_MULTIPLIER
                for dinfo in drop_infos:
                    # YAML の個別確率があればそれを使用、なければレアリティ別テーブルから取得
                    base_rate = dinfo["rate"] if dinfo["rate"] is not None else ITEM_DROP_RATES.get(dinfo["rank_val"], 0.30)
                    target_rate = base_rate * DROP_RATE_MULTIPLIER
                    
                    if random.random() <= target_rate:
                        grid_x = int((enemy.x + dungeon.tile_size / 2) // dungeon.tile_size) * dungeon.tile_size
                        grid_y = int((enemy.y + dungeon.tile_size / 2) // dungeon.tile_size) * dungeon.tile_size
    
                        # ★ 同じグリッドに既存のアイテムがある場合はドロップしない
                        occupied = any(
                            int((it.x + dungeon.tile_size / 2) // dungeon.tile_size) * dungeon.tile_size == grid_x and
                            int((it.y + dungeon.tile_size / 2) // dungeon.tile_size) * dungeon.tile_size == grid_y
                            for it in dungeon.dropped_items
                            if not getattr(it, "is_collected", False)
                        )
                        if occupied:
                            break  # このドロップは諦める
    
                        item_key = dinfo["item"]
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
                        
                        dropped_any = True
                        break  # ★ 高レア順に計算し、1つでも落としたら即 break して終了

            dungeon.enemies.remove(enemy)
            reason = "Destroyed" if getattr(enemy, "is_static", False) else "Killed"
            enemy.__class__.log_population(dungeon, reason)
            continue

        
        # ★ 全ての敵のアニメーション（滑らかな移動や攻撃）を毎フレーム更新する
        moved = enemy.update(dungeon)
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

    # 2. 敵の「思考（行動決定）」を処理する
    from systems.game_state import game_state
    from constants import INTER_ACTION_BREATHER, ENEMY_THINK_LIMIT_PER_FRAME
    
    if game_state["turn_state"] == "enemies":
        enemies = dungeon.enemies
        
        # 思考用にキャッシュされたエンティティと占有情報を取得
        all_entities = game_state.get("all_entities_cache", [player] + enemies)
        occupied_cells = game_state.get("occupied_cells", set())

        think_count = 0
        # 連続して敵に行動を決定させる（攻撃が発生するか、思考制限に達するまで）
        while game_state["current_enemy_idx"] < len(enemies):
            idx = game_state["current_enemy_idx"]
            target_enemy = enemies[idx]
            
            if target_enemy.is_dead or target_enemy.damage_flash_timer > 0:
                game_state["current_enemy_idx"] += 1
                continue
            
            # まだ行動していないなら思考させる
            if not getattr(target_enemy, "has_acted", False):
                # 1フレームあたりの思考回数制限
                if think_count >= ENEMY_THINK_LIMIT_PER_FRAME:
                    return # 次のフレームに持ち越し

                target_enemy.take_turn(player, dungeon, all_entities, dialog, occupied_cells)
                target_enemy.has_acted = True
                think_count += 1
                
                # 移動先が決まったなら占有情報を更新（次の敵の思考に反映）
                new_gx = int((target_enemy.target_x + target_enemy.width / 2) // dungeon.tile_size)
                new_gy = int((target_enemy.target_y + target_enemy.height / 2) // dungeon.tile_size)
                occupied_cells.add((new_gx, new_gy))

                # 【重要】攻撃を開始したなら、一旦止まってアニメーションを待つ（シーケンシャル処理）
                if target_enemy.is_attacking:
                    return 
                
                # 移動だけなら、このフレーム内で次の敵の思考へ進む
                game_state["current_enemy_idx"] += 1
            else:
                # すでに思考済み（アニメーション中、またはメッセージ待機中）
                if target_enemy.is_attacking:
                    return # 攻撃アニメが終わるまで待機
                
                if dialog and dialog.is_active:
                    return # メッセージが閉じるまで待機
                
                # ★ 攻撃を行った敵の後は、今まで通り一呼吸置く（ウェイトを入れる）
                if getattr(target_enemy, "has_dealt_impact_damage", False):
                    if game_state["inter_action_timer"] == 0:
                        game_state["inter_action_timer"] = INTER_ACTION_BREATHER
                    
                    if game_state["inter_action_timer"] > 1:
                        game_state["inter_action_timer"] -= 1
                        return
                    game_state["inter_action_timer"] = 0

                # 次の敵へ
                game_state["current_enemy_idx"] += 1

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
    pass
