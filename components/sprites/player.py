import pygame
import random
from systems.game_state import game_state, is_paused
from components.sprites.entity import Entity
from systems.combat_handler import deal_damage
from constants import (
    KEY_MOVE_UP, KEY_MOVE_DOWN, KEY_MOVE_LEFT, KEY_MOVE_RIGHT,
    KEY_ATTACK, KEY_CONFIRM, KEY_TURN_ONLY,
    ATTACK_TAME_DURATION, ATTACK_STRIKE_DURATION, ATTACK_ANIMATION_FRAMES, 
    COMBAT_LOG_WAIT_FRAMES, PLAYER_HP, PLAYER_COIN, PLAYER_ATTACK, 
    PLAYER_WEAPON, WEAPON_DATA, PLAYER_DEFENSE, PLAYER_ARMOR, ARMOR_DATA, ARMOR_COLORS,
    PLAYER_SHIELD, SHIELD_DATA, SHIELD_COLORS, PLAYER_ORE,
    MAX_ITEM_SLOTS, MAX_EQUIP_SLOTS, MAX_STAVE_SLOTS,
    STAVE_DATA, HIT_STUN_DURATION, SOUND_ATTACK_HIT, SOUND_ATTACK_MISS
)

# 装備品インスタンス管理用カウンター（ゲーム全体でユニークなID）
_equip_id_counter = 0

def _new_equip_id():
    """新しい装備インスタンスIDを発行して返す"""
    global _equip_id_counter
    _equip_id_counter += 1
    return _equip_id_counter

class EquipInstance:
    """
    武器・よろい・盾の1個1個を個別に管理するクラス。
    同名の装備が複数あっても iid で区別できる。
    入手時にステータスが ±20% 変動する個体差システムを搭載。
    """
    def __init__(self, equip_type, key, randomize=False):
        self.iid = _new_equip_id()
        self.equip_type = equip_type
        self.key = key
        self.enhance = 0
        self.stats = {} # 個体差システムは廃止されました

    # def _randomize_stats(self):
    #     import random
    #     # マスターデータの取得
    #     data = {}
    #     if self.equip_type == "weapon": data = WEAPON_DATA.get(self.key, {})
    #     elif self.equip_type == "armor": data = ARMOR_DATA.get(self.key, {})
    #     elif self.equip_type == "shield": data = SHIELD_DATA.get(self.key, {})
    #     
    #     # 変動させたいパラメータ一覧
    #     target_keys = ["attack_bonus", "defense_bonus", "hp_bonus", "dex_bonus", "eva_bonus", "crit_bonus", "stave_bonus", "block_chance"]
    #     
    #     for k in target_keys:
    #         if k in data:
    #             val = data[k]
    #             if isinstance(val, (int, float)):
    #                 # ±20% の変動
    #                 variance = random.uniform(0.8, 1.2)
    #                 new_val = val * variance
    #                 if isinstance(val, int):
    #                     self.stats[k] = int(new_val)
    #                 else:
    #                     self.stats[k] = round(new_val, 3)

    def get_stat(self, stat_key, default=0):
        """常にマスターデータを返す（個体差システム廃止）"""
        # フォールバック：マスターデータ
        data = {}
        if self.equip_type == "weapon": data = WEAPON_DATA.get(self.key, {})
        elif self.equip_type == "armor": data = ARMOR_DATA.get(self.key, {})
        elif self.equip_type == "shield": data = SHIELD_DATA.get(self.key, {})
        elif self.equip_type == "lantern":
            from constants import LANTERN_DATA
            data = LANTERN_DATA.get(self.key, {})
        return data.get(stat_key, default)

    def get_enhance_bonus(self, stat_key):
        """
        growth パラメーターを考慮した強化ボーナスを計算して返す。
        
        growth:
          bonus_limit      : base_bonus の何倍がソフトキャップか (例: 2 → base*2 が上限)
          times_limit      : キャップに到達するまでの強化回数 (例: 50)
          over_limit_growth_rate: キャップ超過後の1回あたりの成長率 (例: 0.003 = 0.3%/回)
        
        growth が未設定の場合は従来の flat +1 動作にフォールバック。
        """
        # マスターデータ取得
        data = {}
        if self.equip_type == "weapon": data = WEAPON_DATA.get(self.key, {})
        elif self.equip_type == "armor": data = ARMOR_DATA.get(self.key, {})
        elif self.equip_type == "shield": data = SHIELD_DATA.get(self.key, {})

        growth = data.get("growth")
        if not growth or self.enhance == 0:
            # growth 未設定 → 旧来の flat +1 per enhance
            return self.enhance

        base = self.get_stat(stat_key, 0)
        if base <= 0:
            return self.enhance  # ベースが0以下なら flat フォールバック

        bonus_limit = growth.get("bonus_limit", 2)
        times_limit = max(1, growth.get("times_limit", 50))
        over_rate   = growth.get("over_limit_growth_rate", 0.003)

        growth_room   = base * (bonus_limit - 1)   # 10 * (2-1) = 10
        per_step      = growth_room / times_limit   # 10 / 50 = 0.2
        over_per_step = base * over_rate            # 10 * 0.003 = 0.03

        if self.enhance <= times_limit:
            bonus = self.enhance * per_step
        else:
            bonus = growth_room + (self.enhance - times_limit) * over_per_step

        # 攻撃・防御・HPなどの主要ステータスは整数で返す（切り捨て）
        if stat_key in ["attack_bonus", "defense_bonus", "hp_bonus"]:
            import math
            return math.floor(bonus)
            
        return round(bonus, 3)

    def get_name(self):
        """表示名を返す（強化値が付いていれば +N を付加）"""
        if self.equip_type == "lantern":
            from constants import LANTERN_DATA
            base = LANTERN_DATA.get(self.key, {}).get("name", self.key)
        else:
            base = self.get_stat("name", self.key)
            
        if self.enhance > 0:
            return f"{base}+{self.enhance}"
        return base

    def to_dict(self):
        return {
            "iid": self.iid,
            "type": self.equip_type,
            "key": self.key,
            "enhance": self.enhance,
            "stats": self.stats
        }

    @classmethod
    def from_dict(cls, data):
        # randomize=False にして、保存されている stats をそのまま使う
        inst = cls(data["type"], data["key"], randomize=False)
        inst.iid = data.get("iid", inst.iid)
        inst.enhance = data.get("enhance", 0)
        
        # 読み込んだ stats を整数にキャストして保持（小数の混入を防ぐ）
        raw_stats = data.get("stats", {})
        inst.stats = {}
        for k, v in raw_stats.items():
            if k in ["attack_bonus", "defense_bonus", "hp_bonus"]:
                inst.stats[k] = int(v)
            else:
                inst.stats[k] = v
                
        global _equip_id_counter
        if inst.iid > _equip_id_counter:
            _equip_id_counter = inst.iid
        return inst

class StaveInstance:
    """
    杖の1個1個を管理するクラス。
    残り回数（charges）を保持する。
    """
    def __init__(self, key, charges=5):
        self.iid = _new_equip_id()
        self.key = key
        self.name = STAVE_DATA.get(key, {}).get("name", key)
        self.charges = charges
        self.enhance = 0

    def get_stat(self, stat_key, default=0):
        from constants import STAVE_DATA
        return STAVE_DATA.get(self.key, {}).get(stat_key, default)

    def get_name_with_charges(self):
        return f"{self.name}[{self.charges}]"

    def get_name(self):
        return self.name

    def to_dict(self):
        return {
            "iid": self.iid,
            "key": self.key,
            "charges": self.charges
        }

    @classmethod
    def from_dict(cls, data):
        inst = cls(data["key"], data.get("charges", 5))
        inst.iid = data.get("iid", inst.iid)
        global _equip_id_counter
        if inst.iid > _equip_id_counter:
            _equip_id_counter = inst.iid
        return inst

from components.sprites.weapon import OneHanded

# 外部モジュールで管理されている方向キーの状態をインポート
from systems.events import active_direction_keys

player_settings = {
    "image_size": (50, 50),
    "speed": 2,
    "x": 300,
    "y": 220,
}

class Player(Entity):
    _player_scaled_cache = {} # {(img_obj, phase, tint, is_back): surface}

    @classmethod
    def clear_cache(cls):
        """蓄積されたプレイヤー関連のスケーリング済み画像をクリアする"""
        count = len(cls._player_scaled_cache)
        cls._player_scaled_cache = {}
        if count > 0:
            print(f"[MEMORY] Player scaled image cache cleared ({count} items)")

    @property
    def total_attack(self):
        """基本攻撃力 + 装備ボーナス(武器・鎧・盾)の合計"""
        bonus = 0
        # 武器
        if self.weapon:
            # self.weapon は OneHanded インスタンスなど。その内部で EquipInstance を参照するようにするか、
            # もしくは所持インベントリから取得する。
            # ここではシンプルに所持武器の EquipInstance から取得
            weapon_inst = self._find_equip_inst(self.weapon_inventory, self.equipped_weapon)
            if weapon_inst:
                bonus += weapon_inst.get_stat("attack_bonus", 0) + weapon_inst.get_enhance_bonus("attack_bonus")
        
        # 鎧
        armor_inst = self._find_equip_inst(self.armor_inventory, self.equipped_armor)
        if armor_inst:
            bonus += armor_inst.get_stat("attack_bonus", 0)
        
        # 盾
        shield_inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield)
        if shield_inst:
            bonus += shield_inst.get_stat("attack_bonus", 0)
            
        # 最終的に整数にキャストして返す（HUD表示対策）
        return int(self.attack + bonus)

    @property
    def max_hp(self):
        """基本最大HPに装備ボーナスを加算した値を返す"""
        bonus = 0
        armor_inst = self._find_equip_inst(self.armor_inventory, self.equipped_armor)
        if armor_inst:
            bonus += armor_inst.get_stat("hp_bonus", 0)
        shield_inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield)
        if shield_inst:
            bonus += shield_inst.get_stat("hp_bonus", 0)
        return int(self._base_max_hp + bonus)

    @max_hp.setter
    def max_hp(self, value):
        self._base_max_hp = value

    @property
    def total_accuracy_close(self):
        """近接命中値の合計 (基本 + 装備補正)"""
        from constants import PLAYER_ACCURACY_CLOSE
        base = PLAYER_ACCURACY_CLOSE
        bonus = 0
        weapon_inst = self._find_equip_inst(self.weapon_inventory, self.equipped_weapon)
        if weapon_inst: bonus += weapon_inst.get_stat("accuracy_bonus_close", weapon_inst.get_stat("accuracy_bonus", 0))
        armor_inst = self._find_equip_inst(self.armor_inventory, self.equipped_armor)
        if armor_inst: bonus += armor_inst.get_stat("accuracy_bonus_close", armor_inst.get_stat("accuracy_bonus", 0))
        shield_inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield)
        if shield_inst: bonus += shield_inst.get_stat("accuracy_bonus_close", shield_inst.get_stat("accuracy_bonus", 0))
        return int(base + bonus)

    @property
    def total_accuracy_ranged(self):
        """遠隔命中値の合計 (基本 + 装備補正)"""
        from constants import PLAYER_ACCURACY_RANGED
        base = PLAYER_ACCURACY_RANGED
        bonus = 0
        weapon_inst = self._find_equip_inst(self.weapon_inventory, self.equipped_weapon)
        if weapon_inst: bonus += weapon_inst.get_stat("accuracy_bonus_ranged", weapon_inst.get_stat("accuracy_bonus", 0))
        armor_inst = self._find_equip_inst(self.armor_inventory, self.equipped_armor)
        if armor_inst: bonus += armor_inst.get_stat("accuracy_bonus_ranged", armor_inst.get_stat("accuracy_bonus", 0))
        shield_inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield)
        if shield_inst: bonus += shield_inst.get_stat("accuracy_bonus_ranged", shield_inst.get_stat("accuracy_bonus", 0))
        return int(base + bonus)

    @property
    def eva_bonus(self):
        """回避率補正の合計 (基礎回避 + 全装備補正)"""
        from constants import PLAYER_EVASION
        base = PLAYER_EVASION
        bonus = 0
        weapon_inst = self._find_equip_inst(self.weapon_inventory, self.equipped_weapon)
        if weapon_inst: bonus += weapon_inst.get_stat("eva_bonus", 0)
        armor_inst = self._find_equip_inst(self.armor_inventory, self.equipped_armor)
        if armor_inst: bonus += armor_inst.get_stat("eva_bonus", 0)
        shield_inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield)
        if shield_inst: bonus += shield_inst.get_stat("eva_bonus", 0)
        return int(base + bonus)

    @property
    def crit_bonus(self):
        """クリティカル率補正の合計"""
        bonus = 0
        weapon_inst = self._find_equip_inst(self.weapon_inventory, self.equipped_weapon)
        if weapon_inst: bonus += weapon_inst.get_stat("crit_bonus", 0)
        armor_inst = self._find_equip_inst(self.armor_inventory, self.equipped_armor)
        if armor_inst: bonus += armor_inst.get_stat("crit_bonus", 0)
        shield_inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield)
        if shield_inst: bonus += shield_inst.get_stat("crit_bonus", 0)
        return bonus

    @property
    def stave_bonus(self):
        """杖の回数ボーナス合計"""
        bonus = 0
        armor_inst = self._find_equip_inst(self.armor_inventory, self.equipped_armor)
        if armor_inst: bonus += armor_inst.get_stat("stave_bonus", 0)
        shield_inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield)
        if shield_inst: bonus += shield_inst.get_stat("stave_bonus", 0)
        return bonus
    
    @property
    def lantern_bonus(self):
        """カンテラの視界半径ボーナス合計"""
        bonus = 0
        armor_inst = self._find_equip_inst(self.armor_inventory, self.equipped_armor)
        if armor_inst: bonus += armor_inst.get_stat("lantern_bonus", 0)
        shield_inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield)
        if shield_inst: bonus += shield_inst.get_stat("lantern_bonus", 0)
        return bonus

    @property
    def regen_bonus(self):
        """リジェネ（自然回復）ボーナス合計（1ターンあたりのHP回復量）"""
        bonus = 0
        armor_inst = self._find_equip_inst(self.armor_inventory, self.equipped_armor)
        if armor_inst: bonus += armor_inst.get_stat("regen_bonus", 0)
        shield_inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield)
        if shield_inst: bonus += shield_inst.get_stat("regen_bonus", 0)
        return bonus
    
    @property
    def total_defense(self):
        """基本防御力 + 装備ボーナスの合計"""
        bonus = 0
        armor_inst = self._find_equip_inst(self.armor_inventory, self.equipped_armor)
        if armor_inst: bonus += armor_inst.get_stat("defense_bonus", 0) + armor_inst.get_enhance_bonus("defense_bonus")
        
        shield_inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield)
        if shield_inst: bonus += shield_inst.get_stat("defense_bonus", 0) + shield_inst.get_enhance_bonus("defense_bonus")
        
        return int(self.defense + bonus)

    @property
    def block_chance_close(self):
        """近接ブロック率 (強化込み)"""
        shield_inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield)
        if not shield_inst: return 0.0
        base = shield_inst.get_stat("block_chance_close", shield_inst.get_stat("block_chance", 0.0))
        return base + shield_inst.get_enhance_bonus("block_chance_close")

    @property
    def block_chance_ranged(self):
        """遠隔ブロック率 (強化込み)"""
        shield_inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield)
        if not shield_inst: return 0.0
        base = shield_inst.get_stat("block_chance_ranged", shield_inst.get_stat("block_chance", 0.0))
        return base + shield_inst.get_enhance_bonus("block_chance_ranged")

    def __init__(self):
        super().__init__(x=player_settings["x"], y=player_settings["y"], 
                         hp=PLAYER_HP, max_hp=PLAYER_HP, attack=PLAYER_ATTACK, width=64, height=64)
        self._base_max_hp = PLAYER_HP
        self.name = "自分"
        self.coin = PLAYER_COIN
        self.bank_coin = 0  # 銀行の預金額
        self.items = [] # {"key": "hp_potion", "count": 2} のような辞書のリスト
        
        # 防御力属性
        self.defense = PLAYER_DEFENSE  # 現在の防御力（装備によって変動する）
        
        # 盾属性
        self.block_chance = 0.0  # 現在のブロック確率（盾の装備によって変動）
        
        # 装備品インベントリ（EquipInstance オブジェクトのリスト）
        self.armor_inventory = []    # 所持中のよろい EquipInstance のリスト
        self.equipped_armor = None   # 現在装備中のよろいの iid（整数）
        
        # 盾インベントリーの初期化
        self.shield_inventory = []   # 所持中の盾 EquipInstance のリスト
        self.equipped_shield = None  # 現在装備中の盾の iid（整数）
        
        # カンデラインベントリの初期化
        self.lantern_inventory = []  # 所持中のカンデラ EquipInstance のリスト
        self.equipped_lantern = None # 現在装備中のカンデラの iid（整数）
        
        # 杖インベントリ
        self.stave_inventory = []
        self.invincible_turns = 0
        self.regen_pool = 0.0 # 小数点以下のリジェネを蓄積するプール
        
        # 杖を振るアニメーション用
        self.waving_stave_inst = None
        
        # 状態異常
        self._status = "normal" # "normal", "poison", etc.
        self.status_timer = 0  # ターン数（必要なら）

        self._init_images()
        
        self.idle_anim_timer = 0
        self.prev_floor = 0
        self.current_floor = 0

        # 落下アニメーション用
        self.is_falling = False
        self.falling_timer = 0
        
        self.reset_status()
        self.guild_point = 0
        self.guild_rank = "-"
        self.active_quests = [] # 複数受注可能とする
        self.quest_tokens = {}  # {"bat": 5, "slime": 2} のように討伐の証をインベントリ外で管理
        self.completed_fixed_quests = [] # 完了済みの固定クエストID
        self.has_seen_ending = False # エンディング視聴済みフラグ
        self.event_items = [] # {"key": "guild_cert_e", "count": 1}

        # 預かり屋（倉庫）システム
        self.warehouse_items = []
        self.warehouse_max = 20

        # 初期装備のよろいを追加
        if PLAYER_ARMOR and PLAYER_ARMOR in ARMOR_DATA:
            inst = EquipInstance("armor", PLAYER_ARMOR)
            self.armor_inventory.append(inst)
            self._apply_armor(inst)
        
        # 初期装備の盾を追加
        if PLAYER_SHIELD and PLAYER_SHIELD in SHIELD_DATA:
            inst = EquipInstance("shield", PLAYER_SHIELD)
            self.shield_inventory.append(inst)
            self._apply_shield(inst)
        
        # ステータスの初期化
        self.max_hp = PLAYER_HP
        self.hp = PLAYER_HP
        self.attack = PLAYER_ATTACK
        self.defense = PLAYER_DEFENSE
        self.mp = 0 
        self.max_mp = 0
        self.coin = PLAYER_COIN
        
        self.weapon_inventory = []  # 所持中の武器 EquipInstance のリスト
        self.equipped_weapon = None  # 現在装備中の武器の iid（整数）
        self.weapon = None

        # 初期装備をインベントリに追加
        if PLAYER_WEAPON:
            inst = EquipInstance("weapon", PLAYER_WEAPON)
            self.weapon_inventory.append(inst)
            self.equipped_weapon = inst.iid
            self.weapon = self._get_weapon_instance(PLAYER_WEAPON, inst.enhance)

    @property
    def condition(self):
        return self._status

    @condition.setter
    def condition(self, value):
        self._status = value
        if value == "poison":
            # 毒状態になった時、持続時間を5-10のランダムで決定
            self.status_timer = random.randint(5, 10)
        else:
            self.status_timer = 0
        
    def _init_images(self):
        # アニメーション画像の読み込み
        import os
        self.walk_images = {}
        self.idle_images = {}
        self.attack_images = {}
        directions = ["down", "left", "right", "up"]
        for d in directions:
            # ベースとなる 0, 1 番フレームを一時保持
            frames = {}
            for i in range(2):
                path = f"components/pictures/player/walk/{d}_{i}.png"
                if os.path.exists(path):
                    frames[i] = pygame.image.load(path).convert_alpha()
                elif d == "right":
                    # leftの同じ番号を反転して使用
                    left_path = f"components/pictures/player/walk/left_{i}.png"
                    if os.path.exists(left_path):
                        frames[i] = pygame.transform.flip(pygame.image.load(left_path).convert_alpha(), True, False)
                    else:
                        frames[i] = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                else:
                    frames[i] = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

            # idel(待機/中間フレーム)の読み込み
            idel_frame = None
            idel_path = f"components/pictures/player/walk/{d}_idel.png"
            if os.path.exists(idel_path):
                idel_frame = pygame.image.load(idel_path).convert_alpha()
            elif d == "right":
                # left_idelがあれば反転して使用
                left_idel_path = f"components/pictures/player/walk/left_idel.png"
                if os.path.exists(left_idel_path):
                    idel_frame = pygame.transform.flip(pygame.image.load(left_idel_path).convert_alpha(), True, False)
            
            self.idle_images[d] = idel_frame
            # 歩行シーケンス構築: [0, idel, 1, idel]
            mid = idel_frame if idel_frame else frames[0]
            self.walk_images[d] = [frames[0], mid, frames[1], mid]
        

    def operate(self, dungeon, dialog=None, events=[]):
        from systems.game_state import game_state, is_paused
        # 敵がダメージ演出（点滅）中の場合は、プレイヤーの入力を受け付けないようにする（ポーズ状態）
        is_any_enemy_damaged = any(e.damage_flash_timer > 0 for e in dungeon.enemies)
        
        if is_paused() or self.is_moving or self.is_attacking or game_state.get("dialog_just_closed") or is_any_enemy_damaged:
            return
            
        turn_consumed = False

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == KEY_ATTACK:
                    if dungeon.current_floor == 0:
                        break 
                    self.waving_stave_inst = None 
                    self._perform_attack()
                    print(f"[COMBAT] Player Attack Action (Facing: {self.facing})")
                    turn_consumed = True
                    break 

        if not turn_consumed:
            latest_key = active_direction_keys[-1] if len(active_direction_keys) > 0 else None
            if latest_key:
                keys = pygame.key.get_pressed()
                is_turning_only = keys[KEY_TURN_ONLY]
                
                dx, dy = 0, 0
                if latest_key == KEY_MOVE_LEFT: self.set_facing("left"); dx = -dungeon.tile_size
                elif latest_key == KEY_MOVE_RIGHT: self.set_facing("right"); dx = dungeon.tile_size
                elif latest_key == KEY_MOVE_UP: self.set_facing("up"); dy = -dungeon.tile_size
                elif latest_key == KEY_MOVE_DOWN: self.set_facing("down"); dy = dungeon.tile_size

                if is_turning_only:
                    return 

                target_x = self.x + dx
                target_y = self.y + dy
                
                all_entities = [self] + dungeon.enemies + dungeon.npcs
                if self.can_move_grid(target_x, target_y, dungeon):
                    self.prev_x = self.x
                    self.prev_y = self.y
                    self.target_x = target_x
                    self.target_y = target_y
                    self.is_moving = True
                    # ミニマップの探索範囲を更新
                    dungeon.reveal_area(target_x // dungeon.tile_size, target_y // dungeon.tile_size)
                    
                    import time
                    t = time.perf_counter()
                    key_name = {KEY_MOVE_UP: "UP", KEY_MOVE_DOWN: "DOWN", KEY_MOVE_LEFT: "LEFT", KEY_MOVE_RIGHT: "RIGHT"}.get(latest_key, "UNKNOWN")
                    print(f"[TIME][{t:.4f}] Player Move Start: ({self.x // dungeon.tile_size}, {self.y // dungeon.tile_size}) -> ({target_x // dungeon.tile_size}, {target_y // dungeon.tile_size}) | Key: {key_name}")
                    
                    # 移動後のグリッド座標でログを出力 (階層、HP、状態異常、入力キーも付加)
                    key_name = {KEY_MOVE_UP: "UP", KEY_MOVE_DOWN: "DOWN", KEY_MOVE_LEFT: "LEFT", KEY_MOVE_RIGHT: "RIGHT"}.get(latest_key, "UNKNOWN")
                    print(f"[DUNGEON] Floor {self.current_floor} | Player Move: ({target_x // dungeon.tile_size}, {target_y // dungeon.tile_size}) | Key: {key_name} | HP: {self.hp}/{self.max_hp}, Cond: {self.condition}")
                    self.step_toggle = not self.step_toggle
                    turn_consumed = True 
                    
        if turn_consumed:
            if self.invincible_turns > 0:
                self.invincible_turns -= 1
                if self.invincible_turns == 0 and dialog:
                    msg = "無敵状態が 切れた！"
                    if dialog.is_active: dialog.text += "\n" + msg
                    else:
                        from systems.game_state import game_state
                        dialog.text = msg
                        dialog.is_active = True
                        game_state["dialog_modal"] = False
                        dialog.auto_close_timer = COMBAT_LOG_WAIT_FRAMES
            
            if self.is_moving:
                # 移動時は即座に敵のターンを開始させて「同時行動」を演出する
                self.start_enemy_turn(dungeon)
            else:
                # 攻撃時などは、今まで通りアニメーション終了を待ってから敵を動かす
                self.enemy_turn_pending = True

    def start_enemy_turn(self, dungeon):
        """敵のターン（思考・行動）を初期化して開始する。同時行動時と通常時で共通。"""
        from systems.game_state import game_state
        game_state["turn_state"] = "enemies"
        game_state["current_enemy_idx"] = 0
        self.enemy_turn_pending = False
        for enemy in dungeon.enemies: enemy.has_acted = False
        
        # ターンの開始時に一度だけ占有情報を計算してキャッシュ
        all_entities = [self] + dungeon.enemies
        occupied_cells = set()
        for e in all_entities:
            if not getattr(e, "is_dead", False):
                gx = int((e.target_x + e.width / 2) // dungeon.tile_size)
                gy = int((e.target_y + e.height / 2) // dungeon.tile_size)
                occupied_cells.add((gx, gy))
        game_state["occupied_cells"] = occupied_cells
        game_state["all_entities_cache"] = all_entities

    def _perform_attack(self):
        self.is_attacking = True
        self.attack_timer = ATTACK_ANIMATION_FRAMES

        from systems.sound_handler import sound_manager
        if self.waving_stave_inst:
            sound_path = STAVE_DATA.get(self.waving_stave_inst.key, {}).get("sound")
            sound_manager.play_sfx(sound_path)
        elif self.weapon:
            sound_path = self.weapon.data.get("sound")
            sound_manager.play_sfx(sound_path)

    def _find_equip_inst(self, inventory, iid):
        for inst in inventory:
            if inst.iid == iid:
                return inst
        return None

    def update_equipment_stats(self):
        if self.equipped_weapon:
            inst = self._find_equip_inst(self.weapon_inventory, self.equipped_weapon)
            if inst:
                new_weapon = self._get_weapon_instance(inst.key, inst.enhance)
                if new_weapon:
                    self.weapon = new_weapon
        if self.equipped_armor:
            inst = self._find_equip_inst(self.armor_inventory, self.equipped_armor)
            if inst:
                self._apply_armor(inst)

    def change_weapon(self, iid):
        inst = self._find_equip_inst(self.weapon_inventory, iid)
        if not inst: return
        new_weapon = self._get_weapon_instance(inst.key, inst.enhance)
        if new_weapon:
            self.equipped_weapon = inst.iid
            self.weapon = new_weapon

    def set_facing(self, direction):
        """向きを設定し、必要ならアニメーションをリセットする"""
        if self.facing != direction:
            self.facing = direction
            self.walk_anim_timer = 0

    def equip_weapon_by_key(self, weapon_key):
        if weapon_key not in WEAPON_DATA: return None
        from constants import MAX_EQUIP_SLOTS
        if self.get_equipment_count() >= MAX_EQUIP_SLOTS: return None
        
        inst = EquipInstance("weapon", weapon_key)
        self.weapon_inventory.append(inst)
        return inst

    def equip_armor_by_key(self, armor_key):
        if armor_key not in ARMOR_DATA: return None
        from constants import MAX_EQUIP_SLOTS
        if self.get_equipment_count() >= MAX_EQUIP_SLOTS: return None
        
        inst = EquipInstance("armor", armor_key)
        self.armor_inventory.append(inst)
        return inst

    def equip_shield_by_key(self, shield_key):
        if shield_key not in SHIELD_DATA: return None
        from constants import MAX_EQUIP_SLOTS
        if self.get_equipment_count() >= MAX_EQUIP_SLOTS: return None
        
        inst = EquipInstance("shield", shield_key)
        self.shield_inventory.append(inst)
        return inst

    def change_armor(self, iid):
        inst = self._find_equip_inst(self.armor_inventory, iid)
        if not inst: return
        if inst.key not in ARMOR_DATA: return
        self._apply_armor(inst)

    def change_shield(self, iid):
        inst = self._find_equip_inst(self.shield_inventory, iid)
        if not inst: return
        self._apply_shield(inst)

    def _apply_armor(self, inst):
        self.equipped_armor = inst.iid
        data = ARMOR_DATA.get(inst.key)
        if not data:
            self.defense = PLAYER_DEFENSE
            return
            
        bonus = data.get("defense_bonus", 0) + inst.enhance
        self.defense = PLAYER_DEFENSE + bonus
        
        # 防具画像のロード
        self._armor_images = {}
        import os
        img_dir = data.get("image_dir", "")
        if img_dir:
            if not os.path.exists(img_dir):
                print(f"[\033[93mWARNING\033[0m] Armor directory not found: {img_dir}")
            else:
                # 代表画像（down.png またはディレクトリ内の最初）
                shared_img = None
                from systems.resources import load_image
                for cand in ["down.png", "armor.png", f"{inst.key}.png"]:
                    p = os.path.join(img_dir, cand)
                    raw = load_image(p)
                    if raw:
                        shared_img = pygame.transform.scale(raw, (self.width, self.height))
                        break

                for direction in ("down", "left", "right", "up"):
                    path = f"{img_dir}/{direction}.png"
                    raw = load_image(path)
                    if raw:
                        self._armor_images[direction] = pygame.transform.scale(
                            raw, (self.width, self.height)
                        )
                    elif direction == "right" and "left" in self._armor_images:
                        # rightが無ければleftを反転
                        self._armor_images[direction] = pygame.transform.flip(self._armor_images["left"], True, False)
                    elif shared_img:
                        self._armor_images[direction] = shared_img

    def unequip_weapon(self):
        self.equipped_weapon = None
        self.weapon = None

    def unequip_armor(self):
        self.equipped_armor = None
        self.defense = PLAYER_DEFENSE
        self._armor_images = {}

    def unequip_shield(self):
        self.equipped_shield = None
        self.block_chance = 0.0
        self._shield_images = {}

    def change_lantern(self, iid):
        inst = self._find_equip_inst(self.lantern_inventory, iid)
        if not inst: return
        self.equipped_lantern = inst.iid

    def get_aggro_modifier(self):
        """装備品によるモンスターの索敵範囲への補正値を取得する"""
        mod = 0
        if self.equipped_weapon:
            inst = self._find_equip_inst(self.weapon_inventory, self.equipped_weapon)
            if inst: mod += inst.get_stat("aggro_mod", 0)
        if self.equipped_armor:
            inst = self._find_equip_inst(self.armor_inventory, self.equipped_armor)
            if inst: mod += inst.get_stat("aggro_mod", 0)
        if self.equipped_shield:
            inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield)
            if inst: mod += inst.get_stat("aggro_mod", 0)
        return mod

    def unequip_lantern(self):
        self.equipped_lantern = None

    def reset_status(self):
        """全ての状態フラグ（攻撃、移動、落下、硬直など）を初期化する"""
        self.is_moving = False
        self.is_attacking = False
        self.is_falling = False
        self.attack_timer = 0
        self.falling_timer = 0
        self.damage_flash_timer = 0
        self.target_x = self.x
        self.target_y = self.y
        self.prev_x = self.x
        self.prev_y = self.y

    def start_falling(self, tile_size):
        if not self.is_falling:
            gx = int((self.x + self.width / 2) // tile_size)
            gy = int((self.y + self.height / 2) // tile_size)
            self.x = gx * tile_size + (tile_size - self.width) // 2
            self.y = gy * tile_size + (tile_size - self.height) // 2
            self.target_x = self.x
            self.target_y = self.y
            
            self.reset_status() # 全ての状態をリセット
            self.is_falling = True
            self.falling_timer = 60 

    def equip_lantern_by_key(self, lantern_key):
        from constants import LANTERN_DATA, MAX_EQUIP_SLOTS
        if lantern_key not in LANTERN_DATA: return None
        if self.get_equipment_count() >= MAX_EQUIP_SLOTS: return None
        
        inst = EquipInstance("lantern", lantern_key)
        self.lantern_inventory.append(inst)
        return inst

    def equip_stave_by_key(self, stave_key, charges=None):
        if stave_key not in STAVE_DATA: return
        from constants import MAX_STAVE_SLOTS
        if self.get_stave_count() >= MAX_STAVE_SLOTS: return
        
        if charges is None:
            charges = STAVE_DATA[stave_key].get("charges", 5)
        
        # [NEW] 装備ボーナスを加算
        charges += self.stave_bonus
        
        inst = StaveInstance(stave_key, charges)
        self.stave_inventory.append(inst)
        return inst

    def _find_stave_inst(self, iid):
        for inst in self.stave_inventory:
            if inst.iid == iid: return inst
        return None

    def remove_stave_by_iid(self, iid):
        target = self._find_stave_inst(iid)
        if target:
            self.stave_inventory.remove(target)
            return True
        return False

    def _apply_shield(self, inst):
        self.equipped_shield = inst.iid
        data = SHIELD_DATA[inst.key]
        self.block_chance = data.get("block_chance", 0.0)
        self._shield_images = {}
        import os
        img_dir = data.get("image_dir", "")
        scale = data.get("image_scale", 1.0)
        target_w = int(self.width * scale)
        target_h = int(self.height * scale)
        if img_dir:
            if not os.path.exists(img_dir):
                print(f"[\033[93mWARNING\033[0m] Shield directory not found: {img_dir}")
            else:
                # 代表画像を探す（down.png を最優先）
                shared_img = None
                from systems.resources import load_image
                for cand in ["down.png", "shield.png", f"{inst.key}.png"]:
                    p = os.path.join(img_dir, cand)
                    raw = load_image(p)
                    if raw:
                        shared_img = pygame.transform.scale(raw, (target_w, target_h))
                        break
                
                for direction in ("down", "left", "right", "up"):
                    path = os.path.join(img_dir, f"{direction}.png")
                    raw = load_image(path)
                    if raw:
                        self._shield_images[direction] = pygame.transform.scale(raw, (target_w, target_h))
                    elif direction == "right" and "left" in self._shield_images:
                        # rightが無ければleftを反転
                        self._shield_images[direction] = pygame.transform.flip(self._shield_images["left"], True, False)
                    elif shared_img:
                        self._shield_images[direction] = shared_img

    def _perform_wave(self, stave_inst, dungeon, dialog):
        # アニメーションをせず即座に効果を発揮する
        from systems.magic_handler import execute_stave
        msg = execute_stave(self, stave_inst, dungeon, dialog)
        if dialog:
            from systems.game_state import game_state
            dialog.text = msg
            # is_active は呼び出し側で制御するのでここではセットしない
            game_state["dialog_modal"] = False
            from constants import COMBAT_LOG_WAIT_FRAMES
            dialog.auto_close_timer = COMBAT_LOG_WAIT_FRAMES
        
        self.enemy_turn_pending = True 


    def _draw_armor_overlay(self, screen, draw_x, draw_y, scale_x=1.0, scale_y=1.0, tint_color=None):
        img = getattr(self, "_armor_images", {}).get(self.facing)
        if img:
            # --- [OPTIMIZED] 鎧のスケーリングキャッシュ利用 ---
            # 呼吸フェーズを取得
            _, phase = self.get_breathing_scale()
            cache_key = (img, phase, tint_color, "armor")
            cached_img = Player._player_scaled_cache.get(cache_key)
            
            if cached_img is None:
                # スケーリング
                w, h = img.get_size()
                scaled = pygame.transform.smoothscale(img, (int(w * scale_x), int(h * scale_y)))
                # 着色
                if tint_color:
                    scaled.fill((*tint_color, 255), special_flags=pygame.BLEND_RGBA_MULT)
                cached_img = scaled
                Player._player_scaled_cache[cache_key] = cached_img
            
            img = cached_img
            
            # スケーリングによる座標補正（プレイヤー本体の 984-985行目と同様の計算が必要）
            # 渡された draw_x, draw_y は「キャラの基本枠(self.width, self.height)の左上」であると定義し直す
            render_x = draw_x + (self.width - img.get_width()) / 2
            render_y = draw_y + (self.height - img.get_height())
            
            inst = self._find_equip_inst(self.armor_inventory, self.equipped_armor)
            armor_data = ARMOR_DATA.get(inst.key, {}) if inst else {}
            pos_config = armor_data.get("position", {})
            offsets_dict = pos_config.get("offsets", armor_data.get("offsets", {}))
            offsets = offsets_dict.get(self.facing, (0, 0))
            
            # オフセットもスケーリング
            off_x, off_y = offsets[0] * scale_x, offsets[1] * scale_y
            screen.blit(img, (render_x + off_x, render_y + off_y))
            return
        # 代替描画（四角形）は簡易化のためスケーリング非対応（または別途実装）
        inst = self._find_equip_inst(self.armor_inventory, self.equipped_armor)
        armor_key = inst.key if inst else ""
        base_color = ARMOR_COLORS.get(armor_key, (120, 120, 120))
        # ... (中略)
        screen.blit(pygame.Surface((36, 22), pygame.SRCALPHA), (draw_x + 14, draw_y + 12)) # Placeholder

    def _draw_shield_overlay(self, screen, draw_x, draw_y, scale_x=1.0, scale_y=1.0, tint_color=None):
        inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield)
        shield_key = inst.key if inst else ""
        is_back = self.facing in ("up", "right")
        
        img = getattr(self, "_shield_images", {}).get(self.facing)
        if img:
            # --- [OPTIMIZED] 盾のスケーリングキャッシュ利用 ---
            _, phase = self.get_breathing_scale()
            cache_key = (img, phase, tint_color, "shield", is_back)
            cached_img = Player._player_scaled_cache.get(cache_key)
            
            if cached_img is None:
                # スケーリング
                w, h = img.get_size()
                scaled = pygame.transform.smoothscale(img, (int(w * scale_x), int(h * scale_y)))
                # 背面なら暗くする
                if is_back:
                    scaled.fill((150, 150, 150), special_flags=pygame.BLEND_RGBA_MULT)
                # 毒などの着色
                if tint_color:
                    scaled.fill((*tint_color, 255), special_flags=pygame.BLEND_RGBA_MULT)
                cached_img = scaled
                Player._player_scaled_cache[cache_key] = cached_img
            
            draw_img = cached_img
            
            shield_data = SHIELD_DATA.get(shield_key, {})
            pos_config = shield_data.get("position", {})
            offsets_dict = pos_config.get("offsets", shield_data.get("offsets", {}))
            offsets = offsets_dict.get(self.facing, (0, 0))
            
            off_x, off_y = offsets[0] * scale_x, offsets[1] * scale_y
            screen.blit(draw_img, (draw_x + off_x, draw_y + off_y))
            return
            
        base_color = SHIELD_COLORS.get(shield_key, (150, 150, 150))
        if is_back:
            # 代替カラーの場合も背面なら暗くする
            base_color = tuple(max(0, int(c * 0.6)) for c in base_color)
            
        w, h = self.width, self.height
        
        # 従来のハードコード値をベースオフセットとし、データの offsets を加算する
        ox, oy = 0, 0
        if self.facing == "down":  ox, oy = -24, 4
        elif self.facing == "up":  ox, oy = 24, -4
        elif self.facing == "left": ox, oy = -10, -12
        elif self.facing == "right": ox, oy = 10, -12
        
        shield_data = SHIELD_DATA.get(shield_key, {})
        pos_config = shield_data.get("position", {})
        offsets_dict = pos_config.get("offsets", shield_data.get("offsets", {}))
        offsets = offsets_dict.get(self.facing, (0, 0))
        final_x = draw_x + w // 2 + ox + offsets[0] - 15
        final_y = draw_y + h // 2 + oy + offsets[1] - 15
        
        surf = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*base_color, 210), (15, 15), 14)
        pygame.draw.circle(surf, (220, 220, 220, 255), (15, 15), 14, 2)
        screen.blit(surf, (final_x, final_y))

    def draw(self, screen, camera_x, camera_y):
        draw_x = self.x - camera_x
        draw_y = self.y - camera_y
        
        # --- 1. アニメーションフレームとスケールの決定 ---
        # 呼吸（スケーリング）の計算（共通メソッドを使用）
        scale_x, scale_y = 1.0, 1.0
        if not self.is_attacking and not self.is_falling:
            scale_x, scale_y = self.get_breathing_scale()
        
        if not self.is_attacking and not self.is_moving and not self.is_falling:
            # 待機中の画像選択 (4フレームサイクル [0, mid, 1, mid])
            total_frames = len(self.walk_images[self.facing])
            # idle_anim_timer は Entity で 60 周期なので 15フレームごとに切り替え
            cycle_step = (self.idle_anim_timer // 15) % total_frames
            img = self.walk_images[self.facing][cycle_step]
        elif self.is_attacking:
            img = self.walk_images[self.facing][0]
        else:
            # 移動中
            from constants import WALK_ANIMATION_SPEED
            total_frames = len(self.walk_images[self.facing])
            step_duration = (WALK_ANIMATION_SPEED * 2) // total_frames
            frame_index = (self.walk_anim_timer // step_duration) % total_frames
            img = self.walk_images[self.facing][frame_index]

        # 毒状態のカラー設定
        poison_tint = None
        if self.condition == "poison":
            from constants import STATUS_EFFECTS
            tint_data = STATUS_EFFECTS.get("poison", {}).get("color_tint", [180, 100, 255])
            if tint_data:
                poison_tint = tuple(tint_data)

        # スケーリングの適用 (攻撃時の拡大は廃止、呼吸エフェクトのみ適用)
        (final_scale_x, final_scale_y), phase = self.get_breathing_scale()
        
        # --- [OPTIMIZED] プレイヤー本体のキャッシュ利用 ---
        cache_key = (img, phase, poison_tint, False)
        cached_img = Player._player_scaled_cache.get(cache_key)
        
        if cached_img is None:
            # スケーリング
            w, h = img.get_size()
            scaled = pygame.transform.smoothscale(img, (int(w * final_scale_x), int(h * final_scale_y)))
            # 着色
            if poison_tint:
                scaled.fill((*poison_tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
            cached_img = scaled
            Player._player_scaled_cache[cache_key] = cached_img
        
        img = cached_img # キャッシュされた画像（スケーリング＆着色済み）を使用

        # 足元を基準に位置を調整
        draw_x += (self.width - img.get_width()) / 2
        draw_y += (self.height - img.get_height())

        if self.is_falling:
            # 落下中（現在の階層で消えていく演出）
            progress = (60 - self.falling_timer) / 60
            scale_fall = max(0.01, 1.0 - progress)
            angle = progress * 720
            base_img = self.walk_images[self.facing][0]
            w, h = int(base_img.get_width() * scale_fall), int(base_img.get_height() * scale_fall)
            if w > 0 and h > 0:
                scaled_img = pygame.transform.smoothscale(base_img, (w, h))
                rotated_img = pygame.transform.rotate(scaled_img, angle)
                rect = rotated_img.get_rect(center=(draw_x + self.width//2, draw_y + self.height//2))
                screen.blit(rotated_img, rect.topleft)
            return

        # 攻撃時のオフセット
        progress = (ATTACK_ANIMATION_FRAMES - self.attack_timer) / ATTACK_ANIMATION_FRAMES if self.is_attacking else 0
        if self.is_attacking:
            offset = 0
            if progress <= 0.3: offset = 40 * (progress / 0.3)
            else: offset = 40 * (1 - (progress - 0.3) / 0.7)
            if self.facing == "up": draw_y -= offset
            elif self.facing == "down": draw_y += offset
            elif self.facing == "left": draw_x -= offset
            elif self.facing == "right": draw_x += offset
        
        # 攻撃時のスケーリング値は上で計算済み
        center_x, center_y = draw_x + (img.get_width() / 2), draw_y + (img.get_height() / 2)
        
        shield_over = {"up": False, "down": True, "left": True, "right": False}.get(self.facing, True)
        
        # 毒状態のカラー設定は冒頭へ移動しました

        # --- 2. 描画実行 ---
        # オーバーレイ描画（鎧・盾）
        # ここで渡す draw_x, draw_y は、スケーリング補正前の「ベースの左上座標」である必要がある
        base_draw_x = self.x - camera_x
        base_draw_y = self.y - camera_y
        if self.is_attacking:
            if self.facing == "up": base_draw_y -= offset
            elif self.facing == "down": base_draw_y += offset
            elif self.facing == "left": base_draw_x -= offset
            elif self.facing == "right": base_draw_x += offset

        if self.equipped_shield and not shield_over:
            self._draw_shield_overlay(screen, base_draw_x, base_draw_y, scale_x=final_scale_x, scale_y=final_scale_y, tint_color=poison_tint)
            
        if self.is_attacking and self.weapon:
            is_over = self.weapon.DRAW_OVER_PLAYER.get(self.facing, False)
            if not is_over: self.weapon.draw_attack(screen, center_x, center_y, self.facing, progress, scale_x=final_scale_x, scale_y=final_scale_y)
        elif self.weapon:
            is_over = self.weapon.DRAW_OVER_PLAYER.get(self.facing, False)
            if not is_over: self.weapon.draw_idle(screen, center_x, center_y, self.facing, scale_x=final_scale_x, scale_y=final_scale_y)
            
        is_visible = True
        if getattr(self, "damage_flash_timer", 0) > HIT_STUN_DURATION:
            if (self.damage_flash_timer - HIT_STUN_DURATION) % 4 < 2: is_visible = False
        
        if is_visible:
            if poison_tint:
                poison_img = img.copy()
                poison_img.fill((*poison_tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
                screen.blit(poison_img, (draw_x, draw_y))
            else:
                screen.blit(img, (draw_x, draw_y))
        
        # 鎧の描画には補正前の base_draw_x を渡す（関数内で再計算するため）。
        if self.equipped_armor: self._draw_armor_overlay(screen, base_draw_x, base_draw_y, scale_x=final_scale_x, scale_y=final_scale_y, tint_color=poison_tint)
        if self.equipped_shield and shield_over:
            self._draw_shield_overlay(screen, base_draw_x, base_draw_y, scale_x=final_scale_x, scale_y=final_scale_y, tint_color=poison_tint)
        
        # --- [NEW] 無敵状態の発光演出 ---
        if self.invincible_turns > 0:
            import math
            # 鼓動するような光の輪
            pulse = (math.sin(pygame.time.get_ticks() / 150) + 1) / 2 # 0.0 to 1.0
            glow_size = int(self.width * (1.1 + pulse * 0.3))
            glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
            alpha = int(100 + pulse * 100)
            pygame.draw.circle(glow_surf, (255, 215, 0, alpha), (glow_size, glow_size), glow_size, 3)
            # 中心の光
            pygame.draw.circle(glow_surf, (255, 255, 200, alpha // 2), (glow_size, glow_size), glow_size // 2)
            screen.blit(glow_surf, (draw_x + self.width // 2 - glow_size, draw_y + self.height // 2 - glow_size))
        
        if self.is_attacking:
            is_over = (self.weapon.DRAW_OVER_PLAYER.get(self.facing, False) if self.weapon else False)
            if is_over and self.weapon: self.weapon.draw_attack(screen, center_x, center_y, self.facing, progress, scale_x=final_scale_x, scale_y=final_scale_y)
        elif self.weapon:
            is_over = self.weapon.DRAW_OVER_PLAYER.get(self.facing, False)
            if is_over: self.weapon.draw_idle(screen, center_x, center_y, self.facing, scale_x=final_scale_x, scale_y=final_scale_y)

    def update_animation(self, dungeon, dialog=None):
        """アニメーション（移動・攻撃）の更新のみを行う"""
        if self.is_falling:
            self.falling_timer -= 1
            return
            
        from constants import ATTACK_ANIMATION_FRAMES
        prev_progress = 0
        if self.is_attacking:
            prev_progress = (ATTACK_ANIMATION_FRAMES - self.attack_timer) / ATTACK_ANIMATION_FRAMES
            
        super().update_animation()
        
        if self.is_attacking:
            new_progress = (ATTACK_ANIMATION_FRAMES - self.attack_timer) / ATTACK_ANIMATION_FRAMES
            if prev_progress < 0.1 <= new_progress:
                self._execute_strike(dungeon, dialog)

    def update(self, dungeon, dialog=None, events=[]):
        """旧来の互換性、および単体更新用のメソッド"""
        self.update_animation(dungeon, dialog)
        from systems.game_state import is_paused, game_state
        if not is_paused() and game_state["turn_state"] == "player":
            self.operate(dungeon, dialog, events)
        game_state["dialog_just_closed"] = False

    def get_item_count(self):
        return len(self.items)

    def get_equipment_count(self):
        return len(self.weapon_inventory) + len(self.armor_inventory) + len(self.shield_inventory)

    def get_stave_count(self):
        return len(self.stave_inventory)

    def get_total_item_count(self):
        return self.get_item_count() + self.get_equipment_count() + self.get_stave_count()

    def add_item_to_inventory(self, item_key, count=1):
        """アイテムをインベントリに追加する（スタック対応）"""
        from constants import CONSUMABLE_DATA
        item_data = CONSUMABLE_DATA.get(item_key, {})
        max_stack = item_data.get("max_stack", 1)

        # 既存のスタックに空きがあるか確認
        if max_stack > 1:
            for item in self.items:
                if item["key"] == item_key and item["count"] < max_stack:
                    can_add = min(count, max_stack - item["count"])
                    item["count"] += can_add
                    count -= can_add
                    if count <= 0: return True
        
        # イベントアイテムの場合は制限なし
        if item_data.get("category") == "event":
            self.event_items.append({"key": item_key, "count": count})
            return True

        # 入り切らない分、または非スタック品を新規スロットに追加
        while count > 0:
            from constants import MAX_ITEM_SLOTS
            if self.get_item_count() >= MAX_ITEM_SLOTS:
                return False
            
            add_count = min(count, max_stack)
            self.items.append({"key": item_key, "count": add_count})
            count -= add_count
            
        return True

    def has_item(self, item_key):
        """指定したキーのアイテムを所持しているか確認する（消耗品）"""
        for item in self.items:
            if item["key"] == item_key and item["count"] > 0:
                return True
        return False

    def remove_item_by_key(self, item_key, count=1):
        """アイテムをインベントリから削除する（スタック対応・イベントアイテム対応）"""
        # 1. 通常アイテムから削除
        for item in self.items:
            if item["key"] == item_key:
                remove_amount = min(count, item["count"])
                item["count"] -= remove_amount
                count -= remove_amount
                if item["count"] <= 0: self.items.remove(item)
                if count <= 0: return True
        
        # 2. まだ足りない場合はイベントアイテムから削除
        for item in self.event_items:
            if item["key"] == item_key:
                remove_amount = min(count, item["count"])
                item["count"] -= remove_amount
                count -= remove_amount
                if item["count"] <= 0: self.event_items.remove(item)
                if count <= 0: return True
        return False

    def add_quest_token(self, enemy_key):
        """討伐トークンを追加し、達成通知があれば返す"""
        if not hasattr(self, "quest_tokens"):
            self.quest_tokens = {}
        self.quest_tokens[enemy_key] = self.quest_tokens.get(enemy_key, 0) + 1
        return self.check_quest_completion(enemy_key)

    def check_quest_completion(self, target_key):
        """特定のキーに関するクエストが達成されたかチェックし、通知用メッセージを返す"""
        for q in self.active_quests:
            if q.get("target_key") == target_key:
                # すでに達成済みとして通知済みならスキップ
                if q.get("_completed_notified"):
                    continue

                # 達成判定
                is_done = False
                if q.get("type") == "hunt":
                    is_done = self.quest_tokens.get(target_key, 0) >= q.get("amount", 1)
                elif q.get("type") == "delivery":
                    # 所持品（通常+イベント）をカウント
                    count = sum(i["count"] for i in self.items if i["key"] == target_key)
                    count += sum(i["count"] for i in self.event_items if i["key"] == target_key)
                    is_done = count >= q.get("amount", 1)
                
                if is_done:
                    q["_completed_notified"] = True
                    # 改行を含めて目立たせる
                    title = q.get("title", "依頼")
                    return f"\n【{title}】を達成した！\n帰還して報告しよう。"
        return ""
    def is_quest_reportable(self, q):
        """指定された依頼が報告可能（達成済み）かチェックする"""
        target_key = q.get("target_key")
        if not target_key:
            # target_key が設定されていないクエストは報告不可（データ不備への安全対策）
            return False
            
        if q.get("type") == "hunt":
            return getattr(self, "quest_tokens", {}).get(target_key, 0) >= q.get("amount", 1)
        elif q.get("type") == "delivery":
            # 通常アイテムとイベントアイテムの両方をチェック
            normal_count = sum(item["count"] for item in self.items if item["key"] == target_key)
            event_count = sum(item["count"] for item in self.event_items if item["key"] == target_key)
            return (normal_count + event_count) >= q.get("amount", 1)
        return False

    def is_any_quest_ready(self):
        """報告可能な依頼が1つでもあるかチェックする"""
        for q in self.active_quests:
            if self.is_quest_reportable(q):
                return True
        return False

    def remove_weapon_by_iid(self, iid):
        target = self._find_equip_inst(self.weapon_inventory, iid)
        if target:
            self.weapon_inventory.remove(target)
            return True
        return False

        return False

    def remove_armor_by_iid(self, iid):
        target = self._find_equip_inst(self.armor_inventory, iid)
        if target:
            self.armor_inventory.remove(target)
            return True
        return False

    def remove_shield_by_iid(self, iid):
        target = self._find_equip_inst(self.shield_inventory, iid)
        if target:
            self.shield_inventory.remove(target)
            return True
        return False

    def _get_weapon_instance(self, weapon_name, enhance=0):
        from components.sprites.weapon import get_weapon_instance
        return get_weapon_instance(weapon_name, enhance)

    def _execute_strike(self, dungeon, dialog=None):
        gx = int((self.x + dungeon.tile_size / 2) // dungeon.tile_size)
        gy = int((self.y + dungeon.tile_size / 2) // dungeon.tile_size)
        
        if self.weapon:
            hit_grids = self.weapon.get_hit_grids(self.facing, gx, gy, dungeon)
        else:
            # 素手：目の前の1マスのみ
            dx, dy = 0, 0
            if self.facing == "up": dy = -1
            elif self.facing == "down": dy = 1
            elif self.facing == "left": dx = -1
            elif self.facing == "right": dx = 1
            hit_grids = [(gx + dx, gy + dy)]

        for (tgx, tgy) in hit_grids:
            # --- 素振りによる罠の発見 ---
            for trap in dungeon.traps:
                if trap.x == tgx and trap.y == tgy and not trap.is_revealed:
                    trap.is_revealed = True
                    print(f"[Trap] Revealed {trap.type} at ({tgx}, {tgy}) by attack.")

            for e in dungeon.enemies:
                if getattr(e, "is_dead", False): continue
                # 敵が占有している全マスを取得
                enemy_grids = e.get_occupied_grids(dungeon.tile_size)
                if (tgx, tgy) in enemy_grids:
                    msg, damage, is_crit, is_miss = deal_damage(self, e)
                    
                    from systems.sound_handler import sound_manager
                    # ミス、またはダメージが0（ブロックなど）の場合はミス音を鳴らす
                    if is_miss or damage == 0:
                        sound_manager.play_sfx(SOUND_ATTACK_MISS)
                    else:
                        sound_manager.play_sfx(SOUND_ATTACK_HIT)

                    if is_crit:
                        dungeon.flash_timer = 10 # 10フレーム発光
                        
                    if dialog:
                        if dialog.is_active:
                            dialog.text += "\n" + msg
                            dialog.auto_close_timer = COMBAT_LOG_WAIT_FRAMES
                        else:
                            from systems.game_state import game_state
                            dialog.text = msg
                            dialog.is_active = True
                            game_state["dialog_modal"] = False
                            dialog.auto_close_timer = COMBAT_LOG_WAIT_FRAMES
                    if self.weapon and not self.weapon.pierce: return
                    elif not self.weapon: return # 素手は非貫通
                    break
    def take_damage(self, amount):
        """ダメージ処理（復活のお守り対応）"""
        from constants import HIT_STUN_DURATION
        self.hp -= amount
        
        # 死亡判定
        if self.hp <= 0:
            if self.has_item("revive_amulet"):
                # 復活のお守りを発動！
                self.remove_item_by_key("revive_amulet")
                self.hp = self.max_hp // 2
                self.is_dead = False
                print(f"[PLAYER] 復活のお守りが砕け、命を繋ぎ止めた！ HP: {self.hp}")
                
                # ダイアログで通知（もし必要なら）
                # ここでは演出としてダメージフラッシュを長めにするなどの対応
                self.damage_flash_timer = 120
            else:
                self.hp = 0
                self.is_dead = True
                print(f"[PLAYER] 力尽きた...")
        else:
            self.damage_flash_timer = 60 + HIT_STUN_DURATION
            print(f"[PLAYER] ダメージ{amount}を受けた！残りHP: {self.hp}")

    def apply_turn_effects(self, dungeon, dialog=None):
        """1ターン終了時の状態異常ダメージと自然回復を処理する"""
        if self.hp <= 0: return

        from constants import STATUS_EFFECTS, COMBAT_LOG_WAIT_FRAMES
        from systems.game_state import game_state

        # 1. 毒ダメージ処理
        if self.condition == "poison":
            p_data = STATUS_EFFECTS.get("poison", {})
            rate = p_data.get("damage_rate", 0.005)
            min_dmg = p_data.get("min_damage", 1)
            
            from systems.math_utils import hardcore_round
            damage = max(min_dmg, hardcore_round(self.max_hp * rate, is_hp=True))
            self.hp = max(1, self.hp - damage) # 毒では死なない仕様（HP1残る）
            print(f"[STATUS] Poison Damage: {damage}, Current HP: {self.hp}/{self.max_hp}, Timer: {self.status_timer}")
            
            # 視覚効果（紫色のフラッシュ）
            from systems.magic_handler import FlashEffect
            dungeon.magic_effects.append(FlashEffect(color=(150, 0, 200), duration=10))
            
            # 持続時間の消化
            self.status_timer -= 1
            
            msg = f"毒のダメージ！ {damage}のダメージを受けた！"
            if self.status_timer <= 0:
                self.condition = "normal"
                msg += "\n毒の持続時間が終わった。毒が消えた！"

            if dialog:
                if dialog.is_active: dialog.text += "\n" + msg
                else:
                    dialog.text = msg
                    dialog.is_active = True
                    game_state["dialog_modal"] = False
                    dialog.auto_close_timer = COMBAT_LOG_WAIT_FRAMES

        # 2. 自然回復処理 (毒状態なら回復しない仕様に変更)
        elif self.hp < self.max_hp:
            base_regen = 0.05
            total_regen = base_regen + self.regen_bonus
            
            self.regen_pool += total_regen
            if self.regen_pool >= 1.0:
                recover_amt = int(self.regen_pool)
                self.hp = min(self.max_hp, self.hp + recover_amt)
                self.regen_pool -= recover_amt

    def process_movement(self):
        """移動完了時の処理（旧自然回復処理を削除し、ターンエンドで一括処理に変更）"""
        return super().process_movement()

    def to_dict(self):
        return {
            "x": self.x, "y": self.y,
            "hp": self.hp, "max_hp": self.max_hp, "coin": self.coin, "bank_coin": getattr(self, "bank_coin", 0), "attack": self.attack,
            "items": [dict(it) for it in self.items],
            "weapon_inventory": [eq.to_dict() for eq in getattr(self, "weapon_inventory", [])],
            "armor_inventory": [eq.to_dict() for eq in getattr(self, "armor_inventory", [])],
            "shield_inventory": [eq.to_dict() for eq in getattr(self, "shield_inventory", [])],
            "equipped_weapon": getattr(self, "equipped_weapon", None),
            "equipped_armor": getattr(self, "equipped_armor", None),
            "equipped_shield": getattr(self, "equipped_shield", None),
            "stave_inventory": [st.to_dict() for st in self.stave_inventory],
            "lantern_inventory": [eq.to_dict() for eq in getattr(self, "lantern_inventory", [])],
            "equipped_lantern": getattr(self, "equipped_lantern", None),
            "invincible_turns": self.invincible_turns,
            "guild_point": getattr(self, "guild_point", 0),
            "guild_rank": getattr(self, "guild_rank", "F"),
            "active_quests": getattr(self, "active_quests", []),
            "quest_tokens": getattr(self, "quest_tokens", {}),
            "completed_fixed_quests": getattr(self, "completed_fixed_quests", []),
            "has_seen_ending": getattr(self, "has_seen_ending", False),
            "warehouse_items": getattr(self, "warehouse_items", []),
            "event_items": getattr(self, "event_items", []),
            "current_floor": getattr(self, "current_floor", 0),
            "prev_floor": getattr(self, "prev_floor", 0),
            "equip_id_counter": globals().get("_equip_id_counter", 0),
        }

    def load_dict(self, data):
        if "x" in data: self.x = data["x"]
        if "y" in data: self.y = data["y"]
        self.hp = int(data.get("hp", self.hp))
        self.max_hp = int(data.get("max_hp", self.max_hp))
        self.coin = int(data.get("coin", self.coin))
        self.bank_coin = int(data.get("bank_coin", 0))
        self.attack = int(data.get("attack", self.attack))
        raw_items = data.get("items", [])
        self.items = []
        if isinstance(raw_items, list):
            for it in raw_items:
                if isinstance(it, dict):
                    # 新形式: {"key": "...", "count": N}
                    self.items.append(dict(it))
                else:
                    # 旧形式: "item_key" (文字列)
                    self.add_item_to_inventory(it)
        elif isinstance(raw_items, dict):
            # さらに古い形式の互換性
            for k, v in raw_items.items():
                self.add_item_to_inventory(k, v)
        self.weapon_inventory = [EquipInstance.from_dict(eq) for eq in data.get("weapon_inventory", [])]
        self.armor_inventory = [EquipInstance.from_dict(eq) for eq in data.get("armor_inventory", [])]
        self.shield_inventory = [EquipInstance.from_dict(eq) for eq in data.get("shield_inventory", [])]
        
        if "equipped_weapon" in data:
            ew = data["equipped_weapon"]
            if ew is not None: self.change_weapon(ew)
            else: self.unequip_weapon()
            
        if "equipped_armor" in data:
            ea = data["equipped_armor"]
            if ea is not None: self.change_armor(ea)
            else: self.unequip_armor()
            
        if "equipped_shield" in data:
            es = data["equipped_shield"]
            if es is not None: self.change_shield(es)
            else: self.unequip_shield()
            
        self.stave_inventory = [StaveInstance.from_dict(st) for st in data.get("stave_inventory", [])]
        self.lantern_inventory = [EquipInstance.from_dict(eq) for eq in data.get("lantern_inventory", [])]
        
        if "equipped_lantern" in data:
            el = data["equipped_lantern"]
            if el is not None: self.change_lantern(el)
            else: self.unequip_lantern()
        self.invincible_turns = int(data.get("invincible_turns", 0))
        self.guild_point = int(data.get("guild_point", 0))
        self.guild_rank = data.get("guild_rank", "F")
        self.active_quests = data.get("active_quests", [])
        # [COMPAT] 古いセーブデータに報酬情報が欠けている場合にデフォルト値で補正する
        for q in self.active_quests:
            if "reward_gold" not in q:
                q["reward_gold"] = 1
            if "reward_gp" not in q:
                q["reward_gp"] = 1
        self.quest_tokens = data.get("quest_tokens", {})
        self.completed_fixed_quests = data.get("completed_fixed_quests", [])
        self.has_seen_ending = data.get("has_seen_ending", False)
        self.warehouse_items = data.get("warehouse_items", [])
        self.event_items = data.get("event_items", [])
        self.current_floor = data.get("current_floor", 0)
        self.prev_floor = data.get("prev_floor", 0)
        
        # 装備IDカウンタの復元
        if "equip_id_counter" in data:
            global _equip_id_counter
            _equip_id_counter = max(_equip_id_counter, data["equip_id_counter"])

    def remove_quest(self, quest):
        """[NEW] クエストを破棄し、関連する証(トークン)もリセットする"""
        if quest in self.active_quests:
            self.active_quests.remove(quest)
            target = quest.get("target_key")
            if target:
                # 他の受注中クエストで同じ対象がないかチェック
                others = [aq for aq in self.active_quests if aq.get("target_key") == target]
                if not others:
                    # 他になければトークンをリセット
                    if target in self.quest_tokens:
                        self.quest_tokens[target] = 0

    def accept_quest(self, quest):
        """[NEW] クエストを受注する（既に受けている場合は何もしない）"""
        if len(self.active_quests) == 0:
            self.active_quests.append(quest)
        else:
            # UI側で既にガードされているはずだが、念のため
            print("[Player] Cannot accept quest: active_quests is not empty.")

    def save_to_file(self, filepath=None):
        if filepath is None:
            from systems.data_loader import SAVE_DATA_PATH
            filepath = SAVE_DATA_PATH
        import json
        print(f"[SYSTEM] Saving progress to {filepath}...")
        
        # セーブ中表示
        screen = pygame.display.get_surface()
        if screen:
            from systems.ui import show_loading_screen
            from wordings import Text
            show_loading_screen(screen, text=Text.UI.SAVING)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def load_from_file(self, filepath=None):
        if filepath is None:
            from constants import SAVE_DATA_PATH
            filepath = SAVE_DATA_PATH
        import json, os
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.load_dict(data)
            return True
        return False