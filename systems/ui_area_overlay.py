import pygame


class AreaMessageOverlay:
    """ダクソ風エリア名演出：画面中央にフェードイン→表示→フェードアウト"""

    FADE_IN_FRAMES  = 40
    HOLD_FRAMES     = 90
    FADE_OUT_FRAMES = 50
    @property
    def SE_PATH(self):
        from constants import SOUND_AREA_MESSAGE
        return SOUND_AREA_MESSAGE

    def __init__(self, screen_width, screen_height):
        self.sw = screen_width
        self.sh = screen_height
        self.is_active = False
        self._title = ""
        self._body  = ""
        self._frame = 0
        self._total = self.FADE_IN_FRAMES + self.HOLD_FRAMES + self.FADE_OUT_FRAMES

    def show(self, message):
        """area_message（文字列またはリスト）を受け取って演出開始。
        リスト: [0]=タイトル, [1以降]=本文行
        文字列: 1行目=タイトル, 残り=本文
        """
        if isinstance(message, list):
            self._title = str(message[0]) if message else ""
            self._body_lines = [str(l) for l in message[1:]]
        else:
            lines = str(message).strip().splitlines()
            self._title = lines[0] if lines else ""
            self._body_lines = lines[1:] if len(lines) > 1 else []
        self._frame = 0
        self.is_active = True
        from systems.sound_handler import sound_manager
        sound_manager.play_sfx(self.SE_PATH)

    def update(self):
        if not self.is_active:
            return
        self._frame += 1
        if self._frame >= self._total:
            self.is_active = False

    def _alpha(self):
        f = self._frame
        fi, fh, fo = self.FADE_IN_FRAMES, self.HOLD_FRAMES, self.FADE_OUT_FRAMES
        if f < fi:
            return int(255 * f / fi)
        elif f < fi + fh:
            return 255
        else:
            return int(255 * (1 - (f - fi - fh) / fo))

    def _render_outlined(self, font, text, alpha):
        """白字・黒縁付きテキストサーフェスを返す"""
        WHITE = (255, 255, 255)
        BLACK = (0,   0,   0)
        base = font.render(text, True, WHITE)
        w, h = base.get_width() + 4, base.get_height() + 4
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        for ox, oy in ((-2,0),(2,0),(0,-2),(0,2),(-1,-1),(1,-1),(-1,1),(1,1)):
            s = font.render(text, True, BLACK)
            s.set_alpha(alpha)
            surf.blit(s, (ox + 2, oy + 2))
        base.set_alpha(alpha)
        surf.blit(base, (2, 2))
        return surf

    def draw(self, screen):
        if not self.is_active:
            return
        from systems.resources import font_medium, font_small
        alpha       = self._alpha()
        body_alpha  = int(alpha * 0.75)

        cx = self.sw // 2
        cy = self.sh // 2

        title_surf = self._render_outlined(font_medium, self._title, alpha)
        ty = cy - title_surf.get_height() - 8
        screen.blit(title_surf, (cx - title_surf.get_width() // 2, ty))

        body_lines = getattr(self, "_body_lines", [])
        if body_lines:
            body_y = cy + 6
            for line in body_lines:
                surf = self._render_outlined(font_small, line, body_alpha)
                screen.blit(surf, (cx - surf.get_width() // 2, body_y))
                body_y += surf.get_height() + 4
