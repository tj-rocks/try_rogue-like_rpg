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
        self.move_speed = 4
        self.facing = "down"
        self.step_toggle = False
        self.walk_anim_timer = 0 # 歩行アニメーション用のタイマー
        self.idle_anim_timer = 0 # 呼吸などの待機アニメーション用
        
        # 攻撃アニメーションの共通ステータス
        self.is_attacking = False
        self.attack_timer = 0
        self.is_dead = False
        self.damage_flash_timer = 0 # 攻撃を受けた時の点滅演出用
        self.status_to_inflict = None # 攻撃時に相手に付与する状態

    def take_damage(self, amount):
        """他者から攻撃を受けてHPを減らす共通処理"""
        from constants import HIT_STUN_DURATION
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.is_dead = True
        # ダメージを受けたことを知らせるために1秒間（60フレーム）+ 硬直時間点滅させる演出！
        self.damage_flash_timer = 60 + HIT_STUN_DURATION
        print(f"[{type(self).__name__}] ダメージ{amount}を受けた！残りHP: {self.hp}")

    def set_facing(self, direction):
        self.facing = direction

    def can_move_grid(self, target_x, target_y, dungeon, entities=[], occupied_cells=None):
        """1マス単位でのシンプルで確実な当たり判定（主人公・敵すべてのキャラクター共通関数！）"""
        center_x = target_x + self.width / 2
        center_y = target_y + self.height / 2
        
        grid_x = int(center_x // dungeon.tile_size)
        grid_y = int(center_y // dungeon.tile_size)
        
        # マップの範囲外には出られない
        if not (0 <= grid_x < dungeon.map_width and 0 <= grid_y < dungeon.map_height):
            return False
            
        # マス目が壁(0)だった場合は移動不可！
        if dungeon.map_data[grid_y][grid_x] == 0:
            return False
            
        # ★ 他のキャラクターとの衝突判定（最適化：occupied_cells があれば高速判定）
        if occupied_cells is not None:
            if (grid_x, grid_y) in occupied_cells:
                # 自分自身が占有しているマスなら移動可能
                my_grid_x = int(round(self.target_x + self.width / 2) // dungeon.tile_size)
                my_grid_y = int(round(self.target_y + self.height / 2) // dungeon.tile_size)
                if grid_x == my_grid_x and grid_y == my_grid_y:
                    return True
                return False
        else:
            # 従来通りのループ判定（フォールバック用）
            for entity in entities:
                if getattr(entity, "is_dead", False): continue
                if entity is not self:
                    # 座標を四捨五入してグリッド位置を特定（浮動小数点の誤差対策）
                    other_grid_x = int(round(entity.target_x + entity.width / 2) // dungeon.tile_size)
                    other_grid_y = int(round(entity.target_y + entity.height / 2) // dungeon.tile_size)
                    
                    if grid_x == other_grid_x and grid_y == other_grid_y:
                        return False
                    
        return True

    def process_movement(self):
        """スライディング移動の共通処理。目的地のマスへ滑るように移動し、ピタッと止まる"""
        if self.is_moving:
            if self.x < self.target_x: self.x = min(self.x + self.move_speed, self.target_x)
            elif self.x > self.target_x: self.x = max(self.x - self.move_speed, self.target_x)
            
            if self.y < self.target_y: self.y = min(self.y + self.move_speed, self.target_y)
            elif self.y > self.target_y: self.y = max(self.y - self.move_speed, self.target_y)
            
            if self.x == self.target_x and self.y == self.target_y:
                self.is_moving = False
                return True # 移動がちょうど完了した瞬間であることを返す
        return False

    def get_breathing_scale(self):
        """呼吸のようななめらかな伸縮スケールを計算して返す (scale_x, scale_y)"""
        import math
        from constants import BREATHING_SCALE
        # 0.0〜1.0の間をなめらかに動く係数
        breath_val = (math.sin(self.idle_anim_timer * math.pi / 30) + 1) / 2
        # BREATHING_SCALE 〜 1.0 の間で伸縮
        scale_y = 1.0 - (1.0 - BREATHING_SCALE) * breath_val
        scale_x = 1.0 + (1.0 - BREATHING_SCALE) * breath_val * 0.5 # 横は少し広がる
        return scale_x, scale_y

    def update_animation(self):
        """すべてのエンティティに共通するフレームごとのアニメーション進行処理（毎フレーム呼ばれる）"""
        self.process_movement()
        
        # 移動中は歩行タイマーを進める（アニメーション用）
        if self.is_moving:
            from constants import WALK_ANIMATION_SPEED
            self.walk_anim_timer = (self.walk_anim_timer + 1) % (WALK_ANIMATION_SPEED * 2)
        else:
            self.walk_anim_timer = 0
            
        if self.is_attacking:
            self.attack_timer -= 1 # Keep decrementing attack_timer
            # 攻撃アニメーションが終わったら元の画像に戻す
            if self.attack_timer <= 0:
                self.is_attacking = False
                
        # 点滅タイマーの消化
        if getattr(self, "damage_flash_timer", 0) > 0:
            self.damage_flash_timer -= 1
            
        # 待機アニメーション（呼吸）タイマーの更新
        self.idle_anim_timer = (self.idle_anim_timer + 1) % 60
