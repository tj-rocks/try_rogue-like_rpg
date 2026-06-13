import json
import os
import pygame
from constants import STAVE_DATA, COMBAT_LOG_WAIT_FRAMES
from systems.combat_handler import deal_damage

# 魔法の設定をロード
from constants import load_master_data
MAGIC_SETTINGS = load_master_data("magic_settings.yml")

# ============================================================
# 演出用エフェクトクラス
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
        super().__init__(x, y, duration=40)
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
            color_obj = pygame.Color(*self.color)
            color_obj.a = alpha
            pygame.draw.circle(s, color_obj, (rs//2, rs//2), rs//2)
            screen.blit(s, (draw_x + rx - rs//2 + 30, draw_y + ry - rs//2 + 30))

class FlashEffect(MagicEffect):
    def __init__(self, color=(255, 255, 255), duration=20):
        super().__init__(0, 0, duration)
        self.color = color

    def draw(self, screen, camera_x, camera_y):
        alpha = int(150 * (self.duration / self.max_duration))
        s = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        color_obj = pygame.Color(*self.color)
        color_obj.a = alpha
        s.fill(color_obj)
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
            c = pygame.Color(*p["color"])
            c.a = alpha
            pygame.draw.circle(s, c, (4, 4), 4)
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
        c_main = pygame.Color(*color)
        c_main.a = 100
        pygame.draw.circle(s, c_main, (radius*1.5, radius*1.5), radius*1.5)
        c_main.a = 255
        pygame.draw.circle(s, c_main, (radius*1.5, radius*1.5), radius)
        pygame.draw.circle(s, (255, 255, 255, 200), (radius*1.5, radius*1.5), radius // 2)
        screen.blit(s, (curr_x - radius*1.5, curr_y - radius*1.5))

class KnockbackEffect(MagicEffect):
    def __init__(self, x1, y1, x2, y2, color=(200, 200, 255), duration=25):
        super().__init__(x1, y1, duration=duration)
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2
        self.color = color

    def draw(self, screen, camera_x, camera_y):
        t = 1.0 - (self.duration / self.max_duration)
        
        # 衝撃波の軌跡を描画 (より大きく、明るく)
        for i in range(4):
            trail_t = max(0, t - i * 0.08)
            curr_x = self.x1 + (self.x2 - self.x1) * trail_t - camera_x + 32
            curr_y = self.y1 + (self.y2 - self.y1) * trail_t - camera_y + 32
            
            for r in range(1, 5):
                # 半径を大きくし、広がるような演出にする
                radius = r * (15 - i * 3) * (1.2 - t)
                if radius <= 0: continue
                alpha = int(220 * (self.duration / self.max_duration) / (i + 1))
                s = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
                # 外側の光
                c_outer = pygame.Color(*self.color)
                c_outer.a = alpha // 2
                pygame.draw.circle(s, c_outer, (int(radius), int(radius)), int(radius))
                # 内側の芯
                c_inner = pygame.Color(255, 255, 255, alpha)
                pygame.draw.circle(s, c_inner, (int(radius), int(radius)), int(radius // 2))
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
            c_flash = pygame.Color(*self.color)
            c_flash.a = alpha // r
            pygame.draw.circle(s, c_flash, (radius, radius), radius)
            screen.blit(s, (draw_x - radius, draw_y - radius))

def _is_fighters_full_set(player):
    """戦士シリーズフルセット装備中かどうかを判定"""
    w_inst = player._find_equip_inst(player.weapon_inventory, player.equipped_weapon)
    a_inst = player._find_equip_inst(player.armor_inventory, player.equipped_armor)
    s_inst = player._find_equip_inst(player.shield_inventory, player.equipped_shield)
    return (
        w_inst and w_inst.key == "fighters_sword"
        and a_inst and a_inst.key == "fighters_armor"
        and s_inst and s_inst.key == "fighters_sheld"
    )

def execute_stave(player, stave, dungeon, dialog):
    """杖を振った際の効果を発動させるメイン関数"""
    from constants import STAVE_DATA
    settings = STAVE_DATA.get(stave.key, {})
    if stave.charges <= 0:
        return "回数が足りない！"

    import random
    stave_bonus = int(getattr(player, "get_magic_bonus", lambda k: 0)("stave_bonus"))
    is_saved = False
    if stave_bonus > 0 and random.randint(1, 100) <= stave_bonus:
        is_saved = True

    if not is_saved:
        stave.charges -= 1
    effect_type = settings.get("effect_type")
    print(f"[MAGIC] Execute Stave: {stave.name} (Key: {stave.key}, Effect: {effect_type})")

    # 戦士フルセット + 賢者秘薬バフ中 → 杖強化
    is_enhanced = (
        getattr(player, "magic_buff_turns", 0) > 0
        and _is_fighters_full_set(player)
    )
    if is_enhanced:
        print(f"[MAGIC] Enhanced mode active! (Fighters Full Set + Sage Buff)")

    # 効果音再生
    sound_path = settings.get("sound")
    if sound_path:
        from systems.sound_handler import sound_manager
        sound_manager.play_sfx(sound_path)

    msg = f"{player.name} は {stave.name} を振った！\n"
    if is_saved:
        msg = f"{player.name} は {stave.name} を振った！（魔力が共鳴し回数を消費しなかった！）\n"
    
    if effect_type == "knockback":
        msg += _effect_knockback(player, settings, dungeon, dialog, is_enhanced)
    elif effect_type == "fire":
        msg += _effect_fire(player, settings, dungeon, dialog, is_enhanced)
    elif effect_type == "heal":
        msg += _effect_heal(player, settings, dungeon, dialog, is_enhanced)
    elif effect_type == "invincible":
        msg += _effect_invincible(player, settings, dungeon, dialog, is_enhanced)
    elif effect_type == "light_all":
        msg += _effect_light_all(player, settings, dungeon, dialog, stave, is_enhanced)
    elif effect_type == "barrier":
        msg += _effect_barrier(player, settings, dungeon, dialog, stave, is_enhanced)
    else:
        msg += "しかし 何もおきなかった！"

    return msg

def _effect_knockback(player, settings, dungeon, dialog, is_enhanced=False):
    """正面の敵を吹き飛ばす（強化時: 貫通して2体吹き飛ばす）"""
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

    # 演出1: プレイヤー位置からターゲット位置まで衝撃波が飛ぶ
    print(f"[MAGIC] Knockback Effect added: From ({gx},{gy}) to ({target_gx},{target_gy})")
    dungeon.magic_effects.append(KnockbackEffect(gx * dungeon.tile_size, gy * dungeon.tile_size, 
                                                target_gx * dungeon.tile_size, target_gy * dungeon.tile_size,
                                                color=(220, 220, 255), duration=15))

    if not target_enemy:
        return "まばゆい衝撃波を 放った！"

    # 強化時: 貫通して2体目も探索
    second_enemy = None
    if is_enhanced and target_enemy:
        # 1体目の先を探索
        scan_gx, scan_gy = target_gx + dx, target_gy + dy
        while 0 <= scan_gx < dungeon.map_width and 0 <= scan_gy < dungeon.map_height:
            if dungeon.map_data[scan_gy][scan_gx] == 0:
                break
            for e in dungeon.enemies:
                if e != target_enemy and not getattr(e, "is_dead", False):
                    egx = int((e.x + e.width / 2) // dungeon.tile_size)
                    egy = int((e.y + e.height / 2) // dungeon.tile_size)
                    if egx == scan_gx and egy == scan_gy:
                        second_enemy = e
                        break
            if second_enemy:
                break
            scan_gx += dx
            scan_gy += dy

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
 
    # 敵を移動させる（ワープさせず、高速スライディング移動させる）
    target_enemy.move_speed = 1200
    target_enemy.target_x = final_gx * dungeon.tile_size
    target_enemy.target_y = final_gy * dungeon.tile_size
    target_enemy.is_moving = True
    
    # ダメージ計算（設定値＋装備ボーナス、必中）
    base_mult = settings.get("damage_mult", 0.5)
    bonus_mult = getattr(player, "get_magic_bonus", lambda k: 0)("knockback_damage")
    msg_dmg, damage, is_crit, is_miss = deal_damage(player, target_enemy, is_magic=True, damage_mult=base_mult + bonus_mult)
    msg = f"{target_enemy.name} を 吹き飛ばした！\n" + msg_dmg
    
    # 演出2: 衝撃波エフェクトを追加
    print(f"[MAGIC] Knockback Slide added: From ({target_gx},{target_gy}) to ({final_gx},{final_gy})")
    dungeon.magic_effects.append(KnockbackEffect(target_gx * dungeon.tile_size, target_gy * dungeon.tile_size, 
                                                final_gx * dungeon.tile_size, final_gy * dungeon.tile_size,
                                                duration=20))
    
    if hit_other:
        # 衝突ダメージ（攻撃力の半分）
        dmg = int(player.attack * settings.get("collision_dmg_mult", 0.5))
        hit_other.take_damage(dmg)
        target_enemy.take_damage(dmg)
        msg += f"\n{hit_other.name} にぶつかって 両者に {dmg} ダメージ！"
        if hit_other.is_dead:
            msg += f"\n{hit_other.name} を 倒した！"
    
    if target_enemy.is_dead:
        msg += f"\n{target_enemy.name} を 倒した！"

    # 強化貫通: 2体目も吹き飛ばす
    if is_enhanced and second_enemy and not second_enemy.is_dead:
        s_gx = int((second_enemy.x + second_enemy.width / 2) // dungeon.tile_size)
        s_gy = int((second_enemy.y + second_enemy.height / 2) // dungeon.tile_size)
        s_final_gx, s_final_gy = s_gx, s_gy
        for _ in range(max_dist):
            next_gx, next_gy = s_final_gx + dx, s_final_gy + dy
            if not (0 <= next_gx < dungeon.map_width and 0 <= next_gy < dungeon.map_height) or \
               dungeon.map_data[next_gy][next_gx] == 0:
                break
            collision = False
            for e in dungeon.enemies:
                if e != second_enemy and e != target_enemy and not getattr(e, "is_dead", False):
                    egx = int((e.x + e.width / 2) // dungeon.tile_size)
                    egy = int((e.y + e.height / 2) // dungeon.tile_size)
                    if egx == next_gx and egy == next_gy:
                        collision = True
                        break
            if collision:
                break
            s_final_gx, s_final_gy = next_gx, next_gy
        second_enemy.move_speed = 1200
        second_enemy.target_x = s_final_gx * dungeon.tile_size
        second_enemy.target_y = s_final_gy * dungeon.tile_size
        second_enemy.is_moving = True
        msg_dmg2, damage2, _, _ = deal_damage(player, second_enemy, is_magic=True, damage_mult=base_mult + bonus_mult)
        msg += f"\n貫通！{second_enemy.name} も 吹き飛ばした！\n" + msg_dmg2
        if second_enemy.is_dead:
            msg += f"\n{second_enemy.name} を 倒した！"

    return msg

def _effect_fire(player, settings, dungeon, dialog, is_enhanced=False):
    """範囲攻撃（炎）（強化時: 範囲+1）"""
    gx = int((player.x + player.width / 2) // dungeon.tile_size)
    gy = int((player.y + player.height / 2) // dungeon.tile_size)

    # 装備ボーナス: 奥方向に何列伸ばすか（強化時+1）
    range_ext = int(getattr(player, "get_magic_bonus", lambda k: 0)("fire_range"))
    if is_enhanced:
        range_ext += 1

    # ターゲットとエフェクト追加
    if settings.get("is_surround"):
        offsets = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
    else:
        base_offsets = list(settings.get("range_offsets", {}).get(player.facing, []))
        # 奥方向ベクトル
        face_dx = {"up": 0, "down": 0, "left": -1, "right": 1}.get(player.facing, 0)
        face_dy = {"up": -1, "down": 1, "left": 0, "right": 0}.get(player.facing, 0)
        # 現在の最大奥行き距離を特定して延長列を追加
        if range_ext > 0 and base_offsets:
            if player.facing in ("up", "down"):
                max_depth = max(abs(oy) for ox, oy in base_offsets)
                xs = sorted(set(ox for ox, oy in base_offsets if abs(oy) == max_depth))
            else:
                max_depth = max(abs(ox) for ox, oy in base_offsets)
                xs = sorted(set(oy for ox, oy in base_offsets if abs(ox) == max_depth))
            for step in range(1, range_ext + 1):
                depth = max_depth + step
                for x in xs:
                    if player.facing in ("up", "down"):
                        base_offsets.append((x, face_dy * depth))
                    else:
                        base_offsets.append((face_dx * depth, x))
        offsets = base_offsets

    targets = []
    print(f"[MAGIC] Fire Offsets: {offsets}")
    for ox, oy in offsets:
        tgx, tgy = gx + ox, gy + oy
        tx, ty = tgx * dungeon.tile_size, tgy * dungeon.tile_size
        print(f"[MAGIC] Add FireEffect at Tile ({tgx}, {tgy})")
        dungeon.magic_effects.append(FireEffect(tx, ty, color=settings.get("effect_color", [255, 100, 0])))

        for e in dungeon.enemies:
            if not getattr(e, "is_dead", False):
                egx = int((e.x + e.width / 2) // dungeon.tile_size)
                egy = int((e.y + e.height / 2) // dungeon.tile_size)
                if egx == tgx and egy == tgy:
                    targets.append(e)

    # 装備ボーナス: ダメージ倍率加算
    mult = settings.get("damage_mult", 1.5) + getattr(player, "get_magic_bonus", lambda k: 0)("fire_damage")
    for t in targets:
        deal_damage(player, t, is_magic=True, damage_mult=mult)

    return f"炎が 湧き上がった！\n{len(targets)}体 の 敵 に ダメージ！"

def _effect_heal(player, settings, dungeon, dialog, is_enhanced=False):
    """自己回復（強化時: HP100%回復）"""
    if is_enhanced:
        # 強化版: HP全回復
        old_hp = player.hp
        player.hp = player.max_hp
        healed = player.hp - old_hp
        dungeon.magic_effects.append(FlashEffect(color=(200, 255, 200)))
        return f"強大な癒しの力が 溢れ出す！\nHP が 完全に 回復した！（+{healed}）"
    # 通常版
    ratio = settings.get("heal_ratio", 0.5) + getattr(player, "get_magic_bonus", lambda k: 0)("heal_ratio")
    amount = int(player.max_hp * ratio)
    old_hp = player.hp
    player.hp = min(player.max_hp, player.hp + amount)
    healed = player.hp - old_hp
    dungeon.magic_effects.append(FlashEffect(color=settings.get("effect_color", [100, 255, 100])))
    return f"体が光に包まれた！\nHP が {healed} 回復した！"

def _effect_invincible(player, settings, dungeon, dialog, is_enhanced=False):
    """無敵付与（強化時: ターン数2倍）"""
    # 装備ボーナス: 無敵ターン数加算
    turns = settings.get("duration_turns", 3) + int(getattr(player, "get_magic_bonus", lambda k: 0)("invincible_turns"))
    if is_enhanced:
        turns *= 2
    player.invincible_turns = turns
    dungeon.magic_effects.append(FlashEffect(color=settings.get("effect_color", [255, 255, 150])))
    return f"聖なる光が 守ってくれる！\n{turns}ターンの間 ダメージを受けない！"

def _effect_light_all(player, settings, dungeon, dialog, stave=None, is_enhanced=False):
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
        msg = "フロア全体に まばゆい光が 広がった！\nすべての罠と マップが 見えるようになった！"
        
        bonus_enhance = int(getattr(player, "get_magic_bonus", lambda k: 0)("light_stave_bonus"))
        total_enhance = (stave.enhance if stave else 0) + bonus_enhance
        
        if total_enhance > 0:
            reduction = total_enhance * 0.5
            affected = 0
            for e in dungeon.enemies:
                if not getattr(e, "is_dead", False) and not getattr(e, "is_static", False):
                    e.detect_range = max(1, e.detect_range - reduction)
                    affected += 1
            if affected > 0:
                msg += f"\n強烈な光で {affected}体の敵の 感知能力が 低下した！"
        
        # 強化版: 敵のstupidity+1（混乱しやすくなる）
        if is_enhanced:
            stupidity_affected = 0
            for e in dungeon.enemies:
                if not getattr(e, "is_dead", False) and not getattr(e, "is_static", False):
                    e.stupidity = getattr(e, "stupidity", 0) + 1
                    stupidity_affected += 1
            if stupidity_affected > 0:
                msg += f"\n眩い光が {stupidity_affected}体の敵を 混乱させた！"
                
        return msg
    return "しかし 何も 起こらなかった"

def _effect_barrier(player, settings, dungeon, dialog, stave=None, is_enhanced=False):
    """正面1マスに敵の侵入を防ぐ魔法の防壁（障害物）を配置する（強化時: 隣接敵を拘束+弱点化）"""
    gx = int((player.x + player.width / 2) // dungeon.tile_size)
    gy = int((player.y + player.height / 2) // dungeon.tile_size)
    
    dx, dy = 0, 0
    if player.facing == "up": dy = -1
    elif player.facing == "down": dy = 1
    elif player.facing == "left": dx = -1
    elif player.facing == "right": dx = 1
    
    target_gx, target_gy = gx + dx, gy + dy
    tile_size = dungeon.tile_size
    
    # 1. マップ範囲内チェック
    if not (0 <= target_gx < dungeon.map_width and 0 <= target_gy < dungeon.map_height):
        if stave: stave.charges += 1
        return "そこには 配置できない！"
        
    # 2. 壁判定チェック (1 または 4, 5, 6 のマスが床/通路であり、それ以外は配置不可)
    tile_type = dungeon.map_data[target_gy][target_gx]
    if tile_type != 1 and not (4 <= tile_type <= 6):
        if stave: stave.charges += 1
        return "そこには 配置できない！"
        
    # 3. プレイヤー自身との重複チェック
    p_grids = player.get_occupied_grids(tile_size)
    if (target_gx, target_gy) in p_grids:
        if stave: stave.charges += 1
        return "そこには 配置できない！"
        
    # 4. 既存エネミーや障害物との重複チェック (動く敵は重ねて配置して閉じ込められるようにする。静止障害物は不可)
    for e in dungeon.enemies:
        if not getattr(e, "is_dead", False):
            e_grids = e.get_occupied_grids(tile_size)
            if (target_gx, target_gy) in e_grids:
                if getattr(e, "is_static", False):
                    if stave: stave.charges += 1
                    return "そこには 配置できない！"
                
    # 5. 防壁（障害物）の生成・追加
    from components.sprites.enemy import Enemy
    barrier = Enemy(target_gx * tile_size, target_gy * tile_size, "magic_barrier", player=player)
    # タイル中央に寄せるオフセットを計算して設定
    barrier.x += (tile_size - barrier.width) // 2
    barrier.y += (tile_size - barrier.height) // 2
    barrier.target_x, barrier.target_y = barrier.x, barrier.y
    
    # 5ターン（ベース値）と装備ボーナスの加算
    base_turns = settings.get("duration_turns", 5)
    bonus_turns = int(getattr(player, "get_magic_bonus", lambda k: 0)("barrier_turns"))
    barrier.lifetime_turns = base_turns + bonus_turns
    
    dungeon.enemies.append(barrier)
    
    # 6. 召喚エフェクトの追加 (紫色の DirectionalFlashEffect)
    tx = target_gx * tile_size
    ty = target_gy * tile_size
    dungeon.magic_effects.append(DirectionalFlashEffect(tx, ty, size=tile_size, color=(200, 100, 255)))
    
    msg = f"正面の床に 魔法の防壁 が出現した！（持続: {barrier.lifetime_turns}ターン）"
    
    # 強化版: 障壁の隣接敵を拘束（移動不可）＋弱点化（被ダメ1.5倍）
    if is_enhanced:
        adjacent_offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        immobilized_count = 0
        for aox, aoy in adjacent_offsets:
            adj_gx, adj_gy = target_gx + aox, target_gy + aoy
            for e in dungeon.enemies:
                if e == barrier or getattr(e, "is_dead", False) or getattr(e, "is_static", False):
                    continue
                egx = int((e.x + e.width / 2) // tile_size)
                egy = int((e.y + e.height / 2) // tile_size)
                if egx == adj_gx and egy == adj_gy:
                    e.immobilized_turns = getattr(e, "immobilized_turns", 0) + barrier.lifetime_turns
                    e.vulnerable_mult = 1.5
                    immobilized_count += 1
        if immobilized_count > 0:
            msg += f"\n防壁の魔力が {immobilized_count}体の敵を 拘束した！\n拘束中の敵には 1.5倍のダメージ！"
    
    return msg
