import pygame
import random
from systems.game_state import game_state
from systems.resources import (
    font_small, font_small_bold, font_medium, font_large,
    font_dialog, font_menu, font_hud
)
from constants import (
    KEY_MOVE_UP, KEY_MOVE_DOWN, KEY_MOVE_LEFT, KEY_MOVE_RIGHT,
    KEY_CONFIRM, KEY_CANCEL, KEY_INVENTORY, GAME_TITLE, GAME_SUBTITLE,
    UI_SETTINGS, PCT_STAT_KEYS
)
import os
from wordings import Text

EQUIP_STAT_LABEL_MAP = {
    "attack_bonus": "攻撃力",
    "defense_bonus": "防御力",
    "hp_bonus": "最大HP",
    "dex_bonus": "器用さ",
    "crit_bonus": "会心率",
    "block_chance_close": "近距離回避率",
    "block_chance_ranged": "遠距離回避率",
    "aggro_mod": "感知補正",
    "armor_penetration": Text.UI.STAT_ARMOR_PENETRATION,
    "stupidity": Text.UI.STAT_CONFUSION_ICON,
    "backstab_crit_bonus": "背後会心",
    "flank_backstab": "側面背後",
    "stupidity_proc_chance": "混乱発動率",
    "stupidity_proc_amount": "混乱上昇量"
}

EQUIP_MAGIC_LABEL_MAP = {
    "magic_fire_damage":    "炎ダメージ",
    "magic_fire_range":     "炎射程",
    "magic_heal_ratio":     "回復量",
    "magic_knockback_damage":"吹飛ダメージ",
    "magic_invincible_turns":"無敵ターン",
    "magic_stave_bonus":     "杖回数",
    "magic_light_stave_bonus": "燈杖回",
    "magic_barrier_turns":     "障壁ターン",
}

# 装備に付与可能なスキルカテゴリ（表示用）
EQUIP_SKILL_CATEGORY_MAP = {
    "lifesteal": ("lifesteal_chance", "lifesteal_ratio"),
    "counter":   ("counter_proc_chance", "counter_damage_ratio"),
    "stun":      ("stun_proc_chance", "stun_duration"),
    "backstab":  ("backstab_crit_bonus", "flank_backstab"),
    "confusion": ("stupidity_proc_chance", "stupidity_proc_amount"),
}
EQUIP_SKILL_LABEL_MAP = {
    "lifesteal": "ライフスティール",
    "counter":   "カウンター",
    "stun":      "スタン",
    "backstab":  "バックスタブ強化",
    "confusion": "混乱",
}

def _get_equipped_set_keys(player):
    """装備中の武器・鎧・盾のキーをセットで返す"""
    keys = set()
    if player and player.equipped_weapon:
        inst = player._find_equip_inst(player.weapon_inventory, player.equipped_weapon)
        if inst: keys.add(inst.key)
    if player and player.equipped_armor:
        inst = player._find_equip_inst(player.armor_inventory, player.equipped_armor)
        if inst: keys.add(inst.key)
    if player and player.equipped_shield:
        inst = player._find_equip_inst(player.shield_inventory, player.equipped_shield)
        if inst: keys.add(inst.key)
    return keys


def get_player_skill_names(player):
    """プレイヤーが発動中のスキルカテゴリ名リストを返す"""
    names = []
    if not player:
        return names

    equipped_keys = _get_equipped_set_keys(player)
    ASSASSIN_SET = {"assassin_dagger", "assassin_light_armor", "assassin_buckler"}
    HOLY_SET = {"holy_sword", "holy_armor", "holy_shield"}
    has_assassin_set = ASSASSIN_SET.issubset(equipped_keys)
    has_holy_set = HOLY_SET.issubset(equipped_keys)

    if has_holy_set and getattr(player, "total_lifesteal_chance", 0):
        names.append(EQUIP_SKILL_LABEL_MAP.get("lifesteal", "lifesteal"))
    if getattr(player, "total_counter_proc_chance", 0):
        names.append(EQUIP_SKILL_LABEL_MAP.get("counter", "counter"))
    if getattr(player, "total_stun_proc_chance", 0):
        names.append(EQUIP_SKILL_LABEL_MAP.get("stun", "stun"))
    if has_assassin_set and (getattr(player, "total_backstab_crit_bonus", 0) or getattr(player, "total_flank_backstab", 0)):
        names.append(EQUIP_SKILL_LABEL_MAP.get("backstab", "backstab"))
    if has_assassin_set and getattr(player, "total_stupidity_proc_chance", 0):
        names.append(EQUIP_SKILL_LABEL_MAP.get("confusion", "confusion"))
    return names

def format_stat_value(val):
    if val % 1 == 0:
        val_str = str(int(val))
    else:
        val_str = str(round(val, 2))
    return f"+{val_str}" if val > 0 else val_str

def draw_stat_bar(screen, x, y, value, stat_key, bar_width=100, bar_height=10, font=None, ratio=None, display_ratio=None):
    """ステータスバーを描画する（長さ＋色＋ランク文字）
    
    Args:
        screen: 描画先サーフェス
        x, y: 描画位置
        value: ステータスの実値（表示用）
        stat_key: STAT_RANGESのキー
        bar_width: バーの最大幅(px)
        bar_height: バーの高さ(px)
        font: ランク文字描画用フォント（Noneならfont_small）
        ratio: バーの割合を直接指定（0.0-1.0）。指定時はvalueは表示専用。ランク/色もこのratioで判定。
        display_ratio: バーの塗り幅に使う割合。指定時、ランク/色はratioを使用し、バーの長さのみdisplay_ratioを使用。
    """
    from constants import STAT_RANGES, STAT_RANK_COLORS, get_stat_rank
    
    # マイナス値の場合は特殊表示
    if value < 0:
        ratio = 0.0  # バーは空
        rank = "-"
        color = (100, 100, 110)  # グレー
    elif ratio is not None:
        # 百分率モード：ratioが直接指定された場合
        ratio = max(0.0, min(1.0, ratio))
        # 百分率を8等分してF-SSランク付け（100/8=12.5%刻み）
        percent = ratio * 100
        if percent >= 87.5:
            rank = "SS"
        elif percent >= 75:
            rank = "S"
        elif percent >= 62.5:
            rank = "A"
        elif percent >= 50:
            rank = "B"
        elif percent >= 37.5:
            rank = "C"
        elif percent >= 25:
            rank = "D"
        elif percent >= 12.5:
            rank = "E"
        else:
            rank = "F"
        color = STAT_RANK_COLORS.get(rank, (255, 255, 255))
    else:
        r = STAT_RANGES.get(stat_key, {"min": 0, "max": 1})
        # バーの割合を算出（min〜maxで正規化）
        if r["max"] == r["min"]:
            ratio = 1.0 if value >= r["max"] else 0.0
        else:
            ratio = (value - r["min"]) / (r["max"] - r["min"])
        ratio = max(0.05, min(1.0, ratio))  # 最低5%は表示する
        
        # ランク判定
        rank = get_stat_rank(value, stat_key)
        color = STAT_RANK_COLORS.get(rank, (255, 255, 255))
    
    # 背景バー（暗い灰色）
    bg_rect = pygame.Rect(x, y, bar_width, bar_height)
    pygame.draw.rect(screen, (40, 40, 50), bg_rect, border_radius=3)
    
    # 値バー（ランク色）- マイナス値の場合は塗らない
    fill_ratio = display_ratio if display_ratio is not None else ratio
    if fill_ratio > 0:
        fill_w = int(bar_width * max(0.0, min(1.0, fill_ratio)))
        fill_rect = pygame.Rect(x, y, fill_w, bar_height)
        pygame.draw.rect(screen, color, fill_rect, border_radius=3)
    
    # 枠線
    pygame.draw.rect(screen, (80, 80, 90), bg_rect, width=1, border_radius=3)
    
    return rank  # 呼び出し側で使用するためランクを返す


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
    
    # サブタイトル
    subtitle_color = (200, 200, 220)
    draw_text_wrapped(screen, font_medium, GAME_SUBTITLE, 0, 230, screen.get_width(), align_h='center', color=subtitle_color)
    
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


class StateKeyMixin:
    """STATE_KEY を持つダイアログ共通の is_active プロパティを提供する Mixin。
    STATE_KEY クラス変数を定義し、必要に応じて _on_open() / _on_close() をオーバーライドする。
    """
    STATE_KEY = ""

    @property
    def is_active(self):
        return game_state.get(self.STATE_KEY, False)

    @is_active.setter
    def is_active(self, v):
        game_state[self.STATE_KEY] = v
        if v:
            print(f"[UI] Open {self.__class__.__name__}")
            self._on_open()
        else:
            print(f"[UI] Close {self.__class__.__name__}")
            game_state["dialog_just_closed"] = True
            self._on_close()

    def _on_open(self):
        """open 時フック。サブクラスでオーバーライド可。"""
        if hasattr(self, "cursor_idx"):
            self.cursor_idx = 0

    def _on_close(self):
        """close 時フック。サブクラスでオーバーライド可。"""
        pass


class BaseListDialog(StateKeyMixin):
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

    def _on_open(self):
        print(f"[UI] Open {self.__class__.__name__} ({self.get_title()})")
        self.cursor_idx = 0
        self.on_activated()

    def on_activated(self): pass  # open 時フック（サブクラスでオーバーライド）

    def _close_back(self):
        """「もどる」: 親ダイアログがあればそれを再表示、なければ普通に閉じる"""
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
        """カーソル移動を処理し、'cancel'|'confirm'|None を返す"""
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
            # 画像の描画 (80x80に縮小して縦スペースを節約)
            img_path = self.get_item_image_path(self.items[self.cursor_idx], self.cursor_idx, player)
            if img_path:
                from systems.resources import load_image, scale_image_aspect
                img = load_image(img_path)
                if img:
                    if hasattr(self, "item_data") and self.cursor_idx < len(self.item_data):
                        itype, key_or_iid = self.item_data[self.cursor_idx]
                        if itype == "consumable":
                            from constants import CONSUMABLE_DATA
                            cdata = CONSUMABLE_DATA.get(key_or_iid, {})
                            tint = cdata.get("color_tint")
                            if tint:
                                img = img.copy()
                                w, h = img.get_size()
                                lower_rect = pygame.Rect(0, h // 2, w, h // 2)
                                img.fill((*tint, 255), rect=lower_rect, special_flags=pygame.BLEND_RGBA_MULT)
                    scaled_img = scale_image_aspect(img, 80, 80)
                    # 中央寄せにするための計算
                    img_w, img_h = scaled_img.get_size()
                    screen.blit(scaled_img, (sep_x + 30 + (80 - img_w) // 2, self.y + 50 + (80 - img_h) // 2))
                    detail_y_offset = 90

        lines = self.get_detail_lines(player)
        if lines:
            self.draw_right_panel(screen, player, sep_x, detail_y_offset)

    def draw_right_panel(self, screen, player, sep_x, detail_y_offset):
        lines = self.get_detail_lines(player)
        if lines:
            draw_text_wrapped(screen, self.font, "\n".join(lines),
                              sep_x + 30, self.y + 80 + detail_y_offset, self.width // 2 - 60, color=(220, 230, 240))

    def draw_equip_detail_right_panel(self, screen, inst, param_texts, desc, sep_x, detail_y_offset):
        """装備品の右パネルをステータスバー＋説明文で描画する共通メソッド。
        inst        : EquipInstance / StaveInstance（名前取得用、Noneなら名前行なし）
        param_texts : [(テキスト文字列, ...)] のリスト（フォールバック用）
        desc        : 説明文（str）
        sep_x       : 左右セパレータのx座標
        detail_y_offset : 画像の有無による縦オフセット
        """
        from constants import STAT_RANGES
        
        start_x = sep_x + 30
        start_y = self.y + 80 + detail_y_offset
        cw = self.width // 2 - 60
        line_h = 22  # バー行の高さ
        
        # バーで描画可能なステータスキー
        bar_stat_keys = {
            "attack_bonus", "defense_bonus", "hp_bonus",
            "crit_bonus", "block_chance_close", "block_chance_ranged",
            "armor_penetration", "aggro_mod", "stupidity",
        }
        
        # instからステータスを取得してバー描画
        bar_items = []  # (label, value, stat_key)
        text_items = []  # バーにできない項目（テキスト表示）
        # スキルの個別パラメータはスキル名でまとめて表示する
        SKILL_STAT_KEYS = {k for keys in EQUIP_SKILL_CATEGORY_MAP.values() for k in keys}

        if inst and hasattr(inst, "get_stat"):
            for k, label in EQUIP_STAT_LABEL_MAP.items():
                if k in SKILL_STAT_KEYS:
                    continue
                val = inst.get_stat(k, 0)
                # 強化ボーナスを加算（StaveInstanceの場合はenhanceがあってもget_enhance_bonusがない）
                if hasattr(inst, 'enhance') and inst.enhance > 0 and hasattr(inst, 'get_enhance_bonus'):
                    val += inst.get_enhance_bonus(k)
                if val:
                    if k in bar_stat_keys and k in STAT_RANGES:
                        # 百分率バー計算：基本値+最大ボーナスを100%とする
                        is_pct = k in PCT_STAT_KEYS
                        max_bonus = 0.10 if is_pct else 10
                        base_val = inst.get_stat(k, 0)  # 基本値（強化前）
                        max_val = base_val + max_bonus
                        if max_val > 0:
                            percent_ratio = val / max_val  # 0.0-1.0
                        else:
                            percent_ratio = 0.0
                        # bar_items: (label, 表示値, バー割合, stat_key)
                        bar_items.append((label, val, percent_ratio, k))
                    else:
                        is_pct = k in PCT_STAT_KEYS
                        val_to_use = val * 100 if is_pct and isinstance(val, float) else val
                        text_items.append(f"{label}: {format_stat_value(val_to_use)}%" if is_pct else f"{label}: {format_stat_value(val)}")
            # マジックステータス（バー非対応→テキスト表示）
            for mk, mlabel in EQUIP_MAGIC_LABEL_MAP.items():
                mval = inst.get_stat(mk, 0)
                if mval:
                    is_pct = mk in ("magic_fire_damage", "magic_heal_ratio", "magic_knockback_damage")
                    val_to_use = mval * 100 if is_pct and isinstance(mval, float) else mval
                    text_items.append(f"{mlabel}: {format_stat_value(val_to_use)}%" if is_pct else f"{mlabel}: {format_stat_value(mval)}")

        # バー描画（左半分: ラベル列、右半分: バー+ランク列+値）
        max_y = start_y
        half_w = cw // 2
        bar_w = half_w - 20  # ランク文字分のマージン
        bar_w = min(bar_w, 90)
        
        for i, (label, display_val, ratio, stat_key) in enumerate(bar_items):
            y = start_y + i * line_h
            # 左半分: ラベル
            screen.blit(self.font.render(label, True, (200, 210, 220)), (start_x, y))
            # 右半分: バー + ランク文字（百分率モードでratioを渡す）
            rank = draw_stat_bar(screen, start_x + half_w, y + 2, display_val, stat_key,
                         bar_width=bar_w, bar_height=12, font=self.font, ratio=ratio)
            # ランク表示（F-SS）- ボーナス値の代わりに百分率ランクを表示
            rank_text = self.font.render(rank, True, (200, 210, 220))
            screen.blit(rank_text, (start_x + half_w + bar_w + 22, y))
            max_y = y + line_h
        
        # テキスト項目（バーにできないもの）
        for i, text in enumerate(text_items):
            y = max_y + i * (self.font.get_height() + 2)
            screen.blit(self.font.render(text, True, (220, 230, 240)), (start_x, y))
            max_y = y + self.font.get_height() + 2

        if desc:
            desc_y = max_y + 12
            draw_text_wrapped(screen, self.font, desc, start_x, desc_y, cw, color=(170, 170, 170))


def show_dialog(dialog, text, modal=False, auto_close=None):
    """メッセージウィンドウにテキストを表示する。既に表示中の場合は改行して追記する。"""
    if not dialog: return
    from constants import COMBAT_LOG_WAIT_FRAMES

    if dialog.is_active:
        last_line = dialog.text.split("\n")[-1] if dialog.text else ""
        if last_line != text:
            dialog.text += "\n" + text
    else:
        dialog.text = text
        dialog.is_active = True

    from systems.game_state import game_state
    game_state["dialog_modal"] = modal
    dialog.auto_close_timer = auto_close if auto_close is not None else COMBAT_LOG_WAIT_FRAMES
