import os
import sys
import unittest
from unittest.mock import MagicMock

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テストモードを強制
os.environ["TEST_MODE"] = "1"
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player, EquipInstance
from systems.combat_handler import calculate_damage, deal_damage
from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA

class TestArmorPenetration(unittest.TestCase):
    def setUp(self):
        # 元のマスターデータをバックアップ
        self.orig_weapon_data = WEAPON_DATA.copy()
        self.orig_armor_data = ARMOR_DATA.copy()
        self.orig_shield_data = SHIELD_DATA.copy()

    def tearDown(self):
        # 元のマスターデータに復元
        WEAPON_DATA.clear()
        WEAPON_DATA.update(self.orig_weapon_data)
        ARMOR_DATA.clear()
        ARMOR_DATA.update(self.orig_armor_data)
        SHIELD_DATA.clear()
        SHIELD_DATA.update(self.orig_shield_data)

    def test_total_armor_penetration_calculation(self):
        # 1. モックデータ定義 (割合での無視率を定義)
        WEAPON_DATA["pen_sword"] = {
            "name": "貫通ソード",
            "hp_bonus": 0,
            "defense_bonus": 0,
            "armor_penetration": 0.20, # 20%無視
        }
        ARMOR_DATA["pen_armor"] = {
            "name": "貫通アーマー",
            "hp_bonus": 0,
            "defense_bonus": 0,
            "armor_penetration": 0.30, # 30%無視
        }
        SHIELD_DATA["pen_shield"] = {
            "name": "貫通シールド",
            "hp_bonus": 0,
            "defense_bonus": 0,
            "armor_penetration": 0.10, # 10%無視
        }

        player = Player()
        player.weapon_inventory.clear()
        player.equipped_weapon = None
        player.armor_inventory.clear()
        player.equipped_armor = None
        player.shield_inventory.clear()
        player.equipped_shield = None

        # 初期値は無視率 0.0
        self.assertEqual(player.total_armor_penetration, 0.0)

        # 武器装備 -> 20%
        wp = EquipInstance("weapon", "pen_sword")
        player.weapon_inventory.append(wp)
        player.equipped_weapon = wp.iid
        self.assertAlmostEqual(player.total_armor_penetration, 0.20, places=5)

        # 防具装備 -> 20% + 30% = 50%
        ar = EquipInstance("armor", "pen_armor")
        player.armor_inventory.append(ar)
        player.equipped_armor = ar.iid
        self.assertAlmostEqual(player.total_armor_penetration, 0.50, places=5)

        # 盾装備 -> 20% + 30% + 10% = 60%
        sh = EquipInstance("shield", "pen_shield")
        player.shield_inventory.append(sh)
        player.equipped_shield = sh.iid
        self.assertAlmostEqual(player.total_armor_penetration, 0.60, places=5)

    def test_damage_combat_with_penetration(self):
        # プレイヤー側 (無視率60%)
        attacker = MagicMock()
        attacker.total_armor_penetration = 0.60
        attacker.total_attack = 50 # 攻撃力50
        attacker.crit_rate = 0.01
        attacker.crit_bonus = 0.0
        attacker.status_to_inflict = None
        attacker.weapon = None

        # 防御力 50 を持った敵ターゲット
        target = MagicMock()
        target.total_defense = 50
        target.defense = 50
        target.hp = 100
        target.condition = "normal"
        target.stupidity = 0
        target.is_god = False
        target.invincible_turns = 0
        
        # 1. 防御無視60%によるダメージシミュレーション
        # 防御力 50 は 60%無視されて 20 になるはず
        # 攻撃力 50 - 防御力 20 = ベースダメージ 30
        # 乱数範囲: 30 * (0.9 ~ 1.0) = 27 ~ 30
        # 最終ダメージは (27 ~ 30) の範囲に収まり、最低ダメージ 1 より確実に大きくなる
        msg, dmg, is_crit, is_miss = deal_damage(attacker, target, is_magic=True)
        
        self.assertTrue(27 <= dmg <= 30, f"Expected damage between 27 and 30, got {dmg}")
        self.assertEqual(target.defense, 50) # 敵の元の防御力値は書き変わっていないこと

        # 2. 100%無視（防御無視率 1.0）のシミュレーション
        attacker.total_armor_penetration = 1.0
        # 攻撃力 50 - 防御力 0 = ベースダメージ 50
        # 乱数範囲: 50 * (0.9 ~ 1.0) = 45 ~ 50
        msg, dmg, is_crit, is_miss = deal_damage(attacker, target, is_magic=True)
        self.assertTrue(45 <= dmg <= 50, f"Expected damage between 45 and 50, got {dmg}")

if __name__ == "__main__":
    unittest.main()
