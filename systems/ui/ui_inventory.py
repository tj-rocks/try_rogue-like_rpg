import pygame
from systems.game_state import game_state
from systems.resources import font_small
from constants import (
    KEY_CONFIRM, KEY_CANCEL, SOUND_SELECT, SOUND_CANCEL
)
from wordings import Text
from systems.ui.ui_base import (
    get_standard_upper_layout, draw_dialog_frame, draw_text_wrapped,
    BaseListDialog, EQUIP_STAT_LABEL_MAP, EQUIP_MAGIC_LABEL_MAP, format_stat_value
)


class InventoryDialog(BaseListDialog):
    """アイテム（消耗品）一覧ダイアログ"""
    STATE_KEY = "inventory_active"

    def __init__(self, screen_width, screen_height):
        super().__init__(screen_width, screen_height)
        self.row_height = 36
        self.item_data = []
        self.on_select = None
        self.action_dialog = None
        self.player = None
        self.dungeon = None
        self._path_cache = {}
        self._last_debug_name = None

    def draw_right_panel(self, screen, player, sep_x, detail_y_offset):
        if not player or self.cursor_idx >= len(self.item_data): return
        data = self.item_data[self.cursor_idx]
        if not data or data[0] == "cancel": return

        itype, key = data
        if itype not in ("weapon", "armor", "shield", "accessory", "stave"):
            lines = self.get_detail_lines(player)
            if lines:
                draw_text_wrapped(screen, self.font, "\n".join(lines),
                                  sep_x + 30, self.y + 80 + detail_y_offset, self.width // 2 - 60, color=(220, 230, 240))
            return

        inv = getattr(player, itype + "_inventory", [])
        inst = player._find_equip_inst(inv, key)
        if not inst: return

        from wordings import Text
        S_MAP = {"attack_bonus": "攻撃力", "defense_bonus": "防御力", "hp_bonus": "最大HP",
                 "dex_bonus": "器用さ", "crit_bonus": "会心率",
                 "block_chance_close": "近距離回避",
                 "block_chance_ranged": "遠距離回避", "aggro_mod": "感知補正", "pursuit_evasion": "追跡妨害",
                 "armor_penetration": Text.UI.STAT_ARMOR_PENETRATION, "stupidity": Text.UI.STAT_CONFUSION_ICON,
                 "accuracy_bonus_close": "命中率"}
        MAGIC_MAP = {
            "magic_fire_damage":    "[炎]ダメ",
            "magic_fire_range":     "[炎]射程",
            "magic_heal_ratio":     "[癒]回復量",
            "magic_knockback_damage":"[風]吹飛ダメ",
            "magic_invincible_turns":"[聖]無敵ターン",
            "magic_stave_bonus":     "[魔]杖回数",
            "magic_light_stave_bonus": "[光]燈杖回",
            "magic_barrier_turns":     "障壁ターン",
        }

        def fmt(val):
            if val % 1 == 0:
                val_str = str(int(val))
            else:
                val_str = str(round(val, 2))
            return f"+{val_str}" if val > 0 else val_str

        param_texts = []
        for k, label in S_MAP.items():
            val = inst.get_stat(k, 0)
            if hasattr(inst, 'enhance') and inst.enhance > 0 and hasattr(inst, 'get_enhance_bonus'):
                val += inst.get_enhance_bonus(k)
            if val:
                is_pct = k in ("crit_bonus", "block_chance_close", "block_chance_ranged", "armor_penetration", "accuracy_bonus_close")
                val_to_use = val * 100 if is_pct and isinstance(val, float) else val
                param_texts.append(f"{label}: {fmt(val_to_use)}%" if is_pct else f"{label}: {fmt(val)}")

        for mk, mlabel in MAGIC_MAP.items():
            mval = inst.get_stat(mk, 0)
            if mval:
                is_pct = mk in ("magic_fire_damage", "magic_heal_ratio", "magic_knockback_damage")
                val_to_use = mval * 100 if is_pct and isinstance(mval, float) else mval
                param_texts.append(f"{mlabel}: {fmt(val_to_use)}%" if is_pct else f"{mlabel}: {fmt(mval)}")

        desc = inst.get_stat("describe", "")
        self.draw_equip_detail_right_panel(screen, inst, param_texts, desc, sep_x, detail_y_offset)

    def get_title(self): return Text.UI.INVENTORY_TITLE

    def setup(self, player, dialog, game_state, dungeon, stave_selection_dialog, item_action_dialog, confirm_dialog=None):
        from systems.item_handler import make_use_item_callback
        self.player = player
        self.dialog = dialog
        self.dungeon = dungeon
        self.on_select = make_use_item_callback(
            player, dialog, self, game_state,
            stave_selection_dialog=stave_selection_dialog,
            confirm_dialog=confirm_dialog
        )
        self.action_dialog = item_action_dialog

    def update_items_from_player(self, player):
        labels, data = [], []
        from constants import CONSUMABLE_DATA
        items_to_sort = list(player.items)
        items_to_sort.sort(key=lambda item: CONSUMABLE_DATA.get(item["key"], {}).get("name", item["key"]).lower())
        for item in items_to_sort:
            k, c = item["key"], item.get("count", 1)
            n = CONSUMABLE_DATA.get(k, {}).get("name", k)
            labels.append(f"{n} x{c}" if c > 1 else n); data.append(("consumable", k))
        labels.append(Text.UI.QUIT); data.append(("cancel", None))
        self.items, self.item_data = labels, data

    def get_item_image_path(self, item, idx, player):
        if idx >= len(self.item_data) or not player: return None
        itype, key_or_iid = self.item_data[idx]
        if itype == "cancel": return None

        from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, ACCESSORY_DATA, STAVE_DATA, CONSUMABLE_DATA
        catalog = {"weapon": WEAPON_DATA, "armor": ARMOR_DATA, "shield": SHIELD_DATA, "accessory": ACCESSORY_DATA, "stave": STAVE_DATA}

        if itype in ("weapon", "armor", "shield", "accessory", "stave"):
            inv = getattr(player, itype + "_inventory", [])
            inst = player._find_equip_inst(inv, key_or_iid)
            if not inst: return None

            cache_key = (itype, inst.key)
            if cache_key in self._path_cache:
                return self._path_cache[cache_key]

            data = catalog.get(itype, {}).get(inst.key, {})
            path = data.get("image_path")
            if not path and data.get("image_dir"):
                import os
                idir = data.get("image_dir")
                if os.path.exists(idir):
                    p = os.path.join(idir, "down.png")
                    if os.path.exists(p): path = p
                    else:
                        p = os.path.join(idir, f"{inst.key}.png")
                        if os.path.exists(p): path = p
                        else:
                            try:
                                files = [f for f in os.listdir(idir) if f.endswith(".png")]
                                if files: path = os.path.join(idir, files[0])
                            except: pass

            self._path_cache[cache_key] = path
            return path
        else:
            return CONSUMABLE_DATA.get(key_or_iid, {}).get("image_path")

    def get_item_label(self, item, idx): return item
    def get_item_color(self, item, idx, is_selected):
        if is_selected: return (255, 255, 100)
        if item.startswith("E:"): return (255, 255, 100)
        return (255, 255, 255)

    def get_detail_lines(self, player):
        if not player or self.cursor_idx >= len(self.item_data): return []
        data = self.item_data[self.cursor_idx]
        if not data or data[0] == "cancel": return []
        return self._build_detail_lines(player, data)

    def _build_detail_lines(self, player, data):
        itype, key = data
        lines = []

        if itype in ("weapon", "armor", "shield", "accessory", "stave"):
            inv = getattr(player, itype + "_inventory", [])
            inst = player._find_equip_inst(inv, key)
            if not inst: return []
            lines.append(inst.get_name())
            if getattr(self, '_last_debug_name', None) != inst.get_name():
                if hasattr(inst, 'stats'):
                    debug_stats = inst.stats
                else:
                    debug_stats = "N/A (Stave)"
                debug_enhance = getattr(inst, 'enhance', 0)
                def_bonus = inst.get_enhance_bonus("defense_bonus") if hasattr(inst, 'get_enhance_bonus') else 0
                base_def = inst.get_stat("defense_bonus", 0)
                print(f"[DEBUG] {inst.get_name()}: enhance={debug_enhance}, stats={debug_stats}")
                print(f"[DEBUG]   defense_bonus: base={base_def}, enhance_bonus={def_bonus}, total={base_def + def_bonus}")
                self._last_debug_name = inst.get_name()
            for k, label in EQUIP_STAT_LABEL_MAP.items():
                if itype == "stave":
                    val = inst.get_stat(k, 0)
                else:
                    val = inst.get_stat(k, 0)
                    if inst.enhance > 0:
                        val += inst.get_enhance_bonus(k)
                if val:
                    is_pct = k in ("crit_bonus", "block_chance_close", "block_chance_ranged", "armor_penetration")
                    val_to_use = val * 100 if is_pct and isinstance(val, float) else val
                    lines.append(f"{label}: {format_stat_value(val_to_use)}%" if is_pct else f"{label}: {format_stat_value(val)}")
            for mk, mlabel in EQUIP_MAGIC_LABEL_MAP.items():
                mval = inst.get_stat(mk, 0)
                if mval:
                    is_pct = mk in ("magic_fire_damage", "magic_heal_ratio", "magic_knockback_damage")
                    val_to_use = mval * 100 if is_pct and isinstance(mval, float) else mval
                    lines.append(f"{mlabel}: {format_stat_value(val_to_use)}%" if is_pct else f"{mlabel}: {format_stat_value(mval)}")
            desc = inst.get_stat("describe", "")
            if desc: lines.extend(["", desc])
        else:
            from constants import CONSUMABLE_DATA
            info = CONSUMABLE_DATA.get(key, {})
            lines.append(info.get("name", key))
            desc = info.get("describe", "")
            if desc: lines.extend(["", desc])
        return lines

    def handle_events(self, events):
        if not self.is_active: return
        from systems.audio_manager import play_sfx
        action = self._navigate(events)
        if action == "cancel":
            play_sfx(SOUND_CANCEL); self._close_back()
        elif action == "confirm":
            if self.cursor_idx < len(self.item_data):
                data = self.item_data[self.cursor_idx]
                if data:
                    itype, iid = data
                    if itype == "cancel":
                        play_sfx(SOUND_CANCEL); self._close_back(); return
                    play_sfx(SOUND_SELECT)
                    if self.action_dialog:
                        from systems.item_handler import make_discard_item_callback, make_unequip_item_callback
                        on_discard = make_discard_item_callback(self.player, self.dialog, self, game_state)
                        on_unequip = make_unequip_item_callback(self.player, self.dialog, self, game_state)
                        self.action_dialog.setup_for_item(data, self.on_select, on_discard, on_unequip)
                        self.action_dialog.is_active = True

    def draw(self, screen, player=None):
        if player: self.update_items_from_player(player)
        super().draw(screen, player)


class EquipDialog(InventoryDialog):
    """装備品専用管理画面（武器・鎧・盾・カンテラ）"""
    STATE_KEY = "equip_active"

    def get_title(self): return Text.UI.EQUIP_TITLE

    def update_items_from_player(self, player):
        labels, data = [], []
        weapons = list(player.weapon_inventory)
        armors = list(player.armor_inventory)
        shields = list(getattr(player, "shield_inventory", []))
        accessories = list(getattr(player, "accessory_inventory", []))

        weapons.sort(key=lambda x: x.get_name().lower())
        armors.sort(key=lambda x: x.get_name().lower())
        shields.sort(key=lambda x: x.get_name().lower())
        accessories.sort(key=lambda x: x.get_name().lower())

        for inst in weapons:
            prefix = "E:" if inst.iid == player.equipped_weapon else ""
            labels.append(prefix + inst.get_name()); data.append(("weapon", inst.iid))
        for inst in armors:
            prefix = "E:" if inst.iid == player.equipped_armor else ""
            labels.append(prefix + inst.get_name()); data.append(("armor", inst.iid))
        for inst in shields:
            prefix = "E:" if inst.iid == player.equipped_shield else ""
            labels.append(prefix + inst.get_name()); data.append(("shield", inst.iid))
        for inst in accessories:
            prefix = "E:" if inst.iid == player.equipped_accessory else ""
            labels.append(prefix + inst.get_name()); data.append(("accessory", inst.iid))
        labels.append(Text.UI.QUIT); data.append(("cancel", None))
        self.items, self.item_data = labels, data


class StaveInventoryDialog(InventoryDialog):
    """杖専用管理画面"""
    STATE_KEY = "stave_inventory_active"

    def __init__(self, screen_width, screen_height):
        super().__init__(screen_width, screen_height)
        self._last_stave_iids = None

    def get_title(self):
        return Text.UI.STAVE_TITLE

    def update_items_from_player(self, player):
        labels, data = [], []
        staves = list(player.stave_inventory)
        staves.sort(key=lambda x: x.get_name().lower())

        current_iids = tuple(inst.iid for inst in staves)

        if current_iids != self._last_stave_iids:
            print(f"[STAVE-DEBUG] update_items_from_player called, stave_inventory={getattr(player, 'stave_inventory', None)}")
            for inst in staves:
                print(f"[STAVE-DEBUG] Adding stave: {inst.get_name_with_charges()} (iid={inst.iid})")
            self._last_stave_iids = current_iids

        for inst in staves:
            labels.append(inst.get_name_with_charges()); data.append(("stave", inst.iid))
        labels.append(Text.UI.QUIT); data.append(("cancel", None))
        self.items, self.item_data = labels, data


class EventInventoryDialog(InventoryDialog):
    """貴重品（イベントアイテム）一覧ダイアログ"""
    STATE_KEY = "event_item_active"

    def get_title(self): return Text.UI.EVENT_ITEM_TITLE

    def update_items_from_player(self, player):
        labels, data = [], []
        from constants import CONSUMABLE_DATA
        items_to_sort = list(player.event_items)
        items_to_sort.sort(key=lambda item: CONSUMABLE_DATA.get(item["key"], {}).get("name", item["key"]).lower())
        for item in items_to_sort:
            k, c = item["key"], item.get("count", 1)
            n = CONSUMABLE_DATA.get(k, {}).get("name", k)
            labels.append(f"{n} x{c}" if c > 1 else n); data.append(("consumable", k))
        labels.append(Text.UI.QUIT); data.append(("cancel", None))
        self.items, self.item_data = labels, data

    def handle_events(self, events):
        if not self.is_active: return
        from systems.audio_manager import play_sfx
        action = self._navigate(events)
        if action == "cancel":
            play_sfx(SOUND_CANCEL); self._close_back()
        elif action == "confirm":
            if self.cursor_idx < len(self.item_data):
                itype, _ = self.item_data[self.cursor_idx]
                if itype == "cancel":
                    play_sfx(SOUND_CANCEL); self._close_back()
                else:
                    play_sfx(SOUND_SELECT)


class MenuDialog(BaseListDialog):
    """メインメニュー (Mキー)"""
    STATE_KEY = "menu_active"

    def __init__(self, screen_width, screen_height):
        super().__init__(screen_width, screen_height)
        self.row_height = 40
        self.callbacks = []
        self._dungeon = None
        self.items = [
            (Text.UI.MENU_ITEMS,      "所持アイテム（薬・巻物など）の一覧を表示します"),
            (Text.UI.MENU_EQUIP,      "武器・鎧・盾・カンテラの管理画面を開きます"),
            (Text.UI.MENU_STAVES,     "所持している杖の管理画面を開きます"),
            (Text.UI.MENU_EVENT_ITEMS, "冒険者の証などの貴重品を確認します"),
            (Text.UI.MENU_STATUS,     "プレイヤーのステータスを表示します"),
            (Text.UI.MENU_QUESTS,     "現在のクエスト進捗を確認します"),
            (Text.UI.MENU_QUIT,       "タイトル画面に戻ります"),
            (Text.UI.MENU_MAP_TOGGLE, "ミニマップの表示・非表示を切り替えます"),
            (Text.UI.MENU_BACK,       "メニューを閉じます"),
        ]

    def setup(self, on_items, on_equip, on_staves, on_event, on_status, on_quests, on_quit):
        self.callbacks = [on_items, on_equip, on_staves, on_event, on_status, on_quests, on_quit]

    def get_title(self): return Text.UI.MENU_TITLE

    def get_item_label(self, item, idx):
        label, _ = item
        if idx == 7:
            st = "ON" if (self._dungeon and getattr(self._dungeon, "show_map", True)) else "OFF"
            return f"{label} [{st}]"
        return label

    def get_detail_lines(self, player):
        return [self.items[self.cursor_idx][1]] if self.items else []

    def handle_events(self, events, dungeon=None):
        if not self.is_active: return
        self._dungeon = dungeon
        from systems.audio_manager import play_sfx
        action = self._navigate(events)
        if action == "cancel":
            play_sfx(SOUND_CANCEL); self.is_active = False
        elif action == "confirm":
            idx = self.cursor_idx
            if idx == len(self.items) - 1:
                play_sfx(SOUND_CANCEL); self.is_active = False
            elif idx == 7:
                if dungeon: dungeon.show_map = not getattr(dungeon, "show_map", True)
                play_sfx(SOUND_SELECT)
            else:
                play_sfx(SOUND_SELECT)
                if 0 <= idx < len(self.callbacks):
                    cb = self.callbacks[idx]
                    cb()
                self.is_active = False

    def setup2(self, inventory_dialog, equip_dialog, status_dialog, stave_inv_dialog=None, event_inv_dialog=None):
        if inventory_dialog: inventory_dialog._back_dialog = self
        if equip_dialog:     equip_dialog._back_dialog = self
        if status_dialog:    status_dialog._back_dialog = self
        if stave_inv_dialog: stave_inv_dialog._back_dialog = self
        if event_inv_dialog: event_inv_dialog._back_dialog = self

    def draw(self, screen, dungeon=None):
        self._dungeon = dungeon
        super().draw(screen, None)
