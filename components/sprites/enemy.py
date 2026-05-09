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
    ENEMY_DATA, SOUND_ATTACK_HIT, SOUND_ATTACK_MISS,
    WEAPON_DATA, ARMOR_DATA, SHIELD_DATA
)
from systems.combat_handler import deal_damage

class Enemy(Entity):
    # クラスレベルで画像をキャッシュする（同じ種類の敵で画像を共有してメモリとCPUを節約）
    _image_cache = {}
    _scaled_image_cache = {} # {(img_obj, phase): surface}
    
    @classmethod
    def clear_cache(cls):
        """蓄積された敵画像のキャッシュを解放する（メモリ節約用）"""
        count = len(cls._image_cache) + len(cls._scaled_image_cache)
        cls._image_cache = {}
        cls._scaled_image_cache = {}
        if count > 0:
            print(f"[MEMORY] Enemy image cache cleared ({count} items)")

    def __init__(self, x, y, enemy_type, width=None, height=None, player=None):
        if enemy_type not in ENEMY_DATA:
            enemy_type = "slime" # デフォルト
            
        data = ENEMY_DATA[enemy_type]
        from constants import TILE_SIZE
        
        # [NEW] image_scale に基づいてサイズを決定（デフォルトは1倍 = TILE_SIZE）
        scale = data.get("image_scale", 1.0)
        self.width = max(1, int(TILE_SIZE * scale) if width is None else width)
        self.height = max(1, int(TILE_SIZE * scale) if height is None else height)
        
        # [NEW] 障害物(is_static)の場合は HP をプレイヤーの攻撃力の倍率として扱う
        self.is_static = data.get("is_static", False)
        hp_val = data.get("hp", 10)
        if self.is_static and player:
            from systems.math_utils import hardcore_round
            p_atk = getattr(player, "total_attack", player.attack)
            hp_val = hardcore_round(hp_val * p_atk, is_hp=True)
            print(f"[Obstacle] {enemy_type} HP set to {hp_val} (Multiplier: {data.get('hp')} x Atk: {p_atk})")
            
        # 共通親クラス（Entity）の初期化を呼び出す
        self.attack = data.get("attack", 0) # [MOD] 省略時は0
        super().__init__(x, y, hp_val, hp_val, self.attack, self.width, self.height)
        self.type = enemy_type
        self.name = data.get("name", "モンスター")
        self.defense = data.get("defense", 0) # [NEW] 防御力
        self.evasion = data.get("evasion", 0) # [NEW] 回避力
        self.attack_pre_delay_timer = 0 # 攻撃前の溜め用タイマー
        # ★ 各モンスターの個性を設定するためのパラメータたち
        self.attack_range = data.get("attack_range", 1) # [MOD] 省略時は1
        self.stupidity = data.get("stupidity", 0) # [MOD] 省略時は0（賢い）
        self.dash_distance = data.get("dash_distance", 50)
        self.is_long_range = False # 遠距離攻撃フラグ
        self.attack_priority = data.get("attack_priority", "close")
        # self.is_static は上部で判定済み
        
        # 討伐時の報酬パラメータ
        self.exp = data.get("exp", 5)
        self.drops = data.get("drops", [])
        self.is_boss = data.get("is_boss", False) # [NEW] ボスフラグ
        self.bgm = data.get("bgm") # [NEW] ボス用BGM
        
        # 戦闘パラメータ
        self.crit_rate = data.get("crit_rate", 0.01) # 会心率
        
        # 命中値 (100 = 命中100%)
        self.accuracy_close = data.get("accuracy_close", data.get("accuracy_bonus", 100))
        self.accuracy_ranged = data.get("accuracy_ranged", data.get("accuracy_bonus", 100))
        
        # 攻撃時に付与するステータス
        self.status_to_inflict = data.get("status")
        self.status_chance = data.get("status_chance", 100) # 付与確率 (0-100)
        
        # 画像の読み込み（キャッシュがあればそれを使う）
        color_hex = data.get("image_color")
        cache_key = (enemy_type, self.width, self.height, color_hex)
        
        if cache_key in Enemy._image_cache:
            self.images = Enemy._image_cache[cache_key]
        else:
            self.images = {}
            image_path = data.get("image_path")
            folder_path = data.get("image_folder", "")
            
            # 着色用の色を取得
            tint_color = None
            if color_hex:
                try:
                    c = color_hex.lstrip('#')
                    tint_color = tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
                except:
                    pass

            def apply_tint(surface):
                if tint_color:
                    tinted = surface.copy()
                    tinted.fill(tint_color, special_flags=pygame.BLEND_RGB_MULT)
                    return tinted
                return surface
            
            # 1. 直接画像パスが指定されている場合
            if image_path:
                try:
                    img = pygame.image.load(image_path).convert_alpha()
                    img = pygame.transform.scale(img, (self.width, self.height))
                    img = apply_tint(img)
                    # 左右反転を適用（障害物は除外）
                    if not self.is_static:
                        self.images = {
                            "up": img, "down": img, "left": img,
                            "right": pygame.transform.flip(img, True, False)
                        }
                    else:
                        self.images = {d: img for d in ["up", "down", "left", "right"]}
                except Exception as e:
                    print(f"Error loading image_path {image_path}: {e}")
            
            # 2. フォルダパスが指定されている場合（各方向のファイルを読み込み）
            if not self.images and folder_path:
                for d in ["up", "down", "left", "right"]:
                    try:
                        img = pygame.image.load(f"{folder_path}/{d}.png").convert_alpha()
                        img = apply_tint(img)
                    except Exception as e:
                        # 右向き画像がない場合は左向きを反転して使う（障害物以外）
                        if d == "right" and not self.is_static and "left" in self.images:
                            img = pygame.transform.flip(self.images["left"], True, False)
                            # 警告ではなく通知レベルにする
                            print(f"[INFO] Using flipped left frame for enemy 'right' in {folder_path}")
                        else:
                            # それ以外の欠落は警告を出す
                            print(f"[\033[93mWARNING\033[0m] Failed to load enemy frame {d} in {folder_path}: {e}")
                            try:
                                fallback = f"{folder_path}/down.png"
                                img = pygame.image.load(fallback).convert_alpha()
                            except:
                                img = pygame.Surface((self.width, self.height))
                    
                    if img:
                        img = pygame.transform.scale(img, (self.width, self.height))
                    self.images[d] = img
            
            # 3. それでも画像がない場合のフォールバック
            if not self.images:
                pink_surf = pygame.Surface((self.width, self.height))
                pink_surf.fill((255, 0, 255))
                self.images = {d: pink_surf for d in ["up", "down", "left", "right"]}
            
            # キャッシュに保存
            Enemy._image_cache[cache_key] = self.images
        
        self.idle_anim_timer = 0


    def draw(self, screen, camera_x, camera_y):
        import math
        draw_x = self.x - camera_x
        draw_y = self.y - camera_y

        # 【攻撃時の突進演出】 
        if self.is_attacking:
            offset = 0
            # 1. 溜め期間（体が後ろに引く＆細かく震える）
            if self.attack_pre_delay_timer > 0:
                from constants import ATTACK_PRE_DELAY_FRAMES
                progress = (ATTACK_PRE_DELAY_FRAMES - self.attack_pre_delay_timer) / ATTACK_PRE_DELAY_FRAMES
                pull_back = -15 * progress 
                vibrate = 2 * math.sin(self.attack_pre_delay_timer * 2) if self.attack_pre_delay_timer < 15 else 0
                offset = pull_back + vibrate
            
            # 2. 突進＆戻り（Attack Timer中）
            elif getattr(self, "attack_timer", 0) > 0 and getattr(self, "current_attack_pattern", {}).get("type") == "close":
                from constants import ATTACK_ANIMATION_FRAMES
                t = (ATTACK_ANIMATION_FRAMES - self.attack_timer) / ATTACK_ANIMATION_FRAMES
                
                # 前半20%（0.0 ~ 0.2）でダッシュ
                if t <= 0.2:
                    dash_progress = t / 0.2
                    offset = -15 + ((self.dash_distance + 15) * dash_progress)
                # 0.2〜の残りで戻る（ピークで止まるのは peak_hold_timer が担うので描画ロジックはシンプルに！）
                else:
                    return_progress = (t - 0.2) / 0.8
                    offset = self.dash_distance * (1 - return_progress)

            if self.facing == "up": draw_y -= offset
            elif self.facing == "down": draw_y += offset
            elif self.facing == "left": draw_x -= offset
            elif self.facing == "right": draw_x += offset
        
        # 【遠距離攻撃時の予兆演出】 
        if self.is_attacking and getattr(self, "is_long_range", False) and self.attack_pre_delay_timer > 0:
            import math
            # 小刻みに震える
            vibrate = 3 * math.sin(self.attack_pre_delay_timer * 3)
            draw_x += vibrate
            # 魔法陣のような円を描画
            pygame.draw.circle(screen, (255, 255, 255, 100), (draw_x + self.width//2, draw_y + self.height//2), 30 + 10 * math.sin(self.attack_pre_delay_timer * 0.2), 2)
        
        # アニメーション（呼吸）の計算（[NEW] 障害物は呼吸しない）
        scale_anim_x, scale_anim_y = 1.0, 1.0
        phase = 0
        if not self.is_attacking and not self.is_static:
            (scale_anim_x, scale_anim_y), phase = self.get_breathing_scale()
        
        # 画面に映っている範囲にある時だけ描画する
        if -self.width <= draw_x <= screen.get_width() and -self.height <= draw_y <= screen.get_height():
            # 画像の取得
            base_img = self.images.get(self.facing)
            if not base_img:
                base_img = pygame.Surface((self.width, self.height))
                base_img.fill((255, 0, 255))
            
            # --- [OPTIMIZED] スケーリングキャッシュの利用 ---
            cache_key = (base_img, "attack" if self.is_attacking else phase)
            current_img = Enemy._scaled_image_cache.get(cache_key)
            
            if current_img is None:
                if self.is_attacking:
                    w, h = base_img.get_size()
                    current_img = pygame.transform.scale(base_img, (int(w * 1.2), int(h * 1.2)))
                elif not self.is_static:
                    w, h = base_img.get_size()
                    current_img = pygame.transform.smoothscale(base_img, (int(w * scale_anim_x), int(h * scale_anim_y)))
                else:
                    current_img = base_img
                Enemy._scaled_image_cache[cache_key] = current_img

            # 足元を基準に位置を調整
            img_w, img_h = current_img.get_size()
            draw_x += (self.width - img_w) / 2
            draw_y += (self.height - img_h)
                
            # ダメージを受けた時は赤くしてチカチカ点滅させる！
            is_visible = True
            from constants import HIT_STUN_DURATION
            if self.damage_flash_timer > HIT_STUN_DURATION:
                # 4フレーム周期で点滅 (2フレーム表示、2フレーム非表示)
                if (self.damage_flash_timer - HIT_STUN_DURATION) % 4 < 2:
                    is_visible = False
            
            
            # モンスター本体の描画
            if is_visible:
                screen.blit(current_img, (draw_x, draw_y))


    def _move_randomly(self, dungeon, all_entities):
        """ランダムな方向へ1歩移動を試みる（壁があれば移動失敗でターン消費のみ）"""
        directions = [
            ("right", dungeon.tile_size, 0),
            ("left", -dungeon.tile_size, 0),
            ("down", 0, dungeon.tile_size),
            ("up", 0, -dungeon.tile_size)
        ]
        facing, dx, dy = random.choice(directions)
        test_x = self.x + dx
        test_y = self.y + dy
        if self.can_move_grid(test_x, test_y, dungeon):
            self.target_x = test_x
            self.target_y = test_y
            self.facing = facing
            self.is_moving = True
            self.step_toggle = not self.step_toggle

    def _is_in_attack_range(self, dist_x, dist_y):
        """自身の攻撃射程内にプレイヤーがいるか判定する（十字方向のみ）"""
        if abs(dist_x) <= self.attack_range and dist_y == 0 and dist_x != 0:
            return True
        elif abs(dist_y) <= self.attack_range and dist_x == 0 and dist_y != 0:
            return True
        return False

    def _handle_attack(self, dist_x, dist_y, player, dialog=None):
        """攻撃射程内にいるプレイヤーへの攻撃（または振り向き）を処理する"""
        facing_needed = self.facing
        if dist_x > 0: facing_needed = "right"
        elif dist_x < 0: facing_needed = "left"
        elif dist_y > 0: facing_needed = "down"
        elif dist_y < 0: facing_needed = "up"
        
        # グリッド距離を計算
        grid_dist = abs(dist_x) + abs(dist_y)
        self.is_long_range = (grid_dist > 1)

        # 違う方向を向いていたら振り向くだけ
        if self.facing != facing_needed:
            self.facing = facing_needed
        else:
            # こちらを向いていたらプレイヤーへ攻撃！（まずは「溜め」から開始）
            from constants import ATTACK_PRE_DELAY_FRAMES
            self.attack_pre_delay_timer = ATTACK_PRE_DELAY_FRAMES
            self.is_attacking = True
            self.target_for_attack = player
            self.dialog_for_attack = dialog

    def _is_line_of_sight_clear(self, dist_x, dist_y, dungeon, all_entities):
        """攻撃者とプレイヤーの間に壁や他の敵がいないか確認する（遠距離攻撃用）"""
        step_x = 1 if dist_x > 0 else -1 if dist_x < 0 else 0
        step_y = 1 if dist_y > 0 else -1 if dist_y < 0 else 0
        
        my_gx = int((self.x + self.width / 2) // dungeon.tile_size)
        my_gy = int((self.y + self.height / 2) // dungeon.tile_size)
        
        grid_dist = abs(dist_x) + abs(dist_y)
        
        for i in range(1, grid_dist):
            check_gx = my_gx + step_x * i
            check_gy = my_gy + step_y * i
            
            # 壁判定
            if not (0 <= check_gx < dungeon.map_width and 0 <= check_gy < dungeon.map_height) or \
               dungeon.map_data[check_gy][check_gx] == 0:
                return False
            
            # 他のモンスター（敵）判定
            for e in all_entities:
                if e == self or getattr(e, "is_dead", False):
                    continue
                # プレイヤーは除外（ターゲットなので）
                from components.sprites.player import Player
                if isinstance(e, Player):
                    continue
                
                egx = int((e.x + e.width / 2) // dungeon.tile_size)
                egy = int((e.y + e.height / 2) // dungeon.tile_size)
                if egx == check_gx and egy == check_gy:
                    return False
        return True

    def _execute_actual_attack(self, player, dungeon, dialog):
        """溜め時間が終わった後に、突進アニメーションを開始する。ダメージ判定は突進のピーク時に行う"""
        from constants import ATTACK_ANIMATION_FRAMES, ATTACK_EFFECT_DATA
        self.is_attacking = True
        self.attack_timer = ATTACK_ANIMATION_FRAMES
        self.has_dealt_impact_damage = False
        
        # 演出データの取得
        enemy_spec = ENEMY_DATA.get(self.type, {})
        pattern_key = enemy_spec.get("ranged_attack_effect") if getattr(self, "is_long_range", False) else enemy_spec.get("close_attack_effect")
        self.current_attack_pattern = ATTACK_EFFECT_DATA.get(pattern_key, {})
        
        # 🎵 攻撃SE（発射音）の再生
        from systems.sound_handler import sound_manager
        sound_path = self.current_attack_pattern.get("launch_sound")
        if not sound_path:
            sound_path = "components/sounds/sfx/enemy_attack_common.wav"
        sound_manager.play_sfx(sound_path)

        # 1. 弾（visual）が設定されている場合は、エフェクトを発射
        visual_type = self.current_attack_pattern.get("visual")
        if visual_type:
            if visual_type == "explosion":
                # 爆発（イグニの流用）: プレイヤーの足元に直接火柱を出す
                from systems.magic_handler import FireEffect
                dungeon.magic_effects.append(FireEffect(player.x, player.y))
            else:
                # 通常の弾（ファイアボール等）
                from systems.magic_handler import ProjectileEffect
                dungeon.magic_effects.append(ProjectileEffect(
                    self.x, self.y, player.x, player.y, effect_type=visual_type, duration=ATTACK_ANIMATION_FRAMES
                ))

        # 突進距離の自動計算
        if self.current_attack_pattern.get("type") == "close":
            from constants import TILE_SIZE
            # 自分に近い方の端のマスを基準にするのではなく、中心同士の距離で計算（タイル単位）
            my_gx = int((self.x + self.width / 2) // TILE_SIZE)
            my_gy = int((self.y + self.height / 2) // TILE_SIZE)
            p_gx = int((player.x + player.width / 2) // TILE_SIZE)
            p_gy = int((player.y + player.height / 2) // TILE_SIZE)
            
            # 距離からお互いの半径（タイル数）を引く
            grid_dist = abs(p_gx - my_gx) + abs(p_gy - my_gy)
            # 半径（1タイルなら0.5、2タイルなら1.0）
            my_radius = (self.width / TILE_SIZE) / 2
            p_radius = (player.width / TILE_SIZE) / 2
            
            # 実質的な隙間タイル数
            gap = max(0, grid_dist - (my_radius + p_radius))
            self.dash_distance = (gap + 1) * TILE_SIZE # 1タイル分踏み込む
        else:
            self.dash_distance = 0

        print(f"[{self.name}] 攻撃開始！タイプ: {self.current_attack_pattern.get('type')} 突進距離: {self.dash_distance}")

    def _deal_impact_damage(self, dungeon):
        """突進がプレイヤーに当たった瞬間にダメージ判定を反映する"""
        target = getattr(self, "target_for_attack", None)
        dialog = getattr(self, "dialog_for_attack", None)
        print(f"[{self.name}] ダッシュ頂点到達！ダメージ判定処理を実行。 target: {target}")
        
        # デバッグ用：頂点に到達したら0.5秒（30フレーム）ホールドさせる
        self.peak_hold_timer = 30
        
        if not target or target.is_dead:
            return
            
        from constants import COMBAT_LOG_WAIT_FRAMES
        msg, damage, is_crit, is_miss = deal_damage(self, target)
        
        # 🎵 着弾音の再生（判定結果に基づいて鳴らす）
        from systems.sound_handler import sound_manager
        # プレイヤーと同様、ミスまたはダメージ0ならミス音
        if is_miss or damage == 0:
            sound_manager.play_sfx(SOUND_ATTACK_MISS)
        else:
            # 演出データに着弾音の設定があればそれを使う
            hit_sound = getattr(self, "current_attack_pattern", {}).get("hit_sound")
            if not hit_sound:
                from constants import SOUND_PROJECTILE_HIT
                hit_sound = SOUND_PROJECTILE_HIT
            sound_manager.play_sfx(hit_sound)

        if is_crit:
            dungeon.flash_timer = 10 # クリティカル演出

        if dialog:
            from systems.game_state import game_state
            if dialog.is_active:
                dialog.text += "\n" + msg
                dialog.auto_close_timer = COMBAT_LOG_WAIT_FRAMES
            else:
                dialog.text = msg
                dialog.is_active = True
                game_state["dialog_modal"] = False
                dialog.auto_close_timer = COMBAT_LOG_WAIT_FRAMES

    def _move_smartly_check_success(self, player, dungeon, all_entities, px_grid, py_grid, my_grid_x, my_grid_y, occupied_cells=None, ideal_dist=None):
        """プレイヤーの位置を予測し、指定された理想の間合い（ideal_dist）を目指して移動を試みる。"""
        if ideal_dist is None:
            ideal_dist = max(0, self.attack_range - 1)
            
        p_face_dx, p_face_dy = 0, 0
        if player.facing == "right": p_face_dx = 1
        elif player.facing == "left": p_face_dx = -1
        elif player.facing == "down": p_face_dy = 1
        elif player.facing == "up": p_face_dy = -1
        
        predicted_px = px_grid + p_face_dx
        predicted_py = py_grid + p_face_dy
        
        # 4方向全てのスコアを計算して、最も ideal_dist に近づくルートを探す
        directions = [
            ("right", dungeon.tile_size, 0),
            ("left", -dungeon.tile_size, 0),
            ("down", 0, dungeon.tile_size),
            ("up", 0, -dungeon.tile_size)
        ]
        
        current_grid_dist_to_pred = abs(predicted_px - my_grid_x) + abs(predicted_py - my_grid_y)
        current_score = abs(current_grid_dist_to_pred - ideal_dist)
        
        valid_moves = []
        for facing, dx, dy in directions:
            test_x = self.x + dx
            test_y = self.y + dy
            if self.can_move_grid(test_x, test_y, dungeon):
                test_grid_x = int((test_x + self.width / 2) // dungeon.tile_size)
                test_grid_y = int((test_y + self.height / 2) // dungeon.tile_size)
                
                dist_to_predicted = abs(predicted_px - test_grid_x) + abs(predicted_py - test_grid_y)
                dist_to_current = abs(px_grid - test_grid_x) + abs(py_grid - test_grid_y)
                
                # スコア計算: ideal_dist との差が小さいほど良い
                score = abs(dist_to_predicted - ideal_dist)
                
                # 今よりスコアが改善されるか、または同等なら候補に入れる
                if score <= current_score:
                    valid_moves.append({
                        "facing": facing,
                        "dx": dx,
                        "dy": dy,
                        "score": score,
                        "dist_to_current": abs(dist_to_current - self.attack_range) # 予備の評価軸
                    })
        
        if valid_moves:
            # スコアが最小（ideal_distに最も近い）の移動を選択
            valid_moves.sort(key=lambda m: (m["score"], m["dist_to_current"]))
            best_score = valid_moves[0]["score"]
            
            # 同じベストスコアが複数あればランダムに（回り込み等の自然な動きのため）
            best_moves = [m for m in valid_moves if m["score"] == best_score]
            chosen_move = random.choice(best_moves)
            
            # ただし、現在のスコアと同じで、かつ移動しなくても良い状況なら留まることもある
            # (移動したほうが predicted に対して良くなる場合のみ移動する)
            if chosen_move["score"] < current_score or random.random() < 0.5:
                self.target_x = self.x + chosen_move["dx"]
                self.target_y = self.y + chosen_move["dy"]
                self.facing = chosen_move["facing"]
                self.is_moving = True
                self.step_toggle = not self.step_toggle
                return True
                
        return False

    def take_turn(self, player, dungeon, all_entities, dialog=None, occupied_cells=None):
        """トルネコ風の厳密な1ターン（1アクション）を決定するAIロジック（スッキリリファクタ版）"""
        if getattr(self, "is_dead", False) or self.is_static:
            return
            
        my_grid_x = int((self.x + self.width / 2) // dungeon.tile_size)
        my_grid_y = int((self.y + self.height / 2) // dungeon.tile_size)
        
        px_grid = int((player.target_x + player.width / 2) // dungeon.tile_size)
        py_grid = int((player.target_y + player.height / 2) // dungeon.tile_size)
        
        dist_x = px_grid - my_grid_x
        dist_y = py_grid - my_grid_y
        
        # 1. 【索敵範囲（アグロ）】 10マス以上離れていたら気づいていない（完全に停止する）
        # プレイヤーの装備（隠密性能）による補正を適用
        aggro_mod = player.get_aggro_modifier()
        effective_radius = max(1, ENEMY_AGGRO_RADIUS + aggro_mod)
        
        # 攻撃を受けた直後の敵は、範囲に関係なくプレイヤーを追跡する（最低限の気づき保証）
        if getattr(self, "damage_flash_timer", 0) > 0:
            effective_radius = max(effective_radius, 100) 

        if abs(dist_x) > effective_radius or abs(dist_y) > effective_radius:
            # 遠距離にいる敵は一切動かない
            return
        
        # 2. 【頭の悪さ（うっかり度）】 発見していても確率でランダム行動を起こす
        # 1-10 のスケールで、設定値の確率でボケるように調整 (1/10 〜 10/10)
        if self.stupidity > 0 and random.randint(1, 10) <= self.stupidity:
            print(f"[AI] {self.name} はぼーっとしている... (Stupidity: {self.stupidity})")
            self._move_randomly(dungeon, all_entities)
            return
            
        # 3. 【インテリジェンス：間合い管理】
        # 賢い敵（stupidity < 7）の挙動調整
        if self.stupidity < 7:
            # 理想の間合いを性格から決定
            # [MOD] ranged の場合、射程2なら間合い2を保つように修正（そうしないと隣接してしまい遠距離攻撃にならないため）
            if self.attack_priority == "close":
                ideal_dist = 1
            else:
                if self.attack_range == 2:
                    ideal_dist = 2
                else:
                    ideal_dist = max(1, self.attack_range - 1)
            
            # 射線が通っているか確認
            has_los = self._is_in_attack_range(dist_x, dist_y) and self._is_line_of_sight_clear(dist_x, dist_y, dungeon, all_entities)
            grid_dist = abs(dist_x) + abs(dist_y)
            
            # --- 優先度判定 ---
            
            # A. すでに理想的な位置にいる場合
            if grid_dist == ideal_dist:
                if has_los:
                    self._handle_attack(dist_x, dist_y, player, dialog)
                    return
                # 射線が通らない（障害物越し等）なら移動を試みる
                if self._move_smartly_check_success(player, dungeon, all_entities, px_grid, py_grid, my_grid_x, my_grid_y, occupied_cells, ideal_dist):
                    return
            
            # B. 隣接（距離1）されている場合（アウトボクサーは逃げたい）
            elif grid_dist == 1 and self.attack_priority == "ranged" and self.attack_range > 1:
                # 70% の確率で距離を取ろうとする
                if random.random() < 0.7:
                    if self._move_smartly_check_success(player, dungeon, all_entities, px_grid, py_grid, my_grid_x, my_grid_y, occupied_cells, ideal_dist):
                        return
                # 逃げない、または逃げられなかった場合は攻撃
                self._handle_attack(dist_x, dist_y, player, dialog)
                return

            # C. それ以外（理想の間合いではないが、攻撃または移動が必要な場合）
            else:
                # 攻撃可能（射程内かつ射線が通っている）なら、移動よりも攻撃を優先する
                if has_los:
                    self._handle_attack(dist_x, dist_y, player, dialog)
                    return
                
                # 攻撃できない場合は理想の間合いへ向けて移動する
                if self._move_smartly_check_success(player, dungeon, all_entities, px_grid, py_grid, my_grid_x, my_grid_y, occupied_cells, ideal_dist):
                    return
                
    def update(self, dungeon):
        """毎フレームの更新（アニメーションの進行など）"""
        if self.is_static:
            self.update_animation()
            return
            
        # 攻撃前の溜め期間中
        if self.attack_pre_delay_timer > 0:
            self.attack_pre_delay_timer -= 1
            if self.attack_pre_delay_timer == 0:
                # 溜めが終わったら、突進アニメーションを開始！
                target = getattr(self, "target_for_attack", None)
                dialog = getattr(self, "dialog_for_attack", None)
                if target and not target.is_dead:
                    self._execute_actual_attack(target, dungeon, dialog)
                else:
                    self.is_attacking = False
                    
        # 突進のピーク時（衝突）のダメージ処理
        if self.is_attacking and self.attack_pre_delay_timer == 0:
            from constants import ATTACK_ANIMATION_FRAMES
            # 全体20フレーム。0.2時点（到達の瞬間）がダメージ判定
            impact_frame = int(ATTACK_ANIMATION_FRAMES * 0.8)
            if getattr(self, "attack_timer", 0) <= impact_frame and not getattr(self, "has_dealt_impact_damage", False):
                self._deal_impact_damage(dungeon)
                self.has_dealt_impact_damage = True
                
        self.update_animation()
        
    def update_animation(self):
        # 溜め期間中・およびダッシュ頂点での停止処理中は、通常の歩行アニメーションを行わない
        if getattr(self, "attack_pre_delay_timer", 0) > 0 or getattr(self, "peak_hold_timer", 0) > 0:
            # 基底クラスの更新（ダメージタイマー、移動処理）のみ行う
            super().update_animation()
            if not self.is_moving:
                self.move_speed = 4
            return
            
        # 通常の更新（この中で process_movement も呼ばれる）
        super().update_animation()
        
        # 移動が終わっていたら速度をリセット（念のためのガード）
        if not self.is_moving:
            self.move_speed = 4
                
    @classmethod
    def spawn_enemies(cls, dungeon, player=None):
        """ダンジョン生成時に、障害物とモンスターをそれぞれ独立した設定数で配置します。"""
        from constants import (
            ENEMY_SPAWN_MIN, ENEMY_SPAWN_MAX, ENEMY_SPAWN_ATTEMPTS, 
            ENEMY_SPAWN_SAFE_RADIUS, ENEMY_SPAWN_SCATTER, ENEMY_DATA,
            ENEMY_TOTAL_MAX, ENEMY_TOTAL_SCALE_EVERY, ENEMY_TOTAL_SCALE_ADD,
            OBSTACLE_SPAWN_MIN, OBSTACLE_SPAWN_MAX, OBSTACLE_SPAWN_SCALE_EVERY,
            OBSTACLE_SPAWN_SCALE_ADD, OBSTACLE_SPAWN_LIMIT,
            OBSTACLE_TOTAL_MAX, OBSTACLE_TOTAL_SCALE_EVERY, OBSTACLE_TOTAL_SCALE_ADD
        )
        enemies = []
        floor = getattr(dungeon, "current_floor", 1)
        player_gx = int(player.x // dungeon.tile_size) if player else -999
        player_gy = int(player.y // dungeon.tile_size) if player else -999
        safe_radius = ENEMY_SPAWN_SAFE_RADIUS
        
        # データの分類
        monster_types = [k for k, v in ENEMY_DATA.items() if not v.get("is_static", False)]
        obstacle_types = [k for k, v in ENEMY_DATA.items() if v.get("is_static", False)]

        # スケーリング計算
        eff_floor = min(floor, OBSTACLE_SPAWN_LIMIT)
        num_rooms = len(dungeon.rooms)
        
        m_spawn_bonus = (floor - 1) // ENEMY_TOTAL_SCALE_EVERY * ENEMY_TOTAL_SCALE_ADD # モンスター用
        m_total_cap   = int(num_rooms * ENEMY_TOTAL_MAX) + m_spawn_bonus # [MOD] 小数点以下切り捨て
        
        o_spawn_bonus = (eff_floor - 1) // OBSTACLE_SPAWN_SCALE_EVERY * OBSTACLE_SPAWN_SCALE_ADD
        o_total_bonus = (eff_floor - 1) // OBSTACLE_TOTAL_SCALE_EVERY * OBSTACLE_TOTAL_SCALE_ADD
        o_total_cap   = int(num_rooms * OBSTACLE_TOTAL_MAX) + o_total_bonus # [MOD] 小数点以下切り捨て

        # 全ての部屋を対象にスポーン処理を行う
        for idx, room in enumerate(dungeon.rooms):
            # 10%の確率でその部屋のスポーンを完全にスキップ（密集しすぎ防止）
            if random.random() < 0.1: continue

            # --- フェーズ1: モンスターの配置（最優先） ---
            is_stair_room = (idx == getattr(dungeon, "start_room_idx", -1) or idx == getattr(dungeon, "target_room_idx", -1))
            s_min, s_max = ENEMY_SPAWN_MIN, ENEMY_SPAWN_MAX
            if is_stair_room:
                s_min, s_max = s_min // 2, max(1, s_max // 2)
            
            num_monsters = random.randint(s_min, s_max)
            for _ in range(num_monsters):
                # モンスターの全体上限チェック
                if sum(1 for e in enemies if not e.is_static) >= m_total_cap: break
                
                for attempt in range(ENEMY_SPAWN_ATTEMPTS * 2): # 試行回数を2倍に
                    ex = random.randint(room[0] - ENEMY_SPAWN_SCATTER, room[0] + ENEMY_SPAWN_SCATTER)
                    ey = random.randint(room[1] - ENEMY_SPAWN_SCATTER, room[1] + ENEMY_SPAWN_SCATTER)
                    
                    if abs(ex - player_gx) <= safe_radius and abs(ey - player_gy) <= safe_radius: continue
                    
                    if 0 <= ey < dungeon.map_height and 0 <= ex < dungeon.map_width:
                        if dungeon.map_data[ey][ex] == 1:
                            if not any((ex, ey) in e.get_occupied_grids(dungeon.tile_size) for e in enemies):
                                valid_m = [m for m in monster_types if ENEMY_DATA[m].get("min_floor", 1) <= floor <= ENEMY_DATA[m].get("max_floor", 999)]
                                if valid_m:
                                    m_type = random.choice(valid_m)
                                    new_m = Enemy(ex * dungeon.tile_size, ey * dungeon.tile_size, m_type, player=player)
                                    new_m.x += (dungeon.tile_size - new_m.width) // 2
                                    new_m.y += (dungeon.tile_size - new_m.height) // 2
                                    new_m.target_x, new_m.target_y = new_m.x, new_m.y
                                    enemies.append(new_m)
                                    dungeon.spawn_counts[m_type] = dungeon.spawn_counts.get(m_type, 0) + 1
                                    break

            # --- フェーズ2: 障害物の配置（空きスペースへ） ---
            num_obs = random.randint(OBSTACLE_SPAWN_MIN, OBSTACLE_SPAWN_MAX + o_spawn_bonus)
            for _ in range(num_obs):
                # 障害物の全体上限チェック
                if sum(1 for e in enemies if e.is_static) >= o_total_cap: break

                for attempt in range(ENEMY_SPAWN_ATTEMPTS):
                    ex = random.randint(room[0] - ENEMY_SPAWN_SCATTER, room[0] + ENEMY_SPAWN_SCATTER)
                    ey = random.randint(room[1] - ENEMY_SPAWN_SCATTER, room[1] + ENEMY_SPAWN_SCATTER)
                    if 0 <= ey < dungeon.map_height and 0 <= ex < dungeon.map_width:
                        if dungeon.map_data[ey][ex] == 1:
                            if not any(int((e.x + e.width/2)//dungeon.tile_size) == ex and 
                                       int((e.y + e.height/2)//dungeon.tile_size) == ey for e in enemies):
                                valid_o = [o for o in obstacle_types if ENEMY_DATA[o].get("min_floor", 1) <= floor <= ENEMY_DATA[o].get("max_floor", 999)]
                                if valid_o:
                                    o_type = random.choice(valid_o)
                                    new_obs = Enemy(ex * dungeon.tile_size, ey * dungeon.tile_size, o_type, player=player)
                                    new_obs.x += (dungeon.tile_size - new_obs.width) // 2
                                    new_obs.y += (dungeon.tile_size - new_obs.height) // 2
                                    new_obs.target_x, new_obs.target_y = new_obs.x, new_obs.y
                                    enemies.append(new_obs)
                                break
        cls.log_population(dungeon, "Warped", override_enemies=enemies)
        return enemies

    @classmethod
    def log_population(cls, dungeon, reason, override_enemies=None):
        """現在のフロア内のモンスターと障害物の数を集計してログ出力する"""
        from constants import (
            ENEMY_TOTAL_MAX, ENEMY_TOTAL_SCALE_EVERY, ENEMY_TOTAL_SCALE_ADD,
            OBSTACLE_TOTAL_MAX, OBSTACLE_TOTAL_SCALE_EVERY, OBSTACLE_TOTAL_SCALE_ADD,
            OBSTACLE_SPAWN_LIMIT
        )
        floor = getattr(dungeon, "current_floor", 1)
        rooms = getattr(dungeon, "rooms", [])
        num_rooms = len(rooms)
        
        # 上限計算 (モンスターも障害物も部屋数倍率を適用)
        eff_floor = min(floor, OBSTACLE_SPAWN_LIMIT)
        m_total_cap = int(num_rooms * ENEMY_TOTAL_MAX) + (floor - 1) // ENEMY_TOTAL_SCALE_EVERY * ENEMY_TOTAL_SCALE_ADD
        o_total_cap = int(num_rooms * OBSTACLE_TOTAL_MAX) + (eff_floor - 1) // OBSTACLE_TOTAL_SCALE_EVERY * OBSTACLE_TOTAL_SCALE_ADD
        
        # 現在数カウント
        target_list = override_enemies if override_enemies is not None else getattr(dungeon, "enemies", [])
        curr_m = sum(1 for e in target_list if not getattr(e, "is_static", False))
        curr_o = sum(1 for e in target_list if getattr(e, "is_static", False))
        
        print(f"[POPULATION] Floor {floor} | Rooms: {num_rooms} | Monsters: {curr_m}/{m_total_cap} | Obstacles: {curr_o}/{o_total_cap} | Reason: {reason}")

    @classmethod
    def spawn_one(cls, dungeon, player):
        """
        【時間リスポーン】全体上限に達していなければ、ランダムな部屋に1体だけ追加スポーンする。
        main.py 側でタイマーを管理し、一定時間ごとにこのメソッドを呼び出す。
        """
        from constants import ENEMY_TOTAL_MAX, ENEMY_TOTAL_SCALE_EVERY, ENEMY_TOTAL_SCALE_ADD
        floor       = getattr(dungeon, "current_floor", 1)
        total_bonus = (floor - 1) // ENEMY_TOTAL_SCALE_EVERY * ENEMY_TOTAL_SCALE_ADD
        # 上限計算（リスポーン時も部屋数倍率を適用）
        num_rooms = len(dungeon.rooms)
        m_total_cap = int(num_rooms * ENEMY_TOTAL_MAX) + total_bonus

        # すでにモンスターの上限に達していたら何もしない
        current_monster_count = sum(1 for e in dungeon.enemies if not e.is_static)
        if current_monster_count >= m_total_cap:
            return

        # スタート部屋以外のランダムな部屋に1体スポーンを試みる（最大20回）
        player_gx = int(player.x // dungeon.tile_size)
        player_gy = int(player.y // dungeon.tile_size)
        rooms = dungeon.rooms[1:]
        if not rooms:
            return  # ほかに部屋がない場合はスポーンしない

        for _ in range(20):
            room = random.choice(rooms)
            ex = random.randint(room[0] - ENEMY_SPAWN_SCATTER, room[0] + ENEMY_SPAWN_SCATTER)
            ey = random.randint(room[1] - ENEMY_SPAWN_SCATTER, room[1] + ENEMY_SPAWN_SCATTER)
            if abs(ex - player_gx) <= ENEMY_SPAWN_SAFE_RADIUS and abs(ey - player_gy) <= ENEMY_SPAWN_SAFE_RADIUS:
                continue
            if 0 <= ey < dungeon.map_height and 0 <= ex < dungeon.map_width:
                t = dungeon.map_data[ey][ex]
                if (1 <= t <= 3 or 10 <= t <= 14):
                    # 【追加】すでに何かがいるマスは避ける
                    all_entities = [player] + dungeon.enemies + dungeon.npcs
                    if any((ex, ey) in e.get_occupied_grids(dungeon.tile_size) for e in all_entities):
                        continue

                    # 制限を満たす敵だけを抽出
                    current_counts = {}
                    for e in dungeon.enemies:
                        current_counts[e.type] = current_counts.get(e.type, 0) + 1
                        
                    valid_enemies = []
                    for e_type, e_data in ENEMY_DATA.items():
                        if e_data.get("is_static"): # [NEW] 障害物はリスポーンさせない
                            continue
                        if not (e_data.get("min_floor", 1) <= floor <= e_data.get("max_floor", 999)):
                            continue
                        if dungeon.spawn_counts.get(e_type, 0) >= e_data.get("max_spawns", 999):
                            continue
                        if current_counts.get(e_type, 0) >= e_data.get("max_concurrent", 999):
                            continue
                        valid_enemies.append(e_type)

                    if valid_enemies:
                        enemy_type = random.choice(valid_enemies)
                        new_enemy = Enemy(0, 0, enemy_type, player=player)
                        new_enemy.x = ex * dungeon.tile_size + (dungeon.tile_size - new_enemy.width) // 2
                        new_enemy.y = ey * dungeon.tile_size + (dungeon.tile_size - new_enemy.height) // 2
                        new_enemy.target_x = new_enemy.x
                        new_enemy.target_y = new_enemy.y
                        dungeon.enemies.append(new_enemy)
                        dungeon.spawn_counts[enemy_type] = dungeon.spawn_counts.get(enemy_type, 0) + 1
                    return  # 1体スポーン試行したら完了！
