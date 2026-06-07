import pygame
from constants import TRAP_DATA
from wordings import Text

class Trap:
    _image_cache = {}

    def __init__(self, x, y, trap_type):
        """
        x, y: グリッド座標
        trap_type: 'pitfall', 'damage_floor', 'mine'
        """
        self.x = x
        self.y = y
        self.type = trap_type
        self.data = TRAP_DATA.get(trap_type, {})
        self.is_revealed = False
        self.is_triggered = False
        
        self.image = self._load_image()

    def _load_image(self):
        path = self.data.get("image_path")
        if not path: return None
        
        if path in Trap._image_cache:
            return Trap._image_cache[path]
        
        import os
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            Trap._image_cache[path] = img
            return img
        return None

    def trigger(self, player, dungeon, dialog):
        """罠を踏んだ時の処理"""
        self.is_triggered = True
        self.is_revealed = True
        
        from systems.magic_handler import FlashEffect, FireEffect
        from systems.sound_handler import sound_manager
        
        # 効果音再生
        sound_path = self.data.get("sound")
        if sound_path:
            sound_manager.play_sfx(sound_path)
        
        msg = Text.Trap.TRIGGERED.format(name=self.data.get('name'))
        
        if self.type == "pitfall":
            # 落とし穴：次の階層へ (共通関数で予約)
            from systems.dungeon import warp_with_pitfall
            warp_with_pitfall(dungeon.current_floor + 1, player, spawn_reason="trap")
            msg += Text.Trap.PITFALL
            
        elif self.type == "damage_floor":
            # ダメージ床：10ダメージ
            dmg = self.data.get("damage", 10)
            player.hp = max(0, player.hp - dmg)
            
            # 赤いフラッシュ演出
            dungeon.magic_effects.append(FlashEffect(color=(255, 0, 0), duration=12))
            msg += Text.Trap.DAMAGE_FLOOR.format(damage=dmg)
            
        elif self.type == "mine":
            # 地雷：現在HPを半分にする
            import math
            old_hp = player.hp
            player.hp = math.ceil(player.hp / 2)
            dmg = old_hp - player.hp
            
            # 爆発演出
            tx = self.x * dungeon.tile_size
            ty = self.y * dungeon.tile_size
            dungeon.magic_effects.append(FireEffect(tx, ty, size=120, color=(255, 180, 50)))
            msg += Text.Trap.MINE.format(damage=dmg)
            

        # [NEW] ステータス異常の付与
        inflict_status = self.data.get("status")
        if inflict_status:
            player.condition = inflict_status
            if inflict_status == "poison":
                msg += "\n毒を受けてしまった！"

        return msg


    def draw(self, screen, camera_x, camera_y, tile_size):
        """発見済みの罠のみ描画する (スイッチは常に表示)"""
        if not self.is_revealed:
            return
            
        draw_x = self.x * tile_size - camera_x
        draw_y = self.y * tile_size - camera_y
        
        if self.image:
            # 画像が読み込めている場合は画像を描画
            scaled_img = pygame.transform.scale(self.image, (tile_size, tile_size))
            screen.blit(scaled_img, (draw_x, draw_y))
        else:
            # フォールバック: 図形描画
            color = self.data.get("color", (100, 100, 100))
            s = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
            if self.type == "pitfall":
                pygame.draw.circle(s, (0, 0, 0, 200), (tile_size//2, tile_size//2), tile_size//3)
            elif self.type == "damage_floor":
                margin = tile_size // 5
                pygame.draw.rect(s, (*color, 120), (margin, margin, tile_size - margin*2, tile_size - margin*2))
            elif self.type == "mine":
                points = [(tile_size//2, 8), (8, tile_size-8), (tile_size-8, tile_size-8)]
                pygame.draw.polygon(s, (*color, 150), points)

            screen.blit(s, (draw_x, draw_y))
