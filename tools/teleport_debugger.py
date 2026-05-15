
import pygame
import json
import os
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import TELEPORT_REQUIRED_ITEM
from wordings import Text

# 色定義
COLOR_BG = (20, 25, 40)
COLOR_PANEL = (40, 50, 70)
COLOR_TEXT = (255, 255, 255)
COLOR_BTN = (60, 100, 180)
COLOR_BTN_HOVER = (80, 130, 230)
COLOR_ACCENT = (0, 200, 255)

# パスの修正
SAVE_TEST_PATH = "components/data/savefile/save_data_test.json"

class TeleportDebugger:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Teleport System Debugger (TEST SAVE)")
        self.font = pygame.font.SysFont("Arial", 24)
        self.font_small = pygame.font.SysFont("Arial", 18)
        self.clock = pygame.time.Clock()
        
        self.save_data = self._load_save()
        self.message = "Ready"
        self.message_timer = 0

    def _load_save(self):
        if os.path.exists(SAVE_TEST_PATH):
            with open(SAVE_TEST_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "coin": 0,
            "max_reached_floor": 0,
            "items": []
        }

    def _save_data(self):
        os.makedirs(os.path.dirname(SAVE_TEST_PATH), exist_ok=True)
        with open(SAVE_TEST_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.save_data, f, indent=4, ensure_ascii=False)
        self._set_message("Save Successful! (TEST SAVE)")

    def _set_message(self, msg):
        self.message = msg
        self.message_timer = 120

    def run(self):
        running = True
        while running:
            self.screen.fill(COLOR_BG)
            
            # --- UI描画 ---
            self._draw_header()
            self._draw_player_stats()
            self._draw_controls()
            
            if self.message_timer > 0:
                self._draw_message()
                self.message_timer -= 1

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_click(event.pos)

            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

    def _draw_header(self):
        title = self.font.render("Teleport System Debugger", True, COLOR_ACCENT)
        self.screen.blit(title, (20, 20))
        path_text = self.font_small.render(f"Target: {SAVE_TEST_PATH}", True, (150, 150, 150))
        self.screen.blit(path_text, (20, 50))

    def _draw_player_stats(self):
        stats = [
            f"Coin: {self.save_data.get('coin', 0)}G",
            f"Max Reached Floor: {self.save_data.get('max_reached_floor', 0)}F",
            f"Items Count: {len(self.save_data.get('items', []))}"
        ]
        
        y = 100
        for s in stats:
            surf = self.font.render(s, True, COLOR_TEXT)
            self.screen.blit(surf, (40, y))
            y += 40

    def _draw_controls(self):
        # ボタン定義: (x, y, w, h, text, callback)
        buttons = [
            (40, 250, 250, 40, "Give 1,000,000 Gold", self._give_gold),
            (40, 300, 250, 40, "Give 10 Teleport Stones", self._give_stones),
            (40, 350, 250, 40, "Unlock All Rest Points", self._unlock_all),
            (40, 400, 250, 40, "Reset Progress (0F)", self._reset_progress),
            (40, 450, 250, 40, "Warp to Village (0F)", self._warp_to_village),
            (320, 250, 250, 40, "SAVE DATA", self._save_data),
            (320, 300, 250, 40, "LAUNCH GAME (TEST)", self._launch_game),
            (320, 350, 250, 40, "CLEAR INVENTORY", self._clear_inv),
            (320, 400, 250, 40, "PREVIEW FALL ANIM", self._start_preview),
        ]

        mx, my = pygame.mouse.get_pos()
        for x, y, w, h, txt, cb in buttons:
            color = COLOR_BTN_HOVER if pygame.Rect(x, y, w, h).collidepoint(mx, my) else COLOR_BTN
            pygame.draw.rect(self.screen, color, (x, y, w, h), border_radius=5)
            txt_surf = self.font_small.render(txt, True, COLOR_TEXT)
            self.screen.blit(txt_surf, (x + (w - txt_surf.get_width()) // 2, y + (h - txt_surf.get_height()) // 2))

        # プレビュー描画エリア
        pygame.draw.rect(self.screen, (10, 10, 20), (600, 250, 150, 200), border_radius=10)
        pygame.draw.rect(self.screen, COLOR_ACCENT, (600, 250, 150, 200), 2, border_radius=10)
        self._draw_preview_sprite(675, 350)

    def _start_preview(self):
        self.preview_timer = 40
        self._set_message("Previewing Fall...")

    def _draw_preview_sprite(self, cx, cy):
        if not hasattr(self, "preview_timer") or self.preview_timer <= 0:
            # 静止状態
            pygame.draw.circle(self.screen, (200, 200, 200), (cx, cy), 20)
            pygame.draw.circle(self.screen, (255, 255, 255), (cx - 5, cy - 5), 5)
            return

        # アニメーション中
        self.preview_timer -= 1
        progress = (40 - self.preview_timer) / 40
        
        # 縮小 + 回転のシミュレーション
        size = int(20 * (1.0 - progress))
        angle = progress * 720 # 2回転
        
        if size > 0:
            surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (200, 200, 200), (size, size), size)
            rot_surf = pygame.transform.rotate(surf, angle)
            self.screen.blit(rot_surf, (cx - rot_surf.get_width()//2, cy - rot_surf.get_height()//2))
        
        # 落とし穴（黒い円）
        hole_size = int(25 * min(1.0, progress * 4))
        pygame.draw.circle(self.screen, (0, 0, 0), (cx, cy + 10), hole_size)

    def _handle_click(self, pos):
        buttons = [
            (40, 250, 250, 40, self._give_gold),
            (40, 300, 250, 40, self._give_stones),
            (40, 350, 250, 40, self._unlock_all),
            (40, 400, 250, 40, self._reset_progress),
            (40, 450, 250, 40, self._warp_to_village),
            (320, 250, 250, 40, self._save_data),
            (320, 300, 250, 40, self._launch_game),
            (320, 350, 250, 40, self._clear_inv),
            (320, 400, 250, 40, self._start_preview),
        ]
        for x, y, w, h, cb in buttons:
            if pygame.Rect(x, y, w, h).collidepoint(pos):
                cb()

    def _give_gold(self):
        self.save_data["coin"] = self.save_data.get("coin", 0) + 1000000
        self._set_message("Gold Added")

    def _give_stones(self):
        items = self.save_data.get("items", [])
        for _ in range(10):
            items.append({"key": TELEPORT_REQUIRED_ITEM, "count": 1})
        self.save_data["items"] = items
        self._set_message("10 Stones Added")

    def _unlock_all(self):
        self.save_data["max_reached_floor"] = 100
        self._set_message("All Areas Unlocked")

    def _reset_progress(self):
        self.save_data["max_reached_floor"] = 0
        self.save_data["coin"] = 0
        self.save_data["current_floor"] = 0
        self.save_data["x"] = 30 * 64
        self.save_data["y"] = 40 * 64
        self._set_message("Progress Reset")

    def _warp_to_village(self):
        self.save_data["current_floor"] = 0
        # ファイル上の 111行目 (P) に相当する内部インデックス 40 にリセット
        self.save_data["x"] = 30 * 64
        self.save_data["y"] = 40 * 64
        self._set_message("Warped to Village (Index 40)")

    def _clear_inv(self):
        self.save_data["items"] = []
        self._set_message("Inventory Cleared")

    def _launch_game(self):
        self._save_data()
        self._set_message("Launching Game (TEST)...")
        import subprocess
        # テスト用セーブデータを読み込むように環境変数をセットして起動
        env = os.environ.copy()
        env["TEST_MODE"] = "1"
        subprocess.Popen([sys.executable, "main.py"], env=env)

    def _draw_message(self):
        surf = self.font_small.render(self.message, True, COLOR_ACCENT)
        self.screen.blit(surf, (40, 500))

if __name__ == "__main__":
    debugger = TeleportDebugger()
    debugger.run()
