import pygame
import os
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE
from systems.ui import handle_ui_events, draw_vision_overlay, draw_all_ui
from systems.game_state import is_paused
from systems.entity_handler import update_dungeon_entities
from systems.death_handler import handle_death_sequence

def handle_opening(screen, events, game_state, opening_imgs, start_new_game_func, ui_elements, story_data=None):
    """
    オープニング演出を処理する。
    """
    screen.fill((0, 0, 0))
    game_state["opening_alpha"] = min(255, game_state["opening_alpha"] + 2)
    idx = game_state["opening_index"]
    
    # 1. 画像の描画
    if idx < len(opening_imgs):
        from systems.ui import draw_opening_scene
        draw_opening_scene(screen, opening_imgs[idx], game_state["opening_alpha"])

    # 2. テキストとBGM의 管理
    dialog = ui_elements["dialog"]
    text = ""
    if story_data and "opening" in story_data:
        page_data = story_data["opening"].get(idx + 1) or story_data["opening"].get(str(idx + 1))
        if page_data:
            text = page_data.get("text", "")
            if dialog.text != text:
                dialog.text = text
                dialog.is_active = True
                game_state["dialog_modal"] = False # オープニング中は入力を強制ポーズさせない
            
            bgm = page_data.get("bgm")
            if bgm and game_state.get("current_bgm") != bgm:
                from systems.audio_manager import play_bgm
                play_bgm(bgm)
                game_state["current_bgm"] = bgm

    # 3. ダイアログの更新と描画
    dialog.handle_events(events)
    dialog.update()
    if dialog.is_active:
        dialog.draw(screen)

    game_state["opening_timer"] += 1
    
    # ダイアログが閉じられたか、一定時間経過か、スキップキーで次へ
    skip = False
    for event in events:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_z):
            if not dialog.is_active:
                skip = True
    
    if game_state["opening_timer"] > 600 or skip:
        game_state["opening_timer"] = 0
        game_state["opening_alpha"] = 0
        game_state["opening_index"] += 1
        dialog.is_active = False # 次のシーンのために一度閉じる
        
        if game_state["opening_index"] >= len(opening_imgs):
            game_state["opening_index"] = 0
            game_state["opening_seen"] = True
            from systems.data_loader import SAVE_DATA_PATH
            if not os.path.exists(SAVE_DATA_PATH):
                game_state["current_scene"] = "title"
            else:
                start_new_game_func()
    
    return game_state["current_scene"]
    
def handle_ending(screen, events, game_state, ending_imgs, ui_elements, story_data=None):
    """
    エンディング演出を処理する。
    """
    screen.fill((0, 0, 0))
    game_state["ending_alpha"] = min(255, game_state.get("ending_alpha", 0) + 2)
    idx = game_state.get("ending_index", 0)
    
    # 1. 画像の描画
    if idx < len(ending_imgs):
        from systems.ui import draw_opening_scene
        draw_opening_scene(screen, ending_imgs[idx], game_state["ending_alpha"])

    # 2. テキストとBGMの管理
    dialog = ui_elements["dialog"]
    text = ""
    if story_data and "ending" in story_data:
        page_data = story_data["ending"].get(idx + 1) or story_data["ending"].get(str(idx + 1))
        if page_data:
            text = page_data.get("text", "")
            if dialog.text != text:
                dialog.text = text
                dialog.is_active = True
                game_state["dialog_modal"] = False
            
            bgm = page_data.get("bgm")
            if bgm and game_state.get("current_bgm") != bgm:
                from systems.audio_manager import play_bgm
                play_bgm(bgm)
                game_state["current_bgm"] = bgm

    # 3. ダイアログの更新と描画
    dialog.handle_events(events)
    dialog.update()
    if dialog.is_active:
        dialog.draw(screen)

    game_state["ending_timer"] = game_state.get("ending_timer", 0) + 1
    
    skip = False
    for event in events:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_z):
            if not dialog.is_active:
                skip = True
    
    if game_state["ending_timer"] > 600 or skip:
        game_state["ending_timer"] = 0
        game_state["ending_alpha"] = 0
        game_state["ending_index"] = idx + 1
        dialog.is_active = False
        
        if game_state["ending_index"] >= len(ending_imgs):
            game_state["ending_index"] = 0
            game_state["current_scene"] = "game"
    
    return game_state["current_scene"]

def handle_title(screen, events, game_state, title_bg, has_save, start_new_game_func, continue_game_func):
    """
    タイトル画面の入力を処理し、描画する。
    """
    from systems.ui import draw_title_screen
    draw_title_screen(screen, title_bg, game_state["title_selected_idx"], has_save)
    
    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP and has_save:
                game_state["title_selected_idx"] = 0
            elif event.key == pygame.K_DOWN:
                game_state["title_selected_idx"] = 1
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_z):
                if game_state["title_selected_idx"] == 0:
                    if has_save:
                        continue_game_func()
                else:
                    if game_state.get("opening_seen"):
                        start_new_game_func()
                    else:
                        game_state["opening_index"] = 0
                        game_state["opening_timer"] = 0
                        game_state["opening_alpha"] = 0
                        game_state["current_scene"] = "opening"
    
    return game_state["current_scene"]

def handle_game(screen, events, player, dungeon, ui_elements, game_state, dt=0):
    """
    ゲーム本編（探索・戦闘）のロジックを処理する。
    """
    # UIイベント処理
    if hasattr(ui_elements, "handle_events"):
        ui_elements.handle_events(events, player=player, dungeon=dungeon)
    else:
        handle_ui_events(events, 
                         ui_elements["dialog"], ui_elements["confirm_dialog"], ui_elements["inventory_dialog"], 
                         ui_elements["status_dialog"], ui_elements["enhance_dialog"], ui_elements["item_action_dialog"], 
                         ui_elements["ore_selection_dialog"], menu_dialog=ui_elements.get("menu_dialog"), player=player, dungeon=dungeon, 
                         shop_dialog=ui_elements.get("shop_dialog"), stave_selection_dialog=ui_elements.get("stave_selection_dialog"), 
                         guild_dialog=ui_elements.get("guild_dialog"), warehouse_dialog=ui_elements.get("warehouse_dialog"), 
                         equip_dialog=ui_elements.get("equip_dialog"),
                         stave_inv_dialog=ui_elements.get("stave_inventory_dialog"),
                         event_inv_dialog=ui_elements.get("event_inventory_dialog"),
                         bank_dialog=ui_elements.get("bank_dialog"),
                         teleport_dialog=ui_elements.get("teleport_dialog"),
                         guild_guide_dialog=ui_elements.get("guild_guide_dialog"),
                         cutscene_manager=ui_elements.get("cutscene_manager"),
                         parameter_selection_active=game_state.get("parameter_selection_active"),
                         parameter_selection_dialog=ui_elements.get("parameter_selection_dialog"),
                         ore_gift_dialog=ui_elements.get("ore_gift_dialog"))
    
    screen.fill((0, 0, 0))
    
    # --- 1. ロジック更新フェーズ ---
    
    # 1-1. プレイヤーの基本更新 (移動、入力、攻撃)
    player.update(dungeon, dt, ui_elements["dialog"], events)
    
    # 1-2. エンティティ更新（敵の思考、アイテム取得、罠判定など）
    new_dungeon = dungeon
    
    # 転移（テレポート・落とし穴）予約の処理: 落下アニメーション終了時に実行
    if player.is_falling and player.falling_timer <= 0:
        if game_state.get("pending_warp"):
            from systems.dungeon import warp_to_floor
            w = game_state["pending_warp"]
            new_dungeon = warp_to_floor(w["floor"], player, spawn_reason=w["spawn_reason"])
            game_state["pending_warp"] = None
    
    is_death_active = game_state.get("death_sequence_step", 0) > 0
    if not is_paused() and not is_death_active and not player.is_dead:
        # 敵の更新、アイテム取得判定
        update_dungeon_entities(new_dungeon, player, dt, ui_elements["dialog"], ui_elements["confirm_dialog"])
        
        # 罠・階段・特殊イベントの判定
        if not player.is_falling:
            new_dungeon = new_dungeon.check_traps(player, ui_elements["dialog"])
            new_dungeon.check_outbreak_start(ui_elements["dialog"])
            new_dungeon.update_outbreak_status(player, ui_elements["dialog"])
        new_dungeon = new_dungeon.check_stairs(player, ui_elements["confirm_dialog"], ui_elements["dialog"])

    # エリア到達メッセージの演出（ダクソ風オーバーレイ）
    if game_state.get("pending_area_message"):
        overlay = ui_elements.get("area_message_overlay")
        if overlay:
            overlay.show(game_state.pop("pending_area_message"))
        else:
            game_state.pop("pending_area_message")

    # 1-3. 死亡演出、カットシーンなどの更新
    new_dungeon = handle_death_sequence(player, new_dungeon, ui_elements["dialog"], game_state)
    if ui_elements.get("cutscene_manager"):
        ui_elements["cutscene_manager"].update()

    # --- 2. 描画フェーズ ---
    # ワープ等でnew_dungeonが更新されている可能性があるため、以降はnew_dungeonを使用
    
    # 2-1. 最新の座標に基づいてカメラを計算
    camera_x = int(player.x - (SCREEN_WIDTH / 2) + (player.width / 2) + new_dungeon.shake_offset[0])
    camera_y = int(player.y - (SCREEN_HEIGHT / 2) + (player.height / 2) + new_dungeon.shake_offset[1])
    
    screen.fill((0, 0, 0))
    
    # 2-2. ダンジョンの描画
    new_dungeon.draw(screen, camera_x, camera_y, player)
    new_dungeon.update(dialog=ui_elements["dialog"])
    if getattr(new_dungeon, "next_dungeon", None):
        new_dungeon = new_dungeon.next_dungeon
    
    # 2-3. プレイヤーと視界の描画
    player.draw(screen, camera_x, camera_y)
    new_dungeon.draw_overhead(screen, camera_x, camera_y) # [NEW] 頭上タイルの描画
    draw_vision_overlay(screen, player, new_dungeon)
        
    # UIの描画
    if hasattr(ui_elements, "draw"):
        ui_elements.draw(screen, player, dungeon=new_dungeon, events=events)
    else:
        if ui_elements.get("status_bar"):
            ui_elements["status_bar"].draw(screen, player, new_dungeon.get_current_floor_level())

        draw_all_ui(screen, player, ui_elements["dialog"], ui_elements["confirm_dialog"], ui_elements["inventory_dialog"], 
                    ui_elements["status_dialog"], ui_elements["enhance_dialog"], ui_elements["item_action_dialog"], 
                    ui_elements["ore_selection_dialog"], ui_elements.get("shop_dialog"), ui_elements.get("stave_selection_dialog"), 
                    guild_dialog=ui_elements.get("guild_dialog"), warehouse_dialog=ui_elements.get("warehouse_dialog"), 
                    bank_dialog=ui_elements.get("bank_dialog"), menu_dialog=ui_elements.get("menu_dialog"), 
                    equip_dialog=ui_elements.get("equip_dialog"), 
                    stave_inv_dialog=ui_elements.get("stave_inventory_dialog"),
                    event_inv_dialog=ui_elements.get("event_inventory_dialog"),
                    teleport_dialog=ui_elements.get("teleport_dialog"),
                    guild_guide_dialog=ui_elements.get("guild_guide_dialog"),
                    dungeon=new_dungeon, events=events,
                    cutscene_manager=ui_elements.get("cutscene_manager"),
                    parameter_selection_dialog=ui_elements.get("parameter_selection_dialog"),
                    ore_gift_dialog=ui_elements.get("ore_gift_dialog"))
    
    # エリア名演出オーバーレイ（ダクソ風）
    if hasattr(ui_elements, "update_and_draw_area_overlay"):
        ui_elements.update_and_draw_area_overlay(screen)
    else:
        area_overlay = ui_elements.get("area_message_overlay")
        if area_overlay:
            area_overlay.update()
            area_overlay.draw(screen)

    # 死亡演出: 暗転オーバーレイ＋「力尽きた…」テキスト
    fade_alpha = game_state.get("death_fade_alpha", 0)
    death_step = game_state.get("death_sequence_step", 0)
    if fade_alpha > 0 or death_step in (1, 2):
        import pygame
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, min(fade_alpha, 255)))
        screen.blit(overlay, (0, 0))
        if death_step == 2:
            from systems.resources import font_medium
            text_surf = font_medium.render("力尽きた…", True, (200, 180, 180))
            tx = (SCREEN_WIDTH - text_surf.get_width()) // 2
            ty = (SCREEN_HEIGHT - text_surf.get_height()) // 2
            screen.blit(text_surf, (tx, ty))

    # [FIX] ダイアログ誤爆防止フラグのリセット
    if game_state.get("dialog_just_closed"):
        game_state["dialog_just_closed"] = False
    
    return new_dungeon
