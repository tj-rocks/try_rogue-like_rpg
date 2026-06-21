import pygame
from systems.game_state import game_state
from systems.resources import font_small, font_medium, font_hud
from wordings import Text
from systems.ui.ui_base import (
    get_standard_upper_layout, draw_dialog_frame, draw_text_wrapped, draw_stat_bar, StateKeyMixin
)


class StatusBar:
    """画面上部に表示されるヘッドアップディスプレイ(HP, ATK, DEFなど)"""
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.y = 15
        self.bar_height = 80
        self.font = font_hud

    def draw(self, screen, player, floor_level, guild_system=None):
        def draw_text_shadow(text, font, color, pos):
            shadow = font.render(text, True, (10, 15, 20))
            screen.blit(shadow, (pos[0] + 1, pos[1] + 1))
            surf = font.render(text, True, color)
            screen.blit(surf, pos)

        COLOR_BG = (20, 25, 35)
        COLOR_TEXT = (236, 240, 241)
        COLOR_HP_HIGH = (46, 204, 113)
        COLOR_HP_MID  = (241, 196, 15)
        COLOR_HP_LOW  = (231, 76, 60)
        COLOR_FLOOR   = (174, 214, 241)

        bar_x, bar_y = 20, 20
        bar_w, bar_h = 180, 16
        hp_ratio = player.hp / player.max_hp if player.max_hp > 0 else 0

        pygame.draw.rect(screen, (50, 60, 70), (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4), border_radius=3)
        pygame.draw.rect(screen, COLOR_BG, (bar_x, bar_y, bar_w, bar_h), border_radius=2)

        if hp_ratio <= 0.25:
            current_bar_color = COLOR_HP_LOW
        elif hp_ratio <= 0.666:
            current_bar_color = COLOR_HP_MID
        else:
            current_bar_color = COLOR_HP_HIGH
        fill_w = int(bar_w * hp_ratio)
        if fill_w > 0:
            pygame.draw.rect(screen, current_bar_color, (bar_x, bar_y, fill_w, bar_h), border_radius=2)
            bright_color = (min(current_bar_color[0] + 50, 255), min(current_bar_color[1] + 50, 255), min(current_bar_color[2] + 50, 255))
            pygame.draw.rect(screen, bright_color, (bar_x, bar_y, fill_w, bar_h // 2), border_radius=2)
            dark_color = (max(current_bar_color[0] - 40, 0), max(current_bar_color[1] - 40, 0), max(current_bar_color[2] - 40, 0))
            pygame.draw.line(screen, dark_color, (bar_x, bar_y + bar_h - 1), (bar_x + fill_w - 1, bar_y + bar_h - 1))

        pygame.draw.rect(screen, (120, 140, 160), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=2)

        hp_text = f"HP {player.hp}/{player.max_hp}"
        hp_text_w = self.font.size(hp_text)[0]
        draw_text_shadow(hp_text, self.font, COLOR_TEXT, (bar_x + bar_w + 12, bar_y - 4))

        rank_name = player.guild_rank
        draw_text_shadow(f"Rank: {rank_name}", self.font, (241, 196, 15), (bar_x, bar_y + bar_h + 6))

        buff_turns = 0
        buff_max = 1
        buff_color = None
        if getattr(player, "attack_buff_turns", 0) > 0:
            buff_turns = player.attack_buff_turns
            buff_max = max(1, getattr(player, "attack_buff_max_turns", buff_turns))
            buff_color = (231, 76, 60)
        elif getattr(player, "regen_buff_turns", 0) > 0:
            buff_turns = player.regen_buff_turns
            buff_max = max(1, getattr(player, "regen_buff_max_turns", buff_turns))
            buff_color = (46, 204, 113)
        elif getattr(player, "magic_buff_turns", 0) > 0:
            buff_turns = player.magic_buff_turns
            buff_max = max(1, getattr(player, "magic_buff_max_turns", buff_turns))
            buff_color = (155, 89, 182)

        if buff_color:
            bbar_x = bar_x + bar_w + 12 + hp_text_w + 10
            bbar_y = bar_y
            bbar_w = 60
            bbar_h = bar_h
            ratio = buff_turns / buff_max
            fill_w = max(1, int(bbar_w * ratio))

            pygame.draw.rect(screen, (50, 60, 70), (bbar_x - 2, bbar_y - 2, bbar_w + 4, bbar_h + 4), border_radius=3)
            pygame.draw.rect(screen, COLOR_BG, (bbar_x, bbar_y, bbar_w, bbar_h), border_radius=2)
            pygame.draw.rect(screen, buff_color, (bbar_x, bbar_y, fill_w, bbar_h), border_radius=2)
            bright = (min(buff_color[0]+50,255), min(buff_color[1]+50,255), min(buff_color[2]+50,255))
            pygame.draw.rect(screen, bright, (bbar_x, bbar_y, fill_w, bbar_h//2), border_radius=2)
            pygame.draw.rect(screen, buff_color, (bbar_x, bbar_y, bbar_w, bbar_h), 1, border_radius=2)

        floor_str = Text.UI.VILLAGE if floor_level == 0 else Text.UI.FLOOR.format(level=floor_level)
        floor_surf = font_medium.render(floor_str, True, COLOR_FLOOR)
        fx = (self.screen_width - floor_surf.get_width()) // 2
        fy = 15
        f_shadow = font_medium.render(floor_str, True, (10, 15, 20))
        screen.blit(f_shadow, (fx + 2, fy + 2))
        screen.blit(floor_surf, (fx, fy))

        rx = self.screen_width - 180
        ry = 15
        draw_text_shadow(f"Gold: {player.coin}", self.font, COLOR_TEXT, (rx, ry))
        draw_text_shadow(f"GP: {player.guild_point}", self.font, (174, 214, 241), (rx, ry + 23))


class StatusDialog(StateKeyMixin):
    """ステータスを詳細表示する画面 (Sキー)"""
    STATE_KEY = "status_active"
    def __init__(self, screen_width, screen_height):
        self.x, self.y, self.width, self.height = get_standard_upper_layout(screen_width, screen_height)
        from systems.resources import font_small
        self.font = font_small
        self.mode = "STATUS"
        self.cursor_idx = 0
        self.categories = [("STATUS", "基本ステータス"), ("BONUS", "装備の加護"), ("QUIT", Text.UI.QUIT)]
        self._back_dialog = None

    def _on_open(self):
        if self.mode not in ("STATUS", "QUESTS", "BONUS", "MENU"):
            self.mode = "STATUS"
        if self.mode in ("MENU", "STATUS", "BONUS", "CURSE"):
            self.categories = [("STATUS", "基本ステータス"), ("BONUS", "装備の加護"), ("CURSE", "呪い進行度"), ("QUIT", Text.UI.QUIT)]
            if self.mode in ("MENU", "STATUS"):
                self.mode = "STATUS"
                self.cursor_idx = 0
            elif self.mode == "BONUS":
                self.cursor_idx = 1
            elif self.mode == "CURSE":
                self.cursor_idx = 2
        else:
            self.categories = [("QUIT", Text.UI.QUIT)]
            self.cursor_idx = 0
        print(f"[UI] Open StatusDialog (Mode: {self.mode})")

    def _on_close(self):
        self.mode = "STATUS"
        print(f"[UI] Close StatusDialog")

    def _close_back(self):
        self.is_active = False
        if self._back_dialog:
            self._back_dialog.is_active = True

    def handle_events(self, events, player=None):
        if not self.is_active: return
        from constants import KEY_CANCEL, KEY_CONFIRM, KEY_MENU, KEY_MOVE_UP, KEY_MOVE_DOWN
        for event in events:
            if event.type == pygame.KEYDOWN:
                if len(self.categories) > 1:
                    if event.key == KEY_MOVE_UP:
                        self.cursor_idx = (self.cursor_idx - 1) % len(self.categories)
                        cat = self.categories[self.cursor_idx][0]
                        if cat != "QUIT":
                            self.mode = cat
                        print(f"[UI] Status Cursor: {self.categories[self.cursor_idx][1]} (Mode: {self.mode})")
                    elif event.key == KEY_MOVE_DOWN:
                        self.cursor_idx = (self.cursor_idx + 1) % len(self.categories)
                        cat = self.categories[self.cursor_idx][0]
                        if cat != "QUIT":
                            self.mode = cat
                        print(f"[UI] Status Cursor: {self.categories[self.cursor_idx][1]} (Mode: {self.mode})")
                    elif event.key in (KEY_CONFIRM, KEY_CANCEL, KEY_MENU):
                        self._close_back()
                else:
                    if event.key in (KEY_CANCEL, KEY_CONFIRM, KEY_MENU):
                        self._close_back()

    def _draw_enhance_progress(self, screen, x, y, player, stat_key, bar_width, font):
        equip_inst = None
        enhance_stat_key = None

        if stat_key == "total_attack":
            equip_inst = player._find_equip_inst(player.weapon_inventory, player.equipped_weapon)
            enhance_stat_key = "attack_bonus"
        elif stat_key == "total_defense":
            armor = player._find_equip_inst(player.armor_inventory, player.equipped_armor)
            shield = player._find_equip_inst(player.shield_inventory, player.equipped_shield)
            total_enhance = 0
            for inst in [armor, shield]:
                if inst:
                    total_enhance += inst.get_enhance_bonus("defense_bonus")
            if total_enhance > 0:
                ratio = min(total_enhance / 10, 1.0)
                self._draw_small_bar(screen, x, y, ratio, bar_width, (180, 140, 60), font, f"+{total_enhance:.1f}")
            return
        elif stat_key == "max_hp":
            armor = player._find_equip_inst(player.armor_inventory, player.equipped_armor)
            shield = player._find_equip_inst(player.shield_inventory, player.equipped_shield)
            total_enhance = 0
            for inst in [armor, shield]:
                if inst:
                    total_enhance += inst.get_enhance_bonus("hp_bonus")
            if total_enhance > 0:
                ratio = min(total_enhance / 10, 1.0)
                self._draw_small_bar(screen, x, y, ratio, bar_width, (60, 140, 180), font, f"+{total_enhance:.1f}")
            return
        elif stat_key == "block_close":
            weapon = player._find_equip_inst(player.weapon_inventory, player.equipped_weapon)
            armor = player._find_equip_inst(player.armor_inventory, player.equipped_armor)
            shield = player._find_equip_inst(player.shield_inventory, player.equipped_shield)
            total_enhance = 0
            for inst in [weapon, armor, shield]:
                if inst:
                    total_enhance += inst.get_enhance_bonus("block_chance_close") * 100
            if total_enhance > 0:
                ratio = min(total_enhance / 10, 1.0)
                self._draw_small_bar(screen, x, y, ratio, bar_width, (140, 180, 60), font, f"+{total_enhance:.1f}%")
            return
        elif stat_key == "block_ranged":
            weapon = player._find_equip_inst(player.weapon_inventory, player.equipped_weapon)
            armor = player._find_equip_inst(player.armor_inventory, player.equipped_armor)
            shield = player._find_equip_inst(player.shield_inventory, player.equipped_shield)
            total_enhance = 0
            for inst in [weapon, armor, shield]:
                if inst:
                    total_enhance += inst.get_enhance_bonus("block_chance_ranged") * 100
            if total_enhance > 0:
                ratio = min(total_enhance / 10, 1.0)
                self._draw_small_bar(screen, x, y, ratio, bar_width, (140, 180, 60), font, f"+{total_enhance:.1f}%")
            return

        if equip_inst and enhance_stat_key:
            enhance_bonus = equip_inst.get_enhance_bonus(enhance_stat_key)
            if enhance_bonus > 0:
                ratio = min(enhance_bonus / 10, 1.0)
                color = (180, 140, 60) if stat_key == "total_attack" else (100, 100, 120)
                self._draw_small_bar(screen, x, y, ratio, bar_width, color, font, f"+{enhance_bonus:.1f}")

    def _draw_small_bar(self, screen, x, y, ratio, bar_width, color, font, label):
        bar_height = 6
        bg_rect = pygame.Rect(x, y, bar_width, bar_height)
        pygame.draw.rect(screen, (50, 50, 60), bg_rect, border_radius=2)
        fill_w = int(bar_width * ratio)
        fill_rect = pygame.Rect(x, y, fill_w, bar_height)
        pygame.draw.rect(screen, color, fill_rect, border_radius=2)
        pygame.draw.rect(screen, (80, 80, 90), bg_rect, width=1, border_radius=2)
        label_surf = font.render(label, True, (200, 200, 200))
        screen.blit(label_surf, (x + bar_width + 4, y - 2))

    def draw(self, screen, player):
        if not self.is_active: return
        draw_dialog_frame(screen, self.x, self.y, self.width, self.height)

        separator_x = self.x + 240
        pygame.draw.line(screen, (80, 100, 120), (separator_x, self.y + 30), (separator_x, self.y + self.height - 30), 2)

        for i, (code, label) in enumerate(self.categories):
            y_pos = self.y + 60 + i * 45
            color = (255, 255, 255)
            is_highlighted = (len(self.categories) == 1) or (i == self.cursor_idx)

            if is_highlighted:
                color = (255, 255, 100)
                pygame.draw.rect(screen, (60, 70, 90), (self.x + 20, y_pos - 5, 200, 40), border_radius=5)
                screen.blit(self.font.render(">", True, color), (self.x + 35, y_pos))

            screen.blit(self.font.render(label, True, color), (self.x + 65, y_pos))

        content_x, content_y = separator_x + 40, self.y + 40
        cw = self.width - (separator_x - self.x) - 80

        if self.mode == "STATUS":
            weapon_inst = player._find_equip_inst(player.weapon_inventory, player.equipped_weapon)
            armor_inst = player._find_equip_inst(player.armor_inventory, player.equipped_armor)
            shield_inst = player._find_equip_inst(player.shield_inventory, player.equipped_shield)

            hp_reduction = 0
            if "hp" in getattr(player, "cursed_stats", []):
                hp_bonus = 0
                if armor_inst: hp_bonus += armor_inst.get_stat("hp_bonus", 0)
                if shield_inst: hp_bonus += shield_inst.get_stat("hp_bonus", 0)
                raw_max_hp = int(player._base_max_hp + hp_bonus)
                hp_reduction = raw_max_hp - player.max_hp

            atk_reduction = 0
            if "attack" in getattr(player, "cursed_stats", []):
                atk_bonus = 0
                if weapon_inst: atk_bonus += weapon_inst.get_stat("attack_bonus", 0) + weapon_inst.get_enhance_bonus("attack_bonus")
                if armor_inst: atk_bonus += armor_inst.get_stat("attack_bonus", 0)
                if shield_inst: atk_bonus += shield_inst.get_stat("attack_bonus", 0)
                raw_attack = round(player.attack + atk_bonus, 1)
                atk_reduction = round(raw_attack - player.total_attack, 1)
                if atk_reduction % 1 == 0:
                    atk_reduction = int(atk_reduction)

            def_reduction = 0
            if "defense" in getattr(player, "cursed_stats", []):
                def_bonus = 0
                for inv, eid, key in [(player.armor_inventory, player.equipped_armor, "defense_bonus"), (player.shield_inventory, player.equipped_shield, "defense_bonus")]:
                    inst = player._find_equip_inst(inv, eid)
                    if inst: def_bonus += inst.get_stat(key, 0) + inst.get_enhance_bonus(key)
                raw_defense = round(player.defense + def_bonus, 1)
                def_reduction = round(raw_defense - player.total_defense, 1)
                if def_reduction % 1 == 0:
                    def_reduction = int(def_reduction)

            eva_close_reduction = 0
            eva_ranged_reduction = 0
            if "evasion" in getattr(player, "cursed_stats", []):
                orig_close = 0.0
                orig_ranged = 0.0
                for inv, eid in [(player.weapon_inventory, player.equipped_weapon), (player.armor_inventory, player.equipped_armor), (player.shield_inventory, player.equipped_shield)]:
                    inst = player._find_equip_inst(inv, eid)
                    if inst:
                        orig_close += inst.get_stat("block_chance_close", 0.0) + inst.get_enhance_bonus("block_chance_close")
                        orig_ranged += inst.get_stat("block_chance_ranged", 0.0) + inst.get_enhance_bonus("block_chance_ranged")
                eva_close_reduction = int(round((orig_close - player.block_chance_close) * 100))
                eva_ranged_reduction = int(round((orig_ranged - player.block_chance_ranged) * 100))

            header_lines = [
                f"【基本ステータス】",
                f"ランク：{player.guild_rank} (GP:{player.guild_point})",
                f"HP  ：{player.hp} / {player.max_hp}" + (f" (-{hp_reduction})" if hp_reduction > 0 else ""),
            ]
            draw_text_wrapped(screen, self.font, "\n".join(header_lines), content_x, content_y, cw)

            eva_close_pct = int(round(player.block_chance_close * 100))
            eva_ranged_pct = int(round(player.block_chance_ranged * 100))

            bar_items = [
                ("攻撃力", player.total_attack, "total_attack"),
                ("防御力", player.total_defense, "total_defense"),
                ("最大HP", player.max_hp, "max_hp"),
                ("近接回避", eva_close_pct, "block_close"),
                ("射撃回避", eva_ranged_pct, "block_ranged"),
            ]

            bar_start_y = content_y + 120
            line_h = 22
            half_w = cw // 2
            bar_w = min(half_w - 20, 90)

            for i, (label, value, stat_key) in enumerate(bar_items):
                y = bar_start_y + i * line_h
                curse_suffix = ""
                if stat_key == "total_attack" and atk_reduction > 0:
                    curse_suffix = f" (-{atk_reduction})"
                elif stat_key == "total_defense" and def_reduction > 0:
                    curse_suffix = f" (-{def_reduction})"
                elif stat_key == "block_close" and eva_close_reduction > 0:
                    curse_suffix = f" (-{eva_close_reduction}%)"
                elif stat_key == "block_ranged" and eva_ranged_reduction > 0:
                    curse_suffix = f" (-{eva_ranged_reduction}%)"

                lbl_text = label + curse_suffix
                font_y = y - 3
                bar_y = y + 5
                screen.blit(self.font.render(lbl_text, True, (200, 210, 220)), (content_x, font_y))
                draw_stat_bar(screen, content_x + half_w, bar_y, value, stat_key,
                             bar_width=bar_w, bar_height=12, font=self.font)

                self._draw_enhance_progress(screen, content_x + half_w, bar_y + 14,
                                           player, stat_key, bar_w, self.font)

            equip_y = bar_start_y + len(bar_items) * line_h + 15
            equip_lines = [
                f"【装備中】",
                f"武器：{weapon_inst.get_name() if weapon_inst else 'なし'}",
                f"鎧  ：{armor_inst.get_name() if armor_inst else 'なし'}",
                f"盾  ：{shield_inst.get_name() if shield_inst else 'なし'}",
            ]
            draw_text_wrapped(screen, self.font, "\n".join(equip_lines), content_x, equip_y, cw)

        elif self.mode == "CURSE":
            curse_level = getattr(player, "curse_level", 0)
            cursed_stats = getattr(player, "cursed_stats", [])

            lines = ["【呪い進行度】"]

            if curse_level == 0:
                lines.append("呪いはかかっていません")
                lines.append("")
                lines.append("死亡するたびに呪いの段階が進み")
                lines.append("最大5段階まで深刻化します")
            else:
                lines.append(f"段階: {curse_level} / 5")
                lines.append("")

                if "hp" in cursed_stats:
                    reduction_pct = curse_level * 10
                    lines.append(f"最大HP: -{reduction_pct}%")
                if "attack" in cursed_stats:
                    lines.append("攻撃力: 低下中")
                if "defense" in cursed_stats:
                    lines.append("防御力: 低下中")
                if "evasion" in cursed_stats:
                    lines.append("回避率: 低下中")

                lines.append("")
                lines.append("【解除方法】")
                lines.append("ギルドの神官にGPとゴールドで解除依頼")

            draw_text_wrapped(screen, self.font, "\n".join(lines), content_x, content_y, cw)

        elif self.mode == "BONUS":
            weapon_inst = player._find_equip_inst(player.weapon_inventory, player.equipped_weapon)
            armor_inst = player._find_equip_inst(player.armor_inventory, player.equipped_armor)
            shield_inst = player._find_equip_inst(player.shield_inventory, player.equipped_shield)

            equips = [inst for inst in [weapon_inst, armor_inst, shield_inst] if inst]

            def get_total_bonus(stat_key):
                total = 0
                for inst in equips:
                    base = inst.get_stat(stat_key, 0)
                    enhance = inst.get_enhance_bonus(stat_key) if hasattr(inst, "get_enhance_bonus") else 0
                    total += base + enhance
                return total

            total_atk = get_total_bonus("attack_bonus")
            total_def = get_total_bonus("defense_bonus")
            total_hp = get_total_bonus("hp_bonus")
            total_acc_close = get_total_bonus("accuracy_bonus_close")
            total_crit = get_total_bonus("crit_rate")
            total_block_close = get_total_bonus("block_chance_close")
            total_block_ranged = get_total_bonus("block_chance_ranged")
            total_stave = get_total_bonus("magic_stave_bonus")
            total_regen = get_total_bonus("regen_bonus")
            total_aggro = get_total_bonus("aggro_mod")
            total_stupidity = get_total_bonus("stupidity")
            total_penetration = get_total_bonus("armor_penetration")
            total_backstab = get_total_bonus("backstab_crit_bonus")
            total_fire_dmg = get_total_bonus("magic_fire_damage")
            total_fire_range = get_total_bonus("magic_fire_range")
            total_heal_ratio = get_total_bonus("magic_heal_ratio")
            total_knockback = get_total_bonus("magic_knockback_damage")
            total_invincible = get_total_bonus("magic_invincible_turns")
            total_barrier = get_total_bonus("magic_barrier_turns")

            def format_val(val):
                if val % 1 == 0:
                    val_str = str(int(val))
                else:
                    val_str = str(round(val, 2))
                return f"+{val_str}" if val > 0 else val_str

            left_lines = ["【基本加護】"]
            has_any_bonus = False

            if total_hp != 0:
                left_lines.append(f"最大HP    {format_val(total_hp)}")
                has_any_bonus = True
            if total_atk != 0:
                left_lines.append(f"攻撃力    {format_val(total_atk)}")
                has_any_bonus = True
            if total_def != 0:
                left_lines.append(f"防御力    {format_val(total_def)}")
                has_any_bonus = True
            if total_acc_close != 0:
                val = total_acc_close * 100 if isinstance(total_acc_close, float) and total_acc_close < 1.0 else total_acc_close
                left_lines.append(f"命中率    {format_val(val)}%")
                has_any_bonus = True
            if total_crit != 0:
                val = total_crit * 100 if isinstance(total_crit, float) and total_crit < 1.0 else total_crit
                left_lines.append(f"会心率    {format_val(val)}%")
                has_any_bonus = True
            if total_block_close != 0:
                val = total_block_close * 100 if isinstance(total_block_close, float) and total_block_close < 1.0 else total_block_close
                left_lines.append(f"近距離回避 {format_val(val)}%")
                has_any_bonus = True
            if total_block_ranged != 0:
                val = total_block_ranged * 100 if isinstance(total_block_ranged, float) and total_block_ranged < 1.0 else total_block_ranged
                left_lines.append(f"遠距離回避 {format_val(val)}%")
                has_any_bonus = True
            if total_regen != 0:
                left_lines.append(f"自然回復  {format_val(total_regen)}/ターン")
                has_any_bonus = True
            if total_aggro != 0:
                left_lines.append(f"感知補正  {format_val(total_aggro)}")
                has_any_bonus = True
            if total_penetration != 0:
                val = total_penetration * 100 if isinstance(total_penetration, float) and total_penetration <= 1.0 else total_penetration
                from wordings import Text
                left_lines.append(f"{Text.UI.STAT_ARMOR_PENETRATION_LABEL}  {format_val(val)}%")
                has_any_bonus = True
            if total_stupidity != 0:
                from wordings import Text
                left_lines.append(f"{Text.UI.STAT_CONFUSION_LABEL}      {format_val(total_stupidity)}")
                has_any_bonus = True
            if total_backstab != 0:
                val = total_backstab * 100 if isinstance(total_backstab, float) and total_backstab <= 1.0 else total_backstab
                left_lines.append(f"背後会心  {format_val(val)}%")
                has_any_bonus = True

            right_lines = ["【魔法加護】"]
            has_magic_bonus = False

            if total_stave != 0:
                right_lines.append(f"杖回数    {format_val(total_stave)}")
                has_magic_bonus = True
            if total_fire_dmg != 0:
                val = total_fire_dmg * 100 if isinstance(total_fire_dmg, float) and total_fire_dmg < 1.0 else total_fire_dmg
                right_lines.append(f"火炎ダメ  {format_val(val)}%")
                has_magic_bonus = True
            if total_fire_range != 0:
                right_lines.append(f"火炎射程  {format_val(total_fire_range)}マス")
                has_magic_bonus = True
            if total_heal_ratio != 0:
                val = total_heal_ratio * 100 if isinstance(total_heal_ratio, float) and total_heal_ratio < 1.0 else total_heal_ratio
                right_lines.append(f"回復効果  {format_val(val)}%")
                has_magic_bonus = True
            if total_knockback != 0:
                val = total_knockback * 100 if isinstance(total_knockback, float) and total_knockback < 1.0 else total_knockback
                right_lines.append(f"吹飛ダメ  {format_val(val)}%")
                has_magic_bonus = True
            if total_invincible != 0:
                right_lines.append(f"無敵効果  {format_val(total_invincible)}ターン")
                has_magic_bonus = True
            if total_barrier != 0:
                right_lines.append(f"障壁ターン {format_val(total_barrier)}ターン")
                has_magic_bonus = True

            if not has_magic_bonus:
                right_lines.append("なし")

            if not has_any_bonus and not has_magic_bonus:
                screen.blit(self.font.render("適用中の装備の加護はありません", True, (200, 200, 200)), (content_x, content_y))
            else:
                line_h = self.font.get_height() + 5
                col_w = cw // 2
                for i, text in enumerate(left_lines):
                    color = (255, 220, 80) if i == 0 else (220, 220, 220)
                    screen.blit(self.font.render(text, True, color), (content_x, content_y + i * line_h))
                right_x = content_x + col_w
                for i, text in enumerate(right_lines):
                    color = (180, 200, 255) if i == 0 else (220, 220, 220)
                    screen.blit(self.font.render(text, True, color), (right_x, content_y + i * line_h))

        elif self.mode == "QUESTS":
            lines = [f"【受注中のクエスト】"]
            if not player.active_quests:
                lines.append("現在受注している依頼はありません")
            else:
                for q in player.active_quests:
                    prog = ""
                    if q.get("type") == "hunt":
                        prog = f"({player.quest_tokens.get(q.get('target_key'), 0)}/{q.get('amount') or 0})"
                    elif q.get("type") == "delivery":
                        count = player._count_owned_items(q.get('target_key'))
                        prog = f"({count}/{q.get('amount') or 0})"

                    if q.get("is_rank_up"):
                        prog = ""

                    reward = q.get("reward_gold", 0)
                    lines.append(f"・{q.get('title')}")
                    if prog:
                        lines.append(f"  進捗: {prog} {q.get('target_name', '')}")
                    lines.append(f"  報酬: {reward} G")

                    desc = q.get("description")
                    if desc:
                        lines.append("  詳細:")
                        desc_lines = desc.split("\n")
                        for dl in desc_lines:
                            lines.append(f"    {dl}")

            draw_text_wrapped(screen, self.font, "\n".join(lines), content_x, content_y, cw)

        else:
            draw_text_wrapped(screen, self.font, Text.UI.STATUS_MENU_HINT, content_x, content_y, cw, color=(150, 150, 150))
