import pygame
from systems.game_state import game_state
from systems.resources import font_small, font_small_bold, font_medium
from wordings import Text
from systems.ui.ui_base import (
    get_standard_upper_layout, draw_dialog_frame, draw_text_wrapped, BaseListDialog, StateKeyMixin
)


class GuildDialog(StateKeyMixin):
    """冒険者ギルドでの依頼受注・報告を行うダイアログ"""
    STATE_KEY = "guild_active"
    def __init__(self, screen_width, screen_height):
        self.x, self.y, self.width, self.height = get_standard_upper_layout(screen_width, screen_height)
        self.font = font_small
        self.row_height = 32
        self.view_size = 10
        self.cursor_idx = 0
        self.items = []
        self.mode = "MENU"
        self._skip_auto_report = False
        self._pending_report = None
        self.dungeon_ref = None
        self.npc_role = "guild_receptionist"
        self.ore_gift_dialog = None

    def _on_open(self):
        print(f"[UI] Open GuildDialog (Mode: {self.mode})")
        self._skip_auto_report = False
        self.cursor_idx = 0
        if self.mode != "AUTO_REPORT":
            self.mode = "MENU"

    def setup(self, player, dungeon, npc_role=None):
        if npc_role is not None:
            self.npc_role = npc_role
        self.dungeon_ref = dungeon
        self.items = []

        if self.mode == "AUTO_REPORT":
            self.mode = "MENU"

        if self.mode == "MENU":
            if not self._skip_auto_report:
                completed_q = None
                for q in player.active_quests:
                    reportable = self._is_reportable(player, q)
                    is_ru = q.get("is_rank_up", False)
                    if not reportable:
                        continue
                    if self.npc_role == "guild_rankup" and not is_ru:
                        continue
                    if self.npc_role == "guild_receptionist" and is_ru:
                        continue
                    completed_q = q
                    break

                if completed_q:
                    self._pending_report = completed_q
                else:
                    self._pending_report = None

            if self.npc_role == "guild_rankup":
                next_rank_data = dungeon.guild_system.get_next_rank_data(player.guild_rank)
                if next_rank_data and player.guild_point >= next_rank_data["required_gp"]:
                    already_active = any(q.get("is_rank_up") for q in player.active_quests)
                    if not already_active:
                        self.items.append(("mode", "ACCEPT_RANKUP", "昇級試験を受ける", f"{next_rank_data['rank']}ランクへの昇格試験に挑戦します"))

                _, info_desc = dungeon.guild_system.get_next_rank_info(player)
                if next_rank_data and player.guild_point >= next_rank_data["required_gp"]:
                    already_active = any(q.get("is_rank_up") for q in player.active_quests)
                    if already_active:
                        info_desc += "\n(昇級試験を受注中です。対象フロア最奥へ向かってください)"
                self.items.append(("info_rank", None, "ランク情報を確認", info_desc))
                self.items.append(("cancel", None, "ギルドを出る", "ギルドメニューを終了します"))
            else:
                self.items = [
                    ("mode", "ACCEPT_DAILY", "日常依頼を受注", "ランダムに生成された日常的な依頼を受けます"),
                    ("mode", "ACCEPT_FIXED", "特別な依頼を見る", "特定の条件で発生する特別な依頼を確認します"),
                    ("mode", "ABANDON", "依頼破棄", "現在受けている依頼をキャンセルします"),
                    ("mode", "SAVE", "記録する", "現在の進行状況をセーブします"),
                    ("cancel", None, "ギルドを出る", "ギルドメニューを終了します")
                ]

        elif self.mode == "REPORT":
            for q in player.active_quests:
                if self._is_reportable(player, q):
                    is_ru = q.get("is_rank_up", False)
                    if self.npc_role == "guild_rankup" and not is_ru:
                        continue
                    if self.npc_role == "guild_receptionist" and is_ru:
                        continue
                    self.items.append(("active", q))
            self.items.append(("back", None, Text.UI.QUIT))

        elif self.mode == "ACCEPT_DAILY":
            for q in dungeon.guild_system.available_quests:
                self.items.append(("available", q))
            self.items.append(("back", None, Text.UI.QUIT))

        elif self.mode == "ACCEPT_RANKUP":
            next_rank_data = dungeon.guild_system.get_next_rank_data(player.guild_rank)
            if next_rank_data and player.guild_point >= next_rank_data["required_gp"]:
                rank_up_q = self._create_rank_up_quest(next_rank_data)
                self.items.append(("available", rank_up_q))
            self.items.append(("back", None, Text.UI.QUIT))

        elif self.mode == "ACCEPT_FIXED":
            for q in dungeon.guild_system.fixed_quests:
                self.items.append(("available", q))
            self.items.append(("back", None, Text.UI.QUIT))

        elif self.mode == "ABANDON":
            for q in player.active_quests:
                self.items.append(("active_to_abandon", q))
            self.items.append(("back", None, Text.UI.QUIT))

    def _is_reportable(self, player, q):
        return player.is_quest_reportable(q)

    def _calc_reward(self, player, q):
        reward_gold = q.get("reward_gold", 0)
        reward_gp = q.get("reward_gp", 0)
        q_min_rank = q.get("min_rank")
        if q_min_rank:
            from constants import RANK_ORDER
            if q_min_rank in RANK_ORDER and player.guild_rank in RANK_ORDER:
                if RANK_ORDER.index(player.guild_rank) > RANK_ORDER.index(q_min_rank):
                    reward_gold = max(1, reward_gold // 4)
                    reward_gp = max(1, reward_gp // 4)
        return reward_gold, reward_gp

    def _create_rank_up_quest(self, next_rank_data):
        from constants import CONSUMABLE_DATA
        cert_data = CONSUMABLE_DATA.get(next_rank_data["rank_up_item"], {})
        target_floor = cert_data.get("min_floor", 1)
        description = f"次のランクへ昇級するための試験です \n対象フロアの最奥に配置される『{cert_data.get('name', '冒険者の証')}』を回収してきてください (対象階層: {target_floor}F)"
        return {
            "id": f"rank_up_{next_rank_data['rank']}",
            "type": "delivery", "is_rank_up": True,
            "target_key": next_rank_data["rank_up_item"],
            "target_name": cert_data.get("name", "冒険者の証"),
            "amount": 1, "reward_gold": next_rank_data.get("rank_up_reward_gold", 0), "reward_gp": 0,
            "next_rank": next_rank_data["rank"],
            "title": "冒険者の証の回収" if next_rank_data['rank'] == "F" else Text.Guild.QUEST_RANK_UP_TITLE.format(rank=next_rank_data['rank']),
            "description": description
        }

    def handle_events(self, events, player, dialog, confirm_dialog):
        from constants import KEY_MOVE_UP, KEY_MOVE_DOWN, KEY_CANCEL, KEY_CONFIRM
        if not self.is_active: return

        if self._pending_report and not confirm_dialog.is_active:
            q = self._pending_report

            if q.get("is_rank_up"):
                from constants import MAX_ITEM_SLOTS
                if len(player.items) >= MAX_ITEM_SLOTS:
                    dialog.text = "お祝いの品をお渡ししたいのですが、\nバッグがいっぱいのようですね。\n荷物を整理してからもう一度話しかけてください。"
                    dialog.is_active = True
                    self._pending_report = None
                    self.is_active = False
                    return

            if q.get("type") == "delivery":
                t_name = q.get('target_name') or q.get('target_key')
                confirm_dialog.text = Text.UI.GUILD_REPORT_CONFIRM.format(name=t_name)
            else:
                confirm_dialog.text = Text.UI.GUILD_REPORT_CONFIRM_GENERIC

            def on_confirm():
                self._report_quest(player, q, dialog)
                self._pending_report = None
            def on_decline():
                self._pending_report = None
                self._skip_auto_report = True
                self.setup(player, self.dungeon_ref)
            confirm_dialog.on_yes = on_confirm
            confirm_dialog.on_no = on_decline
            confirm_dialog.is_active = True
            return

        from systems.audio_manager import play_sfx
        from constants import SOUND_CURSOR_MOVE, SOUND_SELECT, SOUND_CANCEL
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == KEY_MOVE_UP:
                    if self.items:
                        if self.cursor_idx > 0:
                            self.cursor_idx -= 1
                        else:
                            self.cursor_idx = len(self.items) - 1
                        item = self.items[self.cursor_idx]
                        item_name = item[2] if len(item) > 2 else (item[1].get('title', 'Unknown') if isinstance(item[1], dict) else 'Unknown')
                        if item[0] in ("cancel", "back"): item_name = Text.UI.QUIT
                        print(f"[UI] Guild Cursor: {item_name} (Idx: {self.cursor_idx})")
                        play_sfx(SOUND_CURSOR_MOVE)
                elif event.key == KEY_MOVE_DOWN:
                    if self.items:
                        if self.cursor_idx < len(self.items) - 1:
                            self.cursor_idx += 1
                        else:
                            self.cursor_idx = 0
                        item = self.items[self.cursor_idx]
                        item_name = item[2] if len(item) > 2 else (item[1].get('title', 'Unknown') if isinstance(item[1], dict) else 'Unknown')
                        if item[0] in ("cancel", "back"): item_name = Text.UI.QUIT
                        print(f"[UI] Guild Cursor: {item_name} (Idx: {self.cursor_idx})")
                        play_sfx(SOUND_CURSOR_MOVE)
                elif event.key == KEY_CANCEL:
                    print(f"[UI] Guild Button Pressed: CANCEL (Mode: {self.mode})")
                    play_sfx(SOUND_CANCEL)
                    if self.mode == "MENU":
                        self.is_active = False
                        player.outbreak_bonus_active = False
                    else:
                        self.mode = "MENU"
                        self._skip_auto_report = True
                        self.cursor_idx = 0
                        self.setup(player, self.dungeon_ref)
                elif event.key == KEY_CONFIRM:
                    if 0 <= self.cursor_idx < len(self.items):
                        item = self.items[self.cursor_idx]
                        if self.mode == "AUTO_REPORT":
                            self.mode = "MENU"
                            self._skip_auto_report = True
                            self.setup(player, self.dungeon_ref)
                            return

                        title = item[2] if len(item) > 2 else (item[1].get('title', 'Unknown') if isinstance(item[1], dict) else 'Unknown')
                        print(f"[GUILD] Selection: {title} (Status: {item[0]})")
                        if item[0] in ("cancel", "back"):
                            play_sfx(SOUND_CANCEL)
                        else:
                            play_sfx(SOUND_SELECT)
                        self.execute_quest(player, dialog, confirm_dialog)

    def execute_quest(self, player, dialog, confirm_dialog):
        item = self.items[self.cursor_idx]
        status = item[0]

        if status == "cancel":
            self.is_active = False
            player.outbreak_bonus_active = False
            return
        if status == "back":
            self.mode = "MENU"
            self.cursor_idx = 0
            self.setup(player, self.dungeon_ref)
            return
        if status == "info_rank":
            dialog.text = item[3]
            dialog.is_active = True
            return
        if status == "mode":
            self.mode = item[1]
            if self.mode == "SAVE":
                print("[GUILD] Manual save triggered.")
                player.save_to_file()
                dialog.text = "これまでの冒険を記録しました！"
                dialog.is_active = True
                self.mode = "MENU"

            self.cursor_idx = 0
            self.setup(player, self.dungeon_ref)
            return

        q = item[1]
        if status == "available":
            if len(player.active_quests) >= 1:
                dialog.text = Text.NPC.GUILD_LIMIT
                dialog.is_active = True
                return

            def on_accept():
                player.accept_quest(q)
                if q in self.dungeon_ref.guild_system.available_quests:
                    self.dungeon_ref.guild_system.available_quests.remove(q)
                elif q in self.dungeon_ref.guild_system.fixed_quests:
                    self.dungeon_ref.guild_system.fixed_quests.remove(q)

                from systems.sound_handler import sound_manager
                from constants import SOUND_SELECT
                sound_manager.play_sfx(SOUND_SELECT)

                dialog.text = Text.NPC.GUILD_ACCEPT_DONE
                dialog.is_active = True
                self.setup(player, self.dungeon_ref)

            confirm_dialog.text = Text.NPC.GUILD_ACCEPT_CONFIRM.format(title=q['title'])
            confirm_dialog.on_yes = on_accept
            confirm_dialog.is_active = True
        elif status == "active":
            if q.get("type") == "delivery":
                t_name = q.get('target_name') or q.get('target_key')
                confirm_dialog.text = Text.UI.GUILD_REPORT_CONFIRM.format(name=t_name)
            else:
                confirm_dialog.text = Text.UI.GUILD_REPORT_CONFIRM_GENERIC

            def on_report_yes():
                self._report_quest(player, q, dialog)

            confirm_dialog.on_yes = on_report_yes
            confirm_dialog.is_active = True
        elif status == "active_to_abandon":
            self._confirm_abandon(player, q, dialog, confirm_dialog)

    def _report_quest(self, player, q, dialog):
        success = False
        if q["type"] == "hunt":
            if player.quest_tokens.get(q["target_key"], 0) >= q["amount"]:
                player.quest_tokens[q["target_key"]] -= q["amount"]; success = True
        elif q["type"] == "delivery":
            if player.is_quest_reportable(q):
                player.remove_item_by_key(q["target_key"], q["amount"])
                success = True

        if success:
            self._play_placeholder_complete_sound()

            if q.get("is_rank_up"):
                player.guild_rank = q["next_rank"]

                def on_done():
                    dialog.text = f"依頼達成ですね \n{player.guild_rank}ランクに昇格です！おめでとうございます！\n\nランクアップのお祝いとして、\n好きなアイテムを1つ差し上げます！"
                    dialog.is_active = True
                    if hasattr(self, "ore_gift_dialog") and self.ore_gift_dialog:
                        self.ore_gift_dialog.setup(player, dialog)
                        self.ore_gift_dialog.is_active = True

                if hasattr(self, "cutscene_manager") and self.cutscene_manager:
                    self.cutscene_manager.start_rank_up(callback=on_done)
                else:
                    on_done()

            is_ending_quest = q.get("ending", False)
            if not is_ending_quest and q.get("id"):
                from constants import FIXED_QUEST_DATA
                for fq in FIXED_QUEST_DATA:
                    if fq.get("id") == q.get("id") and fq.get("ending"):
                        is_ending_quest = True
                        break

            if is_ending_quest:
                from systems.game_state import game_state
                game_state["current_scene"] = "ending"
                game_state["ending_index"] = 0
                game_state["ending_timer"] = 0
                game_state["ending_alpha"] = 0
                self.is_active = False
                return

            else:
                reward_gold, gp_reward = self._calc_reward(player, q)
                player.coin += reward_gold
                report_msg = q.get("report_message") or self._get_fixed_quest_report_message(q)
                dialog.text = report_msg if report_msg else "見事に依頼を達成しましたね！\nおめでとうございます！"
                player.guild_point += gp_reward
                if q.get("id"): player.completed_fixed_quests.append(q["id"])
                dialog.is_active = True

            player.shop_bonus_refresh = True
            self.mode = "AUTO_REPORT"
            self.items = [("auto_report", q)]
            player.active_quests.remove(q)
            print(f"[GUILD] Quest '{q.get('title')}' completed. Auto-saving...")
            player.save_to_file()
        else:
            dialog.text = Text.UI.GUILD_QUEST_UNMET
            dialog.is_active = True

    def _get_fixed_quest_report_message(self, q):
        if not q.get("id"):
            return None
        from constants import FIXED_QUEST_DATA
        for fq in FIXED_QUEST_DATA:
            if fq.get("id") == q.get("id"):
                return fq.get("report_message")
        return None

    def _play_placeholder_complete_sound(self):
        try:
            from systems.audio_manager import play_sfx
            from constants import SOUND_QUEST_COMPLETE
            play_sfx(SOUND_QUEST_COMPLETE)
        except Exception as e:
            print(f"[GUILD] Sound playback failed: {e}")

    def _confirm_abandon(self, player, q, dialog, confirm_dialog):
        penalty = q.get("reward_gold", 0) // 2
        gp_penalty = q.get("reward_gp", 0) // 2
        def on_confirm():
            if player.coin >= penalty:
                player.coin -= penalty
                player.guild_point = max(0, player.guild_point - gp_penalty)
                player.remove_quest(q)
                dialog.text = Text.UI.GUILD_ABANDON_DONE.format(penalty=penalty, gp_penalty=gp_penalty)
                self.setup(player, self.dungeon_ref)
            else:
                dialog.text = Text.UI.GUILD_ABANDON_NO_COIN.format(penalty=penalty)
            dialog.is_active = True

        msg = Text.UI.GUILD_ABANDON_CONFIRM.format(penalty=penalty, gp_penalty=gp_penalty)
        confirm_dialog.text = msg
        confirm_dialog.on_yes = on_confirm
        confirm_dialog.is_active = True

    def draw(self, screen, player):
        if not self.is_active: return

        if self.mode == "AUTO_REPORT" and self.items:
            draw_dialog_frame(screen, self.x + 50, self.y + 50, self.width - 100, self.height - 100, alpha=250)
            q = self.items[0][1]

            title_text = font_medium.render(Text.UI.GUILD_REPORT_CONGRATS, True, (255, 215, 0))
            screen.blit(title_text, (self.x + self.width // 2 - title_text.get_width() // 2, self.y + 100))

            q_name = self.font.render(q['title'], True, (255, 255, 255))
            screen.blit(q_name, (self.x + self.width // 2 - q_name.get_width() // 2, self.y + 160))

            if q.get("is_rank_up"):
                reward_str = Text.UI.GUILD_REPORT_RANK_UP.format(rank=q['next_rank'])
            else:
                _rg, _gp = self._calc_reward(player, q)
                reward_str = Text.UI.GUILD_REPORT_REWARD.format(gold=_rg, gp=_gp)
            reward_text = self.font.render(reward_str, True, (180, 255, 180))
            screen.blit(reward_text, (self.x + self.width // 2 - reward_text.get_width() // 2, self.y + 220))

            guide = self.font.render(Text.UI.GUILD_REPORT_GUIDE, True, (200, 200, 200))
            screen.blit(guide, (self.x + self.width // 2 - guide.get_width() // 2, self.y + self.height - 130))
            return

        draw_dialog_frame(screen, self.x, self.y, self.width, self.height, alpha=240)

        separator_x = self.x + self.width // 2
        pygame.draw.line(screen, (80, 100, 120), (separator_x, self.y + 40), (separator_x, self.y + self.height - 40), 2)

        title_str = Text.UI.GUILD_QUEST_LIST_HEADER
        title = font_small_bold.render(title_str, True, (255, 200, 100))
        screen.blit(title, (self.x + 30, self.y + 20))

        has_content = any(item[0] not in ("back", "cancel") for item in self.items)
        if not has_content:
            msg_str = Text.UI.GUILD_LIST_EMPTY
            if self.mode == "REPORT": msg_str = "報告できる依頼なし"
            msg = self.font.render(msg_str, True, (150, 150, 150))
            screen.blit(msg, (self.x + 50, self.y + 100))

        if self.items:
            start = max(0, self.cursor_idx - self.view_size // 2)
            if start + self.view_size > len(self.items):
                start = max(0, len(self.items) - self.view_size)

            list_start_y = self.y + 80
            max_list_w = self.width // 2 - 100
            for i in range(start, min(start + self.view_size, len(self.items))):
                item = self.items[i]
                status = item[0]
                y_pos = list_start_y + (i - start) * self.row_height

                color = (255, 255, 255)
                if i == self.cursor_idx:
                    color = (255, 255, 100)
                    pygame.draw.rect(screen, (60, 70, 90), (self.x + 20, y_pos - 5, self.width // 2 - 40, self.row_height), border_radius=5)
                    cursor = self.font.render(">", True, color)
                    screen.blit(cursor, (self.x + 35, y_pos))

                if status in ("mode", "info_rank"):
                    display_name = item[2]
                elif status in ("cancel", "back"):
                    display_name = Text.UI.QUIT
                else:
                    q = item[1]
                    if status == "active": color = (180, 255, 180) if i != self.cursor_idx else (255, 255, 100)
                    raw_title = q['title'].replace("【テスト】", "")
                    display_name = raw_title.strip()

                if self.font.size(display_name)[0] > max_list_w:
                    while self.font.size(display_name + "...")[0] > max_list_w and len(display_name) > 0:
                        display_name = display_name[:-1]
                    display_name += "..."

                name_text = self.font.render(display_name, True, color)
                screen.blit(name_text, (self.x + 65, y_pos))

            if len(self.items) > self.view_size:
                indicator_x = separator_x - 30
                if start > 0:
                    pygame.draw.polygon(screen, (200, 200, 200), [(indicator_x, self.y + 70), (indicator_x - 8, self.y + 80), (indicator_x + 8, self.y + 80)])
                if start + self.view_size < len(self.items):
                    pygame.draw.polygon(screen, (200, 200, 200), [(indicator_x, self.y + self.height - 70), (indicator_x - 8, self.y + self.height - 80), (indicator_x + 8, self.y + self.height - 80)])

        desc_x = separator_x + 30
        desc_y = self.y + 80
        desc_width = self.width // 2 - 60

        selected_item = self.items[self.cursor_idx] if self.items else None
        if selected_item:
            status = selected_item[0]
            desc_text = ""
            if status == "mode":
                mode_id = selected_item[1]
                menu_descs = {
                    "REPORT": "完了した依頼の報告を行い、\n報酬を受け取ります",
                    "ACCEPT_DAILY": "階層に応じた日常依頼を受注します \n(お小遣い稼ぎに適したランダムな内容です)",
                    "ACCEPT_RANKUP": "次のランクへ昇格するための試験を受けます \n(ストーリーが進行する重要な依頼です)",
                    "ACCEPT_FIXED": "特定の条件で発生する依頼を確認します \n(ボス戦や重要なイベントが発生します)",
                    "ABANDON": "現在受けている依頼を中止します \n※違約金とGPの減少が発生します"
                }
                desc_text = menu_descs.get(mode_id, Text.UI.STATUS_MENU_HINT)
            elif status == "info_rank":
                desc_text = selected_item[3]
            elif status in ("cancel", "back"):
                desc_text = "前の画面に戻ります"
            else:
                q = selected_item[1]
                desc_text = ""
                if q.get("requester"):
                    desc_text += f"【依頼主】 {q.get('requester')}\n\n"
                else:
                    desc_text += "\n"
                if q.get("description"):
                    desc_text += f"{q.get('description')}\n\n"

                t = q.get("type", "")
                target = q.get("target_name")
                if not target:
                    key = q.get("target_key")
                    if t == "hunt":
                        from constants import ENEMY_DATA
                        target = ENEMY_DATA.get(key, {}).get("name", "???")
                    elif t == "delivery":
                        from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, CONSUMABLE_DATA, STAVE_DATA
                        for cat in [WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, CONSUMABLE_DATA, STAVE_DATA]:
                            if key in cat:
                                target = cat[key].get("name", "???")
                                break
                    if not target: target = "???"

                amount = q.get("amount", 0)
                if t == "hunt":
                    key = q.get("target_key")
                    from constants import ENEMY_DATA
                    is_static = ENEMY_DATA.get(key, {}).get("is_static", False)
                    unit = "個" if is_static else "体"
                    verb = "破壊" if is_static else "討伐"
                    desc_text += f"【内容】\n{target} を {amount} {unit}{verb}する"
                elif t == "delivery":
                    desc_text += f"【内容】\n{target} を {amount} 個納品する"

                reward_gold, reward_gp = self._calc_reward(player, q)
                desc_text += f"\n\n【報酬】\n{reward_gold} G / {reward_gp} GP"

            draw_text_wrapped(screen, self.font, desc_text, desc_x, desc_y, desc_width, color=(220, 230, 240))


class GuildGuideDialog(BaseListDialog):
    """ギルド職員（案内）によるギルドシステム説明用ダイアログ"""
    STATE_KEY = "guild_guide_active"

    def __init__(self, screen_width, screen_height):
        super().__init__(screen_width, screen_height)
        self.row_height = 36

    def setup_options(self, player):
        from systems.guild import GuildSystem
        guild = GuildSystem()

        next_rank_data = guild.get_next_rank_data(player.guild_rank)
        if next_rank_data:
            needed_gp = next_rank_data["required_gp"] - player.guild_point
            if needed_gp > 0:
                rank_info_desc = f"現在のランクは {player.guild_rank} です \n次の{next_rank_data['rank']}ランクになるには、あと {needed_gp} GP 必要です \n(現在のGP: {player.guild_point} / 目標: {next_rank_data['required_gp']} GP)"
            else:
                rank_info_desc = f"現在のランクは {player.guild_rank} です \n次の{next_rank_data['rank']}ランクへの昇格基準を満たしています！\n(ギルドの受付で昇級試験を受けられます)"
        else:
            rank_info_desc = f"現在のランクは {player.guild_rank} です あなたは最高ランクに達しています！"

        self.items = [
            {"key": "your_rank", "name": "あなたのランク", "desc": rank_info_desc},
            {"key": "guild_point", "name": "ギルドポイント", "desc": "【ギルドポイント(GP)とは】\nクエストを達成すると貰えるポイントよ \nランクを上げる条件になるほか、神官様に死の呪いを解いてもらう際にも必要になるわ"},
            {"key": "adventure_rank", "name": "冒険者ランク", "desc": "【冒険者ランク】\nランクは -（未加入）から始まり、F, E, D, C, B, A, S, SS までの9段階あるわ \nランクが上がると、より難易度と報酬の高い依頼を受けられるようになるのよ"},
            {"key": "floor_limit", "name": "到達可能階層", "desc": "【ランク制限】\nランクに応じて進める限界階層が決まっているわ \n- : B0F(村のみ)\nF : B11F まで\nE : B21F まで\nD : B30F まで\nC : B35F まで\nB : B55F まで\nそれ以上のランクになれば、さらに深くまで進めるようになるわ！"},
            {"key": "promotion_exam", "name": "昇級試験", "desc": "【昇級試験】\nランクごとに必要なGPが溜まると、ギルドで試験を受けられるわ \n試験クエストを受けて、そのランクのボスが落とす『冒険者の証』を回収して報告すればランクアップよ！"},
            {"key": "quit", "name": "閉じる", "desc": "説明を終わります"}
        ]

    def get_title(self):
        return "ギルド案内"

    def get_item_label(self, item, idx):
        return item["name"]

    def get_detail_lines(self, player):
        if not self.items or self.cursor_idx >= len(self.items): return []
        item = self.items[self.cursor_idx]
        return item["desc"].split("\n")

    def handle_input(self, events, player):
        if not self.is_active: return None
        from systems.audio_manager import play_sfx
        from constants import SOUND_SELECT, SOUND_CANCEL

        res = self._navigate(events)
        if res == "cancel":
            play_sfx(SOUND_CANCEL)
            self.is_active = False
            return None
        elif res == "confirm":
            selected = self.items[self.cursor_idx]
            if selected["key"] == "quit":
                play_sfx(SOUND_CANCEL)
                self.is_active = False
                return None
            else:
                play_sfx(SOUND_SELECT)
                dialog = game_state.get("ui_elements", {}).get("dialog")
                if dialog:
                    dialog.text = selected["desc"]
                    dialog.is_active = True
                self.is_active = False
                return None
