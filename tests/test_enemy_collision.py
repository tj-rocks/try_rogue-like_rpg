
import os
import sys
import pygame

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
screen = pygame.display.set_mode((800, 600))

from systems.session_handler import init_ui_elements, start_new_game
from systems.game_state import game_state
from components.sprites.enemy import Enemy
from constants import ENEMY_DATA

def test_enemy_to_enemy_collision():
    print("--- 敵同士の衝突判定テスト開始 ---")
    
    try:
        # 1. 初期化
        ui_elements = init_ui_elements(800, 600)
        player, dungeon = start_new_game(ui_elements, game_state)
        
        # 2. 2体の敵を隣接させて配置
        # 敵A (Slime)
        enemy_a = Enemy(10 * dungeon.tile_size, 10 * dungeon.tile_size, "slime")
        # 敵B (Slime) - Aの右側に配置
        enemy_b = Enemy(11 * dungeon.tile_size, 10 * dungeon.tile_size, "slime")
        
        dungeon.enemies = [enemy_a, enemy_b]
        
        print(f"敵A位置: ({enemy_a.x // dungeon.tile_size}, {enemy_a.y // dungeon.tile_size})")
        print(f"敵B位置: ({enemy_b.x // dungeon.tile_size}, {enemy_b.y // dungeon.tile_size})")

        # 3. 敵Aが敵Bのいる場所（右）へ移動できるかチェック
        target_x = enemy_a.x + dungeon.tile_size
        target_y = enemy_a.y
        
        can_move = enemy_a.can_move_grid(target_x, target_y, dungeon)
        
        # 4. 検証
        print(f"移動判定結果: {can_move}")
        assert not can_move, "敵Aが敵Bのいるマスへ移動可能と判定されました（衝突判定漏れ）"
        
        print("[OK] 敵同士の衝突判定テスト合格！")
        
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    test_enemy_to_enemy_collision()
    pygame.quit()
