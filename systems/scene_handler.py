import pygame
import os
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE
from systems.ui import handle_ui_events, draw_vision_overlay, draw_all_ui
from systems.game_state import is_paused
from systems.entity_handler import update_dungeon_entities
from systems.death_handler import handle_death_sequence

def handle_opening(screen, events, game_state, opening_imgs, start_new_game_func):
    """
    オープニング演出を処理する。
    """
    screen.fill((0, 0, 0))
    game_state["opening_alpha"] = min(255, game_state["opening_alpha"] + 2)
    idx = game_state["opening_index"]
    
    if idx < len(opening_imgs):
        from systems.ui import draw_opening_scene
        draw_opening_scene(screen, opening_imgs[idx], idx, game_state["opening_alpha"])
    
    game_state["opening_timer"] += 1
    
    skip = False
    for event in events:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_z):
            skip = True
    
    if game_state["opening_timer"] > 600 or skip:
        game_state["opening_timer"] = 0
        game_state["opening_alpha"] = 0
        game_state["opening_index"] += 1
        
        if game_state["opening_index"] >= len(opening_imgs):
            game_state["opening_index"] = 0
            game_state["opening_seen"] = True
            from constants import SAVE_DATA_PATH
            if not os.path.exists(SAVE_DATA_PATH):
                game_state["current_scene"] = "title"
            else:
                start_new_game_func()
    
    return game_state["current_scene"]
    
def handle_ending(screen, events, game_state, ending_imgs):
    """
    エンディング演出を処理する。
    """
    screen.fill((0, 0, 0))
    game_state["ending_alpha"] = min(255, game_state.get("ending_alpha", 0) + 2)
    idx = game_state.get("ending_index", 0)
    
    if idx < len(ending_imgs):
        from systems.ui import draw_opening_scene
        draw_opening_scene(screen, ending_imgs[idx], idx, game_state["ending_alpha"])
    
    game_state["ending_timer"] = game_state.get("ending_timer", 0) + 1
    
    skip = False
    for event in events:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_z):
            skip = True
    
    if game_state["ending_timer"] > 600 or skip:
        game_state["ending_timer"] = 0
        game_state["ending_alpha"] = 0
        game_state["ending_index"] = idx + 1
        
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
            if event.key == pygame.K_UP:
                game_state["title_selected_idx"] = 0
            elif event.key == pygame.K_DOWN and has_save:
                game_state["title_selected_idx"] = 1
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_z):
                if game_state["title_selected_idx"] == 0:
                    from systems.game_state import game_state as gs
                    if gs["opening_seen"]:
                        start_new_game_func()
                    else:
                        game_state["opening_index"] = 0
                        game_state["opening_timer"] = 0
                        game_state["opening_alpha"] = 0
                        game_state["current_scene"] = "opening"
                else:
                    continue_game_func()
    
    return game_state["current_scene"]

def handle_game(screen, events, player, dungeon, ui_elements, game_state):
    """
    ゲーム本編（探索・戦闘）のロジックを処理する。
    """
    # UIイベント処理
    handle_ui_events(events, 
                     ui_elements["dialog"], ui_elements["confirm_dialog"], ui_elements["inventory_dialog"], 
                     ui_elements["status_dialog"], ui_elements["enhance_dialog"], ui_elements["item_action_dialog"], 
                     ui_elements["ore_selection_dialog"], menu_dialog=ui_elements.get("menu_dialog"), player=player, dungeon=dungeon, 
                     shop_dialog=ui_elements.get("shop_dialog"), stave_selection_dialog=ui_elements.get("stave_selection_dialog"), 
                     guild_dialog=ui_elements.get("guild_dialog"), warehouse_dialog=ui_elements.get("warehouse_dialog"), 
                     equip_dialog=ui_elements.get("equip_dialog"),
                     stave_inv_dialog=ui_elements.get("stave_inventory_dialog"),
                     event_inv_dialog=ui_elements.get("event_inventory_dialog"),
                     cutscene_manager=ui_elements.get("cutscene_manager"))
    
    screen.fill((0, 0, 0))
    
    # カメラ計算 (端数が出ないように整数に変換)
    camera_x = int(player.x - (SCREEN_WIDTH / 2) + (player.width / 2) + dungeon.shake_offset[0])
    camera_y = int(player.y - (SCREEN_HEIGHT / 2) + (player.height / 2) + dungeon.shake_offset[1])
    
    # 描画と更新
    dungeon.draw(screen, camera_x, camera_y)
    dungeon.update(dialog=ui_elements["dialog"])
    if getattr(dungeon, "next_dungeon", None):
        dungeon = dungeon.next_dungeon
    
    player.update(screen, camera_x, camera_y, dungeon, ui_elements["dialog"], events)
    draw_vision_overlay(screen, player, dungeon)
    
    # エンティティ更新（ポーズ中や死亡演出中は停止）
    if not is_paused() and game_state.get("death_sequence_step", 0) == 0:
        update_dungeon_entities(dungeon, player, ui_elements["dialog"])
 
    # 死亡演出の更新
    new_dungeon = handle_death_sequence(player, dungeon, ui_elements["dialog"], game_state)
    is_death_active = game_state.get("death_sequence_step", 0) > 0
        
    # 死亡演出中以外は罠や階段、モンスター氾濫をチェック
    if not is_death_active:
        if not player.is_falling:
            new_dungeon = new_dungeon.check_traps(player, ui_elements["dialog"])
            new_dungeon = new_dungeon.check_overflow(player, ui_elements["dialog"])
        new_dungeon = new_dungeon.check_stairs(player, ui_elements["confirm_dialog"], ui_elements["dialog"])
    
    # カットシーンの更新
    if ui_elements.get("cutscene_manager"):
        ui_elements["cutscene_manager"].update()
        
    # UIの描画
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
                dungeon=new_dungeon, events=events,
                cutscene_manager=ui_elements.get("cutscene_manager"))
    
    return new_dungeon
