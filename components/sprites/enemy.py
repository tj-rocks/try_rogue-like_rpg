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
    WEAPON_DATA, ARMOR_DATA, SHIELD_DATA,
    STUPIDITY_WANDER_RATES, ENEMY_ESCAPE_BLOCK_ENABLED
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
        self.flip = False
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
        # ボスはアグレッシブに動くよう、困惑度（stupidity）を強制的に0にする
        if self.is_boss: self.stupidity = 0
        else: self.stupidity = data.get("stupidity", 0)
        self.dash_distance = data.get("dash_distance", 50)
        self.is_long_range = False; self.attack_priority = data.get("attack_priority", "close")
        self.smart_ranged_move = data.get("smart_ranged_move", True)
        self.bgm = data.get("bgm"); self.crit_rate = data.get("crit_rate", 0.01)
        self.accuracy_close = data.get("accuracy_close", data.get("accuracy_bonus", 100))
        self.accuracy_ranged = data.get("accuracy_ranged", data.get("accuracy_bonus", 100))
        self.status_to_inflict = data.get("status"); self.status_chance = data.get("status_chance", 100)
        self.detect_range = data.get("detect_range", ENEMY_AGGRO_RADIUS)
        self.damaged_detect_range = data.get("damaged_detect_range", 100)
        
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

    def _log_trace(self, dungeon, msg):
        try:
            with open("enemy_ai.log", "a", encoding="utf-8") as f:
                floor = getattr(dungeon, 'current_floor', '?')
                f.write(f"[Floor {floor}] [{self.name}#{id(self)%10000}] at ({int(self.x//dungeon.tile_size)}, {int(self.y//dungeon.tile_size)}): {msg}\n")
            import constants
            if constants.ENABLE_DEBUG_LOGGING:
                print(f"[TRACE-AI] [{self.name}#{id(self)%10000}]: {msg}")
        except:
            pass

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
            is_flipped = getattr(self, "flip", False)
            base = self.images.get(self.facing, pygame.Surface((self.width, self.height)))
            ck = (base, "attack" if self.is_attacking else ph, is_flipped)
            cur = Enemy._scaled_image_cache.get(ck)
            if cur is None:
                if self.is_attacking: cur = pygame.transform.scale(base, (int(base.get_width() * 1.2), int(base.get_height() * 1.2)))
                elif not self.is_static: cur = pygame.transform.smoothscale(base, (int(base.get_width() * sx), int(base.get_height() * sy)))
                else: cur = base
                
                if is_flipped:
                    cur = pygame.transform.flip(cur, True, False)
                Enemy._scaled_image_cache[ck] = cur
            draw_x += (self.width - cur.get_width()) / 2; draw_y += (self.height - cur.get_height())
            from constants import HIT_STUN_DURATION
            if not (self.damage_flash_timer > HIT_STUN_DURATION and (self.damage_flash_timer - HIT_STUN_DURATION) % 4 < 2):
                screen.blit(cur, (draw_x, draw_y))

    def _move_randomly(self, dungeon, all_entities):
        d = random.choice([("right", dungeon.tile_size, 0), ("left", -dungeon.tile_size, 0), ("down", 0, dungeon.tile_size), ("up", 0, -dungeon.tile_size)])
        tx, ty = self.x + d[1], self.y + d[2]
        if self.can_move_grid(tx, ty, dungeon, debug_log=True):
            self.target_x, self.target_y, self.facing, self.is_moving, self.step_toggle = tx, ty, d[0], True, not self.step_toggle
        else:
            self._log_trace(dungeon, f"_move_randomly: failed to move to {d[0]} ({tx//dungeon.tile_size}, {ty//dungeon.tile_size})")

    def _is_in_attack_range(self, dx, dy): return (abs(dx) <= self.attack_range and dy == 0 and dx != 0) or (abs(dy) <= self.attack_range and dx == 0 and dy != 0)

    def _handle_attack(self, dx, dy, player, dialog=None):
        if dx > 0: self.facing = "right"
        elif dx < 0: self.facing = "left"
        elif dy > 0: self.facing = "down"
        elif dy < 0: self.facing = "up"
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
        cur_s = abs(abs(px-mx)+abs(py-my) - ideal); valid = []
        for f, dx, dy in [("right",dungeon.tile_size,0),("left",-dungeon.tile_size,0),("down",0,dungeon.tile_size),("up",0,-dungeon.tile_size)]:
            tx, ty = self.x+dx, self.y+dy
            if self.can_move_grid(tx, ty, dungeon):
                tgx, tgy = int((tx+self.width/2)//dungeon.tile_size), int((ty+self.height/2)//dungeon.tile_size)
                s = abs(abs(px-tgx)+abs(py-tgy) - ideal)
                if s <= cur_s: valid.append({"f":f, "dx":dx, "dy":dy, "s":s, "dc":abs(abs(px-tgx)+abs(py-tgy) - self.attack_range)})
        if valid:
            valid.sort(key=lambda m: (m["s"], m["dc"])); best_s = valid[0]["s"]
            if best_s < cur_s:
                chosen = random.choice([m for m in valid if m["s"] == best_s])
                self.target_x, self.target_y, self.facing, self.is_moving, self.step_toggle = self.x+chosen["dx"], self.y+chosen["dy"], chosen["f"], True, not self.step_toggle
                self._log_trace(dungeon, f"_move_smartly: chose movement to {chosen['f']} ({self.target_x//dungeon.tile_size}, {self.target_y//dungeon.tile_size})")
                return True
        return False

    # ════════════════════════════════════════════════════════════════
    # [ESCAPE_BLOCK] 逃げ道封鎖AI
    # 削除する場合: このメソッドと take_turn 内の [ESCAPE_BLOCK] ブロックをセットで消す
    # ════════════════════════════════════════════════════════════════
    def _get_escape_block_target(self, px, py, all_entities, dungeon):
        """プレイヤーが逃げられる隣接タイルのうち、他の敵が向かっていないものを返す。
        自分がプレイヤーに近い側ではなく、遠い側（退路の先）を優先する。"""
        mx = int((self.x + self.width / 2) // dungeon.tile_size)
        my = int((self.y + self.height / 2) // dungeon.tile_size)
        dx_to_player = px - mx
        dy_to_player = py - my

        # プレイヤーが実際に移動できる隣接タイルを列挙（逃げ道候補）
        escape_tiles = []
        for ex, ey in [(px, py-1), (px, py+1), (px-1, py), (px+1, py)]:
            if not (0 <= ex < dungeon.map_width and 0 <= ey < dungeon.map_height): continue
            if dungeon.map_data[ey][ex] != 1: continue
            escape_tiles.append((ex, ey))

        if not escape_tiles:
            return None

        # 他の敵が既に向かっているマスを除外（全stupidity対象）
        claimed = set()
        for e in all_entities:
            if e is self or not isinstance(e, Enemy) or getattr(e, "is_dead", False): continue
            ex = int(((e.target_x if getattr(e, "is_moving", False) else e.x) + e.width / 2) // dungeon.tile_size)
            ey = int(((e.target_y if getattr(e, "is_moving", False) else e.y) + e.height / 2) // dungeon.tile_size)
            claimed.add((ex, ey))

        # スコアリング: 自分と反対側の退路タイルを優先（挟み撃ち）
        best, best_score = None, float("inf")
        for ex, ey in escape_tiles:
            if (ex, ey) in claimed: continue
            fdx, fdy = ex - px, ey - py
            dot = fdx * dx_to_player + fdy * dy_to_player   # 負 = 自分の反対側
            self_dist = abs(mx - ex) + abs(my - ey)
            score = (0 if dot <= 0 else 10) + self_dist * 0.1
            if score < best_score:
                best_score = score
                best = (ex, ey)
        return best
    # [/ESCAPE_BLOCK] ════════════════════════════════════════════════

    def _get_flank_target(self, px, py, all_entities, dungeon):
        """包囲行動用: プレイヤー隣接マスのうち、他の敵が向かっていないマスを返す。
        自分のグリッド位置から見てプレイヤーの「反対側」を優先する。"""
        mx = int((self.x + self.width / 2) // dungeon.tile_size)
        my = int((self.y + self.height / 2) // dungeon.tile_size)

        # プレイヤー隣接4マス
        adjacent = [
            (px,     py - 1, "up"),
            (px,     py + 1, "down"),
            (px - 1, py,     "left"),
            (px + 1, py,     "right"),
        ]

        # 他の敵が「向かっている」グリッドを集める（全stupidity対象）
        claimed = set()
        for e in all_entities:
            if e is self or not isinstance(e, Enemy) or getattr(e, "is_dead", False): continue
            # 移動先グリッドを推定（target_x があれば使う）
            if getattr(e, "is_moving", False):
                ex = int((e.target_x + e.width / 2) // dungeon.tile_size)
                ey = int((e.target_y + e.height / 2) // dungeon.tile_size)
            else:
                ex = int((e.x + e.width / 2) // dungeon.tile_size)
                ey = int((e.y + e.height / 2) // dungeon.tile_size)
            claimed.add((ex, ey))

        # 自分からプレイヤーへのベクトル
        dx_to_player = px - mx
        dy_to_player = py - my

        def score(ax, ay, _dir):
            if not (0 <= ax < dungeon.map_width and 0 <= ay < dungeon.map_height): return 999
            if dungeon.map_data[ay][ax] != 1: return 999          # 壁は除外
            if (ax, ay) in claimed: return 100                    # 被りは避ける
            # 自分と「逆方向」にいるマスを優先（挟み撃ち）
            flank_dx = ax - px  # プレイヤー中心から見た方向
            flank_dy = ay - py
            # dot product が負 = 自分と反対側 = 有利な包囲マス
            dot = flank_dx * dx_to_player + flank_dy * dy_to_player
            return 0 if dot <= 0 else 1

        candidates = sorted(adjacent, key=lambda t: score(t[0], t[1], t[2]))
        best = candidates[0]
        if score(best[0], best[1], best[2]) >= 100:
            return None   # 全マス被りまたは壁なら通常行動
        return best[0], best[1]  # (target_gx, target_gy)

    def _move_toward_grid(self, tgx, tgy, dungeon, all_entities):
        """指定グリッドに1歩近づく。直進が塞がれている場合は横移動など迂回ルートも試す。"""
        mx = int((self.x + self.width / 2) // dungeon.tile_size)
        my = int((self.y + self.height / 2) // dungeon.tile_size)
        dx = tgx - mx; dy = tgy - my
        
        # 進行方向と、その直角方向を決定する
        dir_x = "right" if dx > 0 else "left" if dx < 0 else random.choice(["right", "left"])
        dir_y = "down" if dy > 0 else "up" if dy < 0 else random.choice(["down", "up"])
        
        step_x = (dir_x, dungeon.tile_size if dir_x == "right" else -dungeon.tile_size, 0)
        step_y = (dir_y, 0, dungeon.tile_size if dir_y == "down" else -dungeon.tile_size)
        
        # 距離が遠い軸を優先的に進む
        if abs(dx) > abs(dy):
            steps = [step_x, step_y]
        elif abs(dy) > abs(dx):
            steps = [step_y, step_x]
        else:
            steps = [step_x, step_y] if random.random() < 0.5 else [step_y, step_x]
            
        # x軸またはy軸が揃っている（dx==0 or dy==0）場合でも、前方が味方で塞がっている時は
        # 横に避けて進めるように、直角方向の逆側もフォールバックとして追加する
        if dx == 0:
            alt_x = "left" if dir_x == "right" else "right"
            steps.append((alt_x, dungeon.tile_size if alt_x == "right" else -dungeon.tile_size, 0))
        if dy == 0:
            alt_y = "up" if dir_y == "down" else "down"
            steps.append((alt_y, 0, dungeon.tile_size if alt_y == "down" else -dungeon.tile_size))

        for facing, sdx, sdy in steps:
            tx, ty = self.x + sdx, self.y + sdy
            # can_move_grid がすでに地形と他エンティティ（味方含む）との衝突を判定している
            if self.can_move_grid(tx, ty, dungeon, debug_log=True):
                self.target_x, self.target_y = tx, ty
                self.facing = facing; self.is_moving = True
                self.step_toggle = not self.step_toggle
                self._log_trace(dungeon, f"_move_toward_grid: moving to {facing} ({tx//dungeon.tile_size}, {ty//dungeon.tile_size})")
                return True
            else:
                self._log_trace(dungeon, f"_move_toward_grid: failed step to {facing} ({tx//dungeon.tile_size}, {ty//dungeon.tile_size})")
                
        return False

    def take_turn(self, player, dungeon, all_entities, dialog=None, occupied_cells=None):
        if getattr(self, "is_dead", False):
            self._log_trace(dungeon, "take_turn bypassed: is_dead=True")
            return
        if self.is_static:
            self._log_trace(dungeon, "take_turn bypassed: is_static=True")
            if hasattr(self, "lifetime_turns") and self.lifetime_turns is not None:
                self.lifetime_turns -= 1
                if self.lifetime_turns <= 0:
                    self.is_dead = True
                    if dialog:
                        from constants import COMBAT_LOG_WAIT_FRAMES
                        msg = f"{self.name} は 消滅した！"
                        if dialog.is_active:
                            dialog.text += "\n" + msg
                        else:
                            dialog.text = msg
                            dialog.is_active = True
                        dialog.auto_close_timer = COMBAT_LOG_WAIT_FRAMES
            return

        # 魔法の防壁（magic_barrier）に囚われているかチェック
        my_grids = self.get_occupied_grids_at(self.x, self.y, dungeon.tile_size)
        for e in dungeon.enemies:
            if e != self and not getattr(e, "is_dead", False) and getattr(e, "is_static", False) and getattr(e, "type", "") == "magic_barrier":
                e_grids = e.get_occupied_grids(dungeon.tile_size)
                if any(g in e_grids for g in my_grids):
                    # 閉じ込められているため、ターンをスキップ（攻撃も移動も行わない）
                    self._log_trace(dungeon, "is trapped in magic_barrier. Skipping turn.")
                    return

        # 拘束状態チェック（移動不可だが隣接時は攻撃可能）
        if getattr(self, "immobilized_turns", 0) > 0:
            self.immobilized_turns -= 1
            if self.immobilized_turns <= 0:
                self.vulnerable_mult = 1.0  # 弱点化も解除
            mx, my = int((self.x+self.width/2)//dungeon.tile_size), int((self.y+self.height/2)//dungeon.tile_size)
            px, py = int((player.target_x+player.width/2)//dungeon.tile_size), int((player.target_y+player.height/2)//dungeon.tile_size)
            dx, dy = px - mx, py - my
            if abs(dx) + abs(dy) <= 1:
                self._handle_attack(dx, dy, player, dialog)
            else:
                self._log_trace(dungeon, f"immobilized ({self.immobilized_turns} turns left). Cannot move.")
            return

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
        rad = max(1, self.detect_range - player.get_aggro_modifier())
        if getattr(self, "damage_flash_timer", 0) > 0: rad = max(rad, self.damaged_detect_range)
        
        # 感知範囲外チェック
        if abs(dx) > rad or abs(dy) > rad:
            self._log_trace(dungeon, f"out of range (dist to player: {abs(dx)},{abs(dy)} > detect_range: {rad}) | self:({self.x},{self.y}) player_target:({player.target_x},{player.target_y}) player_actual:({player.x},{player.y}) ts:{dungeon.tile_size}")
            return
            
        # 困惑度テーブルを参照してぼーっと確率を決定
        wander_chance = STUPIDITY_WANDER_RATES.get(self.stupidity, self.stupidity / 10.0)
        if wander_chance > 0 and random.random() < wander_chance:
            self._log_trace(dungeon, f"decided to WANDER (chance: {wander_chance})")
            self._move_randomly(dungeon, all_entities)
            return

        # ── [ESCAPE_BLOCK] 逃げ道封鎖AI + フランク (削除時はこのブロックごと除去) ──
        if (abs(dx) + abs(dy)) > 1:
            nearby_allies = [
                e for e in all_entities
                if e is not self and isinstance(e, Enemy) and not getattr(e, "is_dead", False)
                and abs(int((e.x+e.width/2)//dungeon.tile_size) - px) <= rad
                and abs(int((e.y+e.height/2)//dungeon.tile_size) - py) <= rad
            ]
            if nearby_allies:
                my_dist = abs(mx - px) + abs(my - py)
                min_ally_dist = min(
                    abs(int((e.x+e.width/2)//dungeon.tile_size) - px) +
                    abs(int((e.y+e.height/2)//dungeon.tile_size) - py)
                    for e in nearby_allies
                )
                # 自分が最接近ではない → 逃げ道封鎖を優先、次いでフランク
                if ENEMY_ESCAPE_BLOCK_ENABLED and my_dist > min_ally_dist:
                    block = self._get_escape_block_target(px, py, all_entities, dungeon)
                    if block:
                        moved = self._move_toward_grid(block[0], block[1], dungeon, all_entities)
                        self._log_trace(dungeon, f"attempting escape block to ({block[0]}, {block[1]}). moved={moved}")
                        if moved:
                            return
                    else:
                        self._log_trace(dungeon, "escape block target was None")
                # 最接近 or 封鎖失敗 → フランク（包囲）を試みる
                flank = self._get_flank_target(px, py, all_entities, dungeon)
                if flank:
                    ftx, fty = flank
                    if (mx, my) != (ftx, fty) and abs(mx - ftx) + abs(my - fty) > 1:
                        moved = self._move_toward_grid(ftx, fty, dungeon, all_entities)
                        self._log_trace(dungeon, f"attempting flank to ({ftx}, {fty}). moved={moved}")
                        if moved:
                            return
                    else:
                        self._log_trace(dungeon, f"flank target ({ftx}, {fty}) too close or self is already there")
                else:
                    self._log_trace(dungeon, "flank target was None")
        # ── [/ESCAPE_BLOCK] ──────────────────────────────────────────

        if self.stupidity < 7:
            if not self.smart_ranged_move:
                ideal = 1
            else:
                ideal = 1 if self.attack_priority == "close" else (2 if self.attack_range == 2 else max(1, self.attack_range - 1))
            los = self._is_in_attack_range(dx, dy) and self._is_line_of_sight_clear(dx, dy, dungeon, all_entities); gdist = abs(dx)+abs(dy)
            self._log_trace(dungeon, f"AI status: gdist={gdist}, ideal={ideal}, los={los}, attack_priority={self.attack_priority}")
            if gdist == ideal:
                if los:
                    self._log_trace(dungeon, "close-attacking player.")
                    self._handle_attack(dx, dy, player, dialog)
                    return
                smart_moved = self._move_smartly_check_success(player, dungeon, all_entities, px, py, mx, my, occupied_cells, ideal)
                self._log_trace(dungeon, f"tried smart move to ideal dist {ideal}. success={smart_moved}")
                if smart_moved:
                    return
            elif gdist == 1 and self.smart_ranged_move and self.attack_priority == "ranged" and self.attack_range > 1:
                smart_moved = self._move_smartly_check_success(player, dungeon, all_entities, px, py, mx, my, occupied_cells, ideal)
                self._log_trace(dungeon, f"backing away for ranged attack (smart_moved={smart_moved})")
                if random.random() < 0.7 and smart_moved:
                    return
                self._log_trace(dungeon, "ranged-attacking close player")
                self._handle_attack(dx, dy, player, dialog)
                return
            else:
                if los:
                    self._log_trace(dungeon, "attacking player from distance")
                    self._handle_attack(dx, dy, player, dialog)
                    return
                smart_moved = self._move_smartly_check_success(player, dungeon, all_entities, px, py, mx, my, occupied_cells, ideal)
                self._log_trace(dungeon, f"moved smartly check: {smart_moved}")
                if smart_moved:
                    return
                # [FIX] 斜め位置などでスマート移動が失敗した場合のフォールバック: プレイヤーへ1歩直接接近
                if (abs(dx) + abs(dy)) > 1:
                    moved = self._move_toward_grid(px, py, dungeon, all_entities)
                    self._log_trace(dungeon, f"moved toward player ({px}, {py}) (moved: {moved})")
                else:
                    self._log_trace(dungeon, "no fallback move: too close or diagonal but dist <= 1")
        else:
            self._log_trace(dungeon, f"skipping turn because stupidity is {self.stupidity} (>= 7)")

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
    def spawn_enemies(cls, dungeon, player=None, is_outbreak=False):
        from constants import (ENEMY_SPAWN_MIN, ENEMY_SPAWN_MAX, ENEMY_SPAWN_ATTEMPTS, ENEMY_SPAWN_SAFE_RADIUS, ENEMY_SPAWN_SCATTER, ENEMY_DATA, ENEMY_TOTAL_MAX, ENEMY_TOTAL_SCALE_EVERY, ENEMY_TOTAL_SCALE_ADD, OBSTACLE_SPAWN_MIN, OBSTACLE_SPAWN_MAX, OBSTACLE_SPAWN_SCALE_EVERY, OBSTACLE_SPAWN_SCALE_ADD, OBSTACLE_SPAWN_LIMIT, OBSTACLE_TOTAL_MAX, OBSTACLE_TOTAL_SCALE_EVERY, OBSTACLE_TOTAL_SCALE_ADD, BOSS_NO_QUEST_SPAWN_CHANCE)
        enemies = []; floor = getattr(dungeon, "current_floor", 1); pgx, pgy = (int(player.x//dungeon.tile_size), int(player.y//dungeon.tile_size)) if player else (-999,-999)
        mt = [k for k, v in ENEMY_DATA.items() if not v.get("is_static", False)]; ot = [k for k, v in ENEMY_DATA.items() if v.get("is_static", False)]
        ef = min(floor, OBSTACLE_SPAWN_LIMIT); nr = len(dungeon.rooms)
        m_cap = int(nr * ENEMY_TOTAL_MAX) + (floor-1)//ENEMY_TOTAL_SCALE_EVERY * ENEMY_TOTAL_SCALE_ADD
        o_cap = int(nr * OBSTACLE_TOTAL_MAX) + (ef-1)//OBSTACLE_TOTAL_SCALE_EVERY * OBSTACLE_TOTAL_SCALE_ADD
        
        # アウトブレイク時は出現数を倍増させる
        if is_outbreak:
            from constants import OUTBREAK_ENEMY_MULT
            mult = OUTBREAK_ENEMY_MULT
            m_cap = int(m_cap * mult)

        # 1. 階層ボス(is_boss)の確定配置
        # その階層がボスの出現開始階層(min_floor)であれば、最優先で1体配置する
        boss_types = [t for t in mt if ENEMY_DATA[t].get("is_boss") and ENEMY_DATA[t].get("min_floor") == floor]
        # once_only かつ撃破済みのボスは除外する
        defeated_once = getattr(player, "defeated_once_only", []) if player else []
        boss_types = [t for t in boss_types if not (ENEMY_DATA[t].get("once_only") and t in defeated_once)]
        for b_type in boss_types:
            has_quest = False
            is_promo_exam = False
            if player and hasattr(player, "active_quests"):
                has_quest = any(q.get("target_key") == b_type for q in player.active_quests)
                
                # 昇格試験の判定: プレイヤーが昇級クエストを持っており、かつそのボスのランクがプレイヤーの現在ランクと一致する場合
                has_rank_up_quest = any(q.get("is_rank_up") for q in player.active_quests)
                boss_rank = ENEMY_DATA[b_type].get("min_rank") or ENEMY_DATA[b_type].get("rank")
                if has_rank_up_quest and boss_rank == player.guild_rank:
                    is_promo_exam = True
            
            if not has_quest and not is_promo_exam and player is not None:
                spawn_chance = ENEMY_DATA[b_type].get("spawn_chance", BOSS_NO_QUEST_SPAWN_CHANCE)
                if random.random() >= spawn_chance:
                    print(f"[Dungeon] Boss {b_type} skipped: no quest, no promotion exam, and did not roll {spawn_chance*100}% chance.")
                    continue

            spawned = False
            # 全部屋（スタート部屋以外優先）を巡回して場所を探す
            shuffled_rooms = list(enumerate(dungeon.rooms))
            random.shuffle(shuffled_rooms)
            
            # まずは通常のランダムサンプリングで試す
            for ridx, room in shuffled_rooms:
                if ridx == getattr(dungeon, "start_room_idx", -1) and len(dungeon.rooms) > 1: continue
                for att in range(ENEMY_SPAWN_ATTEMPTS * 3):
                    ex, ey = random.randint(room[0]-ENEMY_SPAWN_SCATTER, room[0]+ENEMY_SPAWN_SCATTER), random.randint(room[1]-ENEMY_SPAWN_SCATTER, room[1]+ENEMY_SPAWN_SCATTER)
                    if abs(ex-pgx) <= ENEMY_SPAWN_SAFE_RADIUS and abs(ey-pgy) <= ENEMY_SPAWN_SAFE_RADIUS: continue
                    if 0 <= ey < dungeon.map_height and 0 <= ex < dungeon.map_width:
                        temp_enemy = Enemy(ex*dungeon.tile_size, ey*dungeon.tile_size, b_type, player=player)
                        if temp_enemy.can_move_grid(temp_enemy.x, temp_enemy.y, dungeon):
                            if not any(set(temp_enemy.get_occupied_grids(dungeon.tile_size)) & set(e.get_occupied_grids(dungeon.tile_size)) for e in enemies):
                                enemies.append(temp_enemy); dungeon.spawn_counts[b_type] = dungeon.spawn_counts.get(b_type,0)+1
                                spawned = True; break
                if spawned: break

            # それでも出なかった場合、全タイルを総当たりでチェックする（フォールバック）
            if not spawned:
                for ridx, room in shuffled_rooms:
                    # 部屋の範囲を特定（中心からある程度の範囲を全スキャン）
                    # rooms_raw がある場合はそれを使う
                    target_room_obj = None
                    if hasattr(dungeon, "rooms_raw") and ridx < len(dungeon.rooms_raw):
                        target_room_obj = dungeon.rooms_raw[ridx]
                    
                    if target_room_obj:
                        scan_range_x = range(target_room_obj.x, target_room_obj.x + target_room_obj.w)
                        scan_range_y = range(target_room_obj.y, target_room_obj.y + target_room_obj.h)
                    else:
                        # 部屋オブジェクトがない場合のバックアップ（広めにスキャン）
                        scan_range_x = range(room[0]-10, room[0]+11)
                        scan_range_y = range(room[1]-10, room[1]+11)

                    candidate_tiles = []
                    for ey in scan_range_y:
                        for ex in scan_range_x:
                            if not (0 <= ey < dungeon.map_height and 0 <= ex < dungeon.map_width): continue
                            # プレイヤーとの距離制約を一旦無視して「置ける場所」を探す
                            temp_enemy = Enemy(ex*dungeon.tile_size, ey*dungeon.tile_size, b_type, player=player)
                            final_x = temp_enemy.x + (dungeon.tile_size - temp_enemy.width) // 2
                            final_y = temp_enemy.y + (dungeon.tile_size - temp_enemy.height) // 2
                            if temp_enemy.can_move_grid(final_x, final_y, dungeon):
                                if not any(set(temp_enemy.get_occupied_grids_at(final_x, final_y, dungeon.tile_size)) & set(e.get_occupied_grids(dungeon.tile_size)) for e in enemies):
                                    dist = abs(ex-pgx) + abs(ey-pgy)
                                    candidate_tiles.append((ex, ey, dist, final_x, final_y))
                    
                    if candidate_tiles:
                        # プレイヤーからなるべく離れている場所を優先
                        candidate_tiles.sort(key=lambda x: x[2], reverse=True)
                        best_ex, best_ey, _, fx, fy = candidate_tiles[0]
                        boss = Enemy(best_ex*dungeon.tile_size, best_ey*dungeon.tile_size, b_type, player=player)
                        boss.x, boss.y = fx, fy
                        enemies.append(boss)
                        dungeon.spawn_counts[b_type] = dungeon.spawn_counts.get(b_type,0)+1
                        spawned = True
                        print(f"[Dungeon] Boss {b_type} spawned via fallback exhaustive search at ({best_ex}, {best_ey})")
                        break

            if spawned: print(f"[Dungeon] Boss {b_type} spawned guaranteed at floor {floor}.")
            else: print(f"[ERROR] Failed to spawn guaranteed boss {b_type} on floor {floor} even with fallback!")

        # 2. 通常モンスターの配置
        for idx, room in enumerate(dungeon.rooms):
            if random.random() < 0.1: continue
            isr = (idx == getattr(dungeon, "start_room_idx", -1) or idx == getattr(dungeon, "target_room_idx", -1))
            s_min, s_max = (ENEMY_SPAWN_MIN//2, max(1, ENEMY_SPAWN_MAX//2)) if isr else (ENEMY_SPAWN_MIN, ENEMY_SPAWN_MAX)
            
            # アウトブレイク時は1部屋あたりの出現数も3倍に
            if is_outbreak:
                s_min *= 3
                s_max *= 3
                
            for _ in range(random.randint(s_min, s_max)):
                if sum(1 for e in enemies if not e.is_static) >= m_cap: break
                for att in range(ENEMY_SPAWN_ATTEMPTS*2):
                    ex, ey = random.randint(room[0]-ENEMY_SPAWN_SCATTER, room[0]+ENEMY_SPAWN_SCATTER), random.randint(room[1]-ENEMY_SPAWN_SCATTER, room[1]+ENEMY_SPAWN_SCATTER)
                    if abs(ex-pgx) <= ENEMY_SPAWN_SAFE_RADIUS and abs(ey-pgy) <= ENEMY_SPAWN_SAFE_RADIUS: continue
                    if 0 <= ey < dungeon.map_height and 0 <= ex < dungeon.map_width:
                        # 出現可能なザコ敵をランダムに選ぶ
                        vm = [m for m in mt if ENEMY_DATA[m].get("min_floor", 1) <= floor <= ENEMY_DATA[m].get("max_floor", 999) and not ENEMY_DATA[m].get("is_boss")]
                        if not vm: break
                        mtp = random.choice(vm)
                        nm = Enemy(ex*dungeon.tile_size, ey*dungeon.tile_size, mtp, player=player)
                        # タイル中央に寄せるオフセットを先に計算
                        final_x = nm.x + (dungeon.tile_size - nm.width) // 2
                        final_y = nm.y + (dungeon.tile_size - nm.height) // 2
                        # 最終的な座標で全占有グリッドが床かチェック
                        if nm.can_move_grid(final_x, final_y, dungeon):
                            if not any(set(nm.get_occupied_grids_at(final_x, final_y, dungeon.tile_size)) & set(e.get_occupied_grids(dungeon.tile_size)) for e in enemies):
                                nm.x, nm.y = final_x, final_y
                                nm.target_x, nm.target_y = nm.x, nm.y
                                enemies.append(nm); dungeon.spawn_counts[mtp] = dungeon.spawn_counts.get(mtp,0)+1; break
            
            # 3. 障害物の配置
            for _ in range(random.randint(OBSTACLE_SPAWN_MIN, OBSTACLE_SPAWN_MAX + (ef-1)//OBSTACLE_SPAWN_SCALE_EVERY * OBSTACLE_SPAWN_SCALE_ADD)):
                if sum(1 for e in enemies if e.is_static) >= o_cap: break
                for att in range(ENEMY_SPAWN_ATTEMPTS):
                    ex, ey = random.randint(room[0]-ENEMY_SPAWN_SCATTER, room[0]+ENEMY_SPAWN_SCATTER), random.randint(room[1]-ENEMY_SPAWN_SCATTER, room[1]+ENEMY_SPAWN_SCATTER)
                    if 0 <= ey < dungeon.map_height and 0 <= ex < dungeon.map_width and dungeon.map_data[ey][ex] == 1:
                        vo = [o for o in ot if ENEMY_DATA[o].get("min_floor",1) <= floor <= ENEMY_DATA[o].get("max_floor",999)]
                        if vo:
                            otp = random.choice(vo)
                            no = Enemy(ex*dungeon.tile_size, ey*dungeon.tile_size, otp, player=player)
                            # タイル中央に寄せるオフセットを先に計算
                            final_x = no.x + (dungeon.tile_size - no.width) // 2
                            final_y = no.y + (dungeon.tile_size - no.height) // 2
                            # 最終的な座標で全占有グリッドが床かチェック
                            if no.can_move_grid(final_x, final_y, dungeon):
                                if not any(set(no.get_occupied_grids_at(final_x, final_y, dungeon.tile_size)) & set(e.get_occupied_grids(dungeon.tile_size)) for e in enemies):
                                    no.x, no.y = final_x, final_y
                                    no.target_x, no.target_y = no.x, no.y
                                    enemies.append(no); break
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
        from constants import (ENEMY_TOTAL_MAX, ENEMY_TOTAL_SCALE_EVERY, ENEMY_TOTAL_SCALE_ADD, ENEMY_DATA, ENEMY_SPAWN_ATTEMPTS, ENEMY_SPAWN_SAFE_RADIUS, ENEMY_SPAWN_SCATTER)
        f = getattr(dungeon, "current_floor", 1); nr = len(dungeon.rooms); mc = int(nr * ENEMY_TOTAL_MAX) + (f-1)//ENEMY_TOTAL_SCALE_EVERY * ENEMY_TOTAL_SCALE_ADD
        if sum(1 for e in dungeon.enemies if not e.is_static) >= mc: return
        
        pgx, pgy = (int(player.x//dungeon.tile_size), int(player.y//dungeon.tile_size)) if player else (-999,-999)
        mt = [k for k, v in ENEMY_DATA.items() if not v.get("is_static", False) and not v.get("is_boss")]
        vm = [m for m in mt if ENEMY_DATA[m].get("min_floor", 1) <= f <= ENEMY_DATA[m].get("max_floor", 999)]
        if not vm: return

        # プレイヤーから離れたランダムな部屋の床にスポーンを試みる
        shuffled_rooms = list(dungeon.rooms)
        random.shuffle(shuffled_rooms)
        for room in shuffled_rooms:
            for att in range(ENEMY_SPAWN_ATTEMPTS):
                ex, ey = random.randint(room[0]-ENEMY_SPAWN_SCATTER, room[0]+ENEMY_SPAWN_SCATTER), random.randint(room[1]-ENEMY_SPAWN_SCATTER, room[1]+ENEMY_SPAWN_SCATTER)
                if abs(ex-pgx) <= ENEMY_SPAWN_SAFE_RADIUS and abs(ey-pgy) <= ENEMY_SPAWN_SAFE_RADIUS: continue
                if 0 <= ey < dungeon.map_height and 0 <= ex < dungeon.map_width:
                    mtp = random.choice(vm)
                    nm = Enemy(ex*dungeon.tile_size, ey*dungeon.tile_size, mtp, player=player)
                    if nm.can_move_grid(nm.x, nm.y, dungeon):
                        if not any(set(nm.get_occupied_grids(dungeon.tile_size)) & set(e.get_occupied_grids(dungeon.tile_size)) for e in dungeon.enemies):
                            nm.x += (dungeon.tile_size-nm.width)//2; nm.y += (dungeon.tile_size-nm.height)//2; nm.target_x, nm.target_y = nm.x, nm.y
                            dungeon.enemies.append(nm); dungeon.spawn_counts[mtp] = dungeon.spawn_counts.get(mtp,0)+1; return

    def get_occupied_grids_at(self, tx, ty, tile_size):
        if self.is_static:
            # 障害物（is_static）の場合は描画スケーリング（image_scale）に関わらず1x1グリッドのみを占有する。
            # タイル中央へのセンタリングオフセット（(tile_size - width) // 2）により、
            # tx, ty が元タイルの左上座標からずれるため、物体の中心座標から本来のグリッドを正確に逆算する。
            gx = int((tx + self.width // 2) // tile_size)
            gy = int((ty + self.height // 2) // tile_size)
            return [(gx, gy)]
        return super().get_occupied_grids_at(tx, ty, tile_size)

