import pygame
import random
import os
from systems.game_state import game_state, is_paused, is_enemy_acting
from components.sprites.entity import Entity
from systems.combat_handler import deal_damage
from systems.tactical_profile import TacticalProfile, get_relation_and_distance
from constants import (
    KEY_MOVE_UP, KEY_MOVE_DOWN, KEY_MOVE_LEFT, KEY_MOVE_RIGHT,
    KEY_ATTACK, KEY_CONFIRM, KEY_MENU, KEY_TURN_ONLY,
    ATTACK_TAME_DURATION, ATTACK_STRIKE_DURATION, ATTACK_ANIMATION_FRAMES, 
    COMBAT_LOG_WAIT_FRAMES, PLAYER_HP, PLAYER_COIN, PLAYER_ATTACK, 
    PLAYER_WEAPON, WEAPON_DATA, PLAYER_DEFENSE, PLAYER_ARMOR, ARMOR_DATA, ARMOR_COLORS,
    PLAYER_SHIELD, SHIELD_DATA, SHIELD_COLORS, PLAYER_ORE, ACCESSORY_DATA,
    MAX_ITEM_SLOTS, MAX_EQUIP_SLOTS, MAX_STAVE_SLOTS, MAX_WAREHOUSE_SLOTS,
    STAVE_DATA, HIT_STUN_DURATION, SOUND_ATTACK_HIT, SOUND_ATTACK_MISS, SOUND_KNOCKBACK,
    ENABLE_DEBUG_LOGGING, PLAYER_MOVE_SPEED, STATUS_EFFECTS,
    PCT_STAT_KEYS
)

# 装備品インスタンス管理用カウンター（ゲーム全体でユニークなID）
_equip_id_counter = 0

def _new_equip_id():
    """新しい装備インスタンスIDを発行して返す"""
    global _equip_id_counter
    _equip_id_counter += 1
    return _equip_id_counter

ORE_STAT_CATEGORIES = {
    "red_stone": {
        "attack_bonus", "accuracy_bonus_close", "accuracy_bonus",
        "crit_rate", "crit_bonus", "armor_penetration"
    },
    "blue_stone": {
        "defense_bonus", "hp_bonus"
    },
    "green_stone": {
        "block_chance_close", "block_chance_ranged", "regen_bonus", "lantern_bonus", "aggro_mod", "pursuit_evasion", "stupidity"
    },
    "purple_stone": {
        "magic_stave_bonus", "magic_light_stave_bonus"
        # 以下は現在未使用（メイジ職廃止のため）。復活する場合はセットに追加するだけでOK:
        # "magic_fire_damage", "magic_fire_range", "magic_heal_ratio",
        # "magic_knockback_damage", "magic_invincible_turns"
    },
    "gold_ore": {
        "attack_bonus", "accuracy_bonus_close", "accuracy_bonus",
        "crit_rate", "crit_bonus", "armor_penetration",
        "defense_bonus", "hp_bonus",
        "block_chance_close", "block_chance_ranged", "regen_bonus", "lantern_bonus", "aggro_mod", "pursuit_evasion", "stupidity",
        "magic_stave_bonus", "magic_light_stave_bonus",
    }
}

SKILL_UPGRADE_MAP = {
    "backstab": ("backstab_crit_bonus", "背後攻撃"),
    "stun": ("stun_proc_chance", "スタン"),
    "counter": ("counter_proc_chance", "カウンター"),
    "knockback": ("knockback_proc_chance", "吹き飛ばし"),
    "lifesteal": ("lifesteal_chance", "ライフスティール"),
}

class EquipInstance:
    def __init__(self, equip_type, key, randomize=False):
        self.iid = _new_equip_id()
        self.equip_type = equip_type
        self.key = key
        self.enhance = 0
        self.stats = {} 

    def get_stat(self, stat_key, default=0):
        data = {}
        if self.equip_type == "weapon": data = WEAPON_DATA.get(self.key, {})
        elif self.equip_type == "armor": data = ARMOR_DATA.get(self.key, {})
        elif self.equip_type == "shield": data = SHIELD_DATA.get(self.key, {})
        elif self.equip_type == "accessory": data = ACCESSORY_DATA.get(self.key, {})
        return data.get(stat_key, default)

    def get_base_upgradeable_stats(self):
        # 装備品が現在持っている（base > 0）かつ、いずれかの系統に属するステータス
        # ただし aggro_mod は負の値（見つかりにくさ）がメリットなので、-1を掛けた値が正であれば強化可能とする
        all_upgradeable_keys = set()
        for cats in ORE_STAT_CATEGORIES.values():
            all_upgradeable_keys.update(cats)
        
        # スキル系キーは鍔冶強化しない
        SKILL_STAT_KEYS = {
            "lifesteal_chance", "lifesteal_ratio",
            "counter_proc_chance", "counter_damage_ratio",
            "stun_proc_chance", "stun_duration",
            "backstab_crit_bonus", "flank_backstab",
        }
        compatible = []
        for k in all_upgradeable_keys:
            if k in SKILL_STAT_KEYS:
                continue
            val = self.get_stat(k, 0)
            if k == "aggro_mod":
                if val * -1 > 0:
                    compatible.append(k)
            else:
                if val > 0:
                    compatible.append(k)
        return compatible

    def get_base_upgradeable_skills(self):
        skill_keys = []
        for skill_name, (stat_key, _) in SKILL_UPGRADE_MAP.items():
            val = self.get_stat(stat_key, 0)
            if val > 0:
                skill_keys.append(skill_name)
        return skill_keys

    def get_skill_upgrade_stat_key(self, skill_name):
        entry = SKILL_UPGRADE_MAP.get(skill_name)
        if not entry:
            return None
        return entry[0]

    def is_ore_compatible(self, ore_key):
        base_stats = self.get_base_upgradeable_stats()
        if not base_stats:
            return False
        if ore_key in ORE_STAT_CATEGORIES:
            allowed_stats = ORE_STAT_CATEGORIES[ore_key]
            return any(k in allowed_stats for k in base_stats)
        return False

    def get_upgradeable_stats_for_ore(self, ore_key):
        base_stats = self.get_base_upgradeable_stats()
        if not base_stats:
            return []
        allowed_stats = ORE_STAT_CATEGORIES.get(ore_key, set())
        return [k for k in base_stats if k in allowed_stats]

    def apply_upgrade(self, stat_key, bonus):
        base_stats = self.get_base_upgradeable_stats()
        skill_stats = self.get_base_upgradeable_skills()
        if not base_stats and not skill_stats:
            return
        
        # 過去データとの互換性のため、既存の enhance 値で初期化
        for k in base_stats:
            if k not in self.stats:
                self.stats[k] = self.enhance
        for skill_name in skill_stats:
            stat_key = self.get_skill_upgrade_stat_key(skill_name)
            if stat_key and stat_key not in self.stats:
                self.stats[stat_key] = self.enhance
        
        if stat_key in self.stats:
            self.stats[stat_key] += bonus
            
        self.enhance += bonus

    def get_enhance_bonus(self, stat_key):
        # その装備品が元々持っていないステータスは、強化しても増えない（常に0）
        base = self.get_stat(stat_key, 0)
        
        # aggro_mod は負の値がメリットなので、-1を掛けて正の値として計算を行う
        is_aggro_mod = (stat_key == "aggro_mod")
        if is_aggro_mod:
            base = base * -1
            
        if base <= 0:
            return 0

        data = {}
        if self.equip_type == "weapon": data = WEAPON_DATA.get(self.key, {})
        elif self.equip_type == "armor": data = ARMOR_DATA.get(self.key, {})
        elif self.equip_type == "shield": data = SHIELD_DATA.get(self.key, {})
        elif self.equip_type == "accessory": data = ACCESSORY_DATA.get(self.key, {})

        growth = data.get("growth")
        if not growth:
            # デフォルト成長設定
            growth = {"bonus_limit": 2, "times_limit": 30, "over_limit_growth_rate": 0.003}

        stat_enhance = self.stats.get(stat_key, 0)  # 該当statがない場合は0
        if stat_enhance == 0:
            return 0

        times_limit = max(1, growth.get("times_limit", 30))
        over_rate   = growth.get("over_limit_growth_rate", 0.003)

        # 固定上限方式：基本値に関係なく一律+10（整数系）または+10%（%系）
        is_pct_stat = stat_key in PCT_STAT_KEYS
        if is_pct_stat:
            growth_room = 0.10  # +10%固定
        else:
            growth_room = 10    # +10固定
        
        per_step      = growth_room / times_limit
        over_per_step = growth_room * over_rate

        # 減衰カーブ方式：最初に大きく上がり、後半は微増
        if stat_enhance <= 10:
            # 1-10回：50%の成長（+5相当）
            bonus = stat_enhance * (growth_room * 0.5 / 10)
        elif stat_enhance <= 20:
            # 11-20回：30%の成長（+3相当）
            bonus = (growth_room * 0.5) + (stat_enhance - 10) * (growth_room * 0.3 / 10)
        elif stat_enhance <= times_limit:
            # 21-30回：20%の成長（+2相当）
            bonus = (growth_room * 0.8) + (stat_enhance - 20) * (growth_room * 0.2 / 10)
        else:
            # 限界超え：微増のみ
            bonus = growth_room + (stat_enhance - times_limit) * over_per_step
            
        # aggro_mod の場合は、計算された正のボーナスに -1 を掛けて負のボーナスとして返す
        if is_aggro_mod:
            return -1 * round(bonus, 3)
            
        return round(bonus, 3)

    def get_name(self):
        base = self.get_stat("name", self.key)
        if self.enhance > 0: return f"{base}+{self.enhance}"
        return base

    def to_dict(self):
        return {"iid": self.iid, "type": self.equip_type, "key": self.key, "enhance": self.enhance, "stats": self.stats}

    @classmethod
    def from_dict(cls, data):
        etype = data["type"]
        ekey = data["key"]
        if etype == "lantern":
            etype = "accessory"
            if ekey in ("basic", "luxury", "none", "basic_lantern", "luxury_lantern", "glowing_ring"):
                ekey = "luminous_gem"
        inst = cls(etype, ekey, randomize=False)
        inst.iid = data.get("iid", inst.iid)
        inst.enhance = data.get("enhance", 0)
        inst.stats = data.get("stats", {})
        global _equip_id_counter
        if inst.iid > _equip_id_counter: _equip_id_counter = inst.iid
        return inst

class StaveInstance:
    def __init__(self, key, charges=5):
        self.iid = _new_equip_id()
        self.key = key
        self.name = STAVE_DATA.get(key, {}).get("name", key)
        self.charges = charges
        self.enhance = 0

    def get_stat(self, stat_key, default=0):
        from constants import STAVE_DATA
        return STAVE_DATA.get(self.key, {}).get(stat_key, default)

    def get_name_with_charges(self): return f"{self.name}[{self.charges}]"
    def get_name(self): return self.name
    def to_dict(self): return {"iid": self.iid, "key": self.key, "charges": self.charges}

    @classmethod
    def from_dict(cls, data):
        inst = cls(data["key"], data.get("charges", 5))
        inst.iid = data.get("iid", inst.iid)
        global _equip_id_counter
        if inst.iid > _equip_id_counter: _equip_id_counter = inst.iid
        return inst

from components.sprites.weapon import OneHanded
from systems.events import active_direction_keys

player_settings = {
    "image_size": (64, 64),
    "speed": PLAYER_MOVE_SPEED,
    "x": 300,
    "y": 220,
}

class Player(Entity):
    _player_scaled_cache = {} 

    @classmethod
    def clear_cache(cls):
        cls._player_scaled_cache = {}

    @property
    def total_attack(self):
        bonus = 0
        weapon_inst = self._find_equip_inst(self.weapon_inventory, self.equipped_weapon)
        if weapon_inst: bonus += weapon_inst.get_stat("attack_bonus", 0) + weapon_inst.get_enhance_bonus("attack_bonus")
        armor_inst = self._find_equip_inst(self.armor_inventory, self.equipped_armor)
        if armor_inst: bonus += armor_inst.get_stat("attack_bonus", 0)
        shield_inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield)
        if shield_inst: bonus += shield_inst.get_stat("attack_bonus", 0)
        accessory_inst = self._find_equip_inst(self.accessory_inventory, self.equipped_accessory)
        if accessory_inst: bonus += accessory_inst.get_stat("attack_bonus", 0)
        
        # 攻撃力バフの加算
        if getattr(self, "attack_buff_turns", 0) > 0:
            bonus += getattr(self, "attack_buff_val", 0)

        val = round(self.attack + bonus, 1)
        return val

    @property
    def max_hp(self):
        bonus = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory, self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("hp_bonus", 0)
        val = int(self._base_max_hp + bonus)
        if getattr(self, "curse_level", 0) > 0:
            reduction = min(0.5, self.curse_level * 0.1)
            val = int(val * (1.0 - reduction))
        return val

    @max_hp.setter
    def max_hp(self, value): self._base_max_hp = value

    @property
    def total_accuracy_close(self):
        from constants import PLAYER_ACCURACY_CLOSE
        base = PLAYER_ACCURACY_CLOSE
        bonus = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory, self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("accuracy_bonus_close", inst.get_stat("accuracy_bonus", 0))
        val = int(base + bonus)
        return val

    @property
    def total_accuracy_ranged(self):
        from constants import PLAYER_ACCURACY_RANGED
        base = PLAYER_ACCURACY_RANGED
        bonus = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory, self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("accuracy_bonus_ranged", inst.get_stat("accuracy_bonus", 0))
        val = int(base + bonus)
        return val

    @property
    def crit_bonus(self):
        bonus = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory, self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst:
                # crit_bonus または crit_rate を取得
                val = inst.get_stat("crit_bonus", inst.get_stat("crit_rate", 0))
                # 小数の場合はそのまま加算（0.1 = 10%）
                if isinstance(val, float) and val < 1.0:
                    bonus += val
                else:
                    # 整数の場合はパーセントとして小数に変換（10 = 10% → 0.1）
                    bonus += val / 100.0
        # 雷霆の秘薬バフ（会心率）の加算（整数を小数に変換）
        if getattr(self, "attack_buff_turns", 0) > 0:
            bonus += getattr(self, "attack_buff_crit", 0) / 100.0
        return bonus

    @property
    def stave_bonus(self):
        bonus = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory, self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("magic_stave_bonus", 0)
        return bonus

    @property
    def total_stupidity(self):
        bonus = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory, self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("stupidity", 0)
        # 暗殺者の秘薬バフ
        if getattr(self, "stealth_buff_turns", 0) > 0:
            bonus += getattr(self, "stealth_buff_stupidity", 0)
        return bonus

    @property
    def total_backstab_crit_bonus(self):
        bonus = 0.0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory, self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("backstab_crit_bonus", 0.0)
        return bonus

    @property
    def total_flank_backstab(self):
        bonus = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory, self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("flank_backstab", 0)
        return bonus

    @property
    def total_backstab(self):
        count = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory, self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: count += inst.get_stat("count_backstab", 0)
        return count

    @property
    def total_stun_proc_chance(self):
        bonus = 0.0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory,  self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("stun_proc_chance", 0.0)
        return bonus

    @property
    def total_stun_duration(self):
        bonus = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory,  self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("stun_duration", 0)
        return bonus

    @property
    def total_stun(self):
        count = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory,  self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: count += inst.get_stat("stun", 0)
        return count

    @property
    def trap_sense(self):
        bonus = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory, self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("trap_sense", 0)
        return bonus

    @property
    def total_lifesteal_chance(self):
        bonus = 0.0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory,  self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("lifesteal_chance", 0.0)
        return bonus

    @property
    def total_lifesteal_ratio(self):
        bonus = 0.0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory,  self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("lifesteal_ratio", 0.0)
        return bonus

    @property
    def total_lifesteal(self):
        count = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory,  self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: count += inst.get_stat("count_lifesteal", 0)
        return count

    @property
    def total_knockback_proc_chance(self):
        bonus = 0.0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory,  self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("knockback_proc_chance", 0.0)
        return bonus

    @property
    def total_knockback_max_distance(self):
        bonus = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory,  self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("knockback_max_distance", 0)
        return bonus

    @property
    def total_knockback(self):
        count = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory,  self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: count += inst.get_stat("count_knockback", 0)
        return count

    @property
    def total_counter_proc_chance(self):
        bonus = 0.0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory,  self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("counter_proc_chance", 0.0)
        return bonus

    @property
    def total_counter_damage_ratio(self):
        bonus = 0.0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory,  self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("counter_damage_ratio", 0.0)
        return bonus

    @property
    def total_counter(self):
        count = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory,  self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: count += inst.get_stat("count_counter", 0)
        return count

    def get_magic_bonus(self, key):
        """装備品の bonus.magic 系ボーナスの合計を返す（例: get_magic_bonus("fire_damage")）
        武器・防具・盾・アクセサリの全装備から合算する。yml側の bonus.magic で制御する。
        """
        total = 0
        flat_key = f"magic_{key}"
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory,  self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory),
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst:
                total += inst.get_stat(flat_key, 0)
        # 賢者の秘薬バフの加算（魔法系効果 key にのみ適用）
        if getattr(self, "magic_buff_turns", 0) > 0 and key in ("fire_damage", "heal_ratio", "knockback_damage", "invincible_turns", "light_stave_bonus"):
            total += getattr(self, "magic_buff_val", 0)
        return total

    @property
    def lantern_bonus(self):
        bonus = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory, self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("lantern_bonus", 0)
        # 暗殺者の秘薬バフ
        if getattr(self, "stealth_buff_turns", 0) > 0:
            bonus += getattr(self, "stealth_buff_lantern", 0)
        return bonus

    @property
    def regen_bonus(self):
        bonus = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory, self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("regen_bonus", 0)
        return bonus
    
    @property
    def total_armor_penetration(self):
        bonus = 0.0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory, self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("armor_penetration", 0.0)
        # 雷霆の秘薬バフ（防御無視）の加算
        if getattr(self, "attack_buff_turns", 0) > 0:
            bonus += getattr(self, "attack_buff_armor_pen", 0.0)
        return bonus
    
    @property
    def total_defense(self):
        bonus = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory, self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: bonus += inst.get_stat("defense_bonus", 0) + inst.get_enhance_bonus("defense_bonus")
        val = round(self.defense + bonus, 1)
        return val

    @property
    def block_chance_close(self):
        total = 0.0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory, self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst:
                total += inst.get_stat("block_chance_close", 0.0) + inst.get_enhance_bonus("block_chance_close")
        return total

    @property
    def block_chance_ranged(self):
        total = 0.0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory, self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst:
                total += inst.get_stat("block_chance_ranged", 0.0) + inst.get_enhance_bonus("block_chance_ranged")
        return total

    def __init__(self):
        super().__init__(x=player_settings["x"], y=player_settings["y"], hp=PLAYER_HP, max_hp=PLAYER_HP, attack=PLAYER_ATTACK, width=64, height=64)
        self._base_max_hp = PLAYER_HP
        self.name = "自分"
        self.coin = PLAYER_COIN
        self.bank_coin = 0
        self.items = []
        self.defense = PLAYER_DEFENSE
        self.armor_inventory = []
        self.equipped_armor = None
        self.shield_inventory = []
        self.equipped_shield = None
        self.accessory_inventory = []
        self.equipped_accessory = None
        self.stave_inventory = []
        self.invincible_turns = 0
        self.attack_buff_turns = 0
        self.attack_buff_val = 0
        self.regen_buff_turns = 0
        self.regen_buff_val = 0
        self.magic_buff_turns = 0
        self.magic_buff_val = 0
        self.stealth_buff_turns = 0
        self.stealth_buff_max_turns = 0
        self.stealth_buff_lantern = 0
        self.stealth_buff_aggro = 0
        self.stealth_buff_pursuit_evasion = 0
        self.stealth_buff_stupidity = 0
        self.regen_pool = 0.0
        self.waving_stave_inst = None
        self._status = "normal"
        self.status_timer = 0
        self.last_item_warned_pos = None
        self._init_images()
        self.current_floor = 0
        self.max_reached_floor = 0
        self.is_falling = False
        self.falling_timer = 0
        self.guild_point = 0
        self.guild_rank = "-"
        self.active_quests = []
        self.quest_tokens = {}
        self.completed_fixed_quests = []
        self.defeated_once_only = []
        self.has_seen_ending = False
        self.dungeon_core_cleared = False
        self.ending_clear_count = 0
        self.new_game_plus_pending = False
        self.event_items = [{"key": "fathers_charm", "count": 1}]
        self.warehouse_items = []
        self.warehouse_max = MAX_WAREHOUSE_SLOTS
        self.outbreak_bonus_active = False # アウトブレイククリア後のGP2倍フラグ
        self.outbreak_reward_mult = 1.0
        self.boss_message_shown = False # ボス発見メッセージ表示済みフラグ
        self.curse_level = 0
        self.cursed_stats = []
        self.shop_bonus_refresh = False  # ミッション達成後にショップ品揃え拡張
        self.shop_seen_special = {}
        self.tactical_profile = TacticalProfile()

        if PLAYER_ARMOR and PLAYER_ARMOR in ARMOR_DATA:
            inst = EquipInstance("armor", PLAYER_ARMOR); self.armor_inventory.append(inst); self._apply_armor(inst)
        if PLAYER_SHIELD and PLAYER_SHIELD in SHIELD_DATA:
            inst = EquipInstance("shield", PLAYER_SHIELD); self.shield_inventory.append(inst); self._apply_shield(inst)
        
        self.weapon_inventory = []; self.equipped_weapon = None; self.weapon = None
        if PLAYER_WEAPON:
            inst = EquipInstance("weapon", PLAYER_WEAPON); self.weapon_inventory.append(inst); self.equipped_weapon = inst.iid
            self.weapon = self._get_weapon_instance(PLAYER_WEAPON, inst.enhance)
        self.move_speed = 300

    def set_current_floor(self, floor):
        self.current_floor = floor
        if floor > self.max_reached_floor:
            self.max_reached_floor = floor

    def _log_duel_trace(self, dungeon, action_type, extra=""):
        boss = self._get_tactical_boss(dungeon)
        if not boss:
            return
        try:
            tile = dungeon.tile_size
            px = int((self.target_x + self.width / 2) // tile)
            py = int((self.target_y + self.height / 2) // tile)
            bx = int((boss.target_x + boss.width / 2) // tile)
            by = int((boss.target_y + boss.height / 2) // tile)
            relation, distance = get_relation_and_distance(self, boss, tile)
            with open("duel_ai.log", "a", encoding="utf-8") as f:
                floor = getattr(dungeon, "current_floor", "?")
                suffix = f" | {extra}" if extra else ""
                f.write(
                    f"[Floor {floor}] [PLAYER] pos=({px},{py}) facing={self.facing} "
                    f"boss=({bx},{by}) relation={relation} distance={distance} "
                    f"action={action_type}{suffix}\n"
                )
        except:
            pass

    def _log_duel_player_input(self, dungeon, action_type, target_tile=None, extra=""):
        suffix_parts = []
        if target_tile is not None:
            suffix_parts.append(f"target=({target_tile[0]},{target_tile[1]})")
        if extra:
            suffix_parts.append(extra)
        self._log_duel_trace(dungeon, action_type, " | ".join(suffix_parts))

    def _get_tactical_boss(self, dungeon):
        if not dungeon:
            return None
        for enemy in getattr(dungeon, "enemies", []):
            if getattr(enemy, "is_dead", False):
                continue
            if getattr(enemy, "type", "") == "dungeon_core":
                return enemy
        return None

    def record_tactical_action(self, dungeon, action_type):
        boss = self._get_tactical_boss(dungeon)
        if not boss:
            return
        relation, distance = get_relation_and_distance(self, boss, dungeon.tile_size)
        self.tactical_profile.record(relation, distance, action_type)
        self._log_duel_trace(dungeon, action_type)

    def _get_tactical_action_for_stave(self, inst):
        effect_type = STAVE_DATA.get(getattr(inst, "key", None), {}).get("effect_type")
        if effect_type == "fire":
            return "magic_fire"
        if effect_type == "knockback":
            return "magic_knockback"
        return "magic"

    def apply_curse(self):
        self.curse_level = min(5, self.curse_level + 1)
        self.cursed_stats = ["hp"] if self.curse_level > 0 else []

    def get_cursed_stats_japanese_single(self, key):
        jp_names = {
            "attack": "攻撃力",
            "defense": "防御力",
            "evasion": "回避率",
            "accuracy": "命中率",
            "hp": "最大HP"
        }
        return jp_names.get(key, key)

    def get_cursed_stats_japanese(self):
        return [self.get_cursed_stats_japanese_single(s) for s in self.cursed_stats]


    @property
    def condition(self): return self._status
    @condition.setter
    def condition(self, value):
        self._status = value
        if value == "poison":
            self.status_timer = random.randint(5, 10)
        elif value == "darkness":
            from constants import STATUS_EFFECTS
            self.status_timer = STATUS_EFFECTS.get("darkness", {}).get("duration", 5)
        else:
            self.status_timer = 0
        
    def _init_images(self):
        import os
        self.walk_images = {}; self.idle_images = {}
        for d in ["down", "left", "right", "up"]:
            frames = {}
            for i in range(2):
                path = f"components/pictures/player/walk/{d}_{i}.png"
                if os.path.exists(path): frames[i] = pygame.image.load(path).convert_alpha()
                elif d == "right":
                    lp = f"components/pictures/player/walk/left_{i}.png"
                    if os.path.exists(lp): frames[i] = pygame.transform.flip(pygame.image.load(lp).convert_alpha(), True, False)
                    else: frames[i] = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                else: frames[i] = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            ip = f"components/pictures/player/walk/{d}_idle.png"
            idf = None
            if os.path.exists(ip): idf = pygame.image.load(ip).convert_alpha()
            elif d == "right":
                lip = f"components/pictures/player/walk/left_idle.png"
                if os.path.exists(lip): idf = pygame.transform.flip(pygame.image.load(lip).convert_alpha(), True, False)
            self.idle_images[d] = idf
            mid = idf if idf else frames[0]
            self.walk_images[d] = [frames[0], mid, frames[1], mid]

    def operate(self, dungeon, dialog=None, events=[]):
        if is_paused() or self.is_moving or self.is_attacking or game_state.get("dialog_just_closed") or is_enemy_acting(dungeon):
            if os.environ.get("DEBUG_MODE") == "1":
                pressed_keys = [e.key for e in events if getattr(e, "type", None) == pygame.KEYDOWN]
                if any(k in pressed_keys for k in (KEY_MOVE_UP, KEY_MOVE_DOWN, KEY_MOVE_LEFT, KEY_MOVE_RIGHT, KEY_MENU)):
                    print(
                        "[INPUT-BLOCK] operate blocked "
                        f"paused={is_paused()} moving={self.is_moving} attacking={self.is_attacking} "
                        f"dialog_just_closed={game_state.get('dialog_just_closed')} "
                        f"enemy_acting={is_enemy_acting(dungeon)} "
                        f"dialog_active={game_state.get('dialog_active')} dialog_modal={game_state.get('dialog_modal')} "
                        f"confirm_active={game_state.get('confirm_active')} menu_active={game_state.get('menu_active')} "
                        f"inventory_active={game_state.get('inventory_active')} status_active={game_state.get('status_active')} "
                        f"enhance_active={game_state.get('enhance_active')} guild_active={game_state.get('guild_active')} "
                        f"shop_active={game_state.get('shop_active')} warehouse_active={game_state.get('warehouse_active')} "
                        f"teleport_active={game_state.get('teleport_active')} "
                        f"pressed={pressed_keys} active_dir={list(active_direction_keys)}"
                    )
            return
        if game_state.get("boss_encounter_pending", False):
            if os.environ.get("DEBUG_MODE") == "1":
                pressed_keys = [e.key for e in events if getattr(e, "type", None) == pygame.KEYDOWN]
                if any(k in pressed_keys for k in (KEY_MOVE_UP, KEY_MOVE_DOWN, KEY_MOVE_LEFT, KEY_MOVE_RIGHT, KEY_MENU)):
                    print(f"[INPUT-BLOCK] boss_encounter_pending pressed={pressed_keys} active_dir={list(active_direction_keys)}")
            return
        turn_consumed = False
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == KEY_ATTACK:
                if dungeon.current_floor == 0 or dungeon.floor_info.get("no_attack", False): break
                self.record_tactical_action(dungeon, "melee")
                px = int((self.target_x + self.width / 2) // dungeon.tile_size)
                py = int((self.target_y + self.height / 2) // dungeon.tile_size)
                face_dx = {"up": 0, "down": 0, "left": -1, "right": 1}.get(self.facing, 0)
                face_dy = {"up": -1, "down": 1, "left": 0, "right": 0}.get(self.facing, 0)
                self._log_duel_player_input(
                    dungeon,
                    "melee_input",
                    target_tile=(px + face_dx, py + face_dy),
                    extra=f"from=({px},{py})",
                )
                self.waving_stave_inst = None; self._perform_attack(); turn_consumed = True; break

        if not turn_consumed:
            lk = active_direction_keys[-1] if active_direction_keys else None
            if lk:
                keys = pygame.key.get_pressed()
                is_turning = keys[KEY_TURN_ONLY] or (KEY_TURN_ONLY == pygame.K_LSHIFT and keys[pygame.K_RSHIFT])
                dx, dy = 0, 0
                if lk == KEY_MOVE_LEFT: self.set_facing("left"); dx = -dungeon.tile_size
                elif lk == KEY_MOVE_RIGHT: self.set_facing("right"); dx = dungeon.tile_size
                elif lk == KEY_MOVE_UP: self.set_facing("up"); dy = -dungeon.tile_size
                elif lk == KEY_MOVE_DOWN: self.set_facing("down"); dy = dungeon.tile_size
                if is_turning: return
                tx, ty = self.x + dx, self.y + dy
                if self.can_move_grid(tx, ty, dungeon):
                    self.record_tactical_action(dungeon, "move")
                    self._log_duel_player_input(
                        dungeon,
                        "move_input",
                        target_tile=(int((tx + self.width / 2) // dungeon.tile_size), int((ty + self.height / 2) // dungeon.tile_size)),
                        extra=f"from=({int((self.x + self.width / 2) // dungeon.tile_size)},{int((self.y + self.height / 2) // dungeon.tile_size)})",
                    )
                    self.prev_x, self.prev_y = self.x, self.y; self.target_x, self.target_y = tx, ty; self.is_moving = True
                    dungeon.reveal_area(tx // dungeon.tile_size, ty // dungeon.tile_size)
                    self.step_toggle = not self.step_toggle; turn_consumed = True
                    
        if turn_consumed:
            messages = []
            if self.invincible_turns > 0:
                self.invincible_turns -= 1
                if self.invincible_turns == 0:
                    messages.append("無敵状態が 切れた！")
            if getattr(self, "attack_buff_turns", 0) > 0:
                self.attack_buff_turns -= 1
                if self.attack_buff_turns == 0:
                    messages.append("攻撃力上昇の効果が 切れた！")
            if getattr(self, "regen_buff_turns", 0) > 0:
                self.regen_buff_turns -= 1
                if self.regen_buff_turns == 0:
                    messages.append("自然回復上昇の効果が 切れた！")
            if getattr(self, "magic_buff_turns", 0) > 0:
                self.magic_buff_turns -= 1
                if self.magic_buff_turns == 0:
                    # 杖の回復分を差し引く（スナップショットに基づき元に戻す、0未満にはしない）
                    snapshot = getattr(self, "_sage_stave_snapshot", {})
                    if snapshot:
                        for stave in getattr(self, "stave_inventory", []):
                            if stave.iid in snapshot:
                                stave.charges = max(0, min(stave.charges, snapshot[stave.iid]))
                        # 倉庫に預けた杖の回数も復元
                        for item in getattr(self, "warehouse_items", []):
                            if item.get("type") == "stave_inst":
                                data = item.get("data", {})
                                iid = data.get("iid")
                                if iid in snapshot:
                                    data["charges"] = max(0, min(data.get("charges", 0), snapshot[iid]))
                        self._sage_stave_snapshot = {}
                    messages.append("魔法強化の効果が 切れた！")
            if getattr(self, "stealth_buff_turns", 0) > 0:
                self.stealth_buff_turns -= 1
                if self.stealth_buff_turns == 0:
                    messages.append("暗殺者の秘薬の効果が 切れた！")
                    self.stealth_buff_stupidity = 0
                    self.stealth_buff_lantern = 0
                    self.stealth_buff_aggro = 0
                    self.stealth_buff_pursuit_evasion = 0
            
            if messages and dialog:
                msg = "\n".join(messages)
                if dialog.is_active: dialog.text += "\n" + msg
                else: dialog.text = msg; dialog.is_active = True; game_state["dialog_modal"] = False; dialog.auto_close_timer = COMBAT_LOG_WAIT_FRAMES

            if self.is_moving: self.start_enemy_turn(dungeon)
            else: self.enemy_turn_pending = True

    def start_enemy_turn(self, dungeon):
        game_state["turn_state"] = "enemies"; game_state["current_enemy_idx"] = 0; self.enemy_turn_pending = False
        for enemy in dungeon.enemies: enemy.has_acted = False
        all_ents = [self] + dungeon.enemies
        occs = set((int((e.target_x + e.width/2)//dungeon.tile_size), int((e.target_y + e.height/2)//dungeon.tile_size)) for e in all_ents if not getattr(e, "is_dead", False))
        game_state["occupied_cells"] = occs; game_state["all_entities_cache"] = all_ents
        self._log_duel_player_input(
            dungeon,
            "enemy_turn_start",
            target_tile=(int((self.target_x + self.width / 2) // dungeon.tile_size), int((self.target_y + self.height / 2) // dungeon.tile_size)),
            extra=f"is_moving={self.is_moving}",
        )

    def _perform_attack(self):
        self.is_attacking = True; self.attack_timer = ATTACK_ANIMATION_FRAMES
        from systems.sound_handler import sound_manager
        if self.waving_stave_inst: sound_manager.play_sfx(STAVE_DATA.get(self.waving_stave_inst.key, {}).get("sound"))
        elif self.weapon: sound_manager.play_sfx(self.weapon.data.get("sound"))

    def _perform_wave(self, inst, dungeon, dialog):
        self.record_tactical_action(dungeon, self._get_tactical_action_for_stave(inst))
        px = int((self.target_x + self.width / 2) // dungeon.tile_size)
        py = int((self.target_y + self.height / 2) // dungeon.tile_size)
        face_dx = {"up": 0, "down": 0, "left": -1, "right": 1}.get(self.facing, 0)
        face_dy = {"up": -1, "down": 1, "left": 0, "right": 0}.get(self.facing, 0)
        self._log_duel_player_input(
            dungeon,
            f"stave_input:{getattr(inst, 'key', 'unknown')}",
            target_tile=(px + face_dx, py + face_dy),
            extra=f"from=({px},{py})",
        )
        self.waving_stave_inst = inst
        self.is_attacking = True
        self.attack_timer = ATTACK_ANIMATION_FRAMES
        # 🎵 SE再生（_perform_attack を呼んでも良いが、明示的にここで再生）
        from systems.sound_handler import sound_manager
        from constants import STAVE_DATA
        sound_path = STAVE_DATA.get(inst.key, {}).get("sound")
        if sound_path: sound_manager.play_sfx(sound_path)
        # 杖を振った瞬間にターン消費を確定させる（operateの外で呼ばれるため）
        self.enemy_turn_pending = True

    def _find_equip_inst(self, inv, iid):
        for it in inv:
            if it.iid == iid: return it
        return None

    def _find_stave_inst(self, iid):
        return self._find_equip_inst(self.stave_inventory, iid)

    def update_equipment_stats(self):
        if self.equipped_weapon:
            inst = self._find_equip_inst(self.weapon_inventory, self.equipped_weapon)
            if inst: self.weapon = self._get_weapon_instance(inst.key, inst.enhance)
        if self.equipped_armor:
            inst = self._find_equip_inst(self.armor_inventory, self.equipped_armor)
            if inst: self._apply_armor(inst)

    def change_weapon(self, iid):
        inst = self._find_equip_inst(self.weapon_inventory, iid)
        if inst:
            nw = self._get_weapon_instance(inst.key, inst.enhance)
            if nw:
                self.equipped_weapon = inst.iid
                self.weapon = nw
                self._clamp_hp_to_max()

    def set_facing(self, direction):
        if self.facing != direction: self.facing = direction; self.walk_anim_timer = 0

    def equip_weapon_by_key(self, wk, enhance=0, stats=None):
        if wk not in WEAPON_DATA or self.get_equipment_count() >= MAX_EQUIP_SLOTS: return None
        inst = EquipInstance("weapon", wk)
        if enhance > 0:
            inst.enhance = enhance
        if stats:
            inst.stats = stats.copy()
        self.weapon_inventory.append(inst)
        return inst

    def equip_armor_by_key(self, ak, enhance=0, stats=None):
        if ak not in ARMOR_DATA or self.get_equipment_count() >= MAX_EQUIP_SLOTS: return None
        inst = EquipInstance("armor", ak)
        if enhance > 0:
            inst.enhance = enhance
        if stats:
            inst.stats = stats.copy()
        self.armor_inventory.append(inst)
        return inst

    def equip_shield_by_key(self, sk, enhance=0, stats=None):
        if sk not in SHIELD_DATA or self.get_equipment_count() >= MAX_EQUIP_SLOTS: return None
        inst = EquipInstance("shield", sk)
        if enhance > 0:
            inst.enhance = enhance
        if stats:
            inst.stats = stats.copy()
        self.shield_inventory.append(inst)
        return inst

    def equip_accessory_by_key(self, lk, enhance=0, stats=None):
        from constants import ACCESSORY_DATA
        if lk not in ACCESSORY_DATA or self.get_equipment_count() >= MAX_EQUIP_SLOTS: return None
        inst = EquipInstance("accessory", lk)
        if enhance > 0:
            inst.enhance = enhance
        if stats:
            inst.stats = stats.copy()
        self.accessory_inventory.append(inst)
        return inst

    def _remove_from_inv(self, inv, iid):
        inst = self._find_equip_inst(inv, iid)
        if inst: inv.remove(inst); return True
        return False

    def remove_weapon_by_iid(self, iid): return self._remove_from_inv(self.weapon_inventory, iid)
    def remove_armor_by_iid(self, iid): return self._remove_from_inv(self.armor_inventory, iid)
    def remove_shield_by_iid(self, iid): return self._remove_from_inv(self.shield_inventory, iid)
    def remove_stave_by_iid(self, iid): return self._remove_from_inv(self.stave_inventory, iid)
    def remove_accessory_by_iid(self, iid): return self._remove_from_inv(self.accessory_inventory, iid)

    def change_armor(self, iid):
        inst = self._find_equip_inst(self.armor_inventory, iid)
        if inst and inst.key in ARMOR_DATA:
            self._apply_armor(inst)
            self._clamp_hp_to_max()

    def change_shield(self, iid):
        inst = self._find_equip_inst(self.shield_inventory, iid)
        if inst:
            self._apply_shield(inst)
            self._clamp_hp_to_max()

    def _apply_shield(self, inst):
        self.equipped_shield = inst.iid; data = SHIELD_DATA.get(inst.key)
        if not data: return
        self._shield_images = {}; import os
        img_dir = data.get("image_dir", "")
        if img_dir and os.path.exists(img_dir):
            from systems.resources import load_image
            shared = None
            for c in ["down.png", "left.png", "shield.png", f"{inst.key}.png"]:
                p = os.path.join(img_dir, c); raw = load_image(p)
                if raw: shared = pygame.transform.scale(raw, (self.width, self.height)); break
            for d in ("down", "left", "up"):
                r = load_image(f"{img_dir}/{d}.png")
                if r:
                    self._shield_images[d] = pygame.transform.scale(r, (self.width, self.height))
                elif shared:
                    self._shield_images[d] = shared
            if "left" in self._shield_images:
                self._shield_images["right"] = pygame.transform.flip(self._shield_images["left"], True, False)
            elif shared:
                self._shield_images["right"] = shared
            if "down" in self._shield_images and "up" not in self._shield_images:
                self._shield_images["up"] = self._shield_images["down"]

    def _apply_armor(self, inst):
        self.equipped_armor = inst.iid; data = ARMOR_DATA.get(inst.key)
        if not data: self.defense = PLAYER_DEFENSE; return
        self._armor_images = {}; import os
        img_dir = data.get("image_dir", "")
        if img_dir and os.path.exists(img_dir):
            from systems.resources import load_image
            shared = None
            for c in ["down.png", "left.png", "armor.png", f"{inst.key}.png"]:
                p = os.path.join(img_dir, c); raw = load_image(p)
                if raw: shared = pygame.transform.scale(raw, (self.width, self.height)); break
            for d in ("down", "left", "up"):
                r = load_image(f"{img_dir}/{d}.png")
                if r:
                    self._armor_images[d] = pygame.transform.scale(r, (self.width, self.height))
                elif shared:
                    self._armor_images[d] = shared
            if "left" in self._armor_images:
                self._armor_images["right"] = pygame.transform.flip(self._armor_images["left"], True, False)
            elif shared:
                self._armor_images["right"] = shared
            if "down" in self._armor_images and "up" not in self._armor_images:
                self._armor_images["up"] = self._armor_images["down"]

    def _clamp_hp_to_max(self):
        """現在HPが最大HPを超えている場合、最大HPに収める"""
        if self.hp > self.max_hp:
            self.hp = self.max_hp

    def unequip_weapon(self):
        self.equipped_weapon = None
        self.weapon = None
        self._clamp_hp_to_max()

    def unequip_armor(self):
        self.equipped_armor = None
        self._armor_images = {}
        self._clamp_hp_to_max()

    def unequip_shield(self):
        self.equipped_shield = None
        self._shield_images = {}
        self._clamp_hp_to_max()

    def change_accessory(self, iid):
        inst = self._find_equip_inst(self.accessory_inventory, iid)
        if inst:
            self.equipped_accessory = inst.iid
            self._clamp_hp_to_max()

    def get_aggro_modifier(self):
        mod = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory, self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst: mod += inst.get_stat("aggro_mod", 0) + inst.get_enhance_bonus("aggro_mod")
        # 暗殺者の秘薬バフ
        if getattr(self, "stealth_buff_turns", 0) > 0:
            mod += getattr(self, "stealth_buff_aggro", 0)
        return mod

    def get_pursuit_evasion(self):
        bonus = 0
        for inv, eid in [
            (self.weapon_inventory, self.equipped_weapon),
            (self.armor_inventory, self.equipped_armor),
            (self.shield_inventory, self.equipped_shield),
            (self.accessory_inventory, self.equipped_accessory)
        ]:
            inst = self._find_equip_inst(inv, eid)
            if inst:
                bonus += inst.get_stat("pursuit_evasion", 0) + inst.get_enhance_bonus("pursuit_evasion")
        if getattr(self, "stealth_buff_turns", 0) > 0:
            bonus += getattr(self, "stealth_buff_pursuit_evasion", 0)
        return bonus

    def unequip_accessory(self):
        self.equipped_accessory = None
        self._clamp_hp_to_max()

    def reset_status(self): self.is_moving = self.is_attacking = self.is_falling = False

    def draw(self, screen, camera_x, camera_y):
        draw_x, draw_y = self.x - camera_x, self.y - camera_y
        sx, sy = self.get_breathing_scale() if not (self.is_attacking or self.is_falling) else (1.0, 1.0)
        if not self.is_attacking and not self.is_moving and not self.is_falling:
            img = self.walk_images[self.facing][(self.idle_anim_timer // 15) % len(self.walk_images[self.facing])]
        elif self.is_attacking: img = self.walk_images[self.facing][0]
        else:
            from constants import WALK_ANIMATION_SPEED
            td = (WALK_ANIMATION_SPEED * 2) // len(self.walk_images[self.facing])
            img = self.walk_images[self.facing][(self.walk_anim_timer // td) % len(self.walk_images[self.facing])]

        player_alpha = 255
        if getattr(self, "curse_level", 0) > 0:
            player_alpha = max(60, 255 - int(self.curse_level * 39))

        poison_tint = tuple(STATUS_EFFECTS.get("poison", {}).get("color_tint", [180, 100, 255])) if self.condition == "poison" else None
        (fsx, fsy), phase = self.get_breathing_scale()
        ck = (img, phase, poison_tint, False, player_alpha)
        cached = Player._player_scaled_cache.get(ck)
        if cached is None:
            w, h = img.get_size(); scaled = pygame.transform.smoothscale(img, (int(w * fsx), int(h * fsy)))
            if poison_tint: scaled.fill((*poison_tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
            if player_alpha < 255:
                scaled.set_alpha(player_alpha)
            cached = scaled; Player._player_scaled_cache[ck] = cached
        img = cached; draw_x += (self.width - img.get_width()) / 2; draw_y += (self.height - img.get_height())

        if self.is_falling:
            prog = (60 - self.falling_timer) / 60; sfall = max(0.01, 1.0 - prog); ang = prog * 720
            bimg = self.walk_images[self.facing][0]; w, h = int(bimg.get_width() * sfall), int(bimg.get_height() * sfall)
            if w > 0 and h > 0:
                simg = pygame.transform.smoothscale(bimg, (w, h)); rimg = pygame.transform.rotate(simg, ang)
                if player_alpha < 255:
                    rimg.set_alpha(player_alpha)
                screen.blit(rimg, rimg.get_rect(center=(draw_x + self.width//2, draw_y + self.height//2)).topleft)
            return

        off = 0
        if self.is_attacking:
            prog = (ATTACK_ANIMATION_FRAMES - self.attack_timer) / ATTACK_ANIMATION_FRAMES
            off = 40 * (prog / 0.3) if prog <= 0.3 else 40 * (1 - (prog - 0.3) / 0.7)
            if self.facing == "up": draw_y -= off
            elif self.facing == "down": draw_y += off
            elif self.facing == "left": draw_x -= off
            elif self.facing == "right": draw_x += off
        
        cx, cy = draw_x + img.get_width()/2, draw_y + img.get_height()/2
        bdx, bdy = self.x - camera_x, self.y - camera_y
        if self.is_attacking:
            if self.facing == "up": bdy -= off
            elif self.facing == "down": bdy += off
            elif self.facing == "left": bdx -= off
            elif self.facing == "right": bdx += off

        so = {"up": False, "down": True, "left": True, "right": False}.get(self.facing, True)
        if self.equipped_shield and not so: self._draw_shield_overlay(screen, bdx, bdy, scale_x=fsx, scale_y=fsy, tint_color=poison_tint, alpha=player_alpha)
        if self.weapon:
            over = self.weapon.DRAW_OVER_PLAYER.get(self.facing, False)
            if not over:
                if self.is_attacking: self.weapon.draw_attack(screen, cx, cy, self.facing, prog, scale_x=fsx, scale_y=fsy, alpha=player_alpha)
                else: self.weapon.draw_idle(screen, cx, cy, self.facing, scale_x=fsx, scale_y=fsy, alpha=player_alpha)
        
        is_v = not (getattr(self, "damage_flash_timer", 0) > HIT_STUN_DURATION and (self.damage_flash_timer - HIT_STUN_DURATION) % 4 < 2)
        if is_v: screen.blit(img, (draw_x, draw_y))
        if self.equipped_armor: self._draw_armor_overlay(screen, bdx, bdy, scale_x=fsx, scale_y=fsy, tint_color=poison_tint, alpha=player_alpha)
        if self.equipped_shield and so: self._draw_shield_overlay(screen, bdx, bdy, scale_x=fsx, scale_y=fsy, tint_color=poison_tint, alpha=player_alpha)
        if self.invincible_turns > 0:
            import math; p = (math.sin(pygame.time.get_ticks()/150)+1)/2; gs = int(self.width*(1.1+p*0.3)); gsf = pygame.Surface((gs*2,gs*2), pygame.SRCALPHA)
            a = int(100+p*100); pygame.draw.circle(gsf, (255,215,0,a), (gs,gs), gs, 3); pygame.draw.circle(gsf, (255,255,200,a//2), (gs,gs), gs//2)
            screen.blit(gsf, (draw_x+self.width//2-gs, draw_y+self.height//2-gs))
        # 秘薬バフパーティクル（サークルエフェクトは削除し、各バフ色に合わせた泡のみを表示）
        has_any_buff = False
        buff_color = None
        if getattr(self, "attack_buff_turns", 0) > 0:
            has_any_buff = True
            buff_color = (231, 76, 60)    # 赤：戦士
        elif getattr(self, "regen_buff_turns", 0) > 0:
            has_any_buff = True
            buff_color = (46, 204, 113)   # 緑：巡礼
        elif getattr(self, "magic_buff_turns", 0) > 0:
            has_any_buff = True
            buff_color = (155, 89, 182)   # 紫：賢者
        elif getattr(self, "stealth_buff_turns", 0) > 0:
            has_any_buff = True
            buff_color = (60, 60, 80)     # 暗灰：暗殺者

        if has_any_buff:
            import math
            import random
            if not hasattr(self, "buff_particles"):
                self.buff_particles = []
            if random.random() < 0.15:
                px = random.randint(-15, 15)
                py = random.randint(10, 30)
                self.buff_particles.append({
                    "rel_x": px,
                    "rel_y": py,
                    "age": 0,
                    "max_age": random.randint(30, 50),
                    "speed": random.uniform(0.5, 1.2),
                    "size": random.randint(2, 4),
                    "color": buff_color
                })

        if hasattr(self, "buff_particles") and self.buff_particles:
            import math
            for p in self.buff_particles[:]:
                p["age"] += 1
                if p["age"] >= p["max_age"]:
                    self.buff_particles.remove(p)
                    continue
                p["rel_y"] -= p["speed"]
                p["rel_x"] += math.sin(p["age"] / 5) * 0.3
                alpha = int(200 * (1.0 - p["age"] / p["max_age"]))
                p_surf = pygame.Surface((p["size"] * 2, p["size"] * 2), pygame.SRCALPHA)
                col = p.get("color", (255, 255, 255))
                pygame.draw.circle(p_surf, (col[0], col[1], col[2], alpha), (p["size"], p["size"]), p["size"])
                screen.blit(p_surf, (draw_x + self.width // 2 + p["rel_x"] - p["size"], draw_y + self.height // 2 + p["rel_y"] - p["size"]))
        if self.weapon:
            over = self.weapon.DRAW_OVER_PLAYER.get(self.facing, False)
            if over:
                if self.is_attacking: self.weapon.draw_attack(screen, cx, cy, self.facing, prog, scale_x=fsx, scale_y=fsy, alpha=player_alpha)
                else: self.weapon.draw_idle(screen, cx, cy, self.facing, scale_x=fsx, scale_y=fsy, alpha=player_alpha)

    def _draw_armor_overlay(self, screen, bdx, bdy, scale_x=1.0, scale_y=1.0, tint_color=None, alpha=255):
        if not self.equipped_armor or not hasattr(self, "_armor_images"): return
        img = self._armor_images.get(self.facing)
        if not img: return
        
        # マスターデータからオフセットを取得
        from constants import ARMOR_DATA, ARMOR_CATEGORIES
        inst = self._find_equip_inst(self.armor_inventory, self.equipped_armor)
        data = ARMOR_DATA.get(inst.key, {}) if inst else {}
        cat_data = ARMOR_CATEGORIES.get(data.get("category"), {})
        offsets = cat_data.get("position", {}).get("offsets", {}).get(self.facing, (0, 0))

        (fsx, fsy), phase = self.get_breathing_scale()
        ck = (img, phase, tint_color, False, alpha)
        cached = Player._player_scaled_cache.get(ck)
        if cached is None:
            w, h = img.get_size(); scaled = pygame.transform.smoothscale(img, (int(w * fsx), int(h * fsy)))
            if tint_color: scaled.fill((*tint_color, 255), special_flags=pygame.BLEND_RGBA_MULT)
            if alpha < 255:
                scaled.set_alpha(alpha)
            cached = scaled; Player._player_scaled_cache[ck] = cached
        
        # オフセットを適用して描画
        off_x = (self.width - cached.get_width()) / 2 + offsets[0]
        off_y = (self.height - cached.get_height()) + offsets[1]
        screen.blit(cached, (bdx + off_x, bdy + off_y))

    def _draw_shield_overlay(self, screen, bdx, bdy, scale_x=1.0, scale_y=1.0, tint_color=None, alpha=255):
        if not self.equipped_shield or not hasattr(self, "_shield_images"): return
        img = self._shield_images.get(self.facing)
        if not img: return
        
        # マスターデータからオフセットを取得
        from constants import SHIELD_DATA, SHIELD_CATEGORIES
        inst = self._find_equip_inst(self.shield_inventory, self.equipped_shield)
        data = SHIELD_DATA.get(inst.key, {}) if inst else {}
        cat_data = SHIELD_CATEGORIES.get(data.get("category"), {})
        offsets = cat_data.get("position", {}).get("offsets", {}).get(self.facing, (0, 0))
        is_back = self.facing in ("up", "right")

        (fsx, fsy), phase = self.get_breathing_scale()
        ck = (img, phase, tint_color, is_back, alpha) # is_backとalphaをキャッシュキーに追加
        cached = Player._player_scaled_cache.get(ck)
        if cached is None:
            w, h = img.get_size(); scaled = pygame.transform.smoothscale(img, (int(w * fsx), int(h * fsy)))
            if is_back: scaled.fill((150, 150, 150), special_flags=pygame.BLEND_RGBA_MULT)
            if tint_color: scaled.fill((*tint_color, 255), special_flags=pygame.BLEND_RGBA_MULT)
            if alpha < 255:
                scaled.set_alpha(alpha)
            cached = scaled; Player._player_scaled_cache[ck] = cached
        
        # オフセットを適用して描画
        off_x = (self.width - cached.get_width()) / 2 + offsets[0]
        off_y = (self.height - cached.get_height()) + offsets[1]
        screen.blit(cached, (bdx + off_x, bdy + off_y))


    def update_animation(self, dungeon, dt=1/60, dialog=None):
        if self.is_falling: self.falling_timer -= 1; return
        prev_prog = (ATTACK_ANIMATION_FRAMES - self.attack_timer) / ATTACK_ANIMATION_FRAMES if self.is_attacking else 0
        super().update_animation(dt)
        if self.is_attacking:
            new_prog = (ATTACK_ANIMATION_FRAMES - self.attack_timer) / ATTACK_ANIMATION_FRAMES
            if prev_prog < 0.1 <= new_prog:
                if self.waving_stave_inst:
                    print(f"[STAVE-DEBUG] Executing stave at animation time: {self.waving_stave_inst}")
                    from systems.magic_handler import execute_stave
                    try:
                        msg = execute_stave(self, self.waving_stave_inst, dungeon, dialog)
                        print(f"[STAVE-DEBUG] Stave execution result: {msg}")
                        if dialog:
                            if dialog.is_active: dialog.text += "\n" + msg
                            else: dialog.text = msg; dialog.is_active = True
                    except Exception as e:
                        print(f"[STAVE-DEBUG] Exception in execute_stave: {e}")
                        import traceback
                        traceback.print_exc()
                        if dialog:
                            if dialog.is_active: dialog.text += "\n杖の使用でエラーが発生しました！"
                            else: dialog.text = "杖の使用でエラーが発生しました！"; dialog.is_active = True
                else:
                    self._execute_strike(dungeon, dialog)

    def update(self, dungeon, dt=1/60, dialog=None, events=[]):
        self.current_dungeon = dungeon
        if self.is_falling: self.falling_timer -= 1; return
        if not is_paused() and game_state["turn_state"] == "player": self.operate(dungeon, dialog, events)
        self.update_animation(dungeon, dt, dialog)
        is_any_dmg = any(e.damage_flash_timer > 0 for e in dungeon.enemies)
        if (not is_paused() and not self.is_attacking and not self.is_moving and not (dialog and dialog.is_active) and not is_any_dmg and getattr(self, "enemy_turn_pending", False)):
            self.start_enemy_turn(dungeon)
        game_state["dialog_just_closed"] = False

    def get_total_item_count(self): return len(self.items) + self.get_equipment_count() + len(self.stave_inventory)
    def get_equipment_count(self): return len(self.weapon_inventory) + len(self.armor_inventory) + len(self.shield_inventory) + len(self.accessory_inventory)
    def get_stave_count(self): return len(self.stave_inventory)
    def get_item_count(self): return len(self.items)

    def add_item_to_inventory(self, ik, count=1):
        from constants import CONSUMABLE_DATA
        data = CONSUMABLE_DATA.get(ik, {}); ms = data.get("max_stack", 1)
        if ms > 1:
            for it in self.items:
                if it["key"] == ik and it["count"] < ms:
                    add = min(count, ms - it["count"]); it["count"] += add; count -= add
                    if count <= 0: return True
        if data.get("category") == "event": 
            self.event_items.append({"key": ik, "count": count})
            return True
        while count > 0:
            if len(self.items) >= MAX_ITEM_SLOTS: 
                return False
            add = min(count, ms); self.items.append({"key": ik, "count": add}); count -= add
        return True

    def add_stave_to_inventory(self, sk, charges=5):
        if len(self.stave_inventory) >= MAX_STAVE_SLOTS: return False
        inst = StaveInstance(sk, charges); self.stave_inventory.append(inst); return True

    def equip_stave_by_key(self, sk, charges=5):
        return self.add_stave_to_inventory(sk, charges)

    def add_equipment_to_inventory(self, ek, etype):
        if self.get_equipment_count() >= MAX_EQUIP_SLOTS: return False
        inst = EquipInstance(etype, ek); inv = {"weapon":self.weapon_inventory,"armor":self.armor_inventory,"shield":self.shield_inventory,"accessory":self.accessory_inventory}.get(etype)
        if inv is not None: inv.append(inst); return True
        return False

    def has_item(self, ik):
        for it in self.items:
            if it["key"] == ik and it["count"] > 0: return True
        return False

    def remove_item_by_key(self, ik, count=1):
        # 1. 消耗品とイベントアイテムから削除
        for inv in [self.items, self.event_items]:
            for it in inv[:]:
                if it["key"] == ik:
                    rem = min(count, it["count"]); it["count"] -= rem; count -= rem
                    if it["count"] <= 0: inv.remove(it)
                    if count <= 0: return True
        
        # 2. 杖・装備品から削除
        # インベントリに対応する属性名と解除メソッドの定義
        mapping = [
            (self.stave_inventory, None, None),
            (self.weapon_inventory, "equipped_weapon", self.unequip_weapon),
            (self.armor_inventory, "equipped_armor", self.unequip_armor),
            (self.shield_inventory, "equipped_shield", self.unequip_shield),
            (self.accessory_inventory, "equipped_accessory", self.unequip_accessory)
        ]

        for inv, slot_attr, unequip_method in mapping:
            # 優先度1: 装備していないものを先に削除
            non_equipped = []
            for inst in inv:
                if hasattr(inst, "key") and inst.key == ik:
                    is_equipped = (slot_attr and getattr(self, slot_attr) == inst.iid)
                    if not is_equipped:
                        non_equipped.append(inst)
            
            for inst in non_equipped:
                inv.remove(inst); count -= 1
                if count <= 0: return True
            
            # 優先度2: それでも足りない場合は装備中のものを削除
            for inst in inv[:]:
                if hasattr(inst, "key") and inst.key == ik:
                    # ここに来るのは装備中のものだけ
                    if unequip_method: unequip_method()
                    inv.remove(inst); count -= 1
                    if count <= 0: return True
                    
        return count <= 0

    def add_quest_token(self, ek):
        self.quest_tokens[ek] = self.quest_tokens.get(ek, 0) + 1
        return self.check_quest_completion(ek)

    def _count_owned_items(self, tk):
        # 消耗品とイベントアイテムをカウント
        cnt = sum(i["count"] for i in self.items if i["key"] == tk)
        cnt += sum(i["count"] for i in self.event_items if i["key"] == tk)
        # 杖・装備品をカウント (これらは単体のリストなので要素数を数える)
        # 装備中のものは納品対象外とするため除外
        def get_slot_attr(target_inv):
            if target_inv is self.weapon_inventory: return "equipped_weapon"
            if target_inv is self.armor_inventory: return "equipped_armor"
            if target_inv is self.shield_inventory: return "equipped_shield"
            if target_inv is self.accessory_inventory: return "equipped_accessory"
            return None

        for inv in [self.stave_inventory, self.weapon_inventory, self.armor_inventory, self.shield_inventory, self.accessory_inventory]:
            slot_attr = get_slot_attr(inv)
            cnt += sum(1 for i in inv if i.key == tk and (not slot_attr or getattr(self, slot_attr) != i.iid))
        return cnt

    def check_quest_completion(self, tk):
        for q in self.active_quests:
            if q.get("target_key") == tk and not q.get("_completed_notified"):
                done = False
                if q.get("type") == "hunt": done = self.quest_tokens.get(tk, 0) >= q.get("amount", 1)
                elif q.get("type") == "delivery":
                    cnt = self._count_owned_items(tk)
                    done = cnt >= q.get("amount", 1)
                
                if done:
                    q["_completed_notified"] = True
                    from constants import SOUND_QUEST_COMPLETE
                    import os
                    if os.path.exists(SOUND_QUEST_COMPLETE):
                        pygame.mixer.Sound(SOUND_QUEST_COMPLETE).play()
                    return f"\n<Y>【{q.get('title', '依頼')}】の条件を達成した！</Y>\n帰還して報告しよう。"
        return ""

    def is_quest_reportable(self, q):
        tk = q.get("target_key")
        if not tk: return False
        if q.get("type") == "hunt": return self.quest_tokens.get(tk, 0) >= q.get("amount", 1)
        elif q.get("type") == "delivery":
            res = self._count_owned_items(tk) >= q.get("amount", 1)
            return res
        return False

    def is_any_quest_ready(self):
        for q in self.active_quests:
            if self.is_quest_reportable(q): return True
        return False

    def _get_weapon_instance(self, wn, enhance=0):
        from components.sprites.weapon import get_weapon_instance
        return get_weapon_instance(wn, enhance)

    def _execute_strike(self, dungeon, dialog=None):
        gx, gy = int((self.x + dungeon.tile_size/2)//dungeon.tile_size), int((self.y + dungeon.tile_size/2)//dungeon.tile_size)
        hg = self.weapon.get_hit_grids(self.facing, gx, gy, dungeon) if self.weapon else [(gx + {"up":0,"down":0,"left":-1,"right":1}[self.facing], gy + {"up":-1,"down":1,"left":0,"right":0}[self.facing])]
        for tx, ty in hg:
            for trap in dungeon.traps:
                if trap.x == tx and trap.y == ty and not trap.is_revealed: trap.is_revealed = True
            for e in dungeon.enemies:
                if getattr(e, "is_dead", False): continue
                if (tx, ty) in e.get_occupied_grids(dungeon.tile_size):
                    msg, dmg, crit, miss = deal_damage(self, e)
                    from systems.sound_handler import sound_manager
                    sound_manager.play_sfx(SOUND_ATTACK_MISS if miss or dmg == 0 else SOUND_ATTACK_HIT)
                    if crit: dungeon.flash_timer = 10
                    # --- knockbackスキル発動（クリティカル不問） ---
                    if dmg > 0 and not miss and not getattr(e, "is_static", False):
                        total_knockback = getattr(self, "total_knockback", 0)
                        if isinstance(total_knockback, int) and total_knockback >= 2:
                            kb_chance = getattr(self, "total_knockback_proc_chance", 0.0)
                            if isinstance(kb_chance, (int, float)) and kb_chance > 0:
                                if random.random() < kb_chance:
                                    kb_max_dist = max(1, int(getattr(self, "total_knockback_max_distance", 5)))
                                    e_gx = int((e.x + e.width / 2) // dungeon.tile_size)
                                    e_gy = int((e.y + e.height / 2) // dungeon.tile_size)
                                    dx, dy = {"up":(0,-1),"down":(0,1),"left":(-1,0),"right":(1,0)}.get(self.facing, (0,1))
                                    final_gx, final_gy = e_gx, e_gy
                                    for _ in range(kb_max_dist):
                                        next_gx, next_gy = final_gx + dx, final_gy + dy
                                        if not (0 <= next_gx < dungeon.map_width and 0 <= next_gy < dungeon.map_height) or dungeon.map_data[next_gy][next_gx] == 0:
                                            break
                                        blocked = any(
                                            oe != e and not getattr(oe, "is_dead", False) and
                                            int((oe.x + oe.width/2) // dungeon.tile_size) == next_gx and
                                            int((oe.y + oe.height/2) // dungeon.tile_size) == next_gy
                                            for oe in dungeon.enemies
                                        )
                                        if blocked:
                                            break
                                        final_gx, final_gy = next_gx, next_gy
                                    if (final_gx, final_gy) != (e_gx, e_gy):
                                        e.move_speed = 1200
                                        e.target_x = final_gx * dungeon.tile_size
                                        e.target_y = final_gy * dungeon.tile_size
                                        e.is_moving = True
                                        push_distance = abs(final_gx - e_gx) + abs(final_gy - e_gy)
                                        e.immobilized_turns = max(getattr(e, "immobilized_turns", 0), push_distance + 1)
                                        e.flash_color = (180, 120, 255)
                                        from systems.magic_handler import ParalysisEffect
                                        dungeon.magic_effects.append(
                                            ParalysisEffect(final_gx * dungeon.tile_size, final_gy * dungeon.tile_size, color=(180, 120, 255), duration=24)
                                        )
                                        sound_manager.play_sfx(SOUND_KNOCKBACK)
                                        msg += f"\n{e.name} を吹き飛ばした！"
                                        if os.environ.get("DEBUG_MODE") == "1":
                                            print(f"[ノックバック] ✅ 発動")
                                elif os.environ.get("DEBUG_MODE") == "1":
                                    print(f"[ノックバック] ❌ 抽選失敗")
                    if dialog:
                        if dialog.is_active: dialog.text += "\n" + msg; dialog.auto_close_timer = COMBAT_LOG_WAIT_FRAMES
                        else: dialog.text = msg; dialog.is_active = True; game_state["dialog_modal"] = False; dialog.auto_close_timer = COMBAT_LOG_WAIT_FRAMES
                    if not (self.weapon and self.weapon.pierce): return
                    break

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            if self.has_item("revive_amulet"):
                self.remove_item_by_key("revive_amulet"); self.hp = self.max_hp // 2; self.is_dead = False; self.damage_flash_timer = 120
                self.condition = "normal"; self.status_timer = 0
                current_dungeon = getattr(self, "current_dungeon", None)
                if current_dungeon is not None:
                    from systems.magic_handler import FlashEffect
                    current_dungeon.magic_effects.append(FlashEffect(color=(255, 245, 180), duration=18))
            else: self.hp = 0; self.is_dead = True
        else: self.damage_flash_timer = 60 + HIT_STUN_DURATION

    def apply_turn_effects(self, dungeon, dialog=None):
        if self.hp <= 0: return
        from constants import STATUS_EFFECTS, COMBAT_LOG_WAIT_FRAMES
        if self.condition == "poison":
            pd = STATUS_EFFECTS.get("poison", {}); dmg = max(pd.get("min_damage", 1), int(self.max_hp * pd.get("damage_rate", 0.005)))
            self.hp = max(1, self.hp - dmg)
            from systems.magic_handler import FlashEffect
            dungeon.magic_effects.append(FlashEffect(color=(150, 0, 200), duration=10))
            self.status_timer -= 1
            msg = f"毒のダメージ！ {dmg}のダメージを受けた！"
            if self.status_timer <= 0: self.condition = "normal"; msg += "\n毒の持続時間が終わった。毒が消えた！"
            if dialog:
                if dialog.is_active: dialog.text += "\n" + msg
                else: dialog.text = msg; dialog.is_active = True; game_state["dialog_modal"] = False; dialog.auto_close_timer = COMBAT_LOG_WAIT_FRAMES
        elif self.condition == "darkness":
            self.status_timer -= 1
            if self.status_timer <= 0:
                self.condition = "normal"
                msg = "暗闇が晴れた！"
                if dialog:
                    if dialog.is_active: dialog.text += "\n" + msg
                    else: dialog.text = msg; dialog.is_active = True; game_state["dialog_modal"] = False; dialog.auto_close_timer = COMBAT_LOG_WAIT_FRAMES
        elif self.hp < self.max_hp:
            # 燕バフによる自動回復 (毎ターン hp が regen_buff_val 分だけ回復)
            if getattr(self, "regen_buff_turns", 0) > 0:
                self.hp = min(self.max_hp, self.hp + getattr(self, "regen_buff_val", 2))
            
            if self.hp < self.max_hp:
                from constants import PLAYER_REGEN_BASE, PLAYER_REGEN_MULTIPLIER
                self.regen_pool = round(self.regen_pool + PLAYER_REGEN_BASE + (self.regen_bonus * PLAYER_REGEN_MULTIPLIER), 3)
                if self.regen_pool >= 1.0: rec = int(self.regen_pool); self.hp = min(self.max_hp, self.hp + rec); self.regen_pool -= rec

    def start_falling(self, tile_size):
        self.is_falling = True
        self.falling_timer = 60
        self.target_x, self.target_y = self.x, self.y
        self.is_moving = False

    def process_movement(self, dt=1/60): return super().process_movement(dt)

    def to_dict(self):
        return {
            "x": self.x, "y": self.y, "hp": self.hp, "max_hp": self._base_max_hp, "coin": self.coin, "bank_coin": getattr(self, "bank_coin", 0), "attack": self.attack, "defense": self.defense,
            "items": [dict(it) for it in self.items], "weapon_inventory": [eq.to_dict() for eq in self.weapon_inventory], "armor_inventory": [eq.to_dict() for eq in self.armor_inventory],
            "shield_inventory": [eq.to_dict() for eq in self.shield_inventory], "equipped_weapon": self.equipped_weapon, "equipped_armor": self.equipped_armor, "equipped_shield": self.equipped_shield,
            "stave_inventory": [st.to_dict() for st in self.stave_inventory], "accessory_inventory": [eq.to_dict() for eq in self.accessory_inventory], "equipped_accessory": self.equipped_accessory,
            "invincible_turns": self.invincible_turns,
            "attack_buff_turns": getattr(self, "attack_buff_turns", 0),
            "attack_buff_val": getattr(self, "attack_buff_val", 0),
            "attack_buff_crit": getattr(self, "attack_buff_crit", 0),
            "attack_buff_armor_pen": getattr(self, "attack_buff_armor_pen", 0.0),
            "regen_buff_turns": getattr(self, "regen_buff_turns", 0),
            "regen_buff_val": getattr(self, "regen_buff_val", 0),
            "regen_buff_heal_boost": getattr(self, "regen_buff_heal_boost", 0.0),
            "magic_buff_turns": getattr(self, "magic_buff_turns", 0),
            "magic_buff_val": getattr(self, "magic_buff_val", 0),
            "stealth_buff_turns": getattr(self, "stealth_buff_turns", 0),
            "stealth_buff_max_turns": getattr(self, "stealth_buff_max_turns", 0),
            "stealth_buff_lantern": getattr(self, "stealth_buff_lantern", 0),
            "stealth_buff_aggro": getattr(self, "stealth_buff_aggro", 0),
            "stealth_buff_pursuit_evasion": getattr(self, "stealth_buff_pursuit_evasion", 0),
            "stealth_buff_stupidity": getattr(self, "stealth_buff_stupidity", 0),
            "guild_point": self.guild_point, "guild_rank": self.guild_rank, "active_quests": self.active_quests, "quest_tokens": self.quest_tokens,
            "completed_fixed_quests": self.completed_fixed_quests, "defeated_once_only": getattr(self, "defeated_once_only", []), "has_seen_ending": self.has_seen_ending, "dungeon_core_cleared": getattr(self, "dungeon_core_cleared", False), "warehouse_items": self.warehouse_items, "event_items": self.event_items,
            "ending_clear_count": getattr(self, "ending_clear_count", 0),
            "new_game_plus_pending": getattr(self, "new_game_plus_pending", False),
            "current_floor": self.current_floor, "max_reached_floor": self.max_reached_floor, "equip_id_counter": globals().get("_equip_id_counter", 0),
            "boss_message_shown": getattr(self, "boss_message_shown", False),
            "curse_level": getattr(self, "curse_level", 0),
            "cursed_stats": getattr(self, "cursed_stats", []),
            "shop_seen_special": getattr(self, "shop_seen_special", {}),
            "tactical_profile": self.tactical_profile.to_dict(),
        }

    def load_dict(self, data):
        self.x, self.y = data.get("x", self.x), data.get("y", self.y)
        self.hp, self.max_hp = int(data.get("hp", self.hp)), int(data.get("max_hp", self.max_hp))
        self.coin, self.bank_coin = int(data.get("coin", self.coin)), int(data.get("bank_coin", 0))
        self.attack, self.defense = int(data.get("attack", self.attack)), int(data.get("defense", self.defense))
        ri = data.get("items", [])
        self.items = []
        for it in ri:
            if isinstance(it, dict): self.items.append(dict(it))
            else: self.add_item_to_inventory(it)
        self.weapon_inventory = [EquipInstance.from_dict(eq) for eq in data.get("weapon_inventory", [])]
        self.armor_inventory = [EquipInstance.from_dict(eq) for eq in data.get("armor_inventory", [])]
        self.shield_inventory = [EquipInstance.from_dict(eq) for eq in data.get("shield_inventory", [])]
        ew = data.get("equipped_weapon"); self.change_weapon(ew) if ew is not None else self.unequip_weapon()
        ea = data.get("equipped_armor"); self.change_armor(ea) if ea is not None else self.unequip_armor()
        es = data.get("equipped_shield"); self.change_shield(es) if es is not None else self.unequip_shield()
        self.stave_inventory = [StaveInstance.from_dict(st) for st in data.get("stave_inventory", [])]
        self.accessory_inventory = [EquipInstance.from_dict(eq) for eq in data.get("accessory_inventory", [])]
        ea = data.get("equipped_accessory")
        # 後方互換性：旧セーブデータのカンテラをアクセサリ枠にインポート
        old_lanterns = data.get("lantern_inventory", [])
        old_equipped = data.get("equipped_lantern")
        if old_lanterns:
            for l_data in old_lanterns:
                l_inst = EquipInstance.from_dict(l_data)
                self.accessory_inventory.append(l_inst)
                if old_equipped == l_data.get("iid"):
                    ea = l_inst.iid
        self.change_accessory(ea) if ea is not None else self.unequip_accessory()
        self.invincible_turns = int(data.get("invincible_turns", 0))
        self.attack_buff_turns = int(data.get("attack_buff_turns", 0))
        self.attack_buff_val = int(data.get("attack_buff_val", 0))
        self.attack_buff_crit = int(data.get("attack_buff_crit", 0))
        self.attack_buff_armor_pen = float(data.get("attack_buff_armor_pen", 0.0))
        self.regen_buff_turns = int(data.get("regen_buff_turns", 0))
        self.regen_buff_val = int(data.get("regen_buff_val", 0))
        self.regen_buff_heal_boost = float(data.get("regen_buff_heal_boost", 0.0))
        self.magic_buff_turns = int(data.get("magic_buff_turns", 0))
        self.magic_buff_val = float(data.get("magic_buff_val", 0))
        self.stealth_buff_turns = int(data.get("stealth_buff_turns", 0))
        self.stealth_buff_max_turns = int(data.get("stealth_buff_max_turns", 0))
        self.stealth_buff_lantern = int(data.get("stealth_buff_lantern", 0))
        self.stealth_buff_aggro = int(data.get("stealth_buff_aggro", 0))
        self.stealth_buff_pursuit_evasion = int(data.get("stealth_buff_pursuit_evasion", 0))
        self.stealth_buff_stupidity = int(data.get("stealth_buff_stupidity", 0))
        self.guild_point = int(data.get("guild_point", 0)); self.guild_rank = data.get("guild_rank", "F")
        self.active_quests = data.get("active_quests", [])
        for q in self.active_quests:
            if "reward_gold" not in q: q["reward_gold"] = 1
            if "reward_gp" not in q: q["reward_gp"] = 1
        self.quest_tokens = data.get("quest_tokens", {}); self.completed_fixed_quests = data.get("completed_fixed_quests", []); self.defeated_once_only = data.get("defeated_once_only", [])
        self.has_seen_ending = data.get("has_seen_ending", False); self.dungeon_core_cleared = data.get("dungeon_core_cleared", False); self.max_reached_floor = data.get("max_reached_floor", 0); self.warehouse_items = data.get("warehouse_items", []); self.event_items = data.get("event_items", [])
        self.ending_clear_count = int(data.get("ending_clear_count", 0))
        self.new_game_plus_pending = bool(data.get("new_game_plus_pending", False))
        self.current_floor = data.get("current_floor", 0)
        self.boss_message_shown = data.get("boss_message_shown", False)
        self.curse_level = int(data.get("curse_level", 0))
        self.cursed_stats = data.get("cursed_stats", [])
        self.shop_seen_special = data.get("shop_seen_special", {})
        self.tactical_profile = TacticalProfile.from_dict(data.get("tactical_profile", {}))
        global _equip_id_counter
        _equip_id_counter = max(_equip_id_counter, data.get("equip_id_counter", 0))
        # God Mode はセーブしないので、ロード時に常にOFF
        self.is_god = False

    def get_enemy_stat_multiplier(self):
        clear_count = max(0, int(getattr(self, "ending_clear_count", 0)))
        if clear_count <= 0:
            return 1.0
        if clear_count == 1:
            return 1.3
        if clear_count == 2:
            return 1.5
        return round(1.5 + (clear_count - 2) * 0.2, 1)

    def apply_new_game_plus_start(self):
        if not getattr(self, "new_game_plus_pending", False):
            return False
        self.guild_rank = "-"
        self.guild_point = 0
        self.has_seen_ending = False
        self.dungeon_core_cleared = False
        once_only_bosses = {"undead_father", "dungeon_core"}
        self.defeated_once_only = [
            enemy_type for enemy_type in getattr(self, "defeated_once_only", [])
            if enemy_type not in once_only_bosses
        ]
        self.new_game_plus_pending = False
        self.save_to_file(show_loading=False)
        return True

    def accept_quest(self, q):
        if self.active_quests:
            return False

        self.active_quests.append(q)
        if self.guild_point == 0:
            self.guild_point = 50
            return True
        return False

    def remove_quest(self, q):
        if q in self.active_quests: self.active_quests.remove(q)

    def complete_quest(self, q):
        if q in self.active_quests:
            self.coin += q.get("reward_gold", 0)
            self.guild_point += q.get("reward_gp", 0)
            self.remove_quest(q)
            # 固定クエストなら記録する
            if q.get("is_fixed") and q.get("id") not in self.completed_fixed_quests:
                self.completed_fixed_quests.append(q.get("id"))

    def save_to_file(self, filepath=None, show_loading=True):
        if filepath is None: from systems.data_loader import SAVE_DATA_PATH; filepath = SAVE_DATA_PATH
        import json; print(f"[SYSTEM] Saving progress to {filepath}...")
        screen = pygame.display.get_surface()
        if screen and show_loading:
            from systems.ui import show_loading_screen
            from wordings import Text
            show_loading_screen(screen, text=Text.UI.SAVING)
        with open(filepath, "w", encoding="utf-8") as f: json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def load_from_file(self, filepath=None):
        if filepath is None: from systems.data_loader import SAVE_DATA_PATH; filepath = SAVE_DATA_PATH
        import json, os
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f: data = json.load(f); self.load_dict(data); return True
        return False
