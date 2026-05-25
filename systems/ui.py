import pygame
import random
from systems.game_state import game_state
from systems.resources import (
    font_small, font_small_bold, font_medium, font_large,
    font_dialog, font_menu, font_hud
)
from constants import (
    KEY_MOVE_UP, KEY_MOVE_DOWN, KEY_MOVE_LEFT, KEY_MOVE_RIGHT,
    KEY_CONFIRM, KEY_CANCEL, KEY_INVENTORY, GAME_TITLE,
    UI_SETTINGS
)
import os
from wordings import Text

def draw_opening_scene(screen, image, alpha):
    """オープニング画像をフェードインしながら描画する"""
    if not image: return
    
    # 1. 画像の描画 (alpha適用)
    img_surf = image.copy()
    img_surf.set_alpha(alpha)
    
    # 画面中央に配置
    rect = img_surf.get_rect(center=(screen.get_width()//2, screen.get_height()//2))
    screen.blit(img_surf, rect)

def draw_title_screen(screen, background_img, selected_idx, has_save):
    """タイトル画面を描画する"""
    if background_img:
        screen.blit(background_img, (0, 0))
    else:
        screen.fill((20, 20, 40))
        
    # タイトルロゴ（テキスト）
    title_text = GAME_TITLE
    # ロゴに輝き効果（リッチ）
    logo_color = (255, 220, 100)
    draw_text_wrapped(screen, font_large, title_text, 0, 150, screen.get_width(), align_h='center', color=logo_color)
    
    # メニュー
    menu_items = [Text.UI.CONTINUE, Text.UI.NEW_GAME]
    start_y = 500
    
    for i, item in enumerate(menu_items):
        color = (255, 255, 255)
        if i == 0 and not has_save:
            color = (100, 100, 100) # Saveがない場合はContinueをグレーアウト
            
        if i == selected_idx:
            color = (255, 255, 100) # 選択中は黄色
            # 選択中のアニメーション（矢印）
            cursor_text = ">"
            draw_text_wrapped(screen, font_medium, cursor_text, screen.get_width()//2 - 150, start_y + i * 80, 50, color=color)
            
        draw_text_wrapped(screen, font_medium, item, 0, start_y + i * 80, screen.get_width(), align_h='center', color=color)

def show_loading_screen(screen, text=None):
    """
    重い処理（ダンジョン生成やセーブ）の前に呼び出して、
    画面全体を少し暗くし、中央に読み込み中表示を出す。
    """
    if text is None: text = Text.UI.NOW_LOADING
    
    sw, sh = screen.get_size()
    
    # 1. 画面全体を少し暗くするオーバーレイ
    overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))
    
    # 2. 中央のメッセージボックス
    box_w, box_h = 300, 100
    box_rect = pygame.Rect((sw - box_w) // 2, (sh - box_h) // 2, box_w, box_h)
    
    # 角丸のボックス
    pygame.draw.rect(screen, (30, 30, 50), box_rect, border_radius=10)
    # 二重線
    pygame.draw.rect(screen, (255, 255, 255), box_rect, 2, border_radius=10)
    inner_box = box_rect.inflate(-12, -12)
    pygame.draw.rect(screen, (255, 255, 255), inner_box, 1, border_radius=6)
    
    # テキスト描画
    draw_text_wrapped(screen, font_medium, text, box_rect.x, box_rect.y, box_w, box_h, align_h='center', align_v='center', color=(255, 255, 200))
    
    # 3. スピナー（静止画だが、呼び出し直後に一瞬見えるだけで安心感が出る）
    # 円形の装飾
    center_x, center_y = sw // 2, sh // 2 + 35
    pygame.draw.circle(screen, (255, 255, 100), (center_x, center_y), 5)
    
    # 画面を強制更新（これを行わないと、直後の重い処理中に画面に反映されない）
    pygame.display.flip()

def draw_text_wrapped(screen, font, text, x, y, max_width, box_height=None, color=(255, 255, 255), align_h='left', align_v='top', alpha=255):
    """指定されたボックス内でテキストを折り返し、アライメント（左・中央・右 / 上・中・下）を考慮して描画する"""
    if not text: return
    
    line_height = font.size("あ")[1] + 8
    lines = []
    current_line = ""
    
    # 段階1: 折り返し位置の計算
    for char in text:
        if char == '\n':
            lines.append(current_line)
            current_line = ""
            continue
            
        test_line = current_line + char
        if font.size(test_line)[0] > max_width:
            lines.append(current_line)
            current_line = char
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line)
    
    # 段階2: 垂直方向の開始位置決定
    total_text_height = len(lines) * line_height
    start_y = y
    if box_height and align_v == 'center':
        start_y = y + (box_height - total_text_height) // 2
    elif box_height and align_v == 'bottom':
        start_y = y + box_height - total_text_height
        
    # 段階3: 描画
    for i, line in enumerate(lines):
        line_surf = font.render(line, True, color)
        if alpha < 255:
            line_surf.set_alpha(alpha)
            
        line_w = line_surf.get_width()
        
        line_x = x
        if align_h == 'center':
            line_x = x + (max_width - line_w) // 2
        elif align_h == 'right':
            line_x = x + max_width - line_w
            
        screen.blit(line_surf, (line_x, start_y + i * line_height))

def get_standard_upper_layout(screen_width, screen_height):
    """メッセージウィンドウ以外のすべてのUIウィンドウで使用する標準レイアウトを計算する"""
    width = screen_width - 200
    x = 100
    # メッセージウィンドウ (Dialog.y) は screen_height - 220 - 50
    message_y = screen_height - 220 - 50
    y = 100 # 画面上端からの余白 (TopHUDを避ける)
    height = message_y - y - 10 # メッセージウィンドウとの隙間を10px空ける
    return x, y, width, height

def draw_dialog_frame(screen, x, y, width, height, alpha=None):
    """共通の透明背景と枠線を描画する（ui.yml の設定を反映）"""
    cfg = UI_SETTINGS.get("dialog", {})
    bg_color = list(cfg.get("bg_color", [0, 0, 0, 220]))
    if alpha is not None:
        bg_color[3] = alpha
    
    border_color = cfg.get("border_color", [255, 255, 255])
    border_w = cfg.get("border_width", 2)
    radius = cfg.get("corner_radius", 0)
    
    # 背景
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(s, bg_color, (0, 0, width, height), border_radius=radius)
    screen.blit(s, (x, y))
    
    # 枠線 (二重線)
    if border_w > 0:
        # 外枠
        pygame.draw.rect(screen, border_color, (x, y, width, height), border_w, border_radius=radius)
        # 内枠 (4px 内側に、細い線を描画)
        inset = 6
        if width > inset*2 and height > inset*2:
            inner_rect = (x + inset, y + inset, width - inset*2, height - inset*2)
            pygame.draw.rect(screen, border_color, inner_rect, 1, border_radius=max(0, radius - inset))

def show_dialog(dialog, text, modal=False, auto_close=None):
    """
    メッセージウィンドウにテキストを表示する。
    既に表示中の場合は改行して追記する。
    """
    if not dialog: return
    from constants import COMBAT_LOG_WAIT_FRAMES
    
    if dialog.is_active:
        # 重複表示を避けるため、最後の行と同じなら追記しない
        last_line = dialog.text.split("\n")[-1] if dialog.text else ""
        if last_line != text:
            dialog.text += "\n" + text
    else:
        dialog.text = text
        dialog.is_active = True
        
    from systems.game_state import game_state
    game_state["dialog_modal"] = modal
    dialog.auto_close_timer = auto_close if auto_close is not None else COMBAT_LOG_WAIT_FRAMES

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
        else:
            game_state["dialog_just_closed"] = True # 閉じた瞬間の誤爆防止

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
                    print(f"[CONFIRM] Selection: {selection} (Msg: {self.text.split('\n')[0][:20]}...)")
                    
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
                    elif itype == "lantern" and getattr(self.player, "equipped_lantern", None) == iid_or_key: is_equipped = True

                    if self.cursor_idx == 0:
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
        elif itype == "lantern" and getattr(self.player, "equipped_lantern", None) == iid_or_key: is_equipped = True

        # 選択肢を中央に配置
        if itype == "stave":
            first_opt = Text.UI.WAVE
        elif is_equipped:
            first_opt = Text.UI.UNEQUIP
        else:
            first_opt = Text.UI.USE_EQUIP
            
        options = [first_opt, Text.UI.DISCARD, Text.UI.QUIT]
        for i, opt in enumerate(options):
            color = (255, 255, 255)
            if i == self.cursor_idx:
                color = (255, 255, 100)
                cursor = self.font.render(">", True, color)
                screen.blit(cursor, (self.x + self.width // 2 - 100, self.y + 60 + i * 50))
            
            text = self.font.render(opt, True, color)
            screen.blit(text, (self.x + self.width // 2 - 60, self.y + 60 + i * 50))

class OreSelectionDialog:
    """鍛冶屋で装備選択後に「どの鉱石を使うか」を選ぶダイアログ"""
    def __init__(self, screen_width, screen_height):
        self.x, self.y, self.width, self.height = get_standard_upper_layout(screen_width, screen_height)
        self.font = font_medium
        self.cursor_idx = 0
        self.target_item_data = None # (type, iid) 強化対象
        self.available_ores = []     # (key, name, bonus)
        self.on_confirm = None       # callback(item_type, iid, ore_key)

    def setup(self, enhance_dialog, confirm_dialog=None, player=None, cutscene_manager=None):
        """強化実行のコールバックと確認ダイアログを設定する"""
        self.on_confirm = enhance_dialog.on_select
        self.confirm_dialog = confirm_dialog
        self.player_ref = player
        self.cutscene_manager = cutscene_manager


    @property
    def is_active(self): return game_state["ore_selection_active"]
    @is_active.setter
    def is_active(self, v):
        game_state["ore_selection_active"] = v
        if v:
            print(f"[UI] Open OreSelectionDialog")
            self.cursor_idx = 0
        else:
            print(f"[UI] Close OreSelectionDialog")
            game_state["dialog_just_closed"] = True

    def update_from_player(self, player):
        """インベントリから「鉱石系」を重複を除いてリストアップ"""
        from constants import CONSUMABLE_DATA
        ores = {} # key -> {name, bonus}
        for item in player.items:
            item_key = item["key"]
            data = CONSUMABLE_DATA.get(item_key, {})
            if data.get("effect") == "material":
                if item_key not in ores:
                    ores[item_key] = {
                        "name": data.get("name", item_key),
                        "bonus": data.get("enhance_bonus", 1)
                    }
        self.available_ores = [(k, v["name"], v["bonus"]) for k, v in ores.items()]
        # --- やめるボタンを追加 ---
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
                        if self.on_confirm and self.target_item_data:
                            item_type, iid = self.target_item_data
                            # confirm_dialog があればプレビューを表示してから実行
                            if getattr(self, "confirm_dialog", None) and getattr(self, "player_ref", None):
                                cd = self.confirm_dialog
                                player = self.player_ref
                                ore_bonus = self.available_ores[self.cursor_idx][2]
                                if item_type == "weapon": inv = player.weapon_inventory
                                elif item_type == "armor": inv = player.armor_inventory
                                else: inv = getattr(player, "shield_inventory", [])
                                inst = player._find_equip_inst(inv, iid)
                                if inst:
                                    if item_type == "weapon":
                                        stat_key = "attack_bonus"
                                        unit = ""
                                    elif item_type == "armor":
                                        stat_key = "defense_bonus"
                                        unit = ""
                                    else: # shield
                                        stat_key = "block_chance"
                                        unit = "%"
                                    
                                    before = inst.get_stat(stat_key, 0) + inst.get_enhance_bonus(stat_key)
                                    # 仮に enhance を進めて after を計算
                                    inst.enhance += ore_bonus
                                    after = inst.get_stat(stat_key, 0) + inst.get_enhance_bonus(stat_key)
                                    inst.enhance -= ore_bonus  # 戻す
                                    
                                    # 表示用に変換
                                    if unit == "%":
                                        display_before = before * 100
                                        display_after = after * 100
                                        stat_label = "ブロック率"
                                    else:
                                        display_before = before
                                        display_after = after
                                        stat_label = "能力ボーナス"
                                    from wordings import Text
                                    cd.text = Text.NPC.BLACKSMITH_ENHANCE_PREVIEW.format(
                                        name=inst.get_name(),
                                        label=stat_label,
                                        unit=unit,
                                        before=display_before, after=display_after,
                                        enhance=inst.enhance + ore_bonus,
                                        ore_bonus=ore_bonus
                                    )
                                    stored_type, stored_iid, stored_key = item_type, iid, ore_key
                                    def do_enhance():
                                        if getattr(self, "cutscene_manager", None):
                                            self.cutscene_manager.start_blacksmith(lambda: self.on_confirm(stored_type, stored_iid, stored_key))
                                        else:
                                            self.on_confirm(stored_type, stored_iid, stored_key)
                                    cd.on_yes = do_enhance
                                    cd.on_no = None
                                    cd.is_active = True
                                    return
                            self.on_confirm(item_type, iid, ore_key)

    def draw(self, screen):
        if not self.is_active: return
        draw_dialog_frame(screen, self.x, self.y, self.width, self.height, alpha=240)

        title = font_small.render(Text.UI.USE_WHICH_ORE, True, (255, 200, 100))
        # タイトルも中央に
        screen.blit(title, (self.x + (self.width - title.get_width()) // 2, self.y + 15))

        if not self.available_ores:
            msg = self.font.render(Text.UI.NO_ORE, True, (200, 100, 100))
            screen.blit(msg, (self.x + (self.width - msg.get_width()) // 2, self.y + 100))
            return

        for i, (key, name, bonus) in enumerate(self.available_ores):
            color = (255, 255, 255)
            if i == self.cursor_idx:
                color = (255, 255, 100)
                cursor = self.font.render(">", True, color)
                screen.blit(cursor, (self.x + self.width // 2 - 120, self.y + 70 + i * 40))
            
            
            if key == "cancel":
                text = self.font.render(name, True, color)
            else:
                text = self.font.render(f"{name} (+{bonus})", True, color)
            screen.blit(text, (self.x + self.width // 2 - 80, self.y + 70 + i * 40))

class StaveSelectionDialog:
    """どの杖の使用回数を回復するかを選ぶダイアログ"""
    def __init__(self, screen_width, screen_height):
        self.x, self.y, self.width, self.height = get_standard_upper_layout(screen_width, screen_height)
        self.font = font_medium
        self.cursor_idx = 0
        self.recharge_item_key = None # 使用した回復アイテムのキー
        self.available_staves = []     # StaveInstance リスト
        self.on_confirm = None       # callback(stave_inst, item_key)

    def setup(self, player, dialog):
        """杖の回復コールバックを設定する"""
        from systems.item_handler import make_recharge_callback
        self.on_confirm = make_recharge_callback(player, dialog, self)


    @property
    def is_active(self): return game_state["stave_selection_active"]
    @is_active.setter
    def is_active(self, v):
        game_state["stave_selection_active"] = v
        if v: self.cursor_idx = 0
        else: game_state["dialog_just_closed"] = True

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

class BaseListDialog:
    """NPCサービスダイアログの共通基底クラス。
    2カラムレイアウト（左リスト ＋ 右詳細パネル）と
    カーソルナビゲーションを提供する。
    """
    STATE_KEY = ""  # サブクラスで定義

    def __init__(self, screen_width, screen_height):
        self.x, self.y, self.width, self.height = get_standard_upper_layout(screen_width, screen_height)
        from systems.resources import font_small
        self.font = font_small
        self.row_height = 38
        self.view_size = 10
        self.cursor_idx = 0
        self.items = []
        self._back_dialog = None

    # --- is_active プロパティ ---
    @property
    def is_active(self): return game_state.get(self.STATE_KEY, False)
    @is_active.setter
    def is_active(self, v):
        game_state[self.STATE_KEY] = v
        if v:
            print(f"[UI] Open {self.__class__.__name__} ({self.get_title()})")
            self.cursor_idx = 0; self.on_activated()
        else:
            print(f"[UI] Close {self.__class__.__name__}")
            game_state["dialog_just_closed"] = True

    def on_activated(self): pass  # open 時フック（サブクラスでオーバーライド）

    def _close_back(self):
        """「もどる」: 親ダイアログがあればそれを再表示、なければ普通に閉じる。"""
        self.is_active = False
        if self._back_dialog:
            self._back_dialog.is_active = True
        else:
            game_state["dialog_just_closed"] = True


    # --- サブクラスが実装するフック ---
    def get_title(self): return "MENU"
    def get_header_right(self, player): return ""
    def get_item_label(self, item, idx): return str(item)
    def get_item_color(self, item, idx, is_selected):
        return (255, 255, 100) if is_selected else (255, 255, 255)
    def get_detail_lines(self, player): return []
    def get_item_image_path(self, item, idx, player): return None

    # --- 共通ナビゲーション ---
    def _navigate(self, events):
        """カーソル移動を処理し、'cancel'|'confirm'|None を返す。"""
        from systems.audio_manager import play_sfx
        from constants import SOUND_CURSOR_MOVE, KEY_MOVE_UP, KEY_MOVE_DOWN, KEY_CANCEL, KEY_CONFIRM
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == KEY_CANCEL:
                    print(f"[UI] {self.__class__.__name__} Button: CANCEL")
                    return "cancel"
                if event.key == KEY_MOVE_UP:
                    if self.cursor_idx > 0:
                        self.cursor_idx -= 1
                    else:
                        self.cursor_idx = len(self.items) - 1
                    label = self.get_item_label(self.items[self.cursor_idx], self.cursor_idx)
                    print(f"[UI] {self.__class__.__name__} Cursor: {label} (Idx: {self.cursor_idx})")
                    play_sfx(SOUND_CURSOR_MOVE)
                elif event.key == KEY_MOVE_DOWN:
                    if self.cursor_idx < len(self.items) - 1:
                        self.cursor_idx += 1
                    else:
                        self.cursor_idx = 0
                    label = self.get_item_label(self.items[self.cursor_idx], self.cursor_idx)
                    print(f"[UI] {self.__class__.__name__} Cursor: {label} (Idx: {self.cursor_idx})")
                    play_sfx(SOUND_CURSOR_MOVE)
                elif event.key == KEY_CONFIRM:
                    label = self.get_item_label(self.items[self.cursor_idx], self.cursor_idx)
                    print(f"[UI] {self.__class__.__name__} Button: CONFIRM ({label})")
                    return "confirm"
        return None

    # --- 共通描画 ---
    def draw(self, screen, player=None):
        if not self.is_active: return
        draw_dialog_frame(screen, self.x, self.y, self.width, self.height, alpha=240)
        sep_x = self.x + self.width // 2
        pygame.draw.line(screen, (80, 100, 120), (sep_x, self.y + 40), (sep_x, self.y + self.height - 40), 2)

        from systems.resources import font_small_bold
        screen.blit(font_small_bold.render(self.get_title(), True, (255, 200, 100)), (self.x + 30, self.y + 20))
        rh = self.get_header_right(player)
        if rh: screen.blit(self.font.render(rh, True, (200, 200, 200)), (sep_x - 180, self.y + 20))

        if not self.items:
            screen.blit(self.font.render("(なし)", True, (150, 150, 150)), (self.x + 50, self.y + 100))
        else:
            start = max(0, self.cursor_idx - self.view_size // 2)
            if start + self.view_size > len(self.items): start = max(0, len(self.items) - self.view_size)
            for i in range(start, min(start + self.view_size, len(self.items))):
                item = self.items[i]
                y_pos = self.y + 80 + (i - start) * self.row_height
                is_sel = (i == self.cursor_idx)
                color = self.get_item_color(item, i, is_sel)
                if is_sel:
                    pygame.draw.rect(screen, (60, 70, 90),
                                     (self.x + 20, y_pos - 5, self.width // 2 - 40, self.row_height), border_radius=5)
                    screen.blit(self.font.render(">", True, color), (self.x + 35, y_pos))
                label = self.get_item_label(item, i)
                max_w = sep_x - self.x - 100
                if self.font.size(label)[0] > max_w:
                    while self.font.size(label + "...")[0] > max_w and len(label) > 0: label = label[:-1]
                    label += "..."
                screen.blit(self.font.render(label, True, color), (self.x + 65, y_pos))

            # スクロールインジケーター
            if len(self.items) > self.view_size:
                indicator_x = sep_x - 30
                if start > 0:
                    pygame.draw.polygon(screen, (200, 200, 200), [(indicator_x, self.y + 70), (indicator_x - 8, self.y + 80), (indicator_x + 8, self.y + 80)])
                if start + self.view_size < len(self.items):
                    pygame.draw.polygon(screen, (200, 200, 200), [(indicator_x, self.y + self.height - 70), (indicator_x - 8, self.y + self.height - 80), (indicator_x + 8, self.y + self.height - 80)])

        # 右パネルの詳細表示
        detail_y_offset = 0
        if self.items and 0 <= self.cursor_idx < len(self.items):
            # 画像の描画
            img_path = self.get_item_image_path(self.items[self.cursor_idx], self.cursor_idx, player)
            if img_path:
                from systems.resources import load_image, scale_image_aspect
                img = load_image(img_path)
                if img:
                    scaled_img = scale_image_aspect(img, 128, 128)
                    # 中央寄せにするための計算
                    img_w, img_h = scaled_img.get_size()
                    screen.blit(scaled_img, (sep_x + 30 + (128 - img_w) // 2, self.y + 60 + (128 - img_h) // 2))
                    detail_y_offset = 140

        lines = self.get_detail_lines(player)
        if lines:
            self.draw_right_panel(screen, player, sep_x, detail_y_offset)

    def draw_right_panel(self, screen, player, sep_x, detail_y_offset):
        lines = self.get_detail_lines(player)
        if lines:
            draw_text_wrapped(screen, self.font, "\n".join(lines),
                              sep_x + 30, self.y + 80 + detail_y_offset, self.width // 2 - 60, color=(220, 230, 240))


class InventoryDialog(BaseListDialog):
    """アイテム（消耗品）一覧ダイアログ"""
    STATE_KEY = "inventory_active"

    def __init__(self, screen_width, screen_height):
        super().__init__(screen_width, screen_height)
        self.row_height = 36
        self.on_select = None
        self.item_data = []   # (itype, iid) と items を並行管理
        self.action_dialog = None
        self._path_cache = {} # 画像パスのキャッシュ { (itype, key): path }

    def draw_right_panel(self, screen, player, sep_x, detail_y_offset):
        if not player or self.cursor_idx >= len(self.item_data): return
        data = self.item_data[self.cursor_idx]
        if not data or data[0] == "cancel": return
        
        itype, key = data
        if itype not in ("weapon", "armor", "shield", "lantern", "stave"):
            # 消耗品は従来通り1列で描画
            lines = self.get_detail_lines(player)
            if lines:
                draw_text_wrapped(screen, self.font, "\n".join(lines),
                                  sep_x + 30, self.y + 80 + detail_y_offset, self.width // 2 - 60, color=(220, 230, 240))
            return

        # 装備品の場合は2列パラメータ＋最下部説明文の特別描画
        inv = getattr(player, itype + "_inventory", [])
        inst = player._find_equip_inst(inv, key)
        if not inst: return

        # 1. 装備名の描画
        from systems.resources import font_small_bold
        name_font = font_small_bold
        name_text = inst.get_name()
        screen.blit(name_font.render(name_text, True, (255, 220, 100)), (sep_x + 30, self.y + 80 + detail_y_offset))
        
        # 2. パラメータの収集
        from wordings import Text
        S_MAP = {"attack_bonus": "攻撃力", "defense_bonus": "防御力", "hp_bonus": "最大HP",
                 "dex_bonus": "器用さ", "eva_bonus": "回避率", "crit_bonus": "会心率",
                 "block_chance": "回避率", "block_chance_close": "近距離回避",
                 "block_chance_ranged": "遠距離回避", "aggro_mod": "感知補正",
                 "armor_penetration": Text.UI.STAT_ARMOR_PENETRATION, "stupidity": Text.UI.STAT_CONFUSION_ICON}
        MAGIC_MAP = {
            "magic_fire_damage":    "🔥炎ダメ",
            "magic_fire_range":     "🔥炎射程",
            "magic_heal_ratio":     "💚回復量",
            "magic_knockback_damage":"💨吹飛ダメ",
            "magic_invincible_turns":"✨無敵ターン",
            "magic_stave_bonus":     "🔮杖回数",
            "magic_light_stave_bonus": "💡燈杖回",
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
            if inst.enhance > 0:
                val += inst.get_enhance_bonus(k)
            if val:
                is_pct = k in ("crit_bonus", "block_chance", "eva_bonus", "block_chance_close", "block_chance_ranged", "armor_penetration")
                val_to_use = val * 100 if is_pct and isinstance(val, float) else val
                param_texts.append(f"{label}: {fmt(val_to_use)}%" if is_pct else f"{label}: {fmt(val)}")
                
        for mk, mlabel in MAGIC_MAP.items():
            mval = inst.get_stat(mk, 0)
            if mval:
                is_pct = mk in ("magic_fire_damage", "magic_heal_ratio", "magic_knockback_damage")
                val_to_use = mval * 100 if is_pct and isinstance(mval, float) else mval
                param_texts.append(f"{mlabel}: {fmt(val_to_use)}%" if is_pct else f"{mlabel}: {fmt(mval)}")

        # 3. パラメータの2列描画
        start_x = sep_x + 30
        start_y = self.y + 80 + detail_y_offset + 35
        cw = self.width // 2 - 60
        line_h = self.font.get_height() + 4
        
        N = len(param_texts)
        half = (N + 1) // 2
        
        max_y = start_y
        for i, text in enumerate(param_texts):
            col = 0 if i < half else 1
            row = i if col == 0 else i - half
            x = start_x if col == 0 else start_x + cw // 2 + 10
            y = start_y + row * line_h
            screen.blit(self.font.render(text, True, (220, 230, 240)), (x, y))
            max_y = max(max_y, y + line_h)

        # 4. 説明文の描画（最下部1列）
        desc = inst.get_stat("describe", "")
        if desc:
            desc_y = max(max_y + 15, self.y + self.height - 85)
            draw_text_wrapped(screen, self.font, desc, start_x, desc_y, cw, color=(170, 170, 170))

    def get_title(self): return Text.UI.INVENTORY_TITLE

    def setup(self, player, dialog, game_state, dungeon, stave_selection_dialog, item_action_dialog):
        from systems.item_handler import make_use_item_callback
        self.player = player
        self.dialog = dialog
        self.dungeon = dungeon
        self.on_select = make_use_item_callback(player, dialog, self, game_state, stave_selection_dialog=stave_selection_dialog)
        self.action_dialog = item_action_dialog

    # --- InventoryDialog 固有のデータ更新 ---
    def update_items_from_player(self, player):
        labels, data = [], []
        from constants import CONSUMABLE_DATA
        for item in player.items:
            k, c = item["key"], item.get("count", 1)
            n = CONSUMABLE_DATA.get(k, {}).get("name", k)
            labels.append(f"{n} x{c}" if c > 1 else n); data.append(("consumable", k))
        labels.append(Text.UI.QUIT); data.append(("cancel", None))
        self.items, self.item_data = labels, data

    def get_item_image_path(self, item, idx, player):
        if idx >= len(self.item_data) or not player: return None
        itype, key_or_iid = self.item_data[idx]
        if itype == "cancel": return None
        
        from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, LANTERN_DATA, STAVE_DATA, CONSUMABLE_DATA
        catalog = {"weapon": WEAPON_DATA, "armor": ARMOR_DATA, "shield": SHIELD_DATA, "lantern": LANTERN_DATA, "stave": STAVE_DATA}
        
        if itype in ("weapon", "armor", "shield", "lantern", "stave"):
            inv = getattr(player, itype + "_inventory", [])
            inst = player._find_equip_inst(inv, key_or_iid)
            if not inst: return None
            
            # キャッシュチェック
            cache_key = (itype, inst.key)
            if cache_key in self._path_cache:
                return self._path_cache[cache_key]
            
            data = catalog.get(itype, {}).get(inst.key, {})
            path = data.get("image_path")
            if not path and data.get("image_dir"):
                import os
                idir = data.get("image_dir")
                if os.path.exists(idir):
                    # 1. down.png
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
                
            # キャッシュに保存
            self._path_cache[cache_key] = path
            return path
        else:
            return CONSUMABLE_DATA.get(key_or_iid, {}).get("image_path")

    # --- BaseListDialog フック ---
    def get_title(self): return Text.UI.INVENTORY_TITLE
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
        from wordings import Text
        S_MAP = {"attack_bonus": "攻撃力", "defense_bonus": "防御力", "hp_bonus": "最大HP",
                 "dex_bonus": "器用さ", "eva_bonus": "回避率", "crit_bonus": "会心率",
                 "block_chance": "回避率", "block_chance_close": "近距離回避率",
                 "block_chance_ranged": "遠距離回避率", "aggro_mod": "感知補正",
                 "armor_penetration": Text.UI.STAT_ARMOR_PENETRATION, "stupidity": Text.UI.STAT_CONFUSION_ICON}
        MAGIC_MAP = {
            "magic_fire_damage":    "🔥炎ダメージ",
            "magic_fire_range":     "🔥炎射程",
            "magic_heal_ratio":     "💚回復量",
            "magic_knockback_damage":"💨吹飛ダメージ",
            "magic_invincible_turns":"✨無敵ターン",
            "magic_stave_bonus":     "🔮杖回数",
            "magic_light_stave_bonus": "💡燈杖回",
        }
        
        def fmt(val):
            if val % 1 == 0:
                val_str = str(int(val))
            else:
                val_str = str(round(val, 2))
            return f"+{val_str}" if val > 0 else val_str

        if itype in ("weapon", "armor", "shield", "lantern", "stave"):
            inv = getattr(player, itype + "_inventory", [])
            inst = player._find_equip_inst(inv, key)
            if not inst: return []
            lines.append(inst.get_name())
            for k, label in S_MAP.items():
                val = inst.get_stat(k, 0)
                if inst.enhance > 0:
                    val += inst.get_enhance_bonus(k)
                if val:
                    is_pct = k in ("crit_bonus", "block_chance", "eva_bonus", "block_chance_close", "block_chance_ranged", "armor_penetration")
                    val_to_use = val * 100 if is_pct and isinstance(val, float) else val
                    lines.append(f"{label}: {fmt(val_to_use)}%" if is_pct else f"{label}: {fmt(val)}")
            # 魔法ボーナスの表示
            for mk, mlabel in MAGIC_MAP.items():
                mval = inst.get_stat(mk, 0)
                if mval:
                    is_pct = mk in ("magic_fire_damage", "magic_heal_ratio", "magic_knockback_damage")
                    val_to_use = mval * 100 if is_pct and isinstance(mval, float) else mval
                    lines.append(f"{mlabel}: {fmt(val_to_use)}%" if is_pct else f"{mlabel}: {fmt(mval)}")
            desc = inst.get_stat("describe", "")
            if desc: lines.extend(["", desc])
        else:
            from constants import CONSUMABLE_DATA
            info = CONSUMABLE_DATA.get(key, {})
            lines.append(info.get("name", key))
            desc = info.get("describe", "")
            if desc: lines.extend(["", desc])
        return lines


    # --- イベント処理 ---
    def handle_events(self, events):
        if not self.is_active: return
        from systems.audio_manager import play_sfx
        from constants import SOUND_SELECT, SOUND_CANCEL
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
        for inst in player.weapon_inventory:
            prefix = "E:" if inst.iid == player.equipped_weapon else ""
            labels.append(prefix + inst.get_name()); data.append(("weapon", inst.iid))
        for inst in player.armor_inventory:
            prefix = "E:" if inst.iid == player.equipped_armor else ""
            labels.append(prefix + inst.get_name()); data.append(("armor", inst.iid))
        for inst in getattr(player, "shield_inventory", []):
            prefix = "E:" if inst.iid == player.equipped_shield else ""
            labels.append(prefix + inst.get_name()); data.append(("shield", inst.iid))
        for inst in getattr(player, "lantern_inventory", []):
            prefix = "E:" if inst.iid == player.equipped_lantern else ""
            labels.append(prefix + inst.get_name()); data.append(("lantern", inst.iid))
        labels.append(Text.UI.QUIT); data.append(("cancel", None))
        self.items, self.item_data = labels, data

class StaveInventoryDialog(InventoryDialog):
    """杖専用管理画面"""
    STATE_KEY = "stave_inventory_active"

    def get_title(self): return Text.UI.STAVE_TITLE

    def update_items_from_player(self, player):
        labels, data = [], []
        for inst in player.stave_inventory:
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
        for item in player.event_items:
            k, c = item["key"], item.get("count", 1)
            n = CONSUMABLE_DATA.get(k, {}).get("name", k)
            labels.append(f"{n} x{c}" if c > 1 else n); data.append(("consumable", k))
        labels.append(Text.UI.QUIT); data.append(("cancel", None))
        self.items, self.item_data = labels, data

    def handle_events(self, events):
        if not self.is_active: return
        from systems.audio_manager import play_sfx
        from constants import SOUND_SELECT, SOUND_CANCEL
        action = self._navigate(events)
        if action == "cancel":
            play_sfx(SOUND_CANCEL); self._close_back()
        elif action == "confirm":
            if self.cursor_idx < len(self.item_data):
                itype, _ = self.item_data[self.cursor_idx]
                if itype == "cancel":
                    play_sfx(SOUND_CANCEL); self._close_back()
                else:
                    # 貴重品は選択してもアクションを開かず、詳細表示のみ（drawで更新）
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
            (Text.UI.MENU_ITEMS,      "所持アイテム（薬・巻物など）の一覧を表示します。"),
            (Text.UI.MENU_EQUIP,      "武器・鎧・盾・カンテラの管理画面を開きます。"),
            (Text.UI.MENU_STAVES,     "所持している杖の管理画面を開きます。"),
            (Text.UI.MENU_EVENT_ITEMS, "冒険者の証などの貴重品を確認します。"),
            (Text.UI.MENU_STATUS,     "プレイヤーのステータスを表示します。"),
            (Text.UI.MENU_QUESTS,     "現在のクエスト進捗を確認します。"),
            (Text.UI.MENU_QUIT,       "タイトル画面に戻ります。"),
            (Text.UI.MENU_MAP_TOGGLE, "ミニマップの表示・非表示を切り替えます。"),
            (Text.UI.MENU_BACK,       "メニューを閉じます。"),
        ]

    def setup(self, on_items, on_equip, on_staves, on_event, on_status, on_quests, on_quit):
        self.callbacks = [on_items, on_equip, on_staves, on_event, on_status, on_quests, on_quit]

    def get_title(self): return Text.UI.MENU_TITLE

    def get_item_label(self, item, idx):
        label, _ = item
        if idx == 7: # ミニマップのインデックス
            st = "ON" if (self._dungeon and getattr(self._dungeon, "show_map", True)) else "OFF"
            return f"{label} [{st}]"
        return label

    def get_detail_lines(self, player):
        return [self.items[self.cursor_idx][1]] if self.items else []

    def handle_events(self, events, dungeon=None):
        if not self.is_active: return
        self._dungeon = dungeon
        from systems.audio_manager import play_sfx
        from constants import SOUND_SELECT, SOUND_CANCEL
        action = self._navigate(events)
        if action == "cancel":
            play_sfx(SOUND_CANCEL); self.is_active = False  # メニュー自体の「もどる」 = 完全終了
        elif action == "confirm":
            idx = self.cursor_idx
            if idx == len(self.items) - 1:  # もどる
                play_sfx(SOUND_CANCEL); self.is_active = False
            elif idx == 7:  # ミニマップ
                if dungeon: dungeon.show_map = not getattr(dungeon, "show_map", True)
                play_sfx(SOUND_SELECT)
            else:
                # メニューは閉じずにサブダイアログへ移行
                play_sfx(SOUND_SELECT)
                if 0 <= idx < len(self.callbacks):
                    cb = self.callbacks[idx]
                    cb()  # コールバックがサブダイアログを開く
                self.is_active = False  # メニューを閉じる

    def setup2(self, inventory_dialog, equip_dialog, status_dialog, stave_inv_dialog=None, event_inv_dialog=None):
        """サブダイアログに「もどる」先として自分を登録する。"""
        if inventory_dialog: inventory_dialog._back_dialog = self
        if equip_dialog:     equip_dialog._back_dialog = self
        if status_dialog:    status_dialog._back_dialog = self
        if stave_inv_dialog: stave_inv_dialog._back_dialog = self
        if event_inv_dialog: event_inv_dialog._back_dialog = self

    def draw(self, screen, dungeon=None):
        self._dungeon = dungeon
        super().draw(screen, None)


class StatusBar:
    """画面上部に表示されるヘッドアップディスプレイ(HP, ATK, DEFなど)"""
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.y = 15
        self.bar_height = 80
        self.font = font_hud
        
    def draw(self, screen, player, floor_level, guild_system=None):
        # 影付きテキスト描画 (色を微調整)
        def draw_text_shadow(text, font, color, pos):
            # 影を少し薄く、位置をずらしてシャープに (1px offset)
            shadow = font.render(text, True, (10, 15, 20))
            screen.blit(shadow, (pos[0] + 1, pos[1] + 1))
            # 本体
            surf = font.render(text, True, color)
            screen.blit(surf, pos)

        # 共通の色定義 (Midnight Jewels & Crystal Blue Palette)
        COLOR_BG = (20, 25, 35)       # より深い紺色
        COLOR_TEXT = (236, 240, 241)     # オフホワイト
        COLOR_HP_HIGH = (46, 204, 113)   # エメラルドグリーン (Healthy)
        COLOR_HP_MID  = (241, 196, 15)   # サンフラワーイエロー (Warning: <= 2/3)
        COLOR_HP_LOW  = (231, 76, 60)    # アリザリンレッド (Danger: <= 1/4)
        COLOR_FLOOR   = (174, 214, 241)   # ソフトスカイブルー

        # --- HP & ステータス (左上) ---
        bar_x, bar_y = 20, 20
        bar_w, bar_h = 180, 16 # わずかに厚みを持たせて質感を強調
        hp_ratio = player.hp / player.max_hp if player.max_hp > 0 else 0
        
        # 1. ゲージ背景 (外枠/フレーム)
        pygame.draw.rect(screen, (50, 60, 70), (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4), border_radius=3)
        pygame.draw.rect(screen, COLOR_BG, (bar_x, bar_y, bar_w, bar_h), border_radius=2)
        
        # 2. ゲージ本体 (2/3で黄色、1/4で赤)
        if hp_ratio <= 0.25:
            current_bar_color = COLOR_HP_LOW
        elif hp_ratio <= 0.666:
            current_bar_color = COLOR_HP_MID
        else:
            current_bar_color = COLOR_HP_HIGH
        fill_w = int(bar_w * hp_ratio)
        if fill_w > 0:
            # メインの色
            pygame.draw.rect(screen, current_bar_color, (bar_x, bar_y, fill_w, bar_h), border_radius=2)
            
            # 3. グロス効果 (上部のハイライト)
            # 少し明るい色で光沢を表現
            bright_color = (min(current_bar_color[0] + 50, 255), min(current_bar_color[1] + 50, 255), min(current_bar_color[2] + 50, 255))
            pygame.draw.rect(screen, bright_color, (bar_x, bar_y, fill_w, bar_h // 2), border_radius=2)
            
            # 4. シャドウ効果 (下部の濃い線)
            dark_color = (max(current_bar_color[0] - 40, 0), max(current_bar_color[1] - 40, 0), max(current_bar_color[2] - 40, 0))
            pygame.draw.line(screen, dark_color, (bar_x, bar_y + bar_h - 1), (bar_x + fill_w - 1, bar_y + bar_h - 1))

        # 5. 枠
        pygame.draw.rect(screen, (120, 140, 160), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=2)
        
        # HPテキスト
        hp_text = f"HP {player.hp}/{player.max_hp}"
        draw_text_shadow(hp_text, self.font, COLOR_TEXT, (bar_x + bar_w + 12, bar_y - 4))

        # 攻撃・防御・盾 (HPの下)
        stat_y = bar_y + 24
        atk_val = player.total_attack
        draw_text_shadow(Text.UI.ATK_LABEL.format(atk=atk_val), self.font, COLOR_TEXT, (bar_x, stat_y))
        def_val = player.total_defense
        draw_text_shadow(Text.UI.DEF_LABEL.format(defense=def_val), self.font, COLOR_TEXT, (bar_x + 110, stat_y))
        eva_val = player.eva_bonus
        draw_text_shadow(Text.UI.EVA_LABEL.format(eva=eva_val), self.font, COLOR_TEXT, (bar_x + 220, stat_y))

        # --- 階層 (中央上) ---
        floor_str = Text.UI.VILLAGE if floor_level == 0 else Text.UI.FLOOR.format(level=floor_level)
        floor_surf = font_medium.render(floor_str, True, COLOR_FLOOR)
        # 中央位置
        fx = (self.screen_width - floor_surf.get_width()) // 2
        fy = 15
        # 影
        f_shadow = font_medium.render(floor_str, True, (10, 15, 20))
        screen.blit(f_shadow, (fx + 2, fy + 2))
        screen.blit(floor_surf, (fx, fy))

        # --- 所持金 & ランク (右上・縦並び) ---
        rx = self.screen_width - 180
        ry = 15
        # ゴールド
        draw_text_shadow(f"{player.coin} G", self.font, COLOR_TEXT, (rx, ry))
        # ランク & GP (GPはデバッグ時のみ表示)
        rank_name = player.guild_rank
        draw_text_shadow(f"Rank: {rank_name}", self.font, (241, 196, 15), (rx, ry + 23))
        
        # 呪い表示 (Rankの下・Hollow表示とジェム◆◆◆◆◆の描画)
        curse_level = getattr(player, "curse_level", 0)
        draw_text_shadow(Text.UI.HOLLOW_LABEL, self.font, COLOR_TEXT, (rx, ry + 46))
        
        gem_start_x = rx + 75
        gem_y = ry + 59
        for i in range(5):
            gx = gem_start_x + i * 16
            # 1. 影を描画 (1pxオフセット)
            pygame.draw.polygon(screen, (10, 15, 20), [
                (gx + 6 + 1, gem_y + 1),
                (gx + 12 + 1, gem_y + 6 + 1),
                (gx + 6 + 1, gem_y + 12 + 1),
                (gx + 1, gem_y + 6 + 1)
            ])
            if i < curse_level:
                # 活性化した呪い：怪しく光る赤紫・クリムゾンの炎
                pygame.draw.polygon(screen, (231, 76, 60), [
                    (gx + 6, gem_y),
                    (gx + 12, gem_y + 6),
                    (gx + 6, gem_y + 12),
                    (gx, gem_y + 6)
                ])
                # 内側の光沢ハイライト
                pygame.draw.polygon(screen, (255, 130, 110), [
                    (gx + 6, gem_y + 2),
                    (gx + 9, gem_y + 6),
                    (gx + 6, gem_y + 10),
                    (gx + 3, gem_y + 6)
                ])
            else:
                # 休眠状態：暗いガラスのようなグレーの枠
                pygame.draw.polygon(screen, (30, 35, 45), [
                    (gx + 6, gem_y),
                    (gx + 12, gem_y + 6),
                    (gx + 6, gem_y + 12),
                    (gx, gem_y + 6)
                ])
                pygame.draw.polygon(screen, (70, 80, 95), [
                    (gx + 6, gem_y),
                    (gx + 12, gem_y + 6),
                    (gx + 6, gem_y + 12),
                    (gx, gem_y + 6)
                ], 1)

        if getattr(player, "is_debug", False):
            draw_text_shadow(f"GP: {player.guild_point}", self.font, COLOR_TEXT, (rx, ry + 70))


# --- 視界制限（カンテラ）システム ---
import math
_vision_masks = {} # (radius, fade_radius) -> Surface

def _create_radial_mask(radius, fade_radius):
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
                alpha = 0
            elif dist >= radius + fade_radius:
                alpha = 255
            else:
                # 線形補間で透明度を計算
                alpha = int(255 * (dist - radius) / fade_radius)
            
            surface.set_at((x, y), (0, 0, 0, alpha))
    return surface

def draw_vision_overlay(screen, player, dungeon):
    """
    プレイヤーの周囲以外を暗闇で覆う。
    dungeon.is_lighted が True の場合は何もしない（全域が見える）。
    """
    if getattr(dungeon, "is_lighted", False):
        return

    from constants import LANTERN_DATA
    import pygame

    # 1. 装備中のカンテラから半径を取得
    lantern_key = "none" 
    if getattr(player, "equipped_lantern", None):
        inst = player._find_equip_inst(player.lantern_inventory, player.equipped_lantern)
        if inst:
            lantern_key = inst.key
    
    l_data = LANTERN_DATA.get(lantern_key, LANTERN_DATA["basic"])
    r_tiles = l_data["radius"]
    # [NEW] 装備ボーナスを加算
    r_tiles += getattr(player, "lantern_bonus", 0)
    
    f_tiles = l_data["fade_radius"]
    
    # 2. ピクセル単位に変換
    tile_size = getattr(dungeon, "tile_size", 32)
    
    # 明るさレベルによる半径の倍率 (1: 標準, 2: 1.5倍, 3: 2.5倍, 4: 4.5倍)
    brightness = getattr(dungeon, "brightness", 1)
    brightness_multipliers = {1: 1.0, 2: 1.5, 3: 2.5, 4: 4.5}
    mult = brightness_multipliers.get(brightness, 1.0)
    
    radius_px = int(r_tiles * tile_size * mult)
    fade_px = int(f_tiles * tile_size * mult)
    
    # 3. マスクの生成・取得
    mask_key = (radius_px, fade_px)
    if mask_key not in _vision_masks:
        _vision_masks[mask_key] = _create_radial_mask(radius_px, fade_px)
    
    mask = _vision_masks[mask_key]
    
    # 4. 描画位置の計算（プレイヤーの中心）
    sw, sh = screen.get_size()
    px = sw // 2
    py = sh // 2
    
    fog = pygame.Surface((sw, sh), pygame.SRCALPHA)
    fog.fill((0, 0, 0, 255)) # 真っ暗
    
    mask_rect = mask.get_rect(center=(px, py))
    fog.blit(mask, mask_rect, special_flags=pygame.BLEND_RGBA_MIN)
    
    screen.blit(fog, (0, 0))


def handle_ui_events(events, dialog, confirm_dialog, inventory_dialog, status_dialog, enhance_dialog, item_action_dialog, ore_selection_dialog, menu_dialog=None, player=None, dungeon=None, shop_dialog=None, stave_selection_dialog=None, guild_dialog=None, warehouse_dialog=None, bank_dialog=None, equip_dialog=None, stave_inv_dialog=None, event_inv_dialog=None, teleport_dialog=None, cutscene_manager=None, **kwargs):
    """全てのUIイベントを一括で処理する"""
    
    if cutscene_manager and cutscene_manager.is_active:
        events.clear() # イベントを破棄して操作を受け付けない
        return
        
    if dungeon:
        # インベントリなどが常に最新のダンジョンを参照するように更新
        inventory_dialog.dungeon = dungeon
        if equip_dialog: equip_dialog.dungeon = dungeon
        if stave_inv_dialog: stave_inv_dialog.dungeon = dungeon
        if stave_selection_dialog:
            stave_selection_dialog.dungeon = dungeon
            
    from constants import KEY_CONFIRM, KEY_CANCEL, KEY_INVENTORY, KEY_STATUS, KEY_MENU, KEY_MAP
    
    # マップ表示切り替え (Tab)
    for event in events:
        if event.type == pygame.KEYDOWN and event.key == KEY_MAP:
            if dungeon:
                dungeon.show_map = not getattr(dungeon, "show_map", True)
                print(f"[UI] Map Display Toggled: {dungeon.show_map}")
    
    # 決定ダイアログは最優先
    if confirm_dialog.is_active:
        confirm_dialog.handle_events(events)
        return
    
    if teleport_dialog and teleport_dialog.is_active:
        new_dungeon = teleport_dialog.handle_input(events, player)
        # メッセージが出ていれば決定キーで閉じる（商店などと同様の処理）
        if dialog.is_active and dialog.just_opened_timer <= 0:
            for event in events:
                if event.type == pygame.KEYDOWN and event.key in (KEY_CONFIRM, pygame.K_RETURN, pygame.K_z):
                    dialog.is_active = False
        if new_dungeon:
            # 演出（青いフラッシュ）
            from systems.magic_handler import FlashEffect
            new_dungeon.magic_effects.append(FlashEffect(color=(100, 150, 255), duration=40))
            return new_dungeon
        return
    
    if menu_dialog and menu_dialog.is_active:
        # サブダイアログが開いている場合はそちらを優先
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

    # アクティブなダイアログがあれば優先的に処理
    if inventory_dialog.is_active:
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == KEY_INVENTORY:
                inventory_dialog._close_back(); return
        inventory_dialog.handle_events(events)
    elif status_dialog.is_active:
        status_dialog.handle_events(events, player)
    elif enhance_dialog.is_active:
        enhance_dialog.handle_events(events, player)
        # メッセージが出ていれば決定キーで閉じる
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
        # 非アクティブ時のキー入力
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
                                    elif getattr(npc, "role", None) == "item_shop":
                                        if shop_dialog and dungeon:
                                            dialog.text = Text.NPC.ITEM_SHOP_WELCOME
                                            dialog.is_active = True
                                            shop_dialog.open_shop("道具屋", dungeon.item_shop_stock)
                                            return
                                    elif getattr(npc, "role", None) == "magic_shop":
                                        if shop_dialog and dungeon:
                                            dialog.text = "フォッフォッフォ、杖のことならわしに任せるがよいぞ。"
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
                                            # 状況に応じたメッセージを設定
                                            next_rank_data = dungeon.guild_system.get_next_rank_data(player.guild_rank)
                                            
                                            if player.guild_rank == "-":
                                                has_q = any(q.get("id") == "rank_up_F" for q in player.active_quests)
                                                if not has_q:
                                                    dialog.text = Text.NPC.GUILD_WELCOME_UNRANKED
                                                else:
                                                    dialog.text = Text.NPC.GUILD_REMIND_UNRANKED
                                                dialog.is_active = True
                                            elif next_rank_data and player.guild_point >= next_rank_data["required_gp"]:
                                                dialog.text = Text.UI.GUILD_MASTER_RANK_UP_READY
                                                dialog.is_active = True
                                            elif next_rank_data:
                                                needed = next_rank_data["required_gp"] - player.guild_point
                                                dialog.text = Text.UI.GUILD_MASTER_NEXT_RANK.format(gp=player.guild_point, needed=needed)
                                                dialog.is_active = True
                                            else:
                                                dialog.text = Text.UI.GUILD_MASTER_MAX_RANK
                                                dialog.is_active = True
                                            
                                            # 未初期化ならクエスト生成
                                            if not dungeon.guild_system.available_quests:
                                                dungeon.guild_system.generate_quests(player)
                                            guild_dialog.is_active = True
                                            guild_dialog.setup(player, dungeon)
                                            
                                            # 達成済みがある場合はセリフをお祝いにする
                                            # ただし、エンディング対象だった場合はシーンが切り替わっているので何もしない
                                            from systems.game_state import game_state
                                            if guild_dialog.mode == "AUTO_REPORT" and game_state.get("current_scene") != "ending":
                                                dialog.text = "おお、見事に依頼を達成しましたね！\nおめでとうございます！"
                                                dialog.is_active = True
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
                                        dialog.text = "\n".join(npc.get_dialogue()); dialog.is_active = True
                                        from constants import DOCTOR_FEE, POISON_CURE_FEE
                                        
                                        def make_heal_callback(fee, cure_poison=False):
                                            def heal():
                                                # 支払いロジック
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
                                            # 先に挨拶を表示
                                            dialog.text = "\n".join(npc.get_dialogue())
                                            dialog.is_active = True
                                            # ダイアログが開いた後にテレポートUIを起動
                                            teleport_dialog.open(player)
                                            return
                                    elif getattr(npc, "role", None) == "priest":
                                        from constants import CURSE_RECOVERY_COST_GP_PER_LEVEL
                                        cost = CURSE_RECOVERY_COST_GP_PER_LEVEL
                                        if getattr(player, "curse_level", 0) > 0:
                                            dialog.text = Text.NPC.PRIEST_WELCOME
                                            dialog.is_active = True
                                            if confirm_dialog:
                                                confirm_dialog.text = Text.NPC.PRIEST_CURE_CONFIRM.format(cost=cost)
                                                def on_priest_yes():
                                                    if player.guild_point >= cost:
                                                        player.guild_point -= cost
                                                        player.curse_level -= 1
                                                        import random
                                                        if player.cursed_stats:
                                                            removed = random.choice(player.cursed_stats)
                                                            player.cursed_stats.remove(removed)
                                                            dialog.text = Text.NPC.PRIEST_CURE_DONE.format(stat=player.get_cursed_stats_japanese_single(removed))
                                                        else:
                                                            dialog.text = Text.NPC.PRIEST_CURE_DONE_SIMPLE
                                                        dialog.is_active = True
                                                        from systems.sound_handler import sound_manager
                                                        from constants import SOUND_SELECT
                                                        sound_manager.play_sfx(SOUND_SELECT)
                                                        player.save_to_file()
                                                    else:
                                                        dialog.text = Text.NPC.PRIEST_NO_GP.format(cost=cost)
                                                        dialog.is_active = True
                                                        from systems.audio_manager import play_sfx
                                                        from constants import SOUND_CANCEL
                                                        play_sfx(SOUND_CANCEL)
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
                                        dialog.set_pages(npc.get_dialogue())
                                    return
                elif event.key == KEY_MENU:
                    if menu_dialog: menu_dialog.is_active = True

class GuildDialog:
    """冒険者ギルドでの依頼受注・報告を行うダイアログ"""
    def __init__(self, screen_width, screen_height):
        self.x, self.y, self.width, self.height = get_standard_upper_layout(screen_width, screen_height)
        from systems.resources import font_small
        self.font = font_small
        self.row_height = 32
        self.view_size = 10
        self.cursor_idx = 0
        self.items = [] # (type, status, q_data)
        self.mode = "MENU" # MENU, REPORT, ACCEPT, ABANDON
        self._skip_auto_report = False
        self._pending_report = None # 確認待ちの報告クエスト
        self.dungeon_ref = None

    @property
    def is_active(self): return game_state.get("guild_active", False)
    @is_active.setter
    def is_active(self, v):
        game_state["guild_active"] = v
        if v:
            print(f"[UI] Open GuildDialog (Mode: {self.mode})")
            self._skip_auto_report = False
            self._pending_report = None
            self.cursor_idx = 0
            if self.mode != "AUTO_REPORT":
                self.mode = "MENU"
        else:
            print(f"[UI] Close GuildDialog")
            game_state["dialog_just_closed"] = True

    def setup(self, player, dungeon):
        self.dungeon_ref = dungeon
        self.items = []
        
        # 報告完了後などにMENUに戻れるよう、AUTO_REPORT時は一旦リセット
        if self.mode == "AUTO_REPORT":
            self.mode = "MENU"

        if self.mode == "MENU":
            if not self._skip_auto_report:
                completed_q = None
                for q in player.active_quests:
                    if self._is_reportable(player, q):
                        completed_q = q
                        break
                
                if completed_q:
                    # 達成済みがあれば、保留状態にする（自動遷移はしない）
                    self._pending_report = completed_q
                    # アイテムリストはMENUのまま、通常のメニュー項目を構築する（いいえの場合のため）
                else:
                    self._pending_report = None

            # 通常メニュー (モードに関わらずMENUなら常に構築する)
            self.items = [
                ("mode", "ACCEPT_DAILY", "日常依頼を受注", "ランダムに生成された日常的な依頼を受けます。"),
            ]
            # 昇格試験の判定
            next_rank_data = dungeon.guild_system.get_next_rank_data(player.guild_rank)
            if next_rank_data and player.guild_point >= next_rank_data["required_gp"]:
                already_active = any(q.get("is_rank_up") for q in player.active_quests)
                if not already_active:
                    self.items.append(("mode", "ACCEPT_RANKUP", "昇級試験を受ける", f"{next_rank_data['rank']}ランクへの昇格試験に挑戦します。"))
            
            self.items.append(("mode", "ACCEPT_FIXED", "特別な依頼を見る", "特定の条件で発生する特別な依頼を確認します。"))
            self.items.append(("mode", "ABANDON", "依頼破棄", "現在受けている依頼をキャンセルします。"))
            self.items.append(("mode", "SAVE", "💾 記録する", "現在の進行状況をセーブします。"))
            self.items.append(("cancel", None, "🚪 ギルドを出る", "ギルドメニューを終了します。"))
            
        elif self.mode == "REPORT":
            # 条件を満たしているもののみ
            for q in player.active_quests:
                if self._is_reportable(player, q):
                    self.items.append(("active", q))
            self.items.append(("back", None, Text.UI.QUIT))
            
        elif self.mode == "ACCEPT_DAILY":
            # ランダム生成クエスト (日常依頼)
            for q in dungeon.guild_system.available_quests:
                self.items.append(("available", q))
            self.items.append(("back", None, Text.UI.QUIT))
            
        elif self.mode == "ACCEPT_RANKUP":
            # 昇格クエスト
            next_rank_data = dungeon.guild_system.get_next_rank_data(player.guild_rank)
            if next_rank_data and player.guild_point >= next_rank_data["required_gp"]:
                rank_up_q = self._create_rank_up_quest(next_rank_data)
                self.items.append(("available", rank_up_q))
            self.items.append(("back", None, Text.UI.QUIT))
            
        elif self.mode == "ACCEPT_FIXED":
            # 固定クエスト
            for q in dungeon.guild_system.fixed_quests:
                self.items.append(("available", q))
            self.items.append(("back", None, Text.UI.QUIT))
            
        elif self.mode == "ABANDON":
            # 受注中のものすべて（完了していても破棄はできるが、通常は未完了のものを破棄する）
            for q in player.active_quests:
                self.items.append(("active_to_abandon", q))
            self.items.append(("back", None, Text.UI.QUIT))

    def _is_reportable(self, player, q):
        return player.is_quest_reportable(q)

    def _create_rank_up_quest(self, next_rank_data):
        from constants import CONSUMABLE_DATA
        cert_data = CONSUMABLE_DATA.get(next_rank_data["rank_up_item"], {})
        return {
            "id": f"rank_up_{next_rank_data['rank']}",
            "type": "delivery", "is_rank_up": True,
            "target_key": next_rank_data["rank_up_item"],
            "target_name": cert_data.get("name", "冒険者の証"),
            "amount": 1, "reward_gold": next_rank_data.get("rank_up_reward_gold", 0), "reward_gp": 0,
            "next_rank": next_rank_data["rank"],
            "title": "冒険者の証の回収" if next_rank_data['rank'] == "F" else Text.Guild.QUEST_RANK_UP_TITLE.format(rank=next_rank_data['rank'])
        }

    def handle_events(self, events, player, dialog, confirm_dialog):
        from constants import KEY_MOVE_UP, KEY_MOVE_DOWN, KEY_CANCEL, KEY_CONFIRM
        if not self.is_active: return
        
        # 保留中の報告があれば確認ダイアログを優先
        if self._pending_report and not confirm_dialog.is_active:
            q = self._pending_report
            if q.get("type") == "delivery":
                t_name = q.get('target_name') or q.get('target_key')
                confirm_dialog.text = Text.UI.GUILD_REPORT_CONFIRM.format(name=t_name)
            else:
                confirm_dialog.text = Text.UI.GUILD_REPORT_CONFIRM_GENERIC
            
            def on_confirm():
                self._report_quest(player, q, dialog)
                # 報告処理の中で mode = AUTO_REPORT に遷移する
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
                        player.outbreak_bonus_active = False # ギルドを離れる時にボーナスをリセット
                    else:
                        self.mode = "MENU"
                        self._skip_auto_report = True # キャンセルしたら以降はメニューを表示
                        self.cursor_idx = 0
                        self.setup(player, self.dungeon_ref)
                elif event.key == KEY_CONFIRM:
                    if 0 <= self.cursor_idx < len(self.items):
                        item = self.items[self.cursor_idx]
                        if self.mode == "AUTO_REPORT":
                            # AUTO_REPORT画面では決定でダイアログを閉じてMENUへ
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
            player.outbreak_bonus_active = False # ギルドを離れる時にボーナスをリセット
            return
        if status == "back":
            self.mode = "MENU"
            self.cursor_idx = 0
            self.setup(player, self.dungeon_ref)
            return
        if status == "mode":
            self.mode = item[1]
            if self.mode == "SAVE":
                # ギルドでの手動セーブ実行
                print("[GUILD] Manual save triggered.")
                player.save_to_file()
                dialog.text = "これまでの冒険を記録しました！"
                dialog.is_active = True
                # セーブ完了後はメニューに戻る
                self.mode = "MENU"
                
            self.cursor_idx = 0
            self.setup(player, self.dungeon_ref)
            return

        q = item[1]
        if status == "available":
            # 受注上限チェック
            if len(player.active_quests) >= 1:
                dialog.text = Text.NPC.GUILD_LIMIT
                dialog.is_active = True
                return

            # 受注確認ダイアログ
            def on_accept():
                player.accept_quest(q)
                # リストから削除
                if q in self.dungeon_ref.guild_system.available_quests:
                    self.dungeon_ref.guild_system.available_quests.remove(q)
                elif q in self.dungeon_ref.guild_system.fixed_quests:
                    self.dungeon_ref.guild_system.fixed_quests.remove(q)
                
                # 🎵 効果音再生
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
            # 達成報告 (確認ダイアログを出す)
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
            # 破棄処理
            self._confirm_abandon(player, q, dialog, confirm_dialog)

    def _report_quest(self, player, q, dialog):
        # 既に _is_reportable でチェック済みのはずだが、念の為再計算
        success = False
        if q["type"] == "hunt":
            if player.quest_tokens.get(q["target_key"], 0) >= q["amount"]:
                player.quest_tokens[q["target_key"]] -= q["amount"]; success = True
        elif q["type"] == "delivery":
            if player.is_quest_reportable(q):
                player.remove_item_by_key(q["target_key"], q["amount"])
                success = True
        
        if success:
            # 🎵 簡易ファンファーレを生成して再生
            self._play_placeholder_complete_sound()

            if q.get("is_rank_up"):
                player.guild_rank = q["next_rank"]
                
                def on_done():
                    dialog.text = f"依頼達成ですね。\n{player.guild_rank}ランクに昇格です！おめでとうございます！"
                    dialog.is_active = True
                    
                if hasattr(self, "cutscene_manager") and self.cutscene_manager:
                    self.cutscene_manager.start_rank_up(callback=on_done)
                else:
                    on_done()
            # マスターデータからもエンディング対象かチェック（セーブデータにフラグがない場合への対策）
            is_ending_quest = q.get("ending", False)
            if not is_ending_quest and q.get("id"):
                from constants import FIXED_QUEST_DATA
                for fq in FIXED_QUEST_DATA:
                    if fq.get("id") == q.get("id") and fq.get("ending"):
                        is_ending_quest = True
                        break

            if is_ending_quest:
                # エンディングフラグがある場合は、特別演出へ
                from systems.game_state import game_state
                game_state["current_scene"] = "ending"
                game_state["ending_index"] = 0
                game_state["ending_timer"] = 0
                game_state["ending_alpha"] = 0
                self.is_active = False # ギルド画面を閉じる
                return

            else:
                player.coin += q["reward_gold"]
                gp_reward = q["reward_gp"]
                dialog.text = "見事に依頼を達成しましたね！\nおめでとうございます！"
                
                player.guild_point += gp_reward
                if q.get("id"): player.completed_fixed_quests.append(q["id"])
                dialog.is_active = True

            # 報告完了画面（フラッシュ）のためにモードとアイテムをセット
            self.mode = "AUTO_REPORT"
            self.items = [("auto_report", q)]
            player.active_quests.remove(q)
            # [AUTO-SAVE] クエスト達成時に自動セーブ
            print(f"[GUILD] Quest '{q.get('title')}' completed. Auto-saving...")
            player.save_to_file()
            # self.setup(player, self.dungeon_ref) # setupでmodeがリセットされるのでここでは呼ばない
        else:
            dialog.text = Text.UI.GUILD_QUEST_UNMET
            dialog.is_active = True

    def _play_placeholder_complete_sound(self):
        """クエスト達成時の効果音を再生する（constants.pyで定義されたパスを使用）"""
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
        
        # --- AUTO_REPORT モードの特別な祝福画面 ---
        if self.mode == "AUTO_REPORT" and self.items:
            draw_dialog_frame(screen, self.x + 50, self.y + 50, self.width - 100, self.height - 100, alpha=250)
            q = self.items[0][1]
            
            from systems.resources import font_small_bold, font_medium
            # お祝いテキスト
            title_text = font_medium.render(Text.UI.GUILD_REPORT_CONGRATS, True, (255, 215, 0))
            screen.blit(title_text, (self.x + self.width // 2 - title_text.get_width() // 2, self.y + 100))
            
            # クエスト名
            q_name = self.font.render(q['title'], True, (255, 255, 255))
            screen.blit(q_name, (self.x + self.width // 2 - q_name.get_width() // 2, self.y + 160))
            
            # 報酬プレビュー
            if q.get("is_rank_up"):
                reward_str = Text.UI.GUILD_REPORT_RANK_UP.format(rank=q['next_rank'])
            else:
                reward_str = Text.UI.GUILD_REPORT_REWARD.format(gold=q['reward_gold'], gp=q['reward_gp'])
            reward_text = self.font.render(reward_str, True, (180, 255, 180))
            screen.blit(reward_text, (self.x + self.width // 2 - reward_text.get_width() // 2, self.y + 220))
            
            # ガイド
            guide = self.font.render(Text.UI.GUILD_REPORT_GUIDE, True, (200, 200, 200))
            screen.blit(guide, (self.x + self.width // 2 - guide.get_width() // 2, self.y + self.height - 130))
            return

        # --- 通常のメニュー表示 ---
        draw_dialog_frame(screen, self.x, self.y, self.width, self.height, alpha=240)

        # 1. 境界線の描画 (中央)
        separator_x = self.x + self.width // 2
        pygame.draw.line(screen, (80, 100, 120), (separator_x, self.y + 40), (separator_x, self.y + self.height - 40), 2)

        # 2. ランク情報 (左上に配置)
        from systems.resources import font_small_bold
        title_str = Text.UI.GUILD_QUEST_LIST_HEADER
        title = font_small_bold.render(title_str, True, (255, 200, 100))
        screen.blit(title, (self.x + 30, self.y + 20))

        # --- 左側：リスト ---
        # 戻るボタン以外の実質的な要素があるかチェック
        has_content = any(item[0] not in ("back", "cancel") for item in self.items)
        if not has_content:
            msg_str = Text.UI.GUILD_LIST_EMPTY
            if self.mode == "REPORT": msg_str = "報告できる依頼なし"
            msg = self.font.render(msg_str, True, (150, 150, 150))
            screen.blit(msg, (self.x + 50, self.y + 100))
        
        if not self.items:
            pass # items自体が空の場合は上のメッセージだけ表示（通常はsetupでbackが入る）
        else:
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
                
                # 表示テキストの構築
                if status == "mode":
                    display_name = item[2]
                elif status in ("cancel", "back"):
                    display_name = Text.UI.QUIT
                else:
                    q = item[1]
                    label = "" #"報告:" if status == "active" else "受注:"
                    if status == "active": color = (180, 255, 180) if i != self.cursor_idx else (255, 255, 100)
                    # 「【入会試験】」などの不要なタグを削除
                    raw_title = q['title'].replace("【テスト】", "")
                    display_name = raw_title.strip()

                # はみ出し対策：長すぎる場合は省略
                if self.font.size(display_name)[0] > max_list_w:
                    while self.font.size(display_name + "...")[0] > max_list_w and len(display_name) > 0:
                        display_name = display_name[:-1]
                    display_name += "..."

                name_text = self.font.render(display_name, True, color)
                screen.blit(name_text, (self.x + 65, y_pos))

            # スクロールインジケーター
            if len(self.items) > self.view_size:
                indicator_x = separator_x - 30
                if start > 0:
                    pygame.draw.polygon(screen, (200, 200, 200), [(indicator_x, self.y + 70), (indicator_x - 8, self.y + 80), (indicator_x + 8, self.y + 80)])
                if start + self.view_size < len(self.items):
                    pygame.draw.polygon(screen, (200, 200, 200), [(indicator_x, self.y + self.height - 70), (indicator_x - 8, self.y + self.height - 80), (indicator_x + 8, self.y + self.height - 80)])

        # --- 右側：詳細解説 ---
        desc_x = separator_x + 30
        desc_y = self.y + 80
        desc_width = self.width // 2 - 60
        
        selected_item = self.items[self.cursor_idx] if self.items else None
        if selected_item:
            status = selected_item[0]
            
            # 解説テキストの構築
            desc_text = ""
            if status == "mode":
                mode_id = selected_item[1]
                menu_descs = {
                    "REPORT": "完了した依頼の報告を行い、\n報酬を受け取ります。",
                    "ACCEPT_DAILY": "階層に応じた日常依頼を受注します。\n(お小遣い稼ぎに適したランダムな内容です)",
                    "ACCEPT_RANKUP": "次のランクへ昇格するための試験を受けます。\n(ストーリーが進行する重要な依頼です)",
                    "ACCEPT_FIXED": "特定の条件で発生する依頼を確認します。\n(ボス戦や重要なイベントが発生します)",
                    "ABANDON": "現在受けている依頼を中止します。\n※違約金とGPの減少が発生します。"
                }
                desc_text = menu_descs.get(mode_id, Text.UI.STATUS_MENU_HINT)
            elif status in ("cancel", "back"):
                desc_text = "前の画面に戻ります。"
            else:
                # 依頼詳細 (データ不備に備えて .get() で安全にアクセス)
                q = selected_item[1]
                desc_text = ""
                
                # 依頼主を表示
                if q.get("requester"):
                    desc_text += f"【依頼主】 {q.get('requester')}\n\n"
                else:
                    desc_text += "\n"
                
                # フレーバーテキストを表示
                if q.get("description"):
                    desc_text += f"{q.get('description')}\n\n"
                
                t = q.get("type", "")
                target = q.get("target_name")
                if not target:
                    # target_name が無い場合はマスターデータから取得を試みる
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
                    # 障害物か敵かで文言を切り替える
                    key = q.get("target_key")
                    from constants import ENEMY_DATA
                    is_static = ENEMY_DATA.get(key, {}).get("is_static", False)
                    unit = "個" if is_static else "体"
                    verb = "破壊" if is_static else "討伐"
                    desc_text += f"【内容】\n{target} を {amount} {unit}{verb}する。"
                elif t == "delivery":
                    desc_text += f"【内容】\n{target} を {amount} 個納品する。"
                
                reward_gold = q.get("reward_gold", 0)
                reward_gp = q.get("reward_gp", 0)
                desc_text += f"\n\n【報酬】\n{reward_gold} G / {reward_gp} GP"

            draw_text_wrapped(screen, self.font, desc_text, desc_x, desc_y, desc_width, color=(220, 230, 240))
        # 右下は余白または別の情報を置くために空けておく

class StatusDialog:
    """ステータスを詳細表示する画面 (Sキー)"""
    def __init__(self, screen_width, screen_height):
        self.x, self.y, self.width, self.height = get_standard_upper_layout(screen_width, screen_height)
        from systems.resources import font_small
        self.font = font_small
        self.mode = "STATUS"
        self.cursor_idx = 0
        self.categories = [("STATUS", "基本ステータス"), ("BONUS", "装備の加護"), ("QUIT", Text.UI.QUIT)]
        self._back_dialog = None

    @property
    def is_active(self): return game_state["status_active"]
    @is_active.setter
    def is_active(self, v):
        game_state["status_active"] = v
        if v:
            # mode は呼び出し元が事前にセットする（未設定なら STATUS）
            if self.mode not in ("STATUS", "QUESTS", "BONUS", "MENU"):
                self.mode = "STATUS"
            
            if self.mode in ("MENU", "STATUS", "BONUS"):
                # カテゴリ一覧から選ぶメニュー表示
                self.categories = [("STATUS", "基本ステータス"), ("BONUS", "装備の加護"), ("QUIT", Text.UI.QUIT)]
                if self.mode == "MENU" or self.mode == "STATUS":
                    self.mode = "STATUS"
                    self.cursor_idx = 0
                elif self.mode == "BONUS":
                    self.cursor_idx = 1
            else:
                # クエストなど詳細画面へ直行（左列は「もどる」のみ）
                self.categories = [("QUIT", Text.UI.QUIT)]
                self.cursor_idx = 0
            print(f"[UI] Open StatusDialog (Mode: {self.mode})")
        else:
            # 閉じたら次回のために STATUS に戻す
            self.mode = "STATUS"
            print(f"[UI] Close StatusDialog")
            game_state["dialog_just_closed"] = True

    def _close_back(self):
        game_state["status_active"] = False
        if self._back_dialog:
            self._back_dialog.is_active = True
        else:
            game_state["dialog_just_closed"] = True

    def handle_events(self, events, player=None):
        if not self.is_active: return
        from constants import KEY_CANCEL, KEY_CONFIRM, KEY_MENU, KEY_MOVE_UP, KEY_MOVE_DOWN
        for event in events:
            if event.type == pygame.KEYDOWN:
                if len(self.categories) > 1:
                    # 複数項目がある（カテゴリ一覧）の場合は、上下キーでカーソルと詳細表示（mode）を連動させる
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
                        # 決定またはキャンセルで閉じる
                        self._close_back()
                else:
                    # 直接詳細画面を開いた（categoriesが1つだけ）の場合は、どのキーでも閉じる
                    if event.key in (KEY_CANCEL, KEY_CONFIRM, KEY_MENU):
                        self._close_back()

    def draw(self, screen, player):
        if not self.is_active: return
        draw_dialog_frame(screen, self.x, self.y, self.width, self.height)
        
        # 境界線
        separator_x = self.x + 240
        pygame.draw.line(screen, (80, 100, 120), (separator_x, self.y + 30), (separator_x, self.y + self.height - 30), 2)

        # --- 左側：カテゴリ ---
        for i, (code, label) in enumerate(self.categories):
            y_pos = self.y + 60 + i * 45
            color = (255, 255, 255)
            
            # カーソルが合っている、または唯一の項目の場合はハイライト
            is_highlighted = (len(self.categories) == 1) or (i == self.cursor_idx)
            
            if is_highlighted:
                color = (255, 255, 100)
                pygame.draw.rect(screen, (60, 70, 90), (self.x + 20, y_pos - 5, 200, 40), border_radius=5)
                screen.blit(self.font.render(">", True, color), (self.x + 35, y_pos))
            
            screen.blit(self.font.render(label, True, color), (self.x + 65, y_pos))

        # --- 右側：内容 ---
        content_x, content_y = separator_x + 40, self.y + 40
        cw = self.width - (separator_x - self.x) - 80
        
        if self.mode == "STATUS":
            weapon_inst = player._find_equip_inst(player.weapon_inventory, player.equipped_weapon)
            armor_inst = player._find_equip_inst(player.armor_inventory, player.equipped_armor)
            shield_inst = player._find_equip_inst(player.shield_inventory, player.equipped_shield)
            
            # 各呪いによる減少値の計算
            # 1. HP
            hp_reduction = 0
            if "hp" in getattr(player, "cursed_stats", []):
                hp_bonus = 0
                if armor_inst: hp_bonus += armor_inst.get_stat("hp_bonus", 0)
                if shield_inst: hp_bonus += shield_inst.get_stat("hp_bonus", 0)
                raw_max_hp = int(player._base_max_hp + hp_bonus)
                hp_reduction = raw_max_hp - player.max_hp

            # 2. 攻撃力
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

            # 3. 防御力
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

            # 4. 回避率
            eva_reduction = 0
            if "evasion" in getattr(player, "cursed_stats", []):
                from constants import PLAYER_EVASION
                eva_base = PLAYER_EVASION
                eva_bonus = 0
                for inv, eid in [(player.weapon_inventory, player.equipped_weapon), (player.armor_inventory, player.equipped_armor), (player.shield_inventory, player.equipped_shield)]:
                    inst = player._find_equip_inst(inv, eid)
                    if inst:
                        val = inst.get_stat("eva_bonus", inst.get_stat("block_chance", 0))
                        if isinstance(val, float) and val < 1.0:
                            eva_bonus += val * 100
                        else:
                            eva_bonus += val
                raw_evasion = int(eva_base + eva_bonus)
                eva_reduction = raw_evasion - player.eva_bonus

            # カッコ書き表示テキストの作成
            hp_str = f"HP  ：{player.hp} / {player.max_hp}"
            if hp_reduction > 0:
                hp_str += f" (-{hp_reduction})"

            atk_str = f"攻撃力：{player.total_attack}"
            if atk_reduction > 0:
                atk_str += f" (-{atk_reduction})"

            def_str = f"防御力：{player.total_defense}"
            if def_reduction > 0:
                def_str += f" (-{def_reduction})"

            eva_str = f"回避率：{player.eva_bonus}%"
            if eva_reduction > 0:
                eva_str += f" (-{eva_reduction}%)"

            lines = [
                f"【基本ステータス】",
                f"ランク：{player.guild_rank} (GP:{player.guild_point})",
                hp_str,
                atk_str,
                def_str,
                eva_str,
                "",
                f"【装備中】",
                f"武器：{weapon_inst.get_name() if weapon_inst else 'なし'}",
                f"鎧  ：{armor_inst.get_name() if armor_inst else 'なし'}",
                f"盾  ：{shield_inst.get_name() if shield_inst else 'なし'}",
            ]
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
            total_eva = get_total_bonus("eva_bonus")
            total_acc_close = get_total_bonus("accuracy_bonus_close")
            # total_acc_ranged は将来実装予定のため非表示
            total_crit = get_total_bonus("crit_rate")
            total_block_close = get_total_bonus("block_chance_close")
            total_block_ranged = get_total_bonus("block_chance_ranged")
            total_stave = get_total_bonus("magic_stave_bonus")
            total_regen = get_total_bonus("regen_bonus")
            total_aggro = get_total_bonus("aggro_mod")
            total_stupidity = get_total_bonus("stupidity")
            total_penetration = get_total_bonus("armor_penetration")

            total_fire_dmg = get_total_bonus("magic_fire_damage")
            total_fire_range = get_total_bonus("magic_fire_range")
            total_heal_ratio = get_total_bonus("magic_heal_ratio")
            total_knockback = get_total_bonus("magic_knockback_damage")
            total_invincible = get_total_bonus("magic_invincible_turns")

            def format_val(val):
                if val % 1 == 0:
                    val_str = str(int(val))
                else:
                    val_str = str(round(val, 2))
                return f"+{val_str}" if val > 0 else val_str

            # --- 左列: 基本ボーナス ---
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
            if total_eva != 0:
                val = total_eva * 100 if isinstance(total_eva, float) and total_eva < 1.0 else total_eva
                left_lines.append(f"回避率    {format_val(val)}%")
                has_any_bonus = True
            if total_acc_close != 0:
                left_lines.append(f"近接命中  {format_val(total_acc_close)}")
                has_any_bonus = True
            if total_crit != 0:
                val = total_crit * 100 if isinstance(total_crit, float) and total_crit < 1.0 else total_crit
                left_lines.append(f"会心率    {format_val(val)}%")
                has_any_bonus = True
            if total_block_close != 0:
                val = total_block_close * 100 if isinstance(total_block_close, float) and total_block_close < 1.0 else total_block_close
                left_lines.append(f"近接ガード {format_val(val)}%")
                has_any_bonus = True
            if total_block_ranged != 0:
                val = total_block_ranged * 100 if isinstance(total_block_ranged, float) and total_block_ranged < 1.0 else total_block_ranged
                left_lines.append(f"遠隔ガード {format_val(val)}%")
                has_any_bonus = True
            if total_stave != 0:
                pass # stave_bonus は魔法加護（右列）に移動
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

            # --- 右列: 魔法加護 ---
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

            if not has_magic_bonus:
                right_lines.append("なし")

            if not has_any_bonus and not has_magic_bonus:
                screen.blit(self.font.render("適用中の装備の加護はありません。", True, (200, 200, 200)), (content_x, content_y))
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
                lines.append("現在受注している依頼はありません。")
            else:
                for q in player.active_quests:
                    prog = ""
                    if q.get("type") == "hunt":
                        prog = f"({player.quest_tokens.get(q.get('target_key'), 0)}/{q.get('amount') or 0})"
                    elif q.get("type") == "delivery":
                        count = player._count_owned_items(q.get('target_key'))
                        prog = f"({count}/{q.get('amount') or 0})"
                    
                    # 昇級試験の場合は進捗を「未達成/達成」のような形にするか、あるいはprogを隠す
                    if q.get("is_rank_up"):
                        prog = "" # タイトルに「冒険者の証の回収」とあるので、進捗数値は不要
                    
                    reward = q.get("reward_gold", 0)
                    lines.append(f"・{q.get('title')}")
                    if prog:
                        lines.append(f"  進捗: {prog} {q.get('target_name', '')}")
                    lines.append(f"  報酬: {reward} G")
            
            draw_text_wrapped(screen, self.font, "\n".join(lines), content_x, content_y, cw)
        
        else: # MENU
            draw_text_wrapped(screen, self.font, Text.UI.STATUS_MENU_HINT, content_x, content_y, cw, color=(150, 150, 150))

class EnhanceDialog(InventoryDialog):
    """鍛冶屋での強化メニュー（武器・鎧限定）"""
    @property
    def is_active(self): return game_state["enhance_active"]
    @is_active.setter
    def is_active(self, v):
        game_state["enhance_active"] = v
        if v: self.cursor_idx = 0
        else: game_state["dialog_just_closed"] = True
    def handle_events(self, events, player=None):
        if not self.is_active: return
        from constants import KEY_CONFIRM
        # 基本的な移動操作などは親クラス (InventoryDialog) を呼ぶ
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

    def __init__(self, screen_width, screen_height):
        super().__init__(screen_width, screen_height)
        self.selection_dialog = None # OreSelectionDialog への参照

    def setup(self, player, dialog, ore_selection_dialog):
        """鍛冶屋のコールバックと関連ダイアログを設定する"""
        from systems.item_handler import make_enhance_callback
        self.on_select = make_enhance_callback(player, dialog, self)
        self.selection_dialog = ore_selection_dialog

    def update_items_from_player(self, player):
        new_items, new_data = [], []
        for inst in player.weapon_inventory:
            new_items.append(inst.get_name())
            new_data.append(("weapon", inst.iid))
        for inst in player.armor_inventory:
            new_items.append(Text.UI.ENHANCE_ARMOR_LABEL.format(name=inst.get_name()))
            new_data.append(("armor", inst.iid))
        for inst in getattr(player, "shield_inventory", []):
            new_items.append(Text.UI.ENHANCE_SHIELD_LABEL.format(name=inst.get_name()))
            new_data.append(("shield", inst.iid))
        
        new_items.append(Text.UI.QUIT)
        new_data.append(("cancel", None))

        self.items, self.item_data = new_items, new_data

    def draw(self, screen, player=None):
        if not self.is_active: return
        super().draw(screen, player)
        title = self.font.render(Text.UI.WHICH_TO_ENHANCE, True, (255, 200, 100))
        screen.blit(title, (self.x + 40, self.y + 10))

class ShopDialog(BaseListDialog):
    """NPC商店での売買を行うダイアログ"""
    STATE_KEY = "shop_active"

    def __init__(self, screen_width, screen_height):
        super().__init__(screen_width, screen_height)
        self.row_height = 36
        self.mode = "BUY"  # "BUY" or "SELL"
        self.shop_name = ""
        self.stock_ref = []

    def open_shop(self, shop_name, stock):
        self.shop_name = shop_name; self.stock_ref = stock; self.mode = "BUY"
        self.refresh_items_from_stock(); self.is_active = True

    def refresh_items_from_stock(self):
        self.items = []
        for s in self.stock_ref: self.items.append((s["key"], s["type"], s["name"], s["price"], s["count"]))
        self.items.append(("cancel", "cancel", Text.UI.SHOP_CANCEL, 0, 1))

    def setup_sell_mode(self, player):
        self.mode = "SELL"; self.cursor_idx = 0; self.items = []
        from constants import CONSUMABLE_DATA, WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, STAVE_DATA
        
        def get_sell_price(data):
            """selling_price が設定されていればそれを、なければ price // 3 を返す"""
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
        for eq in getattr(player, "lantern_inventory", []):
            sell_data = {}
            for k, v in CONSUMABLE_DATA.items():
                if v.get("effect") == "lantern" and v.get("lantern_key", "basic") == eq.key:
                    sell_data = v
                    break
            self.items.append((eq.iid, "lantern_inst", eq.get_name(), get_sell_price(sell_data), 1, eq.key))
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
                    elif itype == "stave": from components.sprites.player import StaveInstance; player.stave_inventory.append(StaveInstance(key_or_iid))
                    elif itype == "consumable": player.add_item_to_inventory(key_or_iid)
                    self.stock_ref[self.cursor_idx]["count"] -= 1
                    if self.stock_ref[self.cursor_idx]["count"] <= 0: self.stock_ref.pop(self.cursor_idx)
                    play_sfx(SOUND_PURCHASE); self.refresh_items_from_stock(); self.cursor_idx = min(self.cursor_idx, len(self.items)-1); dialog.text = Text.Items.BOUGHT.format(name=name); dialog.is_active = True
                confirm_dialog.on_yes = do_buy; confirm_dialog.is_active = True
        else: # SELL
            if (itype == "weapon_inst" and key_or_iid == player.equipped_weapon) or (itype == "armor_inst" and key_or_iid == player.equipped_armor) or (itype == "shield_inst" and key_or_iid == player.equipped_shield) or (itype == "lantern_inst" and key_or_iid == getattr(player, "equipped_lantern", None)):
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
                    elif itype == "lantern_inst": player.remove_lantern_by_iid(key_or_iid); ok = True
                    if ok: player.coin += price; play_sfx(SOUND_PURCHASE); dialog.text = Text.Items.SOLD.format(name=name, price=price); dialog.auto_close_timer = 60
                    self.setup_sell_mode(player); self.cursor_idx = min(self.cursor_idx, len(self.items)-1); dialog.is_active = True
                confirm_dialog.on_yes = do_sell; confirm_dialog.is_active = True

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
                # 装備中判定
                is_eq = False
                iid, itype = item[0], item[1]
                if itype == "weapon_inst" and player.equipped_weapon == iid: is_eq = True
                elif itype == "armor_inst" and player.equipped_armor == iid: is_eq = True
                elif itype == "shield_inst" and player.equipped_shield == iid: is_eq = True
                elif itype == "lantern_inst" and player.equipped_lantern == iid: is_eq = True
                
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

            # スクロールインジケーター
            if len(self.items) > self.view_size:
                indicator_x = sep_x - 30
                if start > 0:
                    pygame.draw.polygon(screen, (200, 200, 200), [(indicator_x, self.y + 70), (indicator_x - 8, self.y + 80), (indicator_x + 8, self.y + 80)])
                if start + self.view_size < len(self.items):
                    pygame.draw.polygon(screen, (200, 200, 200), [(indicator_x, self.y + self.height - 70), (indicator_x - 8, self.y + self.height - 80), (indicator_x + 8, self.y + self.height - 80)])
        if 0 <= self.cursor_idx < len(self.items):
            selected = self.items[self.cursor_idx]
            itype = selected[1].replace("_inst", "")
            # SELLモードで装備インスタンスの場合は6番目の要素（マスターデータのキー）を使用する
            master_key = selected[5] if len(selected) > 5 else selected[0]
            
            from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, STAVE_DATA, CONSUMABLE_DATA
            catalog = {"weapon": WEAPON_DATA, "armor": ARMOR_DATA, "shield": SHIELD_DATA, "stave": STAVE_DATA, "consumable": CONSUMABLE_DATA}
            info = catalog.get(itype, {}).get(master_key, {})
            lines = [f"【{selected[2]}】", ""]
            if itype == "shield":
                if info.get("block_chance_close", 0) != 0: lines.append(f"近距離回避率: {int(info['block_chance_close']*100)}%")
                if info.get("block_chance_ranged", 0) != 0: lines.append(f"遠距離回避率: {int(info['block_chance_ranged']*100)}%")
                # 特定の回避率がない場合は基礎回避率を表示
                if info.get("block_chance_close", 0) == 0 and info.get("block_chance_ranged", 0) == 0:
                    if info.get("block_chance", 0) != 0: lines.append(f"回避率: {int(info['block_chance']*100)}%")
                if info.get("hp_bonus", 0) != 0: lines.append(f"最大HP: +{info['hp_bonus']}")
            elif itype == "weapon":
                if info.get("attack_bonus", 0) != 0: lines.append(f"攻撃力: +{info['attack_bonus']}")
                if info.get("hp_bonus", 0) != 0: lines.append(f"最大HP: +{info['hp_bonus']}")
            elif itype == "armor":
                if info.get("defense_bonus", 0) != 0: lines.append(f"防御力: +{info['defense_bonus']}")
                if info.get("hp_bonus", 0) != 0: lines.append(f"最大HP: +{info['hp_bonus']}")
            else: # その他（巻物やポーションなど）
                if info.get("attack_bonus", 0) != 0: lines.append(f"攻撃力: +{info['attack_bonus']}")
                if info.get("defense_bonus", 0) != 0: lines.append(f"防御力: +{info['defense_bonus']}")
                if info.get("hp_bonus", 0) != 0: lines.append(f"最大HP: +{info['hp_bonus']}")
            lines.append(""); lines.append(info.get("describe", "詳細情報はありません。") if selected[1] != "cancel" else "店を出ます。")
            draw_text_wrapped(screen, self.font, "\n".join(lines), sep_x + 30, self.y + 80, self.width // 2 - 60, color=(220, 230, 240))

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
            ("mode_deposit", "action", Text.UI.WAREHOUSE_DEPOSIT, "アイテムを預けます。", False),
            ("mode_withdraw", "action", Text.UI.WAREHOUSE_WITHDRAW, "アイテムを引き出します。", False),
            ("cancel", "cancel", Text.UI.QUIT, "店を出ます。", False)
        ]

    def setup_deposit_mode(self, player):
        from constants import CONSUMABLE_DATA
        self.mode = "DEPOSIT"; self.cursor_idx = 0; self.items = []
        # (id/idx, type, display_name, data_obj, is_equipped)
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
        for eq in player.lantern_inventory:
            is_eq = (eq.iid == player.equipped_lantern)
            self.items.append((eq.iid, "lantern_inst", eq.get_name(), eq, is_eq))
        
        self.items.append((-1, "back", Text.UI.QUIT, None, False))

    def setup_withdraw_mode(self, player):
        self.mode = "WITHDRAW"; self.cursor_idx = 0; self.items = []
        for idx, w in enumerate(player.warehouse_items):
            itype = w.get("type"); data = w.get("data")
            from components.sprites.player import EquipInstance, StaveInstance
            temp = StaveInstance.from_dict(data) if itype == "stave_inst" else EquipInstance.from_dict(data) if "inst" in itype else None
            name = temp.get_name_with_charges() if itype == "stave_inst" else temp.get_name() if temp else ""
            if not temp: from constants import CONSUMABLE_DATA; name = CONSUMABLE_DATA.get(data, {}).get("name", data)
            self.items.append((idx, itype, name, data, False))
        self.items.append((-1, "back", Text.UI.QUIT, None, False))

    def handle_events(self, events, player, confirm_dialog, dialog):
        if not self.is_active: return
        from systems.audio_manager import play_sfx
        from constants import SOUND_CURSOR_MOVE, SOUND_SELECT, SOUND_CANCEL, KEY_MOVE_UP, KEY_MOVE_DOWN, KEY_CANCEL, KEY_CONFIRM
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == KEY_CANCEL:
                    play_sfx(SOUND_CANCEL); 
                    if self.mode == "MAIN": self.is_active = False
                    else: self.setup_main_menu()
                elif event.key == KEY_MOVE_UP:
                    if self.cursor_idx > 0: 
                        play_sfx(SOUND_CURSOR_MOVE); self.cursor_idx -= 1
                    else:
                        # ループ
                        self.cursor_idx = len(self.items) - 1
                        play_sfx(SOUND_CURSOR_MOVE)
                elif event.key == KEY_MOVE_DOWN:
                    if self.cursor_idx < len(self.items) - 1: 
                        play_sfx(SOUND_CURSOR_MOVE); self.cursor_idx += 1
                    else:
                        # ループ
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
                dialog.text = "装備中のアイテムは預けられません。\n装備を外してから再度お試しください。"
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
                    elif itype == "lantern_inst": player.remove_lantern_by_iid(_id)
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
        if itype in ("weapon_inst", "armor_inst", "shield_inst", "lantern_inst"):
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
                    elif itype == "lantern_inst": player.lantern_inventory.append(inst)
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
                if is_equipped:
                    color = (130, 130, 130) # 装備中はグレー
                
                if i == self.cursor_idx:
                    pygame.draw.rect(screen, (60, 70, 90), (self.x + 20, y_pos - 5, self.width // 2 - 40, self.row_height), border_radius=5)
                    screen.blit(self.font.render(">", True, (255, 255, 100)), (self.x + 35, y_pos))
                    if not is_equipped:
                        color = (255, 255, 100) # 選択中は黄色（装備中でない場合）
                
                name = item[2]
                if is_equipped:
                    name = f"[E] {name}"
                
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
                    info_lines.append("※装備中のため預けられません。")
                else:
                    info_lines.append("倉庫に預けます。" if self.mode == "DEPOSIT" else "倉庫から引き出します。")
                
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
            ("DEPOSIT",  100,  Text.UI.BANK_DEPOSIT_100,   "100 G を銀行に預けます。"),
            ("DEPOSIT",  1000, Text.UI.BANK_DEPOSIT_1000,  "1000 G を銀行に預けます。"),
            ("DEPOSIT",  -1,   Text.UI.BANK_DEPOSIT_ALL,   "所持金を全額銀行に預けます。"),
            ("WITHDRAW", 100,  Text.UI.BANK_WITHDRAW_100,  "100 G を引き出します。"),
            ("WITHDRAW", 1000, Text.UI.BANK_WITHDRAW_1000, "1000 G を引き出します。"),
            ("WITHDRAW", -1,   Text.UI.BANK_WITHDRAW_ALL,  "銀行残高を全額引き出します。"),
            ("CANCEL",   0,    Text.UI.QUIT,               "銀行を出ます。"),
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


# 🌀 TELEPORT_DIALOG
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

    def get_title(self):
        return "テレポート屋（転移）"

    def get_header_right(self, player):
        return Text.UI.GOLD_LABEL.format(coin=player.coin)

    def on_activated(self):
        # 活性化時に目的地リストを構築
        from systems.game_state import game_state
        player = game_state.get("player_ref")
        if not player: return
        self.setup_destinations(player)

    def setup_destinations(self, player):
        from constants import DUNGEON_IMAGES, TELEPORT_MONEY_PER_FLOOR, TELEPORT_REQUIRED_ITEM, TELEPORT_RETURN_VILLAGE_COST
        self.items = []
        self.mode = "SELECT"
        self.required_item = TELEPORT_REQUIRED_ITEM

        if player.current_floor == 0:
            # 村にいる：到達済みの休憩所へ
            for f_str, info in DUNGEON_IMAGES.items():
                if not f_str.isdigit(): continue
                f_lv = int(f_str)
                if f_lv == 0: continue
                # 固定マップ(map指定あり)かつ到達済み
                if f_lv <= player.max_reached_floor and info.get("map"):
                    name = f"{f_lv}F 休憩所"
                    self.items.append({"floor": f_lv, "name": name, "cost": f_lv * TELEPORT_MONEY_PER_FLOOR, "type": "warp"})
        else:
            # 休憩所にいる：村(0F)へ帰還
            self.items.append({"floor": 0, "name": "村（帰還）", "cost": TELEPORT_RETURN_VILLAGE_COST, "type": "return"})
        
        if not self.items:
            return # 何もなければQUITも追加しない（openがFalseを返すようにする）

        self.items.append({"floor": -1, "name": Text.UI.QUIT, "cost": 0, "type": "cancel"})

    def get_item_label(self, item, idx):
        return item["name"]

    def get_detail_lines(self, player):
        if not self.items or self.cursor_idx >= len(self.items): return []
        item = self.items[self.cursor_idx]
        if item["type"] == "cancel": return ["店を出ます。"]
        
        from systems.guild import GuildSystem
        guild = GuildSystem()
        f_lv = item["floor"]
        req_rank = guild.get_required_rank_for_floor(f_lv) if f_lv > 0 else "F"
        
        lines = [f"【{item['name']}】", ""]
        lines.append(f"消費コイン: {item['cost']} G")
        
        if f_lv > 0:
            lines.append(f"到達可能ランク: {req_rank}")
            lines.append("")
            lines.append(f"地下 {f_lv} 階にある休憩所へ転移します。")
            lines.append("※強力な魔物の気配が漂っています。")
        else:
            lines.append("")
            lines.append("冒険者の拠点となる村へ帰還します。")
            lines.append("一度休息をとり、装備を整えましょう。")
        return lines

    def open(self, player):
        # player参照を保持し、リストを構築してからアクティブにする
        self.setup_destinations(player)
        if not self.items: return False
        self.is_active = True
        return True

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
            self.mode = "SELECT"
            return None
        elif res == "confirm":
            selected = self.items[self.cursor_idx]
            if selected["type"] == "cancel":
                play_sfx(SOUND_CANCEL)
                self.is_active = False
                return None
                
            self.target_floor = selected["floor"]
            self.cost_money = selected["cost"]
            
            # 所持金・アイテムチェック
            from systems.game_state import game_state
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
                    dialog.text = "テレポートには『転移の石』が必要です。"
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
        # 消耗品データに転移の石があるか
        for item in player.items:
            if item.get("key") == self.required_item:
                return True
        return False

    def _execute_teleport(self, player):
        from systems.dungeon import warp_with_pitfall
        from systems.game_state import game_state
        
        # 挨拶ダイアログを閉じる
        ui_el = game_state.get("ui_elements", {})
        if "dialog" in ui_el:
            ui_el["dialog"].is_active = False

        selected = self.items[self.cursor_idx]
        reason = selected.get("type", "teleport")

        # コインとアイテムを消費
        player.coin -= self.cost_money
        player.remove_item_by_key(self.required_item, 1)
        
        # 演出付き転移の開始
        warp_with_pitfall(self.target_floor, player, spawn_reason=reason)
        self.is_active = False

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
            screen.blit(self.font.render(f"{item['cost']} G", True, color), (sep_x - 110, y_pos))




def draw_minimap(screen, dungeon, player):
    """
    探索済みのタイルを表示するミニマップ（透過オーバーレイ）を描画する。
    """
    from systems.game_state import is_paused
    if not dungeon or not getattr(dungeon, "show_map", True) or is_paused(): return
    if dungeon.current_floor == 0: return # 村では表示しない
    
    # 1タイルのサイズ (ドット数)
    tile_dot = 5
    map_w = dungeon.map_width * tile_dot
    map_h = dungeon.map_height * tile_dot
    
    # 画面右上に配置するためのオフセット (3タイル分のマージンを開ける)
    from constants import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE
    off_x = SCREEN_WIDTH - map_w - (TILE_SIZE * 3)
    off_y = 120 
    
    # 透過サーフェスの作成
    map_surf = pygame.Surface((map_w, map_h), pygame.SRCALPHA)
    
    # --- 背景と枠線 ---
    # 少し厚みのある背景色 (ダークネイビー系)
    map_surf.fill((10, 15, 30, 180)) 
    # 境界線を描画
    pygame.draw.rect(map_surf, (80, 100, 150, 255), (0, 0, map_w, map_h), 1)
    
    # --- 1. 探索済みタイル（地形）の描画 ---
    for y in range(dungeon.map_height):
        for x in range(dungeon.map_width):
            if not dungeon.revealed_tiles[y][x]: continue
            
            tile = dungeon.map_data[y][x]
            rect = (x * tile_dot, y * tile_dot, tile_dot, tile_dot)
            
            if tile == 1: # 部屋の床
                # 落ち着いた青色
                pygame.draw.rect(map_surf, (60, 80, 140, 220), rect)
            elif 4 <= tile <= 6: # 通路
                # 暗めのグレー
                pygame.draw.rect(map_surf, (80, 80, 90, 220), rect)
            elif tile in (2, 3): # 階段 (上/下)
                # 階段は目立つ黄色
                pygame.draw.rect(map_surf, (255, 255, 0, 255), rect)

    # --- 2. 敵の表示 ---
    for e in dungeon.enemies:
        if e.is_dead or getattr(e, "is_static", False): continue
        gx, gy = int(e.x // dungeon.tile_size), int(e.y // dungeon.tile_size)
        if 0 <= gx < dungeon.map_width and 0 <= gy < dungeon.map_height:
            if dungeon.revealed_tiles[gy][gx]:
                # 敵は鮮やかな赤
                pygame.draw.rect(map_surf, (255, 50, 50, 255), (gx * tile_dot, gy * tile_dot, tile_dot, tile_dot))

    # --- 3. プレイヤーの表示 ---
    px, py = int(player.x // dungeon.tile_size), int(player.y // dungeon.tile_size)
    if 0 <= px < dungeon.map_width and 0 <= py < dungeon.map_height:
        # プレイヤーは純白
        pygame.draw.rect(map_surf, (255, 255, 255, 255), (px * tile_dot, py * tile_dot, tile_dot, tile_dot))
    
    # 描画
    screen.blit(map_surf, (off_x, off_y))

def draw_all_ui(screen, player, dialog, confirm_dialog, inventory_dialog, status_dialog, enhance_dialog, item_action_dialog, ore_selection_dialog, shop_dialog, stave_selection_dialog, guild_dialog=None, warehouse_dialog=None, bank_dialog=None, menu_dialog=None, equip_dialog=None, stave_inv_dialog=None, event_inv_dialog=None, teleport_dialog=None, dungeon=None, events=None, **kwargs):
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

    # アクション系ダイアログは最前面（メッセージウィンドウの手前）に描画
    item_action_dialog.draw(screen)
    ore_selection_dialog.draw(screen)
    stave_selection_dialog.draw(screen)
    if teleport_dialog:
        teleport_dialog.draw(screen, player)
    
    dialog.update()
    dialog.draw(screen)
    confirm_dialog.draw(screen)

    cutscene_manager = kwargs.get("cutscene_manager")
    if cutscene_manager and cutscene_manager.is_active:
        cutscene_manager.update()
        cutscene_manager.draw(screen)

    # 最後にミニマップを最前面に描画
    if dungeon:
        draw_minimap(screen, dungeon, player)



