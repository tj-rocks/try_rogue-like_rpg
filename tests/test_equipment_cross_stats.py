import os
import sys
import pygame
import unittest
from unittest.mock import patch

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テストモードを強制して本番セーブデータを保護する
os.environ["TEST_MODE"] = "1"

# Pygameの初期化（ヘッドレスモード）
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player, EquipInstance
from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA

class TestEquipmentCrossStats(unittest.TestCase):
    def setUp(self):
        # テスト用のダミーデータを constants に一時的に登録する
        self.orig_weapon_data = WEAPON_DATA.copy()
        self.orig_armor_data = ARMOR_DATA.copy()
        self.orig_shield_data = SHIELD_DATA.copy()

    def tearDown(self):
        # データを復元
        WEAPON_DATA.clear()
        WEAPON_DATA.update(self.orig_weapon_data)
        ARMOR_DATA.clear()
        ARMOR_DATA.update(self.orig_armor_data)
        SHIELD_DATA.clear()
        SHIELD_DATA.update(self.orig_shield_data)

    def test_cross_equipment_bonuses(self):
        # テスト用データ定義
        WEAPON_DATA["custom_sword"] = {
            "name": "特製ソード",
            "hp_bonus": 20,
            "defense_bonus": 5,
            "magic_stave_bonus": 2,
            "lantern_bonus": 1,
            "regen_bonus": 3,
            "block_chance": 0.1,
            "block_chance_close": 0.1,
            "block_chance_ranged": 0.1,
        }
        ARMOR_DATA["custom_armor"] = {
            "name": "特製アーマー",
            "hp_bonus": 50,
            "defense_bonus": 10,
            "block_chance": 0.05,
            "block_chance_close": 0.05,
            "block_chance_ranged": 0.05,
            "magic_stave_bonus": 3,
            "lantern_bonus": 2,
            "regen_bonus": 4,
        }
        SHIELD_DATA["custom_shield"] = {
            "name": "特製シールド",
            "hp_bonus": 30,
            "defense_bonus": 15,
            "block_chance": 0.2,
            "block_chance_close": 0.2,
            "block_chance_ranged": 0.2,
            "magic_stave_bonus": 4,
            "lantern_bonus": 3,
            "regen_bonus": 5,
        }

        # プレイヤー初期化
        player = Player()

        # 装備を一度全て外す（初期装備の影響を除く）
        player.weapon_inventory.clear()
        player.equipped_weapon = None
        player.armor_inventory.clear()
        player.equipped_armor = None
        player.shield_inventory.clear()
        player.equipped_shield = None

        # 初期値の確認
        self.assertEqual(player.max_hp, player._base_max_hp)
        self.assertEqual(player.total_defense, player.defense)
        self.assertEqual(player.stave_bonus, 0)
        self.assertEqual(player.lantern_bonus, 0)
        self.assertEqual(player.regen_bonus, 0)
        self.assertEqual(player.block_chance_close, 0.0)
        self.assertEqual(player.block_chance_ranged, 0.0)

        # 1. 武器だけ装備してみる
        wp = EquipInstance("weapon", "custom_sword")
        player.weapon_inventory.append(wp)
        player.equipped_weapon = wp.iid

        self.assertEqual(player.max_hp, player._base_max_hp + 20)
        self.assertEqual(player.total_defense, player.defense + 5)
        self.assertEqual(player.stave_bonus, 2)
        self.assertEqual(player.lantern_bonus, 1)
        self.assertEqual(player.regen_bonus, 3)
        self.assertAlmostEqual(player.block_chance_close, 0.1)

        # 2. 防具も装備してみる
        ar = EquipInstance("armor", "custom_armor")
        player.armor_inventory.append(ar)
        player.equipped_armor = ar.iid

        self.assertEqual(player.max_hp, player._base_max_hp + 20 + 50)
        self.assertEqual(player.total_defense, player.defense + 5 + 10)
        self.assertEqual(player.stave_bonus, 2 + 3)
        self.assertEqual(player.lantern_bonus, 1 + 2)
        self.assertEqual(player.regen_bonus, 3 + 4)
        self.assertAlmostEqual(player.block_chance_close, 0.1 + 0.05)

        # 3. 盾も装備してみる
        sh = EquipInstance("shield", "custom_shield")
        player.shield_inventory.append(sh)
        player.equipped_shield = sh.iid

        self.assertEqual(player.max_hp, player._base_max_hp + 20 + 50 + 30)
        self.assertEqual(player.total_defense, player.defense + 5 + 10 + 15)
        self.assertEqual(player.stave_bonus, 2 + 3 + 4)
        self.assertEqual(player.lantern_bonus, 1 + 2 + 3)
        self.assertEqual(player.regen_bonus, 3 + 4 + 5)
        self.assertAlmostEqual(player.block_chance_close, 0.1 + 0.05 + 0.2)
        self.assertAlmostEqual(player.block_chance_ranged, 0.1 + 0.05 + 0.2)

if __name__ == "__main__":
    unittest.main()
