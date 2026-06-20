import pygame
from systems.game_state import game_state
from systems.resources import (
    font_small, font_small_bold, font_medium, font_large,
    font_dialog, font_menu, font_hud
)
from constants import (
    KEY_MOVE_UP, KEY_MOVE_DOWN, KEY_MOVE_LEFT, KEY_MOVE_RIGHT,
    KEY_CONFIRM, KEY_CANCEL, UI_SETTINGS
)
from wordings import Text
from systems.ui.ui_base import (
    get_standard_upper_layout, draw_dialog_frame, draw_text_wrapped,
    EQUIP_STAT_LABEL_MAP, EQUIP_MAGIC_LABEL_MAP, format_stat_value
)


class Dialog:
    def __init__(self, screen_width, screen_height):
        # 画面サイズに合わせて、下部に長方形のダイアログを自動配置する
        self.width = screen_width - 200
        self.height = 220
        self.x = 100
        self.y = screen_height - self.height - 50
        
        self._text = ""
        self.pages = []
        self.page_idx = 0
        # ui.yml の専用フォントを使用
        self.font = font_dialog
        self.auto_close_timer = 0
        self.scroll_y = 0 # 現在の表示開始行
        self.max_scroll = 0
        self.just_opened_timer = 0 # 開いた直後の入力を無視するためのタイマー

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value
        # 直接テキストが代入された場合、それを唯一のページとする（ページ送り処理中を除く）
        if not getattr(self, "_in_page_flip", False):
            self.pages = [value]
            self.page_idx = 0

    def set_pages(self, pages_list):
        self.pages = list(pages_list) if pages_list else [""]
        self.page_idx = 0
        self._in_page_flip = True
        self.text = self.pages[0]
        self._in_page_flip = False
        self.is_active = True

    # is_active（開閉状態）は独立した変数ではなく、中央の game_state を使うように変更！
    @property
    def is_active(self):
        return game_state["dialog_active"]

    @is_active.setter
    def is_active(self, value):
        game_state["dialog_active"] = value
        if value:
            # メッセージの最初の1行だけログに出す（長い場合を考慮）
            msg = self.text.split('\n')[0][:30]
            print(f"[UI] Open Dialog (Msg: {msg}...)")
        # 閉じる時（value=False）のみテキストと状態をクリアするように修正
        if not value:
            print(f"[UI] Close Dialog")
            self._text = ""
            self.pages = []
            self.page_idx = 0
            self.auto_close_timer = 0
            self.scroll_y = 0
            game_state["dialog_modal"] = True # デフォルトに戻す
            game_state["dialog_just_closed"] = True # 誤爆防止
            if getattr(self, "on_close_callback", None):
                cb = self.on_close_callback
                self.on_close_callback = None
                cb()
        else:
            # 開いた瞬間にフラグを立てる (2フレーム分無視)
            self.just_opened_timer = 2

    def update(self):
        """毎フレーム呼ばれ、オートクローズタイマーのカウントダウンなどを行う"""
        if self.just_opened_timer > 0:
            self.just_opened_timer -= 1

        if self.is_active and self.auto_close_timer > 0:
            self.auto_close_timer -= 1
            if self.auto_close_timer <= 0:
                self.is_active = False

    def handle_events(self, events):
        """操作: スペース/Enterで閉じる/次のページへ、上下キーでスクロール"""
        if not self.is_active or self.just_opened_timer > 0: return
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, KEY_CONFIRM):
                    # 次のページがあれば進む
                    if self.pages and self.page_idx < len(self.pages) - 1:
                        self.page_idx += 1
                        self._in_page_flip = True
                        self.text = self.pages[self.page_idx]
                        self._in_page_flip = False
                        self.scroll_y = 0
                        self.just_opened_timer = 2 # 誤連打防止のための短いウェイト
                        print(f"[UI] Dialog page advanced to: {self.page_idx + 1}/{len(self.pages)}")
                    else:
                        self.is_active = False
                elif event.key == KEY_MOVE_UP:
                    self.scroll_y = max(0, self.scroll_y - 1)
                elif event.key == KEY_MOVE_DOWN:
                    self.scroll_y = min(self.max_scroll, self.scroll_y + 1)

    def draw(self, screen):
        if not self.is_active:
            return

        cfg = UI_SETTINGS.get("message_window", {})
        bg_color = cfg.get("bg_color", [0, 0, 0, 180])
        border_color = cfg.get("border_color", [255, 255, 255])
        radius = cfg.get("corner_radius", 0)
        
        # 1. 背景
        s = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.rect(s, bg_color, (0, 0, self.width, self.height), border_radius=radius)
        screen.blit(s, (self.x, self.y))
        
        # 2. 枠線 (二重線)
        # 外枠
        pygame.draw.rect(screen, border_color, (self.x, self.y, self.width, self.height), 4, border_radius=radius)
        # 内枠
        inset = 8
        inner_rect = (self.x + inset, self.y + inset, self.width - inset * 2, self.height - inset * 2)
        pygame.draw.rect(screen, border_color, inner_rect, 1, border_radius=max(0, radius - inset))
        
        # 3. テキストのラッピングとスクロール描画
        line_height = self.font.size("あ")[1] + 8
        padding_x, padding_y = 40, 35
        draw_width = self.width - padding_x * 2
        draw_height = self.height - padding_y * 2
        
        # テキストを改行位置で分割し、さらに幅に合わせてラッピングする
        all_lines = []
        for paragraph in self.text.split('\n'):
            current_line = ""
            for char in paragraph:
                test_line = current_line + char
                if self.font.size(test_line)[0] > draw_width:
                    all_lines.append(current_line)
                    current_line = char
                else:
                    current_line = test_line
            all_lines.append(current_line)
        
        visible_count = draw_height // line_height
        self.max_scroll = max(0, len(all_lines) - visible_count)
        self.scroll_y = max(0, min(self.scroll_y, self.max_scroll))
        
        # 表示範囲の行を描画
        for i in range(visible_count):
            idx = i + self.scroll_y
            if idx < len(all_lines):
                line_text = all_lines[idx]
                text_color = (255, 255, 255)
                if "<Y>" in line_text:
                    line_text = line_text.replace("<Y>", "").replace("</Y>", "")
                    text_color = (255, 255, 0)
                
                line_surf = self.font.render(line_text, True, text_color)
                screen.blit(line_surf, (self.x + padding_x, self.y + padding_y + i * line_height))
        
        # 4. スクロールインジケーター（▲▼）
        if self.scroll_y > 0:
            up_arrow = font_small.render("▲", True, (255, 255, 100))
            screen.blit(up_arrow, (self.x + self.width - 30, self.y + 10))
        if self.scroll_y < self.max_scroll:
            down_arrow = font_small.render("▼", True, (255, 255, 100))
            screen.blit(down_arrow, (self.x + self.width - 30, self.y + self.height - 30))

        # 5. ページ送りインジケーター（次のページがある場合）
        if self.pages and self.page_idx < len(self.pages) - 1:
            # 右下に点滅する ▼ を表示
            import time
            blink = int(time.time() * 2) % 2 == 0
            if blink:
                next_indicator = font_small.render("▼", True, (200, 255, 200))
                screen.blit(next_indicator, (self.x + self.width - 55, self.y + self.height - 30))

class CutsceneManager:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.is_active = False
        self.timer = 0
        self.type = None # "rank_up", "inn_rest"
        self.phase = 0
        self.alpha = 0
        self.callback = None
        self.dungeon_ref = None
    
    def start_rank_up(self, callback=None):
        self.is_active = True
        self.type = "rank_up"
        self.timer = 0
        self.phase = 0
        self.callback = callback
        from systems.audio_manager import play_sfx
        from constants import SOUND_RANK_UP
        play_sfx(SOUND_RANK_UP)

    def start_inn_rest(self, callback=None):
        self.is_active = True
        self.type = "inn_rest"
        self.timer = 0
        self.phase = 0
        self.alpha = 0
        self.callback = callback
        from systems.audio_manager import play_sfx
        from constants import SOUND_INN_REST
        play_sfx(SOUND_INN_REST)

    def start_blacksmith(self, callback=None):
        self.is_active = True
        self.type = "blacksmith"
        self.timer = 0
        self.phase = 0
        self.callback = callback

    def update(self):
        if not self.is_active: return
        self.timer += 1
        
        if self.type == "rank_up":
            # 効果音の再生時間程度待つ (約120フレーム = 2秒)
            if self.timer > 120:
                self.is_active = False
                if self.callback: self.callback()
                
        elif self.type == "inn_rest":
            if self.phase == 0:
                # 暗転 (フェードアウト)
                self.alpha += 5
                if self.alpha >= 255:
                    self.alpha = 255
                    self.phase = 1
                    self.timer = 0
            elif self.phase == 1:
                # 暗転状態で待機
                if self.timer > 60:
                    self.phase = 2
                    self.timer = 0
            elif self.phase == 2:
                # 明転 (フェードイン)
                self.alpha -= 5
                if self.alpha <= 0:
                    self.alpha = 0
                    self.is_active = False
                    if self.callback: self.callback()
        
        elif self.type == "blacksmith":
            from systems.audio_manager import play_sfx
            from constants import SOUND_HAMMER, SOUND_BLACKSMITH_FINISH
            # 20フレームごとに3回叩く
            if self.timer == 10: play_sfx(SOUND_HAMMER)
            if self.timer == 30: play_sfx(SOUND_HAMMER)
            if self.timer == 50: play_sfx(SOUND_HAMMER)
            
            if self.timer == 80:
                play_sfx(SOUND_BLACKSMITH_FINISH)
            
            if self.timer > 110:
                self.is_active = False
                if self.callback: self.callback()

    def draw(self, screen):
        if not self.is_active: return
        
        if self.type == "inn_rest":
            s = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            s.fill((0, 0, 0, self.alpha))
            screen.blit(s, (0, 0))
        elif self.type == "blacksmith":
            # 画面中央に「鍛冶中...」の文字を出す
            s = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            s.fill((0, 0, 0, 100)) # 薄暗くする
            screen.blit(s, (0, 0))
            txt = font_large.render("鍛冶中...", True, (255, 255, 255))
            screen.blit(txt, (self.screen_width // 2 - txt.get_width() // 2, self.screen_height // 2 - 50))

class ConfirmDialog:
    def __init__(self, screen_width, screen_height):
        self.x, self.y, self.width, self.height = get_standard_upper_layout(screen_width, screen_height)
        
        self.text = ""
        self.font = font_medium
        self.cursor_idx = 0  # 0: Yes, 1: No
        self.on_yes = None   # Yesが選ばれた時に実行する処理（関数）
        self.on_no = None    # Noが選ばれた時に実行する処理（関数）

    @property
    def is_active(self):
        return game_state["confirm_active"]

    @is_active.setter
    def is_active(self, value):
        game_state["confirm_active"] = value
        if value:
            self.cursor_idx = 0 # 開くたびにデフォルトでYesにカーソルを合わせる
            print(f"[DEBUG-CONFIRM] confirm_dialog OPENED (text={self.text[:30] if self.text else 'EMPTY'})")
        else:
            game_state["dialog_just_closed"] = True # 閉じた瞬間の誤爆防止
            print(f"[DEBUG-CONFIRM] confirm_dialog CLOSED")

    def handle_events(self, events):
        if not self.is_active: return
        for event in events:
            if event.type == pygame.KEYDOWN:
                # 矢印キーでYes/Noカーソルを移動
                from systems.audio_manager import play_sfx
                from constants import SOUND_CURSOR_MOVE, SOUND_SELECT
                if event.key in (KEY_MOVE_LEFT, KEY_MOVE_UP):
                    if self.cursor_idx != 0:
                        play_sfx(SOUND_CURSOR_MOVE)
                        self.cursor_idx = 0
                elif event.key in (KEY_MOVE_RIGHT, KEY_MOVE_DOWN):
                    if self.cursor_idx != 1:
                        play_sfx(SOUND_CURSOR_MOVE)
                        self.cursor_idx = 1
                # Aボタンで決定
                elif event.key == KEY_CONFIRM:
                    from constants import SOUND_CANCEL
                    selection = "YES" if self.cursor_idx == 0 else "NO"
                    print(f"[CONFIRM] Selection: {selection} (Msg: {self.text.split(chr(10))[0][:20]}...)")
                    
                    if self.cursor_idx == 0:
                        play_sfx(SOUND_SELECT)
                    else:
                        play_sfx(SOUND_CANCEL)
                    self.is_active = False # 決定したらウィンドウを閉じる
                    if self.cursor_idx == 0 and self.on_yes:
                        self.on_yes()
                    elif self.cursor_idx == 1 and self.on_no:
                        self.on_no()

    def draw(self, screen):
        if not self.is_active: return
        draw_dialog_frame(screen, self.x, self.y, self.width, self.height)

        # メッセージをウィンドウ内の上下左右中央に配置
        draw_text_wrapped(
            screen, self.font, self.text, 
            self.x + 40, self.y + 40, 
            self.width - 80, box_height=self.height - 130, # 下部のボタン分を空ける
            align_h='center', align_v='center'
        )

        # 選択肢の描画（中央付近にバランス良く配置）
        yes_text = self.font.render(Text.UI.YES, True, (255, 255, 255))
        no_text = self.font.render(Text.UI.NO, True, (255, 255, 255))
        
        # ウィンドウ幅に合わせて中央に寄せる
        center_x = self.x + self.width // 2
        yes_x, yes_y = center_x - 120, self.y + self.height - 80
        no_x, no_y = center_x + 60, self.y + self.height - 80
        
        screen.blit(yes_text, (yes_x, yes_y))
        screen.blit(no_text, (no_x, no_y))

        # カーソル「＞」を描画
        cursor_x = yes_x - 40 if self.cursor_idx == 0 else no_x - 40
        cursor_text = self.font.render(">", True, (255, 255, 255))
        screen.blit(cursor_text, (cursor_x, yes_y))

class ItemActionDialog:
    """アイテム選択後の「使う・捨てる」メニュー"""
    def __init__(self, screen_width, screen_height):
        self.x, self.y, self.width, self.height = get_standard_upper_layout(screen_width, screen_height)
        self.font = font_medium
        self.cursor_idx = 0 # 0: 使う, 1: 捨てる
        self.selected_data = None # (type, iid_or_key) 
        self.on_use = None
        self.on_discard = None

    def setup(self, player, dialog, inventory_dialog, game_state):
        """アクションメニューのコールバックを設定する"""
        from systems.item_handler import make_discard_item_callback, make_unequip_item_callback
        self.player = player
        self.on_use = inventory_dialog.on_select
        self.on_discard = make_discard_item_callback(player, dialog, inventory_dialog, game_state)
        self.on_unequip = make_unequip_item_callback(player, dialog, inventory_dialog, game_state)

    def setup_for_item(self, data, on_use, on_discard, on_unequip):
        """[NEW] 呼び出し元のダイアログに合わせてコールバックを差し替える"""
        self.selected_data = data
        self.on_use = on_use
        self.on_discard = on_discard
        self.on_unequip = on_unequip


    @property
    def is_active(self): return game_state["item_action_active"]
    @is_active.setter
    def is_active(self, v):
        game_state["item_action_active"] = v
        if v:
            print(f"[UI] Open ItemActionDialog (Target: {self.selected_data})")
            self.cursor_idx = 0
        else:
            print(f"[UI] Close ItemActionDialog")
            game_state["dialog_just_closed"] = True

    def handle_events(self, events):
        if not self.is_active: return
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (KEY_MOVE_UP, KEY_MOVE_LEFT): 
                    self.cursor_idx = (self.cursor_idx - 1) % 3
                    from systems.audio_manager import play_sfx
                    from constants import SOUND_CURSOR_MOVE
                    play_sfx(SOUND_CURSOR_MOVE)
                    print(f"[UI] ItemAction Cursor: {self.cursor_idx}")
                elif event.key in (KEY_MOVE_DOWN, KEY_MOVE_RIGHT): 
                    self.cursor_idx = (self.cursor_idx + 1) % 3
                    from systems.audio_manager import play_sfx
                    from constants import SOUND_CURSOR_MOVE
                    play_sfx(SOUND_CURSOR_MOVE)
                    print(f"[UI] ItemAction Cursor: {self.cursor_idx}")
                elif event.key == KEY_CANCEL:
                    print(f"[UI] ItemAction Button Pressed: CANCEL")
                    self.is_active = False
                elif event.key == KEY_CONFIRM:
                    print(f"[UI] ItemAction Button Pressed: CONFIRM (Idx: {self.cursor_idx})")
                    self.is_active = False
                    itype, iid_or_key = self.selected_data
                    
                    is_equipped = False
                    if itype == "weapon" and self.player.equipped_weapon == iid_or_key: is_equipped = True
                    elif itype == "armor" and self.player.equipped_armor == iid_or_key: is_equipped = True
                    elif itype == "shield" and getattr(self.player, "equipped_shield", None) == iid_or_key: is_equipped = True
                    elif itype == "accessory" and getattr(self.player, "equipped_accessory", None) == iid_or_key: is_equipped = True

                    if self.cursor_idx == 0:
                        if itype == "consumable":
                            from constants import CONSUMABLE_DATA
                            data = CONSUMABLE_DATA.get(iid_or_key, {})
                            effect = data.get("effect")
                            if not effect or effect == "material":
                                from systems.audio_manager import play_sfx
                                from constants import SOUND_CANCEL
                                play_sfx(SOUND_CANCEL)
                                self.is_active = True # 閉じない
                                return
                        
                        if is_equipped:
                            if self.on_unequip: self.on_unequip(itype, iid_or_key)
                        elif self.on_use:
                            self.on_use(itype, iid_or_key)
                    elif self.cursor_idx == 1 and self.on_discard:
                        self.on_discard(itype, iid_or_key)
                    elif self.cursor_idx == 2:
                        self.is_active = False

    def draw(self, screen):
        if not self.is_active: return
        draw_dialog_frame(screen, self.x, self.y, self.width, self.height, alpha=240)

        # 装備中かどうかの判定
        itype, iid_or_key = self.selected_data if self.selected_data else (None, None)
        is_equipped = False
        if itype == "weapon" and self.player.equipped_weapon == iid_or_key: is_equipped = True
        elif itype == "armor" and self.player.equipped_armor == iid_or_key: is_equipped = True
        elif itype == "shield" and getattr(self.player, "equipped_shield", None) == iid_or_key: is_equipped = True
        elif itype == "accessory" and getattr(self.player, "equipped_accessory", None) == iid_or_key: is_equipped = True

        # 選択肢を中央に配置
        is_unusable = False
        if itype == "consumable":
            from constants import CONSUMABLE_DATA
            data = CONSUMABLE_DATA.get(iid_or_key, {})
            effect = data.get("effect")
            if not effect or effect == "material":
                is_unusable = True
                
        if itype == "stave":
            first_opt = Text.UI.WAVE
        elif is_equipped:
            first_opt = Text.UI.UNEQUIP
        else:
            first_opt = Text.UI.USE_EQUIP
            
        options = [first_opt, Text.UI.DISCARD, Text.UI.QUIT]
        for i, opt in enumerate(options):
            color = (255, 255, 255)
            if i == 0 and is_unusable:
                color = (120, 120, 120)
                if i == self.cursor_idx:
                    cursor = self.font.render(">", True, color)
                    screen.blit(cursor, (self.x + self.width // 2 - 100, self.y + 60 + i * 50))
            else:
                if i == self.cursor_idx:
                    color = (255, 255, 100)
                    cursor = self.font.render(">", True, color)
                    screen.blit(cursor, (self.x + self.width // 2 - 100, self.y + 60 + i * 50))
            
            text = self.font.render(opt, True, color)
            screen.blit(text, (self.x + self.width // 2 - 60, self.y + 60 + i * 50))
