import pygame, os
from components.sprites.entity import Entity
from wordings import Text

class NPC(Entity):
    _npc_scaled_cache = {} # {(img_obj, phase): surface}

    @classmethod
    def clear_cache(cls):
        """蓄積されたNPC画像キャッシュをクリアする"""
        count = len(cls._npc_scaled_cache)
        cls._npc_scaled_cache = {}
        if count > 0:
            print(f"[MEMORY] NPC scaled image cache cleared ({count} items)")

    def __init__(self, name, x, y, sprite_type="villager", dialogue=[], image_path=None, base_image_path=None, role=None, flip=False):
        # NPCもEntityを継承して移動や描画の基本機能を持たせる
        # とりあえず固定位置にいるので move_speed=0
        super().__init__(x=x, y=y, hp=100, max_hp=100, attack=0, width=64, height=64)
        self.name = name
        self.sprite_type = sprite_type
        self.dialogue = dialogue
        self.move_speed = 0
        self.role = role
        self.flip = flip
        
        # 背景画像（足元の床など）の読み込み
        self.base_image = None
        if base_image_path and os.path.exists(base_image_path):
            try:
                raw_base = pygame.image.load(base_image_path).convert_alpha()
                self.base_image = pygame.transform.scale(raw_base, (self.width, self.height))
            except Exception as e:
                print(f"[NPC] Failed to load base image {base_image_path}: {e}")

        # [NEW] 画像の読み込み（アニメーション対応：idel, 0, 1 構成）
        self._image_dict = {}
        if image_path:
            if os.path.isdir(image_path):
                try:
                    # idel.png, 0.png, 1.png を探す
                    for key in ["idel", "0", "1"]:
                        fname = f"{key}.png"
                        full_path = os.path.join(image_path, fname)
                        if os.path.exists(full_path):
                            raw = pygame.image.load(full_path).convert_alpha()
                            scaled = pygame.transform.scale(raw, (self.width, self.height))
                            self._image_dict[key] = scaled
                    
                    # 互換性維持：01.png がある場合
                    if "idel" not in self._image_dict:
                        path01 = os.path.join(image_path, "01.png")
                        if os.path.exists(path01):
                            raw = pygame.image.load(path01).convert_alpha()
                            self._image_dict["idel"] = pygame.transform.scale(raw, (self.width, self.height))
                except Exception as e:
                    print(f"[NPC] Failed to load animation from {image_path}: {e}")

        # 仮の見た目設定（画像がない場合のフォールバック）
        self.color = (50, 200, 100) # デフォルトは緑っぽい
        if "武器屋" in name: self.color = (200, 50, 50) # 赤
        elif "道具屋" in name: self.color = (50, 50, 200) # 青
        
    def get_dialogue(self):
        return self.dialogue if self.dialogue else [Text.NPC.GENERIC_FALLBACK.format(name=self.name)]


    def draw(self, screen, camera_x, camera_y):
        draw_x = self.x - camera_x
        draw_y = self.y - camera_y
        
        # 1. 背景（足元）の描画
        if self.base_image:
            screen.blit(self.base_image, (draw_x, draw_y))

        # 2. アニメーションフレームの決定 (idel -> 0 -> idel -> 1 の 4段階サイクル)
        img = None
        if "idel" in self._image_dict and "0" in self._image_dict and "1" in self._image_dict:
            # 60フレーム周期を4分割 (15フレームごと)
            step = (self.idle_anim_timer // 15) % 4
            anim_key = ["idel", "0", "idel", "1"][step]
            img = self._image_dict.get(anim_key)
        elif self._image_dict:
            # idel があれば優先、なければ適当なものを表示
            img = self._image_dict.get("idel") or list(self._image_dict.values())[0]

        if not img:
            # 簡易的な描画（画像がない場合のフォールバック）
            img = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            pygame.draw.rect(img, (0, 0, 0), (0, 0, self.width, self.height))
            pygame.draw.rect(img, self.color, (4, 4, self.width - 8, self.height - 8))

        # 3. 呼吸（スケーリング）の計算（共通メソッドを使用）
        (scale_x, scale_y), phase = self.get_breathing_scale()
        
        # --- [OPTIMIZED] NPCのスケーリングキャッシュ利用 ---
        cache_key = (img, phase, self.flip)
        cached_img = NPC._npc_scaled_cache.get(cache_key)
        
        if cached_img is None:
            w, h = img.get_size()
            scaled_img = pygame.transform.smoothscale(img, (int(w * scale_x), int(h * scale_y)))
            if self.flip:
                scaled_img = pygame.transform.flip(scaled_img, True, False)
            cached_img = scaled_img
            NPC._npc_scaled_cache[cache_key] = cached_img
            NPC._npc_scaled_cache[cache_key] = cached_img
            
        img = cached_img
        
        # 足元を基準に位置を調整（浮かないようにする）
        draw_x_scaled = draw_x + (self.width - img.get_width()) / 2
        draw_y_scaled = draw_y + (self.height - img.get_height()) 

        screen.blit(img, (draw_x_scaled, draw_y_scaled))
        
        # 名前ラベル（共通フォントを使用）
        from systems.resources import font_small
        text = font_small.render(self.name, True, (255, 255, 255))
        screen.blit(text, (draw_x + (self.width - text.get_width())//2, draw_y - 25))

