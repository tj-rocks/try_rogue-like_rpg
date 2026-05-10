import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from components.sprites.entity import Entity

class TestMovement(unittest.TestCase):
    def test_frame_rate_independence(self):
        """デルタタイムに基づいた移動が正確かテストする"""
        # 初期位置 (0, 0)
        entity = Entity(0, 0, 100, 100, 10)
        entity.move_speed = 300  # 300px / sec
        
        # 目的地を (100, 0) に設定
        entity.target_x = 100
        entity.target_y = 0
        entity.is_moving = True
        
        # 1. 0.1秒後の移動距離をテスト (300 * 0.1 = 30px)
        entity.process_movement(0.1)
        self.assertEqual(entity.x, 30, "0.1秒で30ピクセル移動するはずです")
        
        # 2. さらに0.2秒後の移動距離をテスト (計0.3秒 = 90px)
        entity.process_movement(0.2)
        self.assertEqual(entity.x, 90, "合計0.3秒で90ピクセル移動するはずです")
        
        # 3. 目的地を超えようとした場合、目的地で止まるかテスト
        # あと10pxで目的地だが、0.1秒なら30px動こうとするはず
        entity.process_movement(0.1)
        self.assertEqual(entity.x, 100, "目的地 (100) を超えて移動してはいけません")
        self.assertFalse(entity.is_moving, "目的地に到達したら is_moving は False になるはずです")

    def test_high_fps_consistency(self):
        """高フレームレート（短い dt）でも正しく移動するかテストする"""
        entity = Entity(0, 0, 100, 100, 10)
        entity.move_speed = 300
        entity.target_x = 300
        entity.is_moving = True
        
        # 非常に短い時間 (1/1000秒) で100回繰り返す = 0.1秒
        for _ in range(100):
            entity.process_movement(0.001)
        
        # 浮動小数点の誤差を考慮して近似値でチェック
        self.assertAlmostEqual(entity.x, 30, places=5, msg="高フレームレートでも0.1秒で30ピクセル移動するはずです")

if __name__ == "__main__":
    unittest.main()
