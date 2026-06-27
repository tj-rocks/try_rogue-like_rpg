import pygame

class Entity:
    def __init__(self, x, y, hp, max_hp, attack, width=50, height=50):
        self.x = x
        self.y = y
        self.hp = hp
        self.max_hp = max_hp
        self.attack = attack
        self.width = width
        self.height = height
        
        # 移動・アニメーション関連の全キャラクター共通のステータス
        self.target_x = x
        self.target_y = y
        self.prev_x = x
        self.prev_y = y
        self.is_moving = False
        self.is_attacking = False
        self.attack_timer = 0
        self.damage_flash_timer = 0
        self.flash_color = (255, 255, 255)
        self.is_dead = False
        self.is_falling = False
        self.move_speed = 300 # 1秒あたりの移動ピクセル数 (例: 300なら1マス64ピクセルを約0.2秒で移動)
        self.facing = "down"
        self.step_toggle = False
        self.walk_anim_timer = 0 # 歩行アニメーション用のタイマー
        self.idle_anim_timer = 0 # 呼吸などの待機アニメーション用

    def get_occupied_grids(self, tile_size):
        """現在の (x, y) および目標 (target_x, target_y) に基づいて、占有している全グリッド座標リストを返す"""
        grids_current = self.get_occupied_grids_at(self.x, self.y, tile_size)
        grids_target = self.get_occupied_grids_at(self.target_x, self.target_y, tile_size)
        return list(set(grids_current + grids_target))

    def get_occupied_grids_at(self, tx, ty, tile_size):
        """指定した座標(tx, ty)にいると仮定した時の占有グリッドを返す"""
        start_gx = int(tx // tile_size)
        start_gy = int(ty // tile_size)
        end_gx = int((tx + self.width - 1) // tile_size)
        end_gy = int((ty + self.height - 1) // tile_size)
        
        grids = []
        for gy in range(start_gy, end_gy + 1):
            for gx in range(start_gx, end_gx + 1):
                grids.append((gx, gy))
        return grids

    def can_move_grid(self, tx, ty, dungeon, debug_log=False):
        """指定したピクセル座標 (tx, ty) へ、自分のサイズを維持したまま移動可能か判定する"""
        # 移動する敵が魔法の防壁（magic_barrier）と現在重なっている場合、別グリッドへの移動を禁止する（閉じ込め）
        if self.__class__.__name__ == "Enemy" and not getattr(self, "is_static", False):
            curr_grids = self.get_occupied_grids_at(self.x, self.y, dungeon.tile_size)
            tgt_grids = self.get_occupied_grids_at(tx, ty, dungeon.tile_size)
            if set(curr_grids) != set(tgt_grids):
                for e in dungeon.enemies:
                    if e != self and not getattr(e, "is_dead", False) and getattr(e, "is_static", False) and getattr(e, "type", "") == "magic_barrier":
                        e_grids = e.get_occupied_grids(dungeon.tile_size)
                        if any(g in e_grids for g in curr_grids):
                            if debug_log and hasattr(self, "_log_trace"):
                                self._log_trace(dungeon, f"can_move_grid: Blocked by magic_barrier at target grid ({tx//dungeon.tile_size}, {ty//dungeon.tile_size})")
                            return False

        occupied_grids = self.get_occupied_grids_at(tx, ty, dungeon.tile_size)
        for gx, gy in occupied_grids:
            if not (0 <= gx < dungeon.map_width and 0 <= gy < dungeon.map_height):
                if debug_log and hasattr(self, "_log_trace"):
                    self._log_trace(dungeon, f"can_move_grid: Out of bounds at ({gx}, {gy})")
                return False
            if dungeon.map_data[gy][gx] == 0:
                if debug_log and hasattr(self, "_log_trace"):
                    self._log_trace(dungeon, f"can_move_grid: Wall at ({gx}, {gy})")
                return False

            if getattr(dungeon, "player", None) and dungeon.player != self:
                p_grids = dungeon.player.get_occupied_grids(dungeon.tile_size)
                if (gx, gy) in p_grids:
                    if debug_log and hasattr(self, "_log_trace"):
                        self._log_trace(dungeon, f"can_move_grid: Blocked by Player at ({gx}, {gy})")
                    return False
            for e in dungeon.enemies:
                if e != self and not getattr(e, "is_dead", False):
                    e_grids = e.get_occupied_grids(dungeon.tile_size)
                    if (gx, gy) in e_grids:
                        if debug_log and hasattr(self, "_log_trace"):
                            self._log_trace(dungeon, f"can_move_grid: Blocked by Enemy {e.name}#{id(e)%10000} at ({gx}, {gy})")
                        return False
            if hasattr(dungeon, "npcs"):
                for n in dungeon.npcs:
                    n_grids = n.get_occupied_grids(dungeon.tile_size)
                    if (gx, gy) in n_grids:
                        if debug_log and hasattr(self, "_log_trace"):
                            self._log_trace(dungeon, f"can_move_grid: Blocked by NPC {n.name} at ({gx}, {gy})")
                        return False
        return True

    def process_movement(self, dt=1/60):
        """時間ベースのスライディング移動。フレームレートに関わらず一定の速度で移動する"""
        if self.is_moving:
            step = self.move_speed * dt
            if self.x < self.target_x:
                self.x = min(self.x + step, self.target_x)
            elif self.x > self.target_x:
                self.x = max(self.x - step, self.target_x)
            if self.y < self.target_y:
                self.y = min(self.y + step, self.target_y)
            elif self.y > self.target_y:
                self.y = max(self.y - step, self.target_y)
            
            if self.x == self.target_x and self.y == self.target_y:
                self.is_moving = False
                return True
        return False

    def get_breathing_scale(self):
        """呼吸のようななめらかな伸縮スケールを計算して返す ((scale_x, scale_y), phase)"""
        import math
        from constants import BREATHING_SCALE
        breath_val = (math.sin(self.idle_anim_timer * math.pi / 30) + 1) / 2
        scale_y = 1.0 - (1.0 - BREATHING_SCALE) * breath_val
        scale_x = 1.0 + (1.0 - BREATHING_SCALE) * breath_val * 0.5
        return (scale_x, scale_y), self.idle_anim_timer

    def update_animation(self, dt=1/60):
        """すべてのエンティティに共通するフレームごとのアニメーション進行処理"""
        self.process_movement(dt)
        self.idle_anim_timer = (self.idle_anim_timer + 1) % 60
        
        if self.is_moving:
            from constants import WALK_ANIMATION_SPEED
            self.walk_anim_timer = (self.walk_anim_timer + 1) % (WALK_ANIMATION_SPEED * 2)
        else:
            self.walk_anim_timer = 0
            
        if self.is_attacking:
            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self.is_attacking = False
                
        if getattr(self, "damage_flash_timer", 0) > 0:
            self.damage_flash_timer -= 1

    def take_damage(self, amount):
        """ダメージを受ける（共通処理）"""
        from constants import HIT_STUN_DURATION
        self.hp = max(0, self.hp - amount)
        self.damage_flash_timer = 60 + HIT_STUN_DURATION
        self.flash_color = (255, 255, 255)
        if self.hp <= 0:
            self.is_dead = True
            self.is_attacking = False
            self.is_moving = False
            self.target_x, self.target_y = self.x, self.y
