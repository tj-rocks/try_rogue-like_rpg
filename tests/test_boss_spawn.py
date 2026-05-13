import os
import sys
import pygame
import random

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# [IMPORTANT] テストモードを強制して本番セーブデータを保護する
os.environ["TEST_MODE"] = "1"

from systems.dungeon import warp_to_floor
from components.sprites.player import Player
from components.sprites.enemy import Enemy
from constants import TILE_SIZE

def run_test():
    pygame.init()
    pygame.display.set_mode((1, 1))
    
    try:
        test_boss_guaranteed_spawn_on_floor_10()
        test_enemy_wall_spawn_prevention()
        print("\n✅ All boss spawn tests PASSED!")
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        pygame.quit()

def test_boss_guaranteed_spawn_on_floor_10():
    """10Fでスイスイスライムが確実に1体出現することを検証する"""
    print("--- 10Fボス確定出現テスト開始 ---")
    player = Player()
    
    # 複数回試行して、一度も欠けることがないか確認する (確実性のテスト)
    for i in range(10):
        dungeon = warp_to_floor(10, player, spawn_reason="warped")
        
        # ボスを探す
        bosses = [e for e in dungeon.enemies if e.type == "suisui_slime"]
        
        if len(bosses) != 1:
            raise AssertionError(f"Floor 10 should have exactly 1 suisui_slime, but found {len(bosses)} (Iteration {i})")
        print(f"[TEST] Iteration {i}: suisui_slime spawned successfully.")

def test_enemy_wall_spawn_prevention():
    """大型モンスター（ボスなど）が壁の中にスポーンしていないことを検証する"""
    print("\n--- 壁内スポーン防止テスト開始 ---")
    player = Player()
    
    # ボスが出現する10Fで検証
    for i in range(5):
        dungeon = warp_to_floor(10, player, spawn_reason="warped")
        
        for e in dungeon.enemies:
            # 占有グリッドを取得
            occupied = e.get_occupied_grids(TILE_SIZE)
            
            for gx, gy in occupied:
                # 範囲内か
                if not (0 <= gx < dungeon.map_width):
                    raise AssertionError(f"Enemy {e.type} at ({gx}, {gy}) is out of map bounds (x)")
                if not (0 <= gy < dungeon.map_height):
                    raise AssertionError(f"Enemy {e.type} at ({gx}, {gy}) is out of map bounds (y)")
                
                # 壁(0)ではないか
                tile_type = dungeon.map_data[gy][gx]
                if tile_type == 0:
                    raise AssertionError(f"Enemy {e.type} (size {e.width}x{e.height}) is spawned inside a wall at grid ({gx}, {gy}) in iteration {i}")
        
        print(f"[TEST] Iteration {i}: All {len(dungeon.enemies)} enemies are spawned safely on floor tiles.")

if __name__ == "__main__":
    run_test()
