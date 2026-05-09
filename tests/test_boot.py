
import os
import sys
import pygame

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化（ヘッドレス環境に近い状態で最小化）
pygame.init()
screen = pygame.display.set_mode((800, 600)) # 描画テストのため、ある程度のサイズを確保

from systems.session_handler import init_ui_elements, start_new_game
from systems.game_state import game_state
from systems.scene_handler import handle_game

def test_game_boot_and_render():
    print("--- 起動・描画スモークテスト開始 ---")
    
    try:
        # 1. UIエレメントの初期化
        print("UIエレメント初期化中...")
        ui_elements = init_ui_elements(800, 600)
        
        # 2. ゲーム開始（村 0階）
        print("新規ゲームセッション開始中...")
        player, dungeon = start_new_game(ui_elements, game_state)
        
        # 3. 数フレーム描画・更新を走らせる
        print("メインループのシミュレーション（10フレーム）...")
        for i in range(10):
            # 空のイベントリスト
            events = []
            # handle_game を呼び出し（これが描画・更新の統合ポイント）
            # handle_game は内部で dungeon.draw, player.update, draw_all_ui などを呼ぶ
            dungeon = handle_game(screen, events, player, dungeon, ui_elements, game_state)
            
            # 各種重要オブジェクトの健全性チェック
            assert dungeon is not None, "Dungeon object lost during update"
            assert player is not None, "Player object lost during update"
            
        print("[OK] 起動・描画スモークテスト合格！")
        
    except Exception as e:
        print(f"クラッシュ検知: {e}")
        import traceback
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    try:
        test_game_boot_and_render()
        pygame.quit()
    except:
        sys.exit(1)
