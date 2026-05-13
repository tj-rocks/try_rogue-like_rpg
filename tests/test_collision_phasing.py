
import pygame
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テストモードを強制して本番セーブデータを保護する
os.environ["TEST_MODE"] = "1"

from components.sprites.player import Player
from components.sprites.enemy import Enemy
from systems.dungeon import Dungeon

def test_collision_phasing():
    pygame.init()
    pygame.display.set_mode((800, 600))
    
    tile_size = 64
    dungeon = Dungeon(level=1)
    player = Player()
    
    # 1. 敵を (2, 2) に配置し、(3, 2) へ移動開始させる
    # Enemy(x, y, type)
    enemy = Enemy(2 * tile_size, 2 * tile_size, "slime")
    enemy.target_x = 3 * tile_size
    enemy.is_moving = True
    dungeon.enemies = [enemy]
    
    # 2. プレイヤーが (3, 2) へ移動しようとする
    # (3, 2) は敵の target_x なので、ブロックされるべき
    player.x = 3 * tile_size
    player.y = 1 * tile_size # (3, 1) から (3, 2) へ移動を試みる
    
    target_px = 3 * tile_size
    target_py = 2 * tile_size
    
    print(f"Testing Phasing: Enemy moving (2,2) -> (3,2). Player trying to enter (3,2).")
    can_move = player.can_move_grid(target_px, target_py, dungeon)
    
    if not can_move:
        print("[OK] Phasing blocked! Player cannot enter the enemy's target tile.")
    else:
        print("[FAILED] Phasing occurred! Player could enter the tile the enemy is moving to.")
        sys.exit(1)

    # 3. 敵が「ぼーっとしている（静止）」状態でもチェック
    enemy.is_moving = False
    enemy.x = 3 * tile_size
    enemy.target_x = 3 * tile_size
    # 少し中心からズラしてみる（画像サイズが小さい場合を想定）
    enemy.x += 10 
    
    print(f"Testing Idle: Enemy idling at (3,2) with offset. Player trying to enter (3,2).")
    can_move = player.can_move_grid(target_px, target_py, dungeon)
    
    if not can_move:
        print("[OK] Idle collision blocked!")
    else:
        print("[FAILED] Idle collision failed! Player phased through the idling enemy.")
        sys.exit(1)

    print("\n[RESULT] Collision Phasing Test: PASSED")
    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    test_collision_phasing()
