import pygame
import sys
import os
import random

# プロジェクトのルートをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from constants import (
    ENEMY_DATA, WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, 
    SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE
)
from components.sprites.enemy import Enemy

class EnemyViewer:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1000, 700))
        pygame.display.set_caption("Enemy Equipment Viewer")
        self.clock = pygame.time.Clock()
        
        self.enemy_keys = list(ENEMY_DATA.keys())
        self.enemy_index = 0
        
        self.weapon_keys = [None] + list(WEAPON_DATA.keys())
        self.armor_keys = [None] + list(ARMOR_DATA.keys())
        self.shield_keys = [None] + list(SHIELD_DATA.keys())
        
        self.w_idx = 0
        self.a_idx = 0
        self.s_idx = 0
        
        self.enemy = None
        self.update_enemy()
        
        self.font = pygame.font.SysFont("Arial", 20)
        self.bold_font = pygame.font.SysFont("Arial", 24, bold=True)
        
        # オフセット調整用
        self.adj_idx = 0 # 0: idle, 1: attack
        self.last_log_time = 0

    def update_enemy(self):
        key = self.enemy_keys[self.enemy_index]
        # テスト用に強制的に現在の選択装備を反映させる
        self.enemy = Enemy(300, 200, key)
        self.enemy.equipped_weapon = self.weapon_keys[self.w_idx]
        self.enemy.equipped_armor = self.armor_keys[self.a_idx]
        self.enemy.equipped_shield = self.shield_keys[self.s_idx]
        self.enemy.update_equipment_stats()

    def run(self):
        running = True
        while running:
            self.screen.fill((50, 50, 50))
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        self.enemy_index = (self.enemy_index - 1) % len(self.enemy_keys)
                        self.update_enemy()
                    if event.key == pygame.K_DOWN:
                        self.enemy_index = (self.enemy_index + 1) % len(self.enemy_keys)
                        self.update_enemy()
                    
                    if event.key == pygame.K_1:
                        self.w_idx = (self.w_idx + 1) % len(self.weapon_keys)
                        self.update_enemy()
                    if event.key == pygame.K_2:
                        self.a_idx = (self.a_idx + 1) % len(self.armor_keys)
                        self.update_enemy()
                    if event.key == pygame.K_3:
                        self.s_idx = (self.s_idx + 1) % len(self.shield_keys)
                        self.update_enemy()
                    
                    if event.key == pygame.K_w: self.enemy.facing = "up"
                    if event.key == pygame.K_s: self.enemy.facing = "down"
                    if event.key == pygame.K_a: self.enemy.facing = "left"
                    if event.key == pygame.K_d: self.enemy.facing = "right"
                    
                    if event.key == pygame.K_SPACE:
                        self.enemy.is_attacking = not self.enemy.is_attacking
                        if self.enemy.is_attacking:
                            from constants import ATTACK_ANIMATION_FRAMES
                            self.enemy.attack_timer = ATTACK_ANIMATION_FRAMES
                            
                    # オフセット調整ロジック
                    if self.enemy.weapon:
                        changed = False
                        facing = self.enemy.facing
                        # 辞書の中身を直接書き換えるために参照を取得
                        offsets = self.enemy.weapon.HAND_OFFSETS
                        if facing not in offsets:
                            offsets[facing] = [[0, 0], [0, 0]]
                        
                        curr_off = offsets[facing][self.adj_idx]
                        
                        if event.key == pygame.K_u: self.adj_idx = 0
                        if event.key == pygame.K_o: self.adj_idx = 1
                        
                        move_step = 1
                        if pygame.key.get_mods() & pygame.KMOD_SHIFT: move_step = 5
                        
                        if event.key == pygame.K_i: curr_off[1] -= move_step; changed = True # Up
                        if event.key == pygame.K_k: curr_off[1] += move_step; changed = True # Down
                        if event.key == pygame.K_j: curr_off[0] -= move_step; changed = True # Left
                        if event.key == pygame.K_l: curr_off[0] += move_step; changed = True # Right
                        
                        if changed:
                            print(f"\n--- Updated offsets for {self.enemy.weapon.key} ({facing}) ---")
                            print(f"Mode: {'Idle' if self.adj_idx == 0 else 'Attack'}")
                            import json
                            print(json.dumps(offsets, indent=2))

            # 描画
            self.enemy.idle_anim_timer += 1
            if self.enemy.is_attacking:
                self.enemy.attack_timer -= 1
                if self.enemy.attack_timer <= 0:
                    self.enemy.is_attacking = False
            
            # 中心に描画（拡大表示）
            preview_surface = pygame.Surface((300, 300), pygame.SRCALPHA)
            self.enemy.draw(preview_surface, 300 - 150, 200 - 150) # ローカル座標で描画
            
            scaled_preview = pygame.transform.scale(preview_surface, (600, 600))
            self.screen.blit(scaled_preview, (350, 50))
            
            # UI表示
            self._draw_ui()
            
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

    def _draw_ui(self):
        y = 30
        self.screen.blit(self.bold_font.render("Enemy Equipment Viewer", True, (255, 255, 255)), (20, y))
        y += 50
        
        self.screen.blit(self.font.render(f"Enemy [UP/DOWN]: {self.enemy_keys[self.enemy_index]}", True, (200, 255, 200)), (20, y))
        y += 40
        self.screen.blit(self.font.render(f"[1] Weapon: {self.weapon_keys[self.w_idx]}", True, (255, 200, 200)), (20, y))
        y += 30
        self.screen.blit(self.font.render(f"[2] Armor: {self.armor_keys[self.a_idx]}", True, (200, 200, 255)), (20, y))
        y += 30
        self.screen.blit(self.font.render(f"[3] Shield: {self.shield_keys[self.s_idx]}", True, (255, 255, 200)), (20, y))
        
        y += 60
        self.screen.blit(self.font.render("Controls:", True, (200, 200, 200)), (20, y))
        y += 30
        self.screen.blit(self.font.render("WASD: Change Direction", True, (150, 150, 150)), (20, y))
        y += 30
        self.screen.blit(self.font.render("SPACE: Toggle Attack", True, (150, 150, 150)), (20, y))
        
        # ステータス表示
        y += 60
        self.screen.blit(self.bold_font.render("Current Stats:", True, (255, 255, 255)), (20, y))
        y += 30
        self.screen.blit(self.font.render(f"ATK: {self.enemy.attack}", True, (255, 255, 255)), (20, y))
        y += 30
        self.screen.blit(self.font.render(f"DEF: {self.enemy.defense}", True, (255, 255, 255)), (20, y))
        y += 30
        self.screen.blit(self.font.render(f"Accuracy: {self.enemy.accuracy_close} (C) / {self.enemy.accuracy_ranged} (R)", True, (255, 255, 255)), (20, y))
        y += 30
        if hasattr(self.enemy, "block_chance_close"):
            self.screen.blit(self.font.render(f"Block: {int(self.enemy.block_chance_close*100)}% (C) / {int(self.enemy.block_chance_ranged*100)}% (R)", True, (255, 255, 255)), (20, y))

        # オフセット調整情報の表示
        y += 60
        mode_text = "IDLE Offset" if self.adj_idx == 0 else "ATTACK Offset"
        color = (0, 255, 255) if self.adj_idx == 0 else (255, 100, 100)
        self.screen.blit(self.bold_font.render(f"Adjusting: {mode_text}", True, color), (20, y))
        y += 30
        if self.enemy.weapon:
            off = self.enemy.weapon.HAND_OFFSETS.get(self.enemy.facing, [[0,0],[0,0]])[self.adj_idx]
            self.screen.blit(self.font.render(f"Current Offset ({self.enemy.facing}): {off}", True, (255, 255, 255)), (20, y))
            y += 30
            self.screen.blit(self.font.render("U/O: Switch Idle/Attack", True, (150, 150, 150)), (20, y))
            y += 25
            self.screen.blit(self.font.render("IJKL: Move Offset (Shift: x5)", True, (150, 150, 150)), (20, y))

if __name__ == "__main__":
    viewer = EnemyViewer()
    viewer.run()
