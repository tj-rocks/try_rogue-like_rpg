import pygame
from systems.game_state import game_state
from systems.resources import font_small, font_small_bold, font_medium
from constants import (
    KEY_MOVE_UP, KEY_MOVE_DOWN, KEY_CONFIRM, KEY_CANCEL, PCT_STAT_KEYS
)
from wordings import Text
from systems.ui.ui_base import (
    get_standard_upper_layout, draw_dialog_frame, draw_text_wrapped,
    BaseListDialog, StateKeyMixin,
    EQUIP_STAT_LABEL_MAP, EQUIP_MAGIC_LABEL_MAP, format_stat_value
)
from systems.ui.ui_inventory import InventoryDialog


class OreSelectionDialog(StateKeyMixin):
    """鍛冶屋で装備選択後に「どの鉱石を使うか」を選ぶダイアログ"""
    STATE_KEY = "ore_selection_active"
    def __init__(self, screen_width, screen_height):
        self.x, self.y, self.width, self.height = get_standard_upper_layout(screen_width, screen_height)
        self.font = font_medium
        self.cursor_idx = 0
        self.target_item_data = None
        self.available_ores = []
        self.selection_block_reason = None
        self.on_confirm = None
        self.parameter_selection_dialog = None
        self.confirm_dialog = None
        self.player_ref = None
        self.cutscene_manager = None

    def setup(self, enhance_dialog, confirm_dialog=None, player=None, cutscene_manager=None):
        self.on_confirm = enhance_dialog.on_select
        self.confirm_dialog = confirm_dialog
        self.player_ref = player
        self.cutscene_manager = cutscene_manager

    def update_from_player(self, player):
        from constants import CONSUMABLE_DATA
        inst = None
        if self.target_item_data:
            item_type, iid = self.target_item_data
            if item_type == "weapon": inv = player.weapon_inventory
            elif item_type == "armor": inv = player.armor_inventory
            else: inv = getattr(player, "shield_inventory", [])
            inst = player._find_equip_inst(inv, iid)

        ores = {}
        for item in player.items:
            item_key = item["key"]
            data = CONSUMABLE_DATA.get(item_key, {})
            if data.get("effect") == "material":
                if inst is not None and not inst.is_ore_compatible(item_key):
                    continue
                if item_key not in ores:
                    ores[item_key] = {
                        "name": data.get("name", item_key),
                        "bonus": data.get("enhance_bonus", 1)
                    }
        self.available_ores = [(k, v["name"], v["bonus"]) for k, v in ores.items()]
        self.available_ores.append(("cancel", Text.UI.QUIT, 0))

    def handle_events(self, events):
        if not self.is_active: return
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == KEY_MOVE_UP:
                    if self.cursor_idx > 0: self.cursor_idx -= 1
                    else: self.cursor_idx = len(self.available_ores) - 1
                elif event.key == KEY_MOVE_DOWN:
                    if self.cursor_idx < len(self.available_ores) - 1: self.cursor_idx += 1
                    else: self.cursor_idx = 0
                elif event.key == KEY_CANCEL: self.is_active = False
                elif event.key == KEY_CONFIRM:
                    if 0 <= self.cursor_idx < len(self.available_ores):
                        ore_key = self.available_ores[self.cursor_idx][0]
                        if ore_key == "cancel":
                            self.is_active = False
                            return
                        self.is_active = False
                        if getattr(self, "parameter_selection_dialog", None) and getattr(self, "player_ref", None) and self.target_item_data:
                            psd = self.parameter_selection_dialog
                            player = self.player_ref
                            item_type, iid = self.target_item_data
                            psd.update_from_selection(player, item_type, iid, ore_key)
                            if getattr(psd, "selection_block_reason", None) == "no_skill_target":
                                from systems.game_state import game_state
                                dialog = game_state.get("dialog")
                                if dialog:
                                    dialog.text = "使えません。\nこの装備には金の鉱石で伸ばせる技がない。"
                                    dialog.is_active = True
                            elif psd.max_limit_reached:
                                from systems.game_state import game_state
                                dialog = game_state.get("dialog")
                                if dialog:
                                    dialog.text = "この装備はこれ以上鍛えられないよ。\n十分に仕上がっている。"
                                    dialog.is_active = True
                            else:
                                psd.is_active = True

    def draw(self, screen):
        if not self.is_active: return
        from constants import CONSUMABLE_DATA

        draw_dialog_frame(screen, self.x, self.y, self.width, self.height, alpha=240)
        screen.blit(font_small_bold.render(Text.UI.USE_WHICH_ORE, True, (255, 200, 100)), (self.x + 30, self.y + 18))

        sep_x = self.x + self.width // 2
        pygame.draw.line(screen, (80, 100, 120), (sep_x, self.y + 40), (sep_x, self.y + self.height - 40), 2)

        if not self.available_ores:
            msg = font_small.render(Text.UI.NO_ORE, True, (200, 100, 100))
            screen.blit(msg, (self.x + 50, self.y + 100))
            return

        for i, (key, name, bonus) in enumerate(self.available_ores):
            y_pos = self.y + 70 + i * 38
            is_sel = (i == self.cursor_idx)
            color = (255, 255, 100) if is_sel else (255, 255, 255)
            if key == "cancel":
                color = (255, 255, 100) if is_sel else (200, 200, 200)
            if is_sel:
                pygame.draw.rect(screen, (60, 70, 90), (self.x + 20, y_pos - 5, sep_x - self.x - 40, 34), border_radius=5)
                screen.blit(font_small.render(">", True, color), (self.x + 35, y_pos))
            label = name if key == "cancel" else f"{name}  (+{bonus})"
            screen.blit(font_small.render(label, True, color), (self.x + 60, y_pos))

        if 0 <= self.cursor_idx < len(self.available_ores):
            ore_key, ore_name, ore_bonus = self.available_ores[self.cursor_idx]
            if ore_key != "cancel":
                data = CONSUMABLE_DATA.get(ore_key, {})
                rx = sep_x + 30
                ry = self.y + 55

                img_path = data.get("image_path")
                if img_path:
                    from systems.resources import load_image, scale_image_aspect
                    img = load_image(img_path)
                    if img:
                        scaled = scale_image_aspect(img, 72, 72)
                        screen.blit(scaled, (rx, ry))
                        ry += 72 + 12

                screen.blit(font_small_bold.render(ore_name, True, (255, 255, 200)), (rx, ry))
                ry += font_small_bold.get_height() + 8

                describe = data.get("describe", "")
                if describe:
                    draw_text_wrapped(screen, font_small, describe, rx, ry, self.width // 2 - 50, color=(180, 190, 200))


class StaveSelectionDialog(StateKeyMixin):
    """どの杖の使用回数を回復するかを選ぶダイアログ"""
    STATE_KEY = "stave_selection_active"
    def __init__(self, screen_width, screen_height):
        self.x, self.y, self.width, self.height = get_standard_upper_layout(screen_width, screen_height)
        self.font = font_medium
        self.cursor_idx = 0
        self.recharge_item_key = None
        self.available_staves = []
        self.on_confirm = None

    def setup(self, player, dialog):
        from systems.item_handler import make_recharge_callback
        self.on_confirm = make_recharge_callback(player, dialog, self)

    def update_from_player(self, player):
        self.available_staves = list(player.stave_inventory)
        self.available_staves.append("cancel")

    def handle_events(self, events):
        if not self.is_active: return
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == KEY_MOVE_UP:
                    if self.cursor_idx > 0: self.cursor_idx -= 1
                    else: self.cursor_idx = len(self.available_staves) - 1
                elif event.key == KEY_MOVE_DOWN:
                    if self.cursor_idx < len(self.available_staves) - 1: self.cursor_idx += 1
                    else: self.cursor_idx = 0
                elif event.key == KEY_CANCEL: self.is_active = False
                elif event.key == KEY_CONFIRM:
                    if 0 <= self.cursor_idx < len(self.available_staves):
                        stave_inst = self.available_staves[self.cursor_idx]
                        if stave_inst == "cancel":
                            self.is_active = False
                            return
                        self.is_active = False
                        if self.on_confirm:
                            self.on_confirm(stave_inst, self.recharge_item_key)

    def draw(self, screen):
        if not self.is_active: return
        draw_dialog_frame(screen, self.x, self.y, self.width, self.height, alpha=240)

        title = font_small.render(Text.UI.WHICH_STAVE_RECHARGE, True, (255, 200, 100))
        screen.blit(title, (self.x + (self.width - title.get_width()) // 2, self.y + 15))

        if not self.available_staves:
            msg = self.font.render(Text.UI.NO_STAVE, True, (200, 100, 100))
            screen.blit(msg, (self.x + (self.width - msg.get_width()) // 2, self.y + 100))
            return

        for i, inst in enumerate(self.available_staves):
            color = (255, 255, 255)
            if i == self.cursor_idx:
                color = (255, 255, 100)
                cursor = self.font.render(">", True, color)
                screen.blit(cursor, (self.x + self.width // 2 - 120, self.y + 70 + i * 40))

            if inst == "cancel":
                name_str = Text.UI.QUIT
            else:
                name_str = inst.get_name_with_charges()
            text = self.font.render(name_str, True, color)
            screen.blit(text, (self.x + self.width // 2 - 80, self.y + 70 + i * 40))


class ParameterSelectionDialog(BaseListDialog):
    """鍛冶屋で装備と鉱石選択後に「どのステータスを強化するか」を選ぶダイアログ"""
    STATE_KEY = "parameter_selection_active"

    def __init__(self, screen_width, screen_height):
        super().__init__(screen_width, screen_height)
        self.row_height = 38
        self.target_item_data = None
        self.selected_ore_key = None
        self.available_params = []
        self.on_confirm = None
        self.confirm_dialog = None
        self.player_ref = None
        self.cutscene_manager = None
        self._inst_ref = None

    def setup(self, enhance_dialog, confirm_dialog=None, player=None, cutscene_manager=None):
        self.on_confirm = enhance_dialog.on_select
        self.confirm_dialog = confirm_dialog
        self.player_ref = player
        self.cutscene_manager = cutscene_manager

    def get_title(self): return Text.UI.WHICH_PARAM_TO_ENHANCE

    def get_item_label(self, item, idx):
        if item == "cancel":
            return Text.UI.QUIT
        stat_key, label, before, after, is_pct, *rest = item
        return label

    def get_item_color(self, item, idx, is_selected):
        if item == "cancel":
            return (255, 255, 100) if is_selected else (200, 200, 200)
        if isinstance(item, tuple) and item[0] == "max_limit":
            return (80, 80, 100)
        return (255, 255, 100) if is_selected else (255, 255, 255)

    def get_detail_lines(self, player):
        return []

    def get_item_image_path(self, item, idx, player):
        return None

    def draw(self, screen, player=None):
        super().draw(screen, player)
        if not self.is_active or not self.available_params:
            return

        sep_x = self.x + self.width // 2
        right_rect = pygame.Rect(sep_x + 2, self.y + 45, self.width // 2 - 10, self.height - 55)
        pygame.draw.rect(screen, (18, 22, 30), right_rect)

        if self.cursor_idx >= len(self.available_params):
            return
        item = self.available_params[self.cursor_idx]
        if item == "cancel" or item[0] == "max_limit":
            return

        stat_key, label, before, after, is_pct, *rest = item
        if stat_key == "max_limit":
            return

        fh = font_small.get_height()
        bar_x = sep_x + 30
        y = self.y + 55

        if self._inst_ref:
            name_surf = font_small_bold.render(self._inst_ref.get_name(), True, (255, 255, 200))
            screen.blit(name_surf, (bar_x, y))
            y += fh + fh

        if self._inst_ref and self.target_item_data:
            from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA
            item_type, _ = self.target_item_data
            if item_type == "weapon":   data = WEAPON_DATA.get(self._inst_ref.key, {})
            elif item_type == "armor":  data = ARMOR_DATA.get(self._inst_ref.key, {})
            else:                       data = SHIELD_DATA.get(self._inst_ref.key, {})
            img_dir = data.get("image_dir")
            if item_type == "weapon":
                img_path = data.get("image_path")
            elif item_type == "armor":
                img_path = f"{img_dir}/down.png" if img_dir else None
            else:
                img_path = f"{img_dir}/shield.png" if img_dir else None
            if img_path:
                from systems.resources import load_image, scale_image_aspect
                img = load_image(img_path)
                if img:
                    scaled = scale_image_aspect(img, 80, 80)
                    screen.blit(scaled, (bar_x, y))
                    y += 80 + fh

        title = font_small_bold.render(label, True, (255, 220, 120))
        screen.blit(title, (bar_x, y))
        y += fh + 8

        from constants import SKILL_DATA
        skill_key = None
        skill_name = None
        if self.selected_ore_key == "gold_ore" and len(item) >= 7:
            skill_key = item[6]
            skill_data = SKILL_DATA.get(skill_key, {})
            skill_name = skill_data.get("name", label)
            desc = skill_data.get("describe", f"{skill_name} の説明はまだない。")
        else:
            desc = f"{label} を強化する。"

        draw_text_wrapped(screen, font_small, desc, bar_x, y, self.width // 2 - 60, color=(190, 200, 210))

        if skill_key:
            y += 42
            note = f"対象スキル: {skill_name or label}"
            draw_text_wrapped(screen, font_small, note, bar_x, y, self.width // 2 - 60, color=(160, 180, 200))

    def update_from_selection(self, player, item_type, iid, ore_key):
        self.target_item_data = (item_type, iid)
        self.selected_ore_key = ore_key
        self.selection_block_reason = None
        self._inst_ref = None

        if item_type == "weapon":   inv = player.weapon_inventory
        elif item_type == "armor":  inv = player.armor_inventory
        else:                       inv = getattr(player, "shield_inventory", [])
        inst = player._find_equip_inst(inv, iid)

        if not inst:
            self.items = [Text.UI.QUIT]
            self.available_params = ["cancel"]
            return

        self._inst_ref = inst

        from constants import CONSUMABLE_DATA
        ore_bonus = CONSUMABLE_DATA.get(ore_key, {}).get("enhance_bonus", 1)
        target_stats = []
        target_mode = "stat"
        if ore_key == "gold_ore":
            target_mode = "skill"
            target_stats = inst.get_base_upgradeable_skills()
            if not target_stats:
                self.selection_block_reason = "no_skill_target"
                self.items = ["cancel"]
                self.available_params = ["cancel"]
                self.max_limit_reached = True
                return
        else:
            target_stats = inst.get_upgradeable_stats_for_ore(ore_key)

        ALL_LABEL_MAP = {
            "attack_bonus": "攻撃力", "defense_bonus": "防御力", "hp_bonus": "最大HP",
            "dex_bonus": "器用さ",
            "crit_bonus": "会心率", "crit_rate": "会心率",
            "block_chance_close": "近距離回避",
            "block_chance_ranged": "遠距離回避", "aggro_mod": "感知補正",
            "armor_penetration": "防御無視", "stupidity": "混乱",
            "regen_bonus": "自然回復", "lantern_bonus": "光源範囲",
            "magic_fire_damage": "[炎]ダメ", "magic_fire_range": "[炎]射程",
            "magic_heal_ratio": "[癒]回復量", "magic_knockback_damage": "[風]吹飛ダメ",
            "magic_invincible_turns": "[聖]無敵ターン",
            "magic_stave_bonus": "[魔]杖回数", "magic_light_stave_bonus": "[光]燈杖回",
            "magic_barrier_turns": "障壁ターン",
            "accuracy_bonus_close": "命中率",
            "accuracy_bonus": "命中率",
            "backstab": "サイドアタック",
            "confusion": "混乱",
            "stun": "スタン",
            "counter": "カウンター",
            "knockback": "ノックバック",
            "lifesteal": "ライフスティール",
        }
        PCT_KEYS = {
            "crit_bonus", "crit_rate",
            "block_chance_close", "block_chance_ranged", "armor_penetration",
            "magic_fire_damage", "magic_heal_ratio", "magic_knockback_damage",
        }
        INT_PCT_KEYS = {"accuracy_bonus_close", "accuracy_bonus", "accuracy_bonus_ranged"}

        orig_enhance = inst.enhance
        orig_stats   = inst.stats.copy()

        from constants import get_upgrades_to_next_rank

        self.available_params = []
        for k in target_stats:
            if target_mode == "skill":
                label = ALL_LABEL_MAP.get(k, k)
                skill_name = k
                stat_key = inst.get_skill_upgrade_stat_key(k)
                if not stat_key:
                    continue
                before = inst.get_stat(stat_key, 0)
                after = before + ore_bonus
                self.available_params.append((stat_key, label, before, after, False, False, skill_name))
                continue

            remaining = get_upgrades_to_next_rank(inst, k)
            if remaining is not None and remaining > 100:
                label = ALL_LABEL_MAP.get(k, k)
                self.available_params.append(("max_limit", f"{label} (Max Limit)", 0, 0, False, False))
                continue

            inst.enhance = orig_enhance
            inst.stats   = orig_stats.copy()
            before = inst.get_stat(k, 0) + inst.get_enhance_bonus(k)

            inst.enhance = orig_enhance + ore_bonus
            inst.stats   = orig_stats.copy()
            inst.stats.setdefault(k, 0)
            inst.stats[k] += ore_bonus
            after = inst.get_stat(k, 0) + inst.get_enhance_bonus(k)

            label   = ALL_LABEL_MAP.get(k, k)
            is_pct  = k in PCT_KEYS
            is_int_pct = k in INT_PCT_KEYS
            self.available_params.append((k, label, before, after, is_pct, is_int_pct))

        inst.enhance = orig_enhance
        inst.stats   = orig_stats

        self.available_params.append("cancel")

        selectable = [p for p in self.available_params if p != "cancel" and not (isinstance(p, tuple) and p[0] == "max_limit")]
        self.max_limit_reached = len(selectable) == 0

        self.items = self.available_params

    def handle_events(self, events):
        if not self.is_active: return
        from systems.audio_manager import play_sfx
        from constants import SOUND_CURSOR_MOVE, SOUND_SELECT, SOUND_CANCEL

        action = self._navigate(events)
        if action == "cancel":
            play_sfx(SOUND_CANCEL)
            self._close_back()
        elif action == "confirm":
            item = self.available_params[self.cursor_idx] if self.available_params else None
            if item == "cancel":
                play_sfx(SOUND_CANCEL)
                self._close_back()
                return
            if item is None:
                return
            if isinstance(item, tuple) and item[0] == "max_limit":
                play_sfx(SOUND_CANCEL)
                return

            play_sfx(SOUND_SELECT)
            self.is_active = False

            stat_key = item[0]
            cd = self.confirm_dialog
            player = self.player_ref
            if cd and player and self.target_item_data and self._inst_ref:
                cd.text = "強化するぜ。間違いないな？"

                s_type, s_iid = self.target_item_data
                s_ore, s_stat = self.selected_ore_key, stat_key

                def do_enhance():
                    if getattr(self, "cutscene_manager", None):
                        self.cutscene_manager.start_blacksmith(
                            lambda: self.on_confirm(s_type, s_iid, s_ore, s_stat))
                    else:
                        self.on_confirm(s_type, s_iid, s_ore, s_stat)

                psd = self
                def do_cancel():
                    from systems.game_state import game_state as gs
                    gs["dialog_just_closed"] = False
                    psd.is_active = True
                cd.on_yes = do_enhance
                cd.on_no  = do_cancel
                cd.is_active = True


class EnhanceDialog(InventoryDialog):
    """鍛冶屋での強化メニュー（武器・鎧限定）"""
    STATE_KEY = "enhance_active"

    def __init__(self, screen_width, screen_height):
        super().__init__(screen_width, screen_height)
        self.selection_dialog = None

    def handle_events(self, events, player=None):
        if not self.is_active: return
        from constants import KEY_CONFIRM
        super().handle_events(events)

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == KEY_CONFIRM:
                if self.cursor_idx < len(self.item_data):
                    data = self.item_data[self.cursor_idx]
                    if data:
                        itype, iid_or_key = data
                        if itype == "cancel":
                            self.is_active = False
                            return
                        if getattr(self, "selection_dialog", None):
                            self.selection_dialog.target_item_data = data
                            if player:
                                self.selection_dialog.update_from_player(player)
                            self.selection_dialog.is_active = True

    def get_title(self): return Text.UI.WHICH_TO_ENHANCE

    def setup(self, player, dialog, ore_selection_dialog):
        from systems.item_handler import make_enhance_callback
        self.on_select = make_enhance_callback(player, dialog, self)
        self.selection_dialog = ore_selection_dialog

    def update_items_from_player(self, player):
        new_items, new_data = [], []
        weapons = list(player.weapon_inventory)
        armors = list(player.armor_inventory)
        shields = list(getattr(player, "shield_inventory", []))

        weapons.sort(key=lambda x: x.get_name().lower())
        armors.sort(key=lambda x: x.get_name().lower())
        shields.sort(key=lambda x: x.get_name().lower())

        for inst in weapons:
            new_items.append(inst.get_name())
            new_data.append(("weapon", inst.iid))
        for inst in armors:
            new_items.append(Text.UI.ENHANCE_ARMOR_LABEL.format(name=inst.get_name()))
            new_data.append(("armor", inst.iid))
        for inst in shields:
            new_items.append(Text.UI.ENHANCE_SHIELD_LABEL.format(name=inst.get_name()))
            new_data.append(("shield", inst.iid))

        new_items.append(Text.UI.QUIT)
        new_data.append(("cancel", None))

        self.items, self.item_data = new_items, new_data

    def draw(self, screen, player=None):
        if not self.is_active: return
        super().draw(screen, player)
