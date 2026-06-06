import os
import sys
import pygame
from unittest.mock import MagicMock

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テストモードを強制して本番セーブデータを保護する
os.environ["TEST_MODE"] = "1"

# Pygameの初期化（ヘッドレスモード）
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()

from components.sprites.player import Player
from components.sprites.enemy import Enemy
from systems.dungeon import Dungeon
from systems.game_state import game_state

def test_smart_ranged_move():
    print("\n[TEST] 遠距離スマートムーブ設定値のAI動作テストを開始...")
    
    # --- 1. セットアップ ---
    # ダミーのダンジョンを作成
    dungeon = MagicMock(spec=Dungeon)
    dungeon.tile_size = 64
    dungeon.map_width = 20
    dungeon.map_height = 20
    dungeon.current_floor = 1
    # 床(1)で埋める
    dungeon.map_data = [[1 for _ in range(20)] for _ in range(20)]
    dungeon.dropped_items = []
    dungeon.traps = []
    dungeon.npcs = []
    
    # プレイヤー作成 (10, 10)
    player = Player()
    player.x = 10 * 64
    player.y = 10 * 64
    player.target_x = player.x
    player.target_y = player.y
    player.facing = "right"
    
    # ----------------------------------------------------
    # ケース 1: smart_ranged_move = True (デフォルトのこわいくさ)
    # ----------------------------------------------------
    print("\n--- ケース 1: smart_ranged_move = True (隣接時に下がる) ---")
    enemy_smart = Enemy(11 * 64, 10 * 64, "kowai_kusa", player=player)
    enemy_smart.stupidity = 0  # 確実に思考させる
    enemy_smart.smart_ranged_move = True
    dungeon.enemies = [enemy_smart]
    
    # テスト対象のメソッドを呼び出す (隣接状態)
    dialog_mock = MagicMock()
    dialog_mock.is_active = False
    
    # 思考実行
    enemy_smart.take_turn(player, dungeon, dungeon.enemies, dialog_mock, set())
    
    # 検証: smart_ranged_move が True の場合、1歩離れようとするはず
    # 移動状態になり、target_x が 12 (プレイヤーから離れる方向) になることを確認
    print(f"smart=True の行動結果: is_moving={enemy_smart.is_moving}, target_x/y=({enemy_smart.target_x // 64}, {enemy_smart.target_y // 64})")
    # プレイヤーは 10 にいる。元々 11 にいた敵は距離 2 に離れるはず
    dist = abs(enemy_smart.target_x // 64 - 10) + abs(enemy_smart.target_y // 64 - 10)
    assert dist == 2, f"smart_ranged_move=True の時にプレイヤーから離れていません (現在 距離: {dist}, 座標: {enemy_smart.target_x // 64}, {enemy_smart.target_y // 64})"
    assert enemy_smart.is_attacking == False, "smart_ranged_move=True なのに攻撃を開始してしまっています"
    print("✅ ケース 1 合格: 適切にスマートムーブ（後退）しました。")

    # ----------------------------------------------------
    # ケース 2: smart_ranged_move = False (愚直に近づく/攻撃する)
    # ----------------------------------------------------
    print("\n--- ケース 2: smart_ranged_move = False (隣接時に下がらずその場で攻撃) ---")
    enemy_dumb = Enemy(11 * 64, 10 * 64, "kowai_kusa", player=player)
    enemy_dumb.stupidity = 0
    enemy_dumb.smart_ranged_move = False  # スマートムーブを無効化
    dungeon.enemies = [enemy_dumb]
    
    # 思考実行前に向きを初期化
    enemy_dumb.facing = "left" # プレイヤーを向かせる
    
    # 思考実行
    enemy_dumb.take_turn(player, dungeon, dungeon.enemies, dialog_mock, set())
    
    # 検証: smart_ranged_move が False の場合、下がらずにその場で攻撃を開始するはず
    print(f"smart=False の行動結果: is_moving={enemy_dumb.is_moving}, is_attacking={enemy_dumb.is_attacking}")
    assert enemy_dumb.is_moving == False, "smart_ranged_move=False なのに移動してしまっています"
    assert enemy_dumb.is_attacking == True, "smart_ranged_move=False なのにその場での攻撃を開始していません"
    print("✅ ケース 2 合格: 下がらずにその場で攻撃を開始しました。")

if __name__ == "__main__":
    try:
        test_smart_ranged_move()
        print("\n🎉 全てのスマートムーブテストに合格しました！")
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
