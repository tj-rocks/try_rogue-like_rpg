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
    STUPIDITY_WANDER_RATES, STUPIDITY_FLANK_RATES, ENEMY_ESCAPE_BLOCK_ENABLED
)
from systems.combat_handler import deal_damage
from systems.tactical_profile import get_relation_and_distance

def _enemy_equipment_inst(equip_type, key):
    if not key:
        return None
    from components.sprites.player import EquipInstance
    return EquipInstance(equip_type, key)

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
        self.stupidity_temp = 0  # 装備スキルによる一時的 stupidity 上昇
        self.stun_turns = 0  # スタン持続ターン
        self.dash_distance = data.get("dash_distance", 50)
        self.is_long_range = False; self.attack_priority = data.get("attack_priority", "close")
        self.smart_ranged_move = data.get("smart_ranged_move", True)
        self.turn_attack = data.get("turn_attack", False)
        self.turn_attack_chance = data.get("turn_attack_chance", 0.5)
        self.move_face_chance = data.get("move_face_chance", 0.0)
        self.bgm = data.get("bgm"); self.crit_rate = data.get("crit_rate", 0.01)
        self.accuracy_close = data.get("accuracy_close", data.get("accuracy_bonus", 100))
        self.accuracy_ranged = data.get("accuracy_ranged", data.get("accuracy_bonus", 100))
        self.status_to_inflict = data.get("status"); self.status_chance = data.get("status_chance", 100)
        self.detect_range = data.get("detect_range", ENEMY_AGGRO_RADIUS)
        self.damaged_detect_range = data.get("damaged_detect_range", 100)
        self.player_detected = False
        self.counter_ready_turns = 0
        self.attack_modes = data.get("attack_modes", [])
        self.attack_range_line = data.get("attack_range_line", self.attack_range)
        self.attack_range_diagonal = data.get("attack_range_diagonal", self.attack_range)
        self.attack_effects = data.get("attack_effects", {})
        self.knockback_proc_chance = data.get("knockback_proc_chance", 0.0)
        self.knockback_max_distance = data.get("knockback_max_distance", 1)
        self.stealth = data.get("stealth", False)
        self.stealth_reveal_range = data.get("stealth_reveal_range", 3)
        self.stealth_outline_alpha = data.get("stealth_outline_alpha", 90)
        self.trap_type = data.get("trap_type")
        self.trap_proc_chance = data.get("trap_proc_chance", 0.0)
        self.battle_locked = bool(data.get("battle_locked_until_start", False))
        self.current_attack_mode = None
        self.walk_frames = {}
        self.walk_frame_sources = {}
        self._last_draw_frame_info = None
        self.weapon_inventory = []
        self.armor_inventory = []
        self.shield_inventory = []
        self.accessory_inventory = []
        self.equipped_weapon = None
        self.equipped_armor = None
        self.equipped_shield = None
        self.equipped_accessory = None
        self._pending_equipment_cfg = data.get("equipment", {}) or {}
        self._equipment_deferred = getattr(self, "type", "") == "dungeon_core"
        if not self._equipment_deferred:
            self._load_enemy_equipment_from_cfg(self._pending_equipment_cfg)
        self._armor_images = {}
        self._shield_images = {}
        self._load_enemy_equipment_images()
        
        color_hex = data.get("image_color"); cache_key = (enemy_type, self.width, self.height, color_hex)
        cache_entry = Enemy._image_cache.get(cache_key)
        if cache_entry:
            if isinstance(cache_entry, dict) and "images" in cache_entry:
                self.images = cache_entry.get("images", {})
                self.walk_frames = cache_entry.get("walk_frames", {})
                self.walk_frame_sources = cache_entry.get("walk_frame_sources", {})
            else:
                self.images = cache_entry
                self.walk_frames = {}
                self.walk_frame_sources = {}
        else:
            self.images = {}; ip = data.get("image_path"); fp = data.get("image_folder", "")
            tint = None
            if color_hex:
                try: c = color_hex.lstrip('#'); tint = tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
                except: pass
            def apply_tint(s):
                if tint: ts = s.copy(); ts.fill(tint, special_flags=pygame.BLEND_RGB_MULT); return ts
                return s
            def load_frame(path):
                try:
                    return apply_tint(pygame.transform.scale(pygame.image.load(path).convert_alpha(), (self.width, self.height)))
                except:
                    return None
            if ip:
                try:
                    img = load_frame(ip)
                    if not self.is_static: self.images = {"up": img, "down": img, "left": img, "right": pygame.transform.flip(img, True, False)}
                    else: self.images = {d: img for d in ["up", "down", "left", "right"]}
                except: pass
            if not self.images and fp:
                for d in ["up", "down", "left", "right"]:
                    frame_list = []
                    frame_sources = []
                    for suffix in ("0", "1"):
                        frame_path = f"{fp}/{d}_{suffix}.png"
                        frame = load_frame(frame_path)
                        if frame:
                            frame_list.append(frame)
                            frame_sources.append(f"{d}_{suffix}")
                    if not frame_list:
                        single_path = f"{fp}/{d}.png"
                        single = load_frame(single_path)
                        if single:
                            frame_list = [single]
                            frame_sources = [d]
                    if not frame_list and d == "right" and not self.is_static and "left" in self.walk_frames:
                        frame_list = [pygame.transform.flip(img, True, False) for img in self.walk_frames["left"]]
                        frame_sources = [f"flip({src})" for src in self.walk_frame_sources.get("left", ["left"])]
                    if not frame_list:
                        frame_list = [pygame.Surface((self.width, self.height))]
                        frame_sources = ["blank"]
                    self.walk_frames[d] = frame_list
                    self.walk_frame_sources[d] = frame_sources
                    self.images[d] = frame_list[0]
                    if getattr(self, "type", "") == "dungeon_core":
                        try:
                            self._log_trace(
                                None,
                                f"load_frames facing={d} count={len(frame_list)} srcs={','.join(frame_sources)}"
                            )
                        except:
                            pass
            if not self.images: self.images = {d: pygame.Surface((self.width, self.height)) for d in ["up", "down", "left", "right"]}
            if not self.walk_frames:
                self.walk_frames = {d: [self.images.get(d, pygame.Surface((self.width, self.height)))] for d in ["up", "down", "left", "right"]}
                self.walk_frame_sources = {d: [d] for d in ["up", "down", "left", "right"]}
            Enemy._image_cache[cache_key] = {
                "images": self.images,
                "walk_frames": self.walk_frames,
                "walk_frame_sources": self.walk_frame_sources,
            }
        if getattr(self, "type", "") == "dungeon_core":
            try:
                for d in ("down", "left", "right", "up"):
                    fl = self.walk_frames.get(d, [])
                    srcs = self.walk_frame_sources.get(d, [])
                    self._log_trace(None, f"frame_cache facing={d} count={len(fl)} srcs={','.join(srcs) if srcs else '-'} cached={cache_key in Enemy._image_cache}")
            except:
                pass

    def _log_trace(self, dungeon, msg):
        try:
            with open("enemy_ai.log", "a", encoding="utf-8") as f:
                floor = getattr(dungeon, 'current_floor', '?') if dungeon else '?'
                tile_size = getattr(dungeon, "tile_size", 1) if dungeon else 1
                f.write(f"[Floor {floor}] [{self.name}#{id(self)%10000}] at ({int(self.x//tile_size)}, {int(self.y//tile_size)}): {msg}\n")
            import constants
            if constants.ENABLE_DEBUG_LOGGING:
                print(f"[TRACE-AI] [{self.name}#{id(self)%10000}]: {msg}")
        except:
            pass

    def _log_duel_trace(self, dungeon, player, action_type, extra=""):
        if getattr(self, "type", "") != "dungeon_core":
            return
        try:
            tile = dungeon.tile_size
            bx = int((self.target_x + self.width / 2) // tile)
            by = int((self.target_y + self.height / 2) // tile)
            px = int((player.x + player.width / 2) // tile)
            py = int((player.y + player.height / 2) // tile)
            relation, distance = get_relation_and_distance(player, self, tile)
            with open("duel_ai.log", "a", encoding="utf-8") as f:
                floor = getattr(dungeon, "current_floor", "?")
                suffix = f" | {extra}" if extra else ""
                f.write(
                    f"[Floor {floor}] [BOSS] pos=({bx},{by}) facing={self.facing} "
                    f"player=({px},{py}) relation={relation} distance={distance} "
                    f"action={action_type}{suffix}\n"
                )
        except:
            pass

    def _load_enemy_equipment_images(self):
        import os
        from systems.resources import load_image
        from constants import ARMOR_DATA, SHIELD_DATA
        armor_inst = self._find_equip_inst(self.armor_inventory, self.equipped_armor) if hasattr(self, "_find_equip_inst") else None
        shield_inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield) if hasattr(self, "_find_equip_inst") else None
        for inst, data_map, target_attr in [
            (armor_inst, ARMOR_DATA, "_armor_images"),
            (shield_inst, SHIELD_DATA, "_shield_images"),
        ]:
            if not inst:
                continue
            data = data_map.get(inst.key, {})
            img_dir = data.get("image_dir", "")
            if not img_dir or not os.path.exists(img_dir):
                continue
            images = {}
            shared = None
            for c in ["shield.png", "down.png", f"{inst.key}.png"]:
                raw = load_image(f"{img_dir}/{c}")
                if raw:
                    shared = pygame.transform.scale(raw, (self.width, self.height))
                    break
            for d in ("down", "left", "right", "up"):
                raw = load_image(f"{img_dir}/{d}.png")
                if raw:
                    images[d] = pygame.transform.scale(raw, (self.width, self.height))
                elif d == "right" and "left" in images:
                    images[d] = pygame.transform.flip(images["left"], True, False)
                elif shared:
                    images[d] = shared
            setattr(self, target_attr, images)

    def _load_enemy_equipment_from_cfg(self, eq_cfg):
        if not isinstance(eq_cfg, dict):
            return
        wcfg = eq_cfg.get("weapon") or {}
        acfg = eq_cfg.get("armor") or {}
        scfg = eq_cfg.get("shield") or {}
        xcfg = eq_cfg.get("accessory") or {}
        wkey = wcfg.get("key")
        akey = acfg.get("key")
        skey = scfg.get("key")
        xkey = xcfg.get("key")
        winst = _enemy_equipment_inst("weapon", wkey)
        ainst = _enemy_equipment_inst("armor", akey)
        sinst = _enemy_equipment_inst("shield", skey)
        xinst = _enemy_equipment_inst("accessory", xkey)
        if winst:
            self.weapon_inventory.append(winst)
            self.equipped_weapon = winst.iid
            from components.sprites.weapon import get_weapon_instance
            self.weapon = get_weapon_instance(winst.key, winst.enhance)
        else:
            self.weapon = None
        if ainst:
            self.armor_inventory.append(ainst)
            self.equipped_armor = ainst.iid
        if sinst:
            self.shield_inventory.append(sinst)
            self.equipped_shield = sinst.iid
        if xinst:
            self.accessory_inventory.append(xinst)
            self.equipped_accessory = xinst.iid

    def activate_battle_equipment(self):
        if not getattr(self, "_equipment_deferred", False):
            return
        if self.weapon_inventory or self.armor_inventory or self.shield_inventory or self.accessory_inventory:
            self._equipment_deferred = False
            return
        self._load_enemy_equipment_from_cfg(getattr(self, "_pending_equipment_cfg", {}) or {})
        self._load_enemy_equipment_images()
        self._equipment_deferred = False

    def _find_equip_inst(self, inv, iid):
        for inst in inv or []:
            if getattr(inst, "iid", None) == iid:
                return inst
        return None

    def _draw_enemy_armor_overlay(self, screen, draw_x, draw_y):
        if not self.equipped_armor or not self._armor_images:
            return
        img = self._armor_images.get(self.facing)
        if not img:
            return
        screen.blit(img, (draw_x, draw_y))

    def _draw_enemy_shield_overlay(self, screen, draw_x, draw_y):
        if not self.equipped_shield or not self._shield_images:
            return
        img = self._shield_images.get(self.facing)
        if not img:
            return
        from constants import SHIELD_DATA, SHIELD_CATEGORIES
        inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield)
        data = SHIELD_DATA.get(inst.key, {}) if inst else {}
        cat_data = SHIELD_CATEGORIES.get(data.get("category"), {})
        offsets = cat_data.get("position", {}).get("offsets", {}).get(self.facing, (0, 0))
        screen.blit(img, (draw_x + offsets[0], draw_y + offsets[1]))

    @staticmethod
    def _apply_alpha_surface(surface, alpha):
        if alpha >= 255:
            return surface
        scaled = surface.copy()
        scaled.set_alpha(alpha)
        return scaled

    @staticmethod
    def _apply_outline_stealth(surface, alpha):
        if alpha >= 255:
            return surface
        w, h = surface.get_size()
        outline = pygame.transform.smoothscale(surface, (max(1, int(w * 1.08)), max(1, int(h * 1.08)))).copy()
        outline.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        outline.set_alpha(min(255, alpha))
        body = surface.copy()
        body.set_alpha(min(255, alpha + 20))
        combined = pygame.Surface((outline.get_width(), outline.get_height()), pygame.SRCALPHA)
        combined.blit(outline, (0, 0))
        ox = (combined.get_width() - body.get_width()) // 2
        oy = (combined.get_height() - body.get_height()) // 2
        combined.blit(body, (ox, oy))
        return combined

    def draw(self, screen, camera_x, camera_y):
        import math; draw_x, draw_y = self.x - camera_x, self.y - camera_y
        dungeon = getattr(self, "current_dungeon", None)
        fog_alpha = 255
        fog_visible = False
        if dungeon and getattr(dungeon, "darkness_type", "dark") == "fog":
            player = getattr(dungeon, "player", None)
            tile_size = getattr(dungeon, "tile_size", 1) or 1
            if player:
                from systems.tactical_profile import get_relation_and_distance
                relation, distance = get_relation_and_distance(player, self, tile_size)
                lantern = max(1, 1 + getattr(player, "lantern_bonus", 0))
                dist_map = {"1": 1, "2": 2, "3plus": 3}
                dist = dist_map.get(distance, 3)
                if dist <= lantern:
                    fog_alpha = 255
                elif dist == lantern + 1:
                    fog_alpha = 185
                elif dist == lantern + 2:
                    fog_alpha = 125
                else:
                    fog_alpha = 70
                if getattr(self, "type", "") == "dungeon_core":
                    fog_alpha = 255
                fog_visible = True
        stealth_visible = False
        stealth_alpha = 255
        if dungeon and self.stealth:
            player = getattr(dungeon, "player", None)
            if player:
                from systems.tactical_profile import get_relation_and_distance
                relation, distance = get_relation_and_distance(player, self, getattr(dungeon, "tile_size", 1) or 1)
                dist = 3 if distance == "3plus" else int(distance)
                reveal_range = max(1, int(getattr(self, "stealth_reveal_range", 3)))
                if dist > reveal_range:
                    stealth_visible = True
                    stealth_alpha = max(50, int(getattr(self, "stealth_outline_alpha", 90)))
                elif dist == reveal_range:
                    stealth_visible = True
                    stealth_alpha = max(110, int(getattr(self, "stealth_outline_alpha", 90)) + 20)
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
            frame_list = self.walk_frames.get(self.facing) or [self.images.get(self.facing, pygame.Surface((self.width, self.height)))]
            if self.is_moving:
                frame_idx = (self.walk_anim_timer // 12) % len(frame_list)
                base = frame_list[frame_idx]
            else:
                idle_step = 20 if getattr(self, "type", "") == "dungeon_core" else 8
                frame_idx = (self.idle_anim_timer // idle_step) % len(frame_list)
                base = frame_list[frame_idx]
            if getattr(self, "type", "") == "dungeon_core":
                src_list = self.walk_frame_sources.get(self.facing, [self.facing])
                src_name = src_list[frame_idx] if frame_idx < len(src_list) else src_list[0]
                draw_info = (self.facing, frame_idx, src_name, self.is_moving)
                if draw_info != self._last_draw_frame_info:
                    self._last_draw_frame_info = draw_info
                    mode = "walk" if self.is_moving else "idle"
                    dungeon = getattr(self, "current_dungeon", None)
                    if dungeon:
                        self._log_trace(dungeon, f"draw_frame mode={mode} facing={self.facing} idx={frame_idx} src={src_name}")
            ck = (base, "attack" if self.is_attacking else ph, is_flipped)
            cur = Enemy._scaled_image_cache.get(ck)
            if cur is None:
                if self.is_attacking: cur = pygame.transform.scale(base, (int(base.get_width() * 1.2), int(base.get_height() * 1.2)))
                elif not self.is_static: cur = pygame.transform.smoothscale(base, (int(base.get_width() * sx), int(base.get_height() * sy)))
                else: cur = base
                
                if is_flipped:
                    cur = pygame.transform.flip(cur, True, False)
                Enemy._scaled_image_cache[ck] = cur
            if stealth_visible:
                cur = self._apply_outline_stealth(cur, stealth_alpha)
            if fog_visible and fog_alpha < 255:
                cur = self._apply_alpha_surface(cur, fog_alpha)
            draw_x += (self.width - cur.get_width()) / 2; draw_y += (self.height - cur.get_height())
            from constants import HIT_STUN_DURATION
            if not (self.damage_flash_timer > HIT_STUN_DURATION and (self.damage_flash_timer - HIT_STUN_DURATION) % 4 < 2):
                if getattr(self, "weapon", None):
                    cx = draw_x + cur.get_width() / 2
                    cy = draw_y + cur.get_height() / 2
                    over = self.weapon.DRAW_OVER_PLAYER.get(self.facing, False)
                    if not over:
                        weapon_alpha = fog_alpha if fog_visible else 255
                        if self.is_attacking: self.weapon.draw_attack(screen, cx, cy, self.facing, 1.0, scale_x=sx, scale_y=sy, alpha=weapon_alpha)
                        else: self.weapon.draw_idle(screen, cx, cy, self.facing, scale_x=sx, scale_y=sy, alpha=weapon_alpha)
                so = {"up": False, "down": True, "left": True, "right": False}.get(self.facing, True)
                if self.equipped_shield and not so:
                    shield_img = self._shield_images.get(self.facing) if self._shield_images else None
                    if shield_img:
                        shield_draw = self._apply_alpha_surface(shield_img, fog_alpha) if fog_visible else shield_img
                        from constants import SHIELD_DATA, SHIELD_CATEGORIES
                        inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield)
                        data = SHIELD_DATA.get(inst.key, {}) if inst else {}
                        cat_data = SHIELD_CATEGORIES.get(data.get("category"), {})
                        offsets = cat_data.get("position", {}).get("offsets", {}).get(self.facing, (0, 0))
                        screen.blit(shield_draw, (draw_x + offsets[0], draw_y + offsets[1]))
                if self._armor_images:
                    armor_img = self._armor_images.get(self.facing)
                    if armor_img:
                        armor_draw = self._apply_alpha_surface(armor_img, fog_alpha) if fog_visible else armor_img
                        screen.blit(armor_draw, (draw_x, draw_y))
                screen.blit(cur, (draw_x, draw_y))
                if getattr(self, "weapon", None):
                    cx = draw_x + cur.get_width() / 2
                    cy = draw_y + cur.get_height() / 2
                    over = self.weapon.DRAW_OVER_PLAYER.get(self.facing, False)
                    if over:
                        weapon_alpha = fog_alpha if fog_visible else 255
                        if self.is_attacking: self.weapon.draw_attack(screen, cx, cy, self.facing, 1.0, scale_x=sx, scale_y=sy, alpha=weapon_alpha)
                        else: self.weapon.draw_idle(screen, cx, cy, self.facing, scale_x=sx, scale_y=sy, alpha=weapon_alpha)
                if self.equipped_shield and so:
                    shield_img = self._shield_images.get(self.facing) if self._shield_images else None
                    if shield_img:
                        shield_draw = self._apply_alpha_surface(shield_img, fog_alpha) if fog_visible else shield_img
                        from constants import SHIELD_DATA, SHIELD_CATEGORIES
                        inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield)
                        data = SHIELD_DATA.get(inst.key, {}) if inst else {}
                        cat_data = SHIELD_CATEGORIES.get(data.get("category"), {})
                        offsets = cat_data.get("position", {}).get("offsets", {}).get(self.facing, (0, 0))
                        screen.blit(shield_draw, (draw_x + offsets[0], draw_y + offsets[1]))
                # 色付きダメージフラッシュ（スタン・背後攻撃など）
                if self.damage_flash_timer > HIT_STUN_DURATION:
                    color = getattr(self, "flash_color", (255, 255, 255))
                    if color and color != (255, 255, 255):
                        # オーバーレイを敵画像の非透明部分のみに合成（床のタイルには影響しない）
                        flashed = cur.copy()
                        overlay = pygame.Surface(cur.get_size(), pygame.SRCALPHA)
                        overlay.fill(color + (80,))
                        mask = pygame.mask.from_surface(cur)
                        if mask.count() > 0:
                            mask_surf = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
                            overlay.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                        flashed.blit(overlay, (0, 0), special_flags=pygame.BLEND_ADD)
                        screen.blit(flashed, (draw_x, draw_y))

    def _move_randomly(self, dungeon, all_entities):
        d = random.choice([("right", dungeon.tile_size, 0), ("left", -dungeon.tile_size, 0), ("down", 0, dungeon.tile_size), ("up", 0, -dungeon.tile_size)])
        tx, ty = self.x + d[1], self.y + d[2]
        if self.can_move_grid(tx, ty, dungeon, debug_log=True):
            self.target_x, self.target_y, self.facing, self.is_moving, self.step_toggle = tx, ty, d[0], True, not self.step_toggle
        else:
            self._log_trace(dungeon, f"_move_randomly: failed to move to {d[0]} ({tx//dungeon.tile_size}, {ty//dungeon.tile_size})")

    def _get_player_combat_tile(self, player, tile_size):
        use_target = getattr(player, "is_moving", False)
        px_src = player.target_x if use_target else player.x
        py_src = player.target_y if use_target else player.y
        px = int((px_src + player.width / 2) // tile_size)
        py = int((py_src + player.height / 2) // tile_size)
        return px, py

    def _is_in_attack_range(self, dx, dy):
        mode = getattr(self, "current_attack_mode", None)
        if mode == "diagonal":
            return abs(dx) == abs(dy) and 0 < abs(dx) <= max(1, self.attack_range_diagonal)
        if mode == "line":
            return ((abs(dx) <= max(1, self.attack_range_line) and dy == 0 and dx != 0)
                    or (abs(dy) <= max(1, self.attack_range_line) and dx == 0 and dy != 0))
        return (abs(dx) <= self.attack_range and dy == 0 and dx != 0) or (abs(dy) <= self.attack_range and dx == 0 and dy != 0)

    def _handle_attack(self, dx, dy, player, dialog=None):
        self.current_attack_distance = max(abs(dx), abs(dy))
        if getattr(self, "current_attack_mode", None) == "counter":
            if dx > 0: self.facing = "right"
            elif dx < 0: self.facing = "left"
            elif dy > 0: self.facing = "down"
            elif dy < 0: self.facing = "up"
            self.counter_ready_turns = 1
            return
        if dx > 0: needed = "right"
        elif dx < 0: needed = "left"
        elif dy > 0: needed = "down"
        elif dy < 0: needed = "up"
        else: needed = self.facing
        if self.facing != needed:
            self.facing = needed
            if not self.turn_attack:
                return
            relation, distance = get_relation_and_distance(player, self, 1)
            if random.random() >= self._get_turn_attack_chance(player, relation, distance):
                return
        from constants import ATTACK_PRE_DELAY_FRAMES
        self.attack_pre_delay_timer = ATTACK_PRE_DELAY_FRAMES; self.is_attacking = True; self.is_long_range = (abs(dx)+abs(dy) > 1)
        self.target_for_attack, self.dialog_for_attack = player, dialog

    def _choose_dungeon_core_prediction(self, profile):
        move_bias = 0.0
        melee_bias = 0.0
        magic_bias = 0.0
        item_bias = 0.0
        wait_bias = 0.0
        if profile:
            total_actions = (
                profile.get_action_total("move")
                + profile.get_action_total("melee")
                + profile.get_action_total("magic")
                + profile.get_action_total("item")
                + profile.get_action_total("wait")
            )
            if total_actions > 0:
                move_bias = profile.get_action_total("move") / total_actions
                melee_bias = profile.get_action_total("melee") / total_actions
                magic_bias = profile.get_action_total("magic") / total_actions
                item_bias = profile.get_action_total("item") / total_actions
                wait_bias = profile.get_action_total("wait") / total_actions
        line_weight = max(1, int((melee_bias + magic_bias + item_bias + wait_bias) * 100))
        vertical_weight = max(1, int(move_bias * 100))
        if vertical_weight <= 0:
            return "line"
        prediction = random.choices(
            ["line", "up", "down"],
            weights=[line_weight, vertical_weight, vertical_weight],
            k=1,
        )[0]
        return prediction

    def _get_dungeon_core_action_biases(self, profile):
        move_bias = 0.0
        melee_bias = 0.0
        magic_bias = 0.0
        item_bias = 0.0
        wait_bias = 0.0
        if not profile:
            return move_bias, melee_bias, magic_bias, item_bias, wait_bias
        total_actions = (
            profile.get_action_total("move")
            + profile.get_action_total("melee")
            + profile.get_action_total("magic")
            + profile.get_action_total("item")
            + profile.get_action_total("wait")
        )
        if total_actions <= 0:
            return move_bias, melee_bias, magic_bias, item_bias, wait_bias
        move_bias = profile.get_action_total("move") / total_actions
        melee_bias = profile.get_action_total("melee") / total_actions
        magic_bias = profile.get_action_total("magic") / total_actions
        item_bias = profile.get_action_total("item") / total_actions
        wait_bias = profile.get_action_total("wait") / total_actions
        return move_bias, melee_bias, magic_bias, item_bias, wait_bias

    def _choose_dungeon_core_diagonal_action(self, player):
        profile = getattr(player, "tactical_profile", None)
        use_profile = bool(profile and random.random() < 0.7)
        weights = {"diagonal": 30, "step_front": 30, "wait": 20}
        if use_profile:
            move_bias, melee_bias, magic_bias, item_bias, wait_bias = self._get_dungeon_core_action_biases(profile)
            weights["diagonal"] += int(move_bias * 20)
            weights["step_front"] += int(melee_bias * 20)
            weights["wait"] += int((magic_bias + item_bias + wait_bias) * 20)
        return random.choices(
            ["diagonal", "step_front", "wait"],
            weights=[weights["diagonal"], weights["step_front"], weights["wait"]],
            k=1,
        )[0], use_profile

    def _try_dungeon_core_predicted_attack(self, player, dungeon, all_entities, dialog, dx, dy, relation, distance):
        if getattr(self, "type", "") != "dungeon_core":
            return False
        if relation != "front" or distance != "2":
            return False
        if not ((dx == 2 and dy == 0) or (dx == -2 and dy == 0) or (dx == 0 and dy == 2) or (dx == 0 and dy == -2)):
            return False

        profile = getattr(player, "tactical_profile", None)
        prediction = self._choose_dungeon_core_prediction(profile)
        mx = int((self.x + self.width / 2) // dungeon.tile_size)
        my = int((self.y + self.height / 2) // dungeon.tile_size)

        predicted_dx, predicted_dy = dx, dy
        if dx != 0:
            step = 1 if dx > 0 else -1
            if prediction == "up":
                predicted_dx, predicted_dy = step, -1
            elif prediction == "down":
                predicted_dx, predicted_dy = step, 1
        else:
            step = 1 if dy > 0 else -1
            if prediction == "up":
                predicted_dx, predicted_dy = -1, step
            elif prediction == "down":
                predicted_dx, predicted_dy = 1, step

        candidate_modes = ["line"] if prediction == "line" else random.sample(["line", "diagonal"], 2)
        chosen_mode = None
        for mode in candidate_modes:
            if self._can_use_attack_mode(mode, predicted_dx, predicted_dy, dungeon, all_entities):
                chosen_mode = mode
                break
        if not chosen_mode:
            return False

        self.current_attack_mode = chosen_mode
        self._log_trace(
            dungeon,
            f"dungeon_core predict={prediction} mode={chosen_mode} target=({mx + predicted_dx}, {my + predicted_dy})"
        )
        self._log_duel_trace(dungeon, player, f"predict_{prediction}", extra=f"mode={chosen_mode}")
        self._handle_attack(predicted_dx, predicted_dy, player, dialog)
        if getattr(self, "is_attacking", False):
            self.predicted_attack_tile = (mx + predicted_dx, my + predicted_dy)
            return True
        return False

    def _try_dungeon_core_side_gap_prediction(self, player, dungeon, all_entities, dialog, dx, dy, relation, distance):
        if getattr(self, "type", "") != "dungeon_core":
            return False
        if relation != "side" or distance != "2":
            return False
        if not ((abs(dx) == 2 and abs(dy) == 1) or (abs(dx) == 1 and abs(dy) == 2)):
            return False

        profile = getattr(player, "tactical_profile", None)
        move_bias, melee_bias, magic_bias, item_bias, wait_bias = self._get_dungeon_core_action_biases(profile)
        preferred = profile.get_preferred_action(relation, distance) if profile else None

        should_predict_step_in = False
        if preferred == "move":
            should_predict_step_in = True
        elif move_bias > max(melee_bias, magic_bias, item_bias, wait_bias):
            should_predict_step_in = random.random() < 0.65
        else:
            should_predict_step_in = random.random() < 0.2

        if not should_predict_step_in:
            advance_chance = 0.6
            if preferred == "melee":
                advance_chance = 0.75
            elif preferred == "move":
                advance_chance = 0.65
            if random.random() < advance_chance:
                moved = self._move_dungeon_core(player, dungeon, relation)
                self._log_trace(
                    dungeon,
                    f"dungeon_core side_gap_no_predict=advance moved={moved} preferred={preferred}"
                )
                self._log_duel_trace(dungeon, player, "side_gap_advance", extra=f"preferred={preferred}")
                if moved:
                    return True
            self.current_attack_mode = None
            self._log_trace(
                dungeon,
                f"dungeon_core side_gap_no_predict=wait preferred={preferred}"
            )
            self._log_duel_trace(dungeon, player, "side_gap_wait", extra=f"preferred={preferred}")
            return True

        predicted_dx, predicted_dy = dx, dy
        if abs(dx) == 2 and abs(dy) == 1:
            predicted_dy = 0
        elif abs(dy) == 2 and abs(dx) == 1:
            predicted_dx = 0

        if not self._can_use_attack_mode("line", predicted_dx, predicted_dy, dungeon, all_entities):
            return False

        mx = int((self.x + self.width / 2) // dungeon.tile_size)
        my = int((self.y + self.height / 2) // dungeon.tile_size)
        self.current_attack_mode = "line"
        self._log_trace(
            dungeon,
            f"dungeon_core side_gap_predict=line target=({mx + predicted_dx}, {my + predicted_dy}) preferred={preferred}"
        )
        self._log_duel_trace(dungeon, player, "side_gap_predict", extra=f"preferred={preferred}")
        self._handle_attack(predicted_dx, predicted_dy, player, dialog)
        if getattr(self, "is_attacking", False):
            self.predicted_attack_tile = (mx + predicted_dx, my + predicted_dy)
            return True
        return False

    def _try_dungeon_core_diagonal_decision(self, player, dungeon, all_entities, dialog, dx, dy, relation, distance):
        if getattr(self, "type", "") != "dungeon_core":
            return False
        if relation != "diagonal" or distance != "1":
            return False
        action, used_profile = self._choose_dungeon_core_diagonal_action(player)
        if action == "diagonal" and self._can_use_attack_mode("diagonal", dx, dy, dungeon, all_entities):
            self.current_attack_mode = "diagonal"
            self._log_trace(dungeon, f"dungeon_core diagonal_action=diagonal used_profile={used_profile}")
            self._log_duel_trace(dungeon, player, "diagonal_attack", extra=f"profile={used_profile}")
            self._handle_attack(dx, dy, player, dialog)
            return getattr(self, "is_attacking", False)
        if action == "wait":
            self.current_attack_mode = None
            self._log_trace(dungeon, f"dungeon_core diagonal_action=wait used_profile={used_profile}")
            self._log_duel_trace(dungeon, player, "diagonal_wait", extra=f"profile={used_profile}")
            return True
        if action == "step_front":
            moved = self._move_dungeon_core(player, dungeon, relation)
            self._log_trace(dungeon, f"dungeon_core diagonal_action=step_front moved={moved} used_profile={used_profile}")
            self._log_duel_trace(dungeon, player, "diagonal_step_front", extra=f"profile={used_profile}")
            return moved
        return False

    def _is_line_of_sight_clear(self, dx, dy, dungeon, all_entities):
        sx, sy = (1 if dx > 0 else -1 if dx < 0 else 0), (1 if dy > 0 else -1 if dy < 0 else 0)
        gx, gy = int((self.x + self.width/2)//dungeon.tile_size), int((self.y + self.height/2)//dungeon.tile_size)
        steps = abs(dx) if abs(dx) == abs(dy) else abs(dx) + abs(dy)
        for i in range(1, steps):
            cx, cy = gx + sx*i, gy + sy*i
            if not (0 <= cx < dungeon.map_width and 0 <= cy < dungeon.map_height) or dungeon.map_data[cy][cx] == 0: return False
            for e in all_entities:
                from components.sprites.player import Player
                if not (e == self or getattr(e, "is_dead", False) or isinstance(e, Player)) and int((e.x + e.width/2)//dungeon.tile_size) == cx and int((e.y + e.height/2)//dungeon.tile_size) == cy: return False
        return True

    def _execute_actual_attack(self, player, dungeon, dialog):
        from constants import ATTACK_ANIMATION_FRAMES, ATTACK_EFFECT_DATA
        self.is_attacking = True; self.attack_timer = ATTACK_ANIMATION_FRAMES; self.has_dealt_impact_damage = False
        spec = ENEMY_DATA.get(self.type, {})
        mode = getattr(self, "current_attack_mode", None)
        if mode and mode in self.attack_effects:
            pk = self.attack_effects.get(mode)
        else:
            pk = spec.get("ranged_attack_effect" if getattr(self, "is_long_range", False) else "close_attack_effect")
        self.current_attack_pattern = ATTACK_EFFECT_DATA.get(pk, {})
        from systems.sound_handler import sound_manager
        sound_manager.play_sfx(self.current_attack_pattern.get("launch_sound", "components/sounds/sfx/enemy_attack_common.wav"))
        vt = self.current_attack_pattern.get("visual")
        target_px, target_py = player.x, player.y
        predicted_tile = getattr(self, "predicted_attack_tile", None)
        if predicted_tile:
            target_px = predicted_tile[0] * dungeon.tile_size
            target_py = predicted_tile[1] * dungeon.tile_size
        if vt:
            if vt == "explosion": from systems.magic_handler import FireEffect; dungeon.magic_effects.append(FireEffect(target_px, target_py))
            else: from systems.magic_handler import ProjectileEffect; dungeon.magic_effects.append(ProjectileEffect(self.x, self.y, target_px, target_py, vt, ATTACK_ANIMATION_FRAMES))
        if self.current_attack_pattern.get("type") == "close":
            from constants import TILE_SIZE
            mx, my = int((self.x+self.width/2)//TILE_SIZE), int((self.y+self.height/2)//TILE_SIZE)
            if predicted_tile:
                px, py = predicted_tile
            else:
                px, py = int((player.x+player.width/2)//TILE_SIZE), int((player.y+player.height/2)//TILE_SIZE)
            self.dash_distance = (abs(px-mx)+abs(py-my) - (self.width/TILE_SIZE/2 + player.width/TILE_SIZE/2) + 1) * TILE_SIZE
        else: self.dash_distance = 0
        self.current_attack_damage_mult = 1.0
        if (
            getattr(self, "type", "") == "dungeon_core"
            and mode == "line"
            and getattr(self, "current_attack_distance", 0) == 2
        ):
            self.current_attack_damage_mult = 2 / 3

    def _deal_impact_damage(self, dungeon):
        from constants import COMBAT_LOG_WAIT_FRAMES
        t, d = getattr(self, "target_for_attack", None), getattr(self, "dialog_for_attack", None); self.peak_hold_timer = 30
        if not t or t.is_dead: return
        predicted_tile = getattr(self, "predicted_attack_tile", None)
        if predicted_tile:
            actual_tile = self._get_player_combat_tile(t, dungeon.tile_size)
            if actual_tile != predicted_tile:
                from systems.sound_handler import sound_manager
                sound_manager.play_sfx(SOUND_ATTACK_MISS)
                if d:
                    from systems.game_state import game_state
                    if d.is_active: d.text += "\n" + f"{self.name} の攻撃は外れた！"; d.auto_close_timer = COMBAT_LOG_WAIT_FRAMES
                    else: d.text = f"{self.name} の攻撃は外れた！"; d.is_active = True; game_state["dialog_modal"] = False; d.auto_close_timer = COMBAT_LOG_WAIT_FRAMES
                self.predicted_attack_tile = None
                return
        msg, dmg, crit, miss = deal_damage(self, t, damage_mult=getattr(self, "current_attack_damage_mult", 1.0))
        from systems.sound_handler import sound_manager
        sound_manager.play_sfx(SOUND_ATTACK_MISS if miss or dmg == 0 else (self.current_attack_pattern.get("hit_sound", "components/sounds/sfx/projectile_hit.wav")))
        if crit: dungeon.flash_timer = 10
        if (
            dmg > 0
            and not miss
            and getattr(t, "__class__", None).__name__ == "Player"
            and not getattr(t, "is_static", False)
            and (
                getattr(self, "current_attack_mode", None) == "knockback"
                or getattr(getattr(self, "current_attack_pattern", {}), "get", lambda *_: None)("pushback", False)
            )
        ):
            proc_chance = float(getattr(self, "knockback_proc_chance", 1.0))
            if random.random() < max(0.0, min(1.0, proc_chance)):
                self._apply_knockback_to_player(t, dungeon)
        if d:
            from systems.game_state import game_state
            if d.is_active: d.text += "\n" + msg; d.auto_close_timer = COMBAT_LOG_WAIT_FRAMES
            else: d.text = msg; d.is_active = True; game_state["dialog_modal"] = False; d.auto_close_timer = COMBAT_LOG_WAIT_FRAMES
        self.predicted_attack_tile = None

    def _apply_knockback_to_player(self, player, dungeon):
        tile = dungeon.tile_size
        bx = int((self.x + self.width / 2) // tile)
        by = int((self.y + self.height / 2) // tile)
        px = int((player.x + player.width / 2) // tile)
        py = int((player.y + player.height / 2) // tile)

        dx = px - bx
        dy = py - by
        if abs(dx) >= abs(dy):
            step = (1 if dx > 0 else -1, 0)
        else:
            step = (0, 1 if dy > 0 else -1)

        start_gx = int((player.x + player.width / 2) // tile)
        start_gy = int((player.y + player.height / 2) // tile)
        fgx, fgy = start_gx, start_gy

        def _can_stand(gx, gy):
            if not (0 <= gx < dungeon.map_width and 0 <= gy < dungeon.map_height):
                return False
            if dungeon.map_data[gy][gx] == 0:
                return False
            for e in getattr(dungeon, "enemies", []):
                if e is player or getattr(e, "is_dead", False):
                    continue
                if (gx, gy) in e.get_occupied_grids(dungeon.tile_size):
                    return False
            return True

        max_distance = max(1, int(getattr(self, "knockback_max_distance", 1)))
        for _ in range(max_distance):
            ngx, ngy = fgx + step[0], fgy + step[1]
            if not _can_stand(ngx, ngy):
                break
            fgx, fgy = ngx, ngy

        if (fgx, fgy) == (start_gx, start_gy):
            return False

        player.target_x = fgx * tile
        player.target_y = fgy * tile
        player.is_moving = True
        player.move_speed = 300
        player.flash_color = (180, 120, 255)
        try:
            from systems.magic_handler import KnockbackEffect
            dungeon.magic_effects.append(
                KnockbackEffect(
                    start_gx * tile,
                    start_gy * tile,
                    fgx * tile,
                    fgy * tile,
                    color=(220, 220, 255),
                    duration=15,
                )
            )
        except Exception:
            pass
        attacker_name = getattr(self, "name", "enemy")
        self._log_trace(dungeon, f"{attacker_name} knockback player to ({fgx}, {fgy})")
        return True

    def _move_dungeon_core_behind_player(self, player, dungeon):
        tile = dungeon.tile_size
        px = int((player.x + player.width / 2) // tile)
        py = int((player.y + player.height / 2) // tile)
        facing = getattr(player, "facing", None)
        if facing == "up":
            back = (0, 1)
            side_candidates = [(-1, 0), (1, 0)]
        elif facing == "down":
            back = (0, -1)
            side_candidates = [(-1, 0), (1, 0)]
        elif facing == "left":
            back = (1, 0)
            side_candidates = [(0, -1), (0, 1)]
        elif facing == "right":
            back = (-1, 0)
            side_candidates = [(0, -1), (0, 1)]
        else:
            mx = int((self.x + self.width / 2) // tile)
            my = int((self.y + self.height / 2) // tile)
            dx = px - mx
            dy = py - my
            if abs(dx) >= abs(dy):
                back = (-1 if dx > 0 else 1, 0)
                side_candidates = [(0, 1), (0, -1)]
            else:
                back = (0, -1 if dy > 0 else 1)
                side_candidates = [(1, 0), (-1, 0)]

        start_gx = int((self.x + self.width / 2) // tile)
        start_gy = int((self.y + self.height / 2) // tile)

        def _can_stand(gx, gy):
            if not (0 <= gx < dungeon.map_width and 0 <= gy < dungeon.map_height):
                return False
            if dungeon.map_data[gy][gx] == 0:
                return False
            if (gx, gy) in player.get_occupied_grids(dungeon.tile_size):
                return False
            for e in getattr(dungeon, "enemies", []):
                if e is self or getattr(e, "is_dead", False):
                    continue
                if (gx, gy) in e.get_occupied_grids(dungeon.tile_size):
                    return False
            return True

        def _try_line(step_dx, step_dy):
            gx, gy = start_gx, start_gy
            for _ in range(2):
                nx, ny = gx + step_dx, gy + step_dy
                if not _can_stand(nx, ny):
                    return None
                gx, gy = nx, ny
            return gx, gy

        final = _try_line(*back)
        if final is None:
            for cand in side_candidates:
                final = _try_line(*cand)
                if final is not None:
                    break
        if final is None:
            return False

        fgx, fgy = final
        self.target_x = fgx * tile
        self.target_y = fgy * tile
        self.is_moving = True
        self.move_speed = 300
        self._log_trace(dungeon, f"dungeon_core moved behind player to ({fgx}, {fgy})")
        return True

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

    def _get_trap_deploy_target(self, player, dungeon, all_entities):
        tile = dungeon.tile_size
        mx = int((self.x + self.width / 2) // tile)
        my = int((self.y + self.height / 2) // tile)
        px = int((player.x + player.width / 2) // tile)
        py = int((player.y + player.height / 2) // tile)
        if max(abs(px - mx), abs(py - my)) > 3:
            return None
        candidates = [
            (px + (1 if px >= mx else -1), py),
            (px, py + (1 if py >= my else -1)),
            (px + 1, py),
            (px - 1, py),
            (px, py + 1),
            (px, py - 1),
        ]
        def _occupied(gx, gy):
            if not (0 <= gx < dungeon.map_width and 0 <= gy < dungeon.map_height):
                return True
            if dungeon.map_data[gy][gx] != 1:
                return True
            if (gx, gy) in player.get_occupied_grids(tile):
                return True
            for e in all_entities:
                if e is self or getattr(e, "is_dead", False):
                    continue
                if (gx, gy) in e.get_occupied_grids(tile):
                    return True
            return any(t.x == gx and t.y == gy and not getattr(t, "is_triggered", False) for t in getattr(dungeon, "traps", []))
        for gx, gy in candidates:
            if not _occupied(gx, gy):
                return gx, gy
        return None

    def _deploy_trap(self, player, dungeon, all_entities, dialog=None):
        from components.sprites.trap import Trap
        trap_type = getattr(self, "trap_type", None)
        if not trap_type:
            return False
        if trap_type in ("random", "random_trap", "any"):
            from constants import TRAP_DATA
            trap_types = list(TRAP_DATA.keys())
            weights = [TRAP_DATA[k].get("weight", 1) for k in trap_types]
            trap_type = random.choices(trap_types, weights=weights, k=1)[0]
        target = self._get_trap_deploy_target(player, dungeon, all_entities)
        if not target:
            return False
        gx, gy = target
        try:
            from systems.magic_handler import ProjectileEffect
            from constants import ENEMY_DATA
            from systems.sound_handler import sound_manager
            spec = ENEMY_DATA.get(self.type, {})
            effect_type = spec.get("ranged_attack_effect") or spec.get("close_attack_effect") or "dark_bolt"
            tx = gx * dungeon.tile_size
            ty = gy * dungeon.tile_size
            sound_manager.play_sfx("components/sounds/sfx/light.wav")
            dungeon.magic_effects.append(
                ProjectileEffect(self.x, self.y, tx, ty, effect_type, duration=16)
            )
        except Exception:
            pass
        trap = Trap(gx, gy, trap_type, revealed=True, source=getattr(self, "enemy_type", None))
        dungeon.traps.append(trap)
        self._log_trace(dungeon, f"deployed trap={trap_type} at ({gx}, {gy})")
        if dialog:
            from constants import COMBAT_LOG_WAIT_FRAMES
            from systems.game_state import game_state
            trap_name = trap.data.get("name", "罠")
            msg = f"{self.name} は {trap_name}を 仕掛けた！"
            if dialog.is_active:
                dialog.text += "\n" + msg
            else:
                dialog.text = msg
                dialog.is_active = True
                game_state["dialog_modal"] = False
            dialog.auto_close_timer = COMBAT_LOG_WAIT_FRAMES
        return True

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
        if getattr(self, "battle_locked", False):
            self._log_trace(dungeon, "battle_locked: take_turn skipped")
            return
        if getattr(self, "is_dead", False):
            self._log_trace(dungeon, "take_turn bypassed: is_dead=True")
            return
        # スタン状態チェック
        if self.stun_turns > 0:
            self.stun_turns -= 1
            self._log_trace(dungeon, f"stunned! remaining turns: {self.stun_turns}")
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
            px, py = self._get_player_combat_tile(player, dungeon.tile_size)
            dx, dy = px - mx, py - my
            if abs(dx) + abs(dy) <= 1:
                self._handle_attack(dx, dy, player, dialog)
            else:
                self._log_trace(dungeon, f"immobilized ({self.immobilized_turns} turns left). Cannot move.")
            return

        if getattr(self, "type", "") == "dungeon_core":
            self._take_turn_dungeon_core(player, dungeon, all_entities, dialog)
            return

        mx, my = int((self.x+self.width/2)//dungeon.tile_size), int((self.y+self.height/2)//dungeon.tile_size)
        px, py = self._get_player_combat_tile(player, dungeon.tile_size)
        
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
        detect_rad = max(1, self.detect_range - player.get_aggro_modifier())
        if getattr(self, "damage_flash_timer", 0) > 0:
            detect_rad = max(detect_rad, self.damaged_detect_range)

        in_detect_range = abs(dx) <= detect_rad and abs(dy) <= detect_rad
        if not self.player_detected:
            if not in_detect_range:
                self._log_trace(dungeon, f"out of range (dist to player: {abs(dx)},{abs(dy)} > detect_range: {detect_rad}) | self:({self.x},{self.y}) player_actual:({player.x},{player.y}) ts:{dungeon.tile_size}")
                return
            self.player_detected = True
        else:
            if not in_detect_range:
                self.player_detected = False
                self._log_trace(dungeon, f"lost player: range break ({abs(dx)},{abs(dy)} > {detect_rad})")
                return
            pursuit_evasion = max(0, getattr(player, "get_pursuit_evasion", lambda: 0)())
            if pursuit_evasion > 0 and getattr(self, "damage_flash_timer", 0) <= 0 and (abs(dx) + abs(dy)) > 1:
                lose_chance = min(0.60, float(pursuit_evasion) * 0.10)
                if random.random() < lose_chance:
                    self.player_detected = False
                    self._log_trace(dungeon, f"lost player: pursuit_evasion={pursuit_evasion} chance={lose_chance:.2f}")
                    return
            
        # 困惑度テーブルを参照してぼーっと確率を決定（一時的 stupidity も加算）
        effective_stupidity = min(10, self.stupidity + self.stupidity_temp)
        wander_chance = STUPIDITY_WANDER_RATES.get(effective_stupidity, effective_stupidity / 10.0)
        if wander_chance > 0 and random.random() < wander_chance:
            self._log_trace(dungeon, f"decided to WANDER (chance: {wander_chance})")
            self._move_randomly(dungeon, all_entities)
            return

        trap_chance = float(getattr(self, "trap_proc_chance", 0.0))
        if trap_chance > 0 and random.random() < max(0.0, min(1.0, trap_chance)):
            if self._deploy_trap(player, dungeon, all_entities, dialog):
                return

        # `smart_ranged_move` は「理想行動を取りやすい」だけにして、
        # `stupidity` が高いほど位置取りの精度を落とす
        smart_move_leniency = max(0.25, 1.0 - (effective_stupidity * 0.08))

        # ── [DIAGONAL] 斜め位置AIの意思決定（待機 or サイドステップ） ──
        # プレイヤーが斜め1マス (adx==1, ady==1) の場合、stupidityに応じた確率で
        # 「待機」か「サイドステップ（向きを変えずに移動）」かを選ぶ
        # 賢い（低stupidity）ほどこの判断を行いやすい
        if abs(dx) == 1 and abs(dy) == 1:
            act_chance = STUPIDITY_FLANK_RATES.get(effective_stupidity, 0.0)
            if act_chance > 0 and random.random() < act_chance:
                # 待機 or サイドステップを半々で選ぶ
                if random.random() < 0.5:
                    self._log_trace(dungeon, f"diagonal-ai: stupidity={effective_stupidity} -> waiting (chance={act_chance})")
                    return
                else:
                    # サイドステップ: 向きを変えずにdx方向またはdy方向に1マス移動
                    # プレイヤーに正面を向けないようdx方向（横）を優先する
                    saved_facing = self.facing
                    moved = False
                    # dx方向（横）を先に試みる
                    sdx_px = mx + (1 if dx > 0 else -1)
                    if self.can_move_grid(sdx_px * dungeon.tile_size, my * dungeon.tile_size, dungeon, debug_log=False):
                        self.target_x = sdx_px * dungeon.tile_size
                        self.target_y = my * dungeon.tile_size
                        self.facing = saved_facing  # 向きを維持
                        self.is_moving = True
                        self.step_toggle = not self.step_toggle
                        moved = True
                    else:
                        # dy方向（縦）を試みる
                        sdy_py = my + (1 if dy > 0 else -1)
                        if self.can_move_grid(mx * dungeon.tile_size, sdy_py * dungeon.tile_size, dungeon, debug_log=False):
                            self.target_x = mx * dungeon.tile_size
                            self.target_y = sdy_py * dungeon.tile_size
                            self.facing = saved_facing  # 向きを維持
                            self.is_moving = True
                            self.step_toggle = not self.step_toggle
                            moved = True
                    if moved:
                        self._log_trace(dungeon, f"diagonal-ai: stupidity={effective_stupidity} -> sidestep (facing={saved_facing}, moved to ({self.target_x//dungeon.tile_size},{self.target_y//dungeon.tile_size}))")
                        return
                    else:
                        # サイドステップ失敗時は待機
                        self._log_trace(dungeon, f"diagonal-ai: stupidity={effective_stupidity} -> sidestep failed, waiting")
                        return

        # ── [ESCAPE_BLOCK] 逃げ道封鎖AI + フランク (削除時はこのブロックごと除去) ──
        if (abs(dx) + abs(dy)) > 1:
            ally_search_radius = max(1, detect_rad)
            nearby_allies = [
                e for e in all_entities
                if e is not self and isinstance(e, Enemy) and not getattr(e, "is_dead", False)
                and abs(int((e.x+e.width/2)//dungeon.tile_size) - px) <= ally_search_radius
                and abs(int((e.y+e.height/2)//dungeon.tile_size) - py) <= ally_search_radius
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
                ideal = 2 if self.attack_range > 1 else 1
            else:
                ideal = 1 if self.attack_priority == "close" else (2 if self.attack_range == 2 else max(1, self.attack_range - 1))
            if self.attack_priority == "ranged" and abs(dx) > abs(dy):
                ideal = max(1, ideal + 1)
            los = self._is_in_attack_range(dx, dy) and self._is_line_of_sight_clear(dx, dy, dungeon, all_entities); gdist = abs(dx)+abs(dy)
            self._log_trace(dungeon, f"AI status: gdist={gdist}, ideal={ideal}, los={los}, attack_priority={self.attack_priority}")
            if gdist == ideal:
                if los:
                    if not self.turn_attack:
                        # 向き変え攻撃なし: 向きが違う場合はターンを使って向くだけ
                        needed = "right" if dx > 0 else "left" if dx < 0 else "down" if dy > 0 else "up"
                        if self.facing != needed:
                            self.facing = needed
                            self._log_trace(dungeon, f"turned to face player ({needed}), no attack this turn")
                            return
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
                if random.random() < (0.55 + 0.25 * smart_move_leniency) and smart_moved:
                    return
                self._log_trace(dungeon, "ranged-attacking close player")
                self._handle_attack(dx, dy, player, dialog)
                return
            else:
                if los:
                    self._log_trace(dungeon, "attacking player from distance")
                    self._handle_attack(dx, dy, player, dialog)
                    return
                if random.random() < smart_move_leniency:
                    smart_moved = self._move_smartly_check_success(player, dungeon, all_entities, px, py, mx, my, occupied_cells, ideal)
                else:
                    smart_moved = False
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

    def _get_dungeon_core_attack_weights(self, player, dungeon):
        relation, distance = get_relation_and_distance(player, self, dungeon.tile_size)
        preferred = player.tactical_profile.get_preferred_action(relation, distance) if hasattr(player, "tactical_profile") else None
        profile = getattr(player, "tactical_profile", None)
        magic_read = self._read_player_magic_habit(player, relation, distance)
        melee_bias = 0.0
        move_bias = 0.0
        magic_bias = 0.0
        item_bias = 0.0
        if profile:
            melee_bias = profile.get_action_probability("melee", relation=relation, distance=distance, default=0.0)
            move_bias = profile.get_action_probability("move", relation=relation, distance=distance, default=0.0)
            magic_bias = profile.get_action_probability("magic", relation=relation, distance=distance, default=0.0)
            item_bias = profile.get_action_probability("item", relation=relation, distance=distance, default=0.0)
        weights = {"line": 50, "diagonal": 45, "counter": 20, "knockback": 18}
        if relation == "front":
            weights["line"] += 10
            weights["counter"] += 20
            weights["knockback"] += 28
            if magic_read == "magic_fire":
                weights["counter"] += 30
                weights["line"] += 4
            if preferred == "melee":
                weights["counter"] += 50
                weights["knockback"] += 25
            elif preferred == "move":
                weights["diagonal"] += 20
            elif move_bias > melee_bias:
                weights["diagonal"] += 12
                weights["line"] -= 4
            elif melee_bias >= move_bias and melee_bias >= magic_bias:
                weights["counter"] += 8
        elif relation == "diagonal":
            weights["diagonal"] += 45
            weights["counter"] += 5
            if magic_read == "magic_fire":
                weights["counter"] += 10
            if preferred == "move":
                weights["diagonal"] += 20
            elif preferred == "melee":
                weights["line"] += 2
            if move_bias > melee_bias:
                weights["diagonal"] += 18
                weights["line"] -= 3
            elif melee_bias > move_bias:
                weights["line"] += 8
            if magic_bias > 0.35:
                weights["line"] += 4
        elif relation == "side":
            weights["diagonal"] += 12
            weights["counter"] += 25
            weights["knockback"] += 24
            if magic_read == "magic_fire":
                weights["counter"] += 8
            if preferred == "melee":
                weights["counter"] += 35
            if move_bias > melee_bias:
                weights["diagonal"] += 10
            elif melee_bias > move_bias:
                weights["counter"] += 6
        elif relation == "far":
            weights["line"] += 10
            weights["diagonal"] += 10
            weights["counter"] -= 5
            weights["knockback"] -= 5
            if magic_read == "magic_fire":
                weights["counter"] += 8
            if magic_bias > move_bias:
                weights["line"] += 10
                weights["diagonal"] += 6
            elif move_bias > magic_bias:
                weights["diagonal"] += 12
            if item_bias > 0.25:
                weights["line"] += 2
        return weights, relation, distance, preferred

    def _read_player_magic_habit(self, player, relation, distance):
        profile = getattr(player, "tactical_profile", None)
        if not profile:
            return None
        fire_local = profile.get_action_total("magic_fire", relation=relation, distance=distance)
        knockback_local = profile.get_action_total("magic_knockback", relation=relation, distance=distance)
        magic_local = profile.get_action_total("magic", relation=relation, distance=distance)
        if fire_local >= 2 or knockback_local >= 2:
            return "magic_fire" if fire_local >= knockback_local else "magic_knockback"
        if magic_local >= 2 and fire_local == 0 and knockback_local == 0:
            return "magic_barrier"
        fire_total = profile.get_action_total("magic_fire")
        knockback_total = profile.get_action_total("magic_knockback")
        magic_total = profile.get_action_total("magic")
        if fire_total >= 3 or knockback_total >= 3:
            return "magic_fire" if fire_total >= knockback_total else "magic_knockback"
        if magic_total >= 3 and fire_total == 0 and knockback_total == 0:
            return "magic_barrier"
        return None

    def _get_turn_attack_chance(self, player, relation, distance):
        profile = getattr(player, "tactical_profile", None)
        base = max(0.0, min(1.0, getattr(self, "turn_attack_chance", 0.5)))
        if not profile:
            return base
        melee = profile.get_action_probability("melee", relation=relation, distance=distance, default=0.0)
        move = profile.get_action_probability("move", relation=relation, distance=distance, default=0.0)
        magic = profile.get_action_probability("magic", relation=relation, distance=distance, default=0.0)
        item = profile.get_action_probability("item", relation=relation, distance=distance, default=0.0)
        learned = 0.2 + (0.6 * melee) + (0.15 * magic) + (0.05 * item) - (0.2 * move)
        return max(0.05, min(0.95, learned if learned > 0 else base))

    def _can_use_attack_mode(self, mode, dx, dy, dungeon, all_entities):
        if mode == "line":
            line_range = max(1, self.attack_range_line)
            if not (
                (dy == 0 and dx != 0 and abs(dx) <= line_range)
                or (dx == 0 and dy != 0 and abs(dy) <= line_range)
            ):
                return False
            return self._is_line_of_sight_clear(dx, dy, dungeon, all_entities)
        if mode == "diagonal":
            if not (abs(dx) == abs(dy) and 0 < abs(dx) <= max(1, self.attack_range_diagonal)):
                return False
            return self._is_line_of_sight_clear(dx, dy, dungeon, all_entities)
        if mode == "counter":
            return max(abs(dx), abs(dy)) == 1
        if mode == "knockback":
            return max(abs(dx), abs(dy)) == 1
        return False

    def _score_dungeon_core_tile(self, gx, gy, px, py, relation=None):
        dx, dy = px - gx, py - gy
        dist = max(abs(dx), abs(dy))
        line_range = max(1, self.attack_range_line)
        line_ready = ((dy == 0 and dx != 0 and abs(dx) <= line_range)
                      or (dx == 0 and dy != 0 and abs(dy) <= line_range))
        diag_ready = abs(dx) == abs(dy) and 0 < abs(dx) <= max(1, self.attack_range_diagonal)
        score = 0
        if line_ready:
            score += 35
        if diag_ready:
            score += 35
        if max(abs(dx), abs(dy)) == 1:
            score += 10
        score -= abs(dist - 2) * 4
        score += max(0, 8 - dist * 2)
        if relation == "front":
            if diag_ready:
                score += 20
            elif line_ready:
                score -= 8
        elif relation == "diagonal":
            if diag_ready:
                score += 14
        elif relation == "side":
            if line_ready:
                score += 10
        if dist >= 3:
            if line_ready or diag_ready:
                score += 18
            else:
                score -= 10
        return score

    def _score_dungeon_core_defensive_tile(self, gx, gy, px, py, magic_read):
        dx, dy = px - gx, py - gy
        dist = max(abs(dx), abs(dy))
        line_range = max(1, self.attack_range_line)
        line_ready = ((dy == 0 and dx != 0 and abs(dx) <= line_range)
                      or (dx == 0 and dy != 0 and abs(dy) <= line_range))
        diag_ready = abs(dx) == abs(dy) and 0 < abs(dx) <= max(1, self.attack_range_diagonal)

        score = 0
        if dist == 1:
            score += 26
        elif dist == 2:
            score += 14
        else:
            score -= dist * 20

        if line_ready:
            score += 22
        if diag_ready:
            score += 22

        if magic_read == "magic_fire":
            if dist == 2:
                score += 12
            if dx != 0 and dy != 0:
                score += 8
        elif magic_read == "magic_knockback":
            if dx != 0 and dy != 0:
                score += 10
            else:
                score -= 4

        return score

    def _move_to_best_core_candidate(self, dungeon, candidates):
        valid = []
        for score, facing, tx, ty in candidates:
            if self.can_move_grid(tx, ty, dungeon, debug_log=False):
                valid.append((score, facing, tx, ty))
        if not valid:
            return False
        valid.sort(key=lambda x: x[0], reverse=True)
        best_score, best_facing, best_tx, best_ty = valid[0]
        self.target_x, self.target_y = best_tx, best_ty
        self.facing = best_facing
        self.is_moving = True
        self.step_toggle = not self.step_toggle
        self._log_trace(dungeon, f"dungeon_core moved to ({best_tx//dungeon.tile_size}, {best_ty//dungeon.tile_size}) score={best_score}")
        return True

    def _move_dungeon_core(self, player, dungeon, relation=None):
        px, py = self._get_player_combat_tile(player, dungeon.tile_size)
        candidates = []
        for facing, sdx, sdy in [("right", dungeon.tile_size, 0), ("left", -dungeon.tile_size, 0), ("down", 0, dungeon.tile_size), ("up", 0, -dungeon.tile_size)]:
            tx, ty = self.x + sdx, self.y + sdy
            if not self.can_move_grid(tx, ty, dungeon, debug_log=False):
                continue
            gx = int((tx + self.width / 2) // dungeon.tile_size)
            gy = int((ty + self.height / 2) // dungeon.tile_size)
            score = self._score_dungeon_core_tile(gx, gy, px, py, relation)
            candidates.append((score, facing, tx, ty))
        return self._move_to_best_core_candidate(dungeon, candidates)

    def _take_turn_dungeon_core(self, player, dungeon, all_entities, dialog=None):
        if getattr(self, "counter_ready_turns", 0) > 0:
            self.counter_ready_turns = 0
        mx, my = int((self.x+self.width/2)//dungeon.tile_size), int((self.y+self.height/2)//dungeon.tile_size)
        px, py = self._get_player_combat_tile(player, dungeon.tile_size)
        dx, dy = px - mx, py - my
        profile = getattr(player, "tactical_profile", None)
        melee_bias = 0.0
        move_bias = 0.0
        magic_bias = 0.0
        item_bias = 0.0
        if profile:
            total_actions = (
                profile.get_action_total("melee")
                + profile.get_action_total("move")
                + profile.get_action_total("magic")
                + profile.get_action_total("item")
            )
            if total_actions > 0:
                melee_bias = profile.get_action_total("melee") / total_actions
                move_bias = profile.get_action_total("move") / total_actions
                magic_bias = profile.get_action_total("magic") / total_actions
                item_bias = profile.get_action_total("item") / total_actions
        weights, relation, distance, preferred = self._get_dungeon_core_attack_weights(player, dungeon)
        magic_read = self._read_player_magic_habit(player, relation, distance)
        self.turn_attack_chance = self._get_turn_attack_chance(player, relation, distance)
        if self._try_dungeon_core_predicted_attack(player, dungeon, all_entities, dialog, dx, dy, relation, distance):
            return
        if self._try_dungeon_core_side_gap_prediction(player, dungeon, all_entities, dialog, dx, dy, relation, distance):
            return
        if self._try_dungeon_core_diagonal_decision(player, dungeon, all_entities, dialog, dx, dy, relation, distance):
            return
        available = []
        for mode in ("line", "diagonal", "counter", "knockback"):
            if distance == "1" and mode == "diagonal":
                continue
            if self._can_use_attack_mode(mode, dx, dy, dungeon, all_entities):
                available.append((weights.get(mode, 0), mode))
        if available:
            available.sort(key=lambda x: x[0], reverse=True)
            if relation in ("front", "diagonal") and distance == "1":
                chosen_mode = random.choices(
                    [mode for _, mode in available],
                    weights=[max(1, weight) for weight, _ in available],
                    k=1,
                )[0]
            else:
                chosen_mode = available[0][1]
            self.current_attack_mode = chosen_mode
            self._log_trace(dungeon, f"dungeon_core action={self.current_attack_mode} relation={relation} distance={distance} preferred={preferred}")
            self._log_duel_trace(dungeon, player, self.current_attack_mode, extra=f"preferred={preferred}")
            if chosen_mode == "knockback":
                self._handle_attack(dx, dy, player, dialog)
                return
            if chosen_mode == "counter":
                self._handle_attack(dx, dy, player, dialog)
                return
            self._handle_attack(dx, dy, player, dialog)
            return

        if relation in ("front", "diagonal") and distance == "2":
            rush_candidates = []
            for facing, sdx, sdy in [("right", dungeon.tile_size, 0), ("left", -dungeon.tile_size, 0), ("down", 0, dungeon.tile_size), ("up", 0, -dungeon.tile_size)]:
                tx, ty = self.x + sdx, self.y + sdy
                if not self.can_move_grid(tx, ty, dungeon, debug_log=False):
                    continue
                gx = int((tx + self.width / 2) // dungeon.tile_size)
                gy = int((ty + self.height / 2) // dungeon.tile_size)
                score = self._score_dungeon_core_tile(gx, gy, px, py, relation)
                if max(abs(px - gx), abs(py - gy)) == 1:
                    score += 18
                rush_candidates.append((score, facing, tx, ty))
            if rush_candidates:
                rush_candidates.sort(key=lambda x: x[0], reverse=True)
                best_score, best_facing, best_tx, best_ty = rush_candidates[0]
                self.target_x, self.target_y = best_tx, best_ty
                self.facing = best_facing
                self.is_moving = True
                self.step_toggle = not self.step_toggle
                self._log_trace(dungeon, f"dungeon_core rush to ({best_tx//dungeon.tile_size}, {best_ty//dungeon.tile_size}) score={best_score}")
                self._log_duel_trace(dungeon, player, "rush", extra=f"relation={relation}")
                return

        if distance == "3plus":
            wait_bias = 0.0
            if profile:
                wait_bias = profile.get_action_probability("wait", relation=relation, distance=distance, default=0.0)
            if wait_bias <= 0.0:
                total_bias = move_bias + item_bias + magic_bias + melee_bias
                if total_bias > 0:
                    wait_bias = (move_bias + item_bias + magic_bias) / max(total_bias, 1e-6)
                    if melee_bias > max(move_bias, item_bias, magic_bias):
                        wait_bias *= 0.6
                else:
                    wait_bias = 0.18
            if preferred == "move":
                wait_bias += 0.08
            elif preferred == "melee":
                wait_bias -= 0.05
            elif preferred == "item":
                wait_bias += 0.03
            elif preferred == "magic":
                wait_bias += 0.02
            if magic_read == "magic_fire":
                wait_bias += 0.04
            wait_weight = max(5, min(45, int(wait_bias * 100)))
            if random.randint(1, 100) <= wait_weight:
                self.current_attack_mode = None
                self._log_trace(dungeon, f"dungeon_core wait relation={relation} distance={distance} preferred={preferred}")
                self._log_duel_trace(dungeon, player, "wait", extra=f"relation={relation}")
                return
            rush_candidates = []
            for facing, sdx, sdy in [("right", dungeon.tile_size, 0), ("left", -dungeon.tile_size, 0), ("down", 0, dungeon.tile_size), ("up", 0, -dungeon.tile_size)]:
                tx, ty = self.x + sdx, self.y + sdy
                if not self.can_move_grid(tx, ty, dungeon, debug_log=False):
                    continue
                gx = int((tx + self.width / 2) // dungeon.tile_size)
                gy = int((ty + self.height / 2) // dungeon.tile_size)
                score = self._score_dungeon_core_tile(gx, gy, px, py, relation)
                if max(abs(px - gx), abs(py - gy)) < max(abs(px - mx), abs(py - my)):
                    score += 22
                rush_candidates.append((score, facing, tx, ty))
            if rush_candidates:
                rush_candidates.sort(key=lambda x: x[0], reverse=True)
                best_score, best_facing, best_tx, best_ty = rush_candidates[0]
                self.target_x, self.target_y = best_tx, best_ty
                self.facing = best_facing
                self.is_moving = True
                self.step_toggle = not self.step_toggle
                self._log_trace(dungeon, f"dungeon_core advance to ({best_tx//dungeon.tile_size}, {best_ty//dungeon.tile_size}) score={best_score}")
                self._log_duel_trace(dungeon, player, "advance", extra=f"relation={relation}")
                return

            self.current_attack_mode = None
            moved = self._move_dungeon_core(player, dungeon, relation)
            if moved:
                self._log_duel_trace(dungeon, player, "reposition")
            else:
                self._log_duel_trace(dungeon, player, "wait")

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
        movement_finished = self.update_animation(dt)
        if movement_finished:
            self._face_player_after_move(dungeon)

    def _face_player_after_move(self, dungeon):
        chance = getattr(self, "move_face_chance", 0.0)
        if not chance:
            return
        if random.random() >= chance:
            return
        player = getattr(dungeon, "player", None)
        if not player or getattr(player, "is_dead", False):
            return
        mx = int((self.x + self.width / 2) // dungeon.tile_size)
        my = int((self.y + self.height / 2) // dungeon.tile_size)
        px = int((player.x + player.width / 2) // dungeon.tile_size)
        py = int((player.y + player.height / 2) // dungeon.tile_size)
        dx = px - mx
        dy = py - my
        if dx == 0 and dy == 0:
            return
        if abs(dx) > abs(dy):
            needed = "right" if dx > 0 else "left"
        else:
            needed = "down" if dy > 0 else "up"
        if self.facing != needed:
            self.facing = needed
            self._log_trace(dungeon, f"move_face: turned to {needed}")

    def update_animation(self, dt=1/60):
        self.idle_anim_timer = (self.idle_anim_timer + 1) % 60
        if getattr(self, "attack_pre_delay_timer", 0) > 0:
            if getattr(self, "damage_flash_timer", 0) > 0: self.damage_flash_timer -= 1
            movement_finished = self.process_movement(dt)
            if movement_finished: self.move_speed = 300
            return movement_finished
        if getattr(self, "peak_hold_timer", 0) > 0:
            self.peak_hold_timer -= 1
            if getattr(self, "damage_flash_timer", 0) > 0: self.damage_flash_timer -= 1
            movement_finished = self.process_movement(dt)
            if movement_finished: self.move_speed = 300
            return movement_finished
        movement_finished = super().update_animation(dt)
        if not self.is_moving: self.move_speed = 300
        return movement_finished

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
