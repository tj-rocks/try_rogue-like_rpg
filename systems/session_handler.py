
from components.sprites.player import Player
from systems.dungeon import warp_to_floor
from systems.ui import UIManager
from wordings import Text
from constants import SCREEN_WIDTH, SCREEN_HEIGHT


def _ensure_display():
    import pygame
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init():
        pygame.display.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    return screen

def setup_ui_relations(ui_elements, player, dungeon, game_state):
    """
    UIコンポーネント同士、およびプレイヤーやダンジョンとの依存関係をセットアップする。
    """
    if hasattr(ui_elements, "setup_relations"):
        ui_elements.setup_relations(player, dungeon, game_state)
        return

    # 既存の UI オブジェクトを取得（辞書形式を想定）
    inventory_dialog = ui_elements["inventory_dialog"]
    dialog = ui_elements["dialog"]
    stave_selection_dialog = ui_elements["stave_selection_dialog"]
    item_action_dialog = ui_elements["item_action_dialog"]
    enhance_dialog = ui_elements["enhance_dialog"]
    ore_selection_dialog = ui_elements["ore_selection_dialog"]
    parameter_selection_dialog = ui_elements.get("parameter_selection_dialog")
    menu_dialog = ui_elements["menu_dialog"]
    status_dialog = ui_elements["status_dialog"]
    confirm_dialog = ui_elements["confirm_dialog"]
    equip_dialog = ui_elements["equip_dialog"]
    stave_inv_dialog = ui_elements["stave_inventory_dialog"]
    event_inv_dialog = ui_elements["event_inventory_dialog"]

    # セットアップ実行
    inventory_dialog.setup(player, dialog, game_state, dungeon, stave_selection_dialog, item_action_dialog, confirm_dialog=confirm_dialog)
    inventory_dialog.menu_dialog = menu_dialog # 参照を持たせる
    
    stave_selection_dialog.setup(player, dialog)
    enhance_dialog.setup(player, dialog, ore_selection_dialog)
    item_action_dialog.setup(player, dialog, inventory_dialog, game_state)
    ore_selection_dialog.setup(enhance_dialog, confirm_dialog=confirm_dialog, player=player, cutscene_manager=ui_elements["cutscene_manager"])
    if parameter_selection_dialog:
        parameter_selection_dialog.setup(enhance_dialog, confirm_dialog=confirm_dialog, player=player, cutscene_manager=ui_elements["cutscene_manager"])
        ore_selection_dialog.parameter_selection_dialog = parameter_selection_dialog
        parameter_selection_dialog._back_dialog = ore_selection_dialog
    
    equip_dialog.setup(player, dialog, game_state, dungeon, None, item_action_dialog, confirm_dialog=confirm_dialog)
    equip_dialog.menu_dialog = menu_dialog
    
    stave_inv_dialog.setup(player, dialog, game_state, dungeon, None, item_action_dialog, confirm_dialog=confirm_dialog)
    stave_inv_dialog.menu_dialog = menu_dialog
    
    event_inv_dialog.setup(player, dialog, game_state, dungeon, None, item_action_dialog, confirm_dialog=confirm_dialog)
    event_inv_dialog.menu_dialog = menu_dialog
    
    ui_elements["guild_dialog"].cutscene_manager = ui_elements["cutscene_manager"]
    ui_elements["guild_dialog"].ore_gift_dialog = ui_elements.get("ore_gift_dialog")

    # メニューのコールバック設定
    def on_inventory(): inventory_dialog.is_active = True
    def on_equip(): equip_dialog.is_active = True
    def on_staves(): stave_inv_dialog.is_active = True
    def on_event(): event_inv_dialog.is_active = True
    def on_status():
        status_dialog.mode = "MENU"   # カテゴリ一覧から選ぶ
        status_dialog.is_active = True
    def on_quests():
        status_dialog.mode = "QUESTS"
        status_dialog.is_active = True
    def on_quit():
        confirm_dialog.text = Text.UI.QUIT_CONFIRM_MSG
        def do_quit():
            game_state["current_scene"] = "title"
            menu_dialog.is_active = False # メニューも閉じる
        confirm_dialog.on_yes = do_quit
        confirm_dialog.on_no = None
        confirm_dialog.is_active = True

    menu_dialog.setup(on_inventory, on_equip, on_staves, on_event, on_status, on_quests, on_quit)
    menu_dialog.setup2(inventory_dialog, equip_dialog, status_dialog, stave_inv_dialog, event_inv_dialog)

def start_new_game(ui_elements, game_state):
    """
    新しいゲームセッションを開始する。
    """
    import pygame
    from systems.dungeon import Dungeon
    screen = _ensure_display()
    Dungeon.preload_all_themes(screen)
    player = Player()
    dungeon = warp_to_floor(0, player, spawn_reason="new_game")
    
    setup_ui_relations(ui_elements, player, dungeon, game_state)
    game_state["current_scene"] = "game"
    
    return player, dungeon

def continue_game(ui_elements, game_state, player):
    """
    保存されたデータからゲームセッションを再開する。
    1. 中断セーブ(SAVE_SUSPEND_PATH)があれば優先してロードし、ロード後に削除する。
    2. なければ永続セーブ(SAVE_OFFICIAL_PATH)をロードする。
    """
    import pygame
    from systems.dungeon import Dungeon
    screen = _ensure_display()
    Dungeon.preload_all_themes(screen)
    from systems.data_loader import SAVE_OFFICIAL_PATH, SAVE_SUSPEND_PATH
    import os
    
    target_path = None
    is_suspend = False
    
    if os.path.exists(SAVE_SUSPEND_PATH):
        target_path = SAVE_SUSPEND_PATH
        is_suspend = True
    elif os.path.exists(SAVE_OFFICIAL_PATH):
        target_path = SAVE_OFFICIAL_PATH
        
    if target_path and player.load_from_file(target_path):
        print(f"[SESSION] Game loaded from: {target_path}")
        if player.apply_new_game_plus_start():
            print("[SESSION] New Game+ start applied: guild rank and GP reset.")

        floor = player.current_floor if hasattr(player, "current_floor") else 0
        dungeon = warp_to_floor(floor, player, spawn_reason="continue")
        
        # 再開時にUI状態やターン状態をクリーンにする
        for k in game_state:
            if k.endswith("_active"):
                game_state[k] = False
        game_state["turn_state"] = "player"
        game_state["dialog_just_closed"] = True # 初動の誤爆防止

        setup_ui_relations(ui_elements, player, dungeon, game_state)
        game_state["current_scene"] = "game"
        return player, dungeon
    else:
        # ロード失敗時は新規開始
        return start_new_game(ui_elements, game_state)

def init_ui_elements(screen_width, screen_height):
    """
    全てのUIコンポーネントを初期化し、辞書で返す。
    """
    return UIManager(screen_width, screen_height)
