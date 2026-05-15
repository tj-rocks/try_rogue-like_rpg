
import unittest
import pygame
import os
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テスト用の環境設定
os.environ["TEST_MODE"] = "1"
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player
from systems.ui import TeleportDialog
from systems.game_state import game_state
from constants import TELEPORT_REQUIRED_ITEM

class TestTeleportSystem(unittest.TestCase):
    def setUp(self):
        self.player = Player()
        from constants import SCREEN_WIDTH, SCREEN_HEIGHT
        self.dialog = TeleportDialog(SCREEN_WIDTH, SCREEN_HEIGHT)
        game_state["teleport_active"] = False
        game_state["pending_warp"] = None

    def test_destination_listing_village(self):
        """村にいる時、到達済みの休憩所がリストアップされるか"""
        self.player.current_floor = 0
        self.player.max_reached_floor = 15 # 12Fの休憩所を含める
        
        success = self.dialog.open(self.player)
        self.assertTrue(success)
        self.assertTrue(len(self.dialog.items) > 0)
        # 12F休憩所が含まれているか確認
        dest_floors = [d["floor"] for d in self.dialog.items]
        self.assertIn(12, dest_floors)

    def test_destination_listing_rest_area(self):
        """休憩所にいる時、村への帰還がリストアップされるか"""
        self.player.current_floor = 12
        
        success = self.dialog.open(self.player)
        self.assertTrue(success)
        # 「村（帰還）」＋「やめる」の2件
        self.assertEqual(len(self.dialog.items), 2)
        self.assertEqual(self.dialog.items[0]["floor"], 0)
        self.assertEqual(self.dialog.items[1]["type"], "cancel")

    def test_no_destinations(self):
        """一度も休憩所にいっていない場合、村でのオープンに失敗するか"""
        self.player.current_floor = 0
        self.player.max_reached_floor = 5 # 12Fに届いていない
        
        success = self.dialog.open(self.player)
        self.assertFalse(success)

    def test_cost_check_failure_no_money(self):
        """お金が足りない場合に NO_MONEY モードになるか"""
        self.player.current_floor = 0
        self.player.max_reached_floor = 15
        self.player.coin = 0 # お金なし
        # アイテムは持たせる
        self.player.add_item_to_inventory(TELEPORT_REQUIRED_ITEM)
        
        self.dialog.open(self.player)
        # 最初の目的地(12F)を選択して決定キー
        event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE})
        self.dialog.handle_input([event], self.player)
        
        self.assertEqual(self.dialog.mode, "NO_MONEY")

    def test_cost_check_failure_no_item(self):
        """アイテムが足りない場合に NO_ITEM モードになるか"""
        self.player.current_floor = 0
        self.player.max_reached_floor = 15
        self.player.coin = 100000 # お金はある
        # アイテムは持たせない
        
        self.dialog.open(self.player)
        event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE})
        self.dialog.handle_input([event], self.player)
        
        self.assertEqual(self.dialog.mode, "NO_ITEM")

    def test_execute_teleport(self):
        """転移実行時に金とアイテムが減り、予約が行われるか"""
        self.player.current_floor = 0
        self.player.max_reached_floor = 15
        self.player.coin = 20000
        self.player.add_item_to_inventory(TELEPORT_REQUIRED_ITEM)
        item_count_before = self.player.get_item_count()
        
        self.dialog.open(self.player)
        dest = self.dialog.items[0]
        cost = dest["cost"]
        
        # 1. 決定して CONFIRM モードへ
        event_confirm = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE})
        self.dialog.handle_input([event_confirm], self.player)
        self.assertEqual(self.dialog.mode, "CONFIRM")
        
        # 2. 再度決定して実行
        self.dialog.handle_input([event_confirm], self.player)
        
        # 検証
        self.assertEqual(self.player.coin, 20000 - cost)
        self.assertEqual(self.player.get_item_count(), item_count_before - 1)
        self.assertTrue(self.player.is_falling) # 落下演出開始
        self.assertIsNotNone(game_state["pending_warp"])
        self.assertEqual(game_state["pending_warp"]["floor"], dest["floor"])

if __name__ == "__main__":
    unittest.main()
