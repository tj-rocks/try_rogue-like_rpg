import pygame
from systems.game_state import game_state, is_paused
from wordings import Text
from systems.resources import font_medium as font, clock, screen, title_bg, opening_imgs, ending_imgs
from systems.events import handle_events, active_direction_keys
from systems.entity_handler import update_dungeon_entities
from systems.ui import (
    Dialog, ConfirmDialog, InventoryDialog, StatusBar, StatusDialog, 
    EnhanceDialog, ItemActionDialog, OreSelectionDialog, ShopDialog,
    ParameterSelectionDialog,
    StaveSelectionDialog, GuildDialog, WarehouseDialog, BankDialog, handle_ui_events, draw_all_ui, 
    draw_vision_overlay, draw_opening_scene, draw_title_screen
)
from systems.item_handler import (
    make_use_item_callback, make_enhance_callback, make_discard_item_callback, make_recharge_callback
)
from systems.audio_manager import play_bgm
from constants import (
    GAME_TITLE, BGM_TITLE, BGM_OPENING, BGM_VILLAGE, BGM_DEFEAT,
    PLAYER_DEFENSE, SCREEN_WIDTH, SCREEN_HEIGHT
)

from components.sprites.enemy import Enemy
from components.sprites.player import Player
from systems.dungeon import Dungeon, warp_to_floor

# --- グローバル・ログ出力の制御 ---
import builtins
_original_print = builtins.print

def _dummy_print(*args, **kwargs):
    pass

from constants import ENABLE_DEBUG_LOGGING
if not ENABLE_DEBUG_LOGGING:
    builtins.print = _dummy_print

def toggle_debug_logging(dialog=None):
    import constants
    constants.ENABLE_DEBUG_LOGGING = not constants.ENABLE_DEBUG_LOGGING
    if constants.ENABLE_DEBUG_LOGGING:
        builtins.print = _original_print
        _original_print("[SYSTEM] デバッグログ表示をONにしました。")
        if dialog:
            dialog.text = "デバッグログ表示をONにしました。"
            dialog.is_active = True
            from constants import COMBAT_LOG_WAIT_FRAMES
            dialog.auto_close_timer = COMBAT_LOG_WAIT_FRAMES
    else:
        _original_print("[SYSTEM] デバッグログ表示をOFFにしました。")
        builtins.print = _dummy_print
        if dialog:
            dialog.text = "デバッグログ表示をOFFにしました。"
            dialog.is_active = True
            from constants import COMBAT_LOG_WAIT_FRAMES
            dialog.auto_close_timer = COMBAT_LOG_WAIT_FRAMES
