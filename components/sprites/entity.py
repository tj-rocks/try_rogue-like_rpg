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
        """現在の (x, y) および目標 (target_x, target_y) に基づいて、占有している全グリッド座標リストを返す"""
        # 現在位置と目標位置の両方を占有中とみなすことで、移動中のすり抜けを防止する
        grids_current = self.get_occupied_grids_at(self.x, self.y, tile_size)
        grids_target = self.get_occupied_grids_at(self.target_x, self.target_y, tile_size)
        
        # 重複を除去してリストで返す
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
            if getattr(dungeon, "player", None) and dungeon.player != self:
                p_grids = dungeon.player.get_occupied_grids(dungeon.tile_size)
                if (gx, gy) in p_grids:
                    return False
            
            # 他の敵
            for e in dungeon.enemies:
                if e != self and not getattr(e, "is_dead", False):
                    e_grids = e.get_occupied_grids(dungeon.tile_size)
                    if (gx, gy) in e_grids:
                        return False
            
            # NPC
            if hasattr(dungeon, "npcs"):
                for n in dungeon.npcs:
                    n_grids = n.get_occupied_grids(dungeon.tile_size)
                    if (gx, gy) in n_grids:
                        return False
                        
        return True

    def update_animation(self):
        """アニメーションタイマー・移動・ダメージ演出の更新（共通処理）"""
        self.idle_anim_timer = (self.idle_anim_timer + 1) % 60
        
        # ダメージ時の点滅タイマー
        if getattr(self, "damage_flash_timer", 0) > 0:
            self.damage_flash_timer -= 1

        # 攻撃タイマーの更新
        if self.is_attacking and getattr(self, "attack_timer", 0) > 0:
            self.attack_timer -= 1
            if self.attack_timer == 0:
                self.is_attacking = False

        # 移動処理
        self.process_movement()

        if self.is_moving:
            self.walk_anim_timer = (self.walk_anim_timer + 1) % 40
        else:
            self.walk_anim_timer = 0

    def take_damage(self, amount):
        """ダメージを受ける（共通処理）"""
        self.hp = max(0, self.hp - amount)
        self.damage_flash_timer = 40 # 40フレーム点滅 (以前は20)
        if self.hp <= 0:
            self.is_dead = True

    def process_movement(self):
        """スムーズな移動処理（target_x, target_y に向かって移動）"""
        if not self.is_moving:
            return

        import time
        t = time.perf_counter()

        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = (dx**2 + dy**2)**0.5

        if dist <= self.move_speed:
            self.x = self.target_x
            self.y = self.target_y
            self.is_moving = False
            # 移動完了ログ (Playerのみ)
            if hasattr(self, "name") and self.name == "自分":
                print(f"[TIME][{t:.4f}] Player Move Finished: at ({int(self.x)}, {int(self.y)})")
        else:
            self.x += (dx / dist) * self.move_speed
            self.y += (dy / dist) * self.move_speed

    def get_breathing_scale(self):
        """呼吸のようなスケーリング効果を計算する。スケール値と現在のフェーズ(0-59)を返す"""
        if self.is_moving or getattr(self, "is_dead", False):
            return (1.0, 1.0), 0
            
        import math
        # 60フレームで1周期
        phase = self.idle_anim_timer % 60
        scale = 1.0 + math.sin(phase * (2 * math.pi / 60)) * 0.02
        return (1.0, scale), phase
