"""
weapon.py — 武器クラスの定義
各武器は「どのグリッドマスを攻撃するか」を get_hit_grids() で返す。
攻撃アニメーションも draw_attack() で武器ごとに定義する。
プレイヤーは self.weapon を差し替えるだけで武器チェンジできる！
"""
import math
import pygame
from constants import (
    ATTACK_STRIKE_DURATION, ATTACK_ANIMATION_FRAMES,
    WEAPON_DATA, WEAPON_TYPES
)


def get_weapon_instance(weapon_name, enhance=0):
    """武器名から適切な武器クラスをインスタンス化して返す"""
    data = WEAPON_DATA.get(weapon_name)
    if not data: return None
    
    # 循環参照を避けるためにメソッド内でインポート
    from components.sprites.weapon import OneHanded, Spear
    type_map = {"OneHanded": OneHanded, "Spear": Spear}
    weapon_type = data.get("type", "OneHanded")
    cls = type_map.get(weapon_type, OneHanded)
    
    weapon_inst = cls(data, weapon_name)
    weapon_inst.attack_bonus += enhance 
    return weapon_inst


class Weapon:
    """武器の基底クラス"""
    name    = "素手"
    pierce  = False  # 複数の敵を貫通するか（True=貫通、False=最初の1体で止まる）

    def __init__(self, data=None, key=""):
        self.data = data or {}
        self.key = key
        self.name = self.data.get("name", "素手")
        self.attack_bonus = self.data.get("attack_bonus", 0)
        self.image_scale = self.data.get("image_scale", 1.0)
        
        # 武器種 (Sword, Bow等) に基づく共通設定の取得
        weapon_type = self.data.get("type", "OneHanded")
        type_config = WEAPON_TYPES.get(weapon_type, {})

        pos_config = self.data.get("position", {})
        # デフォルト値 (旧 OneHanded 相当)
        def_hand = {
            "down": [[-19, -9], [-8, 31]],
            "left": [[-22, -2], [-28, 24]],
            "right": [[-7, -4], [25, 24]],
            "up": [[17, -4], [36, 13]]
        }
        def_angle = {"down": [0, 210], "left": [-343, 106], "right": [26, -111], "up": [0, -81]}
        def_over = {"down": True, "left": False, "right": True, "up": False}

        self.HAND_OFFSETS     = pos_config.get("hand_offsets", self.data.get("hand_offsets", type_config.get("hand_offsets", def_hand)))
        self.WEAPON_ANGLES    = pos_config.get("weapon_angles", self.data.get("weapon_angles", type_config.get("weapon_angles", def_angle)))
        self.DRAW_OVER_PLAYER = pos_config.get("draw_over_player", self.data.get("draw_over_player", type_config.get("draw_over_player", def_over)))

        # [NEW] キャッシュ
        self._weapon_cache = {} # {(angle, sx, sy): surface}

        # 画像の読み込み
        img_path = self.data.get("image_path")
        try:
            raw_img = pygame.image.load(img_path).convert_alpha() if img_path else None
            # 倍率が 1.0 以外ならスケーリング
            if raw_img and self.image_scale != 1.0:
                new_w = int(raw_img.get_width() * self.image_scale)
                new_h = int(raw_img.get_height() * self.image_scale)
                self.image = pygame.transform.scale(raw_img, (new_w, new_h))
            else:
                self.image = raw_img
        except:
            self.image = None

    def get_hit_grids(self, facing, gx, gy, dungeon=None):
        """攻撃が当たるグリッド座標のリストを返す"""
        raise NotImplementedError

    def draw_attack(self, screen, center_x, center_y, facing, progress, scale_x=1.0, scale_y=1.0):
        """攻撃アニメーションを描画する（子クラスでオーバーライド）"""
        pass

    def draw_idle(self, screen, center_x, center_y, facing, scale_x=1.0, scale_y=1.0):
        """待機時の描画（子クラスでオーバーライド）"""
        pass


class OneHanded(Weapon):
    """
    剣 — 正面1マス ＋ その上下 合計3マスを同時にヒット（扇形）
    アニメーション：大きく弧を描いてスイングする！
    """
    pierce = True
    color  = (200, 200, 200)

    def __init__(self, data=None, key=""):
        super().__init__(data, key)
        # 剣固有の初期化があればここに。基本は基底クラスにお任せ

    def get_hit_grids(self, facing, gx, gy, dungeon=None):
        if facing == "right": return [(gx+1, gy)]
        elif facing == "left": return [(gx-1, gy)]
        elif facing == "down": return [(gx, gy+1)]
        elif facing == "up": return [(gx, gy-1)]
        return []

    def draw_attack(self, screen, center_x, center_y, facing, progress, scale_x=1.0, scale_y=1.0, alpha=255):
        """画像を使って武器を描画する"""
        idx = 1
        
        if self.image:
            # 1. 角度を決定
            angle = self.WEAPON_ANGLES.get(facing, [0, 0])[idx]
            
            # --- [OPTIMIZED] 武器のキャッシュ利用 ---
            cache_key = (angle, scale_x, scale_y)
            cached_img = self._weapon_cache.get(cache_key)
            
            if cached_img is None:
                w_img = self.image
                # スケール
                if scale_x != 1.0 or scale_y != 1.0:
                    w, h = w_img.get_size()
                    w_img = pygame.transform.scale(w_img, (int(w * scale_x), int(h * scale_y)))
                # 回転
                cached_img = pygame.transform.rotate(w_img, angle)
                self._weapon_cache[cache_key] = cached_img
            
            rotated_sword = cached_img
            if alpha < 255:
                rotated_sword.set_alpha(alpha)
            
            # 3. 手の位置（中心基準のオフセット）から描画座標を計算
            offset = self.HAND_OFFSETS.get(facing, [(0, 0), (0, 0)])[idx]
            # スケール分、オフセットも拡大
            off_x, off_y = offset[0] * scale_x, offset[1] * scale_y
            
            draw_x = center_x + off_x - rotated_sword.get_width() // 2
            draw_y = center_y + off_y - rotated_sword.get_height() // 2
            
            screen.blit(rotated_sword, (draw_x, draw_y))
        else:
            # フォールバック：以前の線描画
            is_tame = (idx == 0)
            if facing == "right": angle_deg = -45 if is_tame else 45
            elif facing == "left": angle_deg = 225 if is_tame else 135
            elif facing == "up": angle_deg = -135 if is_tame else -45
            elif facing == "down": angle_deg = 135 if is_tame else 45
            else: return

            rad = math.radians(angle_deg)
            length = 65
            width = 12
            end_x = center_x + math.cos(rad) * length
            end_y = center_y + math.sin(rad) * length
            pygame.draw.line(screen, self.color, (center_x, center_y), (end_x, end_y), width)

    def draw_idle(self, screen, center_x, center_y, facing, scale_x=1.0, scale_y=1.0, alpha=255):
        """待機・歩行時の描画（中心基準のオフセット）"""
        if self.image:
            angle = self.WEAPON_ANGLES.get(facing, [0, 0])[0]
            
            # --- [OPTIMIZED] 武器のキャッシュ利用 ---
            cache_key = (angle, scale_x, scale_y)
            cached_img = self._weapon_cache.get(cache_key)
            
            if cached_img is None:
                w_img = self.image
                if scale_x != 1.0 or scale_y != 1.0:
                    w, h = w_img.get_size()
                    w_img = pygame.transform.scale(w_img, (int(w * scale_x), int(h * scale_y)))
                cached_img = pygame.transform.rotate(w_img, angle)
                self._weapon_cache[cache_key] = cached_img
                
            rotated = cached_img
            if alpha < 255:
                rotated.set_alpha(alpha)
            offset = self.HAND_OFFSETS.get(facing, [(0, 0), (0, 0)])[0]
            # スケール分、オフセットも拡大
            off_x, off_y = offset[0] * scale_x, offset[1] * scale_y

            draw_x = center_x + off_x - rotated.get_width() // 2
            draw_y = center_y + off_y - rotated.get_height() // 2
            screen.blit(rotated, (draw_x, draw_y))
        else:
            # フォールバック
            pass


class Spear(Weapon):
    """
    槍 — 正面方向に2マス先まで直線攻撃
    アニメーション：前方へ突き刺すような直線！

    例：右向きの場合
      ★ ← (1, 0)
      ★ ← (2, 0)
    """
    name   = "槍"
    pierce = False
    length = 80   # 剣より長い
    width  = 8
    color  = (180, 140, 80)   # 木の柄っぽい茶色

    def get_hit_grids(self, facing, gx, gy, dungeon=None):
        if facing == "right":  return [(gx+1, gy), (gx+2, gy)]
        elif facing == "left": return [(gx-1, gy), (gx-2, gy)]
        elif facing == "down": return [(gx, gy+1), (gx, gy+2)]
        elif facing == "up":   return [(gx, gy-1), (gx, gy-2)]
        return []

    def draw_attack(self, screen, center_x, center_y, facing, progress, scale_x=1.0, scale_y=1.0):
        """前方へ突き出す槍アニメーション（progress 0→1 で伸びて戻る）"""
        # 前半(0〜0.5)で伸び、後半(0.5〜1)で引き戻す
        scale = 1.0 - abs(progress - 0.5) * 2  # 0→1→0の山型
        current_len = self.length * (0.3 + scale * 0.7)    # 最低30%の長さから伸びる

        dx, dy = 0, 0
        if facing == "right": dx = 1
        elif facing == "left": dx = -1
        elif facing == "down": dy = 1
        elif facing == "up":   dy = -1

        end_x = center_x + dx * current_len
        end_y = center_y + dy * current_len
        pygame.draw.line(screen, self.color, (center_x, center_y), (end_x, end_y), self.width)
        # 穂先（先端）を少し明るく描く
        tip_x = center_x + dx * current_len
        tip_y = center_y + dy * current_len
        pygame.draw.circle(screen, (220, 220, 240), (int(tip_x), int(tip_y)), 5)

    def draw_idle(self, screen, center_x, center_y, facing, scale_x=1.0, scale_y=1.0):
        # 短い状態で描画
        self.draw_attack(screen, center_x, center_y, facing, 0, scale_x, scale_y)

