import os
import sys
import pygame
import unittest

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テストモード設定
os.environ["TEST_MODE"] = "1"

from systems.dungeon import Dungeon
from components.sprites.player import Player

class TestDungeonGrowth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_room_count_growth(self):
        """各階層で生成される部屋数が、balance.ymlの設定値を下回らないことを検証する"""
        player = Player()
        # 検証する階層 (50階は固定マップを引く可能性があるため、一旦40階までを安定検証対象とする)
        test_floors = [1, 10, 20, 30, 40]
        
        for floor in test_floors:
            with self.subTest(floor=floor):
                # 各階層で3回試行
                for i in range(3):
                    dungeon = Dungeon(level=floor, player=player)
                    
                    # 固定マップの場合はスキップ（固定マップは部屋数ルールが適用されないため）
                    if dungeon.floor_info.get("map"):
                        print(f"  [Skip] Floor {floor} is a fixed map ({dungeon.floor_info.get('map')})")
                        continue
                        
                    min_expected = dungeon.min_rooms
                    actual_count = len(dungeon.rooms)
                    
                    print(f"  [Check] Floor {floor} (Attempt {i}): Rooms={actual_count}, ExpectedMin={min_expected}")
                    
                    self.assertGreaterEqual(
                        actual_count, min_expected,
                        f"Floor {floor} generated only {actual_count} rooms, but expected at least {min_expected}"
                    )

if __name__ == "__main__":
    unittest.main()
