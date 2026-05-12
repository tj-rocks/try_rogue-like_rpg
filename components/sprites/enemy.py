import pygame
import random
from components.sprites.entity import Entity
from constants import (
    ATTACK_ANIMATION_FRAMES, ENEMY_DATA, ENEMY_AGGRO_RADIUS, 
    ENEMY_WANDER_CHANCE, COMBAT_LOG_WAIT_FRAMES,
    ENEMY_SPAWN_SAFE_RADIUS, ENEMY_SPAWN_ATTEMPTS, ENEMY_SPAWN_SCATTER,
    ENEMY_SPAWN_MIN, ENEMY_SPAWN_MAX,
    ENEMY_SPAWN_SCALE_EVERY, ENEMY_SPAWN_SCALE_ADD,
    ENEMY_TOTAL_MAX, ENEMY_TOTAL_SCALE_EVERY, ENEMY_TOTAL_SCALE_ADD,
    ENEMY_SPAWN_NEAR_FLOOR, ENEMY_SPAWN_NEAR_RANDOM_FLOOR, ENEMY_SPAWN_NEAR_CHANCE,
    SOUND_ATTACK_HIT, SOUND_ATTACK_MISS,
    WEAPON_DATA, ARMOR_DATA, SHIELD_DATA
)
from systems.combat_handler import deal_damage

class Enemy(Entity):
    _image_cache = {}
    _scaled_image_cache = {} 
    
    @classmethod
    def clear_cache(cls):
        cls._image_cache = {}
        cls._scaled_image_cache = {}

    def __init__(self, x, y, enemy_type, width=None, height=None, player=None):
        if enemy_type not in ENEMY_DATA: enemy_type = "slime"
        data = ENEMY_DATA[enemy_type]
        from constants import TILE_SIZE
        scale = data.get("image_scale", 1.0)
        self.width = max(1, int(TILE_SIZE * scale) if width is None else width)
        self.height = max(1, int(TILE_SIZE * scale) if height is None else height)
        self.is_static = data.get("is_static", False)
        hp_val = data.get("hp", 10)
        if self.is_static and player:
            from systems.math_utils import hardcore_round
            p_atk = getattr(player, "total_attack", player.attack)
            hp_val = hardcore_round(hp_val * p_atk, is_hp=True)
            print(f"[Obstacle] {enemy_type} HP set to {hp_val}")
            
        self.attack = data.get("attack", 0)
        super().__init__(x, y, hp_val, hp_val, self.attack, self.width, self.height)
        self.type = enemy_type; self.name = data.get("name", "モンスター")
        self.defense = data.get("defense", 0); self.evasion = data.get("evasion", 0)
        self.attack_pre_delay_timer = 0; self.attack_range = data.get("attack_range", 1)
        self.exp = data.get("exp", 5); self.drops = data.get("drops", []); self.is_boss = data.get("is_boss", False)
        # ボスはアグレッシブに動くよう、stupidityを強制的に0にする
        if self.is_boss: self.stupidity = 0
        else: self.stupidity = data.get("stupidity", 0)
        self.dash_distance = data.get("dash_distance", 50)
        self.is_long_range = False; self.attack_priority = data.get("attack_priority", "close")
        self.bgm = data.get("bgm"); self.crit_rate = data.get("crit_rate", 0.01)
        self.accuracy_close = data.get("accuracy_close", data.get("accuracy_bonus", 100))
        self.accuracy_ranged = data.get("accuracy_ranged", data.get("accuracy_bonus", 100))
        self.status_to_inflict = data.get("status"); self.status_chance = data.get("status_chance", 100)
        self.detect_range = data.get("detect_range", ENEMY_AGGRO_RADIUS)
        
        color_hex = data.get("image_color"); cache_key = (enemy_type, self.width, self.height, color_hex)
        if cache_key in Enemy._image_cache: self.images = Enemy._image_cache[cache_key]
        else:
            self.images = {}; ip = data.get("image_path"); fp = data.get("image_folder", "")
            tint = None
            if color_hex:
                try: c = color_hex.lstrip('#'); tint = tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
                except: pass
            def apply_tint(s):
                if tint: ts = s.copy(); ts.fill(tint, special_flags=pygame.BLEND_RGB_MULT); return ts
                return s
            if ip:
                try:
                    img = apply_tint(pygame.transform.scale(pygame.image.load(ip).convert_alpha(), (self.width, self.height)))
                    if not self.is_static: self.images = {"up": img, "down": img, "left": img, "right": pygame.transform.flip(img, True, False)}
                    else: self.images = {d: img for d in ["up", "down", "left", "right"]}
                except: pass
            if not self.images and fp:
                for d in ["up", "down", "left", "right"]:
                    try:
                        img = apply_tint(pygame.transform.scale(pygame.image.load(f"{fp}/{d}.png").convert_alpha(), (self.width, self.height)))
                        self.images[d] = img
                    except:
                        if d == "right" and not self.is_static and "left" in self.images: self.images[d] = pygame.transform.flip(self.images["left"], True, False)
                        else: self.images[d] = pygame.Surface((self.width, self.height))
            if not self.images: self.images = {d: pygame.Surface((self.width, self.height)) for d in ["up", "down", "left", "right"]}
            Enemy._image_cache[cache_key] = self.images

    def draw(self, screen, camera_x, camera_y):
        import math; draw_x, draw_y = self.x - camera_x, self.y - camera_y
        if self.is_attacking:
            off = 0
            if self.attack_pre_delay_timer > 0:
                from constants import ATTACK_PRE_DELAY_FRAMES
                p = (ATTACK_PRE_DELAY_FRAMES - self.attack_pre_delay_timer) / ATTACK_PRE_DELAY_FRAMES
                off = -15 * p + (2 * math.sin(self.attack_pre_delay_timer * 2) if self.attack_pre_delay_timer < 15 else 0)
            elif getattr(self, "attack_timer", 0) > 0 and getattr(self, "current_attack_pattern", {}).get("type") == "close":
                from constants import ATTACK_ANIMATION_FRAMES
                t = (ATTACK_ANIMATION_FRAMES - self.attack_timer) / ATTACK_ANIMATION_FRAMES
                off = -15 + ((self.dash_distance + 15) * (t / 0.2)) if t <= 0.2 else self.dash_distance * (1 - (t - 0.2) / 0.8)
            if self.facing == "up": draw_y -= off
            elif self.facing == "down": draw_y += off
            elif self.facing == "left": draw_x -= off
            elif self.facing == "right": draw_x += off
        
        if self.is_attacking and getattr(self, "is_long_range", False) and self.attack_pre_delay_timer > 0:
            draw_x += 3 * math.sin(self.attack_pre_delay_timer * 3)
            pygame.draw.circle(screen, (255, 255, 255, 100), (draw_x + self.width//2, draw_y + self.height//2), 30 + 10 * math.sin(self.attack_pre_delay_timer * 0.2), 2)
        
        (sx, sy), ph = self.get_breathing_scale() if not (self.is_attacking or self.is_static) else ((1.0, 1.0), 0)
        if -self.width <= draw_x <= screen.get_width() and -self.height <= draw_y <= screen.get_height():
            base = self.images.get(self.facing, pygame.Surface((self.width, self.height)))
            ck = (base, "attack" if self.is_attacking else ph)
            cur = Enemy._scaled_image_cache.get(ck)
            if cur is None:
                if self.is_attacking: cur = pygame.transform.scale(base, (int(base.get_width() * 1.2), int(base.get_height() * 1.2)))
                elif not self.is_static: cur = pygame.transform.smoothscale(base, (int(base.get_width() * sx), int(base.get_height() * sy)))
                else: cur = base
                Enemy._scaled_image_cache[ck] = cur
            draw_x += (self.width - cur.get_width()) / 2; draw_y += (self.height - cur.get_height())
            from constants import HIT_STUN_DURATION
            if not (self.damage_flash_timer > HIT_STUN_DURATION and (self.damage_flash_timer - HIT_STUN_DURATION) % 4 < 2):
                screen.blit(cur, (draw_x, draw_y))

    def _move_randomly(self, dungeon, all_entities):
        d = random.choice([("right", dungeon.tile_size, 0), ("left", -dungeon.tile_size, 0), ("down", 0, dungeon.tile_size), ("up", 0, -dungeon.tile_size)])
        tx, ty = self.x + d[1], self.y + d[2]
        if self.can_move_grid(tx, ty, dungeon): self.target_x, self.target_y, self.facing, self.is_moving, self.step_toggle = tx, ty, d[0], True, not self.step_toggle

    def _is_in_attack_range(self, dx, dy): return (abs(dx) <= self.attack_range and dy == 0 and dx != 0) or (abs(dy) <= self.attack_range and dx == 0 and dy != 0)

    def _handle_attack(self, dx, dy, player, dialog=None):
        fn = self.facing
        if dx > 0: fn = "right"
        elif dx < 0: fn = "left"
        elif dy > 0: fn = "down"
        elif dy < 0: fn = "up"
        if self.facing != fn: self.facing = fn
        else:
            from constants import ATTACK_PRE_DELAY_FRAMES
            self.attack_pre_delay_timer = ATTACK_PRE_DELAY_FRAMES; self.is_attacking = True; self.is_long_range = (abs(dx)+abs(dy) > 1)
            self.target_for_attack, self.dialog_for_attack = player, dialog

    def _is_line_of_sight_clear(self, dx, dy, dungeon, all_entities):
        sx, sy = (1 if dx > 0 else -1 if dx < 0 else 0), (1 if dy > 0 else -1 if dy < 0 else 0)
        gx, gy = int((self.x + self.width/2)//dungeon.tile_size), int((self.y + self.height/2)//dungeon.tile_size)
        for i in range(1, abs(dx)+abs(dy)):
            cx, cy = gx + sx*i, gy + sy*i
            if not (0 <= cx < dungeon.map_width and 0 <= cy < dungeon.map_height) or dungeon.map_data[cy][cx] == 0: return False
            for e in all_entities:
                from components.sprites.player import Player
                if not (e == self or getattr(e, "is_dead", False) or isinstance(e, Player)) and int((e.x + e.width/2)//dungeon.tile_size) == cx and int((e.y + e.height/2)//dungeon.tile_size) == cy: return False
        return True

    def _execute_actual_attack(self, player, dungeon, dialog):
        from constants import ATTACK_ANIMATION_FRAMES, ATTACK_EFFECT_DATA
        self.is_attacking = True; self.attack_timer = ATTACK_ANIMATION_FRAMES; self.has_dealt_impact_damage = False
        spec = ENEMY_DATA.get(self.type, {}); pk = spec.get("ranged_attack_effect" if getattr(self, "is_long_range", False) else "close_attack_effect")
        self.current_attack_pattern = ATTACK_EFFECT_DATA.get(pk, {})
        from systems.sound_handler import sound_manager
        sound_manager.play_sfx(self.current_attack_pattern.get("launch_sound", "components/sounds/sfx/enemy_attack_common.wav"))
        vt = self.current_attack_pattern.get("visual")
        if vt:
            if vt == "explosion": from systems.magic_handler import FireEffect; dungeon.magic_effects.append(FireEffect(player.x, player.y))
            else: from systems.magic_handler import ProjectileEffect; dungeon.magic_effects.append(ProjectileEffect(self.x, self.y, player.x, player.y, vt, ATTACK_ANIMATION_FRAMES))
        if self.current_attack_pattern.get("type") == "close":
            from constants import TILE_SIZE
            mx, my = int((self.x+self.width/2)//TILE_SIZE), int((self.y+self.height/2)//TILE_SIZE)
            px, py = int((player.x+player.width/2)//TILE_SIZE), int((player.y+player.height/2)//TILE_SIZE)
            self.dash_distance = (abs(px-mx)+abs(py-my) - (self.width/TILE_SIZE/2 + player.width/TILE_SIZE/2) + 1) * TILE_SIZE
        else: self.dash_distance = 0

    def _deal_impact_damage(self, dungeon):
        t, d = getattr(self, "target_for_attack", None), getattr(self, "dialog_for_attack", None); self.peak_hold_timer = 30
        if not t or t.is_dead: return
        from constants import COMBAT_LOG_WAIT_FRAMES; msg, dmg, crit, miss = deal_damage(self, t)
        from systems.sound_handler import sound_manager
        sound_manager.play_sfx(SOUND_ATTACK_MISS if miss or dmg == 0 else (self.current_attack_pattern.get("hit_sound", "components/sounds/sfx/projectile_hit.wav")))
        if crit: dungeon.flash_timer = 10
        if d:
            from systems.game_state import game_state
            if d.is_active: d.text += "\n" + msg; d.auto_close_timer = COMBAT_LOG_WAIT_FRAMES
            else: d.text = msg; d.is_active = True; game_state["dialog_modal"] = False; d.auto_close_timer = COMBAT_LOG_WAIT_FRAMES

    def _move_smartly_check_success(self, player, dungeon, all_entities, px, py, mx, my, occs=None, ideal=None):
        if ideal is None: ideal = max(0, self.attack_range - 1)
        pdx, pdy = (1 if player.facing == "right" else -1 if player.facing == "left" else 0), (1 if player.facing == "down" else -1 if player.facing == "up" else 0)
        ppx, ppy = px + pdx, py + pdy; cur_s = abs(abs(ppx-mx)+abs(ppy-my) - ideal); valid = []
        for f, dx, dy in [("right",dungeon.tile_size,0),("left",-dungeon.tile_size,0),("down",0,dungeon.tile_size),("up",0,-dungeon.tile_size)]:
            tx, ty = self.x+dx, self.y+dy
            if self.can_move_grid(tx, ty, dungeon):
                tgx, tgy = int((tx+self.width/2)//dungeon.tile_size), int((ty+self.height/2)//dungeon.tile_size)
                s = abs(abs(ppx-tgx)+abs(ppy-tgy) - ideal)
                if s <= cur_s: valid.append({"f":f, "dx":dx, "dy":dy, "s":s, "dc":abs(abs(px-tgx)+abs(py-tgy) - self.attack_range)})
        if valid:
            valid.sort(key=lambda m: (m["s"], m["dc"])); best_s = valid[0]["s"]
            chosen = random.choice([m for m in valid if m["s"] == best_s])
            if chosen["s"] < cur_s or random.random() < 0.5: self.target_x, self.target_y, self.facing, self.is_moving, self.step_toggle = self.x+chosen["dx"], self.y+chosen["dy"], chosen["f"], True, not self.step_toggle; return True
        return False

    def take_turn(self, player, dungeon, all_entities, dialog=None, occupied_cells=None):
        if getattr(self, "is_dead", False) or self.is_static: return
        mx, my = int((self.x+self.width/2)//dungeon.tile_size), int((self.y+self.height/2)//dungeon.tile_size)
        px, py = int((player.target_x+player.width/2)//dungeon.tile_size), int((player.target_y+player.height/2)//dungeon.tile_size)
        
        # [NEW] 大型モンスター対応: 自分の占有グリッドの中からプレイヤーに最も近いものを選ぶ
        my_grids = self.get_occupied_grids_at(self.x, self.y, dungeon.tile_size)
        best_dx, best_dy = px - mx, py - my
        min_gdist = abs(best_dx) + abs(best_dy)
        for gx, gy in my_grids:
            tdx, tdy = px - gx, py - gy
            tgdist = abs(tdx) + abs(tdy)
            if tgdist < min_gdist:
                min_gdist = tgdist
                best_dx, best_dy = tdx, tdy
        
        dx, dy = best_dx, best_dy
        rad = max(1, self.detect_range + player.get_aggro_modifier())
        if getattr(self, "damage_flash_timer", 0) > 0: rad = max(rad, 100)
        if abs(dx) > rad or abs(dy) > rad: return
        if self.stupidity > 0 and random.randint(1,10) <= self.stupidity: self._move_randomly(dungeon, all_entities); return
        if self.stupidity < 7:
            ideal = 1 if self.attack_priority == "close" else (2 if self.attack_range == 2 else max(1, self.attack_range - 1))
            los = self._is_in_attack_range(dx, dy) and self._is_line_of_sight_clear(dx, dy, dungeon, all_entities); gdist = abs(dx)+abs(dy)
            if gdist == ideal:
                if los: self._handle_attack(dx, dy, player, dialog); return
                if self._move_smartly_check_success(player, dungeon, all_entities, px, py, mx, my, occupied_cells, ideal): return
            elif gdist == 1 and self.attack_priority == "ranged" and self.attack_range > 1:
                if random.random() < 0.7 and self._move_smartly_check_success(player, dungeon, all_entities, px, py, mx, my, occupied_cells, ideal): return
                self._handle_attack(dx, dy, player, dialog); return
            else:
                if los: self._handle_attack(dx, dy, player, dialog); return
                if self._move_smartly_check_success(player, dungeon, all_entities, px, py, mx, my, occupied_cells, ideal): return

    def update(self, dungeon, dt=1/60):
        if self.is_static: self.update_animation(dt); return
        if self.attack_pre_delay_timer > 0:
            self.attack_pre_delay_timer -= 1
            if self.attack_pre_delay_timer == 0:
                t, d = getattr(self, "target_for_attack", None), getattr(self, "dialog_for_attack", None)
                if t and not t.is_dead: self._execute_actual_attack(t, dungeon, d)
                else: self.is_attacking = False
        if self.is_attacking and self.attack_pre_delay_timer == 0:
            impact = int(ATTACK_ANIMATION_FRAMES * 0.8)
            if getattr(self, "attack_timer", 0) <= impact and not getattr(self, "has_dealt_impact_damage", False):
                self._deal_impact_damage(dungeon); self.has_dealt_impact_damage = True
        self.update_animation(dt)

    def update_animation(self, dt=1/60):
        self.idle_anim_timer = (self.idle_anim_timer + 1) % 60
        if getattr(self, "attack_pre_delay_timer", 0) > 0:
            if getattr(self, "damage_flash_timer", 0) > 0: self.damage_flash_timer -= 1
            if self.process_movement(dt): self.move_speed = 300
            return
        if getattr(self, "peak_hold_timer", 0) > 0:
            self.peak_hold_timer -= 1
            if getattr(self, "damage_flash_timer", 0) > 0: self.damage_flash_timer -= 1
            if self.process_movement(dt): self.move_speed = 300
            return
        super().update_animation(dt)
        if not self.is_moving: self.move_speed = 300

    @classmethod
    def spawn_enemies(cls, dungeon, player=None):
        from constants import (ENEMY_SPAWN_MIN, ENEMY_SPAWN_MAX, ENEMY_SPAWN_ATTEMPTS, ENEMY_SPAWN_SAFE_RADIUS, ENEMY_SPAWN_SCATTER, ENEMY_DATA, ENEMY_TOTAL_MAX, ENEMY_TOTAL_SCALE_EVERY, ENEMY_TOTAL_SCALE_ADD, OBSTACLE_SPAWN_MIN, OBSTACLE_SPAWN_MAX, OBSTACLE_SPAWN_SCALE_EVERY, OBSTACLE_SPAWN_SCALE_ADD, OBSTACLE_SPAWN_LIMIT, OBSTACLE_TOTAL_MAX, OBSTACLE_TOTAL_SCALE_EVERY, OBSTACLE_TOTAL_SCALE_ADD)
        enemies = []; floor = getattr(dungeon, "current_floor", 1); pgx, pgy = (int(player.x//dungeon.tile_size), int(player.y//dungeon.tile_size)) if player else (-999,-999)
        mt = [k for k, v in ENEMY_DATA.items() if not v.get("is_static", False)]; ot = [k for k, v in ENEMY_DATA.items() if v.get("is_static", False)]
        ef = min(floor, OBSTACLE_SPAWN_LIMIT); nr = len(dungeon.rooms)
        m_cap = int(nr * ENEMY_TOTAL_MAX) + (floor-1)//ENEMY_TOTAL_SCALE_EVERY * ENEMY_TOTAL_SCALE_ADD
        o_cap = int(nr * OBSTACLE_TOTAL_MAX) + (ef-1)//OBSTACLE_TOTAL_SCALE_EVERY * OBSTACLE_TOTAL_SCALE_ADD
        for idx, room in enumerate(dungeon.rooms):
            if random.random() < 0.1: continue
            isr = (idx == getattr(dungeon, "start_room_idx", -1) or idx == getattr(dungeon, "target_room_idx", -1))
            s_min, s_max = (ENEMY_SPAWN_MIN//2, max(1, ENEMY_SPAWN_MAX//2)) if isr else (ENEMY_SPAWN_MIN, ENEMY_SPAWN_MAX)
            for _ in range(random.randint(s_min, s_max)):
                if sum(1 for e in enemies if not e.is_static) >= m_cap: break
                for att in range(ENEMY_SPAWN_ATTEMPTS*2):
                    ex, ey = random.randint(room[0]-ENEMY_SPAWN_SCATTER, room[0]+ENEMY_SPAWN_SCATTER), random.randint(room[1]-ENEMY_SPAWN_SCATTER, room[1]+ENEMY_SPAWN_SCATTER)
                    if abs(ex-pgx) <= ENEMY_SPAWN_SAFE_RADIUS and abs(ey-pgy) <= ENEMY_SPAWN_SAFE_RADIUS: continue
                    if 0 <= ey < dungeon.map_height and 0 <= ex < dungeon.map_width and dungeon.map_data[ey][ex] == 1:
                        if not any((ex, ey) in e.get_occupied_grids(dungeon.tile_size) for e in enemies):
                            vm = [m for m in mt if ENEMY_DATA[m].get("min_floor", 1) <= floor <= ENEMY_DATA[m].get("max_floor", 999)]
                            if vm:
                                mtp = random.choice(vm); nm = Enemy(ex*dungeon.tile_size, ey*dungeon.tile_size, mtp, player=player)
                                nm.x += (dungeon.tile_size-nm.width)//2; nm.y += (dungeon.tile_size-nm.height)//2; nm.target_x, nm.target_y = nm.x, nm.y; enemies.append(nm); dungeon.spawn_counts[mtp] = dungeon.spawn_counts.get(mtp,0)+1; break
            for _ in range(random.randint(OBSTACLE_SPAWN_MIN, OBSTACLE_SPAWN_MAX + (ef-1)//OBSTACLE_SPAWN_SCALE_EVERY * OBSTACLE_SPAWN_SCALE_ADD)):
                if sum(1 for e in enemies if e.is_static) >= o_cap: break
                for att in range(ENEMY_SPAWN_ATTEMPTS):
                    ex, ey = random.randint(room[0]-ENEMY_SPAWN_SCATTER, room[0]+ENEMY_SPAWN_SCATTER), random.randint(room[1]-ENEMY_SPAWN_SCATTER, room[1]+ENEMY_SPAWN_SCATTER)
                    if 0 <= ey < dungeon.map_height and 0 <= ex < dungeon.map_width and dungeon.map_data[ey][ex] == 1:
                        if not any(int((e.x+e.width/2)//dungeon.tile_size) == ex and int((e.y+e.height/2)//dungeon.tile_size) == ey for e in enemies):
                            vo = [o for o in ot if ENEMY_DATA[o].get("min_floor",1) <= floor <= ENEMY_DATA[o].get("max_floor",999)]
                            if vo:
                                otp = random.choice(vo); no = Enemy(ex*dungeon.tile_size, ey*dungeon.tile_size, otp, player=player)
                                no.x += (dungeon.tile_size-no.width)//2; no.y += (dungeon.tile_size-no.height)//2; no.target_x, no.target_y = no.x, no.y; enemies.append(no); break
        cls.log_population(dungeon, "Warped", override_enemies=enemies); return enemies

    @classmethod
    def log_population(cls, dungeon, reason, override_enemies=None):
        from constants import (ENEMY_TOTAL_MAX, ENEMY_TOTAL_SCALE_EVERY, ENEMY_TOTAL_SCALE_ADD, OBSTACLE_TOTAL_MAX, OBSTACLE_TOTAL_SCALE_EVERY, OBSTACLE_TOTAL_SCALE_ADD, OBSTACLE_SPAWN_LIMIT)
        f = getattr(dungeon, "current_floor", 1); nr = len(getattr(dungeon, "rooms", [])); ef = min(f, OBSTACLE_SPAWN_LIMIT)
        mc = int(nr * ENEMY_TOTAL_MAX) + (f-1)//ENEMY_TOTAL_SCALE_EVERY * ENEMY_TOTAL_SCALE_ADD
        oc = int(nr * OBSTACLE_TOTAL_MAX) + (ef-1)//OBSTACLE_TOTAL_SCALE_EVERY * OBSTACLE_TOTAL_SCALE_ADD
        tl = override_enemies if override_enemies is not None else getattr(dungeon, "enemies", [])
        cm, co = sum(1 for e in tl if not getattr(e, "is_static", False)), sum(1 for e in tl if getattr(e, "is_static", False))
        print(f"[POPULATION] Floor {f} | Rooms: {nr} | Monsters: {cm}/{mc} | Obstacles: {co}/{oc} | Reason: {reason}")

    @classmethod
    def spawn_one(cls, dungeon, player):
        from constants import ENEMY_TOTAL_MAX, ENEMY_TOTAL_SCALE_EVERY, ENEMY_TOTAL_SCALE_ADD
        f = getattr(dungeon, "current_floor", 1); nr = len(dungeon.rooms); mc = int(nr * ENEMY_TOTAL_MAX) + (f-1)//ENEMY_TOTAL_SCALE_EVERY * ENEMY_TOTAL_SCALE_ADD
        if sum(1 for e in dungeon.enemies if not e.is_static) >= mc: return
