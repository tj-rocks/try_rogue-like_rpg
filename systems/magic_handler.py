import json
import os
import pygame
from constants import STAVE_DATA, COMBAT_LOG_WAIT_FRAMES
from systems.combat_handler import deal_damage

# 魔法の設定をロード
from constants import load_master_data
MAGIC_SETTINGS = load_master_data("magic_settings.yml")

# ============================================================
# ✨ 演出用エフェクトクラス
# ============================================================
class MagicEffect:
    def __init__(self, x, y, duration=30):
        self.x = x
        self.y = y
        self.duration = duration
        self.max_duration = duration

    def update(self):
        self.duration -= 1

    def is_done(self):
        return self.duration <= 0

    def draw(self, screen, camera_x, camera_y):
        pass

class FireEffect(MagicEffect):
    def __init__(self, x, y, size=60, color=(255, 100, 0)):
        super().__init__(x, y, duration=20)
        self.size = size
        self.color = color

    def draw(self, screen, camera_x, camera_y):
        import random
        draw_x = self.x - camera_x
        draw_y = self.y - camera_y
        
        # 燃え盛る火の演出
        alpha = int(255 * (self.duration / self.max_duration))
        for _ in range(3):
            rx = random.randint(-self.size//3, self.size//3)
            ry = random.randint(-self.size//3, self.size//3)
            rs = random.randint(self.size//2, self.size)
            s = pygame.Surface((rs, rs), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, alpha), (rs//2, rs//2), rs//2)
            screen.blit(s, (draw_x + rx - rs//2 + 30, draw_y + ry - rs//2 + 30))

class FlashEffect(MagicEffect):
    def __init__(self, color=(255, 255, 255), duration=10):
        super().__init__(0, 0, duration)
        self.color = color

    def draw(self, screen, camera_x, camera_y):
        alpha = int(150 * (self.duration / self.max_duration))
        s = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        s.fill((*self.color, alpha))
        screen.blit(s, (0, 0))

class ProjectileEffect(MagicEffect):
    def __init__(self, start_x, start_y, end_x, end_y, effect_type="fireball", duration=20):
        super().__init__(start_x, start_y, duration=duration)
        self.start_x = start_x
        self.start_y = start_y
        self.end_x = end_x
        self.end_y = end_y
        self.effect_type = effect_type
        self.particles = []

    def update(self):
        super().update()
        import random
        # パーティクルの生成（トレイル演出）
        t = 1.0 - (self.duration / self.max_duration)
        curr_x = self.start_x + (self.end_x - self.start_x) * t + 30
        curr_y = self.start_y + (self.end_y - self.start_y) * t + 30
        
        if self.effect_type == "fireball":
            self.particles.append({"x": curr_x + random.randint(-10, 10), 
                                  "y": curr_y + random.randint(-10, 10), 
                                  "life": 12, "color": (255, random.randint(100, 200), 0)})
        elif self.effect_type == "ice_shard":
             self.particles.append({"x": curr_x + random.randint(-5, 5), 
                                  "y": curr_y + random.randint(-5, 5), 
                                  "life": 15, "color": (200, 230, 255)})
        elif self.effect_type == "dark_bolt":
             self.particles.append({"x": curr_x + random.randint(-8, 8), 
                                  "y": curr_y + random.randint(-8, 8), 
                                  "life": 10, "color": (150, 0, 200)})
        elif self.effect_type == "arrow":
             self.particles.append({"x": curr_x, "y": curr_y, 
                                  "life": 8, "color": (100, 100, 100)})
        elif self.effect_type == "strange_mucus":
             self.particles.append({"x": curr_x + random.randint(-8, 8), 
                                  "y": curr_y + random.randint(-8, 8), 
                                  "life": 18, "color": (150, 0, 200)})
        else: # Default trail
             self.particles.append({"x": curr_x + random.randint(-5, 5), 
                                  "y": curr_y + random.randint(-5, 5), 
                                  "life": 10, "color": (100, 255, 100)})
        
        for p in self.particles[:]:
            p["life"] -= 1
            if p["life"] <= 0:
                self.particles.remove(p)

    def draw(self, screen, camera_x, camera_y):
        # トレイル（パーティクル）の描画
        for p in self.particles:
            alpha = max(0, min(255, int(255 * (p["life"] / 15))))
            s = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p["color"], alpha), (4, 4), 4)
            screen.blit(s, (p["x"] - camera_x - 4, p["y"] - camera_y - 4))

        # メイン弾体の描画
        t = 1.0 - (self.duration / self.max_duration)
        curr_x = self.start_x + (self.end_x - self.start_x) * t - camera_x + 30
        curr_y = self.start_y + (self.end_y - self.start_y) * t - camera_y + 30
        
        radius = 10
        color = (255, 255, 255)
        
        if self.effect_type == "fireball":
            color = (255, 100, 0)
            radius = 12
        elif self.effect_type == "ice_shard":
            color = (150, 220, 255)
            radius = 8
        elif self.effect_type == "dark_bolt":
            color = (100, 0, 150)
            radius = 10
        elif self.effect_type == "arrow":
            color = (200, 200, 200)
            radius = 5
        elif self.effect_type == "strange_mucus":
            color = (180, 0, 255)
            radius = 12
        elif self.effect_type == "sonic_wave":
            color = (200, 255, 200)
            radius = 15
            
        # 発光感のある描画
        s = pygame.Surface((radius * 3, radius * 3), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, 100), (radius*1.5, radius*1.5), radius*1.5)
        pygame.draw.circle(s, (*color, 255), (radius*1.5, radius*1.5), radius)
        pygame.draw.circle(s, (255, 255, 255, 200), (radius*1.5, radius*1.5), radius // 2)
        screen.blit(s, (curr_x - radius*1.5, curr_y - radius*1.5))

class KnockbackEffect(MagicEffect):
    def __init__(self, x1, y1, x2, y2, color=(200, 200, 255), duration=15):
        super().__init__(x1, y1, duration=duration)
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2
        self.color = color

    def draw(self, screen, camera_x, camera_y):
        t = 1.0 - (self.duration / self.max_duration)
        
        # 衝撃波の軌跡を描画
        for i in range(3):
            trail_t = max(0, t - i * 0.1)
            curr_x = self.x1 + (self.x2 - self.x1) * trail_t - camera_x + 30
            curr_y = self.y1 + (self.y2 - self.y1) * trail_t - camera_y + 30
            
            for r in range(1, 4):
                radius = r * (8 - i * 2) * (1.1 - t)
                alpha = int(200 * (self.duration / self.max_duration) / (i + 1))
                s = pygame.Surface((radius * 2 + 1, radius * 2 + 1), pygame.SRCALPHA)
                pygame.draw.circle(s, (*self.color, alpha), (int(radius), int(radius)), int(radius), max(1, 3 - i))
                screen.blit(s, (curr_x - radius, curr_y - radius))

class DirectionalFlashEffect(MagicEffect):
    """プレイヤーの目の前などが光る演出"""
    def __init__(self, x, y, size=150, color=(255, 255, 200), duration=15):
        super().__init__(x, y, duration=duration)
        self.size = size
        self.color = color

    def draw(self, screen, camera_x, camera_y):
        draw_x = self.x - camera_x + 30
        draw_y = self.y - camera_y + 30
        alpha = int(230 * (self.duration / self.max_duration))
        
        # 中心から広がる光
        for r in range(1, 4):
            radius = int(self.size * (1.2 - self.duration / self.max_duration) * (r / 3))
            if radius <= 0: continue
            s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, alpha // r), (radius, radius), radius)
            screen.blit(s, (draw_x - radius, draw_y - radius))

def execute_stave(player, stave, dungeon, dialog):
    """杖を振った際の効果を発動させるメイン関数"""
    from constants import STAVE_DATA
    settings = STAVE_DATA.get(stave.key, {})
    if stave.charges <= 0:
        return "回数が足りない！"

    stave.charges -= 1
    effect_type = settings.get("effect_type")

    # 🎵 効果音再生
    sound_path = settings.get("sound")
    if sound_path:
        from systems.sound_handler import sound_manager
        sound_manager.play_sfx(sound_path)

    msg = f"{player.name} は {stave.name} を振った！\n"
    
    if effect_type == "knockback":
        msg += _effect_knockback(player, settings, dungeon, dialog)
    elif effect_type == "fire":
        msg += _effect_fire(player, settings, dungeon, dialog)
    elif effect_type == "heal":
        msg += _effect_heal(player, settings, dungeon, dialog)
    elif effect_type == "invincible":
        msg += _effect_invincible(player, settings, dungeon, dialog)
    elif effect_type == "light_all":
        msg += _effect_light_all(player, settings, dungeon, dialog)
    else:
        msg += "しかし 何もおきなかった！"

    return msg

def _effect_knockback(player, settings, dungeon, dialog):
    """正面の敵を吹き飛ばす"""
    # プレイヤーの向きから対象タイルを特定
    gx = int((player.x + player.width / 2) // dungeon.tile_size)
    gy = int((player.y + player.height / 2) // dungeon.tile_size)
    
    dx, dy = 0, 0
    if player.facing == "up": dy = -1
    elif player.facing == "down": dy = 1
    elif player.facing == "left": dx = -1
    elif player.facing == "right": dx = 1
    
    # 直線上の敵を探索
    target_enemy = None
    target_gx, target_gy = gx, gy # 衝撃波が命中する最終地点
    
    cur_gx, cur_gy = gx + dx, gy + dy
    while 0 <= cur_gx < dungeon.map_width and 0 <= cur_gy < dungeon.map_height:
        # 壁判定
        if dungeon.map_data[cur_gy][cur_gx] == 0:
            target_gx, target_gy = cur_gx, cur_gy
            break
        
        # マスに敵がいるか？
        found = None
        for e in dungeon.enemies:
            if not getattr(e, "is_dead", False):
                egx = int((e.x + e.width / 2) // dungeon.tile_size)
                egy = int((e.y + e.height / 2) // dungeon.tile_size)
                if egx == cur_gx and egy == cur_gy:
                    found = e
                    break
        
        if found:
            target_enemy = found
            target_gx, target_gy = cur_gx, cur_gy
            break
        
        target_gx, target_gy = cur_gx, cur_gy
        cur_gx += dx
        cur_gy += dy

    # 演出1: プレイヤー位置からターゲット位置まで衝撃波が飛ぶ (少し速め)
    dungeon.magic_effects.append(KnockbackEffect(gx * dungeon.tile_size, gy * dungeon.tile_size, 
                                                target_gx * dungeon.tile_size, target_gy * dungeon.tile_size,
                                                color=(220, 220, 255), duration=10))

    if not target_enemy:
        return "まばゆい衝撃波を 放った！"

    # 吹き飛ばしロジック
    max_dist = settings.get("max_distance", 10)
    current_gx, current_gy = target_gx, target_gy
    
    hit_other = None
    final_gx, final_gy = current_gx, current_gy
    
    for _ in range(max_dist):
        next_gx, next_gy = final_gx + dx, final_gy + dy
        
        # 壁判定
        if not (0 <= next_gx < dungeon.map_width and 0 <= next_gy < dungeon.map_height) or \
           dungeon.map_data[next_gy][next_gx] == 0:
            break
            
        # 他の敵判定
        collision = False
        for e in dungeon.enemies:
            if e != target_enemy and not getattr(e, "is_dead", False):
                egx = int((e.x + e.width / 2) // dungeon.tile_size)
                egy = int((e.y + e.height / 2) // dungeon.tile_size)
                if egx == next_gx and egy == next_gy:
                    hit_other = e
                    collision = True
                    break
        if collision:
            break
            
        final_gx, final_gy = next_gx, next_gy
 
    # 敵を移動させる
    target_enemy.x = final_gx * dungeon.tile_size
    target_enemy.y = final_gy * dungeon.tile_size
    target_enemy.target_x = target_enemy.x
    target_enemy.target_y = target_enemy.y
    
    # ダメージ計算（攻撃力の半分、必中）
    msg_dmg, damage, is_crit, is_miss = deal_damage(player, target_enemy, is_magic=True, damage_mult=0.5)
    msg = f"{target_enemy.name} を 吹き飛ばした！\n" + msg_dmg
    
    # 演出2: 敵の吹き飛ばし移動
    dungeon.magic_effects.append(KnockbackEffect(target_gx * dungeon.tile_size, target_gy * dungeon.tile_size, 
                                                final_gx * dungeon.tile_size, final_gy * dungeon.tile_size,
                                                duration=20))
    
    if hit_other:
        # 衝突ダメージ（攻撃力の半分）
        dmg = int(player.attack * settings.get("collision_dmg_mult", 0.5))
        hit_other.hp -= dmg
        target_enemy.hp -= dmg
        msg += f"\n{hit_other.name} にぶつかって 両者に {dmg} ダメージ！"
        if hit_other.hp <= 0:
            msg += f"\n{hit_other.name} を 倒した！"
            hit_other.is_dead = True
    
    if target_enemy.hp <= 0:
        msg += f"\n{target_enemy.name} を 倒した！"
        target_enemy.is_dead = True
        
    return msg

def _effect_fire(player, settings, dungeon, dialog):
    """範囲攻撃（炎）"""
    gx = int((player.x + player.width / 2) // dungeon.tile_size)
    gy = int((player.y + player.height / 2) // dungeon.tile_size)
    
    # ターゲットとエフェクト追加
    if settings.get("is_surround"):
        offsets = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
    else:
        offsets = settings.get("range_offsets", {}).get(player.facing, [])
    
    targets = []
    for ox, oy in offsets:
        tgx, tgy = gx + ox, gy + oy
        tx, ty = tgx * dungeon.tile_size, tgy * dungeon.tile_size
        dungeon.magic_effects.append(FireEffect(tx, ty, color=settings.get("effect_color", [255, 100, 0])))
        
        for e in dungeon.enemies:
            if not getattr(e, "is_dead", False):
                egx = int((e.x + e.width / 2) // dungeon.tile_size)
                egy = int((e.y + e.height / 2) // dungeon.tile_size)
                if egx == tgx and egy == tgy:
                    targets.append(e)

    mult = settings.get("damage_mult", 1.5)
    for t in targets:
        # 必中の魔法ダメージとして適用
        deal_damage(player, t, is_magic=True, damage_mult=mult)
            
    return f"炎が 湧き上がった！\n{len(targets)}体 の 敵 に ダメージ！"

def _effect_heal(player, settings, dungeon, dialog):
    """自己回復"""
    ratio = settings.get("heal_ratio", 0.5)
    amount = int(player.max_hp * ratio)
    old_hp = player.hp
    player.hp = min(player.max_hp, player.hp + amount)
    healed = player.hp - old_hp
    dungeon.magic_effects.append(FlashEffect(color=settings.get("effect_color", [100, 255, 100])))
    return f"体が光に包まれた！\nHP が {healed} 回復した！"

def _effect_invincible(player, settings, dungeon, dialog):
    """無敵付与"""
    turns = settings.get("duration_turns", 3)
    player.invincible_turns = turns
    dungeon.magic_effects.append(FlashEffect(color=settings.get("effect_color", [255, 255, 150])))
    return f"聖なる光が 守ってくれる！\n{turns}ターンの間 ダメージを受けない！"

def _effect_light_all(player, settings, dungeon, dialog):
    """フロア全体を明るく照らす"""
    if dungeon:
        # プレイヤーの目の前に光の演出を出す
        dx, dy = 0, 0
        if player.facing == "up": dy = -1
        elif player.facing == "down": dy = 1
        elif player.facing == "left": dx = -1
        elif player.facing == "right": dx = 1
        
        fx = player.x + dx * dungeon.tile_size
        fy = player.y + dy * dungeon.tile_size
        dungeon.magic_effects.append(DirectionalFlashEffect(fx, fy))
        
        # 全体を照らす（罠の可視化とマップ全開）
        dungeon.reveal_floor()
        return "フロア全体に まばゆい光が 広がった！\nすべての罠と マップが 見えるようになった！"
    return "しかし 何も 起こらなかった。"
