import os
import sys
import unittest
import pygame

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テストモード設定
os.environ["TEST_MODE"] = "1"

from components.sprites.player import Player, EquipInstance, StaveInstance

class TestDeliveryAllTypes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    def setUp(self):
        self.player = Player()
        self.player.active_quests = []
        self.player.items = []
        self.player.stave_inventory = []
        self.player.weapon_inventory = []
        self.player.armor_inventory = []
        self.player.shield_inventory = []
        self.player.lantern_inventory = []

    def test_delivery_consumable(self):
        """消耗品での納品達成・削除テスト"""
        target_key = "potion"
        self.player.active_quests = [{"type": "delivery", "target_key": target_key, "amount": 1, "title": "ポーション納品"}]
        self.player.items.append({"key": target_key, "count": 1})
        
        # 判定チェック
        self.assertTrue(self.player.is_quest_reportable(self.player.active_quests[0]))
        # 削除チェック
        self.assertTrue(self.player.remove_item_by_key(target_key, 1))
        self.assertEqual(len(self.player.items), 0)

    def test_delivery_stave(self):
        """杖での納品達成・削除テスト"""
        target_key = "fire_stave"
        self.player.active_quests = [{"type": "delivery", "target_key": target_key, "amount": 1, "title": "火の杖納品"}]
        self.player.stave_inventory.append(StaveInstance(target_key))
        
        # 判定チェック
        self.assertTrue(self.player.is_quest_reportable(self.player.active_quests[0]))
        # 削除チェック
        self.assertTrue(self.player.remove_item_by_key(target_key, 1))
        self.assertEqual(len(self.player.stave_inventory), 0)

    def test_delivery_weapon(self):
        """武器での納品達成・削除テスト"""
        target_key = "iron_sword"
        self.player.active_quests = [{"type": "delivery", "target_key": target_key, "amount": 1, "title": "鉄の剣納品"}]
        self.player.weapon_inventory.append(EquipInstance("weapon", target_key))
        
        # 判定チェック
        self.assertTrue(self.player.is_quest_reportable(self.player.active_quests[0]))
        # 削除チェック
        self.assertTrue(self.player.remove_item_by_key(target_key, 1))
        self.assertEqual(len(self.player.weapon_inventory), 0)

    def test_delivery_armor(self):
        """鎧での納品達成・削除テスト"""
        target_key = "leather_breastplate"
        self.player.active_quests = [{"type": "delivery", "target_key": target_key, "amount": 1, "title": "鎧納品"}]
        self.player.armor_inventory.append(EquipInstance("armor", target_key))
        
        # 判定チェック
        self.assertTrue(self.player.is_quest_reportable(self.player.active_quests[0]))
        # 削除チェック
        self.assertTrue(self.player.remove_item_by_key(target_key, 1))
        self.assertEqual(len(self.player.armor_inventory), 0)

    def test_delivery_shield(self):
        """盾での納品達成・削除テスト"""
        target_key = "wooden_round_shield"
        self.player.active_quests = [{"type": "delivery", "target_key": target_key, "amount": 1, "title": "盾納品"}]
        self.player.shield_inventory.append(EquipInstance("shield", target_key))
        
        # 判定チェック
        self.assertTrue(self.player.is_quest_reportable(self.player.active_quests[0]))
        # 削除チェック
        self.assertTrue(self.player.remove_item_by_key(target_key, 1))
        self.assertEqual(len(self.player.shield_inventory), 0)

    def test_delivery_lantern(self):
        """カンテラでの納品達成・削除テスト"""
        target_key = "old_lantern"
        self.player.active_quests = [{"type": "delivery", "target_key": target_key, "amount": 1, "title": "カンテラ納品"}]
        self.player.lantern_inventory.append(EquipInstance("lantern", target_key))
        
        # 判定チェック
        self.assertTrue(self.player.is_quest_reportable(self.player.active_quests[0]))
        # 削除チェック
        self.assertTrue(self.player.remove_item_by_key(target_key, 1))
        self.assertEqual(len(self.player.lantern_inventory), 0)

    def test_delivery_equipped_removal(self):
        """装備中のアイテムを削除した際に装備が解除されるかのテスト"""
        target_key = "iron_sword"
        inst = EquipInstance("weapon", target_key)
        self.player.weapon_inventory.append(inst)
        self.player.equipped_weapon = inst.iid
        self.player.weapon = "dummy_object"
        
        # 削除実行
        self.assertTrue(self.player.remove_item_by_key(target_key, 1))
        # 装備スロットが空になっているかチェック
        self.assertIsNone(self.player.equipped_weapon)
        self.assertIsNone(self.player.weapon)
        self.assertEqual(len(self.player.weapon_inventory), 0)

if __name__ == "__main__":
    unittest.main()
