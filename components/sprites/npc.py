import pygame, os
from components.sprites.entity import Entity
from wordings import Text

class NPC(Entity):
    _npc_scaled_cache = {} # {(img_obj, phase): surface}
    _anim_dir_cache = {} # {(path, width, height): img_dict} — パスベースの画像ロードキャッシュ

    @classmethod
    def clear_cache(cls):
        """蓄積されたNPC画像キャッシュをクリアする"""
        count = len(cls._npc_scaled_cache)
        cls._npc_scaled_cache = {}
        cls._anim_dir_cache = {}
        if count > 0:
            print(f"[MEMORY] NPC scaled image cache cleared ({count} items)")

    def __init__(self, name, x, y, sprite_type="villager", dialogue=[], image_path=None, base_image_path=None, role=None, flip=False, alpha=None):
        # NPCもEntityを継承して移動や描画の基本機能を持たせる
        # とりあえず固定位置にいるので move_speed=0
        super().__init__(x=x, y=y, hp=100, max_hp=100, attack=0, width=64, height=64)
        self.name = name
        self.sprite_type = sprite_type
        self.dialogue = dialogue
        self.move_speed = 0
        self.role = role
        self.flip = flip
        self.alpha = alpha
        
        # 背景画像（足元の床など）の読み込み
        self.base_image = None
        if base_image_path and os.path.exists(base_image_path):
            base_cache_key = (base_image_path, self.width, self.height)
            if base_cache_key in NPC._anim_dir_cache:
                self.base_image = NPC._anim_dir_cache[base_cache_key].get("idle")
            else:
                try:
                    raw_base = pygame.image.load(base_image_path).convert_alpha()
                    scaled = pygame.transform.scale(raw_base, (self.width, self.height))
                    NPC._anim_dir_cache[base_cache_key] = {"idle": scaled}
                    self.base_image = scaled
                except Exception as e:
                    print(f"[NPC] Failed to load base image {base_image_path}: {e}")

        # [NEW] 画像の読み込み（アニメーション対応：idle, 0, 1 構成）
        self._image_dicts_by_rank = {}
        
        def load_anim_dir(path):
            if not path or not isinstance(path, str):
                return {}
            cache_key = (path, self.width, self.height)
            if cache_key in NPC._anim_dir_cache:
                return NPC._anim_dir_cache[cache_key]
            img_dict = {}
            if os.path.isdir(path):
                try:
                    for key in ["idle", "0", "1"]:
                        fname = f"{key}.png"
                        full_path = os.path.join(path, fname)
                        if os.path.exists(full_path):
                            raw = pygame.image.load(full_path).convert_alpha()
                            img_dict[key] = pygame.transform.scale(raw, (self.width, self.height))
                    if "idle" not in img_dict:
                        path01 = os.path.join(path, "01.png")
                        if os.path.exists(path01):
                            raw = pygame.image.load(path01).convert_alpha()
                            img_dict["idle"] = pygame.transform.scale(raw, (self.width, self.height))
                except Exception as e:
                    print(f"[NPC] Failed to load animation from {path}: {e}")
            elif os.path.isfile(path):
                try:
                    raw = pygame.image.load(path).convert_alpha()
                    img_dict["idle"] = pygame.transform.scale(raw, (self.width, self.height))
                except Exception as e:
                    print(f"[NPC] Failed to load image from {path}: {e}")
            NPC._anim_dir_cache[cache_key] = img_dict
            return img_dict

        if isinstance(image_path, dict):
            for rank, path in image_path.items():
                self._image_dicts_by_rank[rank] = load_anim_dir(path)
        else:
            self._image_dicts_by_rank["default"] = load_anim_dir(image_path)

        # 仮の見た目設定（画像がない場合のフォールバック）
        self.color = (50, 200, 100) # デフォルトは緑っぽい
        if "武器屋" in name: self.color = (200, 50, 50) # 赤
        elif "道具屋" in name: self.color = (50, 50, 200) # 青
        
    def get_dialogue(self, player=None):
        rank = player.guild_rank if player else None
        if isinstance(self.dialogue, dict):
            if rank and rank in self.dialogue:
                return self.dialogue[rank]
            elif "default" in self.dialogue:
                return self.dialogue["default"]
            else:
                return list(self.dialogue.values())[0]
        return self.dialogue if self.dialogue else [Text.NPC.GENERIC_FALLBACK.format(name=self.name)]


    def draw(self, screen, camera_x, camera_y, player=None):
        draw_x = self.x - camera_x
        draw_y = self.y - camera_y
        
        # 1. 背景（足元）の描画
        if self.base_image:
            screen.blit(self.base_image, (draw_x, draw_y))

        # 2. アニメーションフレームの決定 (idle -> 0 -> idle -> 1 の 4段階サイクル)
        rank = player.guild_rank if player else None
        current_image_dict = {}
        if rank and rank in self._image_dicts_by_rank:
            current_image_dict = self._image_dicts_by_rank[rank]
        elif "default" in self._image_dicts_by_rank:
            current_image_dict = self._image_dicts_by_rank["default"]
        elif self._image_dicts_by_rank:
            current_image_dict = list(self._image_dicts_by_rank.values())[0]

        img = None
        if "idle" in current_image_dict and "0" in current_image_dict and "1" in current_image_dict:
            # 60フレーム周期を4分割 (15フレームごと)
            step = (self.idle_anim_timer // 15) % 4
            anim_key = ["idle", "0", "idle", "1"][step]
            img = current_image_dict.get(anim_key)
        elif current_image_dict:
            # idle があれば優先、なければ適当なものを表示
            img = current_image_dict.get("idle") or list(current_image_dict.values())[0]

        if not img:
            # 簡易的な描画（画像がない場合のフォールバック）
            img = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            pygame.draw.rect(img, (0, 0, 0), (0, 0, self.width, self.height))
            pygame.draw.rect(img, self.color, (4, 4, self.width - 8, self.height - 8))

        # 3. 呼吸（スケーリング）の計算（共通メソッドを使用）
        (scale_x, scale_y), phase = self.get_breathing_scale()
        
        # 4. 透過度（アルファ値）の計算
        alpha_val = 255
        if self.alpha is not None:
            if isinstance(self.alpha, dict):
                if rank and rank in self.alpha:
                    alpha_val = self.alpha[rank]
                elif "default" in self.alpha:
                    alpha_val = self.alpha["default"]
                elif self.alpha:
                    alpha_val = list(self.alpha.values())[0]
            else:
                alpha_val = self.alpha
        
        # --- [OPTIMIZED] NPCのスケーリングキャッシュ利用 ---
        cache_key = (img, phase, self.flip, alpha_val)
        cached_img = NPC._npc_scaled_cache.get(cache_key)
        
        if cached_img is None:
            w, h = img.get_size()
            scaled_img = pygame.transform.smoothscale(img, (int(w * scale_x), int(h * scale_y)))
            if self.flip:
                scaled_img = pygame.transform.flip(scaled_img, True, False)
            if alpha_val != 255:
                scaled_img = scaled_img.copy()
                scaled_img.set_alpha(alpha_val)
            cached_img = scaled_img
            NPC._npc_scaled_cache[cache_key] = cached_img
            
        img = cached_img
        
        # 足元を基準に位置を調整（浮かないようにする）
        draw_x_scaled = draw_x + (self.width - img.get_width()) / 2
        draw_y_scaled = draw_y + (self.height - img.get_height()) 

        screen.blit(img, (draw_x_scaled, draw_y_scaled))
        
