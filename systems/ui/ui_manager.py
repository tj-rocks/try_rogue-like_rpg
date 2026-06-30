from collections.abc import MutableMapping

from systems.ui.ui_dialog import Dialog, ConfirmDialog, ItemActionDialog, CutsceneManager
from systems.ui.ui_enhance import (
    EnhanceDialog,
    OreSelectionDialog,
    ParameterSelectionDialog,
    StaveSelectionDialog,
)
from systems.ui.ui_guild import GuildDialog, GuildGuideDialog
from systems.ui.ui_inventory import (
    EquipDialog,
    EventInventoryDialog,
    InventoryDialog,
    MenuDialog,
    StaveInventoryDialog,
)
from systems.ui.ui_misc import OreGiftDialog, TeleportDialog, draw_all_ui, handle_ui_events
from systems.ui.ui_shop import BankDialog, ShopDialog, WarehouseDialog
from systems.ui.ui_status import StatusBar, StatusDialog
from systems.ui_area_overlay import AreaMessageOverlay
from wordings import Text


class UIManager(MutableMapping):
    """Thin facade for UI creation, wiring, event handling, and drawing.

    It intentionally behaves like the old ui_elements dict so existing tests,
    debug tools, and gameplay code can migrate gradually.
    """

    def __init__(self, screen_width, screen_height):
        self.elements = {
            "dialog": Dialog(screen_width, screen_height),
            "confirm_dialog": ConfirmDialog(screen_width, screen_height),
            "inventory_dialog": InventoryDialog(screen_width, screen_height),
            "status_bar": StatusBar(screen_width, screen_height),
            "status_dialog": StatusDialog(screen_width, screen_height),
            "enhance_dialog": EnhanceDialog(screen_width, screen_height),
            "item_action_dialog": ItemActionDialog(screen_width, screen_height),
            "ore_selection_dialog": OreSelectionDialog(screen_width, screen_height),
            "parameter_selection_dialog": ParameterSelectionDialog(screen_width, screen_height),
            "shop_dialog": ShopDialog(screen_width, screen_height),
            "stave_selection_dialog": StaveSelectionDialog(screen_width, screen_height),
            "guild_dialog": GuildDialog(screen_width, screen_height),
            "warehouse_dialog": WarehouseDialog(screen_width, screen_height),
            "bank_dialog": BankDialog(screen_width, screen_height),
            "menu_dialog": MenuDialog(screen_width, screen_height),
            "equip_dialog": EquipDialog(screen_width, screen_height),
            "stave_inventory_dialog": StaveInventoryDialog(screen_width, screen_height),
            "event_inventory_dialog": EventInventoryDialog(screen_width, screen_height),
            "teleport_dialog": TeleportDialog(screen_width, screen_height),
            "guild_guide_dialog": GuildGuideDialog(screen_width, screen_height),
            "ore_gift_dialog": OreGiftDialog(screen_width, screen_height),
            "cutscene_manager": CutsceneManager(screen_width, screen_height),
            "area_message_overlay": AreaMessageOverlay(screen_width, screen_height),
        }

    def __getitem__(self, key):
        return self.elements[key]

    def __setitem__(self, key, value):
        self.elements[key] = value

    def __delitem__(self, key):
        del self.elements[key]

    def __iter__(self):
        return iter(self.elements)

    def __len__(self):
        return len(self.elements)

    @property
    def dialog(self):
        return self.elements["dialog"]

    @property
    def confirm_dialog(self):
        return self.elements["confirm_dialog"]

    @property
    def cutscene_manager(self):
        return self.elements["cutscene_manager"]

    @property
    def area_message_overlay(self):
        return self.elements["area_message_overlay"]

    def setup_relations(self, player, dungeon, game_state):
        inventory_dialog = self["inventory_dialog"]
        dialog = self["dialog"]
        stave_selection_dialog = self["stave_selection_dialog"]
        item_action_dialog = self["item_action_dialog"]
        enhance_dialog = self["enhance_dialog"]
        ore_selection_dialog = self["ore_selection_dialog"]
        parameter_selection_dialog = self.get("parameter_selection_dialog")
        menu_dialog = self["menu_dialog"]
        status_dialog = self["status_dialog"]
        confirm_dialog = self["confirm_dialog"]
        equip_dialog = self["equip_dialog"]
        stave_inv_dialog = self["stave_inventory_dialog"]
        event_inv_dialog = self["event_inventory_dialog"]

        inventory_dialog.setup(
            player,
            dialog,
            game_state,
            dungeon,
            stave_selection_dialog,
            item_action_dialog,
            confirm_dialog=confirm_dialog,
        )
        inventory_dialog.menu_dialog = menu_dialog

        stave_selection_dialog.setup(player, dialog)
        enhance_dialog.setup(player, dialog, ore_selection_dialog)
        item_action_dialog.setup(player, dialog, inventory_dialog, game_state)
        ore_selection_dialog.setup(
            enhance_dialog,
            confirm_dialog=confirm_dialog,
            player=player,
            cutscene_manager=self["cutscene_manager"],
        )
        if parameter_selection_dialog:
            parameter_selection_dialog.setup(
                enhance_dialog,
                confirm_dialog=confirm_dialog,
                player=player,
                cutscene_manager=self["cutscene_manager"],
            )
            ore_selection_dialog.parameter_selection_dialog = parameter_selection_dialog
            parameter_selection_dialog._back_dialog = ore_selection_dialog

        equip_dialog.setup(player, dialog, game_state, dungeon, None, item_action_dialog, confirm_dialog=confirm_dialog)
        equip_dialog.menu_dialog = menu_dialog

        stave_inv_dialog.setup(player, dialog, game_state, dungeon, None, item_action_dialog, confirm_dialog=confirm_dialog)
        stave_inv_dialog.menu_dialog = menu_dialog

        event_inv_dialog.setup(player, dialog, game_state, dungeon, None, item_action_dialog, confirm_dialog=confirm_dialog)
        event_inv_dialog.menu_dialog = menu_dialog

        self["guild_dialog"].cutscene_manager = self["cutscene_manager"]
        self["guild_dialog"].ore_gift_dialog = self.get("ore_gift_dialog")

        def on_inventory():
            inventory_dialog.is_active = True

        def on_equip():
            equip_dialog.is_active = True

        def on_staves():
            stave_inv_dialog.is_active = True

        def on_event():
            event_inv_dialog.is_active = True

        def on_status():
            status_dialog.mode = "MENU"
            status_dialog.is_active = True

        def on_quests():
            status_dialog.mode = "QUESTS"
            status_dialog.is_active = True

        def on_quit():
            confirm_dialog.text = Text.UI.QUIT_CONFIRM_MSG

            def do_quit():
                game_state["current_scene"] = "title"
                menu_dialog.is_active = False

            confirm_dialog.on_yes = do_quit
            confirm_dialog.on_no = None
            confirm_dialog.is_active = True

        menu_dialog.setup(on_inventory, on_equip, on_staves, on_event, on_status, on_quests, on_quit)
        menu_dialog.setup2(inventory_dialog, equip_dialog, status_dialog, stave_inv_dialog, event_inv_dialog)

    def handle_events(self, events, player=None, dungeon=None):
        return handle_ui_events(
            events,
            self["dialog"],
            self["confirm_dialog"],
            self["inventory_dialog"],
            self["status_dialog"],
            self["enhance_dialog"],
            self["item_action_dialog"],
            self["ore_selection_dialog"],
            menu_dialog=self.get("menu_dialog"),
            player=player,
            dungeon=dungeon,
            shop_dialog=self.get("shop_dialog"),
            stave_selection_dialog=self.get("stave_selection_dialog"),
            guild_dialog=self.get("guild_dialog"),
            warehouse_dialog=self.get("warehouse_dialog"),
            equip_dialog=self.get("equip_dialog"),
            stave_inv_dialog=self.get("stave_inventory_dialog"),
            event_inv_dialog=self.get("event_inventory_dialog"),
            bank_dialog=self.get("bank_dialog"),
            teleport_dialog=self.get("teleport_dialog"),
            guild_guide_dialog=self.get("guild_guide_dialog"),
            cutscene_manager=self.get("cutscene_manager"),
            parameter_selection_dialog=self.get("parameter_selection_dialog"),
            ore_gift_dialog=self.get("ore_gift_dialog"),
        )

    def draw(self, screen, player, dungeon=None, events=None):
        if self.get("status_bar") and dungeon:
            self["status_bar"].draw(screen, player, dungeon.get_current_floor_level())

        draw_all_ui(
            screen,
            player,
            self["dialog"],
            self["confirm_dialog"],
            self["inventory_dialog"],
            self["status_dialog"],
            self["enhance_dialog"],
            self["item_action_dialog"],
            self["ore_selection_dialog"],
            self.get("shop_dialog"),
            self.get("stave_selection_dialog"),
            guild_dialog=self.get("guild_dialog"),
            warehouse_dialog=self.get("warehouse_dialog"),
            bank_dialog=self.get("bank_dialog"),
            menu_dialog=self.get("menu_dialog"),
            equip_dialog=self.get("equip_dialog"),
            stave_inv_dialog=self.get("stave_inventory_dialog"),
            event_inv_dialog=self.get("event_inventory_dialog"),
            teleport_dialog=self.get("teleport_dialog"),
            guild_guide_dialog=self.get("guild_guide_dialog"),
            dungeon=dungeon,
            events=events,
            cutscene_manager=self.get("cutscene_manager"),
            parameter_selection_dialog=self.get("parameter_selection_dialog"),
            ore_gift_dialog=self.get("ore_gift_dialog"),
        )

    def update_and_draw_area_overlay(self, screen):
        area_overlay = self.get("area_message_overlay")
        if area_overlay:
            area_overlay.update()
            area_overlay.draw(screen)
