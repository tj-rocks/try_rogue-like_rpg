import pygame
from systems.game_state import game_state
from systems.resources import font_small, font_small_bold
from wordings import Text
from systems.ui.ui_base import (
    get_standard_upper_layout, draw_dialog_frame, draw_text_wrapped,
    BaseListDialog, EQUIP_STAT_LABEL_MAP, EQUIP_MAGIC_LABEL_MAP, format_stat_value
)


class ShopDialog(BaseListDialog):
    """NPC商店での売買を行うダイアログ"""
    STATE_KEY = "shop_active"

    def __init__(self, screen_width, screen_height):
        super().__init__(screen_width, screen_height)
        self.row_height = 36
        self.mode = "BUY"
        self.shop_name = ""
        self.stock_ref = []

    def open_shop(self, shop_name, stock):
        self.shop_name = shop_name; self.stock_ref = stock; self.mode = "BUY"
        self.refresh_items_from_stock(); self.is_active = True

    def refresh_items_from_stock(self):
        self.items = []
        for s in self.stock_ref: self.items.append((s["key"], s["type"], s["name"], s["price"], s["count"]))
        self.items.sort(key=lambda x: x[2].lower())
        self.items.append(("cancel", "cancel", Text.UI.SHOP_CANCEL, 0, 1))

    def setup_sell_mode(self, player):
        self.mode = "SELL"; self.cursor_idx = 0; self.items = []
        from constants import CONSUMABLE_DATA, WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, STAVE_DATA

        def get_sell_price(data):
            if "selling_price" in data:
                return int(data["selling_price"])
            return int(data.get("price", 0) // 3)

        for item in player.items:
            info = CONSUMABLE_DATA.get(item["key"], {})
            self.items.append((item["key"], "consumable", info.get("name", item["key"]), get_sell_price(info), item["count"]))
        for eq in player.weapon_inventory:
            data = WEAPON_DATA.get(eq.key, {})
            self.items.append((eq.iid, "weapon_inst", eq.get_name(), get_sell_price(data), 1, eq.key))
        for eq in player.armor_inventory:
            data = ARMOR_DATA.get(eq.key, {})
            self.items.append((eq.iid, "armor_inst", eq.get_name(), get_sell_price(data), 1, eq.key))
        for eq in player.shield_inventory:
            data = SHIELD_DATA.get(eq.key, {})
            self.items.append((eq.iid, "shield_inst", eq.get_name(), get_sell_price(data), 1, eq.key))
        for st in player.stave_inventory:
            data = STAVE_DATA.get(st.key, {})
            self.items.append((st.iid, "stave_inst", st.get_name_with_charges(), get_sell_price(data), 1, st.key))
        from constants import ACCESSORY_DATA
        for eq in getattr(player, "accessory_inventory", []):
            data = ACCESSORY_DATA.get(eq.key, {})
            self.items.append((eq.iid, "accessory_inst", eq.get_name(), get_sell_price(data), 1, eq.key))
        self.items.sort(key=lambda x: x[2].lower())
        self.items.append(("cancel", "cancel", Text.UI.SHOP_CANCEL, 0, 1))

    def handle_events(self, events, player, dialog, confirm_dialog=None, guild_system=None):
        if not self.is_active: return
        from systems.audio_manager import play_sfx
        from constants import SOUND_CURSOR_MOVE, SOUND_SELECT, SOUND_CANCEL, KEY_MOVE_UP, KEY_MOVE_DOWN, KEY_CANCEL, KEY_CONFIRM
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == KEY_CANCEL: play_sfx(SOUND_CANCEL); self.is_active = False; return
                if event.key == KEY_MOVE_UP:
                    play_sfx(SOUND_CURSOR_MOVE)
                    if self.cursor_idx > 0:
                        self.cursor_idx -= 1
                    else:
                        self.cursor_idx = len(self.items) - 1
                elif event.key == KEY_MOVE_DOWN:
                    play_sfx(SOUND_CURSOR_MOVE)
                    if self.cursor_idx < len(self.items) - 1:
                        self.cursor_idx += 1
                    else:
                        self.cursor_idx = 0
                elif event.key == KEY_CONFIRM:
                    if not self.items: return
                    if self.items[self.cursor_idx][1] == "cancel": play_sfx(SOUND_CANCEL); self.is_active = False; return
                    play_sfx(SOUND_SELECT); self.execute_transaction(player, dialog, confirm_dialog, guild_system)

    def execute_transaction(self, player, dialog, confirm_dialog, guild_system):
        selected = self.items[self.cursor_idx]
        key_or_iid, itype, name, price, count = selected[:5]
        from systems.audio_manager import play_sfx
        from constants import SOUND_PURCHASE, WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, CONSUMABLE_DATA, STAVE_DATA
        if self.mode == "BUY":
            catalog = {"weapon": WEAPON_DATA, "armor": ARMOR_DATA, "shield": SHIELD_DATA, "stave": STAVE_DATA, "consumable": CONSUMABLE_DATA}
            item_data = catalog.get(itype, {}).get(key_or_iid, {})
            if guild_system and not guild_system.is_rank_at_least(player.guild_rank, item_data.get("rank", "F")):
                dialog.text = Text.Items.RANK_REQUIRED.format(rank=item_data.get("rank", "F")); dialog.is_active = True; return
            if player.coin < price: dialog.text = Text.Items.NOT_ENOUGH_COIN; dialog.is_active = True; return

            from constants import MAX_ITEM_SLOTS, MAX_EQUIP_SLOTS, MAX_STAVE_SLOTS
            bag_full = False
            if itype in ("weapon", "armor", "shield"):
                if player.get_equipment_count() >= MAX_EQUIP_SLOTS: bag_full = True
            elif itype == "stave":
                if player.get_stave_count() >= MAX_STAVE_SLOTS: bag_full = True
            elif itype == "consumable":
                ms = item_data.get("max_stack", 1)
                can_stack = any(it["key"] == key_or_iid and it["count"] < ms for it in player.items) if ms > 1 else False
                if not can_stack and player.get_item_count() >= MAX_ITEM_SLOTS: bag_full = True

            if bag_full: dialog.text = Text.Items.BAG_FULL_SHOP; dialog.is_active = True; return
            if confirm_dialog:
                confirm_dialog.text = Text.UI.SHOP_BUY_CONFIRM.format(name=name, price=price)
                def do_buy():
                    player.coin -= price
                    if itype == "weapon": player.equip_weapon_by_key(key_or_iid)
                    elif itype == "armor": player.equip_armor_by_key(key_or_iid)
                    elif itype == "shield": player.equip_shield_by_key(key_or_iid)
                    elif itype == "accessory": player.equip_accessory_by_key(key_or_iid)
                    elif itype == "stave":
                        from components.sprites.player import StaveInstance
                        player.stave_inventory.append(StaveInstance(key_or_iid))
                    elif itype == "consumable": player.add_item_to_inventory(key_or_iid)
                    self.stock_ref[self.cursor_idx]["count"] -= 1
                    if self.stock_ref[self.cursor_idx]["count"] <= 0: self.stock_ref.pop(self.cursor_idx)
                    play_sfx(SOUND_PURCHASE); self.refresh_items_from_stock(); self.cursor_idx = min(self.cursor_idx, len(self.items)-1); dialog.text = Text.Items.BOUGHT.format(name=name); dialog.is_active = True
                confirm_dialog.on_yes = do_buy
                confirm_dialog.on_no = None
                confirm_dialog.is_active = True
        else:  # SELL
            if (itype == "weapon_inst" and key_or_iid == player.equipped_weapon) or (itype == "armor_inst" and key_or_iid == player.equipped_armor) or (itype == "shield_inst" and key_or_iid == player.equipped_shield) or (itype == "accessory_inst" and key_or_iid == getattr(player, "equipped_accessory", None)):
                dialog.text = Text.Items.CANT_SELL_EQUIPPED; dialog.is_active = True; return
            if confirm_dialog:
                confirm_dialog.text = Text.UI.SHOP_SELL_CONFIRM.format(name=name, price=price)
                def do_sell():
                    ok = False
                    if itype == "weapon_inst": player.remove_weapon_by_iid(key_or_iid); ok = True
                    elif itype == "armor_inst": player.remove_armor_by_iid(key_or_iid); ok = True
                    elif itype == "shield_inst": player.remove_shield_by_iid(key_or_iid); ok = True
                    elif itype == "consumable": player.remove_item_by_key(key_or_iid); ok = True
                    elif itype == "stave_inst": player.remove_stave_by_iid(key_or_iid); ok = True
                    elif itype == "accessory_inst": player.remove_accessory_by_iid(key_or_iid); ok = True
                    if ok: player.coin += price; play_sfx(SOUND_PURCHASE); dialog.text = Text.Items.SOLD.format(name=name, price=price); dialog.auto_close_timer = 60
                    self.setup_sell_mode(player); self.cursor_idx = min(self.cursor_idx, len(self.items)-1); dialog.is_active = True
                confirm_dialog.on_yes = do_sell
                # 直前に使った鍛冶確認などの「いいえ」処理を持ち越さない。
                confirm_dialog.on_no = None
                confirm_dialog.is_active = True

    def draw(self, screen, player, guild_system=None):
        if not self.is_active: return
        draw_dialog_frame(screen, self.x, self.y, self.width, self.height, alpha=240)
        sep_x = self.x + self.width // 2
        pygame.draw.line(screen, (80, 100, 120), (sep_x, self.y + 40), (sep_x, self.y + self.height - 40), 2)
        mode_str = Text.UI.SHOP_TITLE_BUY if self.mode == "BUY" else Text.UI.SHOP_TITLE_SELL
        screen.blit(font_small_bold.render(f"{self.shop_name} ({mode_str})", True, (255, 200, 100)), (self.x + 30, self.y + 20))
        screen.blit(font_small_bold.render(Text.UI.GOLD_LABEL.format(coin=player.coin), True, (255, 255, 255)), (sep_x - 180, self.y + 20))
        if not self.items: screen.blit(self.font.render(Text.UI.SHOP_EMPTY, True, (150, 150, 150)), (self.x + 50, self.y + 100))
        else:
            start = max(0, self.cursor_idx - self.view_size // 2)
            if start + self.view_size > len(self.items): start = max(0, len(self.items) - self.view_size)
            for i in range(start, min(start + self.view_size, len(self.items))):
                item = self.items[i]; y = self.y + 80 + (i - start) * self.row_height; color = (255, 255, 255)
                is_eq = False
                iid, itype = item[0], item[1]
                if itype == "weapon_inst" and player.equipped_weapon == iid: is_eq = True
                elif itype == "armor_inst" and player.equipped_armor == iid: is_eq = True
                elif itype == "shield_inst" and player.equipped_shield == iid: is_eq = True
                elif itype == "accessory_inst" and player.equipped_accessory == iid: is_eq = True
                if is_eq: color = (150, 150, 150)
                if i == self.cursor_idx:
                    color = (255, 255, 100); pygame.draw.rect(screen, (60, 70, 90), (self.x + 20, y - 5, self.width // 2 - 40, self.row_height), border_radius=5)
                    screen.blit(self.font.render(">", True, color), (self.x + 35, y))
                name_str = f"{item[2]} x{item[4]}" if item[4] > 1 else item[2]
                max_w = self.width // 2 - 140
                if self.font.size(name_str)[0] > max_w:
                    while self.font.size(name_str + "...")[0] > max_w and len(name_str) > 0: name_str = name_str[:-1]
                    name_str += "..."
                screen.blit(self.font.render(name_str, True, color), (self.x + 65, y))
                if item[1] != "cancel": screen.blit(self.font.render(f"{item[3]} G", True, color), (sep_x - 110, y))

            if len(self.items) > self.view_size:
                indicator_x = sep_x - 30
                if start > 0:
                    pygame.draw.polygon(screen, (200, 200, 200), [(indicator_x, self.y + 70), (indicator_x - 8, self.y + 80), (indicator_x + 8, self.y + 80)])
                if start + self.view_size < len(self.items):
                    pygame.draw.polygon(screen, (200, 200, 200), [(indicator_x, self.y + self.height - 70), (indicator_x - 8, self.y + self.height - 80), (indicator_x + 8, self.y + self.height - 80)])

        if 0 <= self.cursor_idx < len(self.items):
            selected = self.items[self.cursor_idx]
            itype = selected[1].replace("_inst", "")
            master_key = selected[5] if len(selected) > 5 else selected[0]

            from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, ACCESSORY_DATA, STAVE_DATA, CONSUMABLE_DATA
            catalog = {"weapon": WEAPON_DATA, "armor": ARMOR_DATA, "shield": SHIELD_DATA, "accessory": ACCESSORY_DATA, "stave": STAVE_DATA, "consumable": CONSUMABLE_DATA}
            info = catalog.get(itype, {}).get(master_key, {})

            detail_y_offset = 0
            img_path = None
            if selected[1] != "cancel":
                img_path = info.get("image_path")
                if not img_path and info.get("image_dir"):
                    import os
                    idir = info.get("image_dir")
                    if os.path.exists(idir):
                        p = os.path.join(idir, "down.png")
                        if os.path.exists(p): img_path = p
                        else:
                            p = os.path.join(idir, f"{master_key}.png")
                            if os.path.exists(p): img_path = p
                            else:
                                try:
                                    files = [f for f in os.listdir(idir) if f.endswith(".png")]
                                    if files: img_path = os.path.join(idir, files[0])
                                except: pass

            if img_path:
                from systems.resources import load_image, scale_image_aspect
                img = load_image(img_path)
                if img:
                    tint = info.get("color_tint")
                    if tint:
                        img = img.copy()
                        w, h = img.get_size()
                        lower_rect = pygame.Rect(0, h // 2, w, h // 2)
                        img.fill((*tint, 255), rect=lower_rect, special_flags=pygame.BLEND_RGBA_MULT)
                    scaled_img = scale_image_aspect(img, 80, 80)
                    img_w, img_h = scaled_img.get_size()
                    screen.blit(scaled_img, (sep_x + 30 + (80 - img_w) // 2, self.y + 80 + (80 - img_h) // 2))
                    detail_y_offset = 90

            if selected[1] == "cancel":
                lines = [Text.UI.QUIT, "", "店を出ます"]
                draw_text_wrapped(screen, self.font, "\n".join(lines), sep_x + 30, self.y + 80 + detail_y_offset, self.width // 2 - 60, color=(220, 230, 240))
            else:
                inst = None
                from components.sprites.player import EquipInstance, StaveInstance
                if itype in ("weapon", "armor", "shield", "accessory"):
                    inst = EquipInstance(itype, master_key)
                elif itype == "stave":
                    charges = info.get("charges", 5)
                    inst = StaveInstance(master_key, charges=charges)

                if inst:
                    param_texts = []
                    for k, label in EQUIP_STAT_LABEL_MAP.items():
                        val = inst.get_stat(k, 0)
                        if val:
                            is_pct = k in ("crit_bonus", "block_chance_close", "block_chance_ranged", "armor_penetration")
                            val_to_use = val * 100 if is_pct and isinstance(val, float) else val
                            param_texts.append(f"{label}: {format_stat_value(val_to_use)}%" if is_pct else f"{label}: {format_stat_value(val)}")
                    for mk, mlabel in EQUIP_MAGIC_LABEL_MAP.items():
                        mval = inst.get_stat(mk, 0)
                        if mval:
                            is_pct = mk in ("magic_fire_damage", "magic_heal_ratio", "magic_knockback_damage")
                            val_to_use = mval * 100 if is_pct and isinstance(mval, float) else mval
                            param_texts.append(f"{mlabel}: {format_stat_value(val_to_use)}%" if is_pct else f"{mlabel}: {format_stat_value(mval)}")
                    desc = inst.get_stat("describe", "")
                    self.draw_equip_detail_right_panel(screen, inst, param_texts, desc, sep_x, detail_y_offset)
                else:
                    lines = [f"【{selected[2]}】", "", info.get("describe", "詳細情報はありません")]
                    draw_text_wrapped(screen, self.font, "\n".join(lines), sep_x + 30, self.y + 80 + detail_y_offset, self.width // 2 - 60, color=(220, 230, 240))


class WarehouseDialog(BaseListDialog):
    """預かり屋（倉庫）でのアイテム出し入れを行うダイアログ"""
    STATE_KEY = "warehouse_active"

    def __init__(self, screen_width, screen_height):
        super().__init__(screen_width, screen_height)
        self.mode = "MAIN"

    def on_activated(self):
        self.mode = "MAIN"
        self.setup_main_menu()

    def setup_main_menu(self):
        self.mode = "MAIN"; self.cursor_idx = 0
        self.items = [
            ("mode_deposit", "action", Text.UI.WAREHOUSE_DEPOSIT, "アイテムを預けます", False),
            ("mode_withdraw", "action", Text.UI.WAREHOUSE_WITHDRAW, "アイテムを引き出します", False),
            ("cancel", "cancel", Text.UI.QUIT, "店を出ます", False)
        ]

    def setup_deposit_mode(self, player):
        from constants import CONSUMABLE_DATA
        self.mode = "DEPOSIT"; self.cursor_idx = 0; self.items = []
        for idx, item in enumerate(player.items):
            info = CONSUMABLE_DATA.get(item["key"], {}); name = info.get("name", item["key"])
            self.items.append((idx, "consumable", f"{name} x{item['count']}" if item['count'] > 1 else name, item["key"], False))

        for eq in player.weapon_inventory:
            is_eq = (eq.iid == player.equipped_weapon)
            self.items.append((eq.iid, "weapon_inst", eq.get_name(), eq, is_eq))
        for eq in player.armor_inventory:
            is_eq = (eq.iid == player.equipped_armor)
            self.items.append((eq.iid, "armor_inst", eq.get_name(), eq, is_eq))
        for eq in player.shield_inventory:
            is_eq = (eq.iid == player.equipped_shield)
            self.items.append((eq.iid, "shield_inst", eq.get_name(), eq, is_eq))
        for st in player.stave_inventory:
            self.items.append((st.iid, "stave_inst", st.get_name_with_charges(), st, False))
        for eq in player.accessory_inventory:
            is_eq = (eq.iid == player.equipped_accessory)
            self.items.append((eq.iid, "accessory_inst", eq.get_name(), eq, is_eq))

        self.items.sort(key=lambda x: x[2].lower())
        self.items.append((-1, "back", Text.UI.QUIT, None, False))

    def setup_withdraw_mode(self, player):
        self.mode = "WITHDRAW"; self.cursor_idx = 0; self.items = []
        for idx, w in enumerate(player.warehouse_items):
            itype = w.get("type"); data = w.get("data")
            from components.sprites.player import EquipInstance, StaveInstance
            temp = StaveInstance.from_dict(data) if itype == "stave_inst" else EquipInstance.from_dict(data) if "inst" in itype else None
            name = temp.get_name_with_charges() if itype == "stave_inst" else temp.get_name() if temp else ""
            if not temp:
                from constants import CONSUMABLE_DATA
                name = CONSUMABLE_DATA.get(data, {}).get("name", data)
            self.items.append((idx, itype, name, data, False))
        self.items.sort(key=lambda x: x[2].lower())
        self.items.append((-1, "back", Text.UI.QUIT, None, False))

    def handle_events(self, events, player, confirm_dialog, dialog):
        if not self.is_active: return
        from systems.audio_manager import play_sfx
        from constants import SOUND_CURSOR_MOVE, SOUND_SELECT, SOUND_CANCEL, KEY_MOVE_UP, KEY_MOVE_DOWN, KEY_CANCEL, KEY_CONFIRM
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == KEY_CANCEL:
                    play_sfx(SOUND_CANCEL)
                    if self.mode == "MAIN": self.is_active = False
                    else: self.setup_main_menu()
                elif event.key == KEY_MOVE_UP:
                    if self.cursor_idx > 0:
                        play_sfx(SOUND_CURSOR_MOVE); self.cursor_idx -= 1
                    else:
                        self.cursor_idx = len(self.items) - 1
                        play_sfx(SOUND_CURSOR_MOVE)
                elif event.key == KEY_MOVE_DOWN:
                    if self.cursor_idx < len(self.items) - 1:
                        play_sfx(SOUND_CURSOR_MOVE); self.cursor_idx += 1
                    else:
                        self.cursor_idx = 0
                        play_sfx(SOUND_CURSOR_MOVE)
                elif event.key == KEY_CONFIRM:
                    if not self.items: return
                    sel = self.items[self.cursor_idx]; status = sel[1]
                    if status == "cancel": self.is_active = False; return
                    if status == "back": self.setup_main_menu(); return
                    play_sfx(SOUND_SELECT)
                    if status == "action":
                        if sel[0] == "mode_deposit": self.setup_deposit_mode(player)
                        elif sel[0] == "mode_withdraw": self.setup_withdraw_mode(player)
                    elif self.mode == "DEPOSIT": self._handle_deposit(player, sel, confirm_dialog, dialog)
                    elif self.mode == "WITHDRAW": self._handle_withdraw(player, sel, confirm_dialog, dialog)

    def _handle_deposit(self, player, selected, confirm_dialog, dialog):
        _id, itype, name, obj, is_equipped = selected
        if is_equipped:
            if dialog:
                dialog.text = "装備中のアイテムは預けられません \n装備を外してから再度お試しください"
                dialog.is_active = True
            return

        if len(player.warehouse_items) >= player.warehouse_max:
            if dialog: dialog.text = Text.NPC.WAREHOUSE_FULL; dialog.is_active = True
            return
        from constants import WAREHOUSE_FEE
        if player.coin < WAREHOUSE_FEE:
            if dialog: dialog.text = Text.NPC.WAREHOUSE_NO_FEE.format(fee=WAREHOUSE_FEE); dialog.is_active = True
            return
        if confirm_dialog:
            confirm_dialog.text = Text.NPC.WAREHOUSE_CONFIRM_DEPOSIT.format(fee=WAREHOUSE_FEE, name=name)
            def do_dep():
                player.coin -= WAREHOUSE_FEE
                if itype == "consumable":
                    player.warehouse_items.append({"type": itype, "data": obj})
                    player.remove_item_by_key(obj)
                else:
                    player.warehouse_items.append({"type": itype, "data": obj.to_dict()})
                    if itype == "weapon_inst": player.remove_weapon_by_iid(_id)
                    elif itype == "armor_inst": player.remove_armor_by_iid(_id)
                    elif itype == "shield_inst": player.remove_shield_by_iid(_id)
                    elif itype == "stave_inst": player.remove_stave_by_iid(_id)
                    elif itype == "accessory_inst": player.remove_accessory_by_iid(_id)
                self.setup_deposit_mode(player)
            confirm_dialog.on_yes = do_dep; confirm_dialog.is_active = True

    def _handle_withdraw(self, player, selected, confirm_dialog, dialog):
        w_idx, itype, name, data, is_equipped = selected
        from constants import WAREHOUSE_FEE
        if player.coin < WAREHOUSE_FEE:
            if dialog: dialog.text = Text.NPC.WAREHOUSE_NO_FEE.format(fee=WAREHOUSE_FEE); dialog.is_active = True
            return

        from constants import MAX_ITEM_SLOTS, MAX_EQUIP_SLOTS, MAX_STAVE_SLOTS
        bag_full = False
        if itype in ("weapon_inst", "armor_inst", "shield_inst", "accessory_inst"):
            if player.get_equipment_count() >= MAX_EQUIP_SLOTS: bag_full = True
        elif itype == "stave_inst":
            if player.get_stave_count() >= MAX_STAVE_SLOTS: bag_full = True
        elif itype == "consumable":
            ms = data.get("max_stack", 1) if isinstance(data, dict) else 1
            can_stack = any(it["key"] == data["key"] and it["count"] < ms for it in player.items) if ms > 1 and isinstance(data, dict) and "key" in data else False
            if not can_stack and player.get_item_count() >= MAX_ITEM_SLOTS: bag_full = True

        if bag_full:
            if dialog: dialog.text = Text.Items.BAG_FULL; dialog.is_active = True
            return
        if confirm_dialog:
            confirm_dialog.text = Text.NPC.WAREHOUSE_CONFIRM_WITHDRAW.format(fee=WAREHOUSE_FEE, name=name)
            def do_with():
                player.coin -= WAREHOUSE_FEE
                player.warehouse_items.pop(w_idx)
                if itype == "consumable": player.add_item_to_inventory(data)
                else:
                    from components.sprites.player import EquipInstance, StaveInstance
                    cls = StaveInstance if itype == "stave_inst" else EquipInstance
                    inst = cls.from_dict(data)
                    if itype == "weapon_inst": player.weapon_inventory.append(inst)
                    elif itype == "armor_inst": player.armor_inventory.append(inst)
                    elif itype == "shield_inst": player.shield_inventory.append(inst)
                    elif itype == "accessory_inst": player.accessory_inventory.append(inst)
                    elif itype == "stave_inst": player.stave_inventory.append(inst)
                self.setup_withdraw_mode(player)
            confirm_dialog.on_yes = do_with; confirm_dialog.is_active = True

    def draw(self, screen, player):
        if not self.is_active: return
        draw_dialog_frame(screen, self.x, self.y, self.width, self.height, alpha=240)
        sep_x = self.x + self.width // 2
        pygame.draw.line(screen, (80, 100, 120), (sep_x, self.y + 40), (sep_x, self.y + self.height - 40), 2)

        title_str = Text.UI.WAREHOUSE_TITLE
        if self.mode == "DEPOSIT": title_str += f" ({Text.UI.WAREHOUSE_MODE_DEPOSIT})"
        elif self.mode == "WITHDRAW": title_str += f" ({Text.UI.WAREHOUSE_MODE_WITHDRAW})"
        from systems.resources import font_small_bold
        screen.blit(font_small_bold.render(title_str, True, (255, 200, 100)), (self.x + 30, self.y + 20))
        cap_str = Text.UI.WAREHOUSE_CAPACITY.format(current=len(player.warehouse_items), max=player.warehouse_max)
        screen.blit(self.font.render(cap_str, True, (200, 200, 200)), (sep_x - 150, self.y + 20))

        if not self.items:
            screen.blit(self.font.render(Text.UI.WAREHOUSE_EMPTY, True, (150, 150, 150)), (self.x + 50, self.y + 100))
        else:
            start = max(0, self.cursor_idx - self.view_size // 2)
            if start + self.view_size > len(self.items): start = max(0, len(self.items) - self.view_size)
            for i in range(start, min(start + self.view_size, len(self.items))):
                item = self.items[i]; y_pos = self.y + 80 + (i - start) * self.row_height
                is_equipped = item[4]
                color = (255, 255, 255)
                if is_equipped: color = (130, 130, 130)
                if i == self.cursor_idx:
                    pygame.draw.rect(screen, (60, 70, 90), (self.x + 20, y_pos - 5, self.width // 2 - 40, self.row_height), border_radius=5)
                    screen.blit(self.font.render(">", True, (255, 255, 100)), (self.x + 35, y_pos))
                    if not is_equipped: color = (255, 255, 100)
                name = item[2]
                if is_equipped: name = f"[E] {name}"
                max_w = sep_x - self.x - 100
                if self.font.size(name)[0] > max_w:
                    while self.font.size(name + "...")[0] > max_w and len(name) > 0: name = name[:-1]
                    name += "..."
                screen.blit(self.font.render(name, True, color), (self.x + 65, y_pos))

        desc_x, desc_y, desc_w = sep_x + 30, self.y + 80, self.width // 2 - 60
        from constants import WAREHOUSE_FEE
        info_lines = [Text.UI.WAREHOUSE_FEE_PANEL.format(fee=WAREHOUSE_FEE, coin=player.coin), "", "【説明】"]
        if 0 <= self.cursor_idx < len(self.items):
            sel = self.items[self.cursor_idx]; status, data = sel[1], sel[3]
            is_equipped = sel[4]
            if status in ("action", "cancel", "back"):
                if data: info_lines.append(data)
            else:
                info_lines.append(f"品名: {sel[2]}")
                if is_equipped:
                    info_lines.append("※装備中のため預けられません")
                else:
                    info_lines.append("倉庫に預けます" if self.mode == "DEPOSIT" else "倉庫から引き出します")
                desc = ""
                if "inst" in status:
                    if hasattr(data, "get_stat"): desc = data.get_stat("describe", "")
                else:
                    from constants import CONSUMABLE_DATA
                    desc = CONSUMABLE_DATA.get(data, {}).get("describe", "")
                if desc: info_lines.append(""); info_lines.append(desc)
        draw_text_wrapped(screen, self.font, "\n".join(info_lines), desc_x, desc_y, desc_w, color=(220, 230, 240))


class BankDialog(BaseListDialog):
    """銀行での預金・引き出しを行うダイアログ"""
    STATE_KEY = "bank_active"

    def __init__(self, screen_width, screen_height):
        super().__init__(screen_width, screen_height)
        self.row_height = 40
        self.items = [
            ("DEPOSIT",  100,  Text.UI.BANK_DEPOSIT_100,   "100 G を銀行に預けます"),
            ("DEPOSIT",  1000, Text.UI.BANK_DEPOSIT_1000,  "1000 G を銀行に預けます"),
            ("DEPOSIT",  -1,   Text.UI.BANK_DEPOSIT_ALL,   "所持金を全額銀行に預けます"),
            ("WITHDRAW", 100,  Text.UI.BANK_WITHDRAW_100,  "100 G を引き出します"),
            ("WITHDRAW", 1000, Text.UI.BANK_WITHDRAW_1000, "1000 G を引き出します"),
            ("WITHDRAW", -1,   Text.UI.BANK_WITHDRAW_ALL,  "銀行残高を全額引き出します"),
            ("CANCEL",   0,    Text.UI.QUIT,               "銀行を出ます"),
        ]

    def get_title(self): return Text.UI.BANK_TITLE
    def get_header_right(self, player):
        return Text.UI.GOLD_LABEL.format(coin=player.coin) if player else ""
    def get_item_label(self, item, idx): return item[2]
    def get_item_color(self, item, idx, is_selected):
        if is_selected: return (255, 255, 100)
        m = item[0]
        if m == "DEPOSIT": return (160, 200, 255)
        if m == "WITHDRAW": return (160, 255, 180)
        return (180, 180, 180)
    def get_detail_lines(self, player):
        if not player: return []
        _, _, _, desc = self.items[self.cursor_idx]
        return [f"所持金:　　{player.coin} G", f"銀行残高: {player.bank_coin} G", "", "【説明】", desc]

    def handle_events(self, events, player, dialog):
        if not self.is_active: return
        from systems.audio_manager import play_sfx
        from constants import SOUND_SELECT, SOUND_CANCEL, SOUND_PURCHASE
        action = self._navigate(events)
        if action == "cancel":
            play_sfx(SOUND_CANCEL); self.is_active = False
        elif action == "confirm":
            mode, amt, label, _ = self.items[self.cursor_idx]
            if mode == "CANCEL":
                play_sfx(SOUND_CANCEL); self.is_active = False; return
            play_sfx(SOUND_SELECT)
            if mode == "DEPOSIT":
                actual = player.coin if amt == -1 else amt
                if actual <= 0: dialog.text = Text.NPC.BANK_NO_DEPOSIT
                elif player.coin < actual: dialog.text = Text.NPC.BANK_NO_MONEY
                else:
                    player.coin -= actual; player.bank_coin += actual
                    play_sfx(SOUND_PURCHASE)
                    dialog.text = Text.NPC.BANK_DEPOSITED.format(amount=actual)
                dialog.is_active = True
            elif mode == "WITHDRAW":
                actual = player.bank_coin if amt == -1 else amt
                if actual <= 0: dialog.text = Text.NPC.BANK_NO_BANK_MONEY
                elif player.bank_coin < actual: dialog.text = Text.NPC.BANK_NO_WITHDRAW
                else:
                    player.bank_coin -= actual; player.coin += actual
                    play_sfx(SOUND_PURCHASE)
                    dialog.text = Text.NPC.BANK_WITHDRAWN.format(amount=actual)
                dialog.is_active = True

    def draw(self, screen, player): super().draw(screen, player)
