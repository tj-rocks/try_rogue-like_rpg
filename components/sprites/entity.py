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
        self.is_dead = False
        self.is_falling = False
        self.move_speed = 4
        self.facing = "down"
        self.step_toggle = False
        self.walk_anim_timer = 0 # 歩行アニメーション用のタイマー
        self.idle_anim_timer = 0 # 呼吸などの待機アニメーション用

    def get_occupied_grids(self, tile_size):
        """キャラクターが占有しているグリッド座標のリストを返す（巨大キャラ対応）"""
        # 左上と右下のグリッドを計算
        start_gx = int(self.x // tile_size)
        start_gy = int(self.y // tile_size)
        end_gx = int((self.x + self.width - 1) // tile_size)
        end_gy = int((self.y + self.height - 1) // tile_size)
        
        grids = []
        for gy in range(start_gy, end_gy + 1):
            for gx in range(start_gx, end_gx + 1):
                grids.append((gx, gy))
        return grids

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

    def can_move_grid(self, tx, ty, dungeon):
        """
        指定したピクセル座標 (tx, ty) へ、自分のサイズ（矩形）を維持したまま移動可能か判定する。
        """
        # 1. 占有する全グリッドを取得
        occupied_grids = self.get_occupied_grids_at(tx, ty, dungeon.tile_size)
        
        # 2. 全てのグリッドが通行可能かチェック
        for gx, gy in occupied_grids:
            # マップ範囲外チェック
            if not (0 <= gx < dungeon.map_width and 0 <= gy < dungeon.map_height):
                return False
            
            # 壁チェック (tile ID 0 は壁)
            if dungeon.map_data[gy][gx] == 0:
                # [NEW] wall_single（壺や樽などの障害物）は Entity が通行不可とする
                # _get_wall_texture_key を利用して判定
                wall_type = dungeon._get_wall_texture_key(gx, gy)
                if wall_type == "wall_single":
                    return False
                # 通常の壁も当然不可
                return False

            # 他のエンティティ（自分以外）との衝突チェック
            # プレイヤー
            if hasattr(dungeon, "player") and dungeon.player != self:
                p_grids = dungeon.player.get_occupied_grids(dungeon.tile_size)
                if (gx, gy) in p_grids:
                    return False
            
            # 他の敵
            for e in dungeon.enemies:
                if e != self and not getattr(e, "is_dead", False):
                    e_grids = e.get_occupied_grids(dungeon.tile_size)
                    if (gx, gy) in e_grids:
                        return False
                        
        return True

    def update_animation(self):
        """アニメーションタイマーの更新（共通処理）"""
        self.idle_anim_timer = (self.idle_anim_timer + 1) % 60
        if self.is_moving:
            self.walk_anim_timer = (self.walk_anim_timer + 1) % 40
        else:
            self.walk_anim_timer = 0

    def process_movement(self):
        """スムーズな移動処理（target_x, target_y に向かって移動）"""
        if not self.is_moving:
            return

        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = (dx**2 + dy**2)**0.5

        if dist < self.move_speed:
            self.x = self.target_x
            self.y = self.target_y
            self.is_moving = False
        else:
            self.x += (dx / dist) * self.move_speed
            self.y += (dy / dist) * self.move_speed

    def get_breathing_scale(self):
        """呼吸のようなスケーリング効果を計算する（共通処理）"""
        import math
        # 60フレームで1周期のサインカーブ
        # 1.0 〜 1.05 の間で変動させる
        scale = 1.0 + math.sin(self.idle_anim_timer * (2 * math.pi / 60)) * 0.02
        return (1.0, scale) # 縦方向にのみ伸縮
