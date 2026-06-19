import pygame
import random

class Item:
    def __init__(self, x, y, name, sprite_type="item"):
        self.x = x
        self.y = y
        self.name = name
        self.sprite_type = sprite_type
        self.width = 30
        self.height = 30
        self.is_collected = False
        self._image = None

    def _load_item_image(self, data):
        """[NEW] アイテムデータを元に画像を読み込み、アスペクト比を維持して最大50pxにリサイズする"""
        import os
        img_dir = data.get("image_dir")
        img_path = data.get("image_path")
        path = None
        
        if img_dir and os.path.exists(img_dir):
            # 優先順位: down.png -> shield.png -> armor.png -> フォルダ内の最初の画像
            priority_names = ["down.png", "shield.png", "armor.png"]
            for name in priority_names:
                test_path = os.path.join(img_dir, name)
                if os.path.exists(test_path):
                    path = test_path
                    break
            
            if not path:
                # それでも見つからない場合は、フォルダ内の最初の .png を使う
                for f in os.listdir(img_dir):
                    if f.lower().endswith(".png"):
                        path = os.path.join(img_dir, f)
                        break
        
        if not path and img_path:
            path = img_path
            
        if not path or not os.path.exists(path):
            return None
            
        try:
            raw = pygame.image.load(path).convert_alpha()
            w, h = raw.get_size()
            
            # 最大サイズを50pxに制限しつつ、アスペクト比を維持
            max_bound = 50
            scale = min(max_bound / w, max_bound / h)
            new_w, new_h = int(w * scale), int(h * scale)
            
            # アイテム本体のサイズも画像に合わせる（中央寄せ描画のため）
            self.width, self.height = new_w, new_h
            return pygame.transform.scale(raw, (new_w, new_h))
        except Exception as e:
            print(f"[Item] Failed to load {path}: {e}")
            return None

    def draw(self, screen, camera_x, camera_y):
        if self.is_collected: return
        draw_x = self.x - camera_x + (60 - self.width) // 2
        draw_y = self.y - camera_y + (60 - self.height) // 2
        
        # 簡易的な描画（コインなら黄色い円など）
        if self.name == "coin":
            pygame.draw.circle(screen, (255, 215, 0), (int(draw_x + self.width // 2), int(draw_y + self.height // 2)), self.width // 2)
            pygame.draw.circle(screen, (218, 165, 32), (int(draw_x + self.width // 2), int(draw_y + self.height // 2)), self.width // 2, 2)
        else:
            pygame.draw.rect(screen, (200, 200, 200), (draw_x, draw_y, self.width, self.height))

class Coin(Item):
    """地面に落ちたコイン。踏んで拾うと所持金が増える。"""
    def __init__(self, x, y, min_amount=1, max_amount=10):
        super().__init__(x, y, "coin", "coin")
        self.iid = -1 # コインはID管理対象外だが構造を他と合わせる
        self.amount = random.randint(min_amount, max_amount)

    def collect(self, player):
        if hasattr(player, "coin"):
            player.coin += self.amount
            self.is_collected = True
            return f"{self.amount} コイン を 拾った！"
        return "コイン を 拾ったが、ポケットに穴が開いていたようだ..."


class DroppedWeapon(Item):
    """地面に落ちた武器アイテム。"""
    def __init__(self, x, y, weapon_key, weapon_data, enhance=0, stats=None):
        name = weapon_data.get("name", weapon_key)
        if enhance > 0:
            name = f"{name}+{enhance}"
        super().__init__(x, y, name, "weapon")
        self.weapon_key = weapon_key
        self.weapon_data = weapon_data
        self.enhance = enhance
        self.stats = stats or {}
        # 共通画像を使用
        from constants import COMMON_ITEM_IMAGES
        self._image = self._load_item_image({"image_path": COMMON_ITEM_IMAGES["weapon"]})

    def draw(self, screen, camera_x, camera_y):
        if self.is_collected:
            return
        import pygame
        draw_x = int(self.x - camera_x + (60 - self.width) // 2)
        draw_y = int(self.y - camera_y + (60 - self.height) // 2)
        if self._image:
            screen.blit(self._image, (draw_x, draw_y))
        else:
            pygame.draw.rect(screen, (180, 120, 50), (draw_x, draw_y, self.width, self.height))
            pygame.draw.rect(screen, (120, 70, 20), (draw_x, draw_y, self.width, self.height), 2)

    def collect(self, player):
        print(f"[WEAPON-COLLECT-START] {self.weapon_key} ({self.name})")
        from constants import MAX_EQUIP_SLOTS
        if player.get_equipment_count() >= MAX_EQUIP_SLOTS:
            print(f"[WEAPON-COLLECT-FAILED] Equipment slots full")
            return "装備がいっぱいで 拾えない！"

        try:
            self.is_collected = True
            if hasattr(player, "equip_weapon_by_key"):
                print(f"[WEAPON-COLLECT] Calling equip_weapon_by_key")
                player.equip_weapon_by_key(self.weapon_key, enhance=self.enhance, stats=self.stats)
                print(f"[WEAPON-COLLECT-SUCCESS] {self.weapon_key}")
            from wordings import Text
            return Text.Items.GET.format(name=self.name)
        except Exception as e:
            print(f"[ERROR] Weapon collect failed: {e}")
            import traceback
            traceback.print_exc()
            raise

class DroppedConsumable(Item):
    """地面に落ちた消費アイテム。拾うとインベントリに入る。"""
    def __init__(self, x, y, item_key, item_data):
        super().__init__(x, y, item_data.get("name", item_key), "consumable")
        self.item_key = item_key
        self.item_data = item_data
        
        # 優先順位: アイテム固有の画像 -> 共通アイテムアイコン
        from constants import COMMON_ITEM_IMAGES
        path = item_data.get("image_path")
        if not path:
            path = COMMON_ITEM_IMAGES.get("consumable")
            
        self._image = self._load_item_image({"image_path": path})
        if self._image and "color_tint" in item_data:
            tint = item_data["color_tint"]
            self._image = self._image.copy()
            w, h = self._image.get_size()
            lower_rect = pygame.Rect(0, h // 2, w, h // 2)
            self._image.fill((*tint, 255), rect=lower_rect, special_flags=pygame.BLEND_RGBA_MULT)

    def draw(self, screen, camera_x, camera_y):
        if self.is_collected:
            return
        import pygame
        draw_x = int(self.x - camera_x + (60 - self.width) // 2)
        draw_y = int(self.y - camera_y + (60 - self.height) // 2)
        if self._image:
            screen.blit(self._image, (draw_x, draw_y))
        else:
            # 仮描画：緑っぽい小瓶のような色
            pygame.draw.rect(screen, (50, 180, 50), (draw_x, draw_y, self.width, self.height))
            pygame.draw.rect(screen, (20, 100, 20), (draw_x, draw_y, self.width, self.height), 2)

    def collect(self, player):
        # effect == "lantern" was deprecated
        print(f"[ITEM-COLLECT-START] {self.item_key} ({self.name})")

        if hasattr(player, "add_item_to_inventory"):
            try:
                success = player.add_item_to_inventory(self.item_key, count=1)
                print(f"[ITEM-COLLECT] add_item_to_inventory returned: {success}")
                if success:
                    self.is_collected = True
                    from wordings import Text
                    msg = Text.Items.GET.format(name=self.name)
                    # クエスト達成チェック
                    if hasattr(player, "check_quest_completion"):
                        try:
                            quest_msg = player.check_quest_completion(self.item_key)
                            msg += quest_msg
                            print(f"[ITEM-COLLECT] Quest check completed")
                        except Exception as e:
                            print(f"[ERROR] Quest check failed: {e}")
                            import traceback
                            traceback.print_exc()
                    print(f"[ITEM-COLLECT-SUCCESS] {self.item_key}")
                    return msg
                else:
                    print(f"[ITEM-COLLECT-FAILED] {self.item_key} - inventory full")
                    return "バッグがいっぱいで 拾えない！"
            except Exception as e:
                print(f"[ERROR] add_item_to_inventory exception: {e}")
                import traceback
                traceback.print_exc()
                raise
        print(f"[ITEM-COLLECT-NO-METHOD] player has no add_item_to_inventory")
        return "拾えなかった！"


class DroppedArmor(Item):
    """地面に落ちたよろい。踏んで拾うとインベントリに入る。"""
    def __init__(self, x, y, armor_key, armor_data, enhance=0, stats=None):
        name = armor_data.get("name", armor_key)
        if enhance > 0:
            name = f"{name}+{enhance}"
        super().__init__(x, y, name, "armor")
        self.armor_key = armor_key
        self.armor_data = armor_data
        self.enhance = enhance
        self.stats = stats or {}
        # 共通画像を使用
        from constants import COMMON_ITEM_IMAGES
        self._image = self._load_item_image({"image_path": COMMON_ITEM_IMAGES["armor"]})


    def draw(self, screen, camera_x, camera_y):
        if self.is_collected:
            return
        draw_x = int(self.x - camera_x + (60 - self.width) // 2)
        draw_y = int(self.y - camera_y + (60 - self.height) // 2)

        if self._image:
            # 実際の画像がある場合はそちらを使う
            screen.blit(self._image, (draw_x, draw_y))
        else:
            # 仮描画：よろいっぽい色付き四角 + 縦線マーク
            from constants import ARMOR_COLORS
            color = ARMOR_COLORS.get(self.armor_key, (100, 100, 100))
            hl = tuple(min(c + 60, 255) for c in color)
            pygame.draw.rect(screen, color, (draw_x, draw_y, self.width, self.height))
            pygame.draw.rect(screen, hl, (draw_x, draw_y, self.width, self.height), 3)
            cx = draw_x + self.width // 2
            pygame.draw.line(screen, (255, 255, 255), (cx, draw_y + 4), (cx, draw_y + self.height - 4), 2)

    def collect(self, player):
        from constants import MAX_EQUIP_SLOTS
        if player.get_equipment_count() >= MAX_EQUIP_SLOTS:
            return "装備がいっぱいで 拾えない！"
            
        self.is_collected = True
        if hasattr(player, "equip_armor_by_key"):
            player.equip_armor_by_key(self.armor_key, enhance=self.enhance, stats=self.stats)
        from wordings import Text
        return Text.Items.GET.format(name=self.name)


class DroppedShield(Item):
    """地面に落ちた盾。踏んで拾うとインベントリーに入る。"""
    def __init__(self, x, y, shield_key, shield_data, enhance=0, stats=None):
        name = shield_data.get("name", shield_key)
        if enhance > 0:
            name = f"{name}+{enhance}"
        super().__init__(x, y, name, "shield")
        self.shield_key = shield_key
        self.shield_data = shield_data
        self.enhance = enhance
        self.stats = stats or {}
        # 共通画像を使用
        from constants import COMMON_ITEM_IMAGES
        self._image = self._load_item_image({"image_path": COMMON_ITEM_IMAGES["shield"]})

    def draw(self, screen, camera_x, camera_y):
        if self.is_collected:
            return
        draw_x = int(self.x - camera_x + (60 - self.width) // 2)
        draw_y = int(self.y - camera_y + (60 - self.height) // 2)

        if self._image:
            screen.blit(self._image, (draw_x, draw_y))
        else:
            # 仮描画：皾型の盾っぽい色付き四角 + 横線マーク
            from constants import SHIELD_COLORS
            color = SHIELD_COLORS.get(self.shield_key, (100, 120, 100))
            hl = tuple(min(c + 60, 255) for c in color)
            pygame.draw.rect(screen, color, (draw_x, draw_y, self.width, self.height))
            pygame.draw.rect(screen, hl, (draw_x, draw_y, self.width, self.height), 3)
            cy = draw_y + self.height // 2
            pygame.draw.line(screen, (255, 255, 255), (draw_x + 4, cy), (draw_x + self.width - 4, cy), 2)

    def collect(self, player):
        from constants import MAX_EQUIP_SLOTS
        if player.get_equipment_count() >= MAX_EQUIP_SLOTS:
            return "装備がいっぱいで 拾えない！"
            
        self.is_collected = True
        if hasattr(player, "equip_shield_by_key"):
            player.equip_shield_by_key(self.shield_key, enhance=self.enhance, stats=self.stats)
        from wordings import Text
        return Text.Items.GET.format(name=self.name)


class DroppedAccessory(Item):
    """地面に落ちたアクセサリ。踏んで拾うとインベントリに入る。"""
    def __init__(self, x, y, accessory_key, accessory_data, enhance=0, stats=None):
        name = accessory_data.get("name", accessory_key)
        if enhance > 0:
            name = f"{name}+{enhance}"
        super().__init__(x, y, name, "accessory")
        self.accessory_key = accessory_key
        self.accessory_data = accessory_data
        self.enhance = enhance
        self.stats = stats or {}
        
        # 個別画像の設定があればそれをロード、なければ共通アイコンを使用
        if accessory_data.get("image_path") or accessory_data.get("image_dir"):
            self._image = self._load_item_image(accessory_data)
        else:
            from constants import COMMON_ITEM_IMAGES
            self._image = self._load_item_image({"image_path": COMMON_ITEM_IMAGES.get("consumable")})

    def draw(self, screen, camera_x, camera_y):
        if self.is_collected:
            return
        draw_x = int(self.x - camera_x + (60 - self.width) // 2)
        draw_y = int(self.y - camera_y + (60 - self.height) // 2)

        if self._image:
            screen.blit(self._image, (draw_x, draw_y))
        else:
            pygame.draw.rect(screen, (100, 100, 180), (draw_x, draw_y, self.width, self.height))
            pygame.draw.rect(screen, (50, 50, 150), (draw_x, draw_y, self.width, self.height), 3)

    def collect(self, player):
        from constants import MAX_EQUIP_SLOTS
        if player.get_equipment_count() >= MAX_EQUIP_SLOTS:
            return "装備がいっぱいで 拾えない！"
            
        self.is_collected = True
        if hasattr(player, "equip_accessory_by_key"):
            player.equip_accessory_by_key(self.accessory_key, enhance=self.enhance, stats=self.stats)
        from wordings import Text
        return Text.Items.GET.format(name=self.name)


class DroppedStave(Item):
    """地面に落ちた杖。拾うとリストに追加される。"""
    def __init__(self, x, y, stave_key, stave_data):
        super().__init__(x, y, stave_data.get("name", stave_key), "stave")
        self.stave_key = stave_key
        self.stave_data = stave_data
        self.charges = stave_data.get("charges", 5)
        # 共通画像を使用
        from constants import COMMON_ITEM_IMAGES
        self._image = self._load_item_image({"image_path": COMMON_ITEM_IMAGES["stave"]})

    def draw(self, screen, camera_x, camera_y):
        if self.is_collected: return
        draw_x = int(self.x - camera_x + (60 - self.width) // 2)
        draw_y = int(self.y - camera_y + (60 - self.height) // 2)
        if self._image:
            screen.blit(self._image, (draw_x, draw_y))
        else:
            # 画像がない場合の仮描画（杖らしいシルエットを描画）
            # 本体（木製部分）
            pygame.draw.rect(screen, (139, 69, 19), (draw_x + 15, draw_y + 4, 6, 26))
            # 飾り（金属的な光沢）
            pygame.draw.rect(screen, (192, 192, 192), (draw_x + 15, draw_y + 10, 6, 4))
            # 先端（魔法の核）
            pygame.draw.circle(screen, (100, 200, 255), (draw_x + 18, draw_y + 6), 6) # 青っぽい宝石に変更
            pygame.draw.circle(screen, (255, 255, 255), (draw_x + 18, draw_y + 6), 3) # ハイライト

    def collect(self, player):
        from constants import MAX_STAVE_SLOTS
        if player.get_stave_count() >= MAX_STAVE_SLOTS:
            return "杖がいっぱいで 拾えない！"
            
        self.is_collected = True
        if hasattr(player, "equip_stave_by_key"):
            player.equip_stave_by_key(self.stave_key, charges=self.charges)
        from wordings import Text
        return Text.Items.GET.format(name=self.name)


class DroppedToken(Item):
    """クエスト対象の撃破/破壊時に落とす「達成の証」。インベントリを圧迫しない。"""
    def __init__(self, x, y, enemy_key, enemy_name):
        super().__init__(x, y, f"{enemy_name}達成の証", "token")
        self.enemy_key = enemy_key

    def draw(self, screen, camera_x, camera_y):
        if self.is_collected: return
        draw_x = int(self.x - camera_x + (60 - self.width) // 2)
        draw_y = int(self.y - camera_y + (60 - self.height) // 2)
        
        # 証っぽい金色のコインやメダルの描画
        import math
        import time
        t = time.time() * 3
        bounce = math.sin(t) * 5
        
        cx, cy = int(draw_x + self.width // 2), int(draw_y + self.height // 2 + bounce)
        
        pygame.draw.circle(screen, (255, 215, 0), (cx, cy), 12)
        pygame.draw.circle(screen, (218, 165, 32), (cx, cy), 12, 3) # ふち
        pygame.draw.circle(screen, (255, 255, 200), (cx-3, cy-3), 3) # ハイライト
        
        # 星マーク（簡易）
        pygame.draw.line(screen, (255, 255, 255), (cx, cy-6), (cx, cy+6), 2)
        pygame.draw.line(screen, (255, 255, 255), (cx-5, cy-2), (cx+5, cy+2), 2)
        pygame.draw.line(screen, (255, 255, 255), (cx-5, cy+2), (cx+5, cy-2), 2)

    def collect(self, player):
        self.is_collected = True
        if hasattr(player, "add_quest_token"):
            completion_msg = player.add_quest_token(self.enemy_key)
            return f"{self.name} を 手に入れた！（達成の証）{completion_msg}"
        
        if not hasattr(player, "quest_tokens"):
            player.quest_tokens = {}
        player.quest_tokens[self.enemy_key] = player.quest_tokens.get(self.enemy_key, 0) + 1
        return f"{self.name} を 手に入れた！（達成の証）"


