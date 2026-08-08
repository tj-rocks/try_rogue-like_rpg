import math
import pygame
from systems.game_state import game_state, is_enemy_acting
from systems.resources import font_medium
from wordings import Text
from systems.ui.ui_base import (
    get_standard_upper_layout, draw_dialog_frame, draw_text_wrapped, BaseListDialog, StateKeyMixin
)


class TeleportDialog(BaseListDialog):
    """テレポート屋（転移）での目的地選択を行うダイアログ"""
    STATE_KEY = "teleport_active"

    def __init__(self, screen_width, screen_height):
        super().__init__(screen_width, screen_height)
        self.row_height = 36
        self.target_floor = 0
        self.target_name = ""
        self.cost_money = 0
        self.required_item = ""

    def open(self, player):
        game_state["player_ref"] = player
        self.setup_destinations(player)
        if not self.items:
            return False
        self.is_active = True
        return True

    def get_title(self):
        return "テレポート屋（転移）"

    def get_header_right(self, player):
        return Text.UI.GOLD_LABEL.format(coin=player.coin)

    def on_activated(self):
        player = game_state.get("player_ref")
        if not player: return
        self.setup_destinations(player)

    def setup_destinations(self, player):
        from constants import DUNGEON_IMAGES, TELEPORT_MONEY_PER_FLOOR, TELEPORT_REQUIRED_ITEM, TELEPORT_RETURN_VILLAGE_COST
        self.items = []
        self.mode = "SELECT"
        self.required_item = TELEPORT_REQUIRED_ITEM

        if player.current_floor == 0:
            for f_str, info in DUNGEON_IMAGES.items():
                if not f_str.isdigit(): continue
                f_lv = int(f_str)
                if f_lv == 0: continue
                if f_lv <= player.max_reached_floor and info.get("map"):
                    name = f"{f_lv}F 休憩所"
                    self.items.append({"floor": f_lv, "name": name, "cost": f_lv * TELEPORT_MONEY_PER_FLOOR, "type": "warp"})
        else:
            self.items.append({"floor": 0, "name": "村（帰還）", "cost": TELEPORT_RETURN_VILLAGE_COST, "type": "return"})

        if not self.items:
            return

        self.items.append({"floor": -1, "name": Text.UI.QUIT, "cost": 0, "type": "cancel"})

    def get_item_label(self, item, idx):
        return item["name"]

    def get_detail_lines(self, player):
        if not self.items or self.cursor_idx >= len(self.items): return []
        item = self.items[self.cursor_idx]
        if item["type"] == "cancel": return ["店を出ます"]

        from systems.guild import GuildSystem
        guild = GuildSystem()
        f_lv = item["floor"]
        req_rank = guild.get_required_rank_for_floor(f_lv) if f_lv > 0 else "F"

        lines = [f"【{item['name']}】", ""]
        lines.append(f"消費コイン: {item['cost']} G")

        if f_lv > 0:
            lines.append(f"到達可能ランク: {req_rank}")
            lines.append("")
            lines.append(f"地下 {f_lv} 階にある休憩所へ転移します")
            lines.append("※強力な魔物の気配が漂っています")
        else:
            lines.append("")
            lines.append("冒険者の拠点となる村へ帰還します")
            lines.append("一度休息をとり、装備を整えましょう")
        return lines

    def handle_input(self, events, player):
        if not self.is_active: return None
        from systems.audio_manager import play_sfx
        from constants import SOUND_SELECT, SOUND_CANCEL

        old_idx = self.cursor_idx
        res = self._navigate(events)
        if self.cursor_idx != old_idx:
            self.mode = "SELECT"

        if res == "cancel":
            play_sfx(SOUND_CANCEL)
            self.is_active = False
            game_state[self.STATE_KEY] = False
            self.mode = "SELECT"
            return None
        elif res == "confirm":
            selected = self.items[self.cursor_idx]
            if selected["type"] == "cancel":
                play_sfx(SOUND_CANCEL)
                self.is_active = False
                game_state[self.STATE_KEY] = False
                return None

            self.target_floor = selected["floor"]
            self.cost_money = selected["cost"]

            dialog = game_state.get("ui_elements", {}).get("dialog")

            if player.coin < self.cost_money:
                self.mode = "NO_MONEY"
                if dialog:
                    dialog.text = Text.Items.NOT_ENOUGH_COIN
                    dialog.is_active = True
                play_sfx(SOUND_CANCEL)
                return None
            elif not self._has_required_item(player):
                self.mode = "NO_ITEM"
                if dialog:
                    dialog.text = "テレポートには『転移の石』が必要です"
                    dialog.is_active = True
                play_sfx(SOUND_CANCEL)
                return None

            if self.mode != "CONFIRM":
                play_sfx(SOUND_SELECT)
                self.mode = "CONFIRM"
                return None

            play_sfx(SOUND_SELECT)
            self._execute_teleport(player)
            self.mode = "SELECT"
        return None

    def _has_required_item(self, player):
        for item in player.items:
            if item.get("key") == self.required_item:
                return True
        return False

    def _execute_teleport(self, player):
        from systems.dungeon import warp_with_pitfall

        ui_el = game_state.get("ui_elements", {})
        if "dialog" in ui_el:
            ui_el["dialog"].is_active = False

        selected = self.items[self.cursor_idx]
        reason = selected.get("type", "teleport")

        player.coin -= self.cost_money
        player.remove_item_by_key(self.required_item, 1)

        warp_with_pitfall(self.target_floor, player, spawn_reason=reason)
        self.is_active = False
        game_state[self.STATE_KEY] = False

    def draw(self, screen, player):
        if not self.is_active: return
        super().draw(screen, player)

        sep_x = self.x + self.width // 2
        start = max(0, self.cursor_idx - self.view_size // 2)
        if start + self.view_size > len(self.items): start = max(0, len(self.items) - self.view_size)

        for i in range(start, min(start + self.view_size, len(self.items))):
            item = self.items[i]
            if item["type"] == "cancel": continue
            y_pos = self.y + 80 + (i - start) * self.row_height
            is_sel = (i == self.cursor_idx)
            color = self.get_item_color(item, i, is_sel)
            from systems.resources import font_small
            screen.blit(font_small.render(f"{item['cost']} G", True, color), (sep_x - 110, y_pos))


class OreGiftDialog(StateKeyMixin):
    """ランクアップお祝い時に好きなアイテムを1つ選んで受け取るダイアログ"""
    STATE_KEY = "ore_gift_active"
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.x, self.y, self.width, self.height = get_standard_upper_layout(screen_width, screen_height)
        self.font = font_medium
        self.cursor_idx = 0
        self.ores = []
        self.player_ref = None
        self.dialog_ref = None
        self.on_close_callback = None

    def setup(self, player, dialog, on_close=None):
        self.player_ref = player
        self.dialog_ref = dialog
        self.on_close_callback = on_close

        from constants import RANKUP_GIFTS, CONSUMABLE_DATA
        self.ores = []
        for key in RANKUP_GIFTS:
            name = CONSUMABLE_DATA.get(key, {}).get("name", key)
            self.ores.append((key, name))

    def handle_events(self, events):
        if not self.is_active: return
        from systems.audio_manager import play_sfx
        from constants import SOUND_CURSOR_MOVE, SOUND_SELECT, KEY_MOVE_UP, KEY_MOVE_DOWN, KEY_CONFIRM, KEY_CANCEL

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == KEY_MOVE_UP:
                    if self.cursor_idx > 0: self.cursor_idx -= 1
                    else: self.cursor_idx = len(self.ores) - 1
                    play_sfx(SOUND_CURSOR_MOVE)
                elif event.key == KEY_MOVE_DOWN:
                    if self.cursor_idx < len(self.ores) - 1: self.cursor_idx += 1
                    else: self.cursor_idx = 0
                    play_sfx(SOUND_CURSOR_MOVE)
                elif event.key == KEY_CONFIRM:
                    play_sfx(SOUND_SELECT)
                    selected_key, selected_name = self.ores[self.cursor_idx]

                    if self.player_ref:
                        self.player_ref.add_item_to_inventory(selected_key)

                    if self.dialog_ref:
                        self.dialog_ref.text = f"お祝いとして\n{selected_name} を手に入れた！"
                        game_state["dialog_modal"] = True
                        self.dialog_ref.is_active = True

                    self.is_active = False
                    if self.on_close_callback:
                        self.on_close_callback()

    def draw(self, screen):
        if not self.is_active: return
        draw_dialog_frame(screen, self.x, self.y, self.width, self.height, alpha=240)

        title = self.font.render("お祝いアイテムを選んでね！", True, (255, 200, 100))
        screen.blit(title, (self.x + (self.width - title.get_width()) // 2, self.y + 15))

        for i, (key, name) in enumerate(self.ores):
            color = (255, 255, 255)
            if i == self.cursor_idx:
                color = (255, 255, 100)
                cursor = self.font.render(">", True, color)
                screen.blit(cursor, (self.x + self.width // 2 - 130, self.y + 70 + i * 35))

            text = self.font.render(name, True, color)
            screen.blit(text, (self.x + self.width // 2 - 100, self.y + 70 + i * 35))


# --- 視界制限（カンテラ）システム ---
_vision_masks = {}


def _create_radial_mask(radius, fade_radius, center_alpha=0):
    """円形の視界マスクを生成する（中心が透明、外側が黒）"""
    size = (radius + fade_radius) * 2
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2

    for y in range(size):
        for x in range(size):
            dx = x - center
            dy = y - center
            dist = math.sqrt(dx*dx + dy*dy)

            if dist <= radius:
                alpha = center_alpha
            elif dist >= radius + fade_radius:
                alpha = 255
            else:
                alpha = int(center_alpha + (255 - center_alpha) * (dist - radius) / fade_radius)
                seed = (x * 73856093) ^ (y * 19349663) ^ (radius * 83492791) ^ (fade_radius * 2654435761)
                alpha = max(0, min(255, alpha + (((seed >> 3) & 31) - 15)))

            surface.set_at((x, y), (255, 255, 255, alpha))
    return surface


def draw_vision_overlay(screen, player, dungeon):
    """プレイヤーの周囲以外を暗闇で覆う。"""
    if getattr(dungeon, "is_lighted", False):
        return

    if getattr(player, "condition", "normal") == "darkness":
        r_tiles = 1
        f_tiles = 1
    else:
        r_tiles = 1 + getattr(player, "lantern_bonus", 0)
        f_tiles = 2

    tile_size = getattr(dungeon, "tile_size", 32)

    brightness = getattr(dungeon, "brightness", 1)
    brightness_multipliers = {1: 1.0, 2: 1.5, 3: 2.5, 4: 4.5}
    mult = brightness_multipliers.get(brightness, 1.0)

    darkness_type = getattr(dungeon, "darkness_type", "dark")

    radius_px = int(r_tiles * tile_size * mult)
    fade_px = int(f_tiles * tile_size * mult)

    fog_center_alpha = 2 if darkness_type == "fog" else 0
    mask_key = (radius_px, fade_px, fog_center_alpha)
    if mask_key not in _vision_masks:
        _vision_masks[mask_key] = _create_radial_mask(radius_px, fade_px, fog_center_alpha)

    mask = _vision_masks[mask_key]

    sw, sh = screen.get_size()
    px = sw // 2
    py = sh // 2

    fog_colors = {
        "dark": (0, 0, 0, 255),
        "fog": (246, 246, 255, 210),
    }
    fog = pygame.Surface((sw, sh), pygame.SRCALPHA)
    fog.fill(fog_colors.get(darkness_type, fog_colors["dark"]))

    mask_rect = mask.get_rect(center=(px, py))
    fog.blit(mask, mask_rect, special_flags=pygame.BLEND_RGBA_MULT)

    screen.blit(fog, (0, 0))


def draw_minimap(screen, dungeon, player):
    """探索済みのタイルを表示するミニマップ（透過オーバーレイ）を描画する。"""
    from systems.game_state import is_paused
    if not dungeon or not getattr(dungeon, "show_map", True) or is_paused(): return
    if dungeon.current_floor == 0: return

    tile_dot = 5
    map_w = dungeon.map_width * tile_dot
    map_h = dungeon.map_height * tile_dot

    from constants import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE
    off_x = SCREEN_WIDTH - map_w - (TILE_SIZE * 3)
    off_y = 120

    map_surf = pygame.Surface((map_w, map_h), pygame.SRCALPHA)

    for y in range(dungeon.map_height):
        for x in range(dungeon.map_width):
            if not dungeon.revealed_tiles[y][x]: continue

            tile = dungeon.map_data[y][x]
            rect = (x * tile_dot, y * tile_dot, tile_dot, tile_dot)

            if tile == 1:
                pygame.draw.rect(map_surf, (60, 80, 140, 220), rect)
            elif 4 <= tile <= 6:
                pygame.draw.rect(map_surf, (80, 80, 90, 220), rect)
            elif tile in (2, 3):
                pygame.draw.rect(map_surf, (255, 255, 0, 255), rect)

    for e in dungeon.enemies:
        if e.is_dead or getattr(e, "is_static", False): continue
        gx, gy = int(e.x // dungeon.tile_size), int(e.y // dungeon.tile_size)
        if 0 <= gx < dungeon.map_width and 0 <= gy < dungeon.map_height:
            if dungeon.revealed_tiles[gy][gx]:
                pygame.draw.rect(map_surf, (255, 50, 50, 255), (gx * tile_dot, gy * tile_dot, tile_dot, tile_dot))

    px, py = int(player.x // dungeon.tile_size), int(player.y // dungeon.tile_size)
    if 0 <= px < dungeon.map_width and 0 <= py < dungeon.map_height:
        pygame.draw.rect(map_surf, (255, 255, 255, 255), (px * tile_dot, py * tile_dot, tile_dot, tile_dot))

    screen.blit(map_surf, (off_x, off_y))


def handle_ui_events(events, dialog, confirm_dialog, inventory_dialog, status_dialog,
                     enhance_dialog, item_action_dialog, ore_selection_dialog,
                     menu_dialog=None, player=None, dungeon=None, shop_dialog=None,
                     stave_selection_dialog=None, guild_dialog=None, warehouse_dialog=None,
                     bank_dialog=None, equip_dialog=None, stave_inv_dialog=None,
                     event_inv_dialog=None, teleport_dialog=None, cutscene_manager=None,
                     parameter_selection_dialog=None, ore_gift_dialog=None, **kwargs):
    """全てのUIイベントを一括で処理する"""

    if cutscene_manager and cutscene_manager.is_active:
        events.clear()
        return

    if ore_gift_dialog and ore_gift_dialog.is_active:
        from constants import KEY_CONFIRM
        ore_gift_dialog.handle_events(events)
        if dialog.is_active and dialog.just_opened_timer <= 0:
            for event in events:
                if event.type == pygame.KEYDOWN and event.key in (KEY_CONFIRM, pygame.K_RETURN, pygame.K_z):
                    dialog.is_active = False
        return

    if dungeon:
        inventory_dialog.dungeon = dungeon
        if equip_dialog: equip_dialog.dungeon = dungeon
        if stave_inv_dialog: stave_inv_dialog.dungeon = dungeon
        if stave_selection_dialog:
            stave_selection_dialog.dungeon = dungeon

    from constants import KEY_CONFIRM, KEY_CANCEL, KEY_INVENTORY, KEY_STATUS, KEY_MENU, KEY_MAP

    for event in events:
        if event.type == pygame.KEYDOWN and event.key == KEY_MAP:
            if dungeon:
                dungeon.show_map = not getattr(dungeon, "show_map", True)
                print(f"[UI] Map Display Toggled: {dungeon.show_map}")

    if confirm_dialog.is_active:
        confirm_dialog.handle_events(events)
        return

    if (not dialog.is_active) and (not confirm_dialog.is_active) and game_state.get("pending_ending_after_dialog"):
        ending_route = game_state["pending_ending_after_dialog"]
        if ending_route == "core":
            from systems.scene_handler import save_core_clear_before_ending
            save_core_clear_before_ending(player, game_state)
        game_state["post_boss_clear_pending"] = False
        game_state["current_scene"] = "ending"
        game_state["ending_route"] = ending_route
        game_state["pending_ending_after_dialog"] = None
        game_state["ending_index"] = 0
        game_state["ending_timer"] = 0
        game_state["ending_alpha"] = 0
        return

    if teleport_dialog and teleport_dialog.is_active:
        new_dungeon = teleport_dialog.handle_input(events, player)
        if dialog.is_active and dialog.just_opened_timer <= 0:
            for event in events:
                if event.type == pygame.KEYDOWN and event.key in (KEY_CONFIRM, pygame.K_RETURN, pygame.K_z):
                    dialog.is_active = False
        if new_dungeon:
            from systems.magic_handler import FlashEffect
            new_dungeon.magic_effects.append(FlashEffect(color=(100, 150, 255), duration=40))
            return new_dungeon
        return

    guild_guide_dialog = kwargs.get("guild_guide_dialog")
    if guild_guide_dialog and guild_guide_dialog.is_active:
        guild_guide_dialog.handle_input(events, player)
        if dialog.is_active and dialog.just_opened_timer <= 0:
            for event in events:
                if event.type == pygame.KEYDOWN and event.key in (KEY_CONFIRM, pygame.K_RETURN, pygame.K_z):
                    dialog.is_active = False
        return

    if menu_dialog and menu_dialog.is_active:
        sub_active = (
            (equip_dialog and equip_dialog.is_active) or
            (stave_inv_dialog and stave_inv_dialog.is_active) or
            (event_inv_dialog and event_inv_dialog.is_active) or
            inventory_dialog.is_active or
            status_dialog.is_active
        )
        if not sub_active:
            menu_dialog.handle_events(events, dungeon=dungeon)
            return

    if item_action_dialog.is_active:
        item_action_dialog.handle_events(events)
        return

    if ore_selection_dialog.is_active:
        ore_selection_dialog.handle_events(events)
        return

    if parameter_selection_dialog and parameter_selection_dialog.is_active:
        parameter_selection_dialog.handle_events(events)
        return

    if equip_dialog and equip_dialog.is_active:
        equip_dialog.handle_events(events)
        return

    if stave_inv_dialog and stave_inv_dialog.is_active:
        stave_inv_dialog.handle_events(events)
        return

    if event_inv_dialog and event_inv_dialog.is_active:
        event_inv_dialog.handle_events(events)
        return

    if stave_selection_dialog and stave_selection_dialog.is_active:
        stave_selection_dialog.handle_events(events)
        return

    if inventory_dialog.is_active:
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == KEY_INVENTORY:
                inventory_dialog._close_back(); return
        inventory_dialog.handle_events(events)
        return
    elif status_dialog.is_active:
        status_dialog.handle_events(events, player)
        return
    elif enhance_dialog.is_active:
        enhance_dialog.handle_events(events, player)
        if dialog.is_active and dialog.just_opened_timer <= 0:
            for event in events:
                if event.type == pygame.KEYDOWN and event.key in (KEY_CONFIRM, pygame.K_RETURN, pygame.K_z):
                    dialog.is_active = False
        return

    if bank_dialog and bank_dialog.is_active:
        bank_dialog.handle_events(events, player, dialog)
        if dialog.is_active and dialog.just_opened_timer <= 0:
            for event in events:
                if event.type == pygame.KEYDOWN and event.key in (KEY_CONFIRM, pygame.K_RETURN, pygame.K_z):
                    dialog.is_active = False
        return

    if shop_dialog and shop_dialog.is_active:
        gs = getattr(dungeon, "guild_system", None)
        shop_dialog.handle_events(events, player, dialog, confirm_dialog, gs)
        if dialog.is_active and dialog.just_opened_timer <= 0:
            for event in events:
                if event.type == pygame.KEYDOWN and event.key in (KEY_CONFIRM, pygame.K_RETURN, pygame.K_z):
                    dialog.is_active = False
        return

    if guild_dialog and guild_dialog.is_active:
        guild_dialog.handle_events(events, player, dialog, confirm_dialog)
        if dialog.is_active and dialog.just_opened_timer <= 0:
            for event in events:
                if event.type == pygame.KEYDOWN and event.key in (KEY_CONFIRM, pygame.K_RETURN, pygame.K_z):
                    dialog.is_active = False
        return

    if warehouse_dialog and warehouse_dialog.is_active:
        warehouse_dialog.handle_events(events, player, confirm_dialog, dialog)
        if dialog.is_active:
            for event in events:
                if event.type == pygame.KEYDOWN and event.key in (KEY_CONFIRM, pygame.K_RETURN, pygame.K_z):
                    dialog.is_active = False
        return
    elif dialog.is_active and dialog.just_opened_timer <= 0:
        dialog.handle_events(events)
    else:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F3 and dungeon is not None and player is not None:
                    dungeon.export_debug_map(player)
                if event.key == KEY_CONFIRM:
                    if player and dungeon:
                        gx = int((player.x + player.width / 2) // dungeon.tile_size)
                        gy = int((player.y + player.height / 2) // dungeon.tile_size)
                        for npc in dungeon.npcs:
                            ngx = int((npc.x + npc.width / 2) // dungeon.tile_size)
                            ngy = int((npc.y + npc.height / 2) // dungeon.tile_size)
                            dx, dy = ngx - gx, ngy - gy
                            if abs(dx) <= 1 and abs(dy) <= 1:
                                is_valid = (dx == 0 and dy == 0) or \
                                           (player.facing == "up" and dy < 0) or \
                                           (player.facing == "down" and dy > 0) or \
                                           (player.facing == "left" and dx < 0) or \
                                           (player.facing == "right" and dx > 0)
                                if is_valid:
                                    post_core_clear_pending = bool(
                                        dungeon and dungeon.current_floor == 0 and game_state.get("post_boss_clear_pending", False)
                                    )
                                    ending_route = game_state.get("ending_route", "default")
                                    if getattr(npc, "role", None) == "core_ending_guide":
                                        game_state["pending_ending_after_dialog"] = "core"
                                        dialog.on_close_callback = None
                                    elif post_core_clear_pending and ending_route != "core":
                                        def _trigger_post_boss_ending():
                                            from systems.game_state import game_state as gs
                                            gs["post_boss_clear_pending"] = False
                                            gs["current_scene"] = "ending"
                                            gs["ending_index"] = 0
                                            gs["ending_timer"] = 0
                                            gs["ending_alpha"] = 0
                                        dialog.on_close_callback = _trigger_post_boss_ending
                                    else:
                                        dialog.on_close_callback = None
                                    if getattr(npc, "role", None) == "inn":
                                        from constants import INN_FEE
                                        dialog.text = Text.NPC.INN_WELCOME
                                        confirm_dialog.text = Text.UI.INN_CONFIRM.format(fee=INN_FEE)
                                        def on_inn_yes():
                                            def on_inn_done():
                                                has_debt = (player.coin < INN_FEE)
                                                player.coin -= INN_FEE
                                                player.hp = player.max_hp
                                                from systems.data_loader import SAVE_OFFICIAL_PATH
                                                player.save_to_file()
                                                if has_debt:
                                                    dialog.text = Text.NPC.INN_DEBT
                                                else:
                                                    dialog.text = Text.NPC.INN_RECOVERED
                                                dialog.is_active = True
                                                print(f"[INN] Rest Complete. Debt: {has_debt}, New Coin: {player.coin}")
                                            if cutscene_manager:
                                                cutscene_manager.start_inn_rest(callback=on_inn_done)
                                            else:
                                                on_inn_done()
                                        def on_inn_no():
                                            dialog.text = Text.NPC.INN_NO
                                            dialog.is_active = True
                                        confirm_dialog.on_yes = on_inn_yes
                                        confirm_dialog.on_no = on_inn_no
                                        confirm_dialog.is_active = True
                                        dialog.is_active = True
                                        return
                                    elif getattr(npc, "role", None) == "blacksmith":
                                        from constants import CONSUMABLE_DATA
                                        has_ore = any(CONSUMABLE_DATA.get(k["key"], {}).get("effect") == "material" for k in player.items)
                                        if has_ore:
                                            dialog.text = Text.NPC.BLACKSMITH_WELCOME
                                            dialog.is_active = True
                                            enhance_dialog.is_active = True
                                            return
                                        else:
                                            dialog.text = Text.NPC.BLACKSMITH_NO_ORE
                                            dialog.is_active = True
                                            return
                                    elif getattr(npc, "role", None) == "weapon_shop":
                                        if shop_dialog and dungeon:
                                            dialog.text = Text.NPC.WEAPON_SHOP_WELCOME
                                            dialog.is_active = True
                                            shop_dialog.open_shop("武器屋", dungeon.weapon_shop_stock)
                                            return
                                    elif getattr(npc, "role", None) == "dedicated_weapon_shop":
                                        if shop_dialog and dungeon:
                                            dialog.text = Text.NPC.DEDICATED_WEAPON_SHOP_WELCOME
                                            dialog.is_active = True
                                            shop_dialog.open_shop("武器専門店", dungeon.dedicated_weapon_shop_stock)
                                            return
                                    elif getattr(npc, "role", None) == "dedicated_armor_shop":
                                        if shop_dialog and dungeon:
                                            dialog.text = Text.NPC.DEDICATED_ARMOR_SHOP_WELCOME
                                            dialog.is_active = True
                                            shop_dialog.open_shop("防具専門店", dungeon.dedicated_armor_shop_stock)
                                            return
                                    elif getattr(npc, "role", None) == "dedicated_accessory_shop":
                                        if shop_dialog and dungeon:
                                            dialog.text = Text.NPC.DEDICATED_ACCESSORY_SHOP_WELCOME
                                            dialog.is_active = True
                                            shop_dialog.open_shop("アクセサリ専門店", dungeon.dedicated_accessory_shop_stock)
                                            return
                                    elif getattr(npc, "role", None) == "item_shop":
                                        if shop_dialog and dungeon:
                                            dialog.text = Text.NPC.ITEM_SHOP_WELCOME
                                            dialog.is_active = True
                                            shop_dialog.open_shop("道具屋", dungeon.item_shop_stock)
                                            return
                                    elif getattr(npc, "role", None) == "magic_shop":
                                        if shop_dialog and dungeon:
                                            dialog.text = "フォッフォッフォ、杖のことならわしに任せるがよいぞ"
                                            dialog.is_active = True
                                            shop_dialog.open_shop("魔法屋", dungeon.magic_shop_stock)
                                            return
                                    elif getattr(npc, "role", None) == "merchant":
                                        if shop_dialog:
                                            dialog.text = Text.NPC.MERCHANT_WELCOME
                                            dialog.is_active = True
                                            shop_dialog.shop_name = "商人"
                                            shop_dialog.setup_sell_mode(player)
                                            shop_dialog.is_active = True
                                            return
                                    elif getattr(npc, "role", None) == "guild_receptionist":
                                        if guild_dialog and dungeon:
                                            if not dungeon.guild_system.available_quests:
                                                dungeon.guild_system.generate_quests(player)
                                            guild_dialog.setup(player, dungeon, npc_role="guild_receptionist")
                                            rank_title, rank_info = dungeon.guild_system.get_next_rank_info(player)
                                            short_info = rank_info.replace("\n", " ").replace("  ", " ")
                                            full_text = f"ようこそ冒険者ギルドへ！\nご用件をどうぞ。\n{short_info}"
                                            dialog.text = full_text
                                            dialog.is_active = True
                                            guild_dialog.is_active = True
                                            if guild_dialog.mode == "AUTO_REPORT" and game_state.get("current_scene") != "ending":
                                                dialog.text = "おお、見事に依頼を達成しましたね！\nおめでとうございます！"
                                                dialog.is_active = True
                                            return
                                    elif getattr(npc, "role", None) == "guild_rankup":
                                        if guild_dialog and dungeon:
                                            if not dungeon.guild_system.available_quests:
                                                dungeon.guild_system.generate_quests(player)
                                            guild_dialog.setup(player, dungeon, npc_role="guild_rankup")
                                            dialog.is_active = True
                                            guild_dialog.is_active = True
                                            next_rank_data = dungeon.guild_system.get_next_rank_data(player.guild_rank)
                                            already_active = any(q.get("is_rank_up") for q in player.active_quests)
                                            is_ready_to_report = guild_dialog._pending_report is not None
                                            if player.guild_rank == "-":
                                                has_q = any(q.get("id") == "rank_up_F" for q in player.active_quests)
                                                if is_ready_to_report:
                                                    dialog.text = "昇給試験担当です。\nおお！無事に証を持ち帰りましたね。さあ、報告を完了させましょう！"
                                                elif not has_q:
                                                    dialog.text = "昇給試験担当です。\nまずはギルドへ正式に加入するための試験を受けてくださいね。"
                                                else:
                                                    dialog.text = "昇給試験担当です。\nFランク加入の試験クエストは順調ですか？"
                                            elif is_ready_to_report:
                                                dialog.text = "昇給試験担当です。\nおお！無事に証を持ち帰りましたね。さあ、報告を完了させましょう！"
                                            elif already_active:
                                                dialog.text = "昇給試験担当です。\n試験クエストは順調ですか？対象フロアの最奥で証を見つけてきてくださいね！"
                                            elif next_rank_data and player.guild_point >= next_rank_data["required_gp"]:
                                                dialog.text = "昇給試験担当です。\n現在のポイントは十分です！次のランクの試験を受けられますよ。"
                                            elif next_rank_data:
                                                needed = next_rank_data["required_gp"] - player.guild_point
                                                dialog.text = f"昇給試験担当です。\n次の{next_rank_data['rank']}ランクの試験を受けるには、あと {needed} GP 必要です。"
                                            else:
                                                dialog.text = "昇給試験担当です。\nあなたは既に最高ランクに到達しています！"
                                            return
                                    elif getattr(npc, "role", None) == "storage":
                                        if warehouse_dialog:
                                            dialog.text = Text.NPC.WAREHOUSE_WELCOME
                                            dialog.is_active = True
                                            warehouse_dialog.is_active = True
                                            return
                                    elif getattr(npc, "role", None) == "bank":
                                        if bank_dialog:
                                            dialog.text = Text.NPC.BANK_WELCOME
                                            dialog.is_active = True
                                            bank_dialog.is_active = True
                                            return
                                    elif getattr(npc, "role", None) == "doctor":
                                        dialog.text = "\n".join(npc.get_dialogue(player)); dialog.is_active = True
                                        from constants import DOCTOR_FEE, POISON_CURE_FEE

                                        def make_heal_callback(fee, cure_poison=False):
                                            def heal():
                                                current_fee = fee
                                                if player.coin >= current_fee:
                                                    player.coin -= current_fee
                                                else:
                                                    current_fee -= player.coin
                                                    player.coin = 0
                                                    if player.bank_coin >= current_fee:
                                                        player.bank_coin -= current_fee
                                                    else:
                                                        current_fee -= player.bank_coin
                                                        player.bank_coin = 0
                                                        player.coin = -current_fee
                                                player.hp = player.max_hp
                                                if cure_poison:
                                                    player.condition = "normal"
                                                dialog.text = Text.NPC.DOCTOR_OK
                                                dialog.is_active = True
                                            return heal

                                        if player.condition == "poison":
                                            if confirm_dialog:
                                                confirm_dialog.text = Text.UI.DOCTOR_POISON_CONFIRM.format(fee=POISON_CURE_FEE)
                                                confirm_dialog.on_yes = make_heal_callback(POISON_CURE_FEE, cure_poison=True)
                                                confirm_dialog.is_active = True
                                                return
                                        elif player.hp < player.max_hp:
                                            if confirm_dialog:
                                                confirm_dialog.text = Text.UI.DOCTOR_HEAL_CONFIRM.format(fee=DOCTOR_FEE)
                                                confirm_dialog.on_yes = make_heal_callback(DOCTOR_FEE)
                                                confirm_dialog.is_active = True
                                                return
                                        else:
                                            dialog.text = Text.UI.DOCTOR_HEALTHY
                                            dialog.is_active = True
                                            return
                                    elif getattr(npc, "role", None) == "teleport":
                                        if teleport_dialog:
                                            teleport_dialog.setup_destinations(player)
                                            if not teleport_dialog.items:
                                                dialog.text = "「まだ転移できる場所がないようじゃな \n もう少し深く潜ってみなされ」"
                                                dialog.is_active = True
                                                return
                                            dialog.text = "\n".join(npc.get_dialogue(player))
                                            dialog.is_active = True
                                            teleport_dialog.is_active = True
                                    elif getattr(npc, "role", None) == "guild_guide":
                                        guild_guide_dialog = kwargs.get("guild_guide_dialog")
                                        if guild_guide_dialog:
                                            guild_guide_dialog.setup_options(player)
                                            dialog.text = "\n".join(npc.get_dialogue(player))
                                            dialog.is_active = True
                                            guild_guide_dialog.is_active = True
                                            return
                                    elif getattr(npc, "role", None) == "priest":
                                        cost = max(1, player.guild_point // 10)
                                        if getattr(player, "curse_level", 0) > 0:
                                            dialog.text = Text.NPC.PRIEST_WELCOME
                                            dialog.is_active = True
                                            if confirm_dialog:
                                                confirm_dialog.text = Text.NPC.PRIEST_CURE_CONFIRM.format(cost=cost)
                                                def on_priest_yes():
                                                    from systems.audio_manager import play_sfx
                                                    from constants import SOUND_CANCEL, SOUND_SELECT
                                                    if player.guild_point < cost:
                                                        dialog.text = Text.NPC.PRIEST_NO_GP.format(cost=cost)
                                                        dialog.is_active = True
                                                        play_sfx(SOUND_CANCEL)
                                                    else:
                                                        player.guild_point -= cost
                                                        player.curse_level -= 1
                                                        player.cursed_stats = ["hp"] if player.curse_level > 0 else []
                                                        dialog.text = Text.NPC.PRIEST_CURE_DONE.format(stat="最大HP")
                                                        dialog.is_active = True
                                                        from systems.sound_handler import sound_manager
                                                        sound_manager.play_sfx(SOUND_SELECT)
                                                        player.save_to_file()
                                                def on_priest_no():
                                                    dialog.text = Text.NPC.PRIEST_DECLINE
                                                    dialog.is_active = True
                                                confirm_dialog.on_yes = on_priest_yes
                                                confirm_dialog.on_no = on_priest_no
                                                confirm_dialog.is_active = True
                                        else:
                                            dialog.text = Text.NPC.PRIEST_HEALTHY
                                            dialog.is_active = True
                                        return
                                    else:
                                        dialog.set_pages(npc.get_dialogue(player))
                                    return
                elif event.key == KEY_MENU:
                    if menu_dialog and not is_enemy_acting(dungeon):
                        menu_dialog.is_active = True
                    elif os.environ.get("DEBUG_MODE") == "1":
                        print(
                            f"[INPUT-BLOCK] menu open failed "
                            f"menu_dialog={bool(menu_dialog)} enemy_acting={is_enemy_acting(dungeon)} "
                            f"dialog_active={dialog.is_active if dialog else None} "
                            f"confirm_active={confirm_dialog.is_active if confirm_dialog else None}"
                        )


def draw_all_ui(screen, player, dialog, confirm_dialog, inventory_dialog, status_dialog,
                enhance_dialog, item_action_dialog, ore_selection_dialog, shop_dialog,
                stave_selection_dialog, guild_dialog=None, warehouse_dialog=None,
                bank_dialog=None, menu_dialog=None, equip_dialog=None, stave_inv_dialog=None,
                event_inv_dialog=None, teleport_dialog=None, dungeon=None, events=None,
                parameter_selection_dialog=None, ore_gift_dialog=None, **kwargs):
    """全てのUIダイアログなどをまとめて更新・描画する"""
    inventory_dialog.draw(screen, player)
    if equip_dialog: equip_dialog.draw(screen, player)
    status_dialog.draw(screen, player)
    enhance_dialog.draw(screen, player)
    shop_dialog.draw(screen, player, getattr(dungeon, "guild_system", None))

    if guild_dialog:
        guild_dialog.draw(screen, player)
    if warehouse_dialog:
        warehouse_dialog.draw(screen, player)
    if bank_dialog: bank_dialog.draw(screen, player)
    if menu_dialog: menu_dialog.draw(screen, dungeon=dungeon)
    if stave_inv_dialog:
        stave_inv_dialog.update_items_from_player(player)
        stave_inv_dialog.draw(screen, player)
    if event_inv_dialog:
        event_inv_dialog.update_items_from_player(player)
        event_inv_dialog.draw(screen, player)

    item_action_dialog.draw(screen)
    ore_selection_dialog.draw(screen)
    if parameter_selection_dialog:
        parameter_selection_dialog.draw(screen, player)
    stave_selection_dialog.draw(screen)
    if teleport_dialog:
        teleport_dialog.draw(screen, player)
    if ore_gift_dialog:
        ore_gift_dialog.draw(screen)

    guild_guide_dialog = kwargs.get("guild_guide_dialog")
    if guild_guide_dialog:
        guild_guide_dialog.draw(screen, player)

    dialog.update()
    dialog.draw(screen)
    confirm_dialog.draw(screen)

    cutscene_manager = kwargs.get("cutscene_manager")
    if cutscene_manager and cutscene_manager.is_active:
        cutscene_manager.update()
        cutscene_manager.draw(screen)

    if dungeon:
        draw_minimap(screen, dungeon, player)
