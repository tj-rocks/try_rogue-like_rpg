
import os
import sys
import pygame

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テストモードを強制して本番セーブデータを保護する
os.environ["TEST_MODE"] = "1"

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
        if not can_move:
            print("[OK] 敵同士の衝突判定テスト合格！")
        else:
            print("[FAILED] 敵同士が重なっています")
            sys.exit(1)

        # --- [NEW] 移動中のすり抜け（Phasing）テスト ---
        print("\n--- 移動中のすり抜け防止テスト開始 ---")
        enemy_a.x = 2 * 64
        enemy_a.y = 2 * 64
        enemy_a.target_x = 3 * 64
        enemy_a.target_y = 2 * 64
        enemy_a.is_moving = True
        
        # 敵Bが、敵Aの「移動先」に入ろうとする
        enemy_b.x = 3 * 64
        enemy_b.y = 1 * 64
        enemy_b.target_x = 3 * 64
        enemy_b.target_y = 1 * 64
        can_move_phasing = enemy_b.can_move_grid(3 * 64, 2 * 64, dungeon)
        print(f"移動中マスへの進入判定結果: {can_move_phasing}")
        
        if not can_move_phasing:
            print("[OK] 移動中のすり抜け防止テスト合格！")
        else:
            print("[FAILED] 移動中の敵のターゲットマスに進入できてしまいました")
            sys.exit(1)

        pygame.quit()
        
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    test_enemy_to_enemy_collision()
    pygame.quit()
